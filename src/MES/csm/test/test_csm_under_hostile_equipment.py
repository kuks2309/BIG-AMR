"""What happens to the CSM when the equipment behaves as it really can.

The tests in test_opcua_equipment.py prove the STAND-IN can misbehave. These
point the actual CSM at it and ask whether the work survives.

Two of them are expected to fail. That is deliberate: they are the exposures
`debt-033` and `debt-034` describe, made reproducible instead of theoretical.
When either is fixed its test starts passing and pytest reports XPASS, which is
the signal to close the debt item.
"""

import asyncio

import pytest

from csm.adapters.base import StationStatus, TaskType
from csm.adapters.mock import ManualClock, MockAcs, OpcUaEquipment
from csm.runtime.job_store import JobStore
from csm.runtime.tasks import EquipmentMonitorTask

FEEDS = {"GRV1_LD": "ASRS"}


def build(poll_period=1.0):
    clock = ManualClock()
    equipment = OpcUaEquipment(["ASRS", "GRV1_LD"], clock)
    equipment.mark_store("ASRS")
    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True)
    monitor = EquipmentMonitorTask(store, source_for=lambda s: FEEDS.get(s, "ASRS"))
    return clock, equipment, store, monitor


def step(task):
    asyncio.run(task.step())


# -- the ordinary path still works ------------------------------------------

def test_a_request_the_csm_sees_in_time_becomes_a_job():
    clock, equipment, store, monitor = build()
    equipment.raise_call_for("GRV1_LD", seconds=2.0)
    clock.advance(0.5)
    step(monitor)
    assert len(store.active) == 1
    assert store.active[0].job.to_station == "GRV1_LD"


def test_the_call_is_acknowledged_only_once_it_is_a_job():
    clock, equipment, store, monitor = build()
    equipment.raise_call_for("GRV1_LD", seconds=2.0)
    clock.advance(0.5)
    step(monitor)
    assert equipment.acknowledged, "the machine may stop asking now, and only now"


# -- the exposures ----------------------------------------------------------

@pytest.mark.xfail(reason="debt-033: the poll interval is unjustified and the "
                          "equipment's minimum hold time is unknown. A request "
                          "shorter than the poll period is lost with no error.",
                   strict=False)
def test_a_request_shorter_than_the_poll_period_is_not_lost():
    """The machine believes it was heard. Nobody comes. Nothing errors.

    This is the failure that has no symptom: no exception, no error code, no
    log line — just a machine waiting for a robot that was never dispatched.

    The fix is not a faster poll. It is either a push path (OPC-UA
    subscriptions) or a minimum hold time from the equipment vendor that the
    poll period can be derived from. Until one of those exists, this fails.
    """
    clock, equipment, store, monitor = build()
    equipment.raise_call_for("GRV1_LD", seconds=0.5)
    clock.advance(1.0)                      # one poll period, as configured
    step(monitor)
    assert len(store.active) == 1, "the request was dropped in silence"


def test_a_command_that_was_ignored_is_noticed():
    """debt-034, now CLOSED for the paths that use send_and_confirm.

    This was xfail: the CSM had no way to tell a command that worked from one
    that did not, because the protocol cannot say no. It is confirmed by
    reading the machine's state back instead — see test_command_readback.py.

    What is closed is the mechanism and the two notifications in job_fsm's Done
    state. An adapter that cannot report presence still cannot confirm anything,
    and says UNVERIFIABLE rather than pretending.
    """
    clock, equipment, store, monitor = build()
    equipment.set_presence("GRV1_LD", roll_null=True)

    equipment.swallow_next_command("GRV1_LD")
    pending = equipment.send_and_confirm("GRV1_LD", "delivered", clock())
    assert pending.state.value == "pending", "the send itself looked fine"

    clock.advance(equipment.COMMAND_TIMEOUT_S)
    step(monitor)

    assert monitor.commands_lost == 1, \
        "a command accepted and ignored must not look like success"


# -- what the CSM does do correctly today -----------------------------------

def test_an_unservable_request_is_kept_rather_than_acknowledged():
    """Not acknowledging is what makes the machine ask again.

    This is the behaviour that saves the system from the exposure above: as
    long as the machine keeps asking, a missed poll is recoverable.
    """
    clock, equipment, store, monitor = build()
    equipment.force_status("ASRS", StationStatus.IDLE)   # nothing to give
    equipment.raise_call("GRV1_LD", TaskType.LOAD)
    step(monitor)
    assert not store.active
    assert not equipment.acknowledged, "silence would strand the request"
    assert equipment.poll_calls(), "and the machine is still asking"
