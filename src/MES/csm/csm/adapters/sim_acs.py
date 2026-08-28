"""SimAcs - an ACS adapter that drives the real Gazebo robot.

Same interface as MockAcs, but instead of pretending a robot travelled it moves
the simulated Foil_A082 and reports ARRIVED when it gets there. That swap is the
whole argument for the adapter layer: the CSM, its main cycle and its job
FSM are unchanged. Only the class behind AcsAdapter differs.

Three things this file has to get right, each learned the hard way:

**Navigate on ground truth, not wheel odometry.** Wheel odometry integrates
wheel rotation, so a robot jammed against a pallet reports metres of travel it
never made. Navigating on /odom therefore let the robot "arrive" at a goal it
was nowhere near, and the job was marked DONE while the chassis sat motionless
against an obstacle. /odom_truth comes from the simulator. On the real robot the
equivalent is Seer's localisation; the wheel /odom remains what it is.

**Avoid obstacles.** The first version drove straight at the goal and ploughed
into pallet_a. The robot already carries two SICK scanners, so avoidance uses
them: a repulsion vector from nearby returns is added to the attraction toward
the goal. This is a reactive potential field, not a planner — it will not escape
a concave trap, and routing remains the real ACS's job.

**Detect being stuck.** Comparing commanded motion against ground-truth motion
catches the case where the robot is driving hard and going nowhere. Without it a
jam is silent: the ACS keeps reporting IN_PROGRESS, and even the job timeout
reads as "slow" rather than "wedged".
"""

import math

from geometry_msgs.msg import Twist
from trnav_msgs.msg import WheelSet, WheelSetArray
from gazebo_msgs.msg import ModelStates
from sensor_msgs.msg import JointState, LaserScan

from . import docking, roads
from .. import plant
from .base import (AcsAdapter, SimpleResponse, TaskKind, TransportResult,
                   build_order, classify_error_code)

#: THE PLANT. Positions, ports and material flow all come from plant.py, which
#: is built from the customer documents — see its header for the source list.
#: This module used to carry its own invented station table with one port per
#: machine; the real line has separate LD and ULD ports and a different chain.
STATION_POSES = dict(plant.OBSTACLES)      # solid machines
APPROACH_POSES = dict(plant.DOCKS)         # where a robot stands to be served

#: Where a robot waits after backing out of a dock: straight back onto its own
#: aisle. On the road by construction, unlike the sideways offset this replaced.
EXIT_POSES = dict(plant.JOINS)

#: PROTECTIVE FIELD for another robot: stop and wait rather than steer.
#:
#: Nothing in the avoidance field can stop this robot. max_repulsion is capped
#: BELOW the goal attraction on purpose, so obstacles can only steer; and the
#: dock fade scales it to zero near the goal. Between them, a robot whose path
#: is occupied drives into whatever is there. The real Foil_A082 carries two
#: SICK safety scanners for exactly this: a protective field that HALTS the
#: vehicle. This is that behaviour.
#:
#: Chassis is 1.6 x 0.9, so two robots nose to tail touch at 1.6 m centre to
#: centre. Stopping at 2.4 m leaves a clear gap to stop in.
ROBOT_STOP_AHEAD = 2.4
#: Half-width of the corridor checked ahead. Wider than the chassis so a robot
#: squarely in the way stops us, but one passing to the side does not.
ROBOT_STOP_SIDE = 1.2

# ------------------------------------------------------- LAYER 1: no contact
#
# ONE RULE, NO CASES. The old test asked "is another robot within 2.4 m ahead of
# me and inside a +/-1.2 m corridor". That is built for one geometry — meeting or
# following along a lane — and is blind to every crossing one: a robot pulling
# out of a spur, turning in, or meeting at a corner. Measured 2026-08-07: two
# robots touched at 1.50 m centre to centre while 1.3 m apart across the
# corridor, i.e. 0.1 m outside a test that was itself narrower than the distance
# at which these robots collide.
#
# So instead of looking down a corridor, PREDICT. Sample both robots forward at
# their measured velocities and stop if the gap between the two bodies would
# close below STOP_GAP. That covers head-on, following, crossing, corners and
# spur mouths with the same arithmetic, including cases nobody enumerated.
#
# THE BODY IS THE RECTANGLE IT ACTUALLY IS.
#
# It was modelled as a CAPSULE — a segment with a radius — on the reasoning that
# a circle big enough to contain a 1.6 m robot (0.92 m) would refuse to pass one
# parked in a spur. True, and a capsule does fix that. But a capsule with the
# body's length and width ROUNDS THE CORNERS OFF, and the corners are exactly
# what two robots meet with:
#
#     box corner sits at (0.80, 0.45) from centre  ->  0.636 m from the axis
#     capsule surface in that direction            ->  0.450 m from the axis
#     every corner therefore protrudes             ->  0.186 m beyond the shape
#
# Two robots square-on and diagonally offset — one down the aisle, one in a spur
# mouth — touch while their capsule axes are still 1.273 m apart. Verified by
# exhaustive search over relative pose: footprints in contact while the capsule
# reported a gap of up to 1.273 m, worst at relative pose (1.6, 0.9, 0 deg).
#
# The old STOP_GAP was 1.20 m. BELOW 1.273. So the margin the avoidance layer
# aimed for permitted a corner collision by construction, and the measurement
# script shared the same blind spot, so it reported "no contact" while the
# operator watched one robot shove the other across the floor (2026-08-10).
#
# So the gap is measured between the true footprints. CONTACT is then simply
# zero — they are touching — and STOP_GAP is real clearance rather than a
# number whose meaning depends on which way the robots happen to be facing.

#: The collision box in the robot description (foil_a082.urdf.xacro:103-104).
ROBOT_L, ROBOT_W = 1.600, 0.900
#: Half the diagonal — the smallest circle that contains the body. Used only to
#: skip the exact test when robots are obviously far apart.
ROBOT_CIRCUM = math.hypot(ROBOT_L, ROBOT_W) / 2.0
#: Footprints touch at zero. Kept as a name so the intent reads at the call site.
CONTACT_GAP = 0.0
#: Clearance the avoidance layer keeps between the two footprints. This is now a
#: true gap in metres, not an axis separation, so it means the same thing in
#: every orientation.
STOP_GAP = 0.30
#: How far the partner's centre must clear a planned stand-aside path: our own
#: half-width plus enough for their body however it is turned.
#: Below this centre separation the footprint distance is computed exactly.
#: Comfortably beyond any margin the traffic layer reasons about, so every
#: number it acts on is a true distance rather than a conservative bound.
EXACT_RANGE = 2.0 * ROBOT_CIRCUM + 1.0
#: How far ahead to predict, and how finely. 2 s at 0.6 m/s is 1.2 m of travel,
#: comfortably longer than it takes to stop.
LOOKAHEAD_S = 2.0
LOOKAHEAD_STEP_S = 0.25

# ---------------------------------------------------------------- giving way
#
# THE AISLES ARE SINGLE FILE, SO SOMEBODY HAS TO LEAVE THE ROAD. Two robots
# meeting head-on both stop, correctly, and then neither can move: there is no
# width to pass in. Waiting longer cannot fix it and backing off cannot either —
# retreat and the other simply advances into the space, so the meeting happens
# again a few metres further on.
#
# The spurs are the answer. Every station already has one, they are perpendicular
# to the aisle, and they are empty unless a robot is being served there. So the
# robot that is nearer to a free spur pulls into it, the other drives past, and
# the first rejoins. A lay-by, using geometry the plant already has.
#
# Both robots must reach the SAME conclusion without talking to each other, so
# the decision is pure arithmetic on fleet state: nearer-to-a-spur yields, and a
# tie is broken by name. Nothing is negotiated, so nothing can disagree.

#: HOW FAR THE YIELDING ROBOT STEPS ASIDE — and it steps TOWARD THE MIDDLE OF
#: THE HALL: south from the north aisle, north from the south aisle, inward from
#: a cross aisle.
#:
#: An aisle is a line on the map, not a walled corridor. There is 6 m of open
#: floor between the two main aisles and 4 m between an aisle and the machine
#: faces, so a robot can simply crab off the lane. It needs no spur, no junction
#: and no free bay — which is the whole point: reaching a spur meant crossing
#: that spur's junction, so the lay-by and the red light arbitrated the same
#: move independently and deadlocked on it, twice.
#:
#: Toward the hall centre is always open ground, and it is the same direction
#: whichever way the robot happens to be pointing.

#: How far ahead a red light is visible. A follower closes up to STOP_GAP and
#: holds; beyond this it carries on normally rather than stopping half an aisle
#: away from something it cannot even see round.
#:
#: There is no second stopping distance. A queue behind a yielder forms at the
#: same STOP_GAP as every other stop in this file, so a queue looks like a
#: queue and the system has ONE number for "how close is too close".

#: A robot that has given way will not wait for ever.

#: THE ROAD NETWORK. Built once, at import. roads.build() raises rather than
#: returning a network with an obstructed lane, so a plant change that puts a
#: machine on a lane fails loudly at startup instead of driving a robot into it.
ROADS = roads.build()


# -------------------------------------------------------------- the two rules
#
# 1. EVERY ROBOT FOLLOWS THE LINES. The road is two one-way rings and the spurs
#    that feed them; a robot drives the lanes and turns off onto a spur to
#    reach a dock or a bay. It never leaves the lines anywhere else.
#
# 2. LEAVING A DOCK, A ROBOT PAUSES BEFORE THE ROAD. While it pauses it tells
#    every robot near it to stop. When nothing is blocking its way onto the
#    road it goes.
#
# THAT IS ALL OF IT. (user, 2026-08-26.) An earlier version of this file grew a
# junction reservation system, a give-way order, a merge rule and a hold-back
# distance, one on top of another, each added to patch what the last one let
# through. They are gone. Layer 1 stays because it is not a rule — it is the
# last physical stop before two bodies touch — and the station interlock stays
# because one robot per machine bay is what the machine protocol can express,
# not a traffic decision.

#: How far short of the road a robot stops so that its BODY is clear of it.
#:
#: Pausing is only useful somewhere the robot is out of the way, and a distance
#: measured to the lane says nothing about where the robot ends. Half its own
#: length reaches toward the lane, half a passing robot's width reaches back,
#: and STOP_GAP is the air between them.
#:
#: Measured 2026-08-26 at 1.00 m, which is 0.55 m short: amr4 paused exactly
#: where it was told, 1.14 m out, with its nose already in the lane, and amr3
#: drove into it. Three contacts in six minutes, all in the same 3 m of road.
ROAD_EDGE = plant.ROBOT_L / 2.0 + plant.ROBOT_W / 2.0 + STOP_GAP

#: THE SAME NUMBER SERVES THE WAY IN, and it is not a coincidence that it is
#: comfortable there rather than exact.
#:
#: Going out the robot reverses down the spur, so its LENGTH points across the
#: lane and 1.55 m leaves exactly STOP_GAP. Going in it holds its aisle heading
#: and crabs (see `_crossing`, which pins the turn), so only its half-WIDTH
#: reaches toward the lane and the same 1.55 m leaves 0.65 m.
#:
#: The exact figure would be 1.20 m, and that is the wrong one to use. At
#: exactly STOP_GAP layer 1 trips on the first robot to pass — "two robots
#: doing everything right sat exactly on the limit" (plant.py, LANE_GAP) — and
#: a robot stopped by layer 1 in front of a pausing robot is the deadlock this
#: rule exists to prevent. The air is the point.

#: RULE 6. HOW LONG A ROBOT WAITS IN THE DOCK FOR ITS NEXT JOB.
#:
#: The cheapest place in the plant for a robot to stand is the one it is
#: already standing in: it is off the road, so no traffic rule applies to it
#: and no lane is blocked. Going home and coming back is a round trip across
#: the plant, and travel is what causes every problem this branch has.
#:
#: But a docked robot holds the station — the protocol carries exactly one
#: "AGV is inside" bit — so waiting there for ever costs that machine every
#: robot that needed it. Twenty seconds is the compromise: long enough to
#: catch the next job for that cell, short enough that a machine is never
#: blocked for long by a robot doing nothing.
LINGER_SECONDS = 20.0

#: RULE 5. HOW FAR BEHIND THE ROBOT IN FRONT, IN YOUR OWN LANE.
#:
#: Centre to centre, so with a 1.6 m robot it leaves 1.4 m of air — far outside
#: layer 1's 0.30 m, which is the point. Layer 1 is the last physical stop and
#: it can only ever say stop, so two robots that reach it are both frozen and
#: neither recovers. A following rule that stops the one BEHIND at 3 m means
#: layer 1 is never reached between two robots on the same lane.
#:
#: Measured 2026-08-27, with no following rule at all on a job leg: amr1 closed
#: from 2.4 m to 0.26 m behind amr2 with nothing telling it to slow. Both were
#: then stopped by layer 1 and stayed stopped for the rest of the run.
#:
#: Ten robots at 3 m spacing need 30 m of a 121 m ring, so the room is free.
FOLLOW_GAP = 3.0

#: How far to the side still counts as MY LANE.
#:
#: The two lanes are LANE_GAP = 1.80 m apart, so half of that separates "in
#: front of me" from "on the other lane, going the other way". A robot width
#: is comfortably inside that and comfortably outside a robot's own wander.
#: Wider and every robot would queue behind the opposing traffic; narrower and
#: a robot slightly off its line would be missed.
FOLLOW_SIDE = plant.ROBOT_W

#: How far PAST the lane a crossing robot has to get before its body is out of
#: it. Crossing, the robot holds its aisle heading and presents its width.
CROSS_CLEAR = plant.ROBOT_W / 2.0 + plant.ROBOT_W / 2.0 + STOP_GAP

#: How near is "near to it" when a robot leaving a dock asks the others to
#: stop. Far enough that a robot at full speed can stop before reaching the
#: spur mouth, and no further — holding the whole plant still would be a
#: different rule from the one asked for.
HOLD_RADIUS = 6.0

#: Below this speed a robot counts as stopped.
MOVING_MIN = 0.05


def _wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def _parallel_heading(marker_yaw, current_yaw):
    """Heading PARALLEL to a machine face, whichever way round is nearer.

    The marker normal points out of the face, so parallel is a quarter turn from
    it — and there are two such headings, 180 deg apart. Both dock equally well
    because the robot crabs, so take the nearer one and never turn 180 deg to
    reach a symmetric result.
    """
    options = (_wrap(marker_yaw + math.pi / 2.0),
               _wrap(marker_yaw - math.pi / 2.0))
    return min(options, key=lambda h: abs(_wrap(h - current_yaw)))


def _point_seg(p, s0, s1):
    """Distance from point p to the segment s0-s1.

    Module level rather than nested inside _seg_gap because the standoff planner
    needs the same arithmetic to ask "does this path pass through anybody?", and
    two copies of a geometry primitive is exactly the duplication that lets one
    of them drift.
    """
    vx, vy = s1[0] - s0[0], s1[1] - s0[1]
    span = vx * vx + vy * vy
    if span < 1e-12:
        return math.hypot(p[0] - s0[0], p[1] - s0[1])
    t = max(0.0, min(1.0, ((p[0] - s0[0]) * vx + (p[1] - s0[1]) * vy) / span))
    return math.hypot(p[0] - (s0[0] + t * vx), p[1] - (s0[1] + t * vy))


def _footprint(pose):
    """The four corners of a robot's body, in world coordinates."""
    x, y, yaw = pose
    c, s = math.cos(yaw), math.sin(yaw)
    hl, hw = ROBOT_L / 2.0, ROBOT_W / 2.0
    return [(x + dx * c - dy * s, y + dx * s + dy * c)
            for dx, dy in ((hl, hw), (hl, -hw), (-hl, -hw), (-hl, hw))]


