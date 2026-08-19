"""Integration tests for the assembled CSM.

Two things are being checked here that no single-task test can see:

1. the three FSMs actually cooperate — a batch finishing at a machine ends as a
   retired job, with nobody having called anything directly
2. the concurrent runtime reaches the **same outcome** as MainCycle. That is the
   whole claim of the merge, and it is worth an explicit test rather than an
   assurance.
"""

import asyncio
import sys
import pathlib
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters.base import StationStatus, TaskType, TransportResult  # noqa: E402
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment  # noqa: E402
from csm.main_cycle import MainCycle                          # noqa: E402
from csm.runtime import build_mes                             # noqa: E402

STATIONS = ["ASRS", "1A01", "1T01", "1L01"]

#: Who feeds whom. The call says who WANTS material; this says where it is.
FEEDS = {"1A01": "ASRS", "1T01": "1A01", "1L01": "1T01"}


def source_for(station_id):
    return FEEDS.get(station_id, "ASRS")


def call_everywhere(equipment):
    """Every machine asks for material, and the supply chain is stocked.

    This is what a busy line looks like from this layer: several outstanding
    calls at once, competing for a fleet that cannot serve them all.
    """
    for sid in STATIONS:
        equipment.force_status(sid, StationStatus.FINISHED)
    for sid in ("1A01", "1T01", "1L01"):
        equipment.raise_call(sid, TaskType.LOAD)


def build(travel=2.0, timeout=600.0, supervisor=True):
    clock = ManualClock()
    equipment = MockEquipment(STATIONS, clock)
    app = build_mes(equipment, MockAcs(clock, travel_seconds=travel),
                    source_for=source_for, clock=clock, logger=lambda m: None,
                    job_timeout_s=timeout, install_supervisor=supervisor)
    return clock, equipment, app


def tick(app, n=1):
    for _ in range(n):
        asyncio.run(app.tick_all())


class OneRobotAcs:
    """A fleet of exactly one. Everything after the first job gets BUSY.

    This is the condition that made queueing worth building: the real SimAcs
    behaves this way, and MainCycle's original code destroyed every job created
    while another was travelling.
    """

    def __init__(self, clock, travel_seconds=2.0):
        self._clock = clock
        self._travel = travel_seconds
        self._current = None
        self._arrive_at = None
        self.submissions = 0
        self.busy_answers = 0

    def submit_job(self, job):
        self.submissions += 1
        if self._current is not None:
            self.busy_answers += 1
            return TransportResult.BUSY
        self._current = job.job_id
        self._arrive_at = self._clock() + self._travel
        return TransportResult.ACCEPTED

    def get_job_result(self, job_id):
        if job_id != self._current:
            return TransportResult.UNKNOWN
        if self._clock() >= self._arrive_at:
            self._current = None
            return TransportResult.ARRIVED
        return TransportResult.IN_PROGRESS

    def cancel_job(self, job_id):
        if job_id == self._current:
            self._current = None
        return True


# ------------------------------------------------------------ they cooperate

def test_a_finished_batch_becomes_a_retired_job():
    """Nobody calls anything directly. The monitor notices, the dispatcher
    grants, the tracker moves it — three machines, one outcome."""
    clock, equipment, app = build(travel=2.0)
    equipment.force_status("ASRS", StationStatus.FINISHED)
    equipment.raise_call("1A01", TaskType.LOAD)

    tick(app, 3)
    clock.advance(3.0)
    tick(app)

    assert app.health() == {
        "jobs_active": 0, "jobs_finished": 1, "created": 1, "granted": 1,
        "completed": 1, "failed": 0, "stations_busy": [],
    }


def test_the_route_is_followed_not_a_default_sink():
    clock, equipment, app = build(travel=1.0)
    equipment.force_status("1A01", StationStatus.FINISHED)
    equipment.raise_call("1T01", TaskType.LOAD)
    tick(app, 2)

    assert app.store.active[0].job.to_station == "1T01"
    assert app.store.active[0].job.from_station == "1A01"


