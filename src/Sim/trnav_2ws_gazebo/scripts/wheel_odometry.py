#!/usr/bin/env python3
"""
wheel_odometry — 실 로봇의 motor_control 이 하던 오도메트리를 시뮬에서 대신한다.

실 로봇: driver_node.py 가 0x6064(조향 실위치)·구동 피드백으로 /odom + odom→base_link TF 발행
시뮬   : /joint_states (joint_state_broadcaster) 의 조향각·구동 각속도로 동일하게 계산

2WS 정기구학 (IK 의 역):
    바퀴 i 의 속도벡터(body frame) = (v_i·cosδ_i, v_i·sinδ_i)
    한편  v_ix = vx − ω·y_i ,  v_iy = vy + ω·x_i
  → 바퀴 2개 × 성분 2개 = 4식, 미지수 3개(vx, vy, ω) 인 과결정계.
    최소자승으로 푼다(양 바퀴 정보 모두 사용 → 슬립에 덜 민감).

        [1  0  −y1] [vx]   [v1·cosδ1]
        [0  1   x1] [vy] = [v1·sinδ1]
        [1  0  −y2] [ω ]   [v2·cosδ2]
        [0  1   x2]        [v2·sinδ2]

주의: 이것은 **휠 오도메트리**다. 실 로봇과 마찬가지로 슬립·드리프트가 누적된다.
      Gazebo 의 참값(ground truth)이 필요하면 /gazebo/model_states 를 쓸 것.
"""

import math

import numpy as np
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster


def yaw_to_quat(yaw):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class WheelOdometry(Node):

    def __init__(self):
        super().__init__('wheel_odometry')

        self.declare_parameter('w1_x', 0.6039)
        self.declare_parameter('w1_y', -0.0014)
        self.declare_parameter('w2_x', -0.5961)
        self.declare_parameter('w2_y', -0.0014)
        self.declare_parameter('wheel_radius', 0.125)
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('publish_tf', True)

        g = self.get_parameter
        self.wheels = [
            (g('w1_x').value, g('w1_y').value),
            (g('w2_x').value, g('w2_y').value),
        ]
        self.wheel_radius = g('wheel_radius').value
        self.odom_frame = g('odom_frame').value
        self.base_frame = g('base_frame').value
        self.publish_tf = g('publish_tf').value

        # 최소자승 설계행렬 A 는 기하만으로 결정되므로 한 번만 만든다.
        rows = []
        for (wx, wy) in self.wheels:
            rows.append([1.0, 0.0, -wy])
            rows.append([0.0, 1.0, wx])
        self.A = np.array(rows)
        self.A_pinv = np.linalg.pinv(self.A)

        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.last_t = None

        self.pub = self.create_publisher(Odometry, '/odom', 10)
        self.tf_bc = TransformBroadcaster(self)
        self.create_subscription(JointState, '/joint_states', self.on_joints, 10)

        self.get_logger().info(
            f'wheel_odometry up — {self.odom_frame} -> {self.base_frame} '
            f'(tf={"on" if self.publish_tf else "off"})')

    def on_joints(self, msg):
        name_to_idx = {n: i for i, n in enumerate(msg.name)}
        need = ['w1_steer_joint', 'w2_steer_joint', 'w1_wheel_joint', 'w2_wheel_joint']
        if not all(n in name_to_idx for n in need):
            return
        if len(msg.velocity) < len(msg.name) or len(msg.position) < len(msg.name):
            return

        d1 = msg.position[name_to_idx['w1_steer_joint']]
        d2 = msg.position[name_to_idx['w2_steer_joint']]
        # 구동 조인트 각속도[rad/s] → 접지 선속도[m/s]
        v1 = msg.velocity[name_to_idx['w1_wheel_joint']] * self.wheel_radius
        v2 = msg.velocity[name_to_idx['w2_wheel_joint']] * self.wheel_radius

        b = np.array([
            v1 * math.cos(d1), v1 * math.sin(d1),
            v2 * math.cos(d2), v2 * math.sin(d2),
        ])
        vx, vy, omega = self.A_pinv @ b

        t = rclpy.time.Time.from_msg(msg.header.stamp)
        if self.last_t is None:
            self.last_t = t
            return
        dt = (t - self.last_t).nanoseconds * 1e-9
        self.last_t = t
        if dt <= 0.0 or dt > 1.0:
            return

        # body frame 속도를 world frame 으로 적분 (중점 yaw 사용)
        mid_yaw = self.yaw + omega * dt / 2.0
        self.x += (vx * math.cos(mid_yaw) - vy * math.sin(mid_yaw)) * dt
        self.y += (vx * math.sin(mid_yaw) + vy * math.cos(mid_yaw)) * dt
        self.yaw = math.atan2(math.sin(self.yaw + omega * dt),
                              math.cos(self.yaw + omega * dt))

        qx, qy, qz, qw = yaw_to_quat(self.yaw)

        odom = Odometry()
        odom.header.stamp = msg.header.stamp
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.x = qx
        odom.pose.pose.orientation.y = qy
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = float(vx)
        odom.twist.twist.linear.y = float(vy)
        odom.twist.twist.angular.z = float(omega)
        self.pub.publish(odom)

        if self.publish_tf:
            tf = TransformStamped()
            tf.header.stamp = msg.header.stamp
            tf.header.frame_id = self.odom_frame
            tf.child_frame_id = self.base_frame
            tf.transform.translation.x = self.x
            tf.transform.translation.y = self.y
            tf.transform.rotation.x = qx
            tf.transform.rotation.y = qy
            tf.transform.rotation.z = qz
            tf.transform.rotation.w = qw
            self.tf_bc.sendTransform(tf)


def main():
    rclpy.init()
    node = WheelOdometry()
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
