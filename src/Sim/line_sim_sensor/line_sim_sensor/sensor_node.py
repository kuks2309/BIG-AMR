#!/usr/bin/env python3
"""SIL 가상 라인 센서 노드.

플랜트(`translate_sim_odom`)가 만든 map→base_link 자세를 읽어, 맵에 놓인 라인을 카메라가
어떻게 볼지 역산해 `/line/error` 를 발행한다. 실제 인식 노드와 **같은 메시지 타입**을 쓰므로
제어기는 이 값이 모사인지 실측인지 구분하지 못한다 — 그것이 SIL 의 목적이다.

인식 성능은 모사하지 않는다(검출 실패·오검출·신뢰도 변동 없음). 제어 수렴성을 보는 도구다.
"""

import math

import rclpy
import tf2_ros
from ai_msgs.msg import LineError
from rclpy.node import Node

from line_sim_sensor.line_geometry import LineSegment, anchor_line, measure

# 실카메라 실측 24.4 Hz 에 맞춘다. 제어는 50 Hz 라 측정율이 절반인 조건이 그대로 재현돼야
# 미분항 처리(새 측정에서만 갱신)가 시험된다.
DEFAULT_PUBLISH_HZ = 25.0
# 실측 conf 0.97 근사. 인식 변동은 모사하지 않으므로 상수다.
DEFAULT_CONFIDENCE = 0.95


class LineSimSensor(Node):
    """맵 라인 + 로봇 자세 → `/line/error`."""

    def __init__(self):
        super().__init__("line_sim_sensor")
        # 라인 기준계. "start" = 로봇 시작 자세 기준(기본), "map" = 맵 절대 좌표.
        # 플랜트 초기 자세는 시나리오 웨이포인트라 맵 원점이 아니다 — 맵 기준으로 놓으면
        # 라인이 화각 밖에 떨어져 시나리오가 성립하지 않는다.
        self.declare_parameter("line_frame", "start")
        self.declare_parameter("line_x0", 0.0)
        self.declare_parameter("line_y0", 0.0)
        self.declare_parameter("line_heading_deg", 0.0)
        self.declare_parameter("line_length", 10.0)
        # 곡률 [1/m]. 0 이면 직선, + 는 좌선회. 반경은 1/|curvature|.
        self.declare_parameter("line_curvature", 0.0)
        self.declare_parameter("lookahead_m", 1.0)
        self.declare_parameter("half_width_m", 0.6)
        self.declare_parameter("direction", "forward")
        self.declare_parameter("forward_camera", "cam_f")
        self.declare_parameter("reverse_camera", "cam_r")
        self.declare_parameter("publish_hz", DEFAULT_PUBLISH_HZ)
        self.declare_parameter("confidence", DEFAULT_CONFIDENCE)
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("base_frame", "base_link")

        self._frame = str(self.get_parameter("line_frame").value).strip().lower()
        self._x0 = float(self.get_parameter("line_x0").value)
        self._y0 = float(self.get_parameter("line_y0").value)
        self._heading_deg = float(self.get_parameter("line_heading_deg").value)
        self._length = float(self.get_parameter("line_length").value)
        self._curvature = float(self.get_parameter("line_curvature").value)
        # "map" 이면 즉시 확정, "start" 면 첫 자세를 받은 뒤 확정한다.
        self._line = None
        if self._frame == "map":
            self._line = LineSegment(
                x0=self._x0, y0=self._y0,
                heading=math.radians(self._heading_deg), length=self._length,
                curvature=self._curvature)
        self._lookahead = float(self.get_parameter("lookahead_m").value)
        self._half_width = float(self.get_parameter("half_width_m").value)
        self._map_frame = str(self.get_parameter("map_frame").value)
        self._base_frame = str(self.get_parameter("base_frame").value)
        self._confidence = float(self.get_parameter("confidence").value)

        self._buffer = tf2_ros.Buffer()
        self._listener = tf2_ros.TransformListener(self._buffer, self)
        # 실제 인식 노드와 같은 프로파일(RELIABLE depth 10)로 발행한다.
        self._pub = self.create_publisher(LineError, "/line/error", 10)

        hz = max(1.0, float(self.get_parameter("publish_hz").value))
        self._timer = self.create_timer(1.0 / hz, self._on_timer)
        self.get_logger().info(
            f"line_sim_sensor: 기준계 {self._frame} · 오프셋 전방 {self._x0:.2f}m "
            f"좌측 {self._y0:.2f}m · heading {self._heading_deg:.1f}° · 길이 {self._length:.1f}m · "
            f"lookahead {self._lookahead:.2f}m · 반폭 {self._half_width:.2f}m · {hz:.1f}Hz")

    def _lookup_pose(self):
        """map→base_link 자세. 조회 실패 시 None."""
        try:
            tf = self._buffer.lookup_transform(
                self._map_frame, self._base_frame, rclpy.time.Time())
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException,
                tf2_ros.ExtrapolationException):
            return None
        t = tf.transform.translation
        q = tf.transform.rotation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                         1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        return t.x, t.y, yaw

    def _anchor(self, pose):
        """`line_frame="start"` 이면 첫 자세로 라인을 확정한다. 확정된 라인을 돌려준다."""
        if self._line is None:
            self._line = anchor_line(pose[0], pose[1], pose[2],
                                     self._x0, self._y0, self._heading_deg, self._length,
                                     self._curvature)
            shape = ("직선" if abs(self._curvature) < 1e-9
                     else f"원호 R={1.0 / abs(self._curvature):.2f}m "
                          f"{'좌' if self._curvature > 0 else '우'}선회")
            self.get_logger().info(
                f"line_sim_sensor: 라인 확정 — 시작 자세 ({pose[0]:.3f}, {pose[1]:.3f}, "
                f"{math.degrees(pose[2]):.1f}°) 기준 → 맵 ({self._line.x0:.3f}, "
                f"{self._line.y0:.3f}) heading {math.degrees(self._line.heading):.1f}° · {shape}")
        return self._line

    def _on_timer(self):
        """자세를 읽어 관측을 만들고 발행한다. 자세가 없으면 미검출로 발행한다."""
        direction = str(self.get_parameter("direction").value).strip().lower()
        reverse = direction == "reverse"
        camera = str(self.get_parameter(
            "reverse_camera" if reverse else "forward_camera").value)

        msg = LineError()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = f"{camera}_optical_frame"
        msg.camera = camera

        pose = self._lookup_pose()
        if pose is None or self._anchor(pose) is None:
            # 자세 두절도 인식 두절처럼 보여야 한다 — 미검출로 발행하고 침묵하지 않는다.
            msg.detected = False
            self._pub.publish(msg)
            return

        m = measure(pose[0], pose[1], pose[2], self._line,
                    self._lookahead, self._half_width, reverse)
        msg.detected = m.detected
        msg.offset = float(m.offset) if m.detected else 0.0
        msg.angle = float(m.angle) if m.detected else 0.0
        msg.confidence = self._confidence if m.detected else 0.0
        self._pub.publish(msg)


def main(args=None):
    """노드 수명주기."""
    rclpy.init(args=args)
    node = LineSimSensor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