def test_a_station_produces_again_after_its_job_completes():
    """The regression that stalled the line, re-checked through the new path."""
    clock, equipment, app = build(travel=1.0)

    equipment.force_status("ASRS", StationStatus.FINISHED)
    equipment.raise_call("1A01", TaskType.LOAD)
    tick(app, 3); clock.advance(2.0); tick(app)
    assert app.tracker.completed == 1

    equipment.force_status("ASRS", StationStatus.FINISHED)
    equipment.raise_call("1A01", TaskType.LOAD)
    tick(app, 3); clock.advance(2.0); tick(app)
    assert app.tracker.completed == 2


# ------------------------------------------------------------------ queueing

def test_a_one_robot_fleet_drains_a_queue_without_losing_a_job():
    clock, equipment, app = build(travel=2.0)
    acs = OneRobotAcs(clock, travel_seconds=2.0)
    app.store.acs = acs

    call_everywhere(equipment)

    for _ in range(60):
        tick(app)
        clock.advance(0.5)

    assert app.tracker.completed == 3, app.health()
    assert app.tracker.failed == 0, "a busy fleet must mean wait, not give up"


def test_the_dispatcher_stops_the_fleet_being_shouted_at():
    """The reason DispatcherTask exists, measured against the driver without it.

    Ungated, every IDLE job re-submits whenever its own backoff expires, so the
    wasted submissions grow with the queue length on every retry round. Gated,
    one job asks per turn.

    Both drivers are run over the same scenario and compared, rather than
    asserting an absolute number. At small queue depths the two are identical —
    with three jobs both produce exactly three BUSY answers — so a threshold
    test here would pass whether or not the dispatcher did anything at all. The
    effect is a queueing effect and only exists once there is a queue.

    Note the gated count is not zero and cannot be. The dispatcher takes turns;
    it does not know whether the fleet is free, because asking would need an
    interface the ACS may not have (ARCHITECTURE.md §10). One BUSY per turn is
    the floor, and the saving is against one BUSY per waiting job per round.
    """
    stations = [f"station_{i}" for i in range(10)] + ["sink"]
    producers = stations[:-1]

    def run(gated):
        clock = ManualClock()
        equipment = MockEquipment(stations, clock)
        acs = OneRobotAcs(clock, travel_seconds=2.0)
        if gated:
            app = build_mes(equipment, acs, source_for=lambda s: "sink",
                            clock=clock, logger=lambda m: None,
                            install_supervisor=False)
            drive, finished = (lambda: asyncio.run(app.tick_all()),
                               lambda: len(app.store.finished))
        else:
            cycle = MainCycle(equipment, acs, clock=clock,
                              logger=lambda m: None)
            cycle.source_for = lambda sid: "sink"
            drive, finished = cycle.tick, lambda: len(cycle.finished)

        for sid in stations:
            equipment.force_status(sid, StationStatus.FINISHED)
        for sid in producers:
            equipment.raise_call(sid, TaskType.LOAD)
        for _ in range(200):
            drive()
            clock.advance(0.5)
        return acs, finished()

    ungated_acs, ungated_done = run(gated=False)
    gated_acs, gated_done = run(gated=True)

    # Neither driver may lose a job — a busy fleet means wait, not give up.
    assert ungated_done == len(producers)
    assert gated_done == len(producers)

    assert gated_acs.busy_answers < ungated_acs.busy_answers, (
        f"taking turns saved nothing: {gated_acs.busy_answers} BUSY gated vs "
        f"{ungated_acs.busy_answers} ungated")


# -------------------------------------------------- equivalence with MainCycle