def _overlap(pa, pb):
    """Separating-axis test for two convex polygons. True if they intersect.

    If any edge normal of either polygon separates their projections, they are
    apart; if none does, they overlap. Exact for convex shapes.
    """
    for poly in (pa, pb):
        n = len(poly)
        for i in range(n):
            ax = poly[(i + 1) % n][0] - poly[i][0]
            ay = poly[(i + 1) % n][1] - poly[i][1]
            nx, ny = -ay, ax
            amin = amax = nx * pa[0][0] + ny * pa[0][1]
            for p in pa[1:]:
                v = nx * p[0] + ny * p[1]
                amin = v if v < amin else amin
                amax = v if v > amax else amax
            bmin = bmax = nx * pb[0][0] + ny * pb[0][1]
            for p in pb[1:]:
                v = nx * p[0] + ny * p[1]
                bmin = v if v < bmin else bmin
                bmax = v if v > bmax else bmax
            if amax < bmin or bmax < amin:
                return False
    return True


def _seg_gap(a, b):
    """The true gap between two robots' footprints, in metres. 0.0 if touching.

    Rectangles, not capsules — see the note above CONTACT_GAP for why the
    difference is 0.186 m at every corner and why that mattered.

    Cheap rejection first, but not too eager: beyond EXACT_RANGE the return is a
    LOWER BOUND rather than the true distance. That is safe for control — it can
    only under-state clearance, never over-state it — but it would make the
    number useless for measurement, and measuring with a model that flatters the
    truth is exactly how the corner error survived. So the band is wide enough
    that every distance the traffic layer actually reasons about is exact, and
    the bound only applies to robots that are plainly far apart.
    """
    centre = math.hypot(a[0] - b[0], a[1] - b[1])
    if centre > EXACT_RANGE:
        return centre - 2.0 * ROBOT_CIRCUM      # a valid lower bound, > 0

    pa, pb = _footprint(a), _footprint(b)
    if _overlap(pa, pb):
        return 0.0

    best = float("inf")
    for poly, other in ((pa, pb), (pb, pa)):
        n = len(other)
        for p in poly:
            for i in range(n):
                d = _point_seg(p, other[i], other[(i + 1) % n])
                if d < best:
                    best = d
    return best


def _to_body(ex, ey, yaw):
    """Rotate a WORLD-frame error into the robot's BODY frame.

    Twist.linear is a body velocity. Feeding it a world-frame direction happens
    to work at yaw 0 and is exactly reversed at yaw 180, which is the sort of
    bug that looks intermittent: the same code drove a robot correctly out of
    one bay and into a wall out of the next.
    """
    c, s = math.cos(yaw), math.sin(yaw)
    return ex * c + ey * s, -ex * s + ey * c


