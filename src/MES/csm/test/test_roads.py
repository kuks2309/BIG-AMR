"""The lane network is clear of every machine, and serves the documented flow.

These tests are the reason roads.py can be trusted: build() raises rather than
returning an obstructed network, and everything below proves the network it does
return actually connects the material flow the customer documents describe.
"""

import math

import pytest

from csm import plant
from csm.adapters import roads


@pytest.fixture
def net():
    return roads.build()


def _clear(p, a, b):
    return roads._clearance(p, a, b)


# ------------------------------------------------------------------ network

def test_network_builds_and_is_connected(net):
    seen, stack = {"aisle_nw"}, ["aisle_nw"]
    while stack:
        for m in net.adjacency[stack.pop()]:
            if m not in seen:
                seen.add(m)
                stack.append(m)
    assert seen == set(net.nodes), "every waypoint must be reachable"


def test_every_dock_is_on_the_network(net):
    for name in plant.DOCKS:
        assert f"dock_{name}" in net.nodes
        assert net.nodes[f"dock_{name}"] == plant.DOCKS[name]


def test_no_lane_passes_through_a_machine(net):
    for (a, b), obstacle, clearance, required in net.report():
        assert clearance >= required, (
            f"lane {a}->{b} passes {obstacle} at {clearance:.2f} m, "
            f"needs {required:.2f} m")


def test_no_waypoint_sits_in_a_wall(net):
    pad = roads.ROBOT_RADIUS + roads.MARGIN
    for name, (x, y) in net.nodes.items():
        assert plant.HALL_W + pad <= x <= plant.HALL_E - pad, f"{name} x={x}"
        assert plant.HALL_S + pad <= y <= plant.HALL_N - pad, f"{name} y={y}"


def test_build_rejects_a_network_with_a_machine_on_a_lane(monkeypatch):
    """An obstructed network must never be returned, only raised."""
    blocked = dict(plant.OBSTACLES)
    blocked["BLOCKER"] = (0.0, plant.AISLE_N_Y)     # straight onto the north aisle
    monkeypatch.setattr(plant, "OBSTACLES", blocked)
    with pytest.raises(roads.UnsafeLane):
        roads.build()


# ------------------------------------------------------------ material flow

def test_every_documented_flow_leg_is_routable(net):
    """Each source -> destination pair in the Big AGV flow must have a route."""
    for segment in plant.SEGMENTS:
        for src in segment["from"]:
            for dst in segment["to"]:
                route = net.route(src, dst)
                assert len(route) >= 2, f"no route {src} -> {dst}"
                assert route[-1] == plant.DOCKS[dst]


def test_no_leg_of_any_flow_route_touches_a_machine(net):
    """The guarantee that matters: no route, anywhere, clips a machine."""
    for segment in plant.SEGMENTS:
        for src in segment["from"]:
            for dst in segment["to"]:
                route = net.route(src, dst)
                for i in range(len(route) - 1):
                    p, q = route[i], route[i + 1]
                    for name, (pos, radius) in net.obstacles.items():
                        # A dock is close to its own machine by design.
                        if name in (_owner(src), _owner(dst)):
                            continue
                        assert _clear(pos, p, q) >= net.required(radius), (
                            f"route {src}->{dst} leg {i} passes {name}")


def _owner(dock):
    for machine in plant.OBSTACLES:
        if dock == machine or dock.startswith(machine + "_"):
            return machine
    return None


@pytest.mark.parametrize("seg", [s["name"] for s in plant.SEGMENTS])
def test_each_robot_can_reach_its_whole_segment_from_its_parking_bay(net, seg):
    start = plant.PARKING[seg]
    segment = next(s for s in plant.SEGMENTS if s["name"] == seg)
    for station in segment["from"] + segment["to"]:
        route = net.route_from(start, station)
        assert len(route) >= 2, f"{seg} cannot reach {station} from parking"


def test_the_hop_from_a_parking_bay_onto_the_network_is_clear(net):
    """The first hop is the one leg no lane check covers, so check it here."""
    for seg, start in plant.PARKING.items():
        node = net.entry_node(start)
        assert net.is_clear(start, net.nodes[node]), (
            f"joining at {node} from {seg}'s parking bay is not clear")


# ------------------------------------------------------- plant / flow model

