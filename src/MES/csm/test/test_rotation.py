"""Rotation — the escape hatch that lets the face match while the winding does not.

CCS manual §1.3 and §3.8. To feed a machine there must be material "whose
attribute has the same bright/dark face — rotation direction need not match",
because a 180° turn of the pallet flips the direction, and that turn is a
first-class AGV task type.

THE ASYMMETRY IS THE POINT. The face cannot be fixed by any manoeuvre: dark
material for a machine that wants bright is simply the wrong material. The
rotation can. So one half of the attribute is a hard constraint and the other
is a task.
"""

import pytest

from csm.adapters.base import TaskKind, build_order
from csm.material import MaterialAttribute, needs_rotation
from csm.material_profile import MaterialProfile, simulator_profile

BRIGHT_CW = MaterialAttribute.BRIGHT_CW
BRIGHT_CCW = MaterialAttribute.BRIGHT_CCW
DARK_CW = MaterialAttribute.DARK_CW
DARK_CCW = MaterialAttribute.DARK_CCW


# ------------------------------------------------------------ the decision

def test_same_face_other_rotation_needs_a_turn():
    assert needs_rotation(BRIGHT_CW, BRIGHT_CCW) is True
    assert needs_rotation(DARK_CCW, DARK_CW) is True


def test_an_exact_match_needs_no_turn():
    """Turning a pallet that is already right is a task, a docking and a
    machine still waiting, for nothing."""
    assert needs_rotation(BRIGHT_CW, BRIGHT_CW) is False


def test_the_wrong_face_does_NOT_need_a_turn():
    """"Needs rotating" is not the answer to "this is the wrong material".
    Answering True here would send a robot to turn a pallet that is still
    useless afterwards - the expensive kind of wrong."""
    assert needs_rotation(BRIGHT_CW, DARK_CW) is False
    assert needs_rotation(BRIGHT_CW, DARK_CCW) is False


def test_a_non_rotatable_type_never_turns():
    """§4.6.11 configures some material types as non-rotatable: the attribute
    must then match exactly."""
    assert needs_rotation(BRIGHT_CW, BRIGHT_CCW, rotatable=False) is False


def test_unknown_on_either_side_never_turns():
    """An unrecorded attribute is not a wildcard - we would be rotating on a
    guess. Same refusal as attribute_matches."""
    assert needs_rotation(None, BRIGHT_CW) is False
    assert needs_rotation(BRIGHT_CW, None) is False


def test_rotating_flips_the_winding_and_keeps_the_face():
    """Turning the PALLET does not change which side of the foil faces out."""
    for a in MaterialAttribute:
        assert a.rotated().face is a.face
        assert a.rotated().rotation is not a.rotation
        assert a.rotated().rotated() is a


def test_a_rotated_pallet_then_matches_exactly():
    """The whole reason the escape hatch works."""
    assert BRIGHT_CW.rotated() is BRIGHT_CCW
    assert needs_rotation(BRIGHT_CW.rotated(), BRIGHT_CCW) is False


# ------------------------------------------- what a station asks for

def test_a_station_can_say_what_attribute_it_wants():
    """§4.6.5 puts the requested attribute in machine configuration, and §1.3
    reads it back before feeding."""
    p = MaterialProfile({"GRV1_LD": {"attribute": DARK_CW}})

    assert p.requires("GRV1_LD") is DARK_CW
    assert p.requires("SOMEWHERE_ELSE") is None


def test_the_simulator_gives_every_station_a_requirement():
    p = simulator_profile(["GRV1_LD", "CTR1_LD", "SLT_LD1"])

    assert p.requires("CTR1_LD") in set(MaterialAttribute)


# --------------------------------------------- and the task that does it

class Job:
    job_id = "job_0001"
    from_station = "CTR1_ULD"
    to_station = "SLT_LD1"
    priority = 0
    class carries:
        value = "roll"


def test_a_plain_delivery_has_no_turn():
    kinds = [t.kind for t in build_order(Job()).tasks]

    assert kinds == [TaskKind.MOVE, TaskKind.LOAD, TaskKind.MOVE,
                     TaskKind.UNLOAD]


