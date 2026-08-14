# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""라인 인식 웹 뷰어 노드.

카메라 JPEG 와 `/line/error` 를 구독해 HTTP 로 내보낸다. 카메라 장치는 열지 않고
`usb_cam_publisher` 의 토픽만 받는다(카메라 HAL 규약).

프레임 저장은 `cctv_webview.frame_store.FrameStore` 를 그대로 쓴다 — 같은 자료구조를
두 벌 두면 갈라진다.
"""

import threading

import rclpy
from ai_msgs.msg import LineError
from cctv_webview.frame_store import FrameStore
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import SetParameters
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import CompressedImage

from .line_state import LineState, centerline_points

# 전진·후진 카메라 논리명 (line_vision 로스터와 같은 이름).
DEFAULT_CAMERAS = ("cam_f", "cam_r")


def sensor_qos():
    """카메라 발행자(SensorDataQoS)와 호환되는 구독 프로파일."""
    return QoSProfile(reliability=QoSReliabilityPolicy.BEST_EFFORT,
                      history=QoSHistoryPolicy.KEEP_LAST, depth=1)


class LineWebview(Node):
    """카메라·라인오차 구독 + HTTP 서버."""

    def __init__(self):
        super().__init__("line_webview")
        self.declare_parameter("forward_camera", DEFAULT_CAMERAS[0])
        self.declare_parameter("reverse_camera", DEFAULT_CAMERAS[1])
        self.declare_parameter("direction", "forward")
        self.declare_parameter("seg_node", "/line_seg_node")
        self.declare_parameter("control_row_ratio", 0.8)
        # 영상 가로/세로 비. 오버레이 기울기를 정규화 좌표로 옮길 때 필요하다 —
        # 빠뜨리면 선이 종횡비만큼 가파르게 그려진다(line_state.centerline_points).
        self.declare_parameter("image_aspect", 1280.0 / 720.0)
        self.declare_parameter("port", 8081)
        self.declare_parameter("bind", "0.0.0.0")
        self.declare_parameter("stream_hz", 15.0)

        self._forward = str(self.get_parameter("forward_camera").value)
        self._reverse = str(self.get_parameter("reverse_camera").value)
        self._direction = str(self.get_parameter("direction").value)
        self._seg_node = str(self.get_parameter("seg_node").value)

        self._store = FrameStore()
        self._state = LineState()

        # 두 카메라를 모두 구독해 둔다 — 전환 시 화면이 즉시 붙는다.
        # 압축 프레임이라 대역은 카메라당 약 4 MB/s(720p MJPEG)로 감당 가능하다.
        self._subs = []
        for cam in (self._forward, self._reverse):
            topic = f"/{cam}/image_raw/compressed"
            self._subs.append(self.create_subscription(
                CompressedImage, topic,
                lambda msg, c=cam: self._on_frame(c, msg), sensor_qos()))

        self._subs.append(self.create_subscription(
            LineError, "/line/error", self._on_line, 10))

        self._param_client = self.create_client(
            SetParameters, f"{self._seg_node}/set_parameters")

        self._server = make_server_for(self)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.get_logger().info(
            f"line_webview: http://<robot>:{self.get_parameter('port').value}/ "
            f"(카메라 {self._forward}/{self._reverse}, 인식 노드 {self._seg_node})")

    def _on_frame(self, camera, msg):
        """JPEG 바이트를 그대로 보관한다 — 디코드하지 않는다."""
        self._store.put(camera, bytes(msg.data))

    def _on_line(self, msg):
        """최신 라인 오차를 보관한다. 미검출도 받는다(소실을 화면에서 봐야 한다)."""
        self._state.put(msg.detected, msg.offset, msg.angle, msg.confidence, msg.camera)

    def current_camera(self):
        """현재 방향에 대응하는 카메라 논리명."""
        return self._reverse if self._direction == "reverse" else self._forward

    def set_direction(self, want):
        """인식 노드의 `direction` 파라미터를 바꾼다.

        Returns:
            (성공 여부, 실패 사유 문자열 또는 None)
        """
        if not self._param_client.service_is_ready():
            return False, f"{self._seg_node} 파라미터 서비스 없음"
        req = SetParameters.Request()
        param = Parameter()
        param.name = "direction"
        param.value = ParameterValue(type=ParameterType.PARAMETER_STRING, string_value=want)
        req.parameters = [param]
        future = self._param_client.call_async(req)
        # 서버 스레드에서 호출되므로 실행기를 돌리지 않고 결과만 기다린다.
        if not future.done() and not _wait(future, 2.0):
            return False, "파라미터 설정 응답 없음(2s)"
        results = future.result().results if future.result() else []
        if results and not results[0].successful:
            return False, results[0].reason or "거부됨"
        self._direction = want
        self.get_logger().info(f"line_webview: 방향 전환 → {want} ({self.current_camera()})")
        return True, None

    def destroy_node(self):
        """HTTP 서버를 먼저 세운 뒤 노드를 정리한다."""
        try:
            self._server.shutdown()
            self._server.server_close()
        finally:
            super().destroy_node()


def _wait(future, timeout_sec):
    """future 완료를 폴링으로 기다린다(실행기는 주 스레드가 돌린다)."""
    import time
    end = time.monotonic() + timeout_sec
    while time.monotonic() < end:
        if future.done():
            return True
        time.sleep(0.02)
    return future.done()


def make_server_for(node):
    """노드 설정으로 HTTP 서버를 만든다."""
    from .server import make_server
    return make_server(
        store=node._store,
        state=node._state,
        geom_fn=centerline_points,
        camera_of=node.current_camera,
        set_direction=node.set_direction,
        port=int(node.get_parameter("port").value),
        bind=str(node.get_parameter("bind").value),
        stream_hz=float(node.get_parameter("stream_hz").value),
        control_row_ratio=float(node.get_parameter("control_row_ratio").value),
        image_aspect=float(node.get_parameter("image_aspect").value),
        log=node.get_logger(),
    )


def main(args=None):
    """노드 수명주기."""
    rclpy.init(args=args)
    node = LineWebview()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
