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

#: Station positions in warehouse.world. Obstacles sit at pallet_a (3.5, 2.5),
#: pallet_b (-3.0, -3.0) and pillar (0.0, 4.0); the scanners handle the rest.
STATION_POSES = {
    "station_3": (3.0, -3.0),
    "station_5": (-3.5, 1.5),
    "station_9": (2.0, 3.5),
    "station_out": (-3.0, 3.5),
}


class SimAcs(AcsAdapter):

    def __init__(self, node, arrive_tolerance=0.35, max_speed=0.6,
                 stations=None, influence_radius=1.9, repel_gain=1.4,
                 stall_seconds=6.0, stall_distance=0.10):
        """
        :param arrive_tolerance: metres from the goal that counts as arrived
        :param max_speed:        m/s cap on commanded body velocity
        :param influence_radius: scan returns nearer than this push the robot away
        :param repel_gain:       strength of that push relative to the goal pull
        :param stall_seconds:    driving for this long without moving = stuck
        :param stall_distance:   ground-truth movement that counts as progress
        """
        self.node = node
        self.tolerance = arrive_tolerance
        self.max_speed = max_speed
        self.stations = dict(stations or STATION_POSES)
        self.influence_radius = influence_radius
        self.repel_gain = repel_gain
        self.stall_seconds = stall_seconds
        self.stall_distance = stall_distance

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

        self._stall_ref = None      # (x, y) last position that counted as progress
        self._stall_since = None    # when we last made progress

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
        """Sum a push-away vector from both scanners, in the body frame.

        Each return nearer than influence_radius contributes a vector pointing
        directly away from it, weighted by (1/r - 1/R) so the push grows sharply
        as an obstacle gets close and is exactly zero at the influence boundary.
        """
        rx = ry = 0.0
        # scan_rear is mounted yaw=pi, so its beam directions are negated.
        for scan, flip in ((self._front, 1.0), (self._rear, -1.0)):
            if scan is None:
                continue
            n = len(scan.ranges)
            if n == 0:
                continue
            # Every 4th beam is plenty for a repulsion field and keeps this cheap
            # enough to run at the drive rate.
            for i in range(0, n, 4):
                r = scan.ranges[i]
                if not math.isfinite(r) or r <= scan.range_min:
                    continue
                if r >= self.influence_radius:
                    continue
                angle = scan.angle_min + i * scan.angle_increment
                bx = flip * math.cos(angle)
                by = flip * math.sin(angle)
                strength = (1.0 / max(r, 0.15)) - (1.0 / self.influence_radius)
                rx -= bx * strength
                ry -= by * strength
        return rx, ry

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

        self._active_job = job.job_id
        self._goal = self.stations[job.to_station]
        self._results[job.job_id] = TransportResult.IN_PROGRESS
        self._stall_ref = None
        self._stall_since = None
        self.node.get_logger().info(
            f"{job.job_id}: driving to {job.to_station} {self._goal}")
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

        if distance <= self.tolerance:
            self.node.get_logger().info(
                f"{self._active_job}: arrived ({distance:.2f} m from goal)")
            self._finish(self._active_job, TransportResult.ARRIVED)
            return

        if self._check_stall(x, y):
            return

        # Attraction: goal direction in the body frame. The platform crabs, so
        # this becomes vx/vy directly with no heading change.
        ax = ex * math.cos(yaw) + ey * math.sin(yaw)
        ay = -ex * math.sin(yaw) + ey * math.cos(yaw)
        norm = math.hypot(ax, ay) or 1.0
        ax, ay = ax / norm, ay / norm

        rx, ry = self._repulsion()
        vx = ax + self.repel_gain * rx
        vy = ay + self.repel_gain * ry

        # Ease down near the goal so the robot settles inside the tolerance band
        # instead of overshooting and hunting.
        speed = min(self.max_speed, 0.8 * distance)
        mag = math.hypot(vx, vy) or 1.0

        cmd = Twist()
        cmd.linear.x = vx / mag * speed
        cmd.linear.y = vy / mag * speed
        self.pub_cmd.publish(cmd)

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
            self.node.get_logger().error(
                f"{self._active_job}: STUCK — moved {moved:.3f} m in "
                f"{self.stall_seconds:.0f}s while driving. Failing the job.")
            self._finish(self._active_job, TransportResult.FAILED)
            return True
        return False

    def _finish(self, job_id, result):
        self._results[job_id] = result
        self._active_job = None
        self._goal = None
        self._stall_ref = None
        self._stall_since = None
        self._stop()

    def _stop(self):
        self.pub_cmd.publish(Twist())
