"""yolo_detector — 카메라 토픽을 구독해 YOLOv8 객체탐지 결과를 발행하는 ROS2 노드.

카메라 장치를 직접 열지 않는다. `usb_cam_publisher` 가 발행하는 `/camN/image_raw` 를 구독만
하므로, 수집기(`dataset_collector`)나 내구 시험과 동시에 떠 있어도 서로 방해하지 않는다.

발행:
  /<camera>/detections        ai_msgs/DetectionArray   (결과만 — 화면 표시는 GUI 소관)

설계 결정:
  ① **라운드로빈 단일 추론** — GPU 는 한 번에 한 프레임이다(실측 18.8 ms). 6대를 각자
     타이머로 돌리면 서로 GPU 를 뺏어 지터가 커진다. 타이머 하나가 한 틱에 한 대씩 처리한다.
  ② **구독 콜백은 보관만** — 추론을 콜백에서 하면 22~24 ms(6대 실서비스 실측,
     2h18m 241,563회 평균 24.3 ms) 동안 다른 콜백이 굶는다
     (ros2-coding.md §2). 최신 프레임만 들고 있다가 타이머가 꺼내 쓴다.
  ③ **기본 executor(단일 스레드)** — 콜백과 타이머가 직렬 실행되므로 `_latest` 에 락이 필요
     없다. 다중 스레드 executor 로 바꾸면 락을 추가해야 한다.
  ④ **클래스는 이름으로 지정** — 사전학습 COCO 의 person 은 0 이지만 자체 학습 모델에서는
     번호가 달라진다. 인덱스를 굳히면 모델 교체 시 조용히 다른 클래스를 본다.

⚠ CPU 로 떨어지면 509 ms/frame 으로 27배 느려진다(실측). device 파라미터가 cuda 인데 실제로
   CPU 를 쓰게 되면 기동 시 경고한다.
"""
from __future__ import annotations

import time

import cv2
import numpy as np
import rclpy
from ai_msgs.msg import Detection, DetectionArray
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import (QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile,
                       QoSReliabilityPolicy)
from sensor_msgs.msg import CompressedImage, Image

from .detection import (DEFAULT_TOTAL_HZ, build_boxes, missing_class_names,
                        next_camera_index, per_camera_hz, resolve_class_filter)

DEFAULT_TOPICS = [f"/cam{i}/image_raw" for i in range(6)]
DEFAULT_MODEL = "/home/nvidia/models/yolov8n.pt"
# 사람만 본다 — 팔레트는 자체 학습 후 이름을 추가한다(COCO 에 없다).
DEFAULT_CLASSES = ["person"]
SUBSCRIPTION_DEPTH = 1
STATS_PERIOD_S = 30.0
MS_PER_S = 1000.0


def sensor_qos() -> QoSProfile:
    """`usb_cam_publisher` 발행 프로파일과 호환되는 센서 스트림 QoS.

    RELIABLE 로 구독하면 BEST_EFFORT 발행자와 호환되지 않아 메시지가 0이 된다.
    """
    return QoSProfile(reliability=QoSReliabilityPolicy.BEST_EFFORT,
                      durability=QoSDurabilityPolicy.VOLATILE,
                      history=QoSHistoryPolicy.KEEP_LAST,
                      depth=SUBSCRIPTION_DEPTH)


def camera_name_from_topic(topic: str) -> str:
    """`/cam3/image_raw` → `cam3`."""
    parts = [p for p in topic.split("/") if p]
    if len(parts) >= 2:
        return parts[-2]
    return parts[0] if parts else "camera"


