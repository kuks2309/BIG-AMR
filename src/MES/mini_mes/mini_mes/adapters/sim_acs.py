"""SimAcs - an ACS adapter that drives the real Gazebo robot.

Same interface as MockAcs, but instead of pretending a robot travelled it moves
the simulated Foil_A082 and reports ARRIVED when it gets there. That swap is the
whole argument for the adapter layer: the Mini MES, its main cycle and its job
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
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan

from .base import AcsAdapter, TransportResult

#: Where the machines physically stand in warehouse.world. These are SOLID —
#: the robot must never drive to these coordinates.
STATION_POSES = {
    # Customer naming: polarity + equipment type + number.
    #   1 = anode      A = gravure   T = coating   L = cold press
    "ASRS": (-3.5, 1.5),      # the automated store — supplies, never calls
    "1A01": (3.0, -3.0),      # gravure
    "1T01": (2.0, 3.5),       # coater
    "1L01": (-3.0, 3.5),      # cold press
}

#: How far in front of a machine the robot parks to load or unload.
#: station half-depth 0.5 + robot half-length 0.8 + clearance = 1.6 m.
APPROACH_DISTANCE = 1.6


def _approach_point(sx, sy):
    """Where the robot parks to serve the machine at (sx, sy).

    Navigating to the station's own coordinates means driving into it — the
    machine is a solid model sitting exactly there. On a real floor you dock at
    a defined position beside the machine, never at it.

    The approach point is offset toward the middle of the hall, which is the
    open side on this layout.
    """
    d = math.hypot(sx, sy) or 1.0
    return (sx - sx / d * APPROACH_DISTANCE,
            sy - sy / d * APPROACH_DISTANCE)


#: What the robot actually navigates to.
APPROACH_POSES = {name: _approach_point(x, y)
                  for name, (x, y) in STATION_POSES.items()}


class SimAcs(AcsAdapter):

    def __init__(self, node, arrive_tolerance=0.35, max_speed=0.6,
                 stations=None, influence_radius=1.9, repel_gain=1.4,
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
        self.tolerance = arrive_tolerance
        self.max_speed = max_speed
        self.stations = dict(stations or APPROACH_POSES)
        self.influence_radius = influence_radius
        self.repel_gain = repel_gain
        self.stall_seconds = stall_seconds
        self.stall_distance = stall_distance
        self.dwell_seconds = dwell_seconds
        self.dock_fade_m = dock_fade_m
        self.max_repulsion = max_repulsion
        self.critical_distance = critical_distance

        self.pub_cmd = node.create_publisher(Twist, "/cmd_vel", 10)
        node.create_subscription(Odometry, "/odom_truth", self._on_truth, 10)
        node.create_subscription(LaserScan, "/scan_front", self._on_front, 10)
        node.create_subscription(LaserScan, "/scan_rear", self._on_rear, 10)

        self.pose = None            # (x, y, yaw) ground truth
        self._front = None
        self._rear = None

        self._active_job = None
        self._goal = None
        self._results = {}

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

    def _on_truth(self, msg):
        q = msg.pose.pose.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                         1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        self.pose = (msg.pose.pose.position.x, msg.pose.pose.position.y, yaw)

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

    def submit_job(self, job):
        if job.to_station not in self.stations:
            self.node.get_logger().warn(f"unknown destination {job.to_station}")
            return TransportResult.REJECTED
        if self._active_job is not None:
            # BUSY, not REJECTED. The job is perfectly valid, there is simply no
            # free robot — it must wait its turn, not be thrown away. A real ACS
            # with a fleet would answer this from a different robot.
            return TransportResult.BUSY

        if job.from_station not in self.stations:
            self.node.get_logger().warn(f"unknown source {job.from_station}")
            return TransportResult.REJECTED

        # A transport job is TWO journeys, not one. Going straight to the
        # destination would report the load delivered without the robot ever
        # having visited the source to pick it up — the job would be fiction.
        self._active_job = job.job_id
        self._leg = "collect"
        self._from = job.from_station
        self._to = job.to_station
        self._goal = self.stations[job.from_station]
        self._dwell_until = None
        self._results[job.job_id] = TransportResult.IN_PROGRESS
        self._reset_stall()
        self.node.get_logger().info(
            f"{job.job_id}: leg 1/2 — collecting from {job.from_station} "
            f"{self._goal}")
        return TransportResult.ACCEPTED

    def get_job_result(self, job_id):
        return self._results.get(job_id, TransportResult.UNKNOWN)

    def cancel_job(self, job_id):
        if self._active_job == job_id:
            self._finish(job_id, TransportResult.FAILED)
        self._results[job_id] = TransportResult.FAILED
        return True

    # -------------------------------------------------------------- driving

    def drive(self):
        """Step the controller once, from the node's timer."""
        if self._active_job is None or self._goal is None:
            return
        if self.pose is None:
            return              # no ground truth yet — never command blind

        x, y, yaw = self.pose
        gx, gy = self._goal
        ex, ey = gx - x, gy - y
        distance = math.hypot(ex, ey)

        # Loading and unloading take real time on a real line. Standing still
        # during a dwell is not a stall, so this is checked before _check_stall.
        if self._dwell_until is not None:
            if self._now() < self._dwell_until:
                self._stop()
                return
            self._dwell_until = None
            self._begin_delivery()
            return

        if distance <= self.tolerance:
            self._on_arrival(distance)
            return

        if self._check_stall(x, y):
            return

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
        fade = min(1.0, distance / self.dock_fade_m)
        (rx, ry), closest = self._repulsion()
        self._closest_obstacle = closest
        vx = ax + fade * rx
        vy = ay + fade * ry

        # Ease down near the goal so the robot settles inside the tolerance band
        # instead of overshooting and hunting.
        speed = min(self.max_speed, 0.8 * distance)
        mag = math.hypot(vx, vy) or 1.0

        cmd = Twist()
        cmd.linear.x = vx / mag * speed
        cmd.linear.y = vy / mag * speed
        self.pub_cmd.publish(cmd)

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
        self._leg = "deliver"
        self._goal = self.stations[self._to]
        self._reset_stall()
        self.node.get_logger().info(
            f"{self._active_job}: leg 2/2 — carrying to {self._to} {self._goal}")

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
        self._results[job_id] = result
        self._active_job = None
        self._goal = None
        self._leg = None
        self._from = None
        self._to = None
        self._dwell_until = None
        self._stall_ref = None
        self._stall_since = None
        self._stop()

    def _stop(self):
        self.pub_cmd.publish(Twist())
