"""The rack as a stateful object, not a bucket with a capacity.

CCS manual §2.2 (the monitor icons), §1.3 (the loading-area supply conditions)
and §2.15 (what counts toward a line's quota).

WHY THIS HAD TO CHANGE. Every selection rule in the manual asks about the RACK
before it asks about the material on it. §1.3 wants "at least three auto-mode
non-abnormal racks in the loading area, at least one of them empty"; §1.2.1.1
wants a buffer rack "with no abnormality"; §4.6.6 writes the carried material
type, attribute, bobbin type and roll number INTO the target rack. None of
those questions can be asked of an integer, which is what a rack was.
"""

import pytest

from csm.material import MaterialAttribute
from csm.records import InMemoryRecords, RackMode, SlotStatus

RACKS = {"WIP_A": 4, "WIP_B": 4, "WIP_C": 4, "WIP_D": 4}


def store():
    return InMemoryRecords(rack_sizes=RACKS)


# ------------------------------------------------------------ the rack mode

def test_a_rack_nobody_has_touched_is_in_service():
    """Racks arrive from configuration already working. A mode has to be set
    to take one OUT of service, never to put one in."""
    r = store()

    assert r.rack_mode("WIP_A") is RackMode.AUTO
    assert r.rack_usable("WIP_A") is True


@pytest.mark.parametrize("mode", [RackMode.MANUAL, RackMode.LOCKED,
                                  RackMode.ABNORMAL, RackMode.UNAVAILABLE])
def test_only_auto_is_in_the_automatic_flow(mode):
    r = store()
    r.set_rack_mode("WIP_A", mode)

    assert r.rack_usable("WIP_A") is False


def test_a_person_may_still_park_on_a_locked_rack():
    """That is what LOCKED is for - "locked in CCS, no automatic transport".
    Gating `park` on the mode would stop the PDA doing its job."""
    r = store()
    r.set_rack_mode("WIP_A", RackMode.LOCKED)

    assert r.park("WIP_A", "ROLL-1", "job_0001", at=1.0) is not None


# --------------------------------------------- the fail-safe that matters

def test_an_empty_abnormal_rack_still_counts_as_holding_material():
    """CCS manual §2.15. A broken rack REDUCES the line's quota rather than
    being ignored - the opposite of what an optimiser would do, and the right
    way round: the line cannot use it, so the line must not be promised it."""
    r = store()
    assert r.holds_material("WIP_A") is False

    r.set_rack_mode("WIP_A", RackMode.ABNORMAL)

    assert r.holds_material("WIP_A") is True


def test_an_occupied_healthy_rack_counts_too():
    r = store()
    r.park("WIP_A", "ROLL-1", "job_0001", at=1.0)

    assert r.holds_material("WIP_A") is True


def test_an_empty_healthy_rack_counts_for_nothing():
    r = store()

    assert r.holds_material("WIP_A") is False


# ------------------------------------- what the slot knows about its material

def test_parking_records_what_was_put_there():
    r = store()
    slot = r.park("WIP_A", "ROLL-1", "job_0001", at=1.0,
                  material_type="CATHODE", bobbin_type=430,
                  material_attribute=MaterialAttribute.BRIGHT_CW)

    assert slot.material_type == "CATHODE"
    assert slot.material_attribute is MaterialAttribute.BRIGHT_CW
    assert slot.bobbin_type == 430
    assert slot.status is SlotStatus.STOCKED


def test_completion_writes_identity_into_the_target_rack():
    """CCS manual §4.6.6: completing a task writes the material type,
    attribute, bobbin type and roll number INTO THE TARGET RACK. The task is
    the carrier of identity and delivery is what transfers it - so this is a
    separate moment from placing the pallet, and has its own call."""
    r = store()
    r.park("WIP_A", "ROLL-1", "job_0001", at=1.0)
    slot = r.slots("WIP_A")[0]
    assert slot.material_type is None

    r.describe_slot("WIP_A", slot.slot, material_type="ANODE",
                    material_attribute=MaterialAttribute.DARK_CCW,
                    bobbin_type=580)

    assert slot.material_type == "ANODE"
    assert slot.material_attribute is MaterialAttribute.DARK_CCW
    assert slot.bobbin_type == 580


def test_retrieving_forgets_what_was_there():
    """Otherwise `holds_attribute` answers about material that has gone, and
    §1.3 refuses to feed a machine because of a roll that left an hour ago."""
    r = store()
    r.park("WIP_A", "ROLL-1", "job_0001", at=1.0, material_type="CATHODE",
           material_attribute=MaterialAttribute.BRIGHT_CW, bobbin_type=430)

    r.retrieve("WIP_A", at=2.0)
    slot = r.slots("WIP_A")[0]

    assert slot.material_type is None
    assert slot.material_attribute is None
    assert slot.status is SlotStatus.EMPTY
    assert r.holds_attribute(["WIP_A"], MaterialAttribute.BRIGHT_CW) is False