def test_wait_spots_are_on_the_network(net):
    """A robot backing out must stop somewhere the network actually goes.

    The previous model put wait spots at a sideways offset belonging to no lane,
    so every job ended with the robot leaving the road entirely.
    """
    for name, join in plant.JOINS.items():
        assert net.nodes[f"join_{name}"] == join


def test_every_robot_is_bound_to_a_real_segment():
    """A robot's segment must exist, and no two robots may share one.

    This used to assert every SEGMENT had exactly one robot, which was a
    property of the three-robot demo rather than of the plant: the documented
    line runs 2 + 2 + 6 [S16], so segments have many robots or — while a
    segment's robot is being written — none at all. An unserved segment is a
    fleet-sizing fact, and its jobs simply queue.

    What must never happen is a robot bound to a segment that does not exist
    (it would be offered no work at all and sit idle for ever), or two robots
    silently sharing one leg.
    """
    names = {s["name"] for s in plant.SEGMENTS}
    seen = {}
    for robot, seg in plant.ROBOT_SEGMENT.items():
        assert seg in names, f"{robot} is bound to unknown segment {seg!r}"
        assert seg not in seen, f"{robot} and {seen[seg]} both serve segment {seg}"
        seen[seg] = robot


def test_a_job_outside_the_documented_flow_has_no_segment():
    """ASRS straight to the Slitter is not a leg any AGV class runs."""
    assert plant.segment_for_job("ASRS", "SLT_LD1") is None
    assert plant.segment_for_job("ASRS", "GRV1_LD")["name"] == "A"
    assert plant.segment_for_job("GRV1_ULD", "CTR1_LD")["name"] == "B"
    assert plant.segment_for_job("CTR1_ULD", "SLT_LD1")["name"] == "C"


def test_every_machine_has_separate_load_and_unload_ports():
    """LD and ULD are distinct docking points [IP][PROT], not one station."""
    for i in range(1, 5):
        for fam in ("GRV", "CTR"):
            ld, uld = plant.DOCKS[f"{fam}{i}_LD"], plant.DOCKS[f"{fam}{i}_ULD"]
            assert ld != uld
            assert math.dist(ld, uld) == pytest.approx(2 * plant.PORT_OFFSET)


# ------------------------------------------------ docks are not thoroughfares

def test_a_dock_is_never_used_to_join_the_network(net):
    """A robot must never enter a station it has no job at.

    The planner used another station's dock as an on-ramp: amr2, sent to
    collect from GRV1_ULD, was given a first waypoint of (-17.0, 4.8) — the
    ASRS dock, inside the bay where amr1 was working — and drove into it.
    """
    import random
    rnd = random.Random(0)
    for _ in range(300):
        pos = (rnd.uniform(plant.HALL_W + 1, plant.HALL_E - 1),
               rnd.uniform(plant.HALL_S + 1, plant.HALL_N - 1))
        node = net.entry_node(pos)
        assert not node.startswith(("dock_", "park_")), (
            f"joined the network at {node} from {pos}")


def test_standing_inside_a_bay_still_leaves_by_the_spur(net):
    """Even starting ON a dock, the way out is the spur — not a neighbour's."""
    for name in ("ASRS", "GRV1_ULD", "CTR2_LD"):
        node = net.entry_node(plant.DOCKS[name])
        assert not node.startswith(("dock_", "park_"))


def test_every_port_has_its_own_marker_id():
    ids = [plant.MARKER_IDS[n] for n in plant.DOCKS]
    assert len(set(ids)) == len(ids), "two ports sharing an id is unresolvable"
    assert set(plant.MARKER_IDS) == set(plant.DOCKS)


def test_the_bay_radius_covers_the_whole_spur_but_not_the_aisle():
    """Inside a bay the robot may not turn; on the aisle it must be free to.

    Rotating docked swings a corner 0.468 m further than the flat side into a
    0.229 m gap, so the release point has to be clear of the machine but still
    let the robot turn before it has to travel.
    """
    face = plant.ROW_N_Y - plant.MACHINE_D / 2.0
    marker_to_dock = face - plant.DOCKS["ASRS"][1]
    marker_to_join = face - plant.JOINS["ASRS"][1]
    assert plant.BAY_RADIUS > marker_to_dock, "the dock itself must count as in-bay"
    assert plant.BAY_RADIUS < marker_to_join, "the aisle junction must not"
