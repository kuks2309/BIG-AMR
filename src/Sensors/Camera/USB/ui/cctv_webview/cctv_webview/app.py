# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""cctv_webview — 압축 카메라 토픽을 브라우저로 그대로 흘리는 노드.

    /<cam>/image_raw/compressed  ──(바이트 그대로)──>  HTTP multipart MJPEG  ──> 브라우저

이 노드는 **JPEG 를 디코드하지 않는다.** 디코드는 보는 사람의 브라우저가 한다. 그래서
로봇 PC 의 표시 비용이 사실상 0 이 된다 — Qt 뷰어가 쓰던 렌더 CPU 와 X11 부담이 없다.

    ros2 launch cctv_webview cctv_webview.launch.py
    ros2 run cctv_webview cctv_webview --ros-args -p port:=8080 -p stream_hz:=10.0
"""

import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import (QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile,
                       QoSReliabilityPolicy)
from sensor_msgs.msg import CompressedImage

from .frame_store import DetectionStore, FrameStore, camera_label
from .server import make_server

try:
    from ai_msgs.msg import DetectionArray
except ImportError:  # pragma: no cover - 탐지기 미설치 환경에서도 영상은 봐야 한다
    DetectionArray = None

DEFAULT_TOPICS = [
    "/cam_rf/image_raw/compressed",
    "/cam_lf/image_raw/compressed",
    "/cam_rr/image_raw/compressed",
    "/cam_f/image_raw/compressed",
    "/cam_r/image_raw/compressed",
    "/cam_lr/image_raw/compressed",
]


def sensor_qos():
    """usb_cam_publisher 의 발행 프로파일과 호환(best-effort keep-last 1)."""
    return QoSProfile(
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=1,
        reliability=QoSReliabilityPolicy.BEST_EFFORT,
        durability=QoSDurabilityPolicy.VOLATILE,
    )


class CctvWebview(Node):
    def __init__(self):
        super().__init__("cctv_webview")
        self.declare_parameter("camera_topics", DEFAULT_TOPICS)
        # 장착이 180° 뒤집힌 카메라(로스터 flip: true). 서버는 픽셀을 만지지 않으므로
        # 대문 페이지가 CSS 로 돌린다. [""] 은 launch 의 빈 목록 sentinel — 걸러낸다.
        self.declare_parameter("flipped_cameras", [""])
        self.declare_parameter("port", 8080)
        self.declare_parameter("bind", "0.0.0.0")
        self.declare_parameter("stream_hz", 10.0)

        topics = list(self.get_parameter("camera_topics").value)
        flipped = [n for n in self.get_parameter("flipped_cameras").value if n]
        port = int(self.get_parameter("port").value)
        bind = str(self.get_parameter("bind").value)
        stream_hz = float(self.get_parameter("stream_hz").value)

        self._store = FrameStore()
        self._names = [camera_label(t) for t in topics]
        self._subs = [
            self.create_subscription(
                CompressedImage, topic,
                lambda msg, n=name: self._store.put(n, bytes(msg.data)),
                sensor_qos())
            for topic, name in zip(topics, self._names)
        ]
        for topic in topics:
            self.get_logger().info(f"구독 '{topic}'")

        # AI 검출은 **좌표만** 받아 브라우저에 넘긴다. 서버는 영상에 그리지 않는다.
        self._detections = DetectionStore()
        self._det_subs = []
        if DetectionArray is None:
            self.get_logger().warn("ai_msgs 없음 — AI 오버레이 없이 영상만 표시한다")
        else:
            for name in self._names:
                self._det_subs.append(self.create_subscription(
                    DetectionArray, f"/{name}/detections",
                    lambda msg, n=name: self._on_detections(n, msg), 10))

        self._server = make_server(
            self._store, self._names, port=port, bind=bind,
            stream_hz=stream_hz, log=self.get_logger(), detections=self._detections,
            flipped=flipped)
        if flipped:
            self.get_logger().info(f"180° 회전 표시: {', '.join(flipped)}")
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.get_logger().info(
            f"http://{bind}:{port}/ 에서 {len(self._names)}대 표시 "
            f"(스트림 {stream_hz:g} Hz, 서버 디코드 없음)")

        self._report_timer = self.create_timer(30.0, self._report)

    def _on_detections(self, name, msg):
        boxes = [
            {"x": d.x, "y": d.y, "w": d.width, "h": d.height,
             "label": d.class_name, "conf": round(float(d.confidence), 3)}
            for d in msg.detections
        ]
        self._detections.put(name, boxes, msg.image_width, msg.image_height)

    def _report(self):
        stats = self._store.stats()
        if not stats:
            self.get_logger().warn("아직 수신한 프레임이 없다 — 퍼블리셔가 compressed 모드인지 확인")
            return
        parts = [f"{n}={s['seq']}장/{s['bytes'] // 1024}KB/{s['age_s']:.1f}s전"
                 for n, s in sorted(stats.items())]
        self.get_logger().info("수신 " + " ".join(parts))
        stale = [n for n, s in stats.items() if s["age_s"] > 5.0]
        if stale:
            self.get_logger().warn(f"5초 이상 갱신 없음: {', '.join(sorted(stale))}")

    def destroy_node(self):
        self._server.shutdown()
        self._server.server_close()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CctvWebview()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
