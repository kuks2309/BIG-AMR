"""The six records of specification section 7.

Deliberately small. The specification says why: "For anything the customer's
systems own we keep the identifier and read the rest — two copies of one fact
is how rack/inventory mismatches arise."
"""

import pytest

from csm.adapters.base import TaskType
from csm.records import (Call, CallStatus, Decision, InMemoryRecords, RackSlot,
                         instance_of)


# -- which of the four machines ---------------------------------------------

@pytest.mark.parametrize("station,expected", [
    ("GRV1_LD", 1),        # family, instance, port
    ("GRV4_ULD", 4),
    ("CTR3_LD", 3),
    ("SLT_LD1", 1),        # port, THEN instance — the names disagree
    ("SLT_LD4", 4),
    ("WIP_CTR_2", 2),
    ("WIP_GRV_1", 1),
])
def test_the_instance_is_found_wherever_the_name_puts_it(station, expected):
    """A positional rule would be right for one family and wrong for the rest."""
    assert instance_of(station) == expected


def test_a_station_with_no_instance_says_none():
    """There is one store. None is the honest answer, not 1."""
    assert instance_of("ASRS") is None
    assert instance_of("") is None
    assert instance_of(None) is None


def test_two_coaters_asking_produce_distinguishable_jobs():
    """Assumption A3: the job NAME is generic, the record carries the instance."""
    assert instance_of("CTR1_LD") != instance_of("CTR2_LD")


# -- calls -------------------------------------------------------------------

def test_a_call_is_recorded_with_its_instance():
    r = InMemoryRecords()
    call = r.add_call("GRV2_LD", TaskType.LOAD, "equipment", raised_at=10.0)
    assert call.station == "GRV2_LD"
    assert call.instance == 2
    assert call.status is CallStatus.RAISED
    assert call.acknowledged_at is None


def test_acknowledging_records_when_and_which_job():
    """The machine stops asking at this moment, so it is worth recording."""
    r = InMemoryRecords()
    call = r.add_call("GRV1_LD", TaskType.LOAD, "PDA", raised_at=10.0)
    r.acknowledge_call(call.call_id, at=12.0, job_id="job_0007")
    assert call.acknowledged_at == 12.0
    assert call.job_id == "job_0007"
    assert call.status is CallStatus.ACKNOWLEDGED


def test_open_calls_are_the_ones_not_yet_heard():
    r = InMemoryRecords()
    a = r.add_call("GRV1_LD", TaskType.LOAD, "equipment", 1.0)
    r.add_call("CTR1_LD", TaskType.LOAD, "equipment", 2.0)
    r.acknowledge_call(a.call_id, at=3.0)
    assert [c.station for c in r.open_calls()] == ["CTR1_LD"]


def test_a_pda_call_is_recorded_as_such():
    """The protocol treats them identically; the RECORD must not."""
    r = InMemoryRecords()
    assert r.add_call("GRV1_LD", TaskType.LOAD, "PDA", 1.0).source == "PDA"


# -- rack slots --------------------------------------------------------------

def test_a_rack_has_the_number_of_slots_it_was_given():
    """WIPGP 2, WIPCTR 13, WIPSLT 30 — real capacities, so slots are counted."""
    r = InMemoryRecords({"WIP_GRV": 2, "WIP_CTR": 13, "WIP_SLT": 30})
    assert len(r.slots("WIP_GRV")) == 2
    assert len(r.slots("WIP_SLT")) == 30


def test_parking_takes_the_first_free_slot():
    r = InMemoryRecords({"WIP_GRV": 2})
    slot = r.park("WIP_GRV", material_ref="ROLL-1", job_id="job_0001", at=5.0)
    assert slot.slot == 1
    assert slot.occupied
    assert slot.parked_by_job == "job_0001"


def test_a_full_rack_says_so_rather_than_overwriting():
    r = InMemoryRecords({"WIP_GRV": 2})
    r.park("WIP_GRV", "ROLL-1", "job_0001", 1.0)
    r.park("WIP_GRV", "ROLL-2", "job_0002", 2.0)
    assert r.is_full("WIP_GRV")
    assert r.park("WIP_GRV", "ROLL-3", "job_0003", 3.0) is None