def test_the_two_drivers_reach_the_same_outcome():
    """The claim of the merge, tested rather than asserted.

    Same factory, same fleet, same clock schedule — the sequential driver and
    the three concurrent FSMs must retire the same jobs with the same results.
    """
    def run_main_cycle():
        clock = ManualClock()
        equipment = MockEquipment(STATIONS, clock)
        cycle = MainCycle(equipment, OneRobotAcs(clock), clock=clock,
                          logger=lambda m: None)
        cycle.source_for = source_for
        call_everywhere(equipment)
        for _ in range(60):
            cycle.tick()
            clock.advance(0.5)
        return cycle.finished

    def run_supervised():
        clock = ManualClock()
        equipment = MockEquipment(STATIONS, clock)
        app = build_mes(equipment, OneRobotAcs(clock), source_for=source_for,
                        clock=clock, logger=lambda m: None,
                        install_supervisor=False)
        call_everywhere(equipment)
        for _ in range(60):
            asyncio.run(app.tick_all())
            clock.advance(0.5)
        return app.store.finished

    sequential = run_main_cycle()
    concurrent = run_supervised()

    def summarise(jobs):
        return sorted((j.from_station, j.to_station, j.state_name) for j in jobs)

    assert summarise(sequential) == summarise(concurrent)
    assert all(j.state_name == "DONE" for j in concurrent)


# --------------------------------------------------- under the real supervisor

def test_it_runs_under_the_supervisor_on_real_timers():
    """No hand-stepping: the FSMs are started, left alone, and must get a job
    through on their own periods."""
    equipment = MockEquipment(STATIONS, time.monotonic)
    app = build_mes(equipment, MockAcs(time.monotonic, travel_seconds=0.05),
                    source_for=source_for, clock=time.monotonic, logger=lambda m: None,
                    poll_seconds={"equipment_monitor": 0.02,
                                  "dispatcher": 0.02,
                                  "job_tracker": 0.02})
    equipment.force_status("ASRS", StationStatus.FINISHED)
    equipment.raise_call("1A01", TaskType.LOAD)

    async def scenario():
        task = asyncio.ensure_future(
            app.supervisor.run(install_signal_handlers=False))
        await asyncio.sleep(0.5)
        app.supervisor.request_stop()
        return await task

    health = asyncio.run(asyncio.wait_for(scenario(), 5.0))

    assert app.tracker.completed >= 1, app.health()
    assert all(h["errors"] == 0 for h in health.values()), health


def test_one_crashing_fsm_does_not_stop_the_others():
    """MainCycle is one failure domain — an exception anywhere stops
    everything. Splitting the loop was supposed to buy this."""
    equipment = MockEquipment(STATIONS, time.monotonic)
    app = build_mes(equipment, MockAcs(time.monotonic, travel_seconds=0.05),
                    source_for=source_for, clock=time.monotonic, logger=lambda m: None,
                    poll_seconds={"equipment_monitor": 0.02,
                                  "dispatcher": 0.02,
                                  "job_tracker": 0.02})

    calls = {"n": 0}
    original = app.dispatcher.step

    async def flaky():
        calls["n"] += 1
        if calls["n"] <= 3:
            raise RuntimeError("dispatcher blew up")
        await original()

    app.dispatcher.step = flaky
    equipment.force_status("ASRS", StationStatus.FINISHED)
    equipment.raise_call("1A01", TaskType.LOAD)

    async def scenario():
        task = asyncio.ensure_future(
            app.supervisor.run(install_signal_handlers=False))
        await asyncio.sleep(0.5)
        app.supervisor.request_stop()
        return await task

    health = asyncio.run(asyncio.wait_for(scenario(), 5.0))

    assert health["dispatcher"]["errors"] == 3
    assert health["equipment_monitor"]["errors"] == 0
    assert health["job_tracker"]["errors"] == 0
    assert app.monitor.created >= 1, "a sibling's crash stopped the monitor"
    assert app.tracker.completed >= 1, "the system did not recover"


# ---------------------------------------------------------------- assembly

def test_the_store_is_gated_when_a_dispatcher_is_present():
    _, _, app = build()
    assert app.store.dispatch_gated is True
    assert app.store.create("station_3", "station_9").ctx.dispatch_permit is False


def test_every_task_is_registered_with_the_supervisor():
    """Four now: charging joined the three job-layer FSMs.

    The list is asserted in full rather than by count, because a task that is
    constructed and never registered is a task that silently never runs — and
    a supervisor exists precisely so that cannot happen quietly.
    """
    _, _, app = build()
    assert [f.name for f in app.supervisor.fsms] == \
        ["equipment_monitor", "dispatcher", "job_tracker", "charging"]