class YoloDetectorNode(Node):
    """카메라 토픽 → YOLOv8 추론 → 검출 발행."""

    def __init__(self, **kwargs) -> None:
        # kwargs 전달은 통합 검증용 — 테스트가 parameter_overrides 로 실제 노드를 띄울 수 있다.
        super().__init__("yolo_detector", **kwargs)

        self.declare_parameter("camera_topics", DEFAULT_TOPICS)
        self.declare_parameter("model_path", DEFAULT_MODEL)
        self.declare_parameter("classes", DEFAULT_CLASSES)
        self.declare_parameter("confidence", 0.35)
        self.declare_parameter("iou", 0.45)
        self.declare_parameter("imgsz", 640)
        self.declare_parameter("device", "cuda")
        self.declare_parameter("total_hz", DEFAULT_TOTAL_HZ)

        self._topics = list(self.get_parameter("camera_topics").value)
        model_path = str(self.get_parameter("model_path").value)
        wanted = list(self.get_parameter("classes").value)
        self._conf = float(self.get_parameter("confidence").value)
        self._iou = float(self.get_parameter("iou").value)
        self._imgsz = int(self.get_parameter("imgsz").value)
        self._device = str(self.get_parameter("device").value)
        total_hz = float(self.get_parameter("total_hz").value)

        self._warn_if_no_gpu()

        from ultralytics import YOLO          # 무거운 임포트는 파라미터 검증 뒤로
        self._model = YOLO(model_path)
        self._names = dict(self._model.names)
        self._class_filter = resolve_class_filter(self._names, wanted)
        missing = missing_class_names(self._names, wanted)
        if missing:
            self.get_logger().error(
                f"모델에 없는 클래스: {missing} — 이 클래스는 절대 검출되지 않는다. "
                f"모델 보유 클래스 {len(self._names)}종. 자체 학습 모델로 교체가 필요한지 확인할 것.")
        if wanted and not self._class_filter:
            self.get_logger().error(
                "요청한 클래스가 모델에 하나도 없다 — 전 클래스를 발행하도록 되돌린다.")

        self._bridge = CvBridge()
        # 퍼블리셔 기본값이 compressed 다(config/camera/camera_common.yaml).
        # raw 로 되돌리려면 이 파라미터와 퍼블리셔의 publish_mode 를 함께 바꿔야 한다.
        self._compressed = str(
            self.declare_parameter("image_transport", "compressed").value) == "compressed"
        self._latest: dict[str, object] = {}
        self._cursor = -1
        self._counts: dict[str, int] = {}
        self._infer_ms_sum = 0.0
        self._infer_n = 0

        self._det_pubs = {}
        for topic in self._topics:
            camera = camera_name_from_topic(topic)
            self._counts[camera] = 0
            self._det_pubs[camera] = self.create_publisher(
                DetectionArray, f"/{camera}/detections", 10)
            if self._compressed:
                # 압축 바이트를 그대로 보관했다가 **추론하는 프레임만** 디코드한다.
                # 카메라당 30 Hz 를 다 푸는 대신 실제 추론률(약 5 Hz)만 디코드한다.
                self.create_subscription(
                    CompressedImage, topic + "/compressed",
                    lambda msg, t=topic: self._on_image(t, msg), sensor_qos())
            else:
                self.create_subscription(
                    Image, topic, lambda msg, t=topic: self._on_image(t, msg), sensor_qos())

        period = 1.0 / total_hz if total_hz > 0 else 1.0
        self.create_timer(period, self._on_tick)
        self.create_timer(STATS_PERIOD_S, self.log_stats)

        each_hz = per_camera_hz(total_hz, len(self._topics))
        self.get_logger().info(
            f"탐지 시작 — 모델 {model_path}, 카메라 {len(self._topics)}대, "
            f"전체 {total_hz} Hz(목표) → 카메라당 약 {each_hz:.1f} Hz(이론, 실측은 log_stats 참조), "
            f"클래스 {wanted or '전체'} (인덱스 {self._class_filter or '전체'}), "
            f"conf {self._conf}, device {self._device}")

    def _warn_if_no_gpu(self) -> None:
        """cuda 를 요청했는데 실제로 못 쓰면 크게 경고한다(27배 느려진다)."""
        if not self._device.startswith("cuda"):
            return
        try:
            import torch
            if not torch.cuda.is_available():
                self.get_logger().error(
                    "device=cuda 인데 torch.cuda.is_available()=False — CPU 로 떨어지면 "
                    "프레임당 약 509 ms(실측)로 27배 느려진다. 드라이버·torch 설치를 확인할 것.")
        except ImportError:
            self.get_logger().error("torch 를 임포트할 수 없다 — 추론 장치를 확인할 수 없다.")

    # ── 콜백 ────────────────────────────────────────────────────────────────
    def _on_image(self, topic: str, msg: Image) -> None:
        """최신 프레임 보관만(추론 금지 — 콜백 starvation 방지)."""
        self._latest[topic] = msg

    def _on_tick(self) -> None:
        """한 틱에 한 대만 추론한다(GPU 직렬 자원)."""
        if not self._topics:
            return
        # 프레임이 있는 다음 카메라를 찾는다. 한 바퀴 돌아도 없으면 이번 틱은 쉰다.
        for _ in range(len(self._topics)):
            self._cursor = next_camera_index(self._cursor, len(self._topics))
            topic = self._topics[self._cursor]
            msg = self._latest.pop(topic, None)
            if msg is not None:
                self._infer_and_publish(topic, msg)
                return

    def _infer_and_publish(self, topic: str, msg: Image) -> None:
        camera = camera_name_from_topic(topic)
        try:
            if self._compressed:
                frame = cv2.imdecode(
                    np.frombuffer(msg.data, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    raise ValueError("JPEG 디코드 실패")
            else:
                frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().warning(f"{camera}: 변환 실패 — 건너뜀: {exc}")
            return

        started = time.monotonic()
        try:
            result = self._model.predict(
                frame, imgsz=self._imgsz, conf=self._conf, iou=self._iou,
                device=self._device, verbose=False)[0]
        except Exception as exc:
            self.get_logger().error(f"{camera}: 추론 실패: {exc}")
            return
        infer_ms = (time.monotonic() - started) * MS_PER_S

        height, width = frame.shape[:2]
        boxes = build_boxes(self._rows(result), self._names, self._class_filter, width, height)

        out = DetectionArray()
        out.header = msg.header               # 취득 시각 승계 — 추론 완료 시각이 아니다
        out.camera = camera
        out.image_width = width
        out.image_height = height
        out.inference_ms = float(infer_ms)
        out.latency_ms = float(
            (self.get_clock().now() - rclpy.time.Time.from_msg(msg.header.stamp)).nanoseconds
            / 1e6)
        out.detections = [
            Detection(class_name=b.class_name, class_id=b.class_id, confidence=b.confidence,
                      x=b.x, y=b.y, width=b.width, height=b.height) for b in boxes]
        self._det_pubs[camera].publish(out)

        self._counts[camera] += 1
        self._infer_ms_sum += infer_ms
        self._infer_n += 1

        # 주석 영상은 발행하지 않는다 — **화면 표시는 GUI 소관**이다(2026-07-29 구조 정정).
        # 탐지기가 박스를 그려 2.8 MB 짜리 영상을 되돌려주면 (a) 추론 스레드가 프레임당 두 번
        # 복사를 지불하고 (b) 표시율이 검출률(약 4.8 Hz)에 묶여 원본 21 fps 를 잃는다.
        # GUI 는 이미 원본 프레임을 갖고 있으므로 좌표만 받아 그리면 된다.

    @staticmethod
    def _rows(result):
        """ultralytics 결과 → `(class_id, conf, x1, y1, x2, y2)` 행. 검출 0건이면 빈 목록."""
        if result.boxes is None or len(result.boxes) == 0:
            return []
        xyxy = result.boxes.xyxy.cpu().numpy()
        cls = result.boxes.cls.cpu().numpy()
        conf = result.boxes.conf.cpu().numpy()
        return [(int(cls[i]), float(conf[i]), *xyxy[i].tolist()) for i in range(len(cls))]

    def log_stats(self) -> None:
        """카메라별 추론 횟수와 평균 추론 시간."""
        mean_ms = self._infer_ms_sum / self._infer_n if self._infer_n else 0.0
        detail = " ".join(f"{c}:{self._counts[c]}" for c in sorted(self._counts))
        self.get_logger().info(
            f"추론 누적 {self._infer_n}회, 평균 {mean_ms:.1f} ms/frame | 카메라별 {detail}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = YoloDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.log_stats()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
