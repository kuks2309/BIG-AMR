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
    """So 'do not turn' costs nothing — the first hop is already a junction."""
    from csm.adapters.sim_acs import ROADS

    start = plant.parking_for("amr4")
    first = ROADS.route_from(start, "SLT_LD2")[0]
    mine = [ROADS.nodes[j] for j in ROADS.spur_joins(start)]

    assert any(math.hypot(first[0] - j[0], first[1] - j[1]) < 0.5 for j in mine), \
        "the first waypoint out of a parking slot is one of its own junctions"
    assert abs(first[1] - start[1]) < 0.1, "and straight down the spur"


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

    # The first hop is one of ITS OWN junctions — a spur now meets both lanes,
    # so there are two right answers and the router picks whichever can reach
    # the destination on a one-way road.
    from csm.adapters.sim_acs import ROADS

    mine = {tuple(round(v, 3) for v in ROADS.nodes[j])
            for j in ROADS.spur_joins(slot)}
    assert mine, f"{name}'s bay has no junction"
    assert tuple(round(v, 3) for v in first) in mine, (
        f"{name} leaves via {first}, which is not a junction of its own spur "
        f"({sorted(mine)})")


def test_a_robot_in_the_open_aisle_is_still_routed_by_cost():
    """The spur rule must not disturb ordinary planning.

    `entry_node_for` exists because nearest-node routing sent a robot back the
    way it came and produced a closed circuit it never escaped. That fix stays.
    """
    from csm.adapters.sim_acs import ROADS

    assert ROADS.spur_join((0.0, plant.AISLE_S_Y)) is None, \
        "a robot on the aisle is not on a spur"
    assert ROADS.route_from((0.0, plant.AISLE_S_Y), "SLT_LD1")


# ------------------------------------------ docking keeps its own rotation

def test_squaring_up_to_a_machine_is_not_affected():
    """Docking has its own rotation, at the approach point where there is room."""
    import inspect
    from csm.adapters.sim_acs import SimRobot

    assert "angular.z" in inspect.getsource(SimRobot._square_up), \
        "the docking turn is a separate path and must keep working"


