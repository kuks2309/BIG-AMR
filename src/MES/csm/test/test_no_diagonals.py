"""RULE 1: a robot on the road drives the road. No slant across the aisle.

Observed 2026-08-26, and reported twice by the user in the same words: a robot
comes out of a dock onto the OUTER lane and then crosses to the inner one at
about 45 degrees instead of driving straight up its own spur; sometimes it
drives a little way along the outer lane, backs up, and then slants across.

The cause is that the first hop is the ONE leg no lane covers, so
`entry_node_for` may choose it freely up to `MAX_ONRAMP` = 6 m, and it chooses
by TOTAL trip cost. From the CTR2_ULD outer junction (-3.36,-4.50):

    its own inner junction   (-3.36,-2.70)   1.80 m, due north
    what cost comparison chose:
      join_CTR2_LD_inner     (-6.24,-2.70)   3.40 m, at 148 degrees

The diagonal saves a little lane distance and spends 3.40 m of open floor
slanting across both lanes to buy it. Under rule 1 there is nothing to compare.

Measured over the convergence harness — every parking bay to every dock,
replanning every half metre, 7,965 on-ramp choices: 2,043 of them (26%) were
slants taken while the robot was on the road. With the rule: 0 of 8,034, and
the same 0 of 270 routes fail to arrive.
"""

import math

import pytest

from csm import plant
from csm.adapters import roads

NETWORK = roads.build()


def slants(pos, node_name):
    """Does the hop from `pos` to this node move in BOTH x and y?"""
    nx, ny = NETWORK.nodes[node_name]
    dx, dy = abs(nx - pos[0]), abs(ny - pos[1])
    if math.hypot(dx, dy) <= 0.3:
        return False                     # standing on it
    return min(dx, dy) > roads.ROBOT_RADIUS


def onramp(pos, station):
    return NETWORK.entry_node_for(pos, f"dock_{station}")


# ------------------------------------------------------------ the dead band

def test_the_strip_between_the_two_lanes_counts_as_road():
    """`ring_at` says "which lane" and between them the answer is neither: they
    are 1.80 m apart, so at the midpoint a robot is 0.90 m from each line and
    outside ROBOT_RADIUS of both. That dead band crosses every spur mouth in
    the plant, and it is where an unconstrained re-plan invents a diagonal."""
    mid = (plant.DOCKS["CTR2_ULD"][0], (plant.AISLE_S_IN + plant.AISLE_S_OUT) / 2)

    assert NETWORK.ring_at(mid) is None, "this is the gap the old test left"
    assert NETWORK.spur_joins(mid) == [], "and spur_joins does not cover it"
    assert NETWORK.on_the_road(mid) is True


@pytest.mark.parametrize("side", ["north", "south", "west", "east"])
def test_both_lanes_and_the_strip_between_them_are_road(side):
    axis, inner = plant.LANE_LINE[("inner", side)]
    _, outer = plant.LANE_LINE[("outer", side)]
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        value = inner + (outer - inner) * t
        point = (value, 0.0) if axis == "x" else (0.0, value)

        assert NETWORK.on_the_road(point) is True


def test_the_middle_of_the_hall_is_not_road():
    assert NETWORK.on_the_road((0.0, 0.0)) is False


# ------------------------------------------------------- the reported case

def test_the_junction_a_robot_backs_out_onto_does_not_slant():
    """amr4 leaving CTR2_ULD, the case as reported."""
    pos = plant.JOINS_OUTER["CTR2_ULD"]

    for station in ("ASRS", "GRV1_LD", "CTR1_LD", "SLT_LD1", "GRV4_ULD"):
        node = onramp(pos, station)
        assert not slants(pos, node), \
            f"heading for {station} it slants to {node} at {NETWORK.nodes[node]}"


def test_it_does_not_slant_after_driving_on_a_little_either():
    """The other half of the report: drives along the outer lane, then slants.
    Re-planning happens every cycle, so every point on the way must hold."""
    x, y = plant.JOINS_OUTER["CTR2_ULD"]
    for step in (0.25, 0.5, 1.0, 1.5, 2.0):
        for pos in ((x - step, y), (x + step, y)):
            for station in ("ASRS", "CTR1_LD", "GRV4_ULD"):
                node = onramp(pos, station)
                assert not slants(pos, node), \
                    f"at {pos} heading for {station} it slants to {node}"


def test_no_dock_in_the_plant_is_left_by_a_slant():
    """27 of 27, from the junction each one backs out onto."""
    for leaving in sorted(plant.DOCKS):
        pos = plant.JOINS_OUTER[leaving]
        for station in ("ASRS", "CTR1_LD", "GRV4_ULD", "SLT_LD1"):
            node = onramp(pos, station)
            assert not slants(pos, node), \
                f"leaving {leaving} for {station} it slants to {node}"


