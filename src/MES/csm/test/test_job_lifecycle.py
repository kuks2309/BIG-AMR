"""Tests for the job state machine and the main cycle.

Everything runs on ManualClock, so a 600-second timeout is verified instantly
and identically on every run. No sleeps, no flakiness.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters.base import StationStatus, TaskType, TransportResult  # noqa: E402
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment  # noqa: E402
from csm.main_cycle import MainCycle                            # noqa: E402


def build(travel=8.0, timeout=600.0, accept=True):
    clock = ManualClock()
    equipment = MockEquipment(["station_3", "station_9"], clock)
    acs = MockAcs(clock, travel_seconds=travel, accept=accept)
    cycle = MainCycle(equipment, acs, clock=clock, logger=lambda m: None,
                      job_timeout_s=timeout)
    cycle.source_for = lambda sid: "station_3"
    return clock, equipment, acs, cycle


def request_transport(equipment, to="station_9", frm="station_3"):
    """Start work the way it really starts: material exists somewhere, and a
    machine asks for it. Both halves are needed — a call nobody can serve is
    left outstanding, and material nobody asked for moves nothing."""
    equipment.force_status(frm, StationStatus.FINISHED)
    return equipment.raise_call(to, TaskType.LOAD)


# ---------------------------------------------------------------- happy path

def test_job_reaches_done():
    clock, equipment, acs, cycle = build(travel=8.0)

    request_transport(equipment)
    cycle.tick()                       # read_inputs creates the job

    assert len(cycle.active) == 1
    job = cycle.active[0][0]
    assert job.state_name == "ASSIGNED"     # t1 fired on the same tick

    cycle.tick()                       # t2: ACS accepted -> RUNNING
    assert job.state_name == "RUNNING"

    clock.advance(9.0)                 # robot arrives
    cycle.tick()                       # t3 -> DONE

    assert job.state_name == "DONE"
    assert job in cycle.finished
    assert cycle.active == []


def test_done_notifies_destination_station():
    clock, equipment, acs, cycle = build(travel=1.0)
    # Route to a station the mock actually knows about. The default destination
    # ("station_out") is a placeholder that exists in no factory.

    request_transport(equipment)
    cycle.tick(); cycle.tick()
    clock.advance(2.0)
    cycle.tick()

    assert any(cmd == "collected" for _, _, cmd in equipment.commands)


def test_unknown_destination_is_warned_not_silent():
    """A notification the destination refuses must not look like clean success."""
    clock, equipment, acs, cycle = build(travel=1.0)
    # Route to a station the mock has never heard of. The transport still
    # succeeds — the robot went and came back — but the notification does not,
    # and that difference has to survive into the log.
    request_transport(equipment, to="station_9")
    cycle.source_for = lambda sid: "station_3"
    logged = []
    cycle.logger = logged.append
    cycle.tick(); cycle.tick()
    cycle.store.active[0].job.to_station = "no_such_station"
    clock.advance(2.0)
    cycle.tick()

    job = cycle.finished[0]
    assert job.state_name == "DONE"          # transport did succeed
    assert any("did not accept" in m for m in logged)



# ------------------------------------------------------------- failure paths

def test_timeout_moves_running_to_failed():
    """t5 — the transition that stops a blind takeover hanging forever."""
    clock, equipment, acs, cycle = build(travel=8.0, timeout=600.0)

    request_transport(equipment)
    cycle.tick(); cycle.tick()
    job = cycle.finished[0] if cycle.finished else cycle.active[0][0]
    assert job.state_name == "RUNNING"

    acs.never_arrives(job.job_id)      # the robot never reports arrival
    clock.advance(601.0)
    cycle.tick()

    assert job.state_name == "FAILED"
    assert "timeout" in job.failure_reason


def test_acs_failure_moves_to_failed():
    clock, equipment, acs, cycle = build()
    acs.fail_next = True

    request_transport(equipment)
    cycle.tick(); cycle.tick(); cycle.tick()

    job = cycle.finished[0]
    assert job.state_name == "FAILED"
    assert "ACS" in job.failure_reason


def test_busy_fleet_queues_the_job_instead_of_failing_it():
    """A busy ACS means wait, not give up.

    The regression: SimAcs returned REJECTED when it already had a job in
    flight, and REJECTED fails a job outright. With a single-robot fleet every
    job created while another was travelling was destroyed on the spot — the
    line produced work and the MES threw it away.
    """
    from csm.adapters.base import TransportResult

    clock, equipment, acs, cycle = build()

    class BusyThenFree:
        """Busy for the first two submissions, then accepts."""
        def __init__(self):
            self.calls = 0

        def submit_job(self, job):
            self.calls += 1
            return (TransportResult.BUSY if self.calls <= 2
                    else TransportResult.ACCEPTED)

        def get_job_result(self, job_id):
            return TransportResult.ARRIVED

        def cancel_job(self, job_id):
            return True

    cycle.acs = BusyThenFree()
    request_transport(equipment)

    # One transition per tick, so this takes two: t1 into ASSIGNED (which
    # submits and is told BUSY), then t_busy back out to IDLE.
    cycle.tick()
    assert cycle.active[0][0].state_name == "ASSIGNED"
    cycle.tick()
    assert cycle.active[0][0].state_name == "IDLE"
    assert not cycle.finished         # crucially, NOT failed

    clock.advance(4.0)                # past the retry backoff
    cycle.tick(); cycle.tick()        # attempt 2 -> BUSY again
    assert cycle.active[0][0].state_name == "IDLE"

    clock.advance(4.0)
    cycle.tick()                      # attempt 3 -> ACCEPTED
    assert cycle.active[0][0].state_name in ("ASSIGNED", "RUNNING")

    cycle.tick(); cycle.tick()
    assert cycle.finished[0].state_name == "DONE"


def test_busy_retry_is_rate_limited():
    """Retries must be spaced, not attempted on every tick."""
    from csm.adapters.base import TransportResult

    clock, equipment, acs, cycle = build()

    class AlwaysBusy:
        def __init__(self):
            self.calls = 0

        def submit_job(self, job):
            self.calls += 1
            return TransportResult.BUSY

        def get_job_result(self, job_id):
            return TransportResult.UNKNOWN

        def cancel_job(self, job_id):
            return True

    busy = AlwaysBusy()
    cycle.acs = busy
    request_transport(equipment)

    for _ in range(20):               # 20 ticks, no time passing
        cycle.tick()

    # One immediate attempt; the rest are held off by the backoff.
    assert busy.calls == 1


def test_rejected_job_fails_without_running():
    clock, equipment, acs, cycle = build(accept=False)

    request_transport(equipment)
    cycle.tick(); cycle.tick()

    job = cycle.finished[0]
    assert job.state_name == "FAILED"
    assert "RUNNING" not in [h[2] for h in job.history]


def test_failed_job_cancels_at_acs():
    """A timed-out job must not leave a robot still driving to it."""
    clock, equipment, acs, cycle = build(timeout=10.0)
    request_transport(equipment)
    cycle.tick(); cycle.tick()
    job = cycle.active[0][0]

    acs.never_arrives(job.job_id)
    clock.advance(11.0)
    cycle.tick()

    assert acs.get_job_result(job.job_id) is TransportResult.FAILED


# ------------------------------------------------------- structural guarantees

def test_idle_cannot_reach_done_directly():
    """There is no IDLE -> DONE transition, so that jump cannot occur."""
    from csm.job_fsm import build_job_fsm

    fsm = build_job_fsm()
    illegal = [t for t in fsm.transitions
               if t.source.name == "IDLE" and t.target.name == "DONE"]
    assert illegal == []


def test_running_has_all_three_exits():
    """Success, failure and timeout. A waiting state with only a success arrow
    is a place the system can hang."""
    from csm.job_fsm import build_job_fsm

    fsm = build_job_fsm()
    targets = {t.target.name for t in fsm.transitions if t.source.name == "RUNNING"}
    assert targets == {"DONE", "FAILED"}

    running_out = [t for t in fsm.transitions if t.source.name == "RUNNING"]
    assert len(running_out) == 3        # t3 success, t4 failure, t5 timeout


def test_only_one_transition_fires_per_tick():
    from csm.fsm import State, StateMachine, Transition

    a, b, c = State(), State(), State()
    a.name, b.name, c.name = "A", "B", "C"
    fsm = StateMachine(a, [Transition("t1", a, b, lambda _: True),
                           Transition("t2", b, c, lambda _: True)])

    fsm.step(None)
    assert fsm.current is b      # not c — one transition per tick

    fsm.step(None)
    assert fsm.current is c


def test_guard_error_does_not_stall_the_cycle():
    """A broken guard must not take the main cycle down with it."""
    clock, equipment, acs, cycle = build()
    request_transport(equipment)
    cycle.tick()

    _, ctx, fsm = cycle.active[0]
    fsm.transitions.insert(0, type(fsm.transitions[0])(
        "t_boom", fsm.current, fsm.current,
        lambda _: (_ for _ in ()).throw(RuntimeError("boom"))))

    cycle.tick()                       # must not raise
    assert ctx.guard_errors
    assert ctx.guard_errors[0][0] == "t_boom"


def test_station_produces_only_one_job_per_batch():
    """FINISHED sitting for many ticks must not spawn a job every tick."""
    clock, equipment, acs, cycle = build()
    request_transport(equipment)

    for _ in range(5):
        cycle.tick()

    assert len(cycle.active) + len(cycle.finished) == 1


def test_station_can_produce_again_after_its_job_completes():
    """The regression that stalled the line after two or three jobs.

    Completing a job must free the SOURCE station. If only the destination is
    notified, the source stays FINISHED, the read_inputs latch keeps it
    suppressed, and that station never produces work again — batches keep
    completing and nothing happens.
    """
    clock, equipment, acs, cycle = build(travel=1.0)

    # first batch
    request_transport(equipment)
    cycle.tick(); cycle.tick()
    clock.advance(2.0)
    cycle.tick()
    assert len(cycle.finished) == 1
    assert cycle.finished[0].state_name == "DONE"

    # the source must be free again, not stuck in FINISHED
    assert equipment.get_station_status("station_3") is StationStatus.IDLE

    # the station may be served again: material exists and it asks once more
    request_transport(equipment)
    cycle.tick(); cycle.tick()
    clock.advance(2.0)
    cycle.tick()

    assert len(cycle.finished) == 2