def test_an_empty_slot_describes_nothing_and_that_is_fine():
    """Empty is not the same as undescribed. Confusing the two would exclude
    every empty rack from feeding, which is exactly the rack we want."""
    r = store()

    assert r.slots("WIP_A")[0].described is True


def test_a_slot_holding_material_it_cannot_name_is_undescribed():
    r = store()
    r.park("WIP_A", "ROLL-1", "job_0001", at=1.0)     # no type, no attribute

    assert r.slots("WIP_A")[0].described is False


# ------------------------------------- §1.3, the loading-area supply conditions

def area():
    return ["WIP_A", "WIP_B", "WIP_C"]


def test_three_usable_racks_with_one_empty_may_be_fed():
    r = store()
    r.park("WIP_A", "ROLL-1", "j1", at=1.0, material_type="CATHODE",
           material_attribute=MaterialAttribute.BRIGHT_CW)

    assert r.racks_fit_to_feed(area()) is True


def test_two_usable_racks_is_not_enough():
    r = store()
    r.set_rack_mode("WIP_C", RackMode.ABNORMAL)

    assert r.racks_fit_to_feed(area()) is False


def test_an_area_with_no_empty_slot_may_not_be_fed():
    r = store()
    for rack in area():
        for _ in range(RACKS[rack]):
            r.park(rack, "ROLL", "j", at=1.0, material_type="CATHODE",
                   material_attribute=MaterialAttribute.BRIGHT_CW)

    assert r.racks_fit_to_feed(area()) is False


def test_a_rack_that_cannot_name_what_it_holds_blocks_the_area():
    """§1.3: every rack holding material must have both type and attribute
    recorded. Feeding a machine beside material we cannot identify is how the
    wrong attribute reaches it."""
    r = store()
    r.park("WIP_A", "ROLL-1", "j1", at=1.0)           # undescribed

    assert r.racks_fit_to_feed(area()) is False


def test_a_task_running_in_the_area_blocks_it():
    r = store()
    r.set_slot_status("WIP_A", 1, SlotStatus.IN_TASK)

    assert r.racks_fit_to_feed(area()) is False


def test_an_area_already_holding_the_required_attribute_is_refused():
    """The caller asks this one, because only it knows what the machine
    requires. §1.3 lists it alongside the rest."""
    r = store()
    r.park("WIP_A", "ROLL-1", "j1", at=1.0, material_type="CATHODE",
           material_attribute=MaterialAttribute.BRIGHT_CW)

    assert r.holds_attribute(area(), MaterialAttribute.BRIGHT_CW) is True
    assert r.holds_attribute(area(), MaterialAttribute.DARK_CCW) is False


# ------------------------------------------------ it has to survive a restart

def test_a_rack_taken_out_of_service_stays_out_across_a_restart(tmp_path):
    """An abnormal rack that came back as AUTO would be fed. The whole point
    of a store that survives an unplanned stop is that this cannot happen."""
    from csm.records_sqlite import SqliteRecords

    path = str(tmp_path / "racks.db")
    first = SqliteRecords(path, rack_sizes=RACKS)
    first.set_rack_mode("WIP_A", RackMode.ABNORMAL)

    again = SqliteRecords(path, rack_sizes=RACKS)

    assert again.rack_mode("WIP_A") is RackMode.ABNORMAL
    assert again.rack_usable("WIP_A") is False
    assert again.holds_material("WIP_A") is True


def test_what_a_rack_holds_survives_a_restart(tmp_path):
    """§4.6.6's identity transfer IS the record of what is on the rack. If it
    does not survive, the rack comes back holding something it cannot name -
    which §1.3 then treats as a reason to refuse feeding the machine."""
    from csm.records_sqlite import SqliteRecords

    path = str(tmp_path / "racks.db")
    first = SqliteRecords(path, rack_sizes=RACKS)
    first.park("WIP_A", "ROLL-1", "job_0001", at=1.0, material_type="CATHODE",
               material_attribute=MaterialAttribute.BRIGHT_CW, bobbin_type=430)

    again = SqliteRecords(path, rack_sizes=RACKS)
    slot = again.slots("WIP_A")[0]

    assert slot.material_type == "CATHODE"
    assert slot.material_attribute is MaterialAttribute.BRIGHT_CW
    assert slot.bobbin_type == 430
    assert slot.status is SlotStatus.STOCKED
    assert slot.described is True
