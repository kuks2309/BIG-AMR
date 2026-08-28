"""A robot following its own route must arrive.

amr2, delivering to CTR1_LD, drove a closed circuit for over a minute on
2026-08-19: west along y≈2.8, east along y≈1.9, back to the start, repeating.
No fault, no stall, no collision — it simply never arrived.

The cause was `entry_node` answering "which on-ramp is NEAREST", which is the
right question with no destination and the wrong one with a destination.
Nearest is not continuous in position: at (-18.1, +1.9) the nearest node was
`join_ASRS` 1.56 m BEHIND the robot, over `join_parkA` 1.94 m ahead. Re-planning
there turned the robot round, and it drove back to where it would turn round
again.

These tests are about the property, not the corner. A route that is re-planned
as the robot moves must converge.
"""

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm import plant                                            # noqa: E402
from csm.adapters import roads                                   # noqa: E402

NETWORK = roads.build()
STEP = 0.5              # metres advanced per replan — smaller than any lane
LIMIT = 400             # generous: the hall is ~50 m across


def walk(start, station, limit=LIMIT):
    """Follow the plan, re-planning EVERY step, as a nudged robot does.

    Returns the positions visited. Re-planning every step is the worst case and
    the honest one: a give-way, an avoidance push or an arrival all trigger it,
    and the robot has no memory of the plan it had before.
    """
    pos = start
    seen = [pos]
    for _ in range(limit):
        route = NETWORK.route_from(pos, station)
        if not route:
            return seen
        # Drop the waypoints already reached, exactly as the driver's pop loop
        # does. Standing ON a waypoint and re-planning returns it as the first
        # element again, so a model that always steers at route[0] never leaves
        # it — which is a flaw in the model, not in the router.
        ahead = [p for p in route
                 if math.hypot(p[0] - pos[0], p[1] - pos[1]) > STEP]
        if not ahead:
            return seen                          # standing on the dock
        goal = ahead[0]
        gap = math.hypot(goal[0] - pos[0], goal[1] - pos[1])
        pos = (pos[0] + STEP * (goal[0] - pos[0]) / gap,
               pos[1] + STEP * (goal[1] - pos[1]) / gap)
        seen.append(pos)
    return seen


def arrived(seen, station):
    dock = plant.DOCKS[station]
    return math.hypot(dock[0] - seen[-1][0], dock[1] - seen[-1][1]) < 3.0


# ------------------------------------------------------ the observed failure

def test_the_position_that_turned_amr2_round():
    """(-18.1, +1.9) heading for CTR1_LD. It planned backwards."""
    # Measured at (-18.1, +1.9) when the west aisle was x -20.0, i.e. 1.9 m
    # east of it. Kept relative so a layout change moves the case with the
    # layout instead of silently testing a different spot.
    route = NETWORK.route_from((plant.AISLE_W_X + 1.9, 1.9), "CTR1_LD")
    assert route[0][1] < 2.5, \
        f"first hop {route[0]} goes back north to the lane it just left"


def test_amr2_now_reaches_ctr1_ld_from_every_point_on_its_circuit():
    for pos in [(-17.2, 2.8), (-18.4, 2.7), (-19.6, 2.9), (-19.6, 1.8),
                (-18.5, 1.9), (-18.1, 1.9), (-17.9, 2.3)]:
        seen = walk(pos, "CTR1_LD")
        assert arrived(seen, "CTR1_LD"), \
            f"from {pos}: {len(seen)} steps and still not there"


# ------------------------------------------------------------ the property

def test_replanning_every_step_still_converges():
    """The general case. Every station, from every parking bay."""
    starts = [plant.parking_for(n) for n in plant.ROBOT_SEGMENT]
    for station in sorted(plant.DOCKS):
        for start in starts:
            seen = walk(start, station)
            assert arrived(seen, station), \
                f"{start} -> {station}: gave up after {len(seen)} steps"


def test_no_route_revisits_a_place_it_has_already_left():
    """A cycle IS the bug. Anything that returns to within half a metre of
    somewhere it stood ten steps ago is going round."""
    for station in ("CTR1_LD", "SLT_LD1", "GRV1_LD", "ASRS"):
        for start in [plant.parking_for(n) for n in plant.ROBOT_SEGMENT]:
            seen = walk(start, station)
            for i, here in enumerate(seen):
                for there in seen[i + 12:]:
                    # 12 steps is 6 m of travel. Coming back within 0.4 m of
                    # where you were is not a corner, it is a circuit.
                    assert math.hypot(here[0] - there[0],
                                      here[1] - there[1]) > 0.4, \
                        f"{start} -> {station} revisits {here}"


def _metres(route):
    return sum(math.hypot(route[i + 1][0] - route[i][0],
                          route[i + 1][1] - route[i][1])
               for i in range(len(route) - 1))


