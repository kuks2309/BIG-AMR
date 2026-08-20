"""The PDA — the fourth responsibility on the customer's CSM scope slide.

The only one where a PERSON is the caller. These test the LOGIC a handheld
screen would call; the screens themselves are unscoped, which the handbook
records as "CSM has no UI in the specification and needs one".
"""

import asyncio

import pytest

from csm.adapters.base import StationStatus, TaskType
from csm.material import MaterialAttribute, pallet_capacity
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment
from csm.pda import Abnormal, Pda
from csm.records import InMemoryRecords
from csm.runtime.job_store import JobStore

STATIONS = ["ASRS", "GRV1_LD", "WIP_GRV_1"]


def build(position_codes=None):
    clock = ManualClock()
    equipment = MockEquipment(STATIONS, clock)
    equipment.mark_store("ASRS")
    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True,
                     records=InMemoryRecords({"WIP_GRV_1": 2}))
    return clock, store, Pda(store, position_codes=position_codes)


#: What a worker reads off the label. Inbound refuses material without it.
DESCRIBED = dict(attribute=MaterialAttribute.BRIGHT_CW, drum_type=430,
                 material_type=302)


def described(pda, **kwargs):
    """Scan and supplement in one go — the state inbound requires."""
    return pda.register_material(**{**DESCRIBED, **kwargs})


# -- D1  생산 정보 등록 -------------------------------------------------------

def test_scanning_material_gives_it_a_lot_id():
    """A worker scanning material is usually the first time we hear of it."""
    _, store, pda = build()
    material = pda.register_material(kind="roll", location="ASRS")
    assert len(material.lot_id) == 17
    assert store.records.locate(material.material_ref) == "ASRS"


def test_binding_supplemented_material_to_a_rack_occupies_a_slot():
    _, store, pda = build()
    material = described(pda, kind="roll")
    result = pda.bind_to_rack(material.material_ref, "WIP_GRV_1")
    assert result.ok
    assert result.slot.material_ref == material.material_ref
    assert store.records.locate(material.material_ref) == "WIP_GRV_1"


def test_a_full_rack_answers_rather_than_raising():
    """A full rack is an ordinary answer a worker needs to see."""
    _, store, pda = build()
    for _ in range(2):
        pda.bind_to_rack(described(pda).material_ref, "WIP_GRV_1")
    third = described(pda)
    result = pda.bind_to_rack(third.material_ref, "WIP_GRV_1")
    assert not result.ok
    assert "full" in result.reason


# -- D2  자재 위치 조회 -------------------------------------------------------

def test_looking_up_a_roll_gives_where_it_is_and_where_it_has_been():
    clock, store, pda = build()
    material = described(pda, location="ASRS")
    clock.advance(5.0)
    assert pda.bind_to_rack(material.material_ref, "WIP_GRV_1").ok

    found = pda.where_is(material.material_ref)
    assert found["location"] == "WIP_GRV_1"
    assert [h.to_location for h in found["history"]] == ["ASRS", "WIP_GRV_1"]


def test_an_unknown_roll_says_not_found_rather_than_guessing():
    """Material can exist on the floor without our knowing it."""
    _, _, pda = build()
    assert pda.where_is("20260818120000000") is None


# -- D3  작업 완료 확인 -------------------------------------------------------

def test_a_running_job_reports_as_unfinished():
    _, store, pda = build()
    job = store.create("ASRS", "GRV1_LD")
    status = pda.job_status(job.job.job_id)
    assert status["finished"] is False
    assert status["state"] == "IDLE"


def test_an_unknown_job_id_returns_nothing():
    _, _, pda = build()
    assert pda.job_status("job_9999") is None


# -- D4  비정상 상황 보고 -----------------------------------------------------

def test_a_worker_can_report_a_problem():
    clock, store, pda = build()
    report = pda.report_abnormal("GRV1_LD", "material jammed at the port")
    assert report.station == "GRV1_LD"
    assert report.open
    assert pda.open_reports() == [report]


def test_a_report_stays_open_until_acknowledged():
    """A report that is only logged is one nobody can chase or close."""
    clock, store, pda = build()
    report = pda.report_abnormal("GRV1_LD", "jam")
    clock.advance(30.0)
    pda.acknowledge_report(report.report_id)
    assert not report.open
    assert pda.open_reports() == []


def test_reports_are_kept_separately_so_they_can_be_counted():
    _, _, pda = build()
    pda.report_abnormal("GRV1_LD", "one")
    pda.report_abnormal("ASRS", "two")
    assert len(pda.open_reports()) == 2


