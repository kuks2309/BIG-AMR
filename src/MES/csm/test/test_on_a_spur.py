"""When a robot has actually left the road, and may therefore be driven past.

RULE 3 (user, 2026-08-24): robots going the same way never overtake. Only a
robot that has turned off onto a dead end — docking, or parked — has left the
lane. A robot GIVING WAY is still on the road, and nobody passes it.

That rule deletes a question this file used to try to answer. `_off_the_road`
asked "is my body far enough from the lane centreline that another robot can
squeeze past". It was rewritten three times in one day — a bay radius, a flat
1.20 m, a heading-dependent reach — and produced a collision, a near miss and a
four-robot deadlock in turn, because a yielder is not passable at ANY distance.
There is no clearance to compute. There is only: am I on a spur, or on a road.

The old radius test is what made this necessary. `_in_a_bay` was any marker
within BAY_RADIUS, a 3.8 m circle; around a station on the machine row that
circle reaches the aisle, so a robot standing IN THE ROAD answered "I am in a
bay, you may pass". Measured 2026-08-24: amr4 said exactly that to amr3 and the
two bodies touched at 0.00 m.
"""

import math

import pytest

from csm import plant
from csm.adapters.sim_acs import ROADS, ROBOT_W, SimRobot


def at(x, y, yaw=0.0):
    r = object.__new__(SimRobot)
    r.pose = (x, y, yaw)
    return r


# ------------------------------------------------------- on a spur = off the road

@pytest.mark.parametrize("station", ["CTR2_ULD", "GRV1_LD", "SLT_LD1", "ASRS"])
def test_a_robot_at_its_dock_is_off_the_road(station):
    x, y = plant.DOCKS[station]

    assert at(x, y)._on_a_spur(), f"{station} dock is a dead end"


@pytest.mark.parametrize("name", ["amr1", "amr2", "amr3", "amr4", "amr5"])
def test_a_parked_robot_is_off_the_road(name):
    x, y = plant.parking_for(name)

    assert at(x, y)._on_a_spur()


def test_half_way_up_a_spur_still_counts():
    """It left the lane the moment it passed the junction."""
    dock = plant.DOCKS["GRV1_LD"]
    join = plant.JOINS["GRV1_LD"]
    x = (dock[0] + join[0]) / 2
    y = dock[1] + (join[1] - dock[1]) * 0.4      # nearer the dock than the join

    assert at(x, y)._on_a_spur()


# ------------------------------------------------------------- on a road is NOT

def test_a_robot_on_the_aisle_is_on_the_road():
    assert not at(-2.73, plant.AISLE_S_Y)._on_a_spur()


def test_a_robot_at_a_junction_is_on_the_road():
    """The join belongs to the aisle, not to the spur it feeds."""
    x, y = plant.JOINS["GRV1_LD"]

    assert not at(x, y)._on_a_spur()


def test_a_robot_standing_aside_is_on_the_road():
    """RULE 3, stated directly. A lay-by is not a spur.

    The lay-by sits SIDESTEP metres off the aisle with nothing but open floor
    around it. A robot there is in the way of everything except the one robot
    it is holding the gap for.
    """
    from csm.adapters.sim_acs import SIDESTEP
    lay_by = at(-13.0, plant.AISLE_N_Y - SIDESTEP)

    assert not lay_by._on_a_spur(), "a yielder must never read as passable"


def test_the_old_bay_circle_reached_the_road():
    """Why the radius test had to go, kept as a measurement.

    A robot one bay-radius from a south-row marker sits ~1 m from the south
    aisle. The old rule called that "in a bay"; it is in the road.
    """
    mx, my, _ = plant.MARKERS["CTR2_ULD"]
    y = my + plant.BAY_RADIUS - 0.04           # just inside the old circle
    r = at(mx, y)

    assert abs(y - plant.AISLE_S_Y) < ROBOT_W + 0.30, "close enough to be hit"
    assert not r._on_a_spur(), "and the new rule refuses it"


# ------------------------------------------- out first, turn on the road

