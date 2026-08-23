"""The nine AGV_Task_Processing codes, and what the CSM does about them.

`TransportResult` collapses codes 2-7 into one BUSY. All six really are
retryable, so that is not wrong — but it throws away WHY, and one of them is
not merely retryable: code 4 is the customer's own instruction to divert to a
WIP rack, which the specification has three whole job types for.
"""

import asyncio

import pytest

from csm.adapters.base import (ProcessingOutcome, StationStatus, TaskProcessing,
                               TaskType, TransportResult,
                               interpret_task_processing)
from csm.adapters.mock import ManualClock, MockAcs, OpcUaEquipment
from csm.runtime.job_store import JobStore
from csm.runtime.tasks import EquipmentMonitorTask
from csm import plant


# -- the mapping -------------------------------------------------------------

def test_success_ends_the_job_well():
    assert interpret_task_processing(1).result is TransportResult.ARRIVED


@pytest.mark.parametrize("code", [2, 3, 5, 6, 7])
def test_the_delaying_codes_are_retryable(code):
    """Material or traffic states that can change without intervention."""
    out = interpret_task_processing(code)
    assert out.result is TransportResult.BUSY
    assert not out.divert_to_buffer


@pytest.mark.parametrize("code", [8, 9])
def test_a_fault_or_a_cancellation_ends_the_job(code):
    """These do not resolve by waiting. 8 is the robot, not the job."""
    assert interpret_task_processing(code).result is TransportResult.FAILED


def test_code_four_is_the_only_one_that_asks_for_a_divert():
    out = interpret_task_processing(TaskProcessing.BUFFER_FULL)
    assert out.divert_to_buffer
    assert out.result is TransportResult.BUSY, "the job waits, it does not fail"
    for code in (1, 2, 3, 5, 6, 7, 8, 9):
        assert not interpret_task_processing(code).divert_to_buffer, code


def test_every_code_is_accounted_for():
    """No code falls through to a default nobody chose."""
    for code in TaskProcessing:
        assert isinstance(interpret_task_processing(code), ProcessingOutcome)


def test_an_unknown_code_is_refused_rather_than_guessed():
    with pytest.raises(ValueError):
        interpret_task_processing(42)


# -- code 4 beats our own inference ------------------------------------------

def build():
    clock = ManualClock()
    eq = OpcUaEquipment(["ASRS", "GRV1_LD"], clock)
    return clock, eq


def test_a_port_reporting_buffer_full_cannot_accept():
    """Even while our own status reading says it is idle."""
    _, eq = build()
    assert eq.get_station_status("GRV1_LD") is StationStatus.IDLE
    assert eq.can_accept("GRV1_LD")

    eq.set_task_processing("GRV1_LD", TaskProcessing.BUFFER_FULL)
    assert eq.buffer_full("GRV1_LD")
    assert not eq.can_accept("GRV1_LD"), \
        "the equipment was there; our status reading was not"


def test_a_warehouse_reporting_buffer_full_cannot_accept_either():
    """"A store always has room" is our assumption, not a measurement."""
    _, eq = build()
    eq.mark_store("ASRS")
    assert eq.can_accept("ASRS")

    eq.set_task_processing("ASRS", TaskProcessing.BUFFER_FULL)
    assert not eq.can_accept("ASRS")


@pytest.mark.parametrize("code", [1, 2, 3, 5, 6, 7, 8, 9])
def test_no_other_code_closes_a_port(code):
    """Only code 4 means "no empty slot". The rest must not block delivery."""
    _, eq = build()
    eq.set_task_processing("GRV1_LD", code)
    assert eq.can_accept("GRV1_LD"), code


# -- and the divert actually fires -------------------------------------------

def test_the_csm_diverts_when_the_equipment_says_the_buffer_is_full():
    """End to end: the customer's signal produces the specification's job.

    Jobs 4, 8 and 12 exist for this condition. Until now the CSM inferred it
    from station status; now it can be told.
    """
    clock = ManualClock()
    segment = plant.SEGMENTS[0]                      # A: ASRS -> gravure LDs
    stations = ["ASRS"] + list(segment["to"]) + list(segment["buffer"])
    eq = OpcUaEquipment(stations, clock)
    eq.mark_store("ASRS")
    eq.force_status("ASRS", StationStatus.FINISHED)  # something to move

    store = JobStore(eq, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True)
    monitor = EquipmentMonitorTask(store, source_for=lambda s: "ASRS")
    monitor.divert_for = [segment]

    # Every gravure LD says it has no empty slot.
    for destination in segment["to"]:
        eq.set_task_processing(destination, TaskProcessing.BUFFER_FULL)

    asyncio.run(monitor.step())

    assert monitor.diverted == 1, "material should have been parked on a rack"
    job = store.active[0].job
    assert job.from_station == "ASRS"
    assert job.to_station in segment["buffer"]


def test_no_divert_while_one_destination_can_still_take_it():
    """The divert is a last resort, not a preference."""
    clock = ManualClock()
    segment = plant.SEGMENTS[0]
    stations = ["ASRS"] + list(segment["to"]) + list(segment["buffer"])
    eq = OpcUaEquipment(stations, clock)
    eq.mark_store("ASRS")
    eq.force_status("ASRS", StationStatus.FINISHED)

    store = JobStore(eq, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True)
    monitor = EquipmentMonitorTask(store, source_for=lambda s: "ASRS")
    monitor.divert_for = [segment]

    for destination in list(segment["to"])[1:]:      # all but one
        eq.set_task_processing(destination, TaskProcessing.BUFFER_FULL)

    asyncio.run(monitor.step())
    assert monitor.diverted == 0
