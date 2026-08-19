"""The hostile equipment stand-in.

Every test here provokes something the real machines can do and a well-behaved
mock cannot: losing a request between polls, accepting a command and ignoring
it, withdrawing entry permission part way through a dock, going quiet.

These are the failure modes that lose work SILENTLY — no exception, no error
code, nothing in a log. They are the reason the stand-in has to be able to
misbehave, and the reason CSM cannot be called correct against a mock that
only behaves.
"""

import pytest

from csm.adapters.base import (MaterialPresence, StationStatus, TaskProcessing,
                               TaskType)
from csm.adapters.mock import ManualClock, OpcUaEquipment

STATIONS = ["GRV1_LD", "CTR1_LD"]


def build(comm_alarm=2.0):
    clock = ManualClock()
    return clock, OpcUaEquipment(STATIONS, clock, comm_alarm_seconds=comm_alarm)


# -- identity is the customer's, not ours ------------------------------------

def test_a_station_carries_the_customers_machine_number():
    _, eq = build()
    eq.set_machine_number("GRV1_LD", "2A01")
    mc = eq.machine_number("GRV1_LD")
    assert str(mc) == "2A01"
    assert mc.polarity.name == "CATHODE"      # 2 = cathode, not alphabetical


def test_the_station_map_is_ours_beside_theirs():
    """This IS the specification's station_map record."""
    _, eq = build()
    eq.set_machine_number("GRV1_LD", "2A01")
    eq.set_machine_number("CTR1_LD", "2T01")
    assert eq.station_map() == {"GRV1_LD": "2A01", "CTR1_LD": "2T01"}


# -- presence: three booleans, and the combination that means nothing --------

def test_presence_reports_what_is_physically_there():
    _, eq = build()
    eq.set_presence("GRV1_LD", rolling_full=True)
    assert eq.presence("GRV1_LD") is MaterialPresence.FULL_ROLL
    eq.set_presence("GRV1_LD", roll_in=True)
    assert eq.presence("GRV1_LD") is MaterialPresence.EMPTY_BOBBIN
    eq.set_presence("GRV1_LD", roll_null=True)
    assert eq.presence("GRV1_LD") is MaterialPresence.NOTHING


def test_a_machine_can_assert_a_combination_that_means_nothing():
    """Mid-transition. It must be visible, not rounded to something sensible."""
    _, eq = build()
    eq.set_presence("GRV1_LD", rolling_full=True, roll_in=True)
    assert eq.presence("GRV1_LD") is MaterialPresence.INCONSISTENT


# -- a request that is withdrawn before anyone looks -------------------------

def test_a_request_held_briefly_is_seen_by_a_fast_enough_poll():
    clock, eq = build()
    eq.raise_call_for("GRV1_LD", seconds=1.0)
    clock.advance(0.5)
    assert [c.station_id for c in eq.poll_calls()] == ["GRV1_LD"]


def test_a_withdrawn_request_is_gone_when_we_next_look():
    """A request that goes away for a reason OTHER than being served.

    ⚠ Corrected 2026-08-18. This used to claim it was what an ordinary
    unanswered call does. It is not: the machine stops calling when it sees
    `AGV_Task_Recive = 1`, our acknowledgement, and not on a timer — so a slow
    poll costs latency, not the request.

    What this models is an operator cancelling at the panel, or a machine
    alarming out. Then the request really is gone, and a CSM that had not yet
    acknowledged it simply never sees it — which is correct behaviour, not a
    fault.
    """
    clock, eq = build()
    eq.raise_call_for("GRV1_LD", seconds=1.0)
    clock.advance(1.5)                       # polled too late
    assert eq.poll_calls() == [], "the request should be gone, silently"


def test_an_ordinary_call_is_not_withdrawn():
    """Only a held call expires; the normal path must be unaffected."""
    clock, eq = build()
    eq.raise_call("GRV1_LD", TaskType.LOAD)
    clock.advance(600.0)
    assert [c.station_id for c in eq.poll_calls()] == ["GRV1_LD"]


