"""SimAcs - an ACS adapter that drives the real Gazebo robot.

Same interface as MockAcs, but instead of pretending a robot travelled, it
actually moves the simulated Foil_A082 and reports ARRIVED when it gets there.

That swap is the whole argument for the adapter layer: the Mini MES, its main
cycle and its job FSM are unchanged. Only the class behind AcsAdapter differs.

Navigation is deliberately crude — straight-line crab, no path planning, no
obstacle avoidance. A real ACS does routing and traffic; this stands in for it
well enough to prove the job pipeline end to end. If the robot needs to get
around the pallets, that is the real ACS's job, not this file's.

Why crab rather than drive-and-turn: this platform carries a steerable wheel at
each end, both able to swivel +/-90 degrees, so it can translate in any
direction without changing heading. Commanding vx and vy directly is therefore
the simplest correct controller — no rotate-then-drive sequencing, and the
robot's heading stays fixed the whole way.
"""

import math

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

from .base import AcsAdapter, TransportResult

#: Where the stations sit in warehouse.world. Kept clear of the pallets at
#: (3.5, 2.5) and (-3.0, -3.0) and the pillar at (0.0, 4.0), since this
#: controller drives straight through anything in the way.
STATION_POSES = {
    "station_3": (3.0, -3.0),
    "station_5": (-3.5, 1.5),
    "station_9": (2.0, 3.5),
    "station_out": (-3.0, 3.5),
}


class SimAcs(AcsAdapter):

    def __init__(self, node, arrive_tolerance=0.25, max_speed=0.6,
                 stations=None):
        """
        :param node:             an rclpy Node used for the publisher/subscriber
        :param arrive_tolerance: metres from the goal that counts as arrived
        :param max_speed:        m/s cap on the commanded body velocity
        """
        self.node = node
        self.tolerance = arrive_tolerance
        self.max_speed = max_speed
        self.stations = dict(stations or STATION_POSES)

        self.pub_cmd = node.create_publisher(Twist, "/cmd_vel", 10)
        node.create_subscription(Odometry, "/odom", self._on_odom, 10)

        self.pose = None            # (x, y, yaw) or None until odom arrives
        self._active_job = None     # job_id currently being driven
        self._goal = None           # (x, y)
        self._results = {}          # job_id -> TransportResult

    # ------------------------------------------------------------ odometry

    def _on_odom(self, msg):
        q = msg.pose.pose.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                         1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        self.pose = (msg.pose.pose.position.x, msg.pose.pose.position.y, yaw)

    # ----------------------------------------------------------- AcsAdapter

    def submit_job(self, job):
        if job.to_station not in self.stations:
            self.node.get_logger().warn(
                f"unknown destination {job.to_station}")
            return TransportResult.REJECTED

        # One robot, so one job at a time. A real ACS would assign a free robot
        # from its fleet instead of refusing.
        if self._active_job is not None:
            return TransportResult.REJECTED

        self._active_job = job.job_id
        self._goal = self.stations[job.to_station]
        self._results[job.job_id] = TransportResult.IN_PROGRESS
        self.node.get_logger().info(
            f"{job.job_id}: driving to {job.to_station} {self._goal}")
        return TransportResult.ACCEPTED

    def get_job_result(self, job_id):
        return self._results.get(job_id, TransportResult.UNKNOWN)

    def cancel_job(self, job_id):
        if self._active_job == job_id:
            self._stop()
            self._active_job = None
            self._goal = None
        self._results[job_id] = TransportResult.FAILED
        return True

    # -------------------------------------------------------------- driving

    def drive(self):
        """Step the controller once. Called from the node's timer.

        Kept separate from the Mini MES tick: the job FSM runs at a few hertz
        because jobs last minutes, while the velocity command wants a steadier
        rate to keep motion smooth.
        """
        if self._active_job is None or self._goal is None:
            return
        if self.pose is None:
            return              # no odometry yet — do not command blind

        x, y, yaw = self.pose
        gx, gy = self._goal
        ex, ey = gx - x, gy - y
        distance = math.hypot(ex, ey)

        if distance <= self.tolerance:
            self._stop()
            self._results[self._active_job] = TransportResult.ARRIVED
            self.node.get_logger().info(
                f"{self._active_job}: arrived ({distance:.2f} m from goal)")
            self._active_job = None
            self._goal = None
            return

        # World-frame error rotated into the body frame. Because the platform
        # can crab, these become vx and vy directly — no heading change needed.
        vx = ex * math.cos(yaw) + ey * math.sin(yaw)
        vy = -ex * math.sin(yaw) + ey * math.cos(yaw)

        # Proportional approach, capped, and eased down near the goal so the
        # robot does not overshoot the tolerance band and oscillate.
        speed = min(self.max_speed, 0.8 * distance)
        norm = math.hypot(vx, vy) or 1.0

        cmd = Twist()
        cmd.linear.x = vx / norm * speed
        cmd.linear.y = vy / norm * speed
        self.pub_cmd.publish(cmd)

    def _stop(self):
        self.pub_cmd.publish(Twist())