# -- D5  AGV 수동 호출 및 취소 -------------------------------------------------

def test_a_manual_call_creates_a_point_to_point_job():
    """Both ends named by the worker, so CSM chooses nothing."""
    _, store, pda = build()
    job = pda.call_transport("ASRS", "GRV1_LD", equipment_no="1A01")
    assert job.job.from_station == "ASRS"
    assert job.job.to_station == "GRV1_LD"
    reason = store.records.decisions_for(job.job.job_id)[0].reason
    assert "manual call" in reason and "1A01" in reason


def test_an_unknown_position_code_is_refused_not_guessed():
    """A worker seeing "unknown code" beats a robot sent somewhere we invented."""
    _, _, pda = build()
    answer = pda.call_transport("047", "GRV1_LD")
    assert isinstance(answer, str)
    assert "unknown start position code" in answer


def test_the_customers_position_codes_are_used_when_we_have_them():
    """The map is empty until they give it to us; supplied, it is honoured."""
    _, store, pda = build(position_codes={"001": "ASRS", "101": "GRV1_LD"})
    job = pda.call_transport("001", "101")
    assert job.job.from_station == "ASRS"
    assert job.job.to_station == "GRV1_LD"


def test_a_call_to_the_same_place_is_refused():
    _, _, pda = build()
    assert isinstance(pda.call_transport("ASRS", "ASRS"), str)


def test_a_manual_job_can_be_cancelled():
    _, store, pda = build()
    job = pda.call_transport("ASRS", "GRV1_LD")
    assert pda.cancel_transport(job.job.job_id) is True
    assert "cancelled from the PDA" in job.job.failure_reason


def test_cancelling_an_unknown_job_says_no():
    _, _, pda = build()
    assert pda.cancel_transport("job_9999") is False


# -- D6  AGV 상태 확인 --------------------------------------------------------

def test_an_acs_that_cannot_report_a_fleet_returns_nothing():
    """Never invent a fleet. MockAcs has no robots to describe."""
    _, _, pda = build()
    assert pda.fleet_status() == []


def test_the_fleet_is_read_through_not_stored():
    """Robot position and battery are on section 7's "not retained" list."""
    _, store, pda = build()

    class Reporting:
        def fleet_status(self):
            return [{"name": "amr1", "busy": True, "responsive": True}]

    store.acs = Reporting()
    assert pda.fleet_status()[0]["name"] == "amr1"
    # Nothing about the fleet was copied into our own records.
    assert not hasattr(store.records, "_robots")


# -- what a PDA call looks like to the rest of the CSM ------------------------

def test_a_pda_raised_call_is_recorded_as_pda_not_as_a_machine():
    """The protocol treats them identically; the RECORD must not."""
    clock, store, pda = build()
    equipment = store.equipment
    equipment.raise_call("GRV1_LD", TaskType.LOAD, source="PDA")
    from csm.runtime.tasks import EquipmentMonitorTask
    monitor = EquipmentMonitorTask(store, source_for=lambda s: "ASRS")
    asyncio.run(monitor.step())
    assert store.records.calls_for("GRV1_LD")[0].source == "PDA"


# -- D1  보록 입고 — the supplement, and inbound refusing without it ----------
#
# CCS manual §3, §3.4. The three routing fields are entered by a person reading
# a label, and inbound requires them: "a zero here is what produces the
# missing-info rack states" (§5.1, and §6 item 5 sends a human to find them).

def test_supplement_records_what_the_worker_read():
    _, store, pda = build()
    material = pda.register_material(kind="roll")
    assert material.attribute is None, "nothing is known before the label"

    pda.supplement(material.material_ref,
                   attribute=MaterialAttribute.DARK_CCW,
                   drum_type=580, material_type=228)

    again = store.records.material(material.material_ref)
    assert again.attribute is MaterialAttribute.DARK_CCW
    assert again.drum_type == 580
    assert again.material_type == 228
    assert pallet_capacity(again.drum_type) == 1, "580 is a single-bobbin pallet"


def test_supplement_accepts_the_customers_raw_number():
    """The screen sends 1-4, not our enum."""
    _, store, pda = build()
    material = pda.register_material()
    pda.supplement(material.material_ref, attribute=3)
    assert store.records.material(material.material_ref).attribute \
        is MaterialAttribute.DARK_CW


