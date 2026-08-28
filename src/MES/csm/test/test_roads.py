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
    """Every node reachable from one corner, following lanes THE RIGHT WAY.

    The graph is directed now — two one-way rings — so a walk that ignored
    direction would prove nothing. Starting from a single corner and following
    only outgoing lanes is the real question: can a robot get anywhere from
    anywhere.
    """
    start = "aisle_nw_inner"
    seen, stack = {start}, [start]
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

    Every station now has a junction on BOTH lanes, so a robot turns off the
    one it is already travelling and never crosses the opposing lane to dock.
    """
    for name in plant.DOCKS:
        for ring in ("inner", "outer"):
            node = f"join_{name}_{ring}"
            assert node in net.nodes, f"{name} has no junction on the {ring} lane"
            assert net.nodes[node] == plant.join_for(name, ring)


def test_every_robot_is_bound_to_a_real_segment():
    """A robot's segment must exist, and no two robots may share one.

    This used to assert every SEGMENT had exactly one robot, which was a
    property of the three-robot demo rather than of the plant: the documented
    line runs 2 + 2 + 6 [S16], so segments have many robots or — while a
    segment's robot is being written — none at all. An unserved segment is a
    fleet-sizing fact, and its jobs simply queue.

    Several robots to one leg is the DESIGN, not an accident: the deck gives
    leg C six of them. What must never happen is a robot bound to a segment
    that does not exist — it would be offered no work at all and sit idle for
    ever — or two robots sent to the same parking slot, which is a collision
    rather than a scheduling problem.
    """
    names = {s["name"] for s in plant.SEGMENTS}
    slots = {}
    for robot, seg in plant.ROBOT_SEGMENT.items():
        assert seg in names, f"{robot} is bound to unknown segment {seg!r}"
        slot = plant.parking_for(robot)
        assert slot is not None, f"{robot} has nowhere to park"
        assert slot not in slots, f"{robot} and {slots[slot]} share slot {slot}"
        slots[slot] = robot


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


def test_a_spurs_two_junctions_are_joined_to_each_other():
    """A spur is ONE line, so its inner and outer junctions connect.

    Regression for 2026-08-26. Each station and bay got a junction on both
    rings, but the two were never linked, so a robot standing on the outer
    junction could not step the 1.80 m down its own spur to the inner lane. The
    router sent it round to a corner instead: 25.4 m to reach a node the route
    then passed through anyway.
    """
    network = roads.build()
    spurs = {n.rsplit("_", 1)[0] for n in network.nodes if n.startswith("join_")}
    assert spurs, "no spur junctions at all"
    for stem in sorted(spurs):
        inner, outer = f"{stem}_inner", f"{stem}_outer"
        if inner not in network.nodes or outer not in network.nodes:
            continue
        assert inner in network.adjacency[outer], stem
        assert outer in network.adjacency[inner], stem


def test_leaving_a_dock_never_needs_a_corner_to_turn_round():
    """The whole point of a spur touching both rings.

    Backing out onto the outer lane and continuing down the spur must cost the
    same as the direct route from the dock — otherwise the exit is a trap.
    """
    import math
    network = roads.build()
    for station in ("ASRS", "GRV1_LD"):
        goal = "dock_GRV1_LD" if station == "ASRS" else "dock_ASRS"
        outer = f"join_{station}_outer"
        direct = network._route_nodes(f"dock_{station}", goal)
        viaout = network._route_nodes(outer, goal)
        assert direct and viaout, station

        def span(route):
            return sum(math.hypot(route[i + 1][0] - route[i][0],
                                  route[i + 1][1] - route[i][1])
                       for i in range(len(route) - 1))

        # the exit itself is dock -> outer junction, so the two must add up
        stub = math.hypot(network.nodes[outer][0] - plant.DOCKS[station][0],
                          network.nodes[outer][1] - plant.DOCKS[station][1])
        assert span(viaout) + stub <= span(direct) + 1e-6, station


def test_the_rings_never_touch_each_other_directly():
    """A ring change is a spur, never a hop across at a corner.

    The eight corner cross-links were needed only while the corners were the
    one place a robot could change ring. Every spur joins both rings now, so
    they became a lane change at the worst possible spot — mid-turn, where the
    two rings run closest.
    """
    network = roads.build()
    for tag in ("nw", "ne", "sw", "se"):
        inner, outer = f"aisle_{tag}_inner", f"aisle_{tag}_outer"
        assert outer not in network.adjacency[inner], tag
        assert inner not in network.adjacency[outer], tag


def test_the_road_is_still_strongly_connected_without_them():
    """Removing edges from a one-way network is how you strand a robot."""
    import collections
    network = roads.build()
    road = {n for n in network.nodes if not n.startswith(network.TERMINAL)}

    def reach(adjacency, src):
        seen, queue = {src}, collections.deque([src])
        while queue:
            for nxt in adjacency[queue.popleft()]:
                if nxt in road and nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen

    src = sorted(road)[0]
    assert reach(network.adjacency, src) == road, "some node cannot be reached"
    assert reach(network.reverse, src) == road, "some node cannot reach the rest"

    for node in network.nodes:
        if node.startswith(network.TERMINAL):
            assert set(network.reverse[node]) & road, f"{node} has no way in"
            assert set(network.adjacency[node]) & road, f"{node} has no way out"


def test_a_docked_robot_knows_it_is_on_its_own_spur():
    """The spur runs to the MARKER, not to the dock node.

    Regression for 2026-08-26. A dock node is the approach point; the robot
    carries on 1.15 m past it and stops DOCK_TARGET short of the marker.
    Measuring the spur to the node made every docked robot read as standing
    off the road, so `spur_joins` returned nothing and "leave by your own
    junction" never fired for the one case it matters most.
    """
    import math
    network = roads.build()
    for station in ("SLT_LD1", "SLT_LD2", "GRV1_LD", "ASRS"):
        mx, my, myaw = plant.MARKERS[station]
        # where the robot actually stands once docked
        docked = (mx + math.cos(myaw) * plant.DOCK_TARGET,
                  my + math.sin(myaw) * plant.DOCK_TARGET)
        joins = network.spur_joins(docked)
        assert joins, f"{station}: a docked robot is not on its own spur"
        for j in joins:
            assert station in j, (station, j)


def test_leaving_a_dock_uses_its_own_junction_not_a_neighbours():
    """The failure this was written for.

    amr3 undocked at SLT_LD1, needed CTR1_ULD, and `entry_node_for` chose
    `join_SLT_LD3_outer` — 4.77 m diagonally across the machine row, through
    the bay where amr5 was docking. Both stopped on layer 1 and stayed there.
    """
    import math
    network = roads.build()
    for station, goal in (("SLT_LD1", "dock_CTR1_ULD"),
                          ("SLT_LD2", "dock_CTR1_ULD"),
                          ("GRV1_LD", "dock_ASRS")):
        mx, my, myaw = plant.MARKERS[station]
        docked = (mx + math.cos(myaw) * plant.DOCK_TARGET,
                  my + math.sin(myaw) * plant.DOCK_TARGET)
        chosen = network.entry_node_for(docked, goal)
        assert station in chosen, (station, chosen)


def test_an_onramp_will_not_be_driven_through_another_robot():
    """The first hop is the only leg no lane covers, so nothing else checks it."""
    network = roads.build()
    pos = (-23.28, -6.97)                 # amr3 where it wedged
    blocked = network.entry_node_for(pos, "dock_CTR1_ULD",
                                     [(-21.60, -7.79)])   # amr5 docked
    free = network.entry_node_for(pos, "dock_CTR1_ULD")
    assert blocked != free or free is None, \
        "avoid made no difference where a robot sits on the hop"
    assert network._clear_of_traffic(pos, network.nodes[blocked],
                                     [(-21.60, -7.79)])


def test_a_junction_knows_the_lane_it_sits_on():
    """The merge rule turns on this, so it must be right at every junction.

    A junction's lane axis is the direction of its neighbours ALONG the lane.
    Its two other links — the dead end it serves and the twin junction on the
    other ring — both run ACROSS the lane and must not be mistaken for it.
    """
    network = roads.build()
    for node, (jx, jy) in network.nodes.items():
        if not node.startswith("join_"):
            continue
        stem = node.rsplit("_", 1)[0]
        along = [o for o in set(network.adjacency[node]) | set(network.reverse[node])
                 if not o.startswith(("dock_", "park_"))
                 and o.rsplit("_", 1)[0] != stem]
        assert along, f"{node} has no neighbour along its lane"
        # every one of them must lie on the SAME axis from the junction
        axes = set()
        for o in along:
            ox, oy = network.nodes[o]
            axes.add(0 if abs(ox - jx) > abs(oy - jy) else 1)
        assert len(axes) == 1, (node, axes, along)

        # and the twin junction must lie ACROSS that axis, never along it
        twin = f"{stem}_inner" if node.endswith("_outer") else f"{stem}_outer"
        if twin in network.nodes:
            tx, ty = network.nodes[twin]
            lane_axis = axes.pop()
            across = abs(ty - jy) if lane_axis == 0 else abs(tx - jx)
            assert across > 0.5, (node, twin, across)


def test_a_robot_pausing_out_of_a_dock_keeps_its_body_off_the_road():
    """RULE 2: pausing only helps if you pause somewhere you are not in the way.

    A distance measured to the lane says nothing about where the robot ENDS.
    Measured 2026-08-26 at a flat 1.00 m: amr4 paused exactly where it was
    told, 1.14 m out, with its nose already in the lane, and amr3 drove into
    it — three contacts in six minutes, all in the same 3 m of road.
    """
    from csm.adapters.sim_acs import ROAD_EDGE, STOP_GAP
    reach = plant.ROBOT_L / 2.0          # worst case: length toward the lane
    passing = plant.ROBOT_W / 2.0        # a robot on the lane, flank toward us
    assert ROAD_EDGE >= reach + passing + STOP_GAP - 1e-9, ROAD_EDGE
    assert ROAD_EDGE - reach - passing >= STOP_GAP - 1e-9
