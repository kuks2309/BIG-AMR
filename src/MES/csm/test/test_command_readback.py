"""A command is not done because the send returned True.

The equipment link is shared memory, not a transaction. There is no
acknowledgement, so `send_station_command()` returning True says a value was
written and nothing about whether the machine acted on it. The only evidence
available is the machine's own state afterwards. debt-034.
"""

import asyncio

import pytest

from csm.adapters.base import (CommandConfirmation, ConfirmState,
                               MaterialPresence, StationStatus)
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment, OpcUaEquipment
from csm.runtime.job_store import JobStore
from csm.runtime.tasks import EquipmentMonitorTask


def build():
    clock = ManualClock()
    equipment = OpcUaEquipment(["GRV1_LD", "ASRS"], clock)
    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True)
    monitor = EquipmentMonitorTask(store, source_for=lambda s: "ASRS")
    return clock, equipment, store, monitor


def step(task):
    asyncio.run(task.step())


# -- the confirmation itself -------------------------------------------------

def test_a_command_stays_pending_until_the_state_changes():
    c = CommandConfirmation("GRV1_LD", "delivered",
                            frozenset({MaterialPresence.FULL_ROLL}),
                            sent_at=0.0, timeout=5.0)
    assert c.poll(MaterialPresence.NOTHING, 1.0) is ConfirmState.PENDING


def test_it_confirms_when_the_machine_shows_the_effect():
    c = CommandConfirmation("GRV1_LD", "delivered",
                            frozenset({MaterialPresence.FULL_ROLL}),
                            sent_at=0.0, timeout=5.0)
    assert c.poll(MaterialPresence.FULL_ROLL, 1.0) is ConfirmState.CONFIRMED


def test_it_is_lost_when_the_effect_never_appears():
    c = CommandConfirmation("GRV1_LD", "delivered",
                            frozenset({MaterialPresence.FULL_ROLL}),
                            sent_at=0.0, timeout=5.0)
    assert c.poll(MaterialPresence.NOTHING, 4.9) is ConfirmState.PENDING
    assert c.poll(MaterialPresence.NOTHING, 5.0) is ConfirmState.LOST


def test_an_adapter_that_cannot_report_presence_says_so():
    """UNVERIFIABLE, never CONFIRMED. Not knowing is not the same as success."""
    c = CommandConfirmation("GRV1_LD", "delivered",
                            frozenset({MaterialPresence.FULL_ROLL}),
                            sent_at=0.0, timeout=5.0)
    assert c.poll(None, 99.0) is ConfirmState.UNVERIFIABLE


def test_a_confirmed_command_does_not_later_become_lost():
    c = CommandConfirmation("GRV1_LD", "delivered",
                            frozenset({MaterialPresence.FULL_ROLL}),
                            sent_at=0.0, timeout=5.0)
    c.poll(MaterialPresence.FULL_ROLL, 1.0)
    assert c.poll(MaterialPresence.NOTHING, 100.0) is ConfirmState.CONFIRMED


# -- end to end: the swallowed command is caught -----------------------------

def test_a_swallowed_command_is_reported_as_lost():
    """The exposure debt-034 describes, now caught instead of believed."""
    clock, equipment, store, monitor = build()
    equipment.set_presence("GRV1_LD", roll_null=True)     # nothing there

    equipment.swallow_next_command("GRV1_LD")
    pending = equipment.send_and_confirm("GRV1_LD", "delivered", clock())
    assert pending.state is ConfirmState.PENDING, "the send looked fine"

    clock.advance(equipment.COMMAND_TIMEOUT_S)
    step(monitor)

    assert monitor.commands_lost == 1
    assert pending.state is ConfirmState.LOST


def test_a_command_that_worked_is_not_reported():
    clock, equipment, store, monitor = build()
    equipment.set_presence("GRV1_LD", roll_null=True)
    equipment.send_and_confirm("GRV1_LD", "delivered", clock())

    equipment.set_presence("GRV1_LD", rolling_full=True)  # the machine acted
    clock.advance(equipment.COMMAND_TIMEOUT_S)
    step(monitor)

    assert monitor.commands_lost == 0


def test_collected_is_confirmed_by_the_material_being_gone():
    """Either an empty machine or one holding the empty core."""
    clock, equipment, store, monitor = build()
    equipment.set_presence("GRV1_LD", rolling_full=True)
    equipment.send_and_confirm("GRV1_LD", "collected", clock())

    equipment.set_presence("GRV1_LD", roll_in=True)       # bobbin left behind
    clock.advance(equipment.COMMAND_TIMEOUT_S)
    step(monitor)
    assert monitor.commands_lost == 0


def test_an_adapter_without_presence_never_reports_a_false_loss():
    """MockEquipment cannot read back, so it must not accuse anyone."""
    clock = ManualClock()
    equipment = MockEquipment(["GRV1_LD"], clock)
    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True)
    monitor = EquipmentMonitorTask(store, source_for=lambda s: "GRV1_LD")

    equipment.send_and_confirm("GRV1_LD", "delivered", clock())
    clock.advance(60.0)
    step(monitor)
    assert monitor.commands_lost == 0


def test_the_loss_is_logged_where_a_person_will_see_it():
    clock = ManualClock()
    equipment = OpcUaEquipment(["GRV1_LD"], clock)
    logged = []
    store = JobStore(equipment, MockAcs(clock), clock, logger=logged.append,
                     dispatch_gated=True)
    monitor = EquipmentMonitorTask(store, source_for=lambda s: "GRV1_LD")

    equipment.set_presence("GRV1_LD", roll_null=True)
    equipment.swallow_next_command("GRV1_LD")
    equipment.send_and_confirm("GRV1_LD", "delivered", clock())
    clock.advance(equipment.COMMAND_TIMEOUT_S)
    step(monitor)

    assert any("never took effect" in m for m in logged), logged