def test_retrieval_takes_the_oldest_first():
    """FIFO falls out of the ordering rather than being a separate feature."""
    r = InMemoryRecords({"WIP_GRV": 2})
    r.park("WIP_GRV", "ROLL-old", "job_0001", at=1.0)
    r.park("WIP_GRV", "ROLL-new", "job_0002", at=9.0)
    taken = r.retrieve("WIP_GRV", at=10.0)
    assert taken.material_ref == "ROLL-old"


def test_a_retrieved_slot_becomes_free_again():
    r = InMemoryRecords({"WIP_GRV": 1})
    r.park("WIP_GRV", "ROLL-1", "job_0001", 1.0)
    assert r.is_full("WIP_GRV")
    r.retrieve("WIP_GRV", at=2.0)
    assert not r.is_full("WIP_GRV")
    assert r.park("WIP_GRV", "ROLL-2", "job_0002", 3.0) is not None


def test_a_specific_material_can_be_asked_for():
    r = InMemoryRecords({"WIP_GRV": 2})
    r.park("WIP_GRV", "ROLL-a", "job_0001", 1.0)
    r.park("WIP_GRV", "ROLL-b", "job_0002", 2.0)
    assert r.retrieve("WIP_GRV", at=3.0, material_ref="ROLL-b").slot == 2


def test_retrieving_from_an_empty_rack_returns_nothing():
    r = InMemoryRecords({"WIP_GRV": 2})
    assert r.retrieve("WIP_GRV", at=1.0) is None


def test_a_slot_holds_a_reference_not_a_copy_of_the_material():
    """The retention rule in one field: keep the id, read the rest."""
    fields = set(RackSlot.__dataclass_fields__)
    assert "material_ref" in fields
    for owned_elsewhere in ("weight", "width", "grade", "expiry", "lot"):
        assert owned_elsewhere not in fields


# -- decisions ---------------------------------------------------------------

def test_a_decision_records_why_not_only_what():
    r = InMemoryRecords()
    r.add_decision(Decision(job_id="job_0001", decided_at=5.0,
                            chosen_source="ASRS", chosen_dest="GRV1_LD",
                            reason="first eligible destination"))
    got = r.decisions_for("job_0001")
    assert len(got) == 1
    assert got[0].reason == "first eligible destination"


def test_decisions_are_kept_per_job_and_in_order():
    r = InMemoryRecords()
    r.add_decision(Decision("job_0001", 1.0, reason="first"))
    r.add_decision(Decision("job_0002", 2.0, reason="other job"))
    r.add_decision(Decision("job_0001", 3.0, reason="second"))
    assert [d.reason for d in r.decisions_for("job_0001")] == ["first", "second"]


# -- station map -------------------------------------------------------------

def test_our_name_is_bound_to_the_customers():
    """Theirs goes on the wire; ours is what the plant and roads are written in."""
    r = InMemoryRecords()
    entry = r.map_station("GRV1_LD", "2A01")
    assert entry.our_name == "GRV1_LD"
    assert entry.customer_port_id == "2A01"
    assert entry.instance == 1
    assert r.customer_id("GRV1_LD") == "2A01"


def test_an_unmapped_station_says_none_rather_than_guessing():
    assert InMemoryRecords().customer_id("GRV9_LD") is None


# -- what is deliberately NOT retained ---------------------------------------

def test_no_record_carries_what_another_system_owns():
    """Section 7: "two copies of one fact is how mismatches arise"."""
    forbidden = {"inventory", "battery", "position", "route", "master_data"}
    for record in (Call, RackSlot, Decision):
        for name in record.__dataclass_fields__:
            assert not any(f in name for f in forbidden), (record, name)


# -- the records as the CSM actually writes them -----------------------------

import asyncio                                                    # noqa: E402

from csm.adapters.base import StationStatus                       # noqa: E402
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment  # noqa: E402
from csm.runtime.job_store import JobStore                        # noqa: E402
from csm.runtime.tasks import EquipmentMonitorTask                # noqa: E402
from csm import plant                                             # noqa: E402


