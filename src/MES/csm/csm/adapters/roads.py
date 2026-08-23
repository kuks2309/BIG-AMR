"""roads — the lane network robots are allowed to drive on.

WHY THIS EXISTS. A robot that drives straight at its goal commits to the line:
the avoidance field is capped BELOW the goal attraction on purpose, and fades to
zero near the goal so the robot can dock. A machine standing on that line is
therefore driven into, not routed around. Measured on the old invented layout,
three of fifteen station pairs ran through something solid, and robots were
observed hitting a pillar and coming to rest against a machine.

WHAT THIS IS. Aisles and spurs, built from plant.py, with every lane checked
against every solid body at build time. build() RAISES rather than returning a
network containing an obstructed lane.

The shape follows the customer's own AGV route map (system deck slide 39): long
parallel aisles with short perpendicular spurs combing off them to each docking
port. It is not a ring around an open floor — that was an invention of the
earlier model, and the real plant does not look like it.

This module owns geometry only and imports nothing from sim_acs, so sim_acs can
depend on it without a cycle.
"""

import math

from .. import plant

#: Effective radius of the robot for lane clearance. The chassis is 1.6 x 0.9,
#: so a full half-diagonal is 0.92 m — right for a robot at an arbitrary yaw and
#: too conservative here, because the platform crabs and holds yaw. 0.70 sits
#: between the half-width and that worst case.
ROBOT_RADIUS = 0.70

#: Machines are MACHINE_W x MACHINE_D boxes; circumscribed radius.
MACHINE_RADIUS = math.hypot(plant.MACHINE_W, plant.MACHINE_D) / 2.0

#: Slack on top of the two radii, absorbing lane-following error.
MARGIN = 0.30


