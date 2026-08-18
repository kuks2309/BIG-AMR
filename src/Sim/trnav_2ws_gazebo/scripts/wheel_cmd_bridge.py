#!/usr/bin/env python3
"""
wheel_cmd_bridge — 시뮬레이션에서 실 로봇의 "모터 계층"을 대신한다.

실 로봇:
    action server ─ WheelSetArray ─→ (mux) ─→ motor_control ─ CANopen SDO ─→ Tongyi 모터
시뮬:
    action server ─ WheelSetArray ─→ [이 노드] ─→ ros2_control 조인트 명령 ─→ Gazebo

두 개의 입력 경로를 모두 받는다(실 motor_control 과 동일한 역할 분담):

  1) /cmd_vel (geometry_msgs/Twist)
       실 motor_control 이 구독하는 경로. 여기서 2WS dual-steer IK 를 돌려
       바퀴별 (조향각, 속도) 로 변환한다. teleop 으로 바로 몰아볼 수 있다.

  2) /motion/wheel_cmd/<action> (trnav_msgs/WheelSetArray)
       trnav 액션서버 9종이 발행하는 경로. 이미 IK 가 끝난 바퀴 명령이므로
       그대로 조인트로 내린다. (in-repo mux 부재 → 이 노드가 그 자리를 메운다)

IK 는 trnav_2ws_kinematics/src/qd_inverse_kinematics.cpp 를 1:1 포팅했다:
    v_ix = vx - ω·y_i ,  v_iy = vy + ω·x_i
    steer = atan2(v_iy, v_ix) → [-π/2, +π/2] 정규화(초과 시 π 접고 방향 반전)
    speed = hypot(v_ix, v_iy)   (항상 ≥ 0, 부호는 direction 이 가진다)

조향 서보 지연(steer_tau): 실 로봇의 조향은 느리다. 1차 지연 모델을 넣어
"지령대로 즉시 꺾이지 않는" 실제 거동을 재현할 수 있다. 0 이면 이상적 서보.

안전: 마지막 명령이 cmd_timeout 보다 오래됐거나 /estop 이 true 면 구동 0 을 낸다
      (조향각은 유지 — 실 로봇의 정지 거동과 동일).
"""

import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, Float64MultiArray

# trnav_msgs 가 아직 빌드 전이어도 /cmd_vel 경로만으로 동작하도록 선택적 import.
try:
    from trnav_msgs.msg import WheelSetArray
    HAVE_WHEELSET = True
except ImportError:  # pragma: no cover
    WheelSetArray = None
    HAVE_WHEELSET = False

# 액션서버 9종이 발행하는 wheel_cmd 토픽 (qd_action_server_base publish_topic 파라미터)
WHEEL_CMD_TOPICS = [
    '/motion/wheel_cmd/spin',
    '/motion/wheel_cmd/turn',
    '/motion/wheel_cmd/translate_forward',
    '/motion/wheel_cmd/translate_reverse',
    '/motion/wheel_cmd/crab_linear',
    '/motion/wheel_cmd/yaw_control',
    '/motion/wheel_cmd/yaw_control_reverse',
    '/motion/wheel_cmd/mpc',
    '/motion/wheel_cmd/mpc_reverse',
]


def normalize_steer(angle_rad, direction):
    """qd_inverse_kinematics.cpp::normalizeAngle 1:1 포팅.

    |angle| > π/2 이면 π 만큼 접고 방향을 뒤집는다 → 해가 유일해진다.
    """
    if angle_rad > math.pi / 2.0:
        angle_rad -= math.pi
        direction = -direction
    elif angle_rad < -math.pi / 2.0:
        angle_rad += math.pi
        direction = -direction
    return angle_rad, direction



# TOPIC NAMES ARE RELATIVE, DELIBERATELY (2026-08-06).
#
# A leading slash makes a topic ABSOLUTE and the node's namespace is ignored.
# That is invisible with one robot, where the namespace is empty and the two
# forms resolve identically — and fatal with several, because every robot's
# bridge then listens on the same global /cmd_vel and publishes to controller
# topics that do not exist for it. The robot spawns, its controllers load, and
# it never moves.
#
# Relative names resolve under whatever namespace the node was launched in, so
# one script serves both worlds.

