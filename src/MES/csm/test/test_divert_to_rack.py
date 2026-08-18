"""Diversion — the one job type CSM originates with no caller.

Every other job answers a machine's request. This one fires when a source is
holding finished material and every destination that could take it is occupied:
if nobody moves it, the upstream machine blocks.

The specification names CSM as the decider and gives the rule — find a free rack
port, take the first.
"""

import pytest

from csm import plant
from csm.adapters.base import StationStatus
from csm.runtime.job_store import JobStore
from csm.runtime.tasks.equipment_monitor import EquipmentMonitorTask


class FakeEquipment:
    """Station status we control outright, and no calls at all."""

    def __init__(self, status):
        self.status = dict(status)

    def poll_calls(self):
        return []

    def acknowledge_call(self, call):
        pass

    def get_station_status(self, station_id):
        return self.status.get(station_id, StationStatus.IDLE)

    def send_station_command(self, station_id, command):
        return True

    def list_stations(self):
        return list(self.status)


def _monitor(status, segments):
    clock = lambda: 0.0                                      # noqa: E731
    store = JobStore(FakeEquipment(status), acs=None, clock=clock,
                     logger=lambda m: None)
    task = EquipmentMonitorTask(store, source_for=lambda s: "ASRS")
    task.divert_for = segments
    return store, task


SEG_B = [s for s in plant.SEGMENTS if s["name"] == "B"]


def test_no_diversion_while_a_destination_can_still_take_it():
    """Diversion must never compete with a real delivery."""
    status = {"GRV1_ULD": StationStatus.FINISHED}
    status.update({d: StationStatus.BUSY for d in SEG_B[0]["to"]})
    status["CTR3_LD"] = StationStatus.IDLE          # one is free
    store, task = _monitor(status, SEG_B)
    task._divert_stranded()
    assert task.diverted == 0
    assert not store.active


def test_material_is_parked_when_every_destination_is_full():
    status = {"GRV1_ULD": StationStatus.FINISHED}
    status.update({d: StationStatus.BUSY for d in SEG_B[0]["to"]})
    store, task = _monitor(status, SEG_B)
    task._divert_stranded()
    assert task.diverted == 1
    job = store.active[0].job
    assert job.from_station == "GRV1_ULD"
    assert job.to_station in SEG_B[0]["buffer"]


def test_nothing_happens_when_the_rack_is_also_full():
    """No free port, no job — and crucially no crash and no lost material."""
    status = {"GRV1_ULD": StationStatus.FINISHED}
    status.update({d: StationStatus.BUSY for d in SEG_B[0]["to"]})
    status.update({b: StationStatus.BUSY for b in SEG_B[0]["buffer"]})
    store, task = _monitor(status, SEG_B)
    task._divert_stranded()
    assert task.diverted == 0
    assert not store.active


def test_a_source_already_being_served_is_left_alone():
    status = {"GRV1_ULD": StationStatus.FINISHED}
    status.update({d: StationStatus.BUSY for d in SEG_B[0]["to"]})
    store, task = _monitor(status, SEG_B)
    store.claim_station("GRV1_ULD")
    task._divert_stranded()
    assert task.diverted == 0


def test_diversion_is_off_unless_asked_for():
    """Existing callers must not silently acquire a new behaviour."""
    status = {"GRV1_ULD": StationStatus.FINISHED}
    status.update({d: StationStatus.BUSY for d in SEG_B[0]["to"]})
    store, task = _monitor(status, SEG_B)
    task.divert_for = None
    task._divert_stranded()
    assert task.diverted == 0


def test_material_goes_to_the_destination_legs_rack():
    """A rack buffers the INPUT of its process, not the output of the source."""
    assert plant.buffer_for("GRV1_ULD") == ["WIP_CTR_1", "WIP_CTR_2"]
    assert plant.buffer_for("CTR2_ULD") == ["WIP_SLT_1", "WIP_SLT_2"]
    assert plant.buffer_for("ASRS") == ["WIP_GRV_1", "WIP_GRV_2"]
