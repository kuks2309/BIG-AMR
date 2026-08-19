"""The PDA — the fourth responsibility on the customer's CSM scope slide.

The only one where a PERSON is the caller. These test the LOGIC a handheld
screen would call; the screens themselves are unscoped, which the handbook
records as "CSM has no UI in the specification and needs one".
"""

import asyncio

import pytest

from csm.adapters.base import StationStatus, TaskType
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


# -- D1  생산 정보 등록 -------------------------------------------------------

def test_scanning_material_gives_it_a_lot_id():
    """A worker scanning material is usually the first time we hear of it."""
    _, store, pda = build()
    material = pda.register_material(kind="roll", location="ASRS")
    assert len(material.lot_id) == 17
    assert store.records.locate(material.material_ref) == "ASRS"


def test_binding_material_to_a_rack_occupies_a_slot():
    _, store, pda = build()
    material = pda.register_material(kind="roll")
    slot = pda.bind_to_rack(material.material_ref, "WIP_GRV_1")
    assert slot.material_ref == material.material_ref
    assert store.records.locate(material.material_ref) == "WIP_GRV_1"


def test_a_full_rack_answers_rather_than_raising():
    """A full rack is an ordinary answer a worker needs to see."""
    _, store, pda = build()
    for _ in range(2):
        pda.bind_to_rack(pda.register_material().material_ref, "WIP_GRV_1")
    third = pda.register_material()
    assert pda.bind_to_rack(third.material_ref, "WIP_GRV_1") is None


# -- D2  자재 위치 조회 -------------------------------------------------------

def test_looking_up_a_roll_gives_where_it_is_and_where_it_has_been():
    clock, store, pda = build()
    material = pda.register_material(location="ASRS")
    clock.advance(5.0)
    pda.bind_to_rack(material.material_ref, "WIP_GRV_1")

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