def test_zero_is_refused_as_firmly_as_missing():
    """ZERO IS NOT A VALUE, IT IS THE MISSING STATE.

    `drum_type=0` would otherwise reach `pallet_capacity(0)` and come back as a
    dual pallet — a confident wrong answer from a field nobody filled in.
    """
    _, store, pda = build()
    material = pda.register_material()

    for field in ("drum_type", "material_type"):
        try:
            pda.supplement(material.material_ref, **{field: 0})
        except ValueError as exc:
            assert "zero" in str(exc)
        else:
            raise AssertionError(f"{field}=0 was accepted")

    assert store.records.material(material.material_ref).drum_type is None


def test_supplementing_something_that_does_not_exist_is_an_error():
    """Not an ordinary answer — the screen sent something it never should."""
    _, _, pda = build()
    try:
        pda.supplement("no-such-roll", drum_type=430)
    except ValueError as exc:
        assert "no such material" in str(exc)
    else:
        raise AssertionError("accepted an unknown material")


def test_inbound_refuses_material_nobody_has_described():
    """The customer's rule, and the state their §5.1 exists to clear up."""
    _, store, pda = build()
    material = pda.register_material(kind="roll")

    result = pda.bind_to_rack(material.material_ref, "WIP_GRV_1")

    assert not result.ok
    assert "not supplemented" in result.reason
    assert store.records.slots("WIP_GRV_1")[0].occupied is False


def test_partial_information_is_still_not_enough():
    """All three, or none of it counts. Two out of three is a missing-info rack."""
    _, _, pda = build()
    material = pda.register_material()
    pda.supplement(material.material_ref,
                   attribute=MaterialAttribute.BRIGHT_CW, drum_type=430)

    assert not pda.is_supplemented(material.material_ref)
    assert not pda.bind_to_rack(material.material_ref, "WIP_GRV_1").ok


def test_inbound_succeeds_once_the_label_has_been_read():
    """The whole flow: scan, supplement, inbound."""
    _, store, pda = build()
    material = pda.register_material(kind="roll")
    assert not pda.bind_to_rack(material.material_ref, "WIP_GRV_1").ok

    pda.supplement(material.material_ref,
                   attribute=MaterialAttribute.BRIGHT_CCW,
                   drum_type=360, material_type=125)
    result = pda.bind_to_rack(material.material_ref, "WIP_GRV_1")

    assert result.ok
    assert store.records.locate(material.material_ref) == "WIP_GRV_1"


def test_the_two_refusals_are_told_apart():
    """A worker needs to know which thing to go and do.

    Find another rack, or go and read the label — collapsing both into None
    would leave them guessing.
    """
    _, _, pda = build()
    for _ in range(2):
        pda.bind_to_rack(described(pda).material_ref, "WIP_GRV_1")

    full = pda.bind_to_rack(described(pda).material_ref, "WIP_GRV_1")
    undescribed = pda.bind_to_rack(
        pda.register_material().material_ref, "WIP_CTR_1")

    assert not full.ok and not undescribed.ok
    assert full.reason != undescribed.reason


def test_the_automatic_path_is_not_gated():
    """The WIP diversion parks through `records.park`, not through the PDA.

    A robot stranding a roll must not be blocked because nobody has read a
    label — that material has not been near a person. The customer puts the
    gate on the human inbound, and so do we.
    """
    _, store, pda = build()
    material = store.records.register_material(kind="roll", at=0.0,
                                               location="GRV1_ULD")
    slot = store.records.park("WIP_GRV_1",
                              material_ref=material.material_ref,
                              job_id="job_0001", at=0.0)
    assert slot is not None and slot.occupied


def test_a_supplement_survives_a_restart(tmp_path):
    """`_save` reaches into the store's own saver, so it is worth proving.

    `InMemoryRecords` hands out the live object and mutating it is enough; a
    durable store needs telling. If that call were wrong the supplement would
    work all session and vanish on restart — silently, and only in production.
    """
    from csm.records_sqlite import SqliteRecords

    path = str(tmp_path / "pda.db")
    clock = ManualClock()
    store = JobStore(MockEquipment(["ASRS"], clock), MockAcs(clock), clock,
                     logger=lambda m: None,
                     records=SqliteRecords(path, rack_sizes={"WIP_GRV_1": 2}))
    pda = Pda(store)

    material = pda.register_material(kind="roll")
    pda.supplement(material.material_ref,
                   attribute=MaterialAttribute.DARK_CW,
                   drum_type=580, material_type=302)

    reopened = SqliteRecords(path, rack_sizes={"WIP_GRV_1": 2})
    saved = reopened.material(material.material_ref)
    assert saved.attribute is MaterialAttribute.DARK_CW
    assert saved.drum_type == 580
    assert saved.material_type == 302