def test_a_robot_does_not_rotate_while_on_a_spur():
    """Leaving a bay flat, rather than turning inside it.

    Rotating swings a corner 0.47 m further out than the flat side. Station
    bays were already guarded; parking bays were not, because `_in_a_bay` is
    the STATION test and a parking slot has no marker.

    Measured 2026-08-25: amr4 could not leave leg C slot 2 while amr5
    manoeuvred beside it at 128 degrees, 0.23 m away. Parking slots are
    2.15 m apart and two turning robots need 2.14 m.
    """
    import inspect

    src = inspect.getsource(SimRobot.drive)
    guard = next(line for line in src.splitlines()
                 if "angular.z = 0.0" in line and "cmd" in line)
    # Match on _in_a_bay, not on "if self._final_leg" — drive() has two lines
    # starting that way and the other one is about arrival tolerance.
    condition = next(line for line in src.splitlines()
                     if "_in_a_bay()" in line and line.strip().startswith("if "))

    assert "_on_a_spur()" in condition, \
        "a robot on a dock or parking spur must crab out, not turn"
    assert "_in_a_bay()" in condition, "station bays stay guarded too"
    assert "0.0" in guard, "and the guard zeroes the turn rate"


def test_the_route_out_of_a_bay_is_straight_down_the_spur():
    """So 'do not turn' costs nothing — the first hop is already the junction."""
    from csm.adapters.sim_acs import ROADS

    start = plant.parking_for("amr4")
    route = ROADS.route_from(start, "SLT_LD2")
    first = route[0]
    join = plant.PARKING_JOIN_SLOTS["C"][1]

    assert math.hypot(first[0] - join[0], first[1] - join[1]) < 0.5, \
        "the first waypoint out of a parking slot is its own junction"


# ------------------------------------ a robot leaves by its OWN junction

@pytest.mark.parametrize("name", ["amr1", "amr2", "amr3", "amr4", "amr5"])
def test_leaving_a_parking_slot_goes_straight_down_its_own_spur(name):
    """The 2026-08-25 contact, and the reason it was invisible at slot C2.

    `entry_node_for` picks the on-ramp that minimises the whole trip, which is
    right in open aisle and wrong in a bay. Parking slots and their junctions
    are both 2.15 m apart, so from slot C3 the cheapest on-ramp is the aisle
    2.2 m north — and the straight line to it crosses slot C2.

    Measured: amr5 leaving slot C3 at (29.14,-5.80) was given a first waypoint
    of (26.64,-3.60) and drove diagonally into amr4, parked in C2. Body gap
    0.00 m.

    It was invisible at slot C2 because that junction sits at y = -3.65 and the
    aisle at y = -3.60 — five centimetres apart, so the wrong answer and the
    right one look identical there. Every slot is checked here for that reason.
    """
    from csm.adapters.sim_acs import ROADS

    slot = plant.parking_for(name)
    first = ROADS.route_from(slot, "SLT_LD1")[0]

    assert abs(first[1] - slot[1]) < 0.1, (
        f"{name} leaves slot y={slot[1]:.2f} via y={first[1]:.2f} — that is a "
        f"diagonal across a neighbouring bay")
    # Toward the aisle, whichever side that is: leg A parks WEST of the west
    # cross aisle and exits east; legs B and C park east and exit west. An
    # assertion that assumed one side passed for four robots and failed for
    # amr1 — the same one-example generalisation this whole test exists for.
    segment, index = plant.parking_index(name)
    join = plant.PARKING_JOIN_SLOTS[segment][index]
    assert abs(first[0] - join[0]) < 0.1, "the first hop IS its own junction"


def test_a_robot_in_the_open_aisle_is_still_routed_by_cost():
    """The spur rule must not disturb ordinary planning.

    `entry_node_for` exists because nearest-node routing sent a robot back the
    way it came and produced a closed circuit it never escaped. That fix stays.
    """
    from csm.adapters.sim_acs import ROADS

    assert ROADS.spur_join((0.0, plant.AISLE_S_Y)) is None, \
        "a robot on the aisle is not on a spur"
    assert ROADS.route_from((0.0, plant.AISLE_S_Y), "SLT_LD1")


# ---------------------------------- RULE 5: turn at the corners, nowhere else

def test_a_robot_may_turn_at_each_of_the_four_corners():
    from csm.adapters.sim_acs import ROADS

    corners = [(n, p) for n, p in ROADS.nodes.items() if n.startswith("aisle")]
    assert len(corners) == 4, "the hall has four aisle junctions"

    for name, (x, y) in corners:
        assert at(x, y)._at_a_corner(), f"{name} is a corner"


@pytest.mark.parametrize("where,x,y", [
    ("mid south aisle", 0.0, None),
    ("mid north aisle", -10.0, None),
    ("near a station join", -13.44, None),
])
def test_a_robot_may_not_turn_out_on_a_lane(where, x, y):
    """RULE 5. Rotating is 0.918 m wide where lying flat is 0.450 m.

    Lanes are sized for the flat number, so a robot turning mid-aisle is
    momentarily half a metre wider than the lane was built for. Every
    clearance failure measured on 2026-08-24 and 2026-08-25 was a turning
    robot against a flat one.
    """
    assert not at(x, plant.AISLE_S_Y)._at_a_corner(), f"{where} is not a corner"


