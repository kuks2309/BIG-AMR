"""C9 — the four-step cancellation, and the promise it gives back.

`AGV_Task_Recive = 1` makes a machine STOP ASKING. That is its whole purpose,
and it means every call CSM answers leaves a machine silent and waiting. If CSM
then gives up and says nothing, the machine waits for ever for a robot that is
never coming — and nobody notices, because our job retired, the machine's
request succeeded, and only the material knows.

    AGV sets AGV_Task_Processing = 9 -> host deletes the task -> host sets
    MC_Task_Delete = 1 -> AGV moves off 9 -> host clears MC_Task_Delete = 0.
    The machine then raises an alarm; an operator resets it and re-dispatches.

The rule that carries the safety is that step 4 may only happen after step 3 is
SEEN. Never on a timer.
"""

import sys
import pathlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters.base import StationStatus, TaskProcessing, TaskType  # noqa: E402
from csm.adapters.cancellation import (CancelState, TaskCancellation,  # noqa: E402
                                       TASK_CANCELLED)
from csm.adapters.mock import (ManualClock, MockAcs, MockEquipment,    # noqa: E402
                               OpcUaEquipment)
from csm.records import CallStatus                                     # noqa: E402
from csm.runtime.job_store import MAX_ATTEMPTS, JobStore               # noqa: E402


def machine(cancel_response=1.0, stations=("1A01",)):
    clock = ManualClock()
    return clock, OpcUaEquipment(list(stations), clock,
                                 cancel_response_seconds=cancel_response)


def run(clock, equipment, seconds, step=0.5):
    """Poll the way the monitor task does — the handshake needs every tick."""
    out = []
    for _ in range(int(seconds / step)):
        clock.advance(step)
        out.append(equipment.resolve_cancellations(clock()))
    return out


# ------------------------------------------------------- the state machine alone

def test_step_one_asserts_the_cancelled_code():
    c = TaskCancellation("1A01", "job_0001", "call_0001", 0.0, 10.0)
    assert c.agv_task_processing == TASK_CANCELLED == 9
    assert c.state is CancelState.RAISED


def test_step_four_waits_for_step_three():
    """THE RULE. Clearing 9 before the machine has deleted the task takes the
    cancellation back without the machine ever having seen it."""
    c = TaskCancellation("1A01", "job_0001", "call_0001", 0.0, 10.0)
    for now in (1.0, 2.0, 5.0, 9.0):
        c.observe(now, mc_task_delete=False)
        assert c.agv_task_processing == TASK_CANCELLED, f"dropped 9 at {now}"


def test_step_four_happens_once_step_three_is_seen():
    c = TaskCancellation("1A01", "job_0001", "call_0001", 0.0, 10.0)
    c.observe(1.0, mc_task_delete=True)

    assert c.state is CancelState.DELETING
    assert c.agv_task_processing is None
    assert c.handed_back


def test_all_four_steps():
    c = TaskCancellation("1A01", "job_0001", "call_0001", 0.0, 10.0)
    c.observe(1.0, mc_task_delete=False)
    c.observe(2.0, mc_task_delete=True)
    c.observe(3.0, mc_task_delete=False)

    assert c.state is CancelState.COMPLETE
    assert c.done


def test_the_time_limit_never_clears_the_signal():
    """Timing out is a report, not a decision. Silence never means clear."""
    c = TaskCancellation("1A01", "job_0001", "call_0001", 0.0, 10.0)
    c.observe(50.0, mc_task_delete=False)

    assert c.state is CancelState.STALLED
    assert c.agv_task_processing == TASK_CANCELLED
    assert c.stranded, "the machine has not been told and does not know"


def test_a_late_reply_is_still_a_reply():
    """STALLED is not terminal. A machine that answers slowly is not a machine
    that never answers, and latching a failure would need a restart to clear."""
    c = TaskCancellation("1A01", "job_0001", "call_0001", 0.0, 10.0)
    c.observe(50.0, mc_task_delete=False)
    c.observe(51.0, mc_task_delete=True)

    assert c.state is CancelState.DELETING
    assert c.stalled_at == 50.0, "but it should still be on the record"