def test_a_turn_goes_after_LOAD_and_before_the_MOVE():
    """The pallet has to be on the deck to be turned, and turning it at the
    destination would mean arriving with the wrong presentation and blocking
    the port while it spins."""
    kinds = [t.kind for t in build_order(Job(), rotate=True).tasks]

    assert kinds == [TaskKind.MOVE, TaskKind.LOAD, TaskKind.TURN,
                     TaskKind.MOVE, TaskKind.UNLOAD]


def test_the_turn_happens_at_the_source():
    order = build_order(Job(), rotate=True)
    turn = next(t for t in order.tasks if t.kind is TaskKind.TURN)

    assert turn.target == "CTR1_ULD"


def test_a_deliver_and_collect_visit_is_untouched():
    """One visit to one port, where the machine confirms placement and pickup
    separately. There is nothing to turn on the way in."""
    class SamePort(Job):
        from_station = to_station = "CTR1_LD"

    kinds = [t.kind for t in build_order(SamePort(), rotate=True).tasks]

    assert TaskKind.TURN not in kinds


# ------------------------------- and the whole chain, source pick to task

def monitor_with(profile, available):
    """An EquipmentMonitorTask with only what `_claim_material` touches."""
    from csm.runtime.tasks.equipment_monitor import EquipmentMonitorTask

    class Records:
        def ready_materials(self, location, at):
            return list(available)
        def register_material(self, **kw):
            raise AssertionError("should have claimed, not minted")

    class Store:
        records = Records()
        active = []
        def clock(self):
            return 0.0

    task = object.__new__(EquipmentMonitorTask)
    task.store = Store()
    task.profile = profile
    task.curing = None
    return task


class Roll:
    kind = "roll"
    def __init__(self, ref, attribute):
        self.material_ref, self.attribute = ref, attribute


def test_an_exact_match_is_preferred_over_one_needing_a_turn():
    """A turn is a real task with a real cost. Taking the rotatable one while
    an exact one sits beside it buys nothing."""
    task = monitor_with(None, [Roll("needs-turn", BRIGHT_CCW),
                               Roll("exact", BRIGHT_CW)])

    ref, turn = task._claim_material("SRC", "roll", at=0.0, wants=BRIGHT_CW)

    assert ref == "exact"
    assert turn is False


def test_a_rotatable_candidate_is_taken_when_there_is_no_exact_one():
    task = monitor_with(None, [Roll("needs-turn", BRIGHT_CCW)])

    ref, turn = task._claim_material("SRC", "roll", at=0.0, wants=BRIGHT_CW)

    assert ref == "needs-turn"
    assert turn is True, "the escape hatch was not used"


def test_the_wrong_face_is_not_claimed_even_if_it_is_all_there_is():
    """It cannot serve the requirement and no turn will fix it, so claiming it
    would occupy a robot to deliver material the machine must refuse."""
    task = monitor_with(None, [Roll("wrong-face", DARK_CW)])

    ref, turn = task._claim_material("SRC", "roll", at=0.0, wants=BRIGHT_CW)

    assert ref == "wrong-face", "no better candidate — still claimed"
    assert turn is False, "a turn must not be claimed to fix a face"


def test_with_no_requirement_configured_the_first_candidate_wins():
    """What the code did before, and still right for a station nobody has
    configured."""
    task = monitor_with(None, [Roll("first", DARK_CCW), Roll("second", BRIGHT_CW)])

    ref, turn = task._claim_material("SRC", "roll", at=0.0, wants=None)

    assert ref == "first"
    assert turn is False


def test_the_decision_reaches_the_order():
    """The job carries it, so build_order can place the TURN without asking
    again — re-deriving it later would mean reading records that have moved on.
    """
    import inspect

    from csm.adapters.sim_acs import SimAcs
    from csm.job import Job

    assert "rotate" in {f for f in Job.__dataclass_fields__}
    src = inspect.getsource(SimAcs.submit_job)
    assert 'build_order(job, rotate=' in src
