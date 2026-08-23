"""위치 관리 — location management, the customer's CSM scope slide, item ②.

"자재 · 랙 위치 실시간 추적 및 재고 동기화 · 자재 이동 이력관리 · LOT 추적
(LOT 생성은 yyyymmddhhmmssfff 로 관리 한다) · Data Traceability · 자재 숙성 및
투입 시점 관리 · FIFO / FEFO"

Two of those are blocked on the customer and say so out loud rather than
guessing: who owns curing time, and where expiry dates come from.
"""

from datetime import datetime

import pytest

from csm.records import InMemoryRecords, Material, lot_id_for


def fixed_clock(*moments):
    """A wall clock that returns each moment in turn, then repeats the last."""
    seq = list(moments)

    def clock():
        return seq.pop(0) if len(seq) > 1 else seq[0]
    return clock


# -- LOT ids: the customer's format, exactly ---------------------------------

def test_a_lot_id_is_the_customers_format():
    """yyyymmddhhmmssfff — 17 characters, to the millisecond."""
    moment = datetime(2026, 8, 18, 14, 30, 5, 123456)
    assert lot_id_for(moment) == "20260818143005123"
    assert len(lot_id_for(moment)) == 17


def test_the_id_is_all_digits():
    """It goes into their systems; no separators, no letters."""
    assert lot_id_for(datetime(2026, 1, 2, 3, 4, 5, 6000)).isdigit()


def test_registering_a_material_gives_it_a_lot_id():
    r = InMemoryRecords(wall_clock=fixed_clock(datetime(2026, 8, 18, 9, 0, 0)))
    material = r.register_material(kind="roll", at=10.0)
    assert material.lot_id == "20260818090000000"
    assert material.kind == "roll"


def test_two_materials_in_the_same_millisecond_do_not_collide():
    """The format has NO counter, so a duplicate is otherwise possible.

    A LOT id is how the customer's systems will refer to this material, so a
    duplicate is worse than an id a millisecond late.
    """
    moment = datetime(2026, 8, 18, 9, 0, 0)
    r = InMemoryRecords(wall_clock=lambda: moment)
    ids = {r.register_material().lot_id for _ in range(5)}
    assert len(ids) == 5, ids


# -- where things are --------------------------------------------------------

def test_a_material_knows_where_it_is():
    r = InMemoryRecords()
    m = r.register_material(at=1.0, location="ASRS")
    assert r.locate(m.material_ref) == "ASRS"


def test_moving_it_updates_where_it_is():
    r = InMemoryRecords()
    m = r.register_material(at=1.0, location="ASRS")
    r.move_material(m.material_ref, "GRV1_LD", at=5.0, job_id="job_0001")
    assert r.locate(m.material_ref) == "GRV1_LD"


def test_an_unknown_material_has_no_location_rather_than_a_guess():
    assert InMemoryRecords().locate("nope") is None


def test_what_is_at_a_place_can_be_asked():
    r = InMemoryRecords()
    r.register_material(at=1.0, location="WIP_GRV_1")
    r.register_material(at=2.0, location="WIP_GRV_1")
    r.register_material(at=3.0, location="ASRS")
    assert len(r.materials_at("WIP_GRV_1")) == 2


# -- traceability: where has this roll BEEN ----------------------------------

def test_every_movement_is_kept_in_order():
    """job_history says what a JOB did. This says what a MATERIAL did.

    They are different questions: a roll outlives the jobs that carried it, so
    "where has this been" cannot be answered from job records.
    """
    r = InMemoryRecords()
    m = r.register_material(at=1.0, location="ASRS")
    r.move_material(m.material_ref, "WIP_GRV_1", at=5.0, job_id="job_0001")
    r.move_material(m.material_ref, "GRV1_LD", at=9.0, job_id="job_0002")

    history = r.history_of(m.material_ref)
    assert [h.seq for h in history] == [1, 2, 3]
    assert [h.to_location for h in history] == ["ASRS", "WIP_GRV_1", "GRV1_LD"]
    assert [h.from_location for h in history] == [None, "ASRS", "WIP_GRV_1"]


def test_a_movement_records_which_job_carried_it():
    r = InMemoryRecords()
    m = r.register_material(at=1.0, location="ASRS")
    r.move_material(m.material_ref, "GRV1_LD", at=5.0, job_id="job_0042")
    assert r.history_of(m.material_ref)[-1].job_id == "job_0042"


# -- FIFO --------------------------------------------------------------------

def test_the_oldest_material_is_offered_first():
    r = InMemoryRecords()
    old = r.register_material(at=1.0, location="WIP_GRV_1")
    new = r.register_material(at=9.0, location="WIP_GRV_1")
    order = [m.material_ref for m in r.ready_materials("WIP_GRV_1", now=10.0)]
    assert order == [old.material_ref, new.material_ref]


# -- FEFO --------------------------------------------------------------------

def test_the_soonest_to_expire_goes_first():
    r = InMemoryRecords()
    late = r.register_material(at=1.0, location="WIP_GRV_1")
    soon = r.register_material(at=2.0, location="WIP_GRV_1")
    late.expires_at, soon.expires_at = 500.0, 100.0
    order = [m.material_ref for m in r.expiring_first("WIP_GRV_1", now=10.0)]
    assert order == [soon.material_ref, late.material_ref]