def test_a_stall_after_the_machine_knows_is_not_stranded():
    """The two stalls mean opposite things.

    Before step 3 the material is stranded and nobody knows. After it, the
    machine has the task back and only the handshake is untidy.
    """
    c = TaskCancellation("1A01", "job_0001", "call_0001", 0.0, 10.0)
    c.observe(1.0, mc_task_delete=True)      # machine knows
    c.observe(50.0, mc_task_delete=True)     # ...and never clears the flag

    assert c.state is CancelState.STALLED
    assert c.handed_back
    assert not c.stranded


def test_a_link_that_cannot_report_the_flag_says_so():
    """None is not False. False says the machine has not deleted the task;
    None says we cannot tell, which makes the handshake unverifiable rather
    than merely unfinished."""
    c = TaskCancellation("1A01", "job_0001", "call_0001", 0.0, 10.0)
    assert c.observe(1.0, mc_task_delete=None) is CancelState.UNVERIFIABLE


def test_there_is_no_default_patience():
    """The protocol does not say how long a host may take, so nor do we."""
    with pytest.raises(ValueError):
        TaskCancellation("1A01", "job_0001", "call_0001", 0.0, 0)
    with pytest.raises(ValueError):
        TaskCancellation("1A01", "job_0001", "call_0001", 0.0, None)


# ------------------------------------------------- against a machine that answers

def test_the_machine_deletes_the_task_and_says_so():
    clock, equipment = machine()
    cancel = equipment.cancel_task("1A01", "job_0001", clock())

    assert equipment.task_processing("1A01") is TaskProcessing.TASK_CANCELLED
    run(clock, equipment, 2.0)
    assert cancel.handed_back


def test_step_four_is_a_write_not_a_decision():
    """The handshake deciding it may drop the 9 changes nothing at the machine
    until somebody writes it. That write is what step 4 IS."""
    clock, equipment = machine()
    equipment.cancel_task("1A01", "job_0001", clock())
    run(clock, equipment, 2.0)

    assert equipment.task_processing("1A01") is None, \
        "the machine still sees a 9 and will wait for ever"


def test_the_machine_alarms_at_the_end():
    """The point of the whole dance. The work does not quietly come back to
    CSM — it goes to a person."""
    clock, equipment = machine()
    equipment.cancel_task("1A01", "job_0001", clock())
    run(clock, equipment, 4.0)

    assert equipment.alarm_at("1A01")


def test_the_operator_reset_puts_the_work_back_on_the_line():
    clock, equipment = machine()
    call = equipment.raise_call("1A01", TaskType.UNLOAD)
    equipment.acknowledge_call(call)             # the machine stops asking
    equipment.cancel_task("1A01", "job_0001", clock())
    run(clock, equipment, 4.0)

    assert equipment.reset_alarm("1A01")
    calls = equipment.poll_calls()
    assert [c.task_type for c in calls] == [TaskType.UNLOAD], \
        "re-dispatch must ask for what it asked for before"
    assert not equipment.alarm_at("1A01")


def test_a_completed_cancellation_stops_being_pending():
    clock, equipment = machine()
    equipment.cancel_task("1A01", "job_0001", clock())
    results = run(clock, equipment, 4.0)

    assert sum(len(finished) for finished, _ in results) == 1
    assert equipment.resolve_cancellations(clock()) == ([], [])


# --------------------------------------------- against a machine that does not

def test_a_machine_that_never_answers_leaves_us_asserting_nine():
    clock, equipment = machine()
    equipment.ignore_cancellation("1A01")
    cancel = equipment.cancel_task("1A01", "job_0001", clock())
    run(clock, equipment, 30.0)

    assert cancel.stranded
    assert equipment.task_processing("1A01") is TaskProcessing.TASK_CANCELLED
    assert not equipment.alarm_at("1A01")