def _clearance(p, a, b):
    """Distance from point p to segment a-b."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    span = dx * dx + dy * dy
    if span < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / span))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class UnsafeLane(Exception):
    """A lane passes too close to something solid. Raised, never returned."""


class Roads:
    def __init__(self, nodes, lanes, obstacles, dock_owner):
        self.nodes = nodes                # name -> (x, y)
        self.lanes = lanes                # [(name_a, name_b)]
        self.obstacles = obstacles        # name -> ((x, y), radius)
        self.dock_owner = dock_owner      # dock node -> the machine it serves
        self.adjacency = {n: set() for n in nodes}
        for a, b in lanes:
            self.adjacency[a].add(b)
            self.adjacency[b].add(a)

    def required(self, obstacle_radius):
        return ROBOT_RADIUS + obstacle_radius + MARGIN

    def report(self):
        """(lane, obstacle, clearance, required), worst first."""
        rows = []
        for a, b in self.lanes:
            pa, pb = self.nodes[a], self.nodes[b]
            for oname, (opos, orad) in self.obstacles.items():
                # EXACTLY ONE exemption: the spur that serves this machine, on
                # its final hop. A dock is deliberately close to the thing it
                # docks against — that is what docking is. Nothing else is
                # excused; an earlier version exempted a station from every lane
                # whose name began with it, which silently excused the very leg
                # that could run alongside the machine it served.
                if self.dock_owner.get(b) == oname or self.dock_owner.get(a) == oname:
                    continue
                rows.append(((a, b), oname, _clearance(opos, pa, pb),
                             self.required(orad)))
        rows.sort(key=lambda r: r[2] - r[3])
        return rows

    def check(self):
        bad = [r for r in self.report() if r[2] < r[3]]
        if bad:
            lines = [f"  {a}->{b}: {o} at {c:.2f} m, needs {q:.2f} m"
                     for (a, b), o, c, q in bad[:12]]
            raise UnsafeLane(f"{len(bad)} obstructed lane(s):\n" + "\n".join(lines))
        return self

    def is_clear(self, a, b, ignore=()):
        for name, (pos, radius) in self.obstacles.items():
            if name in ignore:
                continue
            if _clearance(pos, a, b) < self.required(radius):
                return False
        return True

    #: Nodes that are DEAD ENDS: you go there to be served and reverse out the
    #: way you came. Never somewhere to pass through, and never somewhere to
    #: join the road.
    TERMINAL = ("dock_", "park_")

    def entry_node(self, pos):
        """Cheapest waypoint to join the network from an arbitrary point.

        A robot is not always on a lane — it starts on a parking bay and it
        finishes wherever its last job left it. That first hop is the one leg no
        lane check covers, so prefer the nearest node reachable in a straight
        line.

        DOCKS AND PARKING BAYS ARE EXCLUDED. They were not, and the planner
        happily used another station's dock as an on-ramp: amr2, sent to collect
        from GRV1_ULD, was given a first waypoint of (-17.0, 4.8) — the ASRS
        dock, 1.8 m up a spur, inside the bay where amr1 was working. It drove
        in and hit it; closest approach 0.92 m between two robots 0.9 m wide,
        which is contact.

        A robot must never enter a station it has no job at. Joining the network
        on an aisle or at a spur junction makes that structural rather than a
        rule someone has to remember.
        """
        order = sorted((n for n in self.nodes if not n.startswith(self.TERMINAL)),
                       key=lambda n: math.hypot(self.nodes[n][0] - pos[0],
                                                self.nodes[n][1] - pos[1]))
        for name in order:
            if self.is_clear(pos, self.nodes[name]):
                return name
        return order[0]

    #: How much further than the NEAREST on-ramp we will walk to avoid one
    #: that points the wrong way.
    #:
    #: THE FIRST HOP IS THE ONLY LEG NO LANE COVERS, so it must stay short.
    #: This is the distance between two junctions on one corner — enough to
    #: swap `join_ASRS` for `join_parkA`, which is the flip that produced the
    #: loop — and no more.
    #:
    #: It was 5.0 for one draft and that was worse than the bug. From
    #: (-19.6, +1.8) it chose an on-ramp 5.3 m away diagonally across the
    #: aisle, over one 0.5 m away, because the far one saved a few metres of
    #: lane. Trading lane metres for off-lane metres one-for-one is exactly
    #: what this module exists to refuse: a clear straight line is clear of
    #: MACHINES, not of other robots, and lanes are where the traffic rules
    #: apply.
    ENTRY_DETOUR = 1.5



    def entry_node_for(self, pos, goal):
        """The on-ramp that minimises the WHOLE trip, not just the first hop.

        `entry_node` answers "what is nearest", which is the right question
        when there is no destination yet and the WRONG one when there is.
        Nearest is not continuous in position: a robot that moves a metre can
        find a different node nearest, and if that node lies BEHIND it the new
        route begins by going back the way it came.

        Observed 2026-08-19. amr2, delivering to CTR1_LD, at (-18.1, +1.9):

            join_ASRS   (-17.0, +3.0)   1.56 m away, 10 hops — back north-east
            join_parkA  (-20.0, +1.5)   1.94 m away,  8 hops — onward, south

        Nearest chose `join_ASRS`, so the route reversed. The robot drove back
        up to the corner, re-planned, came south again, and repeated: a closed
        circuit, west along y≈2.8 and east along y≈1.9, indefinitely. Nothing
        was broken — no fault, no stall, no collision — it simply never
        arrived, which is the hardest kind of failure to see.

        Total cost is continuous in position, so it cannot flip like that: an
        on-ramp only wins by saving more than the walk to it costs.
        """
        reach = self._distances_to(goal)
        if not reach:
            return self.entry_node(pos)

        candidates = sorted(
            (n for n in self.nodes if not n.startswith(self.TERMINAL)),
            key=lambda n: math.hypot(self.nodes[n][0] - pos[0],
                                     self.nodes[n][1] - pos[1]))
        nearest = None
        best, best_cost = None, float("inf")
        for name in candidates:
            hop = math.hypot(self.nodes[name][0] - pos[0],
                             self.nodes[name][1] - pos[1])
            if nearest is not None and hop > nearest + self.ENTRY_DETOUR:
                break                    # sorted, so nothing later is closer
            if name not in reach:
                continue                 # cannot get to the goal from there
            if not self.is_clear(pos, self.nodes[name]):
                continue                 # the one leg no lane covers
            if nearest is None:
                nearest = hop
            cost = hop + reach[name]
            if cost < best_cost:
                best, best_cost = name, cost
        # Falling back to `entry_node` rather than to nothing: it applies the
        # same clearance and exclusion rules and is never worse than refusing
        # to plan at all.
        return best if best is not None else self.entry_node(pos)

    def _distances_to(self, goal):
        """Shortest path cost from every node to `goal`.

        One Dijkstra instead of one per candidate on-ramp. The lane graph is
        undirected — `build()` adds each lane once and `adjacency` carries both
        directions — so distances measured FROM the goal are the distances TO
        it.
        """
        if goal not in self.nodes:
            return {}
        dist = {goal: 0.0}
        unvisited = set(self.nodes)
        while unvisited:
            here = min((n for n in unvisited if n in dist),
                       key=lambda n: dist[n], default=None)
            if here is None:
                break
            unvisited.discard(here)
            hx, hy = self.nodes[here]
            for nxt in self.adjacency[here]:
                if nxt not in unvisited:
                    continue
                nx, ny = self.nodes[nxt]
                cost = dist[here] + math.hypot(nx - hx, ny - hy)
                if cost < dist.get(nxt, float("inf")):
                    dist[nxt] = cost
        return dist

    def route_from(self, pos, to_station):
        """Waypoints from an arbitrary point to a station's dock."""
        goal = f"dock_{to_station}"
        return self._forward_of(
            pos, self._route_nodes(self.entry_node_for(pos, goal), goal))

    def _forward_of(self, pos, route):
        """Drop leading waypoints the robot has already gone past.

        The driver pops a reached waypoint and never sees it again. A re-plan
        has no such memory: it recomputes from the current position and can
        hand back the junction just passed as the next thing to drive to. The
        robot turns round for a corner it has already turned, crosses back, and
        gets the same answer — a perfect oscillation either side of the node.
        Observed 0.5 m each way around `join_parkA`.

        DISTANCE CANNOT DECIDE THIS. "Half a metre from the junction" is true
        just before it and just after, and the two need opposite answers. So
        the test is not how far away the waypoint is, but whether it is on the
        way: **going via it must not be a detour**. If the robot is already at
        least as close to the NEXT waypoint as this one is, then this one is
        behind, and steering at it means going backwards.

        Scale-free, so there is no tolerance to tune and nothing to keep in
        step with the driver's own. Fixed here rather than in the driver so
        every caller gets a route that is safe to re-plan, instead of each one
        having to remember.

        The goal itself is never dropped: arriving is the driver's decision.
        """
        while len(route) > 1:
            here, nxt = route[0], route[1]
            to_next = math.hypot(nxt[0] - pos[0], nxt[1] - pos[1])
            via_next = math.hypot(nxt[0] - here[0], nxt[1] - here[1])
            if to_next > via_next:
                break                    # the waypoint is genuinely ahead
            route = route[1:]
        return route

    def route_to_node(self, pos, node):
        """Waypoints from an arbitrary point to any named node.

        Parking bays need this. Driving home used to be a straight line at the
        bay, which is the one thing this module exists to prevent — and it also
        put an idle robot on no road at all, where no traffic rule could apply
        to it. Homing is an ordinary trip and takes ordinary roads.
        """
        return self._forward_of(
            pos, self._route_nodes(self.entry_node_for(pos, node), node))

    def route(self, from_station, to_station):
        return self._route_nodes(f"dock_{from_station}", f"dock_{to_station}")

    def _route_nodes(self, start, goal):
        if start not in self.nodes or goal not in self.nodes:
            return []
        dist, prev = {start: 0.0}, {}
        unvisited = set(self.nodes)
        while unvisited:
            here = min((n for n in unvisited if n in dist),
                       key=lambda n: dist[n], default=None)
            if here is None or here == goal:
                break
            unvisited.discard(here)
            hx, hy = self.nodes[here]
            for nxt in self.adjacency[here]:
                if nxt not in unvisited:
                    continue
                nx, ny = self.nodes[nxt]
                cost = dist[here] + math.hypot(nx - hx, ny - hy)
                if cost < dist.get(nxt, float("inf")):
                    dist[nxt], prev[nxt] = cost, here
        if goal not in dist:
            return []
        chain, node = [], goal
        while node != start:
            chain.append(node)
            node = prev[node]
        chain.append(start)
        chain.reverse()
        return [self.nodes[n] for n in chain]


