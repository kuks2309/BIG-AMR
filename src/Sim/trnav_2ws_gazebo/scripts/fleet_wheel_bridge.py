#!/usr/bin/env python3
"""fleet_wheel_bridge — wheel_cmd_bridge for the fleet, with a docking input.

PORTED FROM scripts/wheel_cmd_bridge.py, which is not ours to edit. The
kinematics, the servo-lag model, the command timeout and the estop behaviour
below are that node's, unchanged in substance. Two things differ, and only two:

  1. A NAMESPACED DOCKING INPUT, `<ns>/dock/wheel_cmd`. The original listens on
     nine ABSOLUTE `/motion/wheel_cmd/...` topics, which is right for a single
     robot and wrong for a fleet: every robot's bridge would act on one shared
     topic. Docking is per robot, so its channel is relative.

  2. Nothing else. This is deliberately a copy rather than a subclass — the
     original is another author's file and should stay free to change.

WHY THIS EXISTS AT ALL — the bug it fixes:

    Docking is "steer to this angle, drive at this speed", and the settle phase
    of the approach is "steer to this angle, drive at ZERO" while the servos
    catch up. That is the whole point of settle-then-drive.

    The docking controller was publishing through /cmd_vel as a Twist:

        cmd.linear.x = speed * cos(steer)
        cmd.linear.y = speed * sin(steer)

    At speed == 0 that Twist is all zeros and THE STEERING ANGLE IS DESTROYED.
    So the settle phase commanded nothing at all for its full 14 s timeout, and
    the run phase then began with the wheels wherever they happened to be —
    precisely the churn settle-then-drive exists to prevent. Measured: robots
    drove 0.20 m past a 0.65 m target to 0.45 m, which is exactly where a 0.45 m
    half-width robot touches the machine face, and could not recover.

    A Twist is a BODY VELOCITY. It cannot express "point the wheels there and
    hold". A wheel command can, and the original bridge already honours it —
    `on_wheel_cmd` sets the steering target and leaves it set at zero speed.
    Nothing was wrong with that node; the loss was in converting to a Twist.
"""

import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, Float64MultiArray

try:
    from trnav_msgs.msg import WheelSetArray
    HAVE_WHEELSET = True
except ImportError:                                        # pragma: no cover
    WheelSetArray = None
    HAVE_WHEELSET = False


def normalize_steer(angle_rad, direction):
    """qd_inverse_kinematics.cpp::normalizeAngle, as in the original bridge.

    Folds |angle| > pi/2 by pi and flips the direction, so the solution is
    unique.
    """
    if angle_rad > math.pi / 2.0:
        angle_rad -= math.pi
        direction = -direction
    elif angle_rad < -math.pi / 2.0:
        angle_rad += math.pi
        direction = -direction
    return angle_rad, direction


