# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""ROS2 side of the CCTV viewer.

A single rclpy node subscribes to every camera topic and writes the latest
decoded BGR frame per topic into a ``LatestFrameStore``. The GUI thread drains
that store on a timer. This module never touches Qt widgets (Qt cross-thread
rule) and never queues frames — the store overwrites, so a slow GUI drops old
frames instead of growing memory without bound.
"""

import threading

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import CompressedImage, Image

try:
    import cv2
except ImportError:  # pragma: no cover - cv2 is a runtime dependency
    cv2 = None

# 검출 메시지는 **선택 의존**이다. ai_msgs 빌드 실패나 미설치가 CCTV 감시 기동 실패가 되면
# 안 되므로 import 를 감싸고, 없으면 AI 표시 기능만 비활성화한다.
try:
    from ai_msgs.msg import DetectionArray
except ImportError:  # pragma: no cover - optional dependency
    DetectionArray = None

NS_PER_SEC = 1_000_000_000


def stamp_to_ns(stamp):
    """`builtin_interfaces/Time` → 정수 나노초."""
    return stamp.sec * NS_PER_SEC + stamp.nanosec


def detection_topic_for(image_topic):
    """이미지 토픽 → 같은 카메라의 검출 토픽.

    `/cam0/image_raw` → `/cam0/detections`. 탐지기의 발행 규칙(`f"/{camera}/detections"`)과
    같은 네임스페이스 규약을 따른다. 마지막 경로 조각만 갈아끼운다.
    """
    head, _, _tail = image_topic.rstrip("/").rpartition("/")
    return f"{head}/detections" if head else "/detections"

# Sensor-data QoS: best-effort keep-last, matching typical camera publishers so
# the subscription actually connects (reliable<->best-effort is incompatible).
SENSOR_QOS = QoSProfile(
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    durability=QoSDurabilityPolicy.VOLATILE,
)


def decode_raw_bgr(msg):
    """Decode a raw sensor_msgs/Image into an HxWx3 BGR uint8 array.

    Supports the encodings the publisher emits (bgr8 / rgb8). Returns None for
    unsupported encodings so the caller can skip the frame rather than crash.
    """
    if msg.encoding not in ("bgr8", "rgb8"):
        return None
    # Guard the reshape: a truncated/padded/zero-sized frame would otherwise raise
    # ValueError inside the callback and take down the whole spin thread.
    expected = msg.height * msg.width * 3
    if msg.height <= 0 or msg.width <= 0 or len(msg.data) != expected:
        return None
    frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
    if msg.encoding == "rgb8":
        frame = frame[:, :, ::-1]  # rgb -> bgr for a uniform downstream format
    return np.ascontiguousarray(frame)


class RosImageWorker(Node):
    """rclpy node that writes the latest decoded frame per topic into a ``LatestFrameStore``.

    프레임마다 Qt 큐드 시그널을 쏘던 종전 경로는 **11.2 GB OOM 으로 뷰어를 죽였다**
    (2026-07-27, `docs/issues_and_fixes/issues_and_fixes.md`). 지금은 store 덮어쓰기다.
    """

    def __init__(self, frame_store, detection_store=None):
        """
        :param frame_store: object with ``put(topic:str, bgr_frame:np.ndarray, stamp_ns:int|None)``
            storing the latest frame per topic (see LatestFrameStore). ``stamp_ns`` 는
            프레임 취득 시각으로, 박스 나이 계산에 쓰인다.
        :param detection_store: ``LatestDetectionStore`` 또는 None. None 이면 AI 표시만
            비활성화되고 감시 기능은 그대로 동작한다.

        ROS parameters (read here, exposed for the GUI):
          * ``camera_topics`` (string[]): ordered base topics, e.g. "/cam0/image_raw".
          * ``image_transport`` (string): "raw" or "compressed".
          * ``layout`` (string): initial grid preset, e.g. "2x3" ("" = auto-fit).
          * ``ai_overlay`` (bool): 기동 시 AI 박스 표시 초기 상태(기본 false).
          * ``render_hz`` (double): 화면 갱신 상한(기본 10.0).
        """
        super().__init__("vision_guard")
        self._store = frame_store
        self._det_store = detection_store
        self._subs = []
        self._det_subs = []
        # 검출 토픽은 이미지 토픽과 **같은 키**로 저장한다 — GUI 가 매핑을 몰라도 되게.
        self._detection_topic_of = {}

        self.camera_topics = list(
            self.declare_parameter(
                "camera_topics",
                ["/cam0/image_raw", "/cam1/image_raw", "/cam2/image_raw"],
            ).value
        )
        transport = self.declare_parameter("image_transport", "raw").value
        self.layout = self.declare_parameter("layout", "").value
        # 기동 시 AI 표시 초기 상태. 기본 off — 켜져 있는 것이 기본이면 F11(박스 0개를
        # '사람 없음' 으로 오독) 위험이 기본값이 된다.
        self.ai_overlay = bool(self.declare_parameter("ai_overlay", False).value)
        # 화면 갱신 상한(Hz). 낮추면 GUI CPU 를 줄여 같은 보드의 다른 노드에 돌려준다.
        self.render_hz = float(self.declare_parameter("render_hz", 10.0).value)
        self.transport = transport

        for topic in self.camera_topics:
            if transport == "compressed":
                sub = self.create_subscription(
                    CompressedImage,
                    topic + "/compressed",
                    self._make_compressed_cb(topic),
                    SENSOR_QOS,
                )
            else:
                sub = self.create_subscription(
                    Image, topic, self._make_raw_cb(topic), SENSOR_QOS
                )
            self._subs.append(sub)
            self.get_logger().info(f"subscribed to '{topic}' ({transport})")

        self._subscribe_detections()

    def _subscribe_detections(self):
        """`/<camera>/detections` 구독. ai_msgs 나 저장소가 없으면 조용히 건너뛴다.

        토글과 무관하게 기동 시 항상 붙인다 — 페이로드가 프레임당 1 KB 미만이라 사실상 공짜이고,
        Qt 스레드에서 구독을 만들었다 없앴다 하는 것은 rclpy 에서 안전하지 않다(executor 가
        구독 목록을 제너레이터로 소비하므로 다른 스레드의 변경이 원소를 건너뛸 수 있다).
        """
        if self._det_store is None or DetectionArray is None:
            if self._det_store is not None:
                self.get_logger().warn("ai_msgs 를 찾지 못해 AI 표시를 비활성화한다")
            return
        for topic in self.camera_topics:
            det_topic = detection_topic_for(topic)
            self._detection_topic_of[det_topic] = topic
            sub = self.create_subscription(
                DetectionArray, det_topic, self._make_detection_cb(topic), 10)
            self._det_subs.append(sub)
            self.get_logger().info(f"subscribed to '{det_topic}'")

    def detection_publisher_count(self):
        """구독 중인 검출 토픽의 발행자 총수 — '탐지기 없음' 판정에 쓴다."""
        if not self._detection_topic_of:
            return 0
        return sum(self.count_publishers(t) for t in self._detection_topic_of)

    def _make_detection_cb(self, image_topic):
        def _cb(msg):
            try:
                self._det_store.put(image_topic, stamp_to_ns(msg.header.stamp),
                                    (msg.image_width, msg.image_height), msg.detections)
            except Exception as exc:  # noqa: BLE001 - keep the subscriber alive
                self.get_logger().error(
                    f"detection callback error on {image_topic}: {exc}",
                    throttle_duration_sec=5.0,
                )

        return _cb

    def _make_raw_cb(self, topic):
        def _cb(msg):
            # A raised exception here would escape into the executor and kill the
            # spin thread, silently freezing every camera. Contain it per-frame.
            try:
                frame = decode_raw_bgr(msg)
                if frame is not None:
                    self._store.put(topic, frame, stamp_to_ns(msg.header.stamp))
                else:
                    self.get_logger().warn(
                        f"dropping unsupported/malformed frame on {topic} "
                        f"(encoding='{msg.encoding}')",
                        throttle_duration_sec=5.0,
                    )
            except Exception as exc:  # noqa: BLE001 - keep the subscriber alive
                self.get_logger().error(
                    f"raw callback error on {topic}: {exc}",
                    throttle_duration_sec=5.0,
                )

        return _cb

    def _make_compressed_cb(self, topic):
        def _cb(msg):
            if cv2 is None:
                return
            try:
                buf = np.frombuffer(msg.data, dtype=np.uint8)
                frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)  # -> BGR
                if frame is not None:
                    self._store.put(topic, frame, stamp_to_ns(msg.header.stamp))
            except Exception as exc:  # noqa: BLE001 - keep the subscriber alive
                self.get_logger().error(
                    f"compressed callback error on {topic}: {exc}",
                    throttle_duration_sec=5.0,
                )

        return _cb


class RosSpinThread(threading.Thread):
    """Runs rclpy.spin on the worker node off the Qt GUI thread."""

    def __init__(self, node):
        super().__init__(daemon=True)
        self._node = node
        self._executor = rclpy.executors.SingleThreadedExecutor()
        self._executor.add_node(node)

    def run(self):
        try:
            self._executor.spin()
        except (rclpy.executors.ExternalShutdownException, KeyboardInterrupt):
            pass
        except Exception as exc:  # noqa: BLE001 - last-resort guard, never die silently
            self._node.get_logger().error(f"spin thread crashed: {exc}")

    def stop(self):
        self._executor.shutdown()