def wired(stations=("ASRS", "GRV1_LD"), racks=None):
    clock = ManualClock()
    equipment = MockEquipment(list(stations), clock)
    equipment.mark_store("ASRS")
    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True, records=InMemoryRecords(racks or {}))
    monitor = EquipmentMonitorTask(store, source_for=lambda s: "ASRS")
    return clock, equipment, store, monitor


def test_a_served_call_is_recorded_and_linked_to_its_job():
    clock, equipment, store, monitor = wired()
    equipment.raise_call("GRV1_LD", TaskType.LOAD, source="PDA")
    asyncio.run(monitor.step())

    calls = store.records.calls_for("GRV1_LD")
    assert len(calls) == 1
    call = calls[0]
    assert call.source == "PDA"
    assert call.instance == 1
    assert call.status is CallStatus.ACKNOWLEDGED
    assert call.job_id == store.active[0].job.job_id


def test_the_job_points_back_at_the_call_it_answers():
    clock, equipment, store, monitor = wired()
    equipment.raise_call("GRV1_LD", TaskType.LOAD)
    asyncio.run(monitor.step())

    job = store.active[0].job
    assert job.call_id is not None
    assert store.records.call(job.call_id).station == "GRV1_LD"


def test_the_job_carries_both_instance_numbers():
    """Assumption A3 — the name is generic, the record identifies the machine."""
    clock, equipment, store, monitor = wired(("ASRS", "GRV3_LD"))
    equipment.raise_call("GRV3_LD", TaskType.LOAD)
    asyncio.run(monitor.step())

    job = store.active[0].job
    assert job.to_instance == 3
    assert job.from_instance is None, "the ASRS has no instance"


def test_every_job_records_why_it_was_created():
    clock, equipment, store, monitor = wired()
    equipment.raise_call("GRV1_LD", TaskType.LOAD)
    asyncio.run(monitor.step())

    job_id = store.active[0].job.job_id
    decisions = store.records.decisions_for(job_id)
    assert len(decisions) == 1
    assert decisions[0].chosen_source == "ASRS"
    assert decisions[0].chosen_dest == "GRV1_LD"
    assert decisions[0].reason


def test_the_diversion_is_the_job_with_no_call():
    """CSM originates it, so there is no caller — and that identifies it."""
    clock = ManualClock()
    segment = plant.SEGMENTS[0]
    stations = ["ASRS"] + list(segment["to"]) + list(segment["buffer"])
    equipment = MockEquipment(stations, clock)
    equipment.mark_store("ASRS")
    equipment.force_status("ASRS", StationStatus.FINISHED)
    for destination in segment["to"]:
        equipment.force_status(destination, StationStatus.BUSY)

    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True,
                     records=InMemoryRecords({b: 2 for b in segment["buffer"]}))
    monitor = EquipmentMonitorTask(store, source_for=lambda s: "ASRS")
    monitor.divert_for = [segment]
    asyncio.run(monitor.step())

    assert monitor.diverted == 1
    job = store.active[0].job
    assert job.call_id is None, "a diversion answers no call"
    assert store.records.decisions_for(job.job_id)[0].reason


def test_a_diverted_roll_occupies_a_rack_slot():
    clock = ManualClock()
    segment = plant.SEGMENTS[0]
    rack = segment["buffer"][0]
    stations = ["ASRS"] + list(segment["to"]) + list(segment["buffer"])
    equipment = MockEquipment(stations, clock)
    equipment.mark_store("ASRS")
    equipment.force_status("ASRS", StationStatus.FINISHED)
    for destination in segment["to"]:
        equipment.force_status(destination, StationStatus.BUSY)

    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True,
                     records=InMemoryRecords({b: 2 for b in segment["buffer"]}))
    monitor = EquipmentMonitorTask(store, source_for=lambda s: "ASRS")
    monitor.divert_for = [segment]
    asyncio.run(monitor.step())

    occupied = [s for s in store.records.slots(rack) if s.occupied]
    assert len(occupied) == 1
    assert occupied[0].parked_by_job == store.active[0].job.job_id