#: A nudge may legitimately cost this much and no more: HALF A LAP.
#:
#: MEASURED IN METRES, NOT HOPS. Hops were the right unit on a two-way road,
#: where a metre sideways barely changed the plan. The lanes are 1.20 m apart
#: and run OPPOSITE ways, so a 1 m nudge can put the robot on the lane going
#: the other way — and if the destination is behind it, the honest route is
#: most of the way round. Measured worst: 35.8 m, at (10.65, +4.20) nudged
#: north off the westbound lane with GRV1_ULD behind it.
#:
#: Half the ring is the line that separates "crossed to the other lane", which
#: is the road working, from "planned a lap it did not need", which is a bug.
#: A full lap of this rectangle is about 120 m.
NUDGE_ALLOWANCE = (plant.AISLE_E_X - plant.AISLE_W_X) + \
                  (plant.AISLE_N_Y - plant.AISLE_S_Y)


def test_a_nudge_sideways_does_not_reverse_the_plan():
    """Avoidance and docking both leave a robot a metre off the lane.
    Neither may turn the journey round."""
    for station in ("CTR1_LD", "SLT_LD1", "GRV1_ULD"):
        for start in [plant.parking_for(n) for n in plant.ROBOT_SEGMENT]:
            for pos in walk(start, station)[:40]:
                straight = NETWORK.route_from(pos, station)
                if len(straight) < 2:
                    continue
                for dx, dy in ((1.0, 0), (-1.0, 0), (0, 1.0), (0, -1.0)):
                    nudged = (pos[0] + dx, pos[1] + dy)
                    after = NETWORK.route_from(nudged, station)
                    if not after:
                        continue
                    added = _metres(after) - _metres(straight)
                    assert added <= NUDGE_ALLOWANCE, \
                        (f"a 1 m nudge at {pos} toward {station} added "
                         f"{added:.1f} m — that is going round, not across")


# --------------------------------------------- and the first hop stays short

def test_the_off_lane_hop_stays_short():
    """The on-ramp is the ONE leg no lane covers, so it must not grow.

    A draft allowed 5 m of detour and picked a node 5.3 m away diagonally
    across an aisle over one 0.5 m away, because it saved a little lane
    distance. Trading off-lane metres for lane metres one-for-one is exactly
    what this module exists to refuse — a clear line is clear of MACHINES, not
    of other robots.

    THE BOUND IS NOW ABSOLUTE, AND LOOSER, AND THAT IS A REAL COST. It used to
    be "no more than 1.5 m further than the nearest candidate". That window
    slides with the robot and closes to nothing when it is almost standing on a
    junction, so the genuinely cheapest on-ramp dropped in and out of range and
    the plan alternated: 88 of 270 routes never arrived on the two-lane road.
    Swept against the harness, only a cap of 6 m converged — 3.0 and 4.5 both
    left 88 stranded.

    What that buys in convergence it spends here. Measured over 10,002
    samples: median hop 4.15 m, 90th 5.66 m, worst 6.00 m, where the old rule
    kept almost everything under 2 m. Robots now cross open floor to join a
    lane more often than they used to, and that floor is where no traffic rule
    applies. This test records the number rather than asserting the old one, so
    the cost is visible instead of forgotten.
    """
    starts = [plant.parking_for(n) for n in plant.ROBOT_SEGMENT]
    starts += [(-18.1, 1.9), (-17.2, 2.8), (0.0, 0.0), (10.0, -2.0)]
    worst = 0.0
    for station in sorted(plant.DOCKS):
        for start in starts:
            for pos in walk(start, station)[:30]:
                node = NETWORK.entry_node_for(pos, f"dock_{station}")
                hop = math.hypot(NETWORK.nodes[node][0] - pos[0],
                                 NETWORK.nodes[node][1] - pos[1])
                worst = max(worst, hop)
                assert hop <= NETWORK.MAX_ONRAMP + 1e-6, (
                    f"at {pos} the on-ramp is {hop:.1f} m, over the "
                    f"{NETWORK.MAX_ONRAMP:.1f} m limit")
    assert worst > 3.0, (
        "if the worst on-ramp has dropped below 3 m the cap can come down "
        "again — re-run the convergence sweep before lowering it")


def test_the_on_ramp_is_never_a_dock_or_a_parking_bay():
    """The old rule that stopped a robot driving into a bay it has no job at.
    Choosing by total cost must not have quietly dropped it."""
    for station in sorted(plant.DOCKS):
        for start in [plant.parking_for(n) for n in plant.ROBOT_SEGMENT]:
            node = NETWORK.entry_node_for(start, f"dock_{station}")
            assert not node.startswith(NETWORK.TERMINAL), \
                f"{node} is a dock or bay and must never be an on-ramp"


def test_homing_routes_also_converge():
    """`route_to_node` takes the same on-ramp choice, so it inherits both the
    bug and the fix."""
    for name in plant.ROBOT_SEGMENT:
        node = roads.park_node(name)
        for start in [(-18.1, 1.9), (0.0, 0.0), (20.0, -2.0)]:
            route = NETWORK.route_to_node(start, node)
            assert route, f"{name} cannot route home from {start}"
            assert route[-1] == plant.parking_for(name)