class SimRobot:

    def __init__(self, node, name="", arrive_tolerance=0.35, max_speed=0.6,
                 stations=None, influence_radius=1.4, repel_gain=1.4,
                 turn_gain=1.6, max_turn=0.9, crab_window=0.5,
                 stall_seconds=8.0, stall_distance=0.12, dwell_seconds=3.0,
                 dock_fade_m=2.2, max_repulsion=0.85, critical_distance=0.7):
        """
        :param arrive_tolerance: metres from the goal that counts as arrived
        :param max_speed:        m/s cap on commanded body velocity
        :param influence_radius: scan returns nearer than this push the robot away
        :param repel_gain:       strength of that push relative to the goal pull
        :param stall_seconds:    driving for this long without moving = stuck
        :param stall_distance:   ground-truth movement that counts as progress
        :param dwell_seconds:    time spent loading at the source station
        :param dock_fade_m:      inside this range of the goal, obstacle
                                 avoidance fades to zero so the robot can dock
        :param max_repulsion:    hard cap on the avoidance force. Below 1.0 —
                                 the attraction is normalised to 1.0 — so
                                 avoidance can deflect the robot strongly but
                                 can never stop it seeking the goal
        :param critical_distance: obstacle range at which repulsion reaches
                                 max_repulsion
        """
        self.node = node
        #: Topic namespace and log identity. "" means the single-robot world.
        self.name = name
        #: The Gazebo model name, which is what -entity set at spawn. The
        #: single-robot world spawns "foil_a082"; the fleet spawns amrN.
        self.model_name = name or "foil_a082"
        self.tolerance = arrive_tolerance
        #: How near a lane corner counts as reaching it. Far looser than the
        #: dock tolerance: a corner is a direction change, not a destination.
        self.waypoint_tolerance = 0.6
        #: ...but a waypoint where the route TURNS is a place, not a corner to
        #: round. Half the arrive tolerance: at a spur mouth, where the two
        #: lanes are LANE_GAP = 1.80 m apart, it holds the turn to
        #: atan2(1.80, 0.175) = 84 degrees. Not tighter, because a waypoint
        #: the robot cannot reach is a waypoint it never leaves — the speed
        #: eases to 0.8 * distance near the goal, so it closes, but the
        #: avoidance field is live out here and it needs room to settle in.
        self.turn_tolerance = arrive_tolerance / 2.0
        self.max_speed = max_speed
        self.stations = dict(stations or APPROACH_POSES)
        self.influence_radius = influence_radius
        #: Heading control. turn_gain/max_turn rotate the body toward the goal;
        #: crab_window is how far off-heading the robot may be before it stops
        #: trying to crab and turns instead (radians — about 29°).
        self.turn_gain = turn_gain
        self.max_turn = max_turn
        self.crab_window = crab_window
        self.repel_gain = repel_gain
        self.stall_seconds = stall_seconds
        self.stall_distance = stall_distance
        self.dwell_seconds = dwell_seconds
        self.dock_fade_m = dock_fade_m
        self.max_repulsion = max_repulsion
        self.critical_distance = critical_distance

        # Namespaced so several robots can share one Gazebo world. Empty
        # namespace keeps the single-robot topics exactly as they were, which
        # is what the current world publishes.
        ns = f"/{self.name}" if self.name else ""
        self.pub_cmd = node.create_publisher(Twist, f"{ns}/cmd_vel", 10)
        # DOCKING COMMANDS THE WHEELS DIRECTLY. A Twist is a body velocity and
        # cannot say "point the wheels there and hold" — at zero speed it is all
        # zeros and the steering angle is lost, which silently disabled the
        # settle phase. A wheel command carries the angle explicitly.
        self.pub_wheels = node.create_publisher(
            WheelSetArray, f"{ns}/dock/wheel_cmd", 10)

        # Ground truth comes from ONE world-level topic carrying every model's
        # pose by name, and each robot picks itself out of it.
        #
        # The per-model p3d plugin did not survive going multi-robot: each copy
        # needed its own ROS namespace AND its own plugin name, and even with
        # both the bindings came out crossed — two publishers on
        # /amr1/odom_truth and none at all on /amr2. Looking yourself up by name
        # has no per-model plumbing to get wrong.
        node.create_subscription(ModelStates, "/gazebo/model_states",
                                 self._on_model_states, 10)
        node.create_subscription(LaserScan, f"{ns}/scan_front", self._on_front, 10)
        node.create_subscription(LaserScan, f"{ns}/scan_rear", self._on_rear, 10)
        # Settle-then-drive needs the MEASURED steering angles. Commanded is not
        # good enough: the whole point is that the servo lags the command.
        node.create_subscription(JointState, f"{ns}/joint_states",
                                 self._on_joints, 10)

        self.pose = None            # (x, y, yaw) ground truth
        #: Measured world velocity (m/s), for the collision predictor.
        self.vel = (0.0, 0.0)
        self._vel_stamp = None
        self._front = None
        self._rear = None

        self._active_job = None
        self._goal = None
        #: Remaining lane corners for this leg; the last entry is the dock.
        self._waypoints = []
        #: Called with (job_id, result) when a job ends, however it ends.
        self.on_finished = None
        #: Set by SimAcs. Owns the entry interlock, which is fleet-wide.
        self.fleet = None
        #: How far out a robot asks for entry. Beyond the approach point,
        #: so the refusal arrives before the trip is wasted.
        self.entry_request_range = 2.2
        self._noted_hold = False
        #: Set while stopped for another robot, so the wait is logged once.
        #: When this robot first stopped for another one. Bounds the wait.
        #: Where this robot is standing aside, or None.
        #: Set once it has ARRIVED there and stopped — the all-clear the other
        #: robot waits for. Nothing may pass until this is true.
        #: Junction currently held by this robot (the red light), or None.
        #: Set while squaring up, so the turn is logged once.
        self._noted_square = False
        #: Set while driving back to the parking bay with no job.
        self._homing = False
        #: Lane waypoints for the drive home.
        self._home_waypoints = []
        #: Marker-guided controller for the last couple of metres, or None.
        self._dock = None
        self._docking = False
        #: Measured steering joint angles — settle-then-drive needs to know
        #: where the wheels ACTUALLY are, not where they were commanded.
        self._steer_actual = [0.0, 0.0]
        #: When joint_states last arrived. None means the control chain has
        #: never spoken — see `can_move`.
        self._joints_stamp = None
        #: So the "cannot move" warning is logged once per outage, not per poll.
        self._noted_immobile = False
        #: Same, for waiting on a machine's entry permission.
        self._noted_permission = False

        #: BATTERY, percent. Simulated, and deliberately crude — what matters
        #: for the CSM is that the number falls while working and rises on a
        #: charger, not that the curve is right. A real cell's behaviour is
        #: the robot's own business and section 7 does not retain it.
        self.battery = 100.0
        #: Multiplies both drain and charge, for DEMONSTRATION only.
        #:
        #: At 1.0 a working robot takes about an hour to reach the charge
        #: threshold, which is the right order for a real AGV and far too slow
        #: to watch. Raising it does not make the model more or less correct —
        #: it only compresses the clock — so it is a knob rather than a
        #: different rate, and it is never used to claim a real duration.
        self.battery_scale = 1.0
        self._battery_stamp = None
        #: Set while the robot is on a charger and told to charge.
        self._charging_to = None
        #: So the not-charging warning is logged once per charge order, not
        #: every control cycle.
        self._noted_not_charging = False
        #: A charge accepted while this robot was working, applied when the
        #: job ends. See `_charge_order`.
        self._charge_pending = None
        #: So the flat-battery warning is logged once, not every cycle.
        self._noted_flat = False
        #: Which robot layer 1 keeps stopping us for, and since when. See
        #: `_note_blocked_by`.
        #: Which rule last published a zero velocity. See `_stop`.
        self._halt_reason = None
        #: Set while reversing out of a bay after finishing.
        self._exit_goal = None
        #: RULE 2. Set while this robot is paused at the road edge on
        #: its way out of a dock, asking the robots near it to stop.
        self._pausing_out = False
        #: RULE 2, THE OTHER HALF. The same, crossing a lane on a spur —
        #: into a dock or bay, or out of one onto the road.
        self._pausing_in = False
        #: RULE 6. Until when this robot waits in the dock for its next job.
        #: None means it is not waiting.
        self._linger_until = None
        #: RULE 4's turn, which RULE 2's hold has to cover. Set while the
        #: robot is turning at a junction, where it sweeps its half-diagonal
        #: 0.918 m instead of the 0.450 m it presents held flat.
        self._turning = False
        #: RULE 3. The source station this robot still stands in, held until
        #: it has driven out of the bay. A station is free when the AMR has
        #: LEFT it, not when the load finished.
        self._holding_source = None
        #: The lane that crossing is over, remembered for the length of the
        #: manoeuvre. Between the two lanes the robot is beyond neither, so
        #: the question cannot be re-asked from where it is standing.
        self._crossing_lane = None
        #: Where the robot that is pausing is trying to get to. Read by the
        #: robots it is holding, so that one standing IN that path knows to
        #: clear it rather than freeze in it. See `_held_for_a_leaver`.
        self._pause_goal = None
        self._exit_station = None
        #: Previous logged position, for a speed estimate.
        self._log_x = self._log_y = 0.0

        # A job is two journeys: collect at the source, then carry to the
        # destination, with a loading pause between them.
        self._leg = None            # "collect" | "deliver"
        self._from = None
        self._to = None
        self._dwell_until = None    # loading finishes at this time

        self._stall_ref = None      # (x, y) last position that counted as progress
        self._stall_since = None    # when we last made progress
        self._closest_obstacle = float("inf")   # for the blocked-path message

    # -------------------------------------------------------------- sensors

    def _on_model_states(self, msg):
        """Find this robot in the world state and take its pose.

        A model that is not in the list yet leaves `pose` as it was — during
        spawning the message arrives before the model does, and treating that
        as "no pose" would make a robot look stalled the moment it appeared.
        """
        try:
            i = msg.name.index(self.model_name)
        except ValueError:
            return
        pose = msg.pose[i]
        q = pose.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                         1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        new_pose = (pose.position.x, pose.position.y, yaw)

        # MEASURED velocity, not commanded. The collision predictor must know
        # what a robot is actually doing: a robot parked in a spur has zero
        # velocity however much its goal is elsewhere, and that is what lets
        # another robot drive past it instead of stopping for it.
        now = self._now()
        if self.pose is not None and self._vel_stamp is not None:
            dt = now - self._vel_stamp
            if dt > 1e-3:
                vx = (new_pose[0] - self.pose[0]) / dt
                vy = (new_pose[1] - self.pose[1]) / dt
                k = 0.4                       # light smoothing, keeps it honest
                self.vel = (self.vel[0] + k * (vx - self.vel[0]),
                            self.vel[1] + k * (vy - self.vel[1]))
                self._vel_stamp = now
        else:
            self._vel_stamp = now
        self.pose = new_pose

    def _on_joints(self, msg):
        # The stamp matters as much as the angles: this topic only publishes
        # while the controller chain is up, which makes it our liveness signal.
        self._joints_stamp = self._now()
        for name, position in zip(msg.name, msg.position):
            if name == "w1_steer_joint":
                self._steer_actual[0] = position
            elif name == "w2_steer_joint":
                self._steer_actual[1] = position

    #: How long joint_states may be silent before this robot is treated as
    #: unable to move. The broadcaster publishes continuously once controllers
    #: are up, so a gap this long means the chain is not running.
    CONTROLLERS_TIMEOUT_S = 3.0

    @property
    def can_move(self):
        """Has this robot's control chain actually come up, and is it still up?

        POSE CANNOT ANSWER THIS. A pose comes from Gazebo ground truth, which
        exists the moment the model is spawned — before its controllers, and
        even if they never start at all. So a spawned shell with no controllers
        is indistinguishable from a working robot by pose alone.

        That is not hypothetical. On 2026-08-18 amr3's spawn_entity hung, its
        controllers and wheel bridge never started, and it sat immobile in its
        bay. It had a valid pose, so it was dispatched a job, and amr2
        manoeuvred into it. The launch timing that triggered that has been
        widened, but timing only makes the race rarer — this is what makes the
        state observable.

        joint_states is the signal that can answer it: published by the
        joint_state_broadcaster, which runs only once the controller chain is
        up, and stops if that chain dies.
        """
        if self.battery <= 0.0:
            return False            # flat: it cannot drive anywhere
        if self._joints_stamp is None:
            return False
        return (self._now() - self._joints_stamp) < self.CONTROLLERS_TIMEOUT_S

    def _on_front(self, msg):
        self._front = msg

    def _on_rear(self, msg):
        self._rear = msg

    def _repulsion(self):
        """A BOUNDED push away from obstacles, in the body frame.

        Returns (vector, closest_distance). The vector never exceeds
        max_repulsion, so avoidance steers the robot without ever becoming the
        thing that drives it.

        Why bounded. The first version summed a term per beam, so the force grew
        with how MANY beams saw something. A wall fills dozens of beams and
        produced a push of magnitude 3.5 against an attraction of exactly 1.0 —
        measured, not guessed. The robot stopped seeking its goal and simply
        fled walls, wandering until the stall detector gave up. Direction was
        always right; magnitude was unbounded.

        So: the beams decide the DIRECTION, and the single closest obstacle
        decides the STRENGTH. Strength is zero at the influence radius and rises
        to max_repulsion at critical_distance, so a distant wall nudges and a
        near miss shoves hard.
        """
        dx = dy = 0.0
        closest = float("inf")

        # scan_rear is mounted yaw=pi, so its beam directions are negated.
        for scan, flip in ((self._front, 1.0), (self._rear, -1.0)):
            if scan is None:
                continue
            for i in range(0, len(scan.ranges), 4):
                r = scan.ranges[i]
                if not math.isfinite(r) or r <= scan.range_min:
                    continue
                if r >= self.influence_radius:
                    continue
                closest = min(closest, r)
                angle = scan.angle_min + i * scan.angle_increment
                # Weight by proximity so the direction leans away from the
                # nearest thing, not the most numerous.
                w = 1.0 / max(r, 0.15) ** 2
                dx -= flip * math.cos(angle) * w
                dy -= flip * math.sin(angle) * w

        if closest == float("inf"):
            return (0.0, 0.0), closest          # nothing within range

        norm = math.hypot(dx, dy)
        if norm < 1e-9:
            return (0.0, 0.0), closest          # pushes cancelled out

        # Strength from the closest obstacle alone: 0 at influence_radius,
        # 1 at critical_distance.
        span = max(self.influence_radius - self.critical_distance, 1e-6)
        t = (self.influence_radius - closest) / span
        strength = max(0.0, min(1.0, t)) * self.max_repulsion

        return (dx / norm * strength, dy / norm * strength), closest

    # ----------------------------------------------------------- AcsAdapter

    @property
    def busy(self):
        # A robot reversing out of a bay is NOT free, even though its job is
        # already finished and _active_job cleared. drive() services _exit_goal
        # first and returns, so a job handed over now is accepted and then
        # never driven — it sits untouched until the MES times it out at 120 s.
        #
        # Measured 2026-08-06: both `timeout after 120s in RUNNING` failures in
        # an eight-job run came from this, given to a robot that was still
        # backing out and never finished doing so.
        # RULE 6's linger does NOT make it busy — the whole point is to be
        # offered the next job while still standing in the dock. It is off the
        # road, holding one station, and ready to go.
        return self._active_job is not None or self._exit_goal is not None

    def accept(self, job):
        """Take this job. The FLEET decides whether to offer it; this only
        knows how to carry one.

        A transport job is TWO journeys, not one. Going straight to the
        destination would report the load delivered without the robot ever
        having visited the source — the job would be fiction.
        """
        # PLAN FIRST, then commit. accept() used to set _active_job and only
        # then compute the route; when routing raised — the very first job
        # arrives before the robot's first ground-truth message, so self.pose
        # was None — the robot was left holding a job it had no route for, and
        # reported busy for ever after. Every later job for that segment then
        # queued behind a robot that would never move.
        waypoints = self._plan(job.from_station)

        # RULE 6 is over the moment there is work. The bay it was waiting in
        # is released here rather than on the way out, because the route it
        # has just planned starts by driving out of it.
        if self._linger_until is not None:
            self._linger_until = None
            if self._exit_station is not None and self.fleet is not None:
                self.fleet.release(self._exit_station, self.name or "robot")
            self._exit_station = None

        self._homing = False
        self._active_job = job.job_id
        self._leg = "collect"
        self._from = job.from_station
        self._to = job.to_station
        self._dwell_until = None
        self._reset_stall()
        self._waypoints = waypoints
        self._goal = waypoints[0]
        self.node.get_logger().info(
            f"{self._tag()}{job.job_id}: leg 1/2 — collecting from "
            f"{job.from_station} {self._goal} via {len(self._waypoints)} waypoints")

    # ------------------------------------------------------------- docking

    def _begin_docking(self, station):
        """Hand the last couple of metres to the marker-guided controller."""
        # The robot is told WHICH marker this bay must show. If it can see a
        # marker but it is the wrong one, the approach is refused before the
        # robot moves — docking against the wrong machine would be reported as
        # success, and the CSM would then believe material is somewhere it is
        # not.
        self._dock = docking.DockController(target=plant.DOCK_TARGET,
                                            d_min=plant.DOCK_MIN,
                                            expect_id=plant.MARKER_IDS.get(station))
        self._dock.reset(now=self._now())
        self._docking = True
        self.node.get_logger().info(
            f"{self._tag()}{self._active_job}: at {station} approach point — "
            f"docking on marker {plant.MARKER_IDS.get(station)}")

    def _run_docking(self, station):
        """One docking cycle. Ends the leg on success, fails the job on fault."""
        marker = plant.MARKERS.get(station)
        obs = (docking.observe(self.pose, marker, plant.MARKER_IDS.get(station))
               if marker else None)
        if obs is not None:
            obs.stamp = self._now()

        speed, steer, status = self._dock.step(obs, self._steer_actual,
                                               self._now())
        if status == docking.Result.DOCKED:
            self.node.get_logger().info(
                f"{self._tag()}{self._active_job}: {self._dock.reason}")
            self._end_docking()
            self._on_arrival(0.0)
            return
        if status == docking.Result.FAILED:
            job = self._active_job
            self.node.get_logger().warn(
                f"{self._tag()}{job}: docking failed — {self._dock.reason}")
            self._end_docking()
            self._finish(job, TransportResult.FAILED)
            return

        # Crab: both wheels to one angle, one speed — pure translation. Sent as
        # a WHEEL command, not a Twist, so a zero-speed steering command still
        # steers. This is what the docking project publishes, and why its
        # settle-then-drive works.
        self._publish_wheels(speed, steer)

    def _publish_wheels(self, speed, steer):
        """Both wheels to one angle and one speed — pure translation."""
        msg = WheelSetArray()
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"
        w1, w2 = WheelSet(), WheelSet()
        w1.velocity = w2.velocity = float(speed)
        w1.steering = w2.steering = float(steer)
        msg.wheels = [w1, w2]
        self.pub_wheels.publish(msg)

    def _end_docking(self):
        self._dock = None
        self._docking = False
        self._noted_square = False
        self._stop("docking finished")

    #: How square is square enough. A degree of tilt costs about 14 mm of
    #: reach, so 2 deg spends 28 mm of the 229 mm gap — comfortable.
    SQUARE_TOL = math.radians(2.0)

    def _dock_heading(self, station):
        """Body heading that is PARALLEL to the machine face.

        The marker normal points out of the face, so parallel is a quarter turn
        from it — and there are two such headings. Take whichever is nearer, so
        the robot never turns 180 degrees to achieve a symmetric result.
        """
        marker = plant.MARKERS.get(station)
        if marker is None:
            return None
        return _parallel_heading(marker[2], self.pose[2])

    def _square_up(self, yaw, station):
        """Rotate to face along the machine. True while still turning.

        Rotation only — no translation. At the approach point the face is
        2.2 m away and the robot's half-diagonal is 0.918 m, so there is room
        to turn here; there is none once it has crabbed in.
        """
        want = self._dock_heading(station)
        if want is None:
            return False
        err = _wrap(want - yaw)
        if abs(err) <= self.SQUARE_TOL:
            return False
        if not self._noted_square:
            self._noted_square = True
            self.node.get_logger().info(
                f"{self._tag()}squaring up to {station}: "
                f"{math.degrees(err):+.1f} deg off parallel")
        cmd = Twist()
        cmd.angular.z = max(-self.max_turn,
                            min(self.max_turn, self.turn_gain * err))
        self.pub_cmd.publish(cmd)
        return True

    #: Close enough to the parking bay to count as home. Loose: a bay is a
    #: place to wait, not a dock, and creeping the last few centimetres wastes
    #: the time the trip was meant to save.
    HOME_TOL = 0.8

    def _home_target(self):
        """Where "home" is for this robot right now: (position, node name).

        Its own parking slot, unless it is charging — then it is the plug it
        has been given, which for most of the fleet is SOMEBODY ELSE'S SLOT.
        Five chargers serve ten robots, so "its charger is its parking slot"
        was true only while every leg had one robot. amr4 parks at (24.5,
        -3.65) and its nearest charger is at (24.5, -1.5); sending it home
        would have parked it beside a plug it never reached, discharging while
        reporting that it was charging.
        """
        if self._charging_to is not None and self.fleet is not None:
            spot = self.fleet.claim_charger(self)
            if spot is not None:
                return spot, roads.park_node_at(spot)
        return plant.parking_for(self.name), roads.park_node(self.name)

    def _go_home(self):
        """Drive an idle robot back to its parking bay, ON THE LANES.

        Homing is an ordinary trip and takes ordinary roads. It used to be a
        straight line at the bay, which put an idle robot on no road at all —
        somewhere no traffic rule could apply to it, cutting across the hall and
        stopping wherever it happened to arrive.
        """
        # This robot's OWN slot. Using the leg's slot sent every robot of a
        # class to one point, which is only survivable while a class has one
        # robot.
        bay, home_node = self._home_target()
        if bay is None or self.pose is None:
            return
        x, y, yaw = self.pose
        if math.hypot(bay[0] - x, bay[1] - y) <= self.HOME_TOL:
            if self._homing:
                self._homing = False
                self._home_waypoints = []
                self._stop("homing: robot ahead")
            return

        if not self._homing:
            self._homing = True
            # `park_{segment}` was a NameError here — `segment` is never
            # defined in this method — so every attempt to drive home killed
            # the drive FSM. It survived unseen because homing is only reached
            # by a robot that is idle AND away from its bay, which the fleet
            # rarely was until charging started sending robots out.
            self._home_waypoints = list(
                ROADS.route_to_node(self.pose[:2], home_node,
                                    self._others())
                if home_node else []) or [bay]
            self.node.get_logger().info(
                f"{self._tag()}no work — returning to park via "
                f"{len(self._home_waypoints)} waypoints")

        while (len(self._home_waypoints) > 1
               and math.hypot(self._home_waypoints[0][0] - x,
                              self._home_waypoints[0][1] - y)
               <= self.waypoint_tolerance):
            self._home_waypoints.pop(0)

        goal = self._home_waypoints[0] if self._home_waypoints else bay
        # Layer 1 is not repeated here: drive() checks it for every robot before
        # dispatching to this path, which is the whole point of putting it in
        # one place. A second copy would drift.
        #
        self._drive_toward(goal, x, y, yaw)

    def _drive_toward(self, goal, x, y, yaw):
        """Straight-line crab toward a point, with full obstacle avoidance."""
        ex, ey = goal[0] - x, goal[1] - y
        distance = math.hypot(ex, ey)
        # RULE 5, and the same arithmetic the job leg uses. This path had its
        # own 2.4 m corridor, which meant "how close may I follow" had two
        # answers depending on whether the robot happened to be carrying a
        # load. One rule, one number.
        infront = self._ahead_in_my_lane(x, y, ex, ey)
        if infront is not None:
            self._stop(f"3 m rule: {infront.name} is in front")
            return
        ax, ay = _to_body(ex, ey, yaw)
        n = math.hypot(ax, ay) or 1.0
        (rx, ry), _ = self._repulsion()
        vx, vy = ax / n + rx, ay / n + ry
        m = math.hypot(vx, vy) or 1.0
        speed = min(self.max_speed, 0.8 * distance)
        cmd = Twist()
        cmd.linear.x = vx / m * speed
        cmd.linear.y = vy / m * speed
        self.pub_cmd.publish(cmd)

    #: Percent per second while driving, and while merely powered. Chosen so
    #: a robot working continuously needs a charge after roughly an hour,
    #: which is the order the deck implies (0.5 m/s, shift-length duty). Not a
    #: measured figure and not claimed to be one.
    DRAIN_MOVING = 0.020
    DRAIN_IDLE = 0.002
    CHARGE_RATE = 0.50

    @property
    def charging(self):
        """Has this robot been told to charge and not finished?

        A CHARGING ROBOT IS NOT A FREE ROBOT, even though it is not busy. It
        was excluded by neither test, so the dispatcher took a robot that was
        sitting on a charger part-charged, drove it away on a job, and left it
        draining — while `charging_to` stayed set, so the live view went on
        reporting it as charging the whole time it was going down. Observed
        2026-08-19: amr1 rose 20% -> 30%, took a job, and fell again.

        Cleared by `_step_battery` on reaching the target, so the exclusion
        ends on its own rather than needing anyone to remember to lift it.
        """
        return self._charging_to is not None

    def _on_own_charger(self):
        """Am I at MY charger, by the SAME tolerance I use to decide I arrived?

        THESE WERE TWO DIFFERENT NUMBERS AND THE GAP BETWEEN THEM WAS A TRAP.
        Homing stops within `HOME_TOL` (0.8 m, deliberately loose — creeping the
        last few centimetres wastes the time the trip was meant to save), while
        `plant.is_charger` answered within 0.3 m. A robot that stopped anywhere
        between the two was parked, idle, reporting `charging_to 90`, and
        drawing nothing.

        Observed 2026-08-19: amr1 stopped at (-21.9, +1.6) with its charger at
        (-22.5, +1.5) — 0.6 m, inside the parking tolerance and outside the
        charging one. It sat there discharging while every screen said it was
        charging, and would have reached zero that way. The state was
        indistinguishable from charging everywhere except the battery.

        Asking about MY charger rather than ANY charger is the second half:
        a charger is one robot's own slot, so being near somebody else's is not
        being on one.
        """
        mine = (self.fleet.claim_charger(self) if self.fleet is not None
                else plant.charger_for(self.name))
        if mine is None or self.pose is None:
            return False
        return math.hypot(mine[0] - self.pose[0],
                          mine[1] - self.pose[1]) <= self.HOME_TOL

    def _step_battery(self, moving):
        """Drain or charge, once per control cycle.

        Driven by ELAPSED TIME rather than counting ticks, so the number means
        the same thing whatever rate the controller happens to run at.
        """
        now = self._now()
        if self._battery_stamp is None:
            self._battery_stamp = now
            return
        elapsed = max(0.0, now - self._battery_stamp)
        self._battery_stamp = now

        on_charger = self._on_own_charger()
        if self._charging_to is not None and on_charger:
            self.battery = min(
                self._charging_to,
                self.battery + self.CHARGE_RATE * self.battery_scale * elapsed)
            if self.battery >= self._charging_to:
                self._charging_to = None
                self.node.get_logger().info(
                    f"{self._tag()}charged to {self.battery:.0f}%")
            return

        if self._charging_to is not None and not moving and not self._noted_not_charging:
            # TOLD TO CHARGE, STANDING STILL, NOT ON THE CHARGER. Whatever the
            # reason — it could not reach the slot, or stopped short of it —
            # this is a robot going flat while every reader believes it is
            # filling up. Said once, because silence here looks exactly like
            # success.
            self._noted_not_charging = True
            self.node.get_logger().warn(
                f"{self._tag()}told to charge to {self._charging_to:.0f}% but "
                f"it is not on its charger and is not moving — battery "
                f"{self.battery:.0f}% and falling")
        rate = self.DRAIN_MOVING if moving else self.DRAIN_IDLE
        self.battery = max(0.0, self.battery - rate * self.battery_scale * elapsed)

    def start_charging(self, to_level=90.0):
        """Told by the ACS to charge. The CSM decides WHEN; this obeys.

        Recorded rather than acted on directly: a robot charges by being on a
        charger, so this only says what it is doing there and how full is
        enough.
        """
        self._charging_to = to_level
        # A new charge order gets a fresh warning. Otherwise a robot that
        # failed to reach its charger once would fail silently ever after.
        self._noted_not_charging = False

    #: Beyond this, two robots are not meeting. Generous — well past the
    #: distance at which either could affect the other — because ending an
    #: encounter early is what the "past it means behind me" note below warns
    #: against, and this is only meant to catch bookkeeping that has outlived
    #: the situation it described.
    ENCOUNTER_RANGE = 8.0

    #: How long two robots may sit stopped by each other before the deadlock
    #: is treated as one. Long enough that a robot briefly waiting for another
    #: to pass is not mistaken for a standoff, short enough that a jam does not
    #: outlive anybody's patience.
    DEADLOCK_AFTER_S = 4.0

    def _machine_permits(self, station):
        """May we cross this machine's door? False means we have stopped.

        Returns True when the equipment cannot be asked — an adapter with no
        handshake is not a machine refusing us, and treating "cannot ask" as
        "refused" would stop a line that has no equipment layer at all.
        """
        machine = getattr(self.fleet, "equipment", None)
        if machine is None or not hasattr(machine, "observe"):
            return True

        handshake = machine.observe(station, agv_entering=self._docking)
        if handshake.may_enter:
            self._noted_permission = False
            return True

        if not self._noted_permission:
            self._noted_permission = True
            self.node.get_logger().info(
                f"{self._tag()}waiting for {station} to permit entry")
        self._reset_stall()
        self._stop("machine has not granted entry")
        return False

    def _in_a_bay(self):
        """True while the robot is inside a station bay, past the spur junction.

        Geometric rather than a flag, so it holds however the robot got there —
        arriving, leaving, or recovering from a failed job.
        """
        x, y = self.pose[0], self.pose[1]
        return any(math.hypot(mx - x, my - y) < plant.BAY_RADIUS
                   for mx, my, _ in plant.MARKERS.values())

    def _plan(self, station):
        """Waypoints from where the robot is now to a station's dock.

        Returns a direct goal only as a last resort — if the robot has no
        position yet, or the network cannot reach the station. submit_job
        refuses to offer work to a robot without a position, so in practice the
        first case does not arise; it is handled here so a missing pose can
        never raise halfway through accept() and strand the robot.
        """
        if self.pose is None:
            return [self.stations[station]]
        return list(ROADS.route_from(self.pose[:2], station,
                                     self._others())) or \
            [self.stations[station]]

    def _others(self):
        """Where every OTHER robot is standing, for the router to avoid.

        Only the on-ramp needs this. Every later hop is a lane the network has
        already proved clear, and traffic on a lane is layer 1's business —
        but the first hop is open floor, and in the machine row open floor is
        where robots stand docked.
        """
        if self.fleet is None:
            return ()
        return [r.pose[:2] for r in self.fleet.robots
                if r is not self and r.pose is not None]

    def _set_route(self, station):
        """Plan this leg along the lane network, from wherever the robot is.

        The goal becomes the FIRST waypoint rather than the station, and the
        robot works down the list. Every hop after the first is a lane that
        roads.build() has proved clear of every machine and the pillar, so the
        three routes that used to drive through something solid cannot recur.

        Only the first hop — from wherever the robot happens to be onto the
        network — is unchecked ground, and entry_node() prefers a waypoint it
        can reach in a straight line.
        """
        self._waypoints = self._plan(station)
        self._goal = self._waypoints[0]

    @property
    def _final_leg(self):
        """True once the current goal is the dock itself.

        The interlock and the dock fade both belong to the last hop only. Asking
        for entry from a waypoint on the far side of the hall would hold a bay
        for the length of the drive, and fading avoidance out at an intermediate
        waypoint would blind the robot in open floor rather than at the machine.
        """
        return len(self._waypoints) <= 1

    #: Sharper than this and the waypoint is a turn, not a corner to round.
    #:
    #: Every turn on this road is a right angle — the lanes are axis-aligned
    #: and every spur meets its lane square — so the real cases are 0 degrees
    #: (carry straight on) and 90. Halfway between them separates the two
    #: without having to be exact.
    TURN_DEGREES = 45.0

    def _turn_here(self):
        """Does the route change direction at the waypoint being driven at?

        A corner the robot merely rounds may be cut; a turn off one line onto
        another may not, because the metres saved come out of the turn and the
        robot leaves its lane early, at an angle. See the caller.
        """
        if len(self._waypoints) < 2 or self.pose is None:
            return False
        here, nxt = self._waypoints[0], self._waypoints[1]
        ax, ay = here[0] - self.pose[0], here[1] - self.pose[1]
        bx, by = nxt[0] - here[0], nxt[1] - here[1]
        na, nb = math.hypot(ax, ay), math.hypot(bx, by)
        if na < 1e-6 or nb < 1e-6:
            return False
        cos = (ax * bx + ay * by) / (na * nb)
        return cos < math.cos(math.radians(self.TURN_DEGREES))

    def _tag(self):
        return f"[{self.name}] " if self.name else ""

    # -------------------------------------------------------------- driving

    #: How near a corner a robot must be before it may turn. Its own
    #: half-diagonal plus the margin: far enough out and the swing is still
    #: inside the junction, not out along a lane.

    def _on_a_spur(self):
        """True if this robot has turned OFF the lane network onto a dead end.

        A dock spur or a parking spur. Both serve exactly one place, so a robot
        on one is not on any road another robot needs, and traffic carries on
        around it.

        MEASURED AGAINST THE ROAD GRAPH, NOT A RADIUS. This used to be
        `_in_a_bay` — any marker within BAY_RADIUS, a 3.8 m circle. A circle
        that wide around a station on the machine row reaches the aisle, so a
        robot standing IN THE ROAD answered "I am in a bay". On 2026-08-24 that
        let amr4 tell amr3 "you may pass" with its body in the lane, and the
        two touched.

        The honest question is whether the robot has left the through network,
        and the graph already knows: it is on a spur when the nearest DOCK or
        PARK node is closer than that spur's own junction with the aisle.
        """
        if self.pose is None:
            return False
        x, y = self.pose[0], self.pose[1]
        for a, b in ROADS.lanes:
            tip, join = (a, b) if a.startswith(("dock_", "park_")) else (b, a)
            if not tip.startswith(("dock_", "park_")):
                continue
            tx, ty = ROADS.nodes[tip]
            jx, jy = ROADS.nodes[join]
            if math.hypot(tx - x, ty - y) < math.hypot(jx - x, jy - y):
                # Past the junction, heading up the dead end.
                if roads._clearance((x, y), (tx, ty), (jx, jy)) < ROBOT_W:
                    return True
        return False

    def drive(self):
        """Step the controller once, from the node's timer."""
        if self.pose is None:
            return              # no ground truth yet — never command blind

        x, y, yaw = self.pose
        self._step_battery(moving=math.hypot(*self.vel) > MOVING_MIN)

        # THE HALT REASON IS THIS CYCLE'S, OR IT IS NOTHING.
        #
        # It recorded the last rule that ever stopped the robot and was never
        # cleared, so a robot that had been held once went on displaying
        # "holding — a robot is coming out of a dock" for the rest of the run,
        # parked in its bay 40 m from the nearest dock. Measured 2026-08-27
        # with ten robots: six robots showed that line and two were actually
        # held. It also made a throughput measurement read 47% of fleet-time
        # frozen by the hold when the true figure was far lower.
        #
        # Cleared here and set by whichever rule stops the robot later in the
        # same cycle, so what the view shows is what is happening now.
        self._halt_reason = None

        # A FLAT BATTERY STOPS THE ROBOT, which is the point of modelling one.
        # Until this existed a robot drove happily at 0% and the feature could
        # not fail — which meant it could not be trusted either.
        #
        # Not a fault to recover from here: something has to come and get it,
        # exactly as on a real floor. What the CSM must do is never let it
        # happen, and `can_move` is what stops it being given more work.
        if self.battery <= 0.0:
            if not self._noted_flat:
                self._noted_flat = True
                self.node.get_logger().warn(
                    f"{self._tag()}battery flat — stopped where it stands")
            self._stop("battery flat")
            return

        # RULE 2, THE OTHER HALF. Somebody near here is pausing at the road
        # edge on its way out of a dock, so stand still until it is out.
        #
        # Checked before anything else a moving robot would do, because the
        # whole point of the rule is that the robot leaving the dock does not
        # have to negotiate with anyone: it says stop, and everyone stops.
        # RULE 2, THE WAY IN. Every dock and every bay is outside both lanes,
        # so a robot going to one crosses a live lane to get there. It pauses
        # at the road edge exactly as it does on the way out.
        #
        # Decided BEFORE the hold below, so the flag the other robots read is
        # this cycle's and not last cycle's — this is the one place in the tick
        # where a robot both reads everybody else's pause and publishes its own.
        # RULE 3: hand the source station back the moment we are out of it.
        self._clear_of_source()

        crossing_stop = self._pause_before_crossing()

        # RULE 4's turn, published before the hold below reads it — the same
        # reason the crossing flag is set here and not later.
        self._note_turning()

        if self._held_for_a_leaver():
            self._stop("holding — a robot is coming out of a dock")
            return

        if crossing_stop:
            return              # already stopped, with the reason recorded

        # ===================== TRAFFIC — EVERY ROBOT ========================
        #
        # A ROBOT IS A ROBOT. Carrying a roll, reversing out of a bay, driving
        # home or parked — it is a body in an aisle and it blocks the others
        # exactly the same. So right of way is applied to the ROBOT, before
        # anything asks what job it happens to be doing.
        #
        # These rules used to live INSIDE the "driving to a goal" branch below,
        # which made obeying them a property of HAVING WORK. Every other state
        # returned before reaching them and was silently exempt. All three were
        # measured in one session on 2026-08-10:
        #
        #   idle      "amr3 gives way to amr2"  and no "stepping aside" ever
        #   exit leg  "amr3 gives way to amr2"  -> "could not clear SLT_LD1 in 8s"
        #   homing    kept a junction 36 m from where it had parked
        #
        # Each time the fleet correctly told a robot to move and the robot was
        # on a code path where that instruction did not exist. The yielder is
        # picked by name and amr3 is idle 63% of the time against amr1's 2%, so
        # amr3 met the gap constantly and looked broken while being identical.
        #
        # Fixing it per-state was tried and is the wrong shape: the rule would
        # then live in four places and the next state added would miss it again.
        target = ((self._from if self._leg == "collect" else self._to)
                  if self._active_job is not None else None)

        # LAYER 1 — THE LAST WORD BEFORE ANY VELOCITY IS PUBLISHED.
        #
        # _threat() is the only thing that knows STOP_GAP, and it was wired to
        # exactly two places: the homing path, and the question "who yields?".
        # It never stopped anything on a normal job leg. A head-on meeting was
        # covered because it routed into the give-way handshake above; a robot
        # CROSSING our path, or catching us from behind, produced no stop at
        # all. What was left was _repulsion(), which does see robots but is
        # deliberately bounded so it "steers the robot without ever becoming the
        # thing that drives it" — it nudges, it does not halt.
        #
        # Measured 2026-08-10 on the build that had every other fix in place:
        # amr1 and amr2 overlapped for 225 samples, about 7.5 seconds, while the
        # run reported 82 deliveries and zero failures. Job success is not a
        # safety signal.
        #
        # So it goes here, after the handshake and before the job dispatch: past
        # this line every path — driving, docking, reversing out, homing — has
        # been checked. Reaching it means no encounter is being negotiated, so
        # anything still on course to touch us is a plain stop.
        #
        # This can leave two robots frozen facing each other, and that is the
        # correct failure for this layer: "layer 1 only ever says stop: it
        # cannot say who goes" (see the junction control note above). Deciding
        # who moves is the job of the rules above it, not of this one.
        # RULE 5. THREE METRES BEHIND THE ROBOT IN FRONT, IN THIS LANE.
        #
        # Checked BEFORE layer 1, deliberately. Layer 1 is the last physical
        # stop and it can only say stop — reaching it between two robots on the
        # same lane means both are frozen and neither recovers. This rule stops
        # the one behind while there is still 1.4 m of air, so layer 1 is never
        # the thing that separates two robots following each other.
        #
        # It lives here rather than inside the driving branch below so it holds
        # on every leg — driving to a goal, backing out, homing. It was wired
        # only into the homing path, which is how amr1 came to close from 2.4 m
        # to 0.26 m behind amr2 on a job leg with nothing telling it to slow.
        #
        # Standing still behind another robot is not a stall: the robot ahead
        # will move, and failing this robot's job for waiting its turn is what
        # the stall clock is reset for.
        if self._goal is not None:
            infront = self._ahead_in_my_lane(
                x, y, self._goal[0] - x, self._goal[1] - y)
            if infront is not None:
                self._reset_stall()
                self._stop(f"3 m rule: {infront.name} is in front")
                return

        blocker = self._threat()
        if blocker is not None:
            self._reset_stall()
            # LAYER 1 CANNOT SAY WHO GOES — so if it has been saying STOP about
            # the same robot for long enough, ask the layer above to decide.
            self._stop("layer 1: on course to touch another robot")
            return

        # THE RED LIGHT BEHIND A YIELDER. Layer 1 sees only closing geometry,
        # and a robot standing aside is stationary, so the gap to it never
        # closes and it never stops anybody. That is right for a robot gone to
        # its dock and wrong for one holding a gap open — the gap belongs to
        # the robot it is yielding for, and everybody else queues.
        #
        # Placed after layer 1 rather than inside it because layer 1 is about
        # collision and this is about right of way. They answer different
        # questions and mixing them is what made a yielder and a docked robot
        # indistinguishable in the first place.

        # ======================= WORK — WHAT IS IT DOING? ===================
        #
        # Reversing out of a bay after finishing. Nothing else may happen until
        # the robot is clear, including taking a new job — it still holds the
        # interlock, and the next robot is waiting on it.
        # RULE 6. WAITING IN THE DOCK FOR THE NEXT JOB.
        #
        # Checked before the exit leg, because the exit leg is what this
        # postpones. Standing still here is not a stall — the robot is exactly
        # where it should be — so the stall clock is held off.
        if self._linger_until is not None:
            if self._now() < self._linger_until:
                self._reset_stall()
                self._stop("waiting in the dock for the next job")
                return
            # Twenty seconds, no work. Back out and go home.
            self._linger_until = None
            if self._exit_station in EXIT_POSES:
                self._exit_goal = EXIT_POSES[self._exit_station]
                self.node.get_logger().info(
                    f"{self._tag()}no work in {LINGER_SECONDS:.0f}s — "
                    f"leaving {self._exit_station}")

        if self._exit_goal is not None:
            self._drive_to_exit()
            return

        # GO HOME WHEN THERE IS NOTHING TO DO. A robot that simply stops where
        # it finished stops ON A LANE, and then it is a road block: measured,
        # amr1 ended a job on the north aisle, amr2 came along, its protective
        # field correctly refused to drive into it, and the stall detector then
        # failed amr2's job eight seconds later. Two idle robots 1.6 m apart,
        # blocking the through-lane for everyone.
        #
        # Parking bays are already off the aisles, one per AGV class at the end
        # of that class's own run. See the ADR
        # docs/adr/2026-08-07-job-timeout-and-idle-parking.md
        if self._active_job is None or self._goal is None:
            self._go_home()
            return

        # DOCKING OWNS THE TICK once it has started. It is a distinct mode with
        # its own guards and its own timeout, and it must not be re-entered
        # through the waypoint logic: the robot sits inside the approach
        # tolerance for the whole manoeuvre, so an arrival check ahead of this
        # would return every cycle and the dock would never be driven at all.
        if self._docking:
            return self._run_docking(target)

        gx, gy = self._goal
        ex, ey = gx - x, gy - y
        distance = math.hypot(ex, ey)

        # ENTRY INTERLOCK. Ask before approaching, and hold outside if refused.
        #
        # The waiting happens at the node BEFORE the machine, deliberately: a
        # robot that drives up and then discovers the bay is taken has wasted
        # the trip and is now in the way. Asking from a distance costs nothing.
        #
        # Standing still here is NOT a stall, so the stall clock is reset while
        # waiting — otherwise a robot politely queueing would fail its own job
        # after eight seconds.
        if (self.fleet is not None and self._final_leg
                and distance < self.entry_request_range):
            if not self.fleet.request_entry(target, self.name or "robot"):
                if not self._noted_hold:
                    self._noted_hold = True
                    self.node.get_logger().info(
                        f"{self._tag()}holding outside {target} — occupied")
                self._reset_stall()
                self._stop("entry refused: bay occupied")
                return
            self._noted_hold = False

            # AND THE MACHINE'S OWN PERMISSION, which is a different question.
            #
            # `request_entry` above is the FLEET's interlock: one robot per bay,
            # arbitrated between robots. This is the MACHINE saying whether it
            # is safe to come in at all — MC_Enter_Permitted — and it is not a
            # flag. Condition 7: entry is permitted only once the signal has
            # been received CONTINUOUSLY for longer than the comm-alarm time.
            # A signal that flickers satisfies a boolean check and violates the
            # rule, so the answer has to be asked every cycle and the duration
            # accumulated. `handshake.py` holds that; here it is consulted.
            #
            # AGV_Entering is asserted from the moment we are docking, and
            # keeps being asserted until we are out. Rule 2: the machine may
            # not move while it is set, and rule 3 says the machine only
            # believes we have left after PROLONGED SILENCE — so it must not
            # lapse merely because we stopped looking.
            if not self._machine_permits(target):
                return

        # Loading and unloading take real time on a real line. Standing still
        # during a dwell is not a stall, so this is checked before _check_stall.
        if self._dwell_until is not None:
            if self._now() < self._dwell_until:
                self._stop("dwelling at the port")
                return
            # `_begin_delivery` may refuse — RULE 3, the destination is not
            # free yet — so it clears the dwell itself, on success only.
            # Clearing it here meant one attempt and then falling through this
            # branch for ever with the leg never advanced.
            self._begin_delivery()
            return

        # WAYPOINT REACHED. Intermediate waypoints are corners on the road, not
        # destinations: step to the next one and carry on in the same pass. Only
        # the last waypoint is the dock, and only that counts as arriving.
        #
        # The tolerance is looser out on the lanes than at a machine. A corner
        # does not have to be hit precisely, and demanding dock accuracy at every
        # turn would have the robot creeping around the whole ring.
        #
        # ...EXCEPT WHERE THE ROUTE TURNS OFF ONE LINE ONTO ANOTHER, and there
        # the loose tolerance draws the diagonal all by itself. `_turn_here`
        # has the arithmetic; the short version is that letting go of a spur
        # junction 0.60 m early aims the robot at the junction on the other
        # lane from atan2(1.80, 0.60) = 72 degrees instead of 90, and the
        # avoidance field then widens that to the 60-odd degrees measured in
        # the 16:35 run. The router had already been made to plan square
        # (`roads._along_a_line`); this is the driver drawing a slant across a
        # square plan.
        reach_at = (self.turn_tolerance if self._turn_here()
                    else self.waypoint_tolerance)
        if not self._final_leg and distance <= reach_at:
            self._waypoints.pop(0)
            self._goal = self._waypoints[0]
            self._reset_stall()
            gx, gy = self._goal
            ex, ey = gx - x, gy - y
            distance = math.hypot(ex, ey)

        # HANDOFF TO DOCKING. Reaching the last waypoint is not arriving — it is
        # arriving at the APPROACH POINT, a couple of metres out. The lane
        # network navigates by map position, and the map only knows where we
        # drew the machine; the last stretch is closed against the marker fixed
        # to the real machine instead. See adapters/docking.py.
        if self._final_leg and distance <= self.tolerance:
            # SQUARE UP BEFORE ENTERING. The robot must be PARALLEL to the
            # machine face before it crabs in, and nothing made it so: heading
            # is held inside a bay, so whatever tilt it carried up the spur was
            # preserved all the way to the dock.
            #
            # A tilt costs reach. Square on, the robot presents its half-width,
            # 0.45 m, into a 0.229 m gap. At 11.4 deg the corner reaches
            #   0.45*cos(11.4) + 0.8*sin(11.4) = 0.599 m
            # so it TOUCHES the machine while its centre still reads 0.60 m —
            # measured exactly that, then 40 s of no motion and a timeout. It
            # was not stuck for want of command: 0.0075 m/s moves this robot
            # 0.0067 m/s, so the correction was executable. It was in contact.
            #
            # The source project aligns first (the ICR arc) and only then
            # crabs. This is that alignment, simplified: the spurs are
            # perpendicular to the face, so "parallel" is one rotation.
            if self._square_up(yaw, target):
                return
            self._begin_docking(target)
            return self._run_docking(target)

        if self._check_stall(x, y):
            return

        # Attraction: goal direction in the body frame. The platform crabs, so
        # this becomes vx/vy directly with no heading change.
        ax, ay = _to_body(ex, ey, yaw)
        norm = math.hypot(ax, ay) or 1.0
        ax, ay = ax / norm, ay / norm

        # Fade avoidance out as the robot docks. The approach point is
        # deliberately close to a machine, so full-strength repulsion there
        # would push the robot away from the very place it is trying to reach —
        # the classic "goal near an obstacle" deadlock in a potential field.
        # Beyond dock_fade_m the field is at full strength; at the goal it is
        # zero, so the last stretch is committed.
        # The fade belongs to the FINAL hop only. Out on the lanes the robot is
        # in open floor with other robots about and needs full avoidance; it is
        # only at the machine that repulsion has to yield, because the dock is
        # deliberately close to something solid. Fading at an intermediate
        # waypoint blinded the robot in exactly the places it had room to steer.
        fade = (min(1.0, distance / self.dock_fade_m) if self._final_leg
                else 1.0)
        (rx, ry), closest = self._repulsion()
        self._closest_obstacle = closest
        vx = ax + fade * rx
        vy = ay + fade * ry

        # Ease down near the goal so the robot settles inside the tolerance band
        # instead of overshooting and hunting.
        speed = min(self.max_speed, 0.8 * distance)
        mag = math.hypot(vx, vy) or 1.0
        vx, vy = vx / mag, vy / mag

        # TURN TOWARD THE GOAL rather than crabbing everywhere.
        #
        # This used to command linear x and y only, so the robot never rotated —
        # it slid sideways and backwards to reach anything. That puts the
        # required wheel angle on the ±90° fold boundary, where the inverse
        # kinematics has two equally valid answers: point at +89° and drive
        # forward, or point at −89° and drive back. It flipped between them
        # every cycle, and the robot juddered forward-backward on the spot
        # without getting anywhere.
        #
        # Driving mostly forwards keeps the solution well away from that
        # boundary. Crab is still available and still used for the last stretch,
        # where the offset is small and the angle is nowhere near ±90°.
        heading_err = math.atan2(vy, vx)
        cmd = Twist()

        # HOLD HEADING ON THE FINAL SPUR, AND CRAB IN.
        #
        # The docking cameras are SIDE mounted (d435_left / d435_right), so the
        # marker has to stay off to one side. Turning to face the machine — which
        # is what the rule below would do, since the spur runs perpendicular to
        # the aisle — swings the marker to bearing 0, where neither camera can
        # see it. Measured on this layout: the ASRS marker is visible from the
        # approach point at yaw 0 and 30 deg, and NOT visible at 60 or 90.
        #
        # So on the last hop the body keeps its aisle heading and slides in
        # sideways, which is exactly how the docking project approaches a dock.
        #
        # The turn rule exists because crabbing everywhere put the wheel angle on
        # the +-90 deg fold, where the inverse kinematics has two equally valid
        # answers and flipped between them every cycle. A STEADY 90 deg crab does
        # not do that: commanding linear.y = 0.4 directly moved this robot 2.36 m
        # in 6 s, smoothly. The judder came from a heading error that kept
        # changing sign, not from the angle itself.
        # ... and equally on the way OUT. The first hop of the next leg is the
        # spur junction, which is a normal leg, so the turn rule fired and the
        # robot spun ~80 deg while still in the bay before driving out
        # nose-first. Measured leaving the ASRS dock:
        #
        #   DOCK  (-17.00, 6.33)  yaw  -16.3
        #   DOCK  (-17.12, 6.00)  yaw  -66.1
        #   SPUR  (-17.30, 5.35)  yaw  -95.3
        #
        # That cannot be done without contact: rotating swings a corner 0.468 m
        # further than the flat side, into a 0.229 m gap. It also explains why
        # it only happened sometimes — the rule turns only when the heading
        # error exceeds the crab window, so a robot already pointing roughly the
        # right way crabbed out cleanly.
        # A PARKING SPUR IS AS NARROW AS A DOCK, AND WAS NOT COVERED.
        #
        # `_in_a_bay` is the STATION test — within BAY_RADIUS of a machine
        # marker. A parking slot is not a station and has no marker, so a robot
        # leaving its bay fell through to the `else` below and rotated while it
        # drove out, swinging a corner into the neighbouring bay.
        #
        # Measured 2026-08-25 with five robots: amr4 sat in leg C slot 2 unable
        # to leave while amr5 manoeuvred beside it at 128 degrees, 0.23 m away.
        # Parking slots are PARK_PITCH = 2.15 m apart and two turning robots
        # need 2.14 m, so the manoeuvre has one centimetre of headroom — and a
        # robot that crabs straight out does not need any of it.
        #
        # The platform crabs, so heading is optional while travelling. Out
        # first, turn on the road. The route already does the right thing: the
        # first waypoint from a parking slot IS its own junction, straight out
        # along the spur.
        # A LINE FOLLOWER TURNS WHERE THE LINE TURNS.
        #
        # RULE 5 — turn only at the four corners — was a rule because the robot
        # could crab anywhere and therefore had to be told not to. On a
        # two-lane road it follows the lane, and the lane only turns at the
        # corners, so the behaviour falls out of the road and needs no rule.
        #
        # Sideways motion survives for going in and out of a dock, where the
        # robot must square up to a machine face; that is `_square_up` and the
        # docking path, which this branch does not touch.
        # AND NOT WHILE CROSSING A LANE. The crossing hop is not the final
        # leg, is not in a bay and is not yet on the spur, so the turn rule
        # fired there and swung the robot from its aisle heading toward the
        # junction — with its body over a live lane. Rotating reaches the
        # half-diagonal, 0.918 m, against 0.450 m held flat: the 0.65 m of air
        # ROAD_EDGE leaves becomes 0.18 m, which is inside layer 1's own stop
        # distance. The turn is also pure waste — the final leg holds the
        # aisle heading and crabs in, so the robot only has to turn back.
        if (self._final_leg or self._in_a_bay() or self._on_a_spur()
                or self._pausing_in):
            cmd.angular.z = 0.0
        else:
            cmd.angular.z = max(-self.max_turn, min(self.max_turn,
                                                    self.turn_gain * heading_err))
            if abs(heading_err) > self.crab_window:
                speed *= max(0.0, math.cos(heading_err))

        cmd.linear.x = vx * speed
        cmd.linear.y = vy * speed
        self.pub_cmd.publish(cmd)

    #: How square with the lane is square enough to drive out of a corner.
    #:
    #: At 5 degrees a 1.6 x 0.9 m robot is 0.518 m across where a perfectly
    #: aligned one is 0.450 m — 0.068 m of extra width, about a quarter of the
    #: 0.30 m margin. Tightening it costs time turning at every corner and buys
    #: little: 2 degrees still costs 0.028 m, so the curve is shallow here.
    #: What it must NOT be is loose — at 20 degrees the robot is 0.696 m
    #: across, which is the crooked driving this tolerance exists to stop.

    def _drive_to_exit(self):
        """Back out to the waiting spot, then release the bay.

        RULE 2 lives here. On the way out the robot stops short of the road,
        tells the robots near it to stand still, and only then drives on.
        """
        x, y, yaw = self.pose
        gx, gy = self._exit_goal
        distance = math.hypot(gx - x, gy - y)

        # RULE 2. PAUSE BEFORE THE ROAD, HOLD EVERYONE NEAR, THEN GO.
        #
        # `ROAD_EDGE` back from the lane is where the robot's own body is still
        # clear of it, so a robot waiting here is not itself an obstacle. It
        # holds while anything is standing in the way of its path onto the
        # road; the moment nothing is, it lets go and drives out.
        #
        # THE HOLD RUNS UNTIL IT IS OUT, not until it commits. It used to be
        # cleared here the moment `distance` fell inside ROAD_EDGE — which is
        # the moment the robot starts entering the lane. Every robot it had
        # told to stand still began moving again exactly then, into the road it
        # was driving onto. `_release_exit` is where being out is decided, so
        # that is where the hold ends.
        #
        # The BLOCKER question still belongs to the near side only. Past
        # ROAD_EDGE the robot is in the lane and there is nowhere to stop: the
        # lanes are LANE_GAP = 1.80 m apart and the robot is 0.90 m wide, so
        # stopping half way out is stopping in the road. Decide before you
        # commit, then go.
        self._pausing_out = True
        self._pause_goal = (gx, gy)
        if distance > ROAD_EDGE:
            blocker = self._crossing_blocker(x, y, (gx, gy), distance)
            if blocker is not None:
                self._reset_stall()
                self._stop(f"pausing before the road — {blocker.name} in the way")
                return

        if distance < self.tolerance:
            station = self._exit_station
            self._release_exit()
            self.node.get_logger().info(
                f"{self._tag()}clear of {station} — waiting outside")
            return

        # STALL GUARD. Arriving was the only way out of this leg, so a robot
        # that cannot reach the waiting spot — wedged, or blocked by another
        # robot — drives at the exit pose forever. Nothing upstream notices,
        # because with _active_job already cleared the fleet reports it "idle"
        # the whole time it is driving.
        #
        # Measured 2026-08-06: amr1 backed out of 1A03, never arrived, and kept
        # driving about 5 m across the hall into the pillar at (0, 2.0), where
        # it wedged and stayed for the rest of the run.
        #
        # Giving up releases the bay. Holding it would strand the next robot on
        # behalf of one whose job is already over.
        if self._exit_stalled(x, y):
            self.node.get_logger().warn(
                f"{self._tag()}could not clear {self._exit_station} in "
                f"{self.stall_seconds:.0f}s — giving up and releasing the bay")
            self._release_exit()
            return

        # Full avoidance on the way out: there is no goal near a machine to
        # protect here, so nothing has to fade. This is the one leg where a
        # robot is most likely to meet another coming in.
        rep = self._repulsion()[0] if hasattr(self, "_repulsion") else (0.0, 0.0)
        rx, ry = (rep if isinstance(rep, tuple) else (0.0, 0.0))

        # ROTATE THE ERROR INTO THE BODY FRAME. cmd.linear is a BODY velocity;
        # the error is in world coordinates. This leg used the world error
        # directly, and the repulsion it added is already body-frame, so two
        # frames were being summed.
        #
        # At yaw 0 the two frames coincide and it worked, which is why it looked
        # fine sometimes. At yaw 180 the command is exactly REVERSED: the robot
        # drives away from the spot it is trying to reach. Measured — amr2, exit
        # goal at (-11.2, -3) to the south-east, yaw -178.5:
        #
        #   t+319  (-16.4, +3.0) ->None  v=0.62      job ends, exit leg starts
        #   t+325  (-18.7, +5.6) ->None  v=0.56      driving away from it
        #   t+344  (-21.8, +12.5)->None  v=0.00      stopped by the corner
        #
        # It also explains the "could not clear ... in 8s" failures: a robot
        # driving the wrong way never arrives, so it always stalled out.
        ex, ey = _to_body(gx - x, gy - y, yaw)
        n = math.hypot(ex, ey) or 1.0
        vx, vy = ex / n + rx, ey / n + ry
        m = math.hypot(vx, vy) or 1.0
        speed = min(self.max_speed, 0.8 * distance)

        cmd = Twist()
        cmd.linear.x = vx / m * speed
        cmd.linear.y = vy / m * speed
        self.pub_cmd.publish(cmd)

    def _ahead_in_my_lane(self, x, y, ex, ey):
        """RULE 5: the robot less than FOLLOW_GAP in front, in this lane.

        THE ONE BEHIND STOPS, and that falls out of the arithmetic rather than
        needing to be decided: `along` is positive only for a robot in front of
        us, so the robot in front never sees us and never stops for us. Both
        stopping is what layer 1 does, and it is why layer 1 deadlocks.

        Measured from the direction of TRAVEL, not the nose. On a lane those
        are the same once rule 4 has turned the robot, and they are not the
        same while it is still turning at the junction — where it must still
        not be driven into.
        """
        n = math.hypot(ex, ey)
        if n < 1e-9:
            return None
        fx, fy = ex / n, ey / n
        for other in self._fleet_others():
            dx, dy = other.pose[0] - x, other.pose[1] - y
            along = dx * fx + dy * fy
            if along <= 0.0 or along > FOLLOW_GAP:
                continue                  # behind us, or far enough ahead
            if abs(-dx * fy + dy * fx) < FOLLOW_SIDE:
                return other
        return None

    def _robot_ahead(self, x, y, ex, ey):
        """The other robot inside the protective field, or None.

        Returns the ROBOT, not its name: giving way has to ask where the other
        one is going, not merely that it is there. Callers wanting a label use
        `.name`.

        Fleet poses, not the scanners, and on purpose: a range reading cannot
        tell a robot from the machine being docked to, and the approach point
        sits only 1.6 m from a solid machine. A protective field driven by range
        alone would refuse to let the robot dock at all — which is precisely why
        the dock fade exists. Robot positions are known exactly, so this can
        stop for robots and still allow docking.

        Only the corridor AHEAD counts. The platform crabs, so "ahead" is the
        direction of travel — the goal vector — not where the nose points.
        """
        if self.fleet is None:
            return None
        goal = (x + ex, y + ey)
        for other in self.fleet.robots:
            if other is self:
                continue
            if self._blocks_path(other, x, y, goal):
                return other
        return None

    #: How far along the lane two robots must be apart to pass each other at a
    #: spur mouth. DERIVED FROM THE BODIES, not chosen.
    #:
    #: A robot crossing a lane holds its aisle heading — `_on_a_spur` and the
    #: crossing pin both keep it there — so it lies ALONG the lane, and so does
    #: the robot travelling on the lane. Half a length each, plus the air:
    #:
    #:     1.6/2 + 1.6/2 + 0.30 = 1.90 m
    #:
    #: `ROBOT_STOP_SIDE` is 1.20 m and was doing this job. Measured 2026-08-26
    #: 17:04, the CTR2_ULD spur mouth: amr4 stood 1.81 m along the lane from
    #: amr3's crossing. 1.90 > 1.81 > 1.20 — so the corridor called it clear,
    #: amr3 committed, and layer 1 stopped it BETWEEN THE TWO LANES, where the
    #: 1.80 m gap has no room for a 0.90 m robot to stand out of the way.
    #: amr3 then waited for amr4, amr4 was held by amr3, amr5 queued behind
    #: amr4, and the three of them stayed there. Three margin breaches, closest
    #: 0.18 m.
    CROSS_SIDE = plant.ROBOT_L + STOP_GAP

    def _crossing_blocker(self, x, y, goal, reach):
        """The robot in the way of a crossing, or None. RULE 2's "path clear".

        `_blocks_path` is the protective field a robot drives behind: a fixed
        2.4 x 1.2 m corridor, right for following a lane and wrong for stepping
        across one. A crossing is a different shape and a different length —
        `reach` is the whole move, from here to standing clear on the far side,
        because a robot that stops half way across has stopped in the road.
        """
        fx, fy = goal[0] - x, goal[1] - y
        n = math.hypot(fx, fy)
        if n < 1e-9:
            return None
        fx, fy = fx / n, fy / n
        for other in self._fleet_others():
            dx, dy = other.pose[0] - x, other.pose[1] - y
            along = dx * fx + dy * fy
            if along < 0.0 or along > reach:
                continue
            if abs(-dx * fy + dy * fx) < self.CROSS_SIDE:
                return other
        return None

    def _blocks_path(self, other, x, y, goal):
        """Is `other` standing in the protective corridor from here to `goal`?

        The corridor arithmetic of `_robot_ahead` for ONE named robot, so that
        a route can be tested before it is driven rather than discovered to be
        blocked halfway along it. `_robot_ahead` is this asked about everybody.

        Kept as the single copy on purpose. The planner needs exactly the
        test that will later stop the robot, and a second implementation of it
        would drift from this one — at which point the planner would choose
        lay-bys the driver refuses to drive to, which is the 2026-08-24 deadlock
        with extra steps.
        """
        if other is None or other.pose is None:
            return False
        ex, ey = goal[0] - x, goal[1] - y
        n = math.hypot(ex, ey)
        if n < 1e-9:
            return False
        fx, fy = ex / n, ey / n
        dx, dy = other.pose[0] - x, other.pose[1] - y
        along = dx * fx + dy * fy
        if along <= 0.0 or along >= ROBOT_STOP_AHEAD:
            return False                  # behind us, or far enough off
        return abs(-dx * fy + dy * fx) < ROBOT_STOP_SIDE

    # ------------------------------------------------------------ giving way

    def _travel_dir(self):
        """Unit vector this robot is currently travelling along, or None.

        The goal vector, not the nose: the platform crabs, so where it points
        and where it moves are different things.
        """
        if self.pose is None or self._goal is None:
            return None
        ex, ey = self._goal[0] - self.pose[0], self._goal[1] - self.pose[1]
        n = math.hypot(ex, ey)
        return (ex / n, ey / n) if n > 1e-9 else None

    def _threat(self, exclude=None):
        """The robot we are on course to touch, or None. LAYER 1.

        :param exclude: a robot to ignore — used only while standing aside, so
            that the partner we are already negotiating with does not freeze the
            very manoeuvre that resolves the encounter. Everybody else still
            stops us.

        Samples both bodies forward at their MEASURED velocities and reports the
        first whose gap would close below STOP_GAP. No cases and no corridor:
        head-on, following, crossing a junction and meeting at a corner are all
        the same arithmetic, and a robot standing still is ignored because a
        constant separation never closes — which is what lets another robot
        drive past one parked in a spur.
        """
        if self.fleet is None or self.pose is None:
            return None
        steps = int(LOOKAHEAD_S / LOOKAHEAD_STEP_S) + 1
        for other in self.fleet.robots:
            if other is self or other is exclude or other.pose is None:
                continue
            for k in range(steps):
                t = k * LOOKAHEAD_STEP_S
                pa = (self.pose[0] + self.vel[0] * t,
                      self.pose[1] + self.vel[1] * t, self.pose[2])
                pb = (other.pose[0] + other.vel[0] * t,
                      other.pose[1] + other.vel[1] * t, other.pose[2])
                if _seg_gap(pa, pb) < STOP_GAP:
                    return other
        return None


    def _fleet_others(self):
        """Every other robot with a pose. One place, so nothing forgets self."""
        if self.fleet is None:
            return ()
        return [r for r in self.fleet.robots if r is not self and r.pose is not None]

    @property
    def _pausing(self):
        """Taking more room than usual, so the robots near it must stand still.

        RULE 2 is one rule with two halves and the robots around it cannot tell
        them apart: a body stopped at a spur mouth about to enter the lane is
        the same body whichever direction it is about to go.

        AND TURNING COUNTS. The hold used to end the instant the crossing
        ended — and the turn happens straight after, which is exactly when the
        robot stops presenting 0.450 m and starts sweeping 0.918 m. Measured
        2026-08-27: amr6 on the inner lane and amr7 on the outer, both off the
        GRV2_ULD spur, both mid-turn, 1.93 m apart. Two turning robots need
        0.918 + 0.918 + 0.30 = 2.14 m. Both stopped on layer 1 and neither
        recovered. Nothing had held either of them, because by then the
        crossing was over.
        """
        return self._pausing_out or self._pausing_in or self._turning

    #: How much room a turning robot needs around it. DERIVED, not chosen.
    #:
    #: Two robots turning at once each sweep their half-diagonal, plus the air
    #: between them: 0.918 + 0.918 + 0.30 = 2.14 m. That is the worst case, so
    #: it is the one to hold.
    #:
    #: It is deliberately far smaller than HOLD_RADIUS. A turn takes 1.7 s and
    #: endangers only what is beside it — holding everything within 6 m for
    #: that would stop the plant every time a robot rounded a corner.
    TURN_ROOM = math.hypot(plant.ROBOT_L, plant.ROBOT_W) + STOP_GAP

    def _note_turning(self):
        """RULE 4's turn. Sets `_turning`, so the hold can cover it.

        A turn only happens where the heading is NOT pinned — not on the final
        leg, not in a bay, not on a spur, not mid-crossing — which is to say
        at a junction or a corner, on the road. That is the one place the
        robot needs more room than its own width.

        Measured against the goal vector, not the nose, and against the same
        `crab_window` the driver itself uses, so this cannot disagree with the
        turn it is reporting.
        """
        self._turning = False
        if self.pose is None or self._goal is None:
            return
        if (self._final_leg or self._in_a_bay() or self._on_a_spur()
                or self._pausing_in):
            return                        # heading is pinned; no turn here
        ex, ey = self._goal[0] - self.pose[0], self._goal[1] - self.pose[1]
        if math.hypot(ex, ey) < 1e-6:
            return
        ax, ay = _to_body(ex, ey, self.pose[2])
        if abs(math.atan2(ay, ax)) <= self.crab_window:
            return                        # near enough square to drive on
        self._turning = True
        if not (self._pausing_out or self._pausing_in):
            # A turning robot is not going anywhere — it is standing on the
            # spot taking up room. Where it stands IS what the others must
            # keep clear of.
            self._pause_goal = self.pose[:2]

    #: How near the lane the robot has to be before the crossing rule engages.
    #:
    #: A robot on the inner lane is exactly LANE_GAP from the outer one, so
    #: anything further out has not turned onto the spur yet. The extra width
    #: is for a robot that is not sitting perfectly on its line.
    CROSS_ENGAGE = plant.LANE_GAP + plant.ROBOT_W

    def _crossing(self):
        """The lane this robot is about to drive ACROSS, or None.

        Returns ``(goal, gap)`` — the point it is steering at, and how far it
        still has to go before it reaches the lane. `gap` counts down to zero
        at the line and goes negative once the robot is past it. IN OR OUT: the
        sign is taken from where the goal is relative to the line, not from an
        assumed direction, because crossing a lane is one manoeuvre and a robot
        stopped half way across it is stopped in the road either way.

        WHY THERE IS ANYTHING TO CROSS. All 27 docks and all 10 parking bays
        sit outside BOTH lanes, so a spur crosses the outer lane whichever way
        the robot is going.

        THREE WAYS TO BE ON A SPUR, AND THIS COVERS ALL THREE. They were found
        one at a time, each by a jam:

        - GOING IN to a dock or bay. Measured 2026-08-26 15:36:24 — amr2
          eastbound on the south outer lane, amr3 crossing it on the SLT_LD3
          spur; contact, gap -0.007 m.
        - BACKING OUT, which `_drive_to_exit` owns and this leaves alone.
        - LEAVING THE DOCK ON A NEW JOB, which is neither. The back-out leg
          ends at the outer junction and releases; the robot then takes a job
          whose first waypoint is its own INNER junction, and drives from the
          dock straight across both lanes. `_pausing_out` is for the exit leg
          and `_pausing_in` used to be for a goal BEYOND the lane, so this
          crossing held nobody and asked nobody. Measured 2026-08-26 17:2x:
          amr5 0.84 m up the CTR1_ULD spur bound for SLT_LD1, amr2 stopped on
          the outer lane 0.33 m from that spur line, both frozen on layer 1
          and neither able to start.

        Three tests, and all three are needed. A lane must lie BETWEEN us and
        the waypoint we are steering at — that is what separates crossing a
        lane from driving along one; we must be near enough to it to have
        turned onto the spur; and we must be lined up on the spur rather than
        somewhere else on the same lane.
        """
        if self.pose is None or self._exit_goal is not None:
            return None               # backing out is the OTHER half, above
        if self._active_job is not None and self._goal is not None:
            station = self._from if self._leg == "collect" else self._to
            dest, goal = plant.DOCKS.get(station), self._goal
        elif self._homing and self._home_waypoints:
            # The bay, not `_home_target()`: asking again would re-claim a
            # charger every control cycle.
            dest, goal = self._home_waypoints[-1], self._home_waypoints[0]
        else:
            return None
        if goal is None:
            return None

        # WHICH LANE. Standing on a spur answers it directly; approaching one
        # from the hall does not, and there the destination answers it. The
        # answer is then REMEMBERED for the length of the manoeuvre, because
        # between the two lanes neither question works: the robot is beyond
        # nothing, and a destination on the far side of the plant names the
        # wrong lane.
        latched = self._crossing_lane
        lane = latched or plant.outer_lane_beyond(self.pose[:2]) \
            or (plant.outer_lane_beyond(dest) if dest is not None else None)
        if not lane:
            return None
        axis, value, outward = lane[0], lane[1], lane[2]
        i, j = (0, 1) if axis == "x" else (1, 0)

        here = (value - self.pose[i]) * outward   # + hall side, - dead-end side
        there = (value - goal[i]) * outward
        # WHICH WAY ACROSS. Positive `gap` means the line is still ahead.
        #
        # The waypoint sits exactly ON the line for one moment — a spur
        # junction IS the line — and in that moment it cannot say which side
        # the robot is heading for. Carrying the answer from the tick before
        # is the only honest thing to do, and a crossing is one manoeuvre, so
        # there is only ever one answer to carry.
        if abs(here - there) >= 1e-9:
            forward = 1.0 if there > here else -1.0
        elif latched is not None:
            forward = latched[3]
        else:
            return None
        gap = -here * forward

        if gap > self.CROSS_ENGAGE:
            return None               # not on the spur yet
        if gap <= -ROAD_EDGE:
            return None               # across, and the body is clear of it
        if gap <= plant.ROBOT_W / 2.0 and not self._pausing_in:
            # NEVER STARTED ON THE OTHER SIDE, so it never crossed anything. A
            # robot arriving ALONG the outer lane turns off the lane it is
            # already on; holding the neighbourhood for that would cost every
            # dock arrival in the plant and buy nothing. The deadband is half a
            # robot width, which is wider than a robot wanders off its line and
            # far short of the 1.55 m where the pause actually happens.
            return None
        if there * forward < -0.10:
            return None               # the waypoint is this side: not crossing
        if abs(self.pose[j] - goal[j]) > ROBOT_STOP_SIDE:
            return None               # alongside the spur, not lined up on it
        self._crossing_lane = (axis, value, outward, forward)
        return goal, gap

    def _pause_before_crossing(self):
        """RULE 2, THE WAY IN. True if the robot must stand still this cycle.

        The same rule as backing out, read the other way round: stop ROAD_EDGE
        short of the lane, tell every robot within HOLD_RADIUS to stand still,
        and cross when nothing is in the way.

        THE HOLD OUTLASTS THE PAUSE ON PURPOSE. It is set from the moment the
        robot stops short until its body is clear on the far side, not just
        while it is waiting — a hold that ended the instant the robot moved
        would release the lane into the one moment the robot is standing in it.
        """
        found = self._crossing()
        if found is None:
            self._pausing_in = False
            self._crossing_lane = None
            if not (self._pausing_out or self._turning):
                self._pause_goal = None
            return False

        goal, gap = found
        self._pause_goal = goal

        self._pausing_in = True
        if gap <= ROAD_EDGE:
            return False              # committed: crossing now, still holding

        # THE WHOLE CROSSING, not a fixed corridor. Reaching the lane is `gap`
        # and getting clear of it is CROSS_CLEAR more, and a robot that stops
        # between the two has stopped in the road.
        x, y = self.pose[0], self.pose[1]
        blocker = self._crossing_blocker(x, y, goal, gap + CROSS_CLEAR)
        if blocker is None:
            return False
        self._reset_stall()
        self._stop(f"pausing before the road — {blocker.name} in the way")
        return True

    def _clear_of_source(self):
        """RULE 3: free the source station once the robot is OUT of the bay.

        Out means past the junction its spur meets — the dock node is nearer
        than the junction while the robot is still up the spur, and further
        once it has driven onto the road. That is the same question
        `_on_a_spur` asks, asked about one named station instead of all of
        them.

        Checked every cycle rather than at a moment, because there is no
        single event that means "left the bay": the robot simply drives, and
        at some point it is out.
        """
        if self._holding_source is None or self.pose is None:
            return
        dock = plant.DOCKS.get(self._holding_source)
        join = plant.JOINS_OUTER.get(self._holding_source)
        if dock is None or join is None:
            self._holding_source = None
            return
        x, y = self.pose[0], self.pose[1]
        if math.hypot(dock[0] - x, dock[1] - y) <= math.hypot(join[0] - x,
                                                              join[1] - y):
            return                        # still nearer the dock: still in it
        if self.fleet is not None:
            self.fleet.release(self._holding_source, self.name or "robot")
        self._holding_source = None

    def _could_still_reach(self, point):
        """Could this robot still arrive at that point, or is it behind us?

        WHAT "NEAR IT" HAS TO MEAN. Rule 2 holds the robots near a crossing so
        that none of them drives into it. A robot that has already gone PAST
        the spur, or that is not on the road at all, cannot drive into
        anything — holding it buys nothing and costs the plant a robot.

        Measured 2026-08-27, amr2 backing out of GRV1_ULD (spur x = -10.56):

            amr1 (-8.25,+2.70)  on the inner lane, 2.31 m EAST of that spur
                                and driving east. Held. It had already passed.
            amr6 (-6.24,+7.71)  docked at GRV2_LD, off the road. Held.

        Both were inside HOLD_RADIUS and neither could have reached the
        crossing. Distance alone is the wrong question.
        """
        if self.pose is None or point is None:
            return False
        if self._on_a_spur() or self._in_a_bay():
            return False              # off the road; not going through anything
        direction = self._travel_dir()
        if direction is None:
            return False              # not going anywhere
        dx = point[0] - self.pose[0]
        dy = point[1] - self.pose[1]
        return dx * direction[0] + dy * direction[1] > 0.0

    def _held_for_a_leaver(self):
        """RULE 2: is a robot near here pausing at the edge of the road?

        Near is HOLD_RADIUS. Two exemptions, and only two.

        Near is HOLD_RADIUS **and able to get there**: see
        `_could_still_reach`. A robot that has passed the spur, or that is off
        the road, is not near the crossing in any sense that matters.

        A robot that is itself pausing does not stop for another one — two of
        them facing each other would both wait for ever — so the lower-numbered
        one carries on and the other gives it room.

        AND A ROBOT ALREADY STANDING IN THE PAUSER'S WAY IS NOT HELD. Holding
        it is what turns the pause into the deadlock the pause exists to
        prevent: the pauser waits for its path to clear, and the only robot
        that could clear it has just been told to stand still. HOLD_RADIUS is
        6 m and the path corridor is 2.4 m long, so this only bites when the
        other robot was already inside the corridor when the pause began —
        which is exactly the case that never resolves on its own.
        """
        if self.pose is None:
            return False
        x, y = self.pose[0], self.pose[1]
        mine = plant.robot_number(self.name) or 0
        for other in self._fleet_others():
            if not other._pausing:
                continue
            # A TURN IS A DIFFERENT SHAPE OF HAZARD FROM A CROSSING, and needs
            # a different question. A crossing robot is going somewhere, so
            # what matters is whether we could drive into where it is going. A
            # turning robot is going nowhere — it stands on the spot and sweeps
            # — so what matters is simply whether we are inside the sweep.
            # Direction is meaningless there: amr7 was directly BESIDE amr6,
            # not ahead of it, and a direction test let it drive on and turn.
            spinning = other._turning and not (other._pausing_out
                                               or other._pausing_in)
            room = self.TURN_ROOM if spinning else HOLD_RADIUS
            if math.hypot(other.pose[0] - x, other.pose[1] - y) > room:
                continue
            if self._pausing and (plant.robot_number(other.name) or 0) > mine:
                continue                  # we were here first, by number
            if spinning:
                return True               # inside the sweep: stand still
            if not self._could_still_reach(other._pause_goal):
                continue                  # past it, or not on the road at all
            if other._pause_goal is not None and other._crossing_blocker(
                    other.pose[0], other.pose[1], other._pause_goal,
                    HOLD_RADIUS) is self:
                continue                  # we ARE the obstruction — clear it
            return True
        return False

    def _release_exit(self):
        """Let go of the bay and stop. The only way out of the exit leg."""
        if self.fleet is not None and self._exit_station:
            self.fleet.release(self._exit_station, self.name or "robot")
        self._exit_goal = None
        self._exit_station = None
        self._pausing_out = False         # RULE 2: out of the dock, hold ends
        self._pause_goal = None
        self._reset_stall()
        self._stop("exit complete")

    def _exit_stalled(self, x, y):
        """_check_stall for the exit leg.

        Separate because _check_stall ends the job through _finish, and there
        is no job here — _finish is what started this leg. Same thresholds, so
        a robot that cannot back out gives up as readily as one that cannot
        reach a station.
        """
        now = self.node.get_clock().now().nanoseconds * 1e-9
        if self._stall_ref is None:
            self._stall_ref = (x, y)
            self._stall_since = now
            return False
        moved = math.hypot(x - self._stall_ref[0], y - self._stall_ref[1])
        if moved >= self.stall_distance:
            self._stall_ref = (x, y)
            self._stall_since = now
            return False
        return now - self._stall_since >= self.stall_seconds

    def _on_arrival(self, distance):
        """Reached the current leg's goal."""
        self._stop("arrived")
        if self._leg == "collect":
            self.node.get_logger().info(
                f"{self._active_job}: at {self._from} ({distance:.2f} m) — "
                f"loading for {self.dwell_seconds:.0f}s")
            self._dwell_until = self._now() + self.dwell_seconds
        else:
            self.node.get_logger().info(
                f"{self._active_job}: delivered to {self._to} "
                f"({distance:.2f} m from goal)")
            self._finish(self._active_job, TransportResult.ARRIVED)

    def _begin_delivery(self):
        """Loading finished — set off on leg 2, if the destination will have us.

        RULE 3, THE SECOND LEG. The robot does not come out onto the road until
        the station it is going to is free. If it is not, the robot stays in
        the source bay and asks again next cycle.

        THAT BLOCKS THE SOURCE, and that is the trade rule 3 makes: a robot
        waiting in a bay stops one machine, and a robot waiting on the road
        stops a whole lane. The bay is the cheaper place to wait.
        """
        if self.fleet is not None:
            if not self.fleet.request_entry(self._to, self.name or "robot"):
                if not self._noted_hold:
                    self._noted_hold = True
                    self.node.get_logger().info(
                        f"{self._tag()}loaded — waiting in {self._from} until "
                        f"{self._to} is free")
                self._reset_stall()
                self._stop(f"rule 3: {self._to} is not free yet")
                return
            self._noted_hold = False
        self._dwell_until = None
        self._leg = "deliver"
        # HOLD THE SOURCE UNTIL WE ARE OUT OF IT. Releasing it here — the
        # moment loading finished — handed the bay to the next robot while
        # this one was still standing 1.15 m up the spur. The next robot then
        # set off across the plant and met it coming down a 2.1 m spur where
        # neither can pass and neither can turn. `_clear_of_source` frees it.
        self._holding_source = self._from
        self._reset_stall()
        self._set_route(self._to)
        self.node.get_logger().info(
            f"{self._active_job}: leg 2/2 — carrying to {self._to} {self._goal} "
            f"via {len(self._waypoints)} waypoints")

    def _now(self):
        return self.node.get_clock().now().nanoseconds * 1e-9

    def _reset_stall(self):
        self._stall_ref = None
        self._stall_since = None

    def _check_stall(self, x, y):
        """True if the robot is driving but not moving. Fails the job.

        Ground truth is essential here: wheel odometry would happily report
        progress while the chassis is wedged against a pallet.
        """
        now = self.node.get_clock().now().nanoseconds * 1e-9

        if self._stall_ref is None:
            self._stall_ref = (x, y)
            self._stall_since = now
            return False

        moved = math.hypot(x - self._stall_ref[0], y - self._stall_ref[1])
        if moved >= self.stall_distance:
            self._stall_ref = (x, y)
            self._stall_since = now
            return False

        if now - self._stall_since >= self.stall_seconds:
            # Not an error — a robot that cannot get somewhere is a normal
            # situation on a floor with obstacles. Report it as a blocked path
            # so an operator can clear the route; the MES will re-raise the job
            # while the station still holds material.
            near = (f", nearest obstacle {self._closest_obstacle:.2f} m"
                    if self._closest_obstacle < float("inf") else "")
            self.node.get_logger().warn(
                f"{self._active_job}: PATH BLOCKED — moved {moved:.2f} m in "
                f"{self.stall_seconds:.0f}s while driving to {self._leg} goal"
                f"{near}. Giving up on this attempt.")
            self._finish(self._active_job, TransportResult.FAILED)
            return True
        return False

    def _apply_pending_charge(self):
        """Start a charge that was accepted while this robot was busy."""
        if self._charge_pending is None:
            return
        level, self._charge_pending = self._charge_pending, None
        self.start_charging(to_level=level)
        self._go_home()
        self.node.get_logger().info(
            f"{self._tag()}job done — going to charge to {level:.0f}%")

    def _finish(self, job_id, result):
        # Reported upward. The fleet owns the job -> result table, because a
        # caller asking "is job_7 done?" must get an answer whichever robot
        # happened to carry it — and after the robot has moved on to the next.
        if self.on_finished:
            self.on_finished(job_id, result)
        self._apply_pending_charge()

        # BACK OUT before the bay is released. The robot is physically in it
        # until it has driven clear, and freeing the interlock while it still
        # stands there invites the next robot to drive into it. Only on arrival
        # outside does the bay go free — see _arrive_at_exit.
        # RULE 6. STAY IN THE DOCK AND WAIT FOR THE NEXT JOB.
        #
        # `_exit_station` is claimed now but `_exit_goal` is not set yet, so
        # the robot keeps the bay and keeps standing in it. `_linger` sets the
        # exit goal when the twenty seconds run out. Backing out immediately is
        # what this replaces: the round trip home and back is pure traffic, and
        # traffic is what breaks.
        station = self._to if self._leg == "deliver" else self._from
        if station in EXIT_POSES:
            self._exit_station = station
            self._linger_until = self._now() + LINGER_SECONDS

        # A job that ends — done or failed — never keeps a station claimed.
        if self._holding_source is not None and self.fleet is not None:
            self.fleet.release(self._holding_source, self.name or "robot")
        self._holding_source = None

        self._active_job = None
        self._goal = None
        self._waypoints = []
        self._dock = None
        self._docking = False
        self._leg = None
        self._from = None
        self._to = None
        self._dwell_until = None
        self._stall_ref = None
        self._stall_since = None
        if self._exit_goal is None and self._linger_until is None:
            self._stop("no exit goal")

    def _stop(self, why="unspecified"):
        """Publish zero velocity, and REMEMBER WHY.

        A stopped robot is the hardest thing to diagnose in this system: every
        layer can stop one, the layers are deliberately independent, and the
        published Twist looks identical whichever said so. On 2026-08-18 two
        robots sat frozen for four minutes and the logs could not say which
        rule was holding either of them — the reason had to be reconstructed by
        reading the code, and that reconstruction was wrong twice.

        The reason costs one string assignment per cycle and turns "it is
        stuck" into "it is stuck because".
        """
        self._halt_reason = why
        self.pub_cmd.publish(Twist())



