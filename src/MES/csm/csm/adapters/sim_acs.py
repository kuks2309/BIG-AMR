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
from gazebo_msgs.msg import ModelStates
from sensor_msgs.msg import JointState, LaserScan

from . import docking, roads
from .. import plant
from .base import AcsAdapter, TransportResult

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

#: THE ROAD NETWORK. Built once, at import. roads.build() raises rather than
#: returning a network with an obstructed lane, so a plant change that puts a
#: machine on a lane fails loudly at startup instead of driving a robot into it.
ROADS = roads.build()


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
        self._noted_yield = False
        #: Marker-guided controller for the last couple of metres, or None.
        self._dock = None
        self._docking = False
        #: Measured steering joint angles — settle-then-drive needs to know
        #: where the wheels ACTUALLY are, not where they were commanded.
        self._steer_actual = [0.0, 0.0]
        #: Set while reversing out of a bay after finishing.
        self._exit_goal = None
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
        self.pose = (pose.position.x, pose.position.y, yaw)

    def _on_joints(self, msg):
        for name, position in zip(msg.name, msg.position):
            if name == "w1_steer_joint":
                self._steer_actual[0] = position
            elif name == "w2_steer_joint":
                self._steer_actual[1] = position

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
        self._dock = docking.DockController(target=plant.DOCK_TARGET,
                                            d_min=plant.DOCK_MIN)
        self._dock.reset(now=self._now())
        self._docking = True
        self.node.get_logger().info(
            f"{self._tag()}{self._active_job}: at {station} approach point — "
            f"docking on marker")

    def _run_docking(self, station):
        """One docking cycle. Ends the leg on success, fails the job on fault."""
        marker = plant.MARKERS.get(station)
        obs = docking.observe(self.pose, marker) if marker else None
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

        # Crab: both wheels to one angle, one speed — pure translation.
        cmd = Twist()
        cmd.linear.x = speed * math.cos(steer)
        cmd.linear.y = speed * math.sin(steer)
        self.pub_cmd.publish(cmd)

    def _end_docking(self):
        self._dock = None
        self._docking = False
        self._stop()

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
        return list(ROADS.route_from(self.pose[:2], station)) or \
            [self.stations[station]]

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

    def _tag(self):
        return f"[{self.name}] " if self.name else ""

    # -------------------------------------------------------------- driving

    def drive(self):
        """Step the controller once, from the node's timer."""
        if self.pose is None:
            return              # no ground truth yet — never command blind

        # Reversing out of a bay after finishing. Nothing else may happen until
        # the robot is clear, including taking a new job — it still holds the
        # interlock, and the next robot is waiting on it.
        if self._exit_goal is not None:
            self._drive_to_exit()
            return

        if self._active_job is None or self._goal is None:
            return

        # DOCKING OWNS THE TICK once it has started. It is a distinct mode with
        # its own guards and its own timeout, and it must not be re-entered
        # through the waypoint logic: the robot sits inside the approach
        # tolerance for the whole manoeuvre, so an arrival check ahead of this
        # would return every cycle and the dock would never be driven at all.
        if self._docking:
            target = self._from if self._leg == "collect" else self._to
            return self._run_docking(target)

        x, y, yaw = self.pose
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
        target = self._from if self._leg == "collect" else self._to
        if self.fleet is not None and distance < self.entry_request_range:
            if not self.fleet.request_entry(target, self.name or "robot"):
                if not self._noted_hold:
                    self._noted_hold = True
                    self.node.get_logger().info(
                        f"{self._tag()}holding outside {target} — occupied")
                self._reset_stall()
                self._stop()
                return
            self._noted_hold = False

        # Loading and unloading take real time on a real line. Standing still
        # during a dwell is not a stall, so this is checked before _check_stall.
        if self._dwell_until is not None:
            if self._now() < self._dwell_until:
                self._stop()
                return
            self._dwell_until = None
            self._begin_delivery()
            return

        # WAYPOINT REACHED. Intermediate waypoints are corners on the road, not
        # destinations: step to the next one and carry on in the same pass. Only
        # the last waypoint is the dock, and only that counts as arriving.
        #
        # The tolerance is looser out on the lanes than at a machine. A corner
        # does not have to be hit precisely, and demanding dock accuracy at every
        # turn would have the robot creeping around the whole ring.
        if not self._final_leg and distance <= self.waypoint_tolerance:
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
            self._begin_docking(target)
            return self._run_docking(target)

        if self._check_stall(x, y):
            return

        # PROTECTIVE STOP. Deliberately AFTER _check_stall: a robot held here
        # keeps accumulating stall time, so two robots that stop facing each
        # other give up on their jobs after stall_seconds instead of waiting on
        # one another for ever. Failing a job is recoverable — the MES re-raises
        # it while the station still holds material — and, unlike a collision,
        # it leaves both robots free to take the next one rather than wedged
        # together where they stopped.
        blocker = self._robot_ahead(x, y, ex, ey)
        if blocker is not None:
            if not self._noted_yield:
                self._noted_yield = True
                self.node.get_logger().info(
                    f"{self._tag()}waiting — {blocker} is in the way")
            self._stop()
            return
        self._noted_yield = False

        # Attraction: goal direction in the body frame. The platform crabs, so
        # this becomes vx/vy directly with no heading change.
        ax = ex * math.cos(yaw) + ey * math.sin(yaw)
        ay = -ex * math.sin(yaw) + ey * math.cos(yaw)
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
        cmd.angular.z = max(-self.max_turn, min(self.max_turn,
                                                self.turn_gain * heading_err))

        # Slow down while badly misaligned — turning on the spot beats driving
        # confidently in the wrong direction, and it stops the robot arcing
        # wide around every goal.
        align = max(0.0, math.cos(heading_err))
        if abs(heading_err) > self.crab_window:
            speed *= align

        cmd.linear.x = vx * speed
        cmd.linear.y = vy * speed
        self.pub_cmd.publish(cmd)

    def _drive_to_exit(self):
        """Back out to the waiting spot, then release the bay."""
        x, y, _ = self.pose
        gx, gy = self._exit_goal
        distance = math.hypot(gx - x, gy - y)

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
        ex, ey = gx - x, gy - y
        n = math.hypot(ex, ey) or 1.0
        vx, vy = ex / n + rx, ey / n + ry
        m = math.hypot(vx, vy) or 1.0
        speed = min(self.max_speed, 0.8 * distance)

        cmd = Twist()
        cmd.linear.x = vx / m * speed
        cmd.linear.y = vy / m * speed
        self.pub_cmd.publish(cmd)

    def _robot_ahead(self, x, y, ex, ey):
        """Name of another robot inside the protective field, or None.

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
        n = math.hypot(ex, ey)
        if n < 1e-9:
            return None
        fx, fy = ex / n, ey / n
        for other in self.fleet.robots:
            if other is self or other.pose is None:
                continue
            dx, dy = other.pose[0] - x, other.pose[1] - y
            along = dx * fx + dy * fy
            if along <= 0.0 or along >= ROBOT_STOP_AHEAD:
                continue                      # behind us, or far enough off
            if abs(-dx * fy + dy * fx) < ROBOT_STOP_SIDE:
                return other.name or "robot"
        return None

    def _release_exit(self):
        """Let go of the bay and stop. The only way out of the exit leg."""
        if self.fleet is not None and self._exit_station:
            self.fleet.release(self._exit_station, self.name or "robot")
        self._exit_goal = None
        self._exit_station = None
        self._reset_stall()
        self._stop()

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
        self._stop()
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
        """Loading finished — set off on leg 2."""
        # Out of the source bay. Only now, not when the robot arrived: it was
        # physically in the bay for the whole loading dwell, and releasing on
        # arrival would invite the next robot in on top of it.
        if self.fleet is not None:
            self.fleet.release(self._from, self.name or "robot")
        self._leg = "deliver"
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

    def _finish(self, job_id, result):
        # Reported upward. The fleet owns the job -> result table, because a
        # caller asking "is job_7 done?" must get an answer whichever robot
        # happened to carry it — and after the robot has moved on to the next.
        if self.on_finished:
            self.on_finished(job_id, result)

        # BACK OUT before the bay is released. The robot is physically in it
        # until it has driven clear, and freeing the interlock while it still
        # stands there invites the next robot to drive into it. Only on arrival
        # outside does the bay go free — see _arrive_at_exit.
        station = self._to if self._leg == "deliver" else self._from
        if station in EXIT_POSES:
            self._exit_station = station
            self._exit_goal = EXIT_POSES[station]

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
        if self._exit_goal is None:
            self._stop()

    def _stop(self):
        self.pub_cmd.publish(Twist())



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

    def __init__(self, node, robot_names=None, **robot_kwargs):
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
        self._last_log = 0.0
        self.stations = self.robots[0].stations
        node.get_logger().info(
            f"ACS: fleet of {len(self.robots)} "
            f"({', '.join(n or 'default' for n in names)})")

    # -------------------------------------------------------- AcsAdapter

    def submit_job(self, job):
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
        free = [r for r in self.robots
                if not r.busy
                and r.pose is not None
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

        self._results[job.job_id] = TransportResult.IN_PROGRESS
        robot.accept(job)
        return TransportResult.ACCEPTED

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
            parts.append(
                f"{r.name}({x:+.1f},{y:+.1f})"
                f"->{r._to if r._leg == 'deliver' else r._from}"
                f" d={math.hypot(gx - x, gy - y):.1f}"
                f" v={moved / period:.2f}"
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

    def release_all(self, _job_id=None):
        """Free every bay held by a robot that no longer has a job."""
        # A robot backing out still holds its bay, even though its job is done.
        busy = {r.name for r in self.robots
                if r.busy or r._exit_goal is not None}
        for st in [k for k, v in self._occupied.items() if v not in busy]:
            self.node.get_logger().info(f"{st}: bay released")
            del self._occupied[st]