def test_material_with_no_expiry_sorts_last_not_first():
    """Nothing tells us expiries today, so this degrades to FIFO — and should.

    Sorting unknown-expiry first would invent an order out of missing data.
    """
    r = InMemoryRecords()
    unknown = r.register_material(at=1.0, location="WIP_GRV_1")
    dated = r.register_material(at=2.0, location="WIP_GRV_1")
    dated.expires_at = 100.0
    order = [m.material_ref for m in r.expiring_first("WIP_GRV_1", now=10.0)]
    assert order == [dated.material_ref, unknown.material_ref]


# -- resting / 숙성, and being honest about not knowing -----------------------

def test_material_that_has_not_finished_resting_is_not_offered():
    r = InMemoryRecords()
    m = r.register_material(at=1.0, location="WIP_GRV_1")
    r.set_ready_at(m.material_ref, when=100.0)
    assert not r.is_ready(m.material_ref, now=50.0)
    assert r.ready_materials("WIP_GRV_1", now=50.0) == []


def test_it_is_offered_once_it_has_rested():
    r = InMemoryRecords()
    m = r.register_material(at=1.0, location="WIP_GRV_1")
    r.set_ready_at(m.material_ref, when=100.0)
    assert r.is_ready(m.material_ref, now=100.0)


def test_unknown_resting_counts_as_ready_and_is_COUNTED():
    """The decision, and the reason it is visible.

    The specification selects material that "has finished resting" while
    section 7 says resting state is not retained. Until the customer says who
    owns it, we cannot apply the rule — so we accept, because a stopped line is
    the louder failure, and we COUNT how often we did it blind so the exposure
    is measurable rather than assumed.
    """
    r = InMemoryRecords()
    m = r.register_material(at=1.0, location="WIP_GRV_1")
    assert r.unrested_decisions == 0
    assert r.is_ready(m.material_ref, now=5.0)
    assert r.unrested_decisions == 1


def test_knowing_the_resting_time_does_not_count_as_blind():
    r = InMemoryRecords()
    m = r.register_material(at=1.0, location="WIP_GRV_1")
    r.set_ready_at(m.material_ref, when=10.0)
    r.is_ready(m.material_ref, now=20.0)
    assert r.unrested_decisions == 0


# -- what is deliberately not kept -------------------------------------------

def test_a_material_record_does_not_copy_the_customers_master_data():
    """Section 7: keep the identifier, read the rest."""
    fields = set(Material.__dataclass_fields__)
    for owned_elsewhere in ("width", "weight", "grade", "coating", "thickness",
                            "supplier", "part_number"):
        assert owned_elsewhere not in fields


# -- as the CSM actually writes it -------------------------------------------

import asyncio                                                    # noqa: E402

from csm.adapters.base import StationStatus                       # noqa: E402
from csm.adapters.mock import (ManualClock, MockAcs,              # noqa: E402
                               MockEquipment)
from csm.runtime.job_store import JobStore                        # noqa: E402
from csm.runtime.tasks import EquipmentMonitorTask                # noqa: E402
from csm import plant                                             # noqa: E402


def diverting_line():
    """A segment whose destinations are all full, so material must be parked."""
    clock = ManualClock()
    segment = plant.SEGMENTS[0]
    rack = segment["buffer"][0]
    stations = ["ASRS"] + list(segment["to"]) + list(segment["buffer"])
    equipment = MockEquipment(stations, clock)
    equipment.mark_store("ASRS")
    equipment.force_status("ASRS", StationStatus.FINISHED)
    for destination in segment["to"]:
        equipment.force_status(destination, StationStatus.BUSY)

    records = InMemoryRecords({b: 2 for b in segment["buffer"]},
                              wall_clock=lambda: datetime(2026, 8, 18, 12, 0, 0))
    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True, records=records)
    monitor = EquipmentMonitorTask(store, source_for=lambda s: "ASRS")
    monitor.divert_for = [segment]
    return clock, store, monitor, rack


def test_diverted_material_is_given_a_lot_id():
    clock, store, monitor, rack = diverting_line()
    asyncio.run(monitor.step())

    job = store.active[0].job
    assert job.material_ref, "the job must know what it is moving"
    material = store.records.material(job.material_ref)
    assert material.lot_id == job.material_ref
    assert len(material.lot_id) == 17


def test_the_rack_slot_holds_the_lot_id_not_the_job_id():
    """The rack is where identity lives — so it must hold the MATERIAL's."""
    clock, store, monitor, rack = diverting_line()
    asyncio.run(monitor.step())

    job = store.active[0].job
    occupied = [s for s in store.records.slots(rack) if s.occupied]
    assert occupied[0].material_ref == job.material_ref
    assert occupied[0].parked_by_job == job.job_id


def test_a_completed_job_moves_its_material():
    clock, store, monitor, rack = diverting_line()
    asyncio.run(monitor.step())
    record = store.active[0]
    job = record.job

    assert store.records.locate(job.material_ref) == "ASRS"
    record.fsm.force("DONE") if hasattr(record.fsm, "force") else None
    store._on_change(record.ctx, _ToDone())
    assert store.records.locate(job.material_ref) == rack


def test_a_failed_job_moves_nothing():
    """Recording a movement that did not happen is worse than recording none."""
    clock, store, monitor, rack = diverting_line()
    asyncio.run(monitor.step())
    record = store.active[0]
    job = record.job

    store._on_change(record.ctx, _ToFailed())
    assert store.records.locate(job.material_ref) == "ASRS"
    assert len(store.records.history_of(job.material_ref)) == 1


class _Target:
    def __init__(self, name):
        self.name = name


class _ToDone:
    name = "t3"
    target = _Target("DONE")


class _ToFailed:
    name = "t4"
    target = _Target("FAILED")