class WheelCmdBridge(Node):

    def __init__(self):
        super().__init__('wheel_cmd_bridge')

        # 휠 기하에는 **기본값을 두지 않는다.** 정본은 trnav_2ws_core/config/robot_geometry_2ws.yaml
        #   하나이며 런치가 주입한다. 여기에 '그럴듯한' 기본값을 두면 정본이 갱신돼도 이 노드만
        #   옛 값으로 조용히 돌아간다 — 그래서 미주입은 기동 실패로 처리한다.
        for key in ('w1_x', 'w1_y', 'w2_x', 'w2_y', 'wheel_radius'):
            self.declare_parameter(key, float('nan'))
        self.declare_parameter('steer_limit_rad', math.pi / 2.0)

        # ── 거동 모델 ──
        self.declare_parameter('steer_tau', 0.0)      # 조향 서보 1차 지연 시상수 [s]
        self.declare_parameter('cmd_timeout', 0.5)    # 명령 만료 [s]
        self.declare_parameter('rate_hz', 100.0)

        g = self.get_parameter
        geom = {k: float(g(k).value) for k in ('w1_x', 'w1_y', 'w2_x', 'w2_y', 'wheel_radius')}
        missing = [k for k, v in geom.items() if math.isnan(v)]
        if missing:
            raise RuntimeError(
                f'휠 기하 파라미터 미주입: {missing} — 런치가 robot_geometry_2ws.yaml 을 얹어야 한다')
        self.wheels = [
            (geom['w1_x'], geom['w1_y']),   # W1 Front
            (geom['w2_x'], geom['w2_y']),   # W2 Rear
        ]
        self.wheel_radius = geom['wheel_radius']
        self.steer_limit = g('steer_limit_rad').value
        self.steer_tau = float(g('steer_tau').value)
        self.cmd_timeout = float(g('cmd_timeout').value)
        rate_hz = float(g('rate_hz').value)

        # ── 상태 ──
        self.steer_target = [0.0, 0.0]   # 조향 목표각 [rad]
        self.steer_actual = [0.0, 0.0]   # 서보 지연 적용된 조향각 [rad]
        self.drive_speed = [0.0, 0.0]    # 부호 있는 바퀴 선속도 [m/s]
        self.estop = False
        self.last_cmd_t = None
        self.last_src = '(none)'

        # ── 출력: ros2_control 컨트롤러 ──
        self.pub_steer = self.create_publisher(
            Float64MultiArray, 'steer_position_controller/commands', 10)
        self.pub_drive = self.create_publisher(
            Float64MultiArray, 'drive_velocity_controller/commands', 10)

        # ── 입력 1: /cmd_vel (실 motor_control 과 동일 경로) ──
        self.create_subscription(Twist, 'cmd_vel', self.on_cmd_vel, 10)
        self.create_subscription(Bool, '/estop', self.on_estop, 10)

        # ── 입력 2: 액션서버 wheel_cmd ──
        if HAVE_WHEELSET:
            for topic in WHEEL_CMD_TOPICS:
                self.create_subscription(
                    WheelSetArray, topic,
                    lambda msg, t=topic: self.on_wheel_cmd(msg, t), 10)
            wheel_state = f'{len(WHEEL_CMD_TOPICS)} wheel_cmd topics'
        else:
            wheel_state = 'wheel_cmd DISABLED (trnav_msgs not built)'

        self.create_timer(1.0 / rate_hz, self.tick)

        lag = 'ideal servo' if self.steer_tau <= 0.0 else f'lag tau={self.steer_tau:.2f}s'
        self.get_logger().info(
            f'wheel_cmd_bridge up — W1={self.wheels[0]} W2={self.wheels[1]} '
            f'r={self.wheel_radius} | {lag} | /cmd_vel + {wheel_state}')

    # ------------------------------------------------------------------ 입력

    def on_estop(self, msg):
        if msg.data != self.estop:
            self.get_logger().warn(f'estop -> {msg.data}')
        self.estop = msg.data

    def on_cmd_vel(self, msg):
        """Twist → 2WS dual-steer IK → 바퀴별 (조향각, 부호 있는 속도)."""
        vx, vy, wz = msg.linear.x, msg.linear.y, msg.angular.z

        for i, (wx, wy) in enumerate(self.wheels):
            # v_i = V_body + ω × r_i
            v_ix = vx - wz * wy
            v_iy = vy + wz * wx

            speed = math.hypot(v_ix, v_iy)
            if speed < 1e-6:
                # 정지: 조향각은 그대로 두고 구동만 0 (실 로봇 거동과 동일)
                self.drive_speed[i] = 0.0
                continue

            angle = math.atan2(v_iy, v_ix)
            steer, direction = normalize_steer(angle, 1)

            self.steer_target[i] = max(-self.steer_limit,
                                       min(self.steer_limit, steer))
            self.drive_speed[i] = direction * speed

        self.last_cmd_t = self.get_clock().now()
        self.last_src = 'cmd_vel'

    def on_wheel_cmd(self, msg, topic):
        """WheelSetArray → 조인트 명령. IK 는 이미 액션서버가 끝냈다."""
        if len(msg.wheels) < 2:
            self.get_logger().warn(
                f'{topic}: wheels[{len(msg.wheels)}] — 2 개 필요, 무시')
            return

        for i in range(2):
            w = msg.wheels[i]
            self.steer_target[i] = max(-self.steer_limit,
                                       min(self.steer_limit, w.steering))
            self.drive_speed[i] = w.velocity

        self.last_cmd_t = self.get_clock().now()
        if self.last_src != topic:
            self.get_logger().info(f'command source -> {topic}')
        self.last_src = topic

    # ------------------------------------------------------------------ 출력

    def tick(self):
        dt = 1.0 / float(self.get_parameter('rate_hz').value)

        # 명령 만료 / estop → 구동 0 (조향은 유지)
        stale = True
        if self.last_cmd_t is not None:
            age = (self.get_clock().now() - self.last_cmd_t).nanoseconds * 1e-9
            stale = age > self.cmd_timeout

        drive = [0.0, 0.0] if (stale or self.estop) else list(self.drive_speed)

        # 조향 서보 지연 모델 (1차): steer_actual += (target - actual)·dt/tau
        if self.steer_tau > 1e-6:
            for i in range(2):
                self.steer_actual[i] += (
                    (self.steer_target[i] - self.steer_actual[i]) * dt / self.steer_tau)
        else:
            self.steer_actual = list(self.steer_target)

        steer_msg = Float64MultiArray()
        steer_msg.data = [float(a) for a in self.steer_actual]
        self.pub_steer.publish(steer_msg)

        # 선속도[m/s] → 바퀴 각속도[rad/s]
        drive_msg = Float64MultiArray()
        drive_msg.data = [float(v / self.wheel_radius) for v in drive]
        self.pub_drive.publish(drive_msg)


def main():
    rclpy.init()
    node = WheelCmdBridge()
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