def park_node(robot_name):
    """The graph node for this robot's OWN parking slot, or None.

    The NAME is built here because `build()` builds it — slot 0 keeps the
    historic `park_A` and later slots take `park_A2`, `park_A3`. A caller
    spelling that rule out for itself is a caller that will eventually spell it
    differently, and the failure is a route to a node that does not exist.

    Which slot a robot owns comes from `plant.parking_index`, so the node and
    the coordinates `plant.parking_for` returns cannot drift apart.
    """
    segment, index = plant.parking_index(robot_name)
    if segment is None or index >= len(plant.PARKING_SLOTS[segment]):
        return None
    return f"park_{segment}" + ("" if index == 0 else str(index + 1))


def park_node_at(position, tolerance=0.05):
    """The `park_*` node standing at these coordinates, or None.

    A charger IS a parking slot, so a robot sent to charge is sent to some
    slot's node — usually not its own. `park_node` answers "where does THIS
    robot live"; this answers "what is the node at that place", which is the
    question once the two stop being the same.
    """
    for segment, slots in plant.PARKING_SLOTS.items():
        for i, slot in enumerate(slots):
            if (abs(slot[0] - position[0]) <= tolerance
                    and abs(slot[1] - position[1]) <= tolerance):
                return f"park_{segment}" + ("" if i == 0 else str(i + 1))
    return None


