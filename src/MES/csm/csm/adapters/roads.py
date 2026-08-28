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
        # DIRECTED. A lane is (from, to) and may only be driven that way.
        #
        # It was undirected, which was right when every aisle carried traffic
        # both ways. With two one-way lanes the direction IS the road: an
        # undirected graph would happily route a robot the wrong way up a lane
        # and put it head-on into everything using it properly.
        #
        # A spur is entered as two lanes, one each way, so a dead end still
        # works in both directions without a special case here.
        self.adjacency = {n: set() for n in nodes}
        #: The same graph with every lane reversed. `_distances_to` needs
        #: distance TO a goal, and walking the forward graph outward from the
        #: goal gives distance FROM it — the same number only while the graph
        #: is undirected, which it no longer is.
        self.reverse = {n: set() for n in nodes}
        for a, b in lanes:
            self.adjacency[a].add(b)
            self.reverse[b].add(a)

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

    def _through(self, node, goal):
        """May a route pass THROUGH this node on the way to `goal`?

        A dock or a parking bay is somewhere to arrive, never somewhere to cut
        through. Both lanes reach every station, so a dock now sits between two
        junctions and a shortest path would happily use it as a shortcut from
        one ring to the other — driving into a station the robot has no job at,
        which is exactly what `entry_node` refuses to do on the way in.
        """
        return node == goal or not node.startswith(self.TERMINAL)

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
        own = self.spur_join(pos)
        if own is not None:
            return own

        order = sorted((n for n in self.nodes if not n.startswith(self.TERMINAL)),
                       key=lambda n: math.hypot(self.nodes[n][0] - pos[0],
                                                self.nodes[n][1] - pos[1]))
        for name in order:
            if self.is_clear(pos, self.nodes[name]):
                return name
        return order[0]

    def spur_join(self, pos):
        """The junction of the spur this point is ON, or None if it is not on one.

        A ROBOT LEAVES BY ITS OWN JUNCTION, NEVER A NEIGHBOUR'S.

        `entry_node` below picks the nearest node reachable in a straight line,
        which is right for a robot standing in open aisle and wrong for one
        standing in a bay. Parking slots are 2.15 m apart and their junctions
        2.15 m apart too, so from slot C3 the nearest reachable node can easily
        be C2's junction or the aisle beyond it — and the straight line to
        either one crosses slot C2.

        Measured 2026-08-25: amr5 leaving leg C slot 3 at (29.14, -5.80) was
        given a first waypoint of (26.64, -3.60) — the aisle, 2.2 m north — so
        it drove diagonally across slot C2 and into amr4, which was parked
        there. Body gap 0.00 m. `entry_node` reported `join_parkC2` as the
        on-ramp for a robot whose own spur was C3.

        This is the same structural fix the docstring below already argues for
        with docks: a robot must never enter a bay it has no business in, and
        making the on-ramp its OWN junction is what makes that structural rather
        than a rule somebody has to remember.
        """
        found = self.spur_joins(pos)
        return found[0] if found else None

    def ring_at(self, pos, tolerance=None):
        """Which ring this point is travelling on, or None if it is off both.

        Measured against the lane LINES rather than the nodes, so a robot
        between two junctions still counts as being on its lane.
        """
        if tolerance is None:
            tolerance = ROBOT_RADIUS
        best, best_d = None, tolerance
        for (ring, _side), (axis, value) in plant.LANE_LINE.items():
            d = abs(pos[1] - value) if axis == "y" else abs(pos[0] - value)
            if d < best_d:
                best, best_d = ring, d
        return best

    def on_the_road(self, pos):
        """Is this point on the ROADWAY — either lane, or the strip between?

        `ring_at` answers "which lane am I travelling on", and between the two
        lanes of one aisle the honest answer is neither: they are `LANE_GAP`
        = 1.80 m apart, so at the midpoint a robot is 0.90 m from each line and
        outside ROBOT_RADIUS of both.

        THAT DEAD BAND IS 1.80 m WIDE AND IT CROSSES EVERY SPUR MOUTH IN THE
        PLANT. A robot half way from one lane to the other is on nothing, so
        nothing constrains its next plan, and it is free to invent a diagonal
        from there. Measured 2026-08-26 at (-3.36,-3.60), the middle of the
        CTR2_ULD spur: `spur_joins` empty, `ring_at` None.

        This is the question the on-ramp rule actually needs: not "which lane"
        but "am I on the road at all", because a robot on the road follows the
        lines and one in open floor has to get to them.
        """
        for side in ("north", "south", "west", "east"):
            axis, inner = plant.LANE_LINE[("inner", side)]
            _, outer = plant.LANE_LINE[("outer", side)]
            here = pos[0] if axis == "x" else pos[1]
            lo, hi = min(inner, outer), max(inner, outer)
            if lo - ROBOT_RADIUS <= here <= hi + ROBOT_RADIUS:
                return True
        return False

    def spur_joins(self, pos):
        """EVERY junction of the spur this point is on — one per ring.

        A spur now meets both lanes, so "leave by your own junction" has two
        answers and only the caller with a destination can choose between them.
        Choosing wrongly is not a longer route, it is no route at all: the
        parking spurs extend the cross aisle PAST the corner, and on a one-way
        lane that is a dead end. Measured on the first two-ring build, seven of
        ten robots could not leave their bay because the inner junction was
        picked and the inner lane there runs away from everything.
        """
        out = []
        for a, b in self.lanes:
            tip, join = (a, b) if a.startswith(self.TERMINAL) else (b, a)
            if not tip.startswith(self.TERMINAL) or join in out:
                continue
            end = self._spur_end(tip)
            jx, jy = self.nodes[join]
            if math.hypot(end[0] - pos[0], end[1] - pos[1]) >= \
                    math.hypot(jx - pos[0], jy - pos[1]):
                continue                      # nearer the junction: already out
            if _clearance(pos, end, (jx, jy)) < ROBOT_RADIUS:
                out.append(join)              # standing on this spur
        return out

    def _spur_end(self, tip):
        """The far end of a spur — where the road really stops.

        NOT the dock node. A dock node is the APPROACH point; the robot carries
        on past it to the marker and stands `DOCK_TARGET` short of that, which
        is 1.15 m further down the spur. Measuring the spur to the node made
        every docked robot look as though it were standing off the road:

            amr3 docked at SLT_LD1, (-24.00,-7.75)
                clearance to dock->junction segment   1.150 m   -> not a spur
                clearance to marker->junction segment 0.000 m   -> dead on it

        So `spur_joins` returned nothing for it, "leave by your own junction"
        never fired, and `entry_node_for` was free to pick an on-ramp two
        stations east — 4.77 m diagonally across the machine row, through the
        bay where amr5 was docking. Both robots stopped on layer 1 and stayed
        stopped. Measured 2026-08-26.

        A parking bay has no marker and no standoff: the robot stops on the
        node, so the node is the end.
        """
        if tip.startswith("dock_"):
            station = tip[len("dock_"):]
            marker = plant.MARKERS.get(station)
            if marker is not None:
                return (marker[0], marker[1])
        return self.nodes[tip]

    #: The longest first hop we will accept, ABSOLUTELY.
    #:
    #: It was measured relative to the NEAREST candidate — "no more than
    #: ENTRY_DETOUR further than the closest on-ramp". That window slides with
    #: the robot, and when the robot is almost standing on a junction the
    #: window closes to nothing: measured 2026-08-26, a robot 0.19 m from
    #: `join_parkB2_inner` could not even see `aisle_ne_outer` 1.80 m away,
    #: which was the genuinely cheapest route. Half a metre later the window
    #: opened and the plan reversed. It alternated for ever, and 88 of 270
    #: routes never arrived.
    #:
    #: The requirement was always absolute — THE FIRST HOP IS THE ONLY LEG NO
    #: LANE COVERS, so it must stay short — and an absolute limit cannot slide.
    #: MEASURED, NOT CHOSEN. Swept against the convergence harness — every
    #: robot, every station, replanning every half metre:
    #:
    #:     cap 3.0  ->  88 of 270 routes never arrive
    #:     cap 4.5  ->  88
    #:     cap 6.0  ->   0
    #:
    #: The cap has to comfortably exceed the longest USEFUL hop, which here is
    #: the reach to a corner from between two junctions, about 3 m. Set at or
    #: just above that and the best candidate drops in and out of range as the
    #: robot moves — measured at 3.01 m one tick and 2.53 m the next, and the
    #: two candidates either side of the boundary point opposite ways round a
    #: one-way ring.
    #:
    #: Weighting off-lane metres more heavily was tried at the same time and
    #: made it worse, not better: 55 of 270 at weight 2, 88 at weight 3.
    MAX_ONRAMP = 6.0

    #: Two on-ramps whose total cost differs by less than this are a tie, and
    #: are settled by which is nearer the goal rather than by which is nearer
    #: the robot. Half a step, so a single replan cannot cross it.
    TIE_BREAK = 0.75

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



    def entry_node_for(self, pos, goal, avoid=()):
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
        # ON A SPUR, THE JUNCTION IS NOT A CHOICE. Cost comparison is the right
        # question for a robot in open aisle and the wrong one in a bay: the
        # cheapest on-ramp from slot C3 is the aisle 2.2 m north, and the
        # straight line to it crosses slot C2. See `spur_join`.
        reach = self._distances_to(goal)

        # ON A SPUR: one of its junctions, whichever can actually get there.
        own = self.spur_joins(pos)
        if own:
            usable = [j for j in own if j in reach]
            if usable:
                return min(usable, key=lambda j: reach[j])
            # NONE OF THEM CAN GET THERE — fall through to the general search.
            #
            # Leaving by your own junction is a PREFERENCE, and returning an
            # unreachable one strands the robot. It happens part way along a
            # spur: once the robot is past the outer junction, only the inner
            # one still counts as "its spur", and on the parking spurs the
            # inner lane runs away from everything. Measured on the first
            # two-ring build: a robot 1 m out of leg C slot 2 got no route at
            # all to the ASRS and stopped where it stood.
            pass

        if not reach:
            return self.entry_node(pos)

        # THE ON-RAMP IS THE ONE LEG NO LANE COVERS, so it is also the one leg
        # no lane has cleared of traffic. `is_clear` keeps it off the machines;
        # nothing kept it off other robots, and up to MAX_ONRAMP metres of open
        # floor in the machine row is exactly where robots stand docked.
        #
        # Tried without `avoid` first is wrong and tried with it only is worse:
        # refusing every candidate strands the robot, and a route it cannot
        # drive yet is better than no route, because layer 1 still stops it.
        # So: prefer a clear hop, fall back to the best one if none is clear.
        # A ROBOT ON THE ROAD REJOINS IT ALONG A LINE, NOT AT AN ANGLE, AND
        # NOT BACKWARDS. See `_along_a_line` and `_with_the_traffic`.
        #
        # Squareness is tried before traffic avoidance, not after: rule 1 is
        # structural and traffic is dynamic, and a square hop that meets a
        # robot is layer 1's problem, which it is equipped for. It is also
        # rarer than it was — an on-ramp that runs along a lane or straight up
        # a spur is far less likely to cross the open floor where robots stand
        # docked, which is what `avoid` was added for.
        #
        # Unconstrained is still tried before giving up: a route the robot must
        # slant onto beats no route. Measured over the convergence harness,
        # 8,065 on-ramp choices, that fallback fires at two positions in the
        # whole plant, both of them "just nosed past the junction I want" —
        # 0.72 m and 0.92 m back, and the driver's `_forward_of` drops a
        # waypoint that far behind it anyway.
        for square in (self.on_the_road(pos), False):
            for blocked in (avoid, ()):
                found = self._best_onramp(pos, reach, blocked, square)
                if found is not None:
                    return found
        # Falling back to `entry_node` rather than to nothing: it applies the
        # same clearance and exclusion rules and is never worse than refusing
        # to plan at all.
        return self.entry_node(pos)

    def _clear_of_traffic(self, pos, node, avoid):
        """True if the hop from pos to node keeps clear of every robot in avoid.

        Two bodies plus the lane-following margin, measured from the other
        robot's CENTRE to the line the hop runs along.
        """
        room = 2.0 * ROBOT_RADIUS + MARGIN
        return all(_clearance(other, pos, node) >= room for other in avoid)

    def _along_a_line(self, pos, node):
        """Does the hop from `pos` to `node` run ALONG a lane or ACROSS one?

        Every lane in this plant is axis-aligned and every spur is at right
        angles to the lane it meets, so a legal hop moves in x or in y and not
        in both. Anything else is a slant across the roadway — which is the
        one manoeuvre RULE 1 exists to forbid, and the one the on-ramp search
        was free to choose because the first hop is the leg no lane covers.

        The tolerance is the robot's own radius: a robot sitting a little off
        its line still counts as driving along it.

        THIS REPLACED A NARROWER FIX THAT MADE THINGS WORSE. The first attempt
        was "a robot standing on a node rejoins at that node", with "standing
        on" meaning within half the lane gap. It cured the junction the robot
        backs out onto and broke everything around it: 0.5 m west of that
        junction it chose the junction 0.5 m BEHIND, and half way across to the
        inner lane it chose the junction 0.90 m behind. Sending a robot
        backwards to a node it has just left is the "drives on, then backs up,
        then slants across" the diagonal was reported with.

        Constraining the SHAPE of the hop has no such backward pull: it removes
        the illegal candidates and leaves the cost comparison to choose among
        what is left.
        """
        return (abs(node[0] - pos[0]) <= ROBOT_RADIUS
                or abs(node[1] - pos[1]) <= ROBOT_RADIUS)

    #: Which way each compass word points.
    _HEADING = {"east": (1.0, 0.0), "west": (-1.0, 0.0),
                "north": (0.0, 1.0), "south": (0.0, -1.0)}

    def _with_the_traffic(self, pos, node):
        """Does this hop run WITH the lane it lands on, rather than back up it?

        Being axis-aligned is not enough. A robot half way across from the
        outer lane to the inner one, re-planning, was offered a junction 2.88 m
        along the OUTER lane — square, legal by shape, and 2.88 m the wrong way
        up a one-way lane it had already left. That is the "drives on, then
        backs up, then slants across" half of the report.

        A hop straight ACROSS a lane has no component along it and passes.
        Everything else has to point the way the traffic goes.

        A corner sits on two lanes and either is a fair way to arrive at it, so
        one agreeing lane is enough.
        """
        hx, hy = node[0] - pos[0], node[1] - pos[1]
        agrees = None
        for (ring, side), (axis, value) in plant.LANE_LINE.items():
            on = node[0] if axis == "x" else node[1]
            if abs(on - value) > 1e-6:
                continue                 # this node is not on that lane
            dx, dy = self._HEADING[plant.RING[ring][side]]
            agrees = bool(agrees) or (hx * dx + hy * dy >= 0.0)
        return True if agrees is None else agrees

    def _best_onramp(self, pos, reach, avoid, square=False):
        """Cheapest reachable on-ramp within MAX_ONRAMP, or None.

        :param square: reject any hop that is neither along a lane nor
            straight across one. Set for a robot that is already on the road.
        """
        candidates = sorted(
            (n for n in self.nodes if not n.startswith(self.TERMINAL)),
            key=lambda n: math.hypot(self.nodes[n][0] - pos[0],
                                     self.nodes[n][1] - pos[1]))
        nearest = None
        best, best_cost = None, float("inf")
        for name in candidates:
            hop = math.hypot(self.nodes[name][0] - pos[0],
                             self.nodes[name][1] - pos[1])
            if hop > self.MAX_ONRAMP:
                break                    # sorted, so nothing later is closer
            if name not in reach:
                continue                 # cannot get to the goal from there
            if not self.is_clear(pos, self.nodes[name]):
                continue                 # the one leg no lane covers
            if avoid and not self._clear_of_traffic(pos, self.nodes[name],
                                                    avoid):
                continue                 # would drive through another robot
            if square and not self._along_a_line(pos, self.nodes[name]):
                continue                 # a slant across the roadway
            if square and not self._with_the_traffic(pos, self.nodes[name]):
                continue                 # backwards up a one-way lane
            if nearest is None:
                nearest = hop
            cost = hop + reach[name]
            # BREAK A NEAR-TIE ON SOMETHING THE ROBOT'S MOTION CANNOT CHANGE.
            #
            # Total cost is continuous in position, which stops a candidate
            # winning by a jump. It does NOT stop two candidates being almost
            # equal: driving half a metre toward one then makes the other
            # cheaper, and the plan alternates for ever. Measured 2026-08-26 on
            # the two-lane road, amr2 heading for the ASRS oscillating between
            # `join_parkB2_outer` (east) and `aisle_ne_outer` (west) every
            # replan — 88 of 270 routes never converged.
            #
            # `reach` is a property of the NODE, not of where the robot is
            # standing, so preferring the candidate genuinely nearer the goal
            # settles it and keeps settling it as the robot moves.
            if cost < best_cost - self.TIE_BREAK:
                best, best_cost = name, cost
            elif best is not None and cost < best_cost + self.TIE_BREAK \
                    and reach[name] < reach[best]:
                best, best_cost = name, cost
        return best

    def _distances_to(self, goal):
        """Shortest path cost from every node to `goal`.

        One Dijkstra instead of one per candidate on-ramp, walked over the
        REVERSED graph so the answer is distance TO the goal. On the undirected
        graph this used `adjacency` and the two were the same number; with
        one-way lanes they are not, and using the forward graph would have
        costed every on-ramp by how far it is to drive AWAY from the goal.
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
            for nxt in self.reverse[here]:
                if nxt not in unvisited or not self._through(nxt, goal):
                    continue
                nx, ny = self.nodes[nxt]
                cost = dist[here] + math.hypot(nx - hx, ny - hy)
                if cost < dist.get(nxt, float("inf")):
                    dist[nxt] = cost
        return dist

    def route_from(self, pos, to_station, avoid=()):
        """Waypoints from an arbitrary point to a station's dock."""
        goal = f"dock_{to_station}"
        return self._forward_of(
            pos, self._route_nodes(self.entry_node_for(pos, goal, avoid), goal))

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

    def route_to_node(self, pos, node, avoid=()):
        """Waypoints from an arbitrary point to any named node.

        Parking bays need this. Driving home used to be a straight line at the
        bay, which is the one thing this module exists to prevent — and it also
        put an idle robot on no road at all, where no traffic rule could apply
        to it. Homing is an ordinary trip and takes ordinary roads.
        """
        return self._forward_of(
            pos, self._route_nodes(self.entry_node_for(pos, node, avoid), node))

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
                if nxt not in unvisited or not self._through(nxt, goal):
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
    """The checked two-lane network. Raises UnsafeLane if obstructed.

    TWO ONE-WAY RINGS, inner and outer, around the same rectangle the plant
    always had. Every station and every parking bay has a junction on BOTH
    rings, so a robot turns off the lane it is already on and never crosses the
    opposing one to reach a spur.

    The rings never touch each other directly. A robot changes ring the same
    way it reaches anything else — by turning onto a spur, which crosses both
    lanes and joins each of them. That is 37 places round the rectangle, and it
    means a lane change is always a turn off the road, never a swerve across
    the neighbouring lane.
    """
    obstacles = {n: (pos, MACHINE_RADIUS) for n, pos in plant.OBSTACLES.items()}
    nodes, lanes, dock_owner = {}, [], {}

    # ---- the eight corners: four per ring -------------------------------
    corner_of = {}
    for ring in ("inner", "outer"):
        _, ns_w = plant.LANE_LINE[(ring, "west")]
        _, ns_e = plant.LANE_LINE[(ring, "east")]
        _, ew_n = plant.LANE_LINE[(ring, "north")]
        _, ew_s = plant.LANE_LINE[(ring, "south")]
        for tag, x, y in (("nw", ns_w, ew_n), ("ne", ns_e, ew_n),
                          ("sw", ns_w, ew_s), ("se", ns_e, ew_s)):
            name = f"aisle_{tag}_{ring}"
            nodes[name] = (x, y)
            corner_of[(ring, tag)] = name

    # ---- a junction per station, on each ring ---------------------------
    joins = {(ring, side): [] for ring in ("inner", "outer")
             for side in ("north", "south", "west", "east")}
    for name, (dx, dy) in plant.DOCKS.items():
        dn = f"dock_{name}"
        nodes[dn] = (dx, dy)
        dock_owner[dn] = _owner_of(name)
        side = "north" if dy > 0 else "south"
        spur = {}
        for ring in ("inner", "outer"):
            jn = f"join_{name}_{ring}"
            nodes[jn] = plant.join_for(name, ring)
            dock_owner[jn] = None
            # The spur is driven both ways: in to dock, out to leave.
            lanes.append((jn, dn))
            lanes.append((dn, jn))
            joins[(ring, side)].append(jn)
            spur[ring] = jn
        # THE SPUR IS ONE LINE, SO ITS TWO JUNCTIONS ARE JOINED.
        #
        # They sit on the same straight run out of the dock, LANE_GAP apart,
        # and a robot driving in from the inner lane already crosses the outer
        # one to get there. Leaving them unlinked made the outer junction a
        # trap: the router could only send a robot standing on it the long way
        # round the ring to reach a node 1.80 m away.
        #
        # Measured 2026-08-26. amr1 finished at ASRS, needed GRV1_LD 6.96 m
        # EAST, and was put on the westbound outer lane by EXIT_POSES. The
        # route it got ran join_ASRS_outer -> aisle_nw_outer -> aisle_nw_inner
        # -> join_ASRS_inner: 25.4 m to reach the node directly below where it
        # started, and the route came back to that node anyway. Driven 35.7 m
        # against 17.3 m direct, with two corner turns nobody needed.
        lanes.append((spur["outer"], spur["inner"]))
        lanes.append((spur["inner"], spur["outer"]))

    # ---- parking spurs, likewise on both rings ---------------------------
    for seg, slots in plant.PARKING_SLOTS.items():
        for i, pos in enumerate(slots):
            suffix = "" if i == 0 else str(i + 1)
            pn = f"park_{seg}{suffix}"
            nodes[pn] = pos
            side = "west" if pos[0] < 0 else "east"
            jx, jy = plant.PARKING_JOIN_SLOTS[seg][i]
            spur = {}
            for ring in ("inner", "outer"):
                axis, value = plant.LANE_LINE[(ring, side)]
                jn = f"join_park{seg}{suffix}_{ring}"
                nodes[jn] = (value, jy) if axis == "x" else (jx, value)
                lanes.append((jn, pn))
                lanes.append((pn, jn))
                joins[(ring, side)].append(jn)
                spur[ring] = jn
            # Same line, same reason as a dock spur above. The bay sits beyond
            # BOTH lanes, so the drive out of it crosses the outer one to reach
            # the inner one whether the graph admits it or not.
            lanes.append((spur["outer"], spur["inner"]))
            lanes.append((spur["inner"], spur["outer"]))

    # ---- chain each lane, IN ITS OWN DIRECTION --------------------------
    #
    # `_chain` links everything sitting on a lane in order along it. Which end
    # it starts from is now the direction of travel, and that is the whole
    # difference between this road and the one-way one.
    for ring in ("inner", "outer"):
        going = plant.RING[ring]
        for side, near, far in (("north", "nw", "ne"), ("south", "sw", "se"),
                                ("west", "nw", "sw"), ("east", "ne", "se")):
            axis = 0 if side in ("north", "south") else 1
            chain = [corner_of[(ring, near)]] + joins[(ring, side)] \
                + [corner_of[(ring, far)]]
            ordered = _chain(nodes, chain, axis=axis)
            # `_chain` returns pairs sorted along the axis, low to high. Keep
            # them that way for east/north travel and flip for west/south.
            direction = going[side]
            if direction in ("east", "north"):
                lanes += ordered
            else:
                lanes += [(b, a) for a, b in ordered]

    # ---- THE RINGS DO NOT MEET AT THE CORNERS ---------------------------
    #
    # They used to: eight cross-links, two per corner, added when the corners
    # were the ONLY place a robot could change ring. Once every spur joined
    # both rings that stopped being true, and these became the worst place to
    # do it — a corner is where a robot is already turning and where the two
    # rings run closest together.
    #
    # Measured 2026-08-26 before removing them. Without the eight links the
    # road is still strongly connected (82 of 82 road nodes reach every other,
    # both ways) and no dock or bay loses its way in or out. All 702
    # dock-to-dock routes come out at exactly the same length: the working
    # traffic never used them. 107 of 540 homing routes get longer, mean
    # +2.37 m and worst +3.45 m, which buys the rule that a robot changes ring
    # only on a spur, chosen by the direction it is going.
    #
    # A ring change is now always the same manoeuvre: turn off the lane onto a
    # spur, cross to the other lane, turn back on. The 37 spur junctions are
    # spread right round the rectangle, so one is never far.

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
