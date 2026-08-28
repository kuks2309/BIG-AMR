"""Parking is a QUEUE, not one bay per leg.

One bay per leg silently assumed one robot per leg. The specification puts two
robots on legs A and B and six on leg C, and with two robots both were sent
home to identical coordinates — two robots aiming at the same point, which is
the collision the bay geometry was fixed for on 2026-08-18.

The customer's own layout works as a queue: the surveyed drawing has a dock
column and a separate queue column behind it, 51 positions in the cell area,
not a reserved bay per vehicle.
"""

import pytest

from csm import plant
from csm.adapters import roads

ROBOTS = ("amr1", "amr2", "amr3")


# -- every robot gets its own place to stand ---------------------------------

def test_every_robot_has_a_slot():
    for name in ROBOTS:
        assert plant.parking_for(name) is not None, name


def test_no_two_robots_share_a_slot():
    """The whole point. Identical coordinates is the failure being removed."""
    slots = [plant.parking_for(n) for n in ROBOTS]
    assert len(set(slots)) == len(slots), slots


def test_a_robot_with_no_leg_gets_no_slot():
    """None, not a default. A default means two robots at one point.

    The name has to be one the fleet table really does not contain. It used to
    be `amr9`, which stopped being unknown the moment the table was generated
    for the deck's full ten — a test that passes because of a coincidence stops
    testing anything the day the coincidence ends.
    """
    assert "amr99" not in plant.ROBOT_SEGMENT, "pick a name that is not a robot"
    assert plant.parking_for("amr99") is None
    assert plant.parking_for("forklift") is None


def test_slot_assignment_is_stable_when_the_fleet_grows():
    """A robot drives home to its slot, so it must not move under it.

    Adding a second robot to leg A must not shift amr1's slot.
    """
    before = plant.parking_for("amr1")
    plant.ROBOT_SEGMENT["amr4"] = "A"
    try:
        assert plant.parking_for("amr1") == before
        assert plant.parking_for("amr4") != before
        assert plant.parking_for("amr4") == plant.PARKING_SLOTS["A"][1]
    finally:
        del plant.ROBOT_SEGMENT["amr4"]


def test_a_leg_with_more_robots_than_slots_says_so():
    """None rather than wrapping round onto an occupied slot."""
    plant.ROBOT_SEGMENT.update({f"amrX{i}": "A" for i in range(9)})
    try:
        crowded = [plant.parking_for(f"amrX{i}") for i in range(9)]
        assert None in crowded
    finally:
        for i in range(9):
            del plant.ROBOT_SEGMENT[f"amrX{i}"]


# -- the queue matches the fleet the specification describes -----------------

def test_a_slot_exists_for_every_robot_in_the_fleet_table():
    for segment, count in plant.FLEET.items():
        assert len(plant.PARKING_SLOTS[segment]) == count, segment


def test_slots_are_spaced_by_the_robots_own_length():
    """Derived, not chosen — and it is LENGTH now, not width.

    Robots park sideways on, nose along the aisle, so the queue runs down the
    robot's long axis. Spacing by width left 0.55 m of air between two 1.6 m
    bodies: on 2026-08-26 amr4 moved 0.18 m out of leg C slot 2 and was
    immediately 0.167 m from amr5, and three robots froze on "layer 1" with no
    way to resolve it.
    """
    assert plant.PARK_PITCH == plant.ROBOT_L + plant.PARK_CLEARANCE
    for segment, slots in plant.PARKING_SLOTS.items():
        for a, b in zip(slots, slots[1:]):
            gap = abs(b[1] - a[1]) - plant.ROBOT_L
            assert gap >= plant.PARK_CLEARANCE - 1e-9, (segment, gap)


def test_a_bay_clears_the_lane_it_hangs_off_not_the_aisle_centre():
    """The bays must clear the LANE, which is not where the centreline is.

    Regression for the two-lane build: PARK_X was measured from the aisle
    centreline, so splitting each aisle moved the outer lane 0.90 m toward the
    bays and ate most of the clearance without changing the constant that
    claimed to guarantee it.
    """
    for which, lane in ((0, plant.AISLE_W_OUT), (1, plant.AISLE_E_OUT)):
        bay = plant.PARK_X[which]
        gap = abs(bay - lane) - plant.ROBOT_W       # both bodies, sideways on
        assert gap >= plant.PARK_CLEARANCE - 1e-9, (which, gap)


def test_a_parked_robot_faces_the_way_its_lane_runs():
    """It leaves by crabbing sideways, so it cannot be parked nose-in."""
    import math
    for segment in plant.PARKING_SLOTS:
        which, _ = plant._PARK_SIDE[segment]
        side = plant._PARK_AISLE[which]
        expected = plant._HEADING_YAW[plant.RING["outer"][side]]
        assert plant.parking_yaw(segment) == expected, segment
        assert abs(math.cos(plant.parking_yaw(segment))) < 1e-9, segment


def test_the_two_east_queues_grow_apart_not_into_each_other():
    """B runs north, C runs south. Otherwise they would meet in the middle."""
    b = [y for _, y in plant.PARKING_SLOTS["B"]]
    c = [y for _, y in plant.PARKING_SLOTS["C"]]
    assert b == sorted(b) and min(b) > 0
    assert c == sorted(c, reverse=True) and max(c) < 0


def test_every_slot_is_inside_the_hall():
    """With the robot's TURNING radius, not merely its width."""
    pad = roads.ROBOT_RADIUS + roads.MARGIN
    for segment, slots in plant.PARKING_SLOTS.items():
        for x, y in slots:
            assert plant.HALL_S + pad <= y <= plant.HALL_N - pad, (segment, y)
            assert plant.HALL_W + pad <= x <= plant.HALL_E - pad, (segment, x)


# -- the road network reaches all of them ------------------------------------

def test_every_slot_has_a_spur_on_the_network():
    net = roads.build()
    for segment, slots in plant.PARKING_SLOTS.items():
        for i in range(len(slots)):
            suffix = "" if i == 0 else str(i + 1)
            assert f"park_{segment}{suffix}" in net.nodes
            for ring in ("inner", "outer"):
                assert f"join_park{segment}{suffix}_{ring}" in net.nodes, \
                    "a bay needs a junction on each lane, like any other spur"


def test_slot_zero_keeps_its_historic_name():
    """So anything that only knew about one bay per leg still resolves."""
    net = roads.build()
    for segment in plant.PARKING_SLOTS:
        assert net.nodes[f"park_{segment}"] == plant.PARKING[segment]


def test_a_queue_slot_never_sits_on_the_aisle_itself():
    """Spurs hang OFF a cross aisle. A robot parked on one blocks it."""
    for segment, slots in plant.PARKING_SLOTS.items():
        for x, _ in slots:
            assert x not in (plant.AISLE_W_X, plant.AISLE_E_X)
