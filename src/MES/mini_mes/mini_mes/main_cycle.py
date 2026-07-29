"""MainCycle - the loop that runs forever.

The "Core loop / Main Cycle" box on the 2026-07-28 whiteboard. Each tick does
three things and nothing else:

    read inputs   ask equipment what changed, create jobs for new work
    step the FSM  advance every active job by exactly one transition
    send commands (done inside the states, through the adapters)

The loop makes no decisions of its own. It only ticks. Every decision lives in a
guard, which is what keeps the logic in one inspectable place instead of spread
through the loop body.

Note it is `tick()` that is public, not the `while` itself. A cycle you can step
by hand is a cycle you can test — the whole job lifecycle, timeouts included, is
verified without ever calling run().
"""

import time

from .job import Job, JobContext
from .job_fsm import build_job_fsm


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
        self.equipment = equipment
        self.acs = acs
        self.clock = clock
        self.logger = logger
        self.period = 1.0 / rate_hz
        self.job_timeout_s = job_timeout_s

        self.active = []            # [(Job, JobContext, StateMachine)]
        self.finished = []          # jobs that reached DONE or FAILED
        self._seen_finished = set()  # stations already turned into a job
        self._job_seq = 0
        self.running = False

    # ---------------------------------------------------------------- jobs

    def create_job(self, from_station, to_station, priority=0):
        self._job_seq += 1
        now = self.clock()
        job = Job(
            job_id=f"job_{self._job_seq:04d}",
            from_station=from_station,
            to_station=to_station,
            priority=priority,
            created_at=now,
            state_since=now,
        )
        ctx = JobContext(job, self.equipment, self.acs, self.clock,
                         logger=self.logger, job_timeout_s=self.job_timeout_s)
        fsm = build_job_fsm(on_change=self._on_state_change)
        self.active.append((job, ctx, fsm))
        self.logger(f"[{job.job_id}] created: {from_station} -> {to_station}")
        return job

    def _on_state_change(self, ctx, transition):
        """Mirror the FSM's state onto the job record.

        state_since is reset here, and that is what makes the timeout guard mean
        "too long in *this* state" rather than "too long since the job existed".
        """
        job = ctx.job
        job.state_name = transition.target.name
        job.state_since = ctx.now()
        job.history.append((ctx.now(), transition.name, transition.target.name))

    # ---------------------------------------------------------------- loop

    def read_inputs(self):
        """Turn finished stations into transport jobs.

        A station is only converted once — without `_seen_finished`, a station
        sitting in FINISHED would spawn a new job on every tick, five times a
        second, until something collected it.
        """
        from .adapters.base import StationStatus

        for station_id in self.equipment.list_stations():
            status = self.equipment.get_station_status(station_id)

            if status is StationStatus.FINISHED:
                if station_id not in self._seen_finished:
                    self._seen_finished.add(station_id)
                    self.on_station_finished(station_id)
            else:
                # Re-arm once it leaves FINISHED, so the next batch is noticed.
                self._seen_finished.discard(station_id)

    def on_station_finished(self, station_id):
        """Override to choose a destination. Default sends everything to
        `station_out`, which is enough to exercise the pipeline."""
        self.create_job(from_station=station_id, to_station="station_out")

    def step_jobs(self):
        """Advance every active job by one tick, retiring the terminal ones."""
        still_active = []
        for job, ctx, fsm in self.active:
            fsm.step(ctx)
            if fsm.current.name in ("DONE", "FAILED"):
                self.finished.append(job)
                self.logger(f"[{job.job_id}] retired in {fsm.current.name}")
            else:
                still_active.append((job, ctx, fsm))
        self.active = still_active

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
