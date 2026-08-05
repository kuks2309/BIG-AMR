"""MainCycle - the sequential driver.

The "Core loop / Main Cycle" box on the 2026-07-28 whiteboard. Each tick does
two things and nothing else:

    read inputs   ask equipment what changed, create jobs for new work
    step the FSM  advance every active job by exactly one transition

The loop makes no decisions of its own. It only ticks. Every decision lives in a
guard, which is what keeps the logic in one inspectable place instead of spread
through the loop body.

Note it is `tick()` that is public, not the `while` itself. A cycle you can step
by hand is a cycle you can test — the whole job lifecycle, timeouts included, is
verified without ever calling run().

**This is now one of two drivers.** The bookkeeping moved to `runtime.JobStore`
so that this and the concurrent supervisor share it rather than each keeping a
copy. What is left here is the sequencing: read, then step, in that order, on
one thread.

    MainCycle          everything in order on one thread — tests, demo, and the
                       reference for what the system is supposed to do
    runtime/tasks.py   the same store driven by independent FSMs under the
                       Supervisor, which is the shape the whiteboard specifies

Keep this one. A single-threaded driver that steps by hand is why the job FSM's
bugs were findable at all, and the concurrent runtime is checked against it.
"""

import time

from .runtime.job_store import JobStore


class MainCycle:

    def __init__(self, equipment, acs, clock=time.monotonic, logger=print,
                 rate_hz=5.0, job_timeout_s=600.0):
        """
        :param equipment:     EquipmentAdapter (mock or real)
        :param acs:           AcsAdapter (mock or real)
        :param clock:         callable() -> seconds; injected so tests control time
        :param rate_hz:       tick rate. 5 Hz is plenty — this layer thinks in
                              jobs, which last minutes, not in control cycles
        :param job_timeout_s: how long a job may stay in one state before t5
        """
        self.period = 1.0 / rate_hz
        self.running = False
        self.store = JobStore(equipment, acs, clock, logger=logger,
                              job_timeout_s=job_timeout_s,
                              dispatch_gated=False)

    # -- delegated to the store, kept as attributes so callers read naturally --

    @property
    def equipment(self):
        return self.store.equipment

    @property
    def acs(self):
        return self.store.acs

    @acs.setter
    def acs(self, adapter):
        """Swapping the ACS mid-run is a test affordance, not production use.

        Jobs already created hold their own reference through JobContext, so
        this only affects jobs created afterwards — which is what the tests that
        use it expect.
        """
        self.store.acs = adapter

    @property
    def clock(self):
        return self.store.clock

    @property
    def logger(self):
        return self.store.logger

    @logger.setter
    def logger(self, fn):
        self.store.logger = fn

    @property
    def job_timeout_s(self):
        return self.store.job_timeout_s

    @property
    def active(self):
        return self.store.active

    @property
    def finished(self):
        return self.store.finished

    # ---------------------------------------------------------------- jobs

    def create_job(self, from_station, to_station, priority=0):
        return self.store.create(from_station, to_station, priority).job

    # ---------------------------------------------------------------- loop

    def read_inputs(self):
        """Turn outstanding calls into transport jobs.

        Corrected 2026-08-04 along with the concurrent driver. This used to
        watch for stations reporting FINISHED and invent work for them, which
        is backwards — the equipment calls, and material being present is a
        separate fact that decides whether a call can be *served*.

        Both drivers now read the same input through the same store, which is
        the point of sharing it. Two drivers implementing two different designs
        would be worse than the duplication the store was extracted to avoid.
        """
        from .adapters.base import StationStatus

        for call in self.store.equipment.poll_calls():
            source = self.source_for(call.station_id)
            # Not servable yet: leave the call outstanding rather than
            # acknowledging work we are not going to do.
            if (self.store.equipment.get_station_status(source)
                    is not StationStatus.FINISHED):
                continue
            if not self.store.claim_station(call.station_id):
                continue
            self.store.create(source, call.station_id, task_type=call.task_type)
            self.store.equipment.acknowledge_call(call)

    def source_for(self, station_id):
        """Which station feeds this one. Override to describe the real route.

        Note the direction: a call says who WANTS material, never where it
        comes from. Answering that is the CSM's job.
        """
        return "ASRS"

    def step_jobs(self):
        """Advance every active job by one tick, retiring the terminal ones."""
        self.store.step_all()

    def tick(self):
        """One pass of the main cycle. Public so tests can drive it by hand."""
        self.read_inputs()
        self.step_jobs()

    def run(self):
        """Loop until stop() is called."""
        self.running = True
        self.logger(f"main cycle running at {1.0 / self.period:.1f} Hz")
        try:
            while self.running:
                self.tick()
                time.sleep(self.period)
        except KeyboardInterrupt:
            self.logger("interrupted")
        finally:
            self.running = False
            self.logger("main cycle stopped")

    def stop(self):
        self.running = False