#: ERROR CODES THIS SIMULATED ACS RETURNS.
#:
#: ⚠ INVENTED. The real server returns one integer per mutation and its code
#: table is not in the schema — our analysis calls it "the single most important
#: thing still owed to us". These stand in so the simulator can exercise the
#: same SHAPE the real one uses; the VALUES are ours and will be wrong.
#:
#: They are decoded only by `classify_error_code`, so replacing them with the
#: vendor's table is a change in one place. Nothing here should be read as a
#: claim about what the real ACS returns.
ERR_BUSY = 1            # no robot free on this leg yet — retry
ERR_UNKNOWN_STATION = 2
ERR_NO_TASKS = 3

_RESULT_TO_CODE = {
    TransportResult.ACCEPTED: 0,
    TransportResult.BUSY: ERR_BUSY,
    TransportResult.REJECTED: ERR_UNKNOWN_STATION,
}

#: The other direction, for `classify_error_code`. We know THIS server's codes
#: because we wrote them; that is exactly what the real one is missing. Without
#: this an unknown station would come back as BUSY and be retried for ever
#: instead of failed.
SIM_ERROR_CODES = {
    0: TransportResult.ACCEPTED,
    ERR_BUSY: TransportResult.BUSY,
    ERR_UNKNOWN_STATION: TransportResult.REJECTED,
    ERR_NO_TASKS: TransportResult.REJECTED,
}