def test_turning_is_gated_on_the_corner_test():
    """The rule must actually reach the wheel command."""
    import inspect
    from csm.adapters.sim_acs import SimRobot

    src = inspect.getsource(SimRobot.drive)
    condition = next(line for line in src.splitlines()
                     if "_in_a_bay()" in line and line.strip().startswith("if "))
    following = src.splitlines()[src.splitlines().index(condition) + 1]

    assert "_at_a_corner()" in condition or "_at_a_corner()" in following, \
        "rotation must be forbidden away from the corners"


def test_squaring_up_to_a_machine_is_not_affected():
    """Docking has its own rotation, at the approach point where there is room."""
    import inspect
    from csm.adapters.sim_acs import SimRobot

    assert "angular.z" in inspect.getsource(SimRobot._square_up), \
        "the docking turn is a separate path and must keep working"


# ------------------------------- RULE 5, second half: finish the turn at corners

def aligned(pose, yaw, goal):
    """(lane axis, heading error) for a robot at `pose` heading to `goal`."""
    from csm.adapters.sim_acs import SimRobot, _wrap
    r = object.__new__(SimRobot)
    r.pose = (pose[0], pose[1], yaw)
    r._goal = goal
    axis = r._lane_heading()
    forward, backward = _wrap(axis - yaw), _wrap(axis + math.pi - yaw)
    return axis, (forward if abs(forward) <= abs(backward) else backward)


def test_a_crooked_robot_must_square_up_before_leaving_a_corner():
    """The half of RULE 5 that was missing.

    Forbidding rotation on the lanes without this left a robot leaving the
    junction half-turned and keeping that heading all the way down the aisle.
    Measured 2026-08-25: amr2 and amr5 driving the south aisle 20 degrees
    crooked — 0.70 m across where an aligned robot is 0.45 m. A momentary
    widening became a permanent one.
    """
    from csm.adapters.sim_acs import ROADS, SimRobot

    corner = ROADS.nodes["aisle_nw"]
    _axis, error = aligned(corner, math.radians(160), ROADS.nodes["join_ASRS"])

    assert abs(error) > SimRobot.LANE_ALIGN_TOL, "20 degrees off must be corrected"


def test_a_square_robot_drives_straight_out():
    from csm.adapters.sim_acs import ROADS, SimRobot

    corner = ROADS.nodes["aisle_nw"]
    for yaw in (0.0, math.pi):
        _axis, error = aligned(corner, yaw, ROADS.nodes["join_ASRS"])
        assert abs(error) <= SimRobot.LANE_ALIGN_TOL, "already on the axis"


def test_it_never_spins_180_degrees_to_be_symmetric():
    """Backwards along the lane is as good as forwards — the platform crabs."""
    from csm.adapters.sim_acs import ROADS, SimRobot

    corner = ROADS.nodes["aisle_nw"]
    _axis, error = aligned(corner, math.pi / 2, ROADS.nodes["aisle_sw"])

    assert abs(error) <= SimRobot.LANE_ALIGN_TOL, \
        "heading north with the next hop south is already aligned"


def test_changing_lane_axis_at_a_corner_needs_a_turn():
    from csm.adapters.sim_acs import ROADS, SimRobot

    corner = ROADS.nodes["aisle_nw"]
    _axis, error = aligned(corner, 0.0, ROADS.nodes["aisle_sw"])

    assert abs(error) > SimRobot.LANE_ALIGN_TOL, \
        "east-west to north-south is a real turn, and the corner is where it happens"


def test_the_tolerance_is_a_small_fraction_of_the_margin():
    """5 degrees is chosen, and this is what it actually costs.

    0.068 m of extra width, about a quarter of the 0.30 m margin. An earlier
    comment claimed "under a centimetre", which was simply wrong arithmetic;
    the number is checked here so the claim cannot drift from the value again.
    """
    from csm.adapters.sim_acs import ROBOT_L, ROBOT_W, SimRobot

    th = SimRobot.LANE_ALIGN_TOL
    across = (ROBOT_L / 2) * math.sin(th) + (ROBOT_W / 2) * math.cos(th)
    extra = across - ROBOT_W / 2

    assert 0.06 < extra < 0.08, f"5 degrees costs {extra:.3f} m"
    assert extra < 0.30 / 3, "and stays well inside the margin"