def test_crossing_between_the_lanes_never_turns_the_robot_round():
    """The "backs up a little" half of the report.

    A first attempt at this fixed the junction and caused exactly that: it made
    the node a robot is standing NEAR the on-ramp, so half way across to the
    inner lane the plan pointed at the junction 0.90 m BEHIND. Constraining the
    SHAPE of the hop has no such backward pull.
    """
    x = plant.DOCKS["CTR2_ULD"][0]
    for t in (0.25, 0.5, 0.75):
        y = plant.AISLE_S_OUT + (plant.AISLE_S_IN - plant.AISLE_S_OUT) * t
        node = onramp((x, y), "ASRS")           # ASRS is reached via the inner
        assert NETWORK.nodes[node][1] >= y, \
            f"at {(x, y)} it sends the robot back south to {node}"


# --------------------------------------------------- and it still finds a way

def test_a_robot_in_open_floor_may_still_slant_onto_the_road():
    """The rule is about robots ON the road. One in open floor has to get to
    it, and refusing every angled hop would strand it."""
    pos = (0.0, 0.0)

    assert NETWORK.on_the_road(pos) is False
    assert onramp(pos, "ASRS") is not None


def test_every_dock_is_still_reachable_from_every_bay():
    """The constraint must not cost a route. `test_routing_terminates` walks
    these; this only asks that a plan exists at all."""
    for name in plant.ROBOT_SEGMENT:
        start = plant.parking_for(name)
        for station in sorted(plant.DOCKS):
            assert NETWORK.route_from(start, station), \
                f"{name} cannot plan to {station}"


def test_the_sweep_finds_no_slant_anywhere_on_the_road():
    """The property, not the corner: every position on the way from four bays
    to four docks, re-planned every half metre."""
    seen = 0
    for name in list(plant.ROBOT_SEGMENT)[:4]:
        start = plant.parking_for(name)
        for station in ("ASRS", "CTR1_LD", "GRV4_ULD", "SLT_LD1"):
            pos = start
            for _ in range(120):
                route = NETWORK.route_from(pos, station)
                if not route:
                    break
                ahead = [p for p in route
                         if math.hypot(p[0] - pos[0], p[1] - pos[1]) > 0.5]
                if not ahead:
                    break
                if NETWORK.on_the_road(pos):
                    seen += 1
                    node = onramp(pos, station)
                    assert not slants(pos, node), \
                        f"{name}->{station} slants at {pos} to {node}"
                g = ahead[0]
                gap = math.hypot(g[0] - pos[0], g[1] - pos[1])
                pos = (pos[0] + 0.5 * (g[0] - pos[0]) / gap,
                       pos[1] + 0.5 * (g[1] - pos[1]) / gap)
    assert seen > 200, f"only {seen} on-road samples — the sweep is not walking"


# ------------------------------------------- and the driver must not draw one

def test_a_turn_is_not_cut_the_way_a_corner_is():
    """The router plans square and the DRIVER can still slant across it.

    `waypoint_tolerance` is 0.60 m, deliberately loose because "a corner does
    not have to be hit precisely". At a spur mouth that is not a corner to
    round, it is a turn off one line onto another, and letting go 0.60 m early
    aims the robot at the junction on the other lane from atan2(1.80, 0.60) =
    72 degrees instead of 90. The avoidance field widened that to the 60-odd
    degrees measured live on 2026-08-26 16:35 — 13 aims at 5 places, every one
    of them a robot leaving the outer lane for the inner one.
    """
    from csm.adapters.sim_acs import SimRobot

    r = object.__new__(SimRobot)
    x, y = plant.JOINS_OUTER["CTR2_ULD"]

    # Approaching that junction along the outer lane, then turning up the spur.
    r.pose = (x + 2.0, y, 0.0)
    r._waypoints = [(x, y), plant.JOINS_INNER["CTR2_ULD"]]
    assert r._turn_here() is True

    # Carrying straight on along the same lane is a corner, not a turn.
    r._waypoints = [(x, y), (x - 4.0, y)]
    assert r._turn_here() is False


def test_the_turn_tolerance_holds_the_spur_mouth_near_square():
    """The number, so that loosening it later has to argue with the geometry."""
    from csm.adapters.sim_acs import SimRobot

    r = object.__new__(SimRobot)
    r.tolerance = 0.35
    r.waypoint_tolerance = 0.6
    r.turn_tolerance = r.tolerance / 2.0
    angle = math.degrees(math.atan2(plant.LANE_GAP, r.turn_tolerance))
    loose = math.degrees(math.atan2(plant.LANE_GAP, r.waypoint_tolerance))

    assert angle > 80.0, f"a turn off the lane is cut to {angle:.0f} deg"
    assert loose < 75.0, "if the loose tolerance is this tight, drop the rule"