class FleetWheelBridge(Node):

    def __init__(self):
        super().__init__('fleet_wheel_bridge')

        self.declare_parameter('w1_x', 0.6039)
        self.declare_parameter('w1_y', -0.0014)
        self.declare_parameter('w2_x', -0.5961)
        self.declare_parameter('w2_y', -0.0014)
        self.declare_parameter('wheel_radius', 0.125)
        self.declare_parameter('steer_limit_rad', math.pi / 2.0)
        self.declare_parameter('steer_tau', 0.0)
        self.declare_parameter('cmd_timeout', 0.5)
        self.declare_parameter('rate_hz', 100.0)

        g = self.get_parameter
        self.wheels = [(g('w1_x').value, g('w1_y').value),
                       (g('w2_x').value, g('w2_y').value)]
        self.wheel_radius = g('wheel_radius').value
        self.steer_limit = g('steer_limit_rad').value
        self.steer_tau = float(g('steer_tau').value)
        self.cmd_timeout = float(g('cmd_timeout').value)
        rate_hz = float(g('rate_hz').value)

        self.steer_target = [0.0, 0.0]
        self.steer_actual = [0.0, 0.0]
        self.drive_speed = [0.0, 0.0]
        self.estop = False
        self.last_cmd_t = None
        self.last_src = '(none)'

        self.pub_steer = self.create_publisher(
            Float64MultiArray, 'steer_position_controller/commands', 10)
        self.pub_drive = self.create_publisher(
            Float64MultiArray, 'drive_velocity_controller/commands', 10)

        self.create_subscription(Twist, 'cmd_vel', self.on_cmd_vel, 10)
        self.create_subscription(Bool, '/estop', self.on_estop, 10)

        # RELATIVE, so each robot has its own. Docking is per robot; a shared
        # global topic would have every robot's bridge acting on one command.
        if HAVE_WHEELSET:
            self.create_subscription(WheelSetArray, 'dock/wheel_cmd',
                                     self.on_wheel_cmd, 10)
            dock_state = 'dock/wheel_cmd'
        else:
            dock_state = 'dock DISABLED (trnav_msgs not built)'

        self.create_timer(1.0 / rate_hz, self.tick)
        lag = 'ideal servo' if self.steer_tau <= 0.0 else f'lag tau={self.steer_tau:.2f}s'
        self.get_logger().info(
            f'fleet_wheel_bridge up — W1={self.wheels[0]} W2={self.wheels[1]} '
            f'r={self.wheel_radius} | {lag} | /cmd_vel + {dock_state}')

    # ---------------------------------------------------------------- input

    def on_estop(self, msg):
        if msg.data != self.estop:
            self.get_logger().warn(f'estop -> {msg.data}')
        self.estop = msg.data

    def on_cmd_vel(self, msg):
        """Twist -> 2WS dual-steer IK -> per-wheel (steering, signed speed)."""
        vx, vy, wz = msg.linear.x, msg.linear.y, msg.angular.z
        for i, (wx, wy) in enumerate(self.wheels):
            v_ix = vx - wz * wy
            v_iy = vy + wz * wx
            speed = math.hypot(v_ix, v_iy)
            if speed < 1e-6:
                # Stopped: hold the steering, zero the drive — the real robot's
                # behaviour, and the original bridge's.
                self.drive_speed[i] = 0.0
                continue
            steer, direction = normalize_steer(math.atan2(v_iy, v_ix), 1)
            self.steer_target[i] = max(-self.steer_limit,
                                       min(self.steer_limit, steer))
            self.drive_speed[i] = direction * speed
        self.last_cmd_t = self.get_clock().now()
        self.last_src = 'cmd_vel'

    def on_wheel_cmd(self, msg):
        """WheelSetArray -> joint commands directly. No IK, nothing inferred.

        This is the path docking needs. A wheel command carries the steering
        angle explicitly, so "steer to this angle at zero speed" survives —
        which is exactly what a Twist cannot express.
        """
        if len(msg.wheels) < 2:
            self.get_logger().warn(
                f'dock/wheel_cmd: wheels[{len(msg.wheels)}] — need 2, ignoring')
            return
        for i in range(2):
            w = msg.wheels[i]
            # FOLD, DO NOT CLAMP. A 2WS wheel cannot steer past +/-90 deg, so a
            # demand beyond that means "drive the other way": normalize_steer
            # folds the angle by pi and reverses the direction. on_cmd_vel above
            # already does exactly this; this path did not, and the two inputs
            # disagreed about what a steering angle meant.
            #
            # Clamping turns a sideways or backwards demand into a FORWARD one —
            # a 90 deg error. Measured 2026-08-07: once the gap is closed a
            # docking command is almost pure lateral, and a lateral demand on
            # the negative side arrives as 180 deg. Clamped to +90 deg that is
            # precisely the direction that closes the gap, so the robot drove
            # into the machine face at 0.025 m/s and pressed there until the
            # 60 s docking timeout. amr1 finished 5 cm INSIDE GRV2's face;
            # amr2 was touching GRV1_ULD. Whether it happened at all depended
            # only on which side the lateral offset fell, which is why it
            # looked intermittent.
            steer, direction = normalize_steer(w.steering, 1)
            self.steer_target[i] = max(-self.steer_limit,
                                       min(self.steer_limit, steer))
            self.drive_speed[i] = direction * w.velocity
        self.last_cmd_t = self.get_clock().now()
        if self.last_src != 'dock':
            self.get_logger().info('command source -> dock/wheel_cmd')
        self.last_src = 'dock'

    # --------------------------------------------------------------- output

    def tick(self):
        dt = 1.0 / float(self.get_parameter('rate_hz').value)

        stale = True
        if self.last_cmd_t is not None:
            age = (self.get_clock().now() - self.last_cmd_t).nanoseconds * 1e-9
            stale = age > self.cmd_timeout
        drive = [0.0, 0.0] if (stale or self.estop) else list(self.drive_speed)

        if self.steer_tau > 1e-6:
            for i in range(2):
                self.steer_actual[i] += (
                    (self.steer_target[i] - self.steer_actual[i]) * dt / self.steer_tau)
        else:
            self.steer_actual = list(self.steer_target)

        steer_msg = Float64MultiArray()
        steer_msg.data = [float(a) for a in self.steer_actual]
        self.pub_steer.publish(steer_msg)

        drive_msg = Float64MultiArray()
        drive_msg.data = [float(v / self.wheel_radius) for v in drive]
        self.pub_drive.publish(drive_msg)


def main():
    rclpy.init()
    node = FleetWheelBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