class _Assignment:
    """What the robot layer needs in order to carry one order.

    An order is a task list; a robot is driven by two journeys, collect then
    deliver. This is the small translation between them, and it exists so the
    robot code keeps reading `job.from_station` unchanged while the interface
    above it has become orders and tasks.
    """

    __slots__ = ("job_id", "from_station", "to_station", "priority")

    def __init__(self, job_id, from_station, to_station, priority=0):
        self.job_id = job_id
        self.from_station = from_station
        self.to_station = to_station
        self.priority = priority


def _yield_rank(robot):
    """Lower gives way. The robot's number, or last if it has none.

    Numeric, not textual: text order reads "amr10" as lower than "amr2".
    """
    number = plant.robot_number(robot.name or "")
    return (number is None, number if number is not None else 0, robot.name or "")


def _name_of(robot):
    return robot.name if robot is not None else None


class SimAcs(AcsAdapter):
    """The fleet controller — one or more robots, and the choice between them.

    This is the boundary the project was reorganised around. The CSM decides
    WHICH JOB goes next; the ACS decides WHICH ROBOT takes it. Until now this
    class was a single robot wearing an AcsAdapter interface, so the second
    decision did not exist — there was only ever one candidate.

    What it owns that a robot cannot:

      * the choice of robot, which no robot can make for itself
      * the job -> result table, because a caller asking "is job_7 done?" must
        get an answer whichever robot carried it, and after that robot has
        moved on to something else
      * BUSY, which means "valid job, no robot free" — not "bad job". With one
        robot every job raised during a transit used to be destroyed by the
        code that conflated the two.
    """

    def __init__(self, node, robot_names=None, equipment=None,
                 **robot_kwargs):
        """
        :param equipment: the machines, so a robot can ask one whether it may
            come in. Optional: without it the docking watchdog is simply not
            consulted, which is the behaviour every caller had before. It is
            NOT defaulted to a permissive stand-in — a missing equipment layer
            and a machine that has granted permission are different things.
        """
        self.equipment = equipment
        """
        :param robot_names: namespaces, e.g. ["amr1", "amr2"]. The default is a
            single unnamed robot on the global topics, which is what a
            one-robot Gazebo world publishes.
        """
        self.node = node
        names = robot_names if robot_names is not None else [""]
        self.robots = [SimRobot(node, name=n, **robot_kwargs) for n in names]
        for r in self.robots:
            r.on_finished = self._on_robot_finished
            r.fleet = self
        self._results = {}
        #: station_id -> robot holding it. One robot per bay.
        self._occupied = {}
        #: robot name -> the charging slot it holds. Five plugs, ten robots,
        #: so this is a reservation and not a lookup.
        self._chargers = {}
        #: pair of robot names -> the one that must give way.
        #: junction node -> the robot holding it (the red light).
        self._last_log = 0.0
        self.stations = self.robots[0].stations
        node.get_logger().info(
            f"ACS: fleet of {len(self.robots)} "
            f"({', '.join(n or 'default' for n in names)})")

    # -------------------------------------------------------- AcsAdapter

    # ------------------------------------------------------- the order API
    #
    # ADR 2026-08-18-acs-order-task-interface. `create_order` is what the real
    # ACS exposes, so it is what the simulator must expose too — otherwise what
    # is verified here has a different shape from what runs at deployment,
    # which is the one thing specification section 9 asks us not to do.
    #
    # `submit_job` is kept and now goes THROUGH the order path, so the four
    # existing call sites are already exercising orders and task lists without
    # having been touched.

    def create_order(self, order):
        """Take an order — an id and an ORDERED LIST OF TASKS.

        The task list is authoritative. Where the robot has to go is read from
        it rather than passed alongside it:

            LOAD   target -> where material is collected
            UNLOAD target -> where it is delivered

        which for a plain delivery (MOVE, LOAD, MOVE, UNLOAD) gives the two
        ends, and for a deliver-and-collect at one port (MOVE, UNLOAD, STAGE,
        LOAD) gives the same station twice — one visit, which is the case that
        made an order a list in the first place.

        Returns a `SimpleResponse`, as every real ACS mutation does. The
        integer is the only channel the real server has, and
        `classify_error_code` is the only place allowed to interpret one.
        """
        if not order.tasks:
            return SimpleResponse(ERR_NO_TASKS, "order carries no tasks")

        # A CHARGE ORDER IS NOT A TRANSPORT. It moves a named robot to its own
        # charger and tops it up; there is no material, no source and no
        # destination, so the LOAD/UNLOAD reading below does not apply to it.
        charge = next((t for t in order.tasks if t.kind is TaskKind.CHARGE),
                      None)
        if charge is not None:
            return self._charge_order(order, charge)

        frm = next((t.target for t in order.tasks
                    if t.kind is TaskKind.LOAD), None)
        to = next((t.target for t in reversed(order.tasks)
                   if t.kind is TaskKind.UNLOAD), None)
        if frm is None or to is None:
            return SimpleResponse(
                ERR_NO_TASKS,
                "an order must carry at least one LOAD and one UNLOAD")

        result = self._dispatch(order.id, frm, to, order.priority or 0)
        return SimpleResponse(_RESULT_TO_CODE.get(result, ERR_BUSY),
                              result.value)

    def _charge_order(self, order, charge):
        """Send a robot to its charger. The CSM decided; this obeys.

        The robot is named in the MOVE task's target as `charger:<robot>`,
        because a charger is that robot's own slot and no other robot may use
        it — so naming the place would be naming the robot anyway.
        """
        move = next((t for t in order.tasks if t.kind is TaskKind.MOVE), None)
        target = (move.target or "") if move else ""
        name = target.split(":", 1)[1] if target.startswith("charger:") else None
        robot = next((r for r in self.robots if r.name == name), None)
        if robot is None:
            return SimpleResponse(ERR_UNKNOWN_STATION,
                                  f"no robot named {name!r}")
        if robot.busy and order.priority and order.priority >= 100:
            # CRITICAL: TAKE THE JOB OFF IT AND GO NOW.
            #
            # "Finish the job first" deadlocks whenever the remaining charge
            # cannot outlast the job — and the simulator produced exactly that:
            # a robot told to charge after its current job, which then went
            # flat mid-job, so the job never ended and the charge never
            # started. All three robots died holding jobs they could not
            # finish.
            #
            # The job is FAILED rather than quietly dropped, so the CSM sees a
            # terminal state and can raise it again for whoever is free. A job
            # nobody is doing must never look like a job in progress.
            abandoned = robot._active_job
            if abandoned is not None:
                robot._finish(abandoned, TransportResult.FAILED)
                self._results[abandoned] = TransportResult.FAILED
                self.node.get_logger().warn(
                    f"{robot.name}: recalled to charge — {abandoned} given up")
            robot.start_charging(to_level=float(charge.chargeTo or 90))
            robot._go_home()
            self._results[order.id] = TransportResult.IN_PROGRESS
            return SimpleResponse(0, "recalled to charge")

        if robot.busy:
            # ACCEPTED AND DEFERRED, not refused.
            #
            # Refusing was wrong and the simulator proved it: the CSM sends a
            # critically low robot even while it is working, this refused every
            # such order BECAUSE it was working, and the two halves argued 43
            # times in one run while the battery went to zero. A robot cannot
            # abandon a roll in an aisle, but the request is still valid — so
            # it is remembered and honoured the moment the job ends.
            robot._charge_pending = float(charge.chargeTo or 90)
            self._results[order.id] = TransportResult.ACCEPTED
            self.node.get_logger().info(
                f"{robot.name}: will charge to {charge.chargeTo}% "
                f"after this job")
            return SimpleResponse(0, "queued until the current job ends")

        # EVERY PLUG ON THIS LEG MAY BE TAKEN. Five serve ten, so this is a
        # real and ordinary state, not a fault — BUSY, so the CSM asks again
        # rather than treating the robot as unchargeable.
        spot = self.claim_charger(robot)
        if spot is None:
            held = ", ".join(sorted(
                f"{n}" for n, s in self._chargers.items()
                if s in plant.chargers_for(robot.name)))
            self.node.get_logger().info(
                f"{robot.name}: every charger on its leg is taken "
                f"({held}) — waiting")
            return SimpleResponse(ERR_BUSY, "no free charger on this leg")

        robot.start_charging(to_level=float(charge.chargeTo or 90))
        # Home is the plug it now holds — which for most of the fleet is not
        # its own parking slot. See `_home_target`.
        robot._go_home()
        self._results[order.id] = TransportResult.IN_PROGRESS
        self.node.get_logger().info(
            f"{robot.name}: charging to {charge.chargeTo}% "
            f"at ({spot[0]:.1f}, {spot[1]:.1f})")
        return SimpleResponse(0, "charging")

    def order_state(self, order_id):
        return self._results.get(order_id, TransportResult.UNKNOWN)

    def cancel_order(self, order_id):
        return SimpleResponse(0 if self.cancel_job(order_id) else ERR_BUSY)

    def abort_order(self, order_id):
        """Stop a running order. Takes NO drop-off location — the ACS decides."""
        return self.cancel_order(order_id)

    def submit_job(self, job):
        """The older shape, now a thin wrapper over the order path.

        Kept so the four call sites migrate one at a time rather than all at
        once — but they are already going through `create_order` from here, so
        the order path is what the simulator actually runs.
        """
        response = self.create_order(build_order(job))
        return classify_error_code(response.errorCode, SIM_ERROR_CODES)

    def _dispatch(self, job_id, from_station, to_station, priority=0):
        job = _Assignment(job_id, from_station, to_station, priority)
        if job.from_station not in self.stations:
            self.node.get_logger().warn(f"unknown source {job.from_station}")
            return TransportResult.REJECTED
        if job.to_station not in self.stations:
            self.node.get_logger().warn(f"unknown destination {job.to_station}")
            return TransportResult.REJECTED

        # Do not send a robot where another robot is already going.
        #
        # The entry interlock only guards the threshold. Without this, three
        # jobs that all collect from the store send all three robots to the
        # same point: one is let in and the other two crowd the approach,
        # blocking the robot that was permitted. Everybody stalls, and the jobs
        # fail one after another.
        #
        # Claiming the endpoints at ASSIGNMENT means the wasted trip never
        # starts. The second job is told BUSY and waits its turn, which is the
        # same answer it would get for any other fleet constraint.
        # DESTINATIONS only. Two robots must not be sent to the same drop-off:
        # there is nothing to arbitrate between them there, and both would wait
        # for a bay only one can use.
        #
        # Sources are deliberately NOT claimed. Three machines fed by one store
        # means three jobs that all collect from it, and claiming the source
        # would serialise them completely — destroying the parallelism the extra
        # machines exist to provide, and leaving two robots permanently idle.
        # The shared pickup is arbitrated by the entry interlock instead: one
        # robot in the bay, the others hold outside and enter as it frees.
        taken = {r._to for r in self.robots if r.busy}
        if job.to_station in taken:
            return TransportResult.BUSY

        # SEGMENTED FLEET. A robot serves ONE leg of the material flow, which is
        # how the line is actually designed [system deck slide 16]:
        #
        #   1.5T-Big AGV A  ASRS        -> Gravure LD
        #   1.5T-Big AGV B  Gravure ULD -> Coater LD
        #   3.5T-Big AGV    Coater ULD  -> Slitter LD
        #
        # This was previously a free-for-all: nearest free robot took any job,
        # so all three roamed the whole floor and met head-on constantly. Most
        # of the traffic conflict that behaviour produced was an artefact of a
        # fleet model the customer never specified.
        segment = plant.segment_for_job(job.from_station, job.to_station)
        if segment is None:
            self.node.get_logger().warn(
                f"{job.from_station} -> {job.to_station} is not a leg of the "
                f"documented material flow")
            return TransportResult.REJECTED

        # A robot with no ground truth yet cannot be routed — the network is
        # entered from where the robot IS. It is a real state, not an error:
        # the node can be offered work in the moment between starting and its
        # first /gazebo/model_states message.
        # A robot that cannot MOVE is not a candidate, however free it looks.
        # `can_move` explains why pose is not enough on its own.
        for r in self.robots:
            if plant.ROBOT_SEGMENT.get(r.name) != segment["name"]:
                continue
            if r.pose is not None and not r.can_move:
                if not r._noted_immobile:
                    r._noted_immobile = True
                    self.node.get_logger().warn(
                        f"{r.name}: no joint_states — control chain is not "
                        f"running, so it will not be given work")
            elif r.can_move and r._noted_immobile:
                r._noted_immobile = False
                self.node.get_logger().info(f"{r.name}: control chain back")

        free = [r for r in self.robots
                if not r.busy
                and not r.charging
                and r.pose is not None
                and r.can_move
                and plant.ROBOT_SEGMENT.get(r.name) == segment["name"]]
        if not free:
            # BUSY, not REJECTED. The job is perfectly valid; the robot class
            # that serves this leg is simply working. It waits its turn.
            return TransportResult.BUSY

        # Nearest free robot to the pickup. This is the decision the ACS really
        # owns, and the only one it makes that the CSM could not.
        sx, sy = self.stations[job.from_station]
        # A robot that has not reported odometry yet sorts last rather than
        # crashing the sort. It is a real state — the node can be offered work
        # in the moment between starting and its first /odom_truth message.
        def distance_to_pickup(r):
            if r.pose is None:
                return float("inf")
            return math.hypot(r.pose[0] - sx, r.pose[1] - sy)

        free.sort(key=distance_to_pickup)
        robot = free[0]

        # RULE 3. DO NOT SET OFF FOR A STATION THAT IS NOT FREE.
        #
        # The interlock used to be asked on the FINAL LEG, 2.2 m from the dock —
        # by which time the robot is standing on the outer lane, because the
        # final leg begins AT the outer junction. A robot refused there blocks
        # the lane for everyone behind it. Measured 2026-08-27: amr1 sat on
        # `join_ASRS_outer` refused entry while amr6 held the ASRS bay.
        #
        # Asked here instead, the robot never leaves wherever it is standing —
        # its parking bay, or the station it has just finished at — and the
        # queue forms off the road instead of on it. The job stays BUSY and is
        # offered again, which is what BUSY already means.
        if not self.request_entry(job.from_station, robot.name or "robot"):
            return TransportResult.BUSY

        self._results[job.job_id] = TransportResult.IN_PROGRESS
        robot.accept(job)
        return TransportResult.ACCEPTED

    def fleet_status(self):
        """One row per robot, for the PDA. Read live, not remembered."""
        out = []
        for r in self.robots:
            out.append({
                "name": r.name,
                # The customer's own shape, `1A1` — class, leg, sequence.
                # Display only: the node name stays `amr1` so the screen and
                # the log lines still name the same robot.
                "agv": plant.agv_number(r.name),
                "leg": plant.ROBOT_SEGMENT.get(r.name),
                "busy": bool(r.busy),
                "job_id": r._active_job,
                "position": r.pose[:2] if r.pose else None,
                # Whether it is able to move at all, which is the thing an
                # operator most wants to know when a leg has gone quiet.
                "responsive": r.can_move,
                "halted_because": r._halt_reason,
                # RULE 2, VISIBLE. A robot pausing at the edge of the road
                # holds everything near it, so "why is nothing moving" is
                # answered by which robot is crossing and how far it has left
                # to go. Reconstructing that from positions alone cost two
                # sessions of guessing.
                "crossing": (round(r._crossing()[1], 2)
                             if r._crossing() is not None else None),
                "pausing": ("out" if r._pausing_out else
                            "in" if r._pausing_in else None),
                "battery": round(r.battery, 1),
                "charging_to": r._charging_to,
                # Who it is negotiating with, and which side it is on. Absent
                # from the view, a stuck handshake looks like a stuck robot.
            })
        return out

    def get_job_result(self, job_id):
        return self._results.get(job_id, TransportResult.UNKNOWN)

    def cancel_job(self, job_id):
        for r in self.robots:
            if r._active_job == job_id:
                r._finish(job_id, TransportResult.FAILED)
        self._results[job_id] = TransportResult.FAILED
        return True

    # ------------------------------------------------------------ driving

    def drive(self):
        """One control cycle for every robot."""
        for r in self.robots:
            r.drive()
        self._log_state()

    def _log_state(self, period=2.0):
        """Print what every robot is doing, at a readable rate.

        Diagnosing a stalled fleet from job outcomes alone is guesswork: a job
        that fails tells you a robot stopped, not where it was, what it was
        aiming at, or whether it was moving at all. One line per robot per two
        seconds is enough to see a robot creeping, circling, or held at a bay,
        and cheap enough to leave on.
        """
        now = self.node.get_clock().now().nanoseconds * 1e-9
        if now - self._last_log < period:
            return
        self._last_log = now

        parts = []
        for r in self.robots:
            if r.pose is None:
                parts.append(f"{r.name}: no pose")
                continue
            x, y, _ = r.pose
            moved = math.hypot(x - r._log_x, y - r._log_y)
            r._log_x, r._log_y = x, y
            if not r.busy:
                parts.append(f"{r.name}({x:+.1f},{y:+.1f}) idle")
                continue
            gx, gy = r._goal if r._goal else (x, y)
            speed = moved / period
            # A robot with a job that is not moving is the thing worth
            # explaining, so say WHY rather than only that it is at v=0.00.
            why = f" [{r._halt_reason}]" if speed < 0.02 and r._halt_reason else ""
            parts.append(
                f"{r.name}({x:+.1f},{y:+.1f})"
                f"->{r._to if r._leg == 'deliver' else r._from}"
                f" d={math.hypot(gx - x, gy - y):.1f}"
                f" v={speed:.2f}{why}"
                + (" HELD" if r._noted_hold else ""))
        self.node.get_logger().info("STATE " + " | ".join(parts))

    def _stop(self):
        for r in self.robots:
            r._stop()

    def _on_robot_finished(self, job_id, result):
        self._results[job_id] = result
        # A robot that has finished must not keep holding a bay.
        self.release_all(job_id)

    # ------------------------------------------------------- entry interlock

    def request_entry(self, station_id, robot_name):
        """May this robot approach that station? One at a time, ever.

        The protocol carries exactly one "AGV is inside" bit per docking axis,
        so a second robot has nowhere to report itself even if it wanted to. It
        is mutual exclusion built into the data, not a rule somebody has to
        remember — and the safe way to model it is to refuse rather than to
        queue silently.
        """
        holder = self._occupied.get(station_id)
        if holder in (None, robot_name):
            if holder is None:
                self.node.get_logger().info(
                    f"{station_id}: entry permitted -> {robot_name}")
            self._occupied[station_id] = robot_name
            return True
        return False

    def release(self, station_id, robot_name):
        if self._occupied.get(station_id) == robot_name:
            del self._occupied[station_id]
            self.node.get_logger().info(
                f"{station_id}: {robot_name} clear — bay free")

    # -- chargers: five plugs, ten robots ---------------------------------

    def claim_charger(self, robot):
        """Reserve a free charger on this robot's leg. Returns it, or None.

        THE DECK GIVES 5 CHARGERS TO 10 ROBOTS and `CHARGER_EVERY` says two
        share each one, so "this robot's charger" was only ever true while
        every leg had a single robot. With three on leg C, `charger_for` hands
        the same plug to two of them — and nothing would have complained: both
        would drive to the same slot, one would arrive, the other would sit
        beside it discharging while reporting that it was charging.

        A robot that already holds one keeps it, so asking twice is safe.
        Nearest first, so a robot walks past a free plug only when it is taken.
        """
        held = self._chargers.get(robot.name)
        if held is not None:
            return held
        taken = set(self._chargers.values())
        for spot in plant.chargers_for(robot.name):
            if spot not in taken:
                self._chargers[robot.name] = spot
                return spot
        return None

    def release_charger(self, robot):
        """Give the plug back. Silent — this runs on every job start."""
        self._chargers.pop(robot.name, None)

    def charger_held_by(self, spot):
        for name, held in self._chargers.items():
            if held == spot:
                return name
        return None

    def release_all(self, _job_id=None):
        """Free every bay held by a robot that no longer has a job."""
        # A robot backing out still holds its bay, even though its job is done.
        busy = {r.name for r in self.robots
                if r.busy or r._exit_goal is not None}
        # A robot that has finished charging is not holding its plug any more.
        for robot in self.robots:
            if robot._charging_to is None:
                self.release_charger(robot)
        for st in [k for k, v in self._occupied.items() if v not in busy]:
            self.node.get_logger().info(f"{st}: bay released")
            del self._occupied[st]