# -- there is no acknowledgement ---------------------------------------------

def test_a_command_can_be_accepted_and_ignored():
    """send_station_command() -> True says the SEND happened, nothing more.

    The interface is shared memory, not a transaction. A CSM that treats the
    return value as proof of effect is trusting something the wire cannot tell
    it. debt-034.
    """
    _, eq = build()
    eq.swallow_next_command("GRV1_LD")
    assert eq.send_station_command("GRV1_LD", "load") is True, \
        "the protocol has no way to say no"
    assert eq.commands[-1] == ("GRV1_LD", "load", "swallowed")


def test_only_the_next_command_is_swallowed():
    _, eq = build()
    eq.swallow_next_command("GRV1_LD")
    eq.send_station_command("GRV1_LD", "first")
    eq.send_station_command("GRV1_LD", "second")
    assert eq.commands[-1][2] != "swallowed"


# -- the door: permission is a duration, and silence is not consent ----------

def test_entry_needs_permission_held_continuously():
    clock, eq = build(comm_alarm=2.0)
    eq.set_enter_permitted("GRV1_LD", True)
    for _ in range(3):
        hs = eq.observe("GRV1_LD")
        clock.advance(1.0)
    assert eq.observe("GRV1_LD").may_enter


def test_withdrawing_permission_mid_dock_stops_the_robot():
    """The case a boolean check cannot express."""
    clock, eq = build(comm_alarm=2.0)
    eq.set_enter_permitted("GRV1_LD", True)
    for _ in range(4):
        eq.observe("GRV1_LD")
        clock.advance(1.0)
    assert eq.observe("GRV1_LD").may_enter

    eq.set_enter_permitted("GRV1_LD", False)          # withdrawn
    assert not eq.observe("GRV1_LD").may_enter

    eq.set_enter_permitted("GRV1_LD", True)           # back at once
    assert not eq.observe("GRV1_LD").may_enter, \
        "the clock restarts; banked time does not survive the gap"


def test_a_stopped_heartbeat_withdraws_permission():
    """MC_Enter_Permitted condition 6: comms not normal, the AGV stops."""
    clock, eq = build(comm_alarm=2.0)
    eq.set_enter_permitted("GRV1_LD", True)
    for _ in range(4):
        eq.observe("GRV1_LD")
        clock.advance(1.0)
    assert eq.observe("GRV1_LD").may_enter

    eq.stop_heartbeat("GRV1_LD")
    clock.advance(3.0)
    assert not eq.observe("GRV1_LD").may_enter


def test_the_bay_stays_occupied_when_the_robot_goes_quiet():
    """Silence means "assume the robot is still inside", never "it left"."""
    clock, eq = build(comm_alarm=2.0)
    eq.observe("GRV1_LD", agv_entering=True)
    assert not eq.observe("GRV1_LD", agv_entering=True).may_machine_move

    clock.advance(0.5)                       # signal lost, briefly
    assert not eq.observe("GRV1_LD", agv_entering=False).may_machine_move

    clock.advance(3.0)                       # prolonged silence
    assert eq.observe("GRV1_LD", agv_entering=False).may_machine_move


# -- the nine status codes ---------------------------------------------------

@pytest.mark.parametrize("code", list(TaskProcessing))
def test_any_of_the_nine_codes_can_be_reported(code):
    _, eq = build()
    eq.set_task_processing("GRV1_LD", code)
    assert eq.task_processing("GRV1_LD") is code


def test_code_four_is_the_one_that_should_divert_to_a_rack():
    _, eq = build()
    eq.set_task_processing("GRV1_LD", TaskProcessing.BUFFER_FULL)
    assert eq.task_processing("GRV1_LD").value == 4


# -- it is still an ordinary machine when not provoked -----------------------

def test_it_behaves_like_the_plain_mock_by_default():
    _, eq = build()
    assert eq.get_station_status("GRV1_LD") is StationStatus.IDLE
    eq.raise_call("GRV1_LD", TaskType.LOAD)
    assert len(eq.poll_calls()) == 1
