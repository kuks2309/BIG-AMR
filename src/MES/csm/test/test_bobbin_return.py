"""The bobbin returns — specification jobs 3, 7 and 11.

Every hop in this plant is an EXCHANGE: a roll goes forward, an empty core
comes back. Until now only the forward half existed, so the line would run out
of empty cores and nothing would say why.
"""

import asyncio

import pytest

from csm import plant
from csm.adapters.base import StationStatus, TaskType
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment
from csm.job import Carried
from csm.runtime.job_store import JobStore
from csm.runtime.tasks import EquipmentMonitorTask


# -- the route rule, straight from assumption A5 -----------------------------

@pytest.mark.parametrize("station,expected", [
    ("GRV1_LD", "ASRS"),        # leg A -> back to the store
    ("GRV4_LD", "ASRS"),
    ("CTR1_LD", "GRV1_ULD"),    # leg B -> one process upstream
    ("CTR3_LD", "GRV3_ULD"),
    ("SLT_LD1", "CTR1_ULD"),    # leg C -> one process upstream
    ("SLT_LD4", "CTR4_ULD"),
])
def test_a5_return_destinations(station, expected):
    assert plant.bobbin_return_for(station) == expected


@pytest.mark.parametrize("station", ["ASRS", "WIP_GRV_1", "WIP_CTR_1",
                                     "WIP_SLT_1", "GRV1_ULD"])
def test_stations_that_hand_no_bobbin_back(station):
    """The store and the racks are not machines; they consume nothing."""
    assert plant.bobbin_return_for(station) is None


def test_the_return_pairs_with_the_same_instance():
    """CTR3 gets its roll from GRV3, so its bobbin goes back to GRV3.

    Returning to whichever gravure happened to be first would slowly shuffle
    every bobbin onto one machine.
    """
    for i in (1, 2, 3, 4):
        assert plant.bobbin_return_for(f"CTR{i}_LD") == f"GRV{i}_ULD"


def test_is_bobbin_return_recognises_direction():
    assert plant.is_bobbin_return("CTR2_LD", "GRV2_ULD")
    assert not plant.is_bobbin_return("GRV2_ULD", "CTR2_LD")


# -- an UNLOAD call raises a return job, not a material job ------------------

def build(stations, returns=True):
    clock = ManualClock()
    equipment = MockEquipment(stations, clock)
    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True)
    monitor = EquipmentMonitorTask(store, source_for=lambda s: "ASRS")
    if returns:
        monitor.return_for = plant.bobbin_return_for
    return equipment, store, monitor


def step(task):
    asyncio.run(task.step())


def test_an_unload_call_creates_a_bobbin_job_going_upstream():
    equipment, store, monitor = build(["CTR1_LD", "GRV1_ULD"])
    equipment.raise_call("CTR1_LD", TaskType.UNLOAD)
    step(monitor)

    jobs = [r.job for r in store.active]
    assert len(jobs) == 1
    job = jobs[0]
    assert job.from_station == "CTR1_LD", "the caller is the SOURCE, not the destination"
    assert job.to_station == "GRV1_ULD"
    assert job.carries is Carried.BOBBIN


def test_a_load_call_still_brings_material_the_other_way():
    """The inversion must not leak into the normal path."""
    equipment, store, monitor = build(["GRV1_LD", "ASRS"])
    equipment.force_status("ASRS", StationStatus.FINISHED)
    equipment.raise_call("GRV1_LD", TaskType.LOAD)
    step(monitor)

    job = store.active[0].job
    assert job.from_station == "ASRS"
    assert job.to_station == "GRV1_LD", "the caller is the DESTINATION here"
    assert job.carries is Carried.ROLL


def test_an_unheard_return_is_not_acknowledged():
    """A station with no return route must keep asking, not be silenced.

    Acknowledging tells the machine it was heard. Doing that and then not
    moving the bobbin is the silent failure this layer exists to prevent.
    """
    equipment, store, monitor = build(["ASRS"])
    equipment.raise_call("ASRS", TaskType.UNLOAD)
    step(monitor)

    assert not store.active, "no route, so no job"
    assert equipment.poll_calls(), "the call must still be outstanding"


def test_returns_are_counted_separately_from_material_jobs():
    """A line moving rolls and never returning cores is visible in the split."""
    equipment, store, monitor = build(["CTR1_LD", "GRV1_ULD"])
    equipment.raise_call("CTR1_LD", TaskType.UNLOAD)
    step(monitor)

    assert monitor.returned == 1
    assert monitor.created == 1


def test_bobbin_returns_stay_off_unless_asked_for():
    """Every existing caller must behave exactly as before.

    With no return_for injected an unload call falls through to the material
    path, which is what every caller written before this change expects.
    """
    equipment, store, monitor = build(["CTR1_LD", "GRV1_ULD"], returns=False)
    equipment.force_status("ASRS", StationStatus.FINISHED)
    equipment.raise_call("CTR1_LD", TaskType.UNLOAD)
    step(monitor)

    for record in store.active:
        assert record.job.carries is Carried.ROLL
    assert monitor.returned == 0


# -- the leg binding: a bobbin is the return half, not a different leg -------

@pytest.mark.parametrize("frm,to,leg", [
    ("ASRS", "GRV1_LD", "A"),        # roll forward
    ("GRV1_LD", "ASRS", "A"),        # bobbin back — same leg
    ("GRV1_ULD", "CTR1_LD", "B"),
    ("CTR1_LD", "GRV1_ULD", "B"),
    ("CTR1_ULD", "SLT_LD1", "C"),
    ("SLT_LD1", "CTR1_ULD", "C"),
])
def test_a_segment_matches_in_both_directions(frm, to, leg):
    """The specification puts both halves on the same AGV class.

    Jobs 1 and 3 are both LOWBIGA, 5 and 7 both LOWBIGB, 9 and 11 both HIGHBIG.
    Matching the forward direction only meant every bobbin return was rejected
    by the ACS for having no segment — five created, five failed, in the
    simulator.
    """
    assert plant.segment_for_job(frm, to)["name"] == leg


def test_unrelated_stations_still_match_nothing():
    """Bidirectional must not mean "anything goes"."""
    assert plant.segment_for_job("ASRS", "SLT_LD1") is None
    assert plant.segment_for_job("SLT_LD1", "ASRS") is None