def build():
    """The checked lane network for the plant. Raises UnsafeLane if obstructed."""
    obstacles = {n: (pos, MACHINE_RADIUS) for n, pos in plant.OBSTACLES.items()}

    nodes, lanes, dock_owner = {}, [], {}

    # Aisle corners.
    corners = {
        "aisle_nw": (plant.AISLE_W_X, plant.AISLE_N_Y),
        "aisle_ne": (plant.AISLE_E_X, plant.AISLE_N_Y),
        "aisle_sw": (plant.AISLE_W_X, plant.AISLE_S_Y),
        "aisle_se": (plant.AISLE_E_X, plant.AISLE_S_Y),
    }
    nodes.update(corners)

    # A spur per dock, dropping perpendicularly onto its own aisle.
    joins = {"N": [], "S": [], "W": [], "E": []}
    for name, (dx, dy) in plant.DOCKS.items():
        aisle_y = plant.AISLE_N_Y if dy > 0 else plant.AISLE_S_Y
        jn, dn = f"join_{name}", f"dock_{name}"
        nodes[jn] = (dx, aisle_y)
        nodes[dn] = (dx, dy)
        lanes.append((jn, dn))
        joins["N" if dy > 0 else "S"].append(jn)
        dock_owner[dn] = _owner_of(name)
        dock_owner[jn] = None

    # Parking spurs hang off the cross aisles, never on them.
    #
    # ONE SPUR PER QUEUE SLOT, not one per leg. A leg has as many slots as it
    # has robots (plant.FLEET), because a bay shared by two robots means two
    # robots sent to identical coordinates.
    #
    # No new lane type is needed: `_chain` below links everything sitting on an
    # aisle in order along it, so a spur further out simply EXTENDS that aisle.
    # That is what lets the queue grow past the aisle corners.
    #
    # Slot 0 keeps the historic names `join_parkA` / `park_A`, so anything that
    # only ever knew about one bay per leg still resolves.
    for seg, slots in plant.PARKING_SLOTS.items():
        for i, pos in enumerate(slots):
            suffix = "" if i == 0 else str(i + 1)
            jn, pn = f"join_park{seg}{suffix}", f"park_{seg}{suffix}"
            nodes[jn] = plant.PARKING_JOIN_SLOTS[seg][i]
            nodes[pn] = pos
            lanes.append((jn, pn))
            joins["W" if pos[0] < 0 else "E"].append(jn)

    # Chain each aisle through every node that sits on it, in order, so the
    # graph is connected at every junction instead of only at the corners.
    lanes += _chain(nodes, ["aisle_nw"] + joins["N"] + ["aisle_ne"], axis=0)
    lanes += _chain(nodes, ["aisle_sw"] + joins["S"] + ["aisle_se"], axis=0)
    lanes += _chain(nodes, ["aisle_nw"] + joins["W"] + ["aisle_sw"], axis=1)
    lanes += _chain(nodes, ["aisle_ne"] + joins["E"] + ["aisle_se"], axis=1)

    return Roads(nodes, lanes, obstacles, dock_owner).check()


def _owner_of(dock_name):
    """The solid machine a dock belongs to, so its own spur may approach it."""
    for machine in plant.OBSTACLES:
        if dock_name == machine or dock_name.startswith(machine + "_"):
            return machine
    return None


def _chain(nodes, names, axis):
    """Link nodes lying on one aisle in order along `axis` (0 = x, 1 = y)."""
    ordered = sorted(set(names), key=lambda n: nodes[n][axis])
    return [(ordered[i], ordered[i + 1]) for i in range(len(ordered) - 1)]
