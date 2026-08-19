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


@pytest.mark.xfail(reason="debt-034: send_station_command() -> bool reports the "
                          "SEND, not the effect. The protocol is shared memory "
                          "and has no acknowledgement, so the CSM cannot yet "
                          "tell a command that worked from one that did not.",
                   strict=False)
def test_a_command_that_was_ignored_is_noticed():
    """Confirmation must come from reading the state back, not from the return.

    The real interface cannot say no. A CSM that believes the return value has
    believed something the wire never told it.
    """
    _, equipment, store, monitor = build()
    equipment.swallow_next_command("GRV1_LD")
    accepted = equipment.send_station_command("GRV1_LD", "load")

    # It said True. The state says otherwise, and only the state is evidence.
    assert accepted is True
    assert equipment.presence("GRV1_LD").name != "NOTHING", \
        "the CSM should have read back and seen the command did nothing"


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
