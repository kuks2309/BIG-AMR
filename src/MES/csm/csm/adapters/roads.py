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

    def route_from(self, pos, to_station):
        """Waypoints from an arbitrary point to a station's dock."""
        return self._route_nodes(self.entry_node(pos), f"dock_{to_station}")

    def route_to_node(self, pos, node):
        """Waypoints from an arbitrary point to any named node.

        Parking bays need this. Driving home used to be a straight line at the
        bay, which is the one thing this module exists to prevent — and it also
        put an idle robot on no road at all, where no traffic rule could apply
        to it. Homing is an ordinary trip and takes ordinary roads.
        """
        return self._route_nodes(self.entry_node(pos), node)

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
