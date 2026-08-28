"""The four transport states, and the three rules that need them.

CCS manual §2.3, §4.6.6, §5.8-5.12. Collapsing the four into one RUNNING state
loses all three rules below, and loses the first in the expensive direction.
"""

import pytest

from csm.transport_task import (ABNORMAL_SECONDS, WARNING_SECONDS, Ageing,
                                Escalation, PostTaskState, TaskState,
                                TransportTask)


def task(**kw):
    return TransportTask(task_id="T-1", from_rack="1501", to_rack="1801", **kw)


# --------------------------------------------------- the states themselves

def test_a_new_task_is_dispatched_with_no_vehicle():
    """中控已下发 — CCS gave it to the AGV system, which received it and has
    not assigned a vehicle."""
    t = task()

    assert t.state is TaskState.DISPATCHED
    assert t.vehicle is None


def test_the_vehicle_number_appears_when_it_starts_executing():
    """§4.6.6 ② says so explicitly, and it is the only place it can appear -
    before this there is no vehicle to name."""
    t = task()

    t.assign("AGV-07", at=10.0)

    assert t.state is TaskState.EXECUTING
    assert t.vehicle == "AGV-07"


def test_the_four_states_run_in_order():
    t = task()
    t.assign("AGV-07", at=10.0)
    t.loaded(at=60.0)
    t.arrived(at=120.0)

    assert [s for _at, s in t.history] == [
        TaskState.EXECUTING, TaskState.LOADED, TaskState.ARRIVED]


# ------------------------------------ rule 1: cancellation is state-dependent

@pytest.mark.parametrize("state", [TaskState.DISPATCHED, TaskState.EXECUTING])
def test_cancel_is_allowed_before_the_vehicle_reaches_the_source(state):
    t = task(state=state)

    assert t.may_cancel() is True
    assert t.cancel(at=5.0) is True
    assert t.cancelled is True


def test_cancel_is_REFUSED_once_loaded():
    """§5.12: 取消的话 AGV 停在半路 - the AGV would stop in the middle of the
    route holding a pallet. This is the rule that cannot be stated at all
    without the LOADED state."""
    t = task(state=TaskState.LOADED)

    assert t.may_cancel() is False
    assert t.cancel(at=5.0) is False
    assert t.cancelled is False


def test_cancel_after_arrival_is_refused_too_but_for_the_other_reason():
    """Not dangerous - pointless. There is nothing left to cancel."""
    t = task(state=TaskState.ARRIVED)

    assert t.may_cancel() is False


def test_a_refused_cancel_is_not_an_error():
    """The caller has to HEAR the refusal, so it comes back as False rather
    than an exception somebody wraps in a bare except."""
    t = task(state=TaskState.LOADED)

    assert t.cancel(at=1.0) is False


# ------------------------------- rule 2: what "in flight" means (§4.6.6)

def test_a_task_that_has_not_arrived_is_in_flight():
    assert task().in_flight is True
    assert task(state=TaskState.LOADED).in_flight is True


def test_an_arrived_task_with_no_post_task_is_finished():
    t = task(state=TaskState.ARRIVED, post_task=PostTaskState.NONE)

    assert t.in_flight is False
    assert t.complete is True


def test_an_arrived_task_with_a_pending_post_task_is_STILL_in_flight():
    """The definition every screen in the manual uses. A task that has
    delivered its pallet and still owes a return leg is occupying a vehicle,
    and a count that ignores it over-commits the line."""
    t = task(state=TaskState.ARRIVED)
    t.needs_post_task(at=100.0)

    assert t.in_flight is True
    assert t.complete is False


def test_a_dispatched_post_task_is_still_in_flight():
    t = task(state=TaskState.ARRIVED)
    t.needs_post_task(at=100.0)
    t.post_task_dispatched(at=110.0)

    assert t.in_flight is True


def test_a_cancelled_post_task_lets_the_task_finish():
    t = task(state=TaskState.ARRIVED)
    t.needs_post_task(at=100.0)
    t.post_task_cancelled(at=110.0)

    assert t.in_flight is False


def test_never_needed_and_no_longer_needed_are_different_states():
    """They look the same from outside and answer different questions when
    something has gone wrong."""
    assert PostTaskState.NONE is not PostTaskState.CANCELLED


def test_a_cancelled_task_is_not_in_flight():
    t = task()
    t.cancel(at=5.0)

    assert t.in_flight is False


# -------------------------------------------- rule 3: ageing (§2.3)

def test_a_task_reporting_normally_is_normal():
    t = task()
    t.assign("AGV-07", at=100.0)

    assert t.ageing(now=100.0) is Ageing.NORMAL
    assert t.ageing(now=100.0 + WARNING_SECONDS - 1) is Ageing.NORMAL


def test_ten_minutes_of_silence_is_a_warning():
    t = task()
    t.assign("AGV-07", at=100.0)

    assert t.ageing(now=100.0 + WARNING_SECONDS) is Ageing.WARNING


def test_twenty_minutes_of_silence_is_abnormal():
    t = task()
    t.assign("AGV-07", at=100.0)

    assert t.ageing(now=100.0 + ABNORMAL_SECONDS) is Ageing.ABNORMAL


def test_ageing_is_measured_from_the_last_report_not_from_dispatch():
    """A task reporting every minute for an hour is healthy; one silent for
    twenty minutes is not, however new it is."""
    t = task(dispatched_at=0.0)
    t.assign("AGV-07", at=0.0)
    t.report(at=ABNORMAL_SECONDS)

    assert t.ageing(now=ABNORMAL_SECONDS + 60) is Ageing.NORMAL


def test_a_post_task_change_counts_as_a_report():
    """§2.3 applies the thresholds to the post-task status too."""
    t = task(state=TaskState.ARRIVED)
    t.assign("AGV-07", at=0.0)
    t.needs_post_task(at=ABNORMAL_SECONDS)

    assert t.ageing(now=ABNORMAL_SECONDS + 60) is Ageing.NORMAL


def test_the_two_thresholds():
    assert WARNING_SECONDS == 600
    assert ABNORMAL_SECONDS == 1200


# ------------------------------ what completion hands to the target rack

def test_the_task_carries_the_identity_that_completion_transfers():
    """§4.6.6: completion writes the material type, attribute, bobbin type and
    roll number INTO THE TARGET RACK. If the task does not hold them, delivery
    has nothing to transfer."""
    from csm.material import MaterialAttribute

    t = task(material_ref="R-1", material_type=302,
             material_attribute=MaterialAttribute.BRIGHT_CW, bobbin_type=430)

    assert t.carried_identity() == {
        "material_type": 302,
        "material_attribute": MaterialAttribute.BRIGHT_CW,
        "bobbin_type": 430}


def test_the_identity_goes_straight_into_describe_slot():
    """The shapes have to match, or the transfer needs a translation layer
    that will drift."""
    import inspect

    from csm.records import InMemoryRecords

    accepted = set(inspect.signature(InMemoryRecords.describe_slot).parameters)

    assert set(task().carried_identity()) <= accepted


# --------------------------------------------- the escalation is ordered

def test_the_escalation_has_three_named_levels_in_order():
    """§5.3-5.12, repeated verbatim six times. The enum exists so a caller has
    to NAME which level it is using rather than reaching for the convenient
    one - every level is prefixed 联系供应商, contact the supplier first."""
    assert [e.value for e in Escalation] == ["report", "simulate", "clear"]