def test_a_stranded_cancellation_is_reported_every_tick():
    """Material is standing at a station that still expects a robot. That is
    not a thing to mention once."""
    clock, equipment = machine()
    equipment.ignore_cancellation("1A01")
    equipment.cancel_task("1A01", "job_0001", clock())
    results = run(clock, equipment, 30.0)

    reported = sum(len(stranded) for _, stranded in results)
    assert reported > 5, f"only reported {reported} times"


def test_a_plain_mock_cannot_run_the_dance_and_admits_it():
    """MockEquipment has no MC_Task_Delete. It must not pretend one is False."""
    clock = ManualClock()
    equipment = MockEquipment(["station_3"], clock)
    cancel = equipment.cancel_task("station_3", "job_0001", clock())

    assert cancel.state is CancelState.UNVERIFIABLE


# --------------------------------------------------- and now through the store

def build_store(**kw):
    clock = ManualClock()
    equipment = OpcUaEquipment(["1A01", "1A02"], clock,
                               cancel_response_seconds=1.0)
    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     **kw)
    return clock, equipment, store


def abandoned_job(store, clock, attempt=MAX_ATTEMPTS, retryable=True):
    call = store.records.add_call(station="1A01", task_type=TaskType.LOAD,
                                  source="machine", raised_at=clock())
    record = store.create("1A02", "1A01", call_id=call.call_id, attempt=attempt)
    store.records.acknowledge_call(call.call_id, at=clock(),
                                   job_id=record.job.job_id)
    record.job.failure_reason = "ACS reported failure"
    record.job.retryable = retryable
    return call, record.job


def test_giving_up_hands_the_call_back():
    clock, equipment, store = build_store()
    call, job = abandoned_job(store, clock)

    assert store._raise_again(job) is None, "this is the give-up path"
    assert equipment.task_processing("1A01") is TaskProcessing.TASK_CANCELLED
    assert store.abandoned == 1


def test_the_call_record_says_who_failed():
    """WITHDRAWN is the machine changing its mind. CANCELLED is us failing.
    They look the same in a count of unserved calls and mean the opposite."""
    clock, equipment, store = build_store()
    call, job = abandoned_job(store, clock)
    store._raise_again(job)

    assert store.records.call(call.call_id).status is CallStatus.CANCELLED
    assert store.records.call(call.call_id).cancelled_at is not None


def test_a_retry_does_not_alarm_the_machine():
    """A retry is still us coming. Telling the machine would alarm a station
    over a job that is about to be served."""
    clock, equipment, store = build_store()
    call, job = abandoned_job(store, clock, attempt=1)

    assert store._raise_again(job) is not None, "this is the retry path"
    assert equipment.task_processing("1A01") is None
    assert store.abandoned == 0


def test_a_job_a_person_cancelled_still_frees_the_machine():
    """The person stopped the transport, not the machine's need to be told."""
    clock, equipment, store = build_store()
    call, job = abandoned_job(store, clock, attempt=1, retryable=False)
    store._raise_again(job)

    assert store.abandoned == 1
    assert store.records.call(call.call_id).status is CallStatus.CANCELLED


def test_csms_own_work_has_nobody_to_tell():
    """The WIP diversion answers no call — no machine is waiting on it."""
    clock, equipment, store = build_store()
    job = store.create("1A02", "1A01", attempt=MAX_ATTEMPTS).job
    job.failure_reason = "ACS reported failure"

    assert store._raise_again(job) is None
    assert store.abandoned == 0
    assert equipment.task_processing("1A01") is None


def test_the_whole_way_round_from_failure_to_re_dispatch():
    """Give up -> hand back -> all four steps -> alarm -> operator -> called
    again. The material never stops being somebody's problem."""
    clock, equipment, store = build_store()
    call, job = abandoned_job(store, clock)
    equipment.force_status("1A02", StationStatus.FINISHED)

    store._raise_again(job)
    run(clock, equipment, 5.0)

    assert equipment.alarm_at("1A01"), "step 5"
    assert equipment.reset_alarm("1A01"), "a person clears it"
    assert [c.station_id for c in equipment.poll_calls()] == ["1A01"]
