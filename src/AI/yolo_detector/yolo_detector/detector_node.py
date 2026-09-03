"""yolo_detector — 카메라 토픽을 구독해 YOLOv8 객체탐지 결과를 발행하는 ROS2 노드.

카메라 장치를 직접 열지 않는다. `usb_cam_publisher` 가 발행하는 `/camN/image_raw` 를 구독만
하므로, 수집기(`dataset_collector`)나 내구 시험과 동시에 떠 있어도 서로 방해하지 않는다.

발행:
  /<camera>/detections        ai_msgs/DetectionArray   (결과만 — 화면 표시는 GUI 소관)

설계 결정:
  ① **배치 추론** — 한 틱에 그때까지 들어온 프레임을 **전부 한 번에** 넘긴다. 비용이
     계산이 아니라 **호출당 고정비**(커널 런치)에 묶여 있기 때문이다 — 배치 1 은 프레임당
     CPU 18.83 ms, 배치 6 은 5.68 ms(3.3배, 2026-08-06 실측). 그래서 타이머 주기가 곧
     **카메라당** 검출률이 되고, 대수로 나누는 계산이 사라진다(ADR 2026-08-06).
     ⚠ 2026-08-06 이전 이 자리에는 "GPU 는 한 번에 한 프레임이라 6대를 동시에 못 돌린다"
        는 **검증 없는 추정**이 적혀 있었고, 그 위에 세운 라운드로빈이 수신 프레임의
        약 83%를 버리고 있었다. 반증 근거는 위 실측이다.
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

from .detection import (DEFAULT_DETECT_HZ, build_boxes, missing_class_names,
                        per_camera_hz, resolve_class_filter)

DEFAULT_TOPICS = [f"/cam{i}/image_raw" for i in range(6)]
DEFAULT_MODEL = "/home/nvidia/models/yolov8n.pt"
# 사람만 본다 — 팔레트는 자체 학습 후 이름을 추가한다(COCO 에 없다).
DEFAULT_CLASSES = ["person"]
SUBSCRIPTION_DEPTH = 1
STATS_PERIOD_S = 30.0
MS_PER_S = 1000.0
NS_PER_MS = 1e6                  # ROS 시각은 ns — 리터럴을 흩뿌리지 않는다
# 구 파라미터. 설정되면 `detect_hz` 로 환산하고 경고한다(의미가 조용히 바뀌면 안 된다).
LEGACY_TOTAL_HZ_PARAM = "total_hz"
LEGACY_UNSET = -1.0              # "설정 안 됨" 을 나타내는 sentinel(주기는 항상 양수)


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
        # 장착이 180° 뒤집힌 카메라 이름(로스터 flip: true 파생 — launch 가 주입).
        # [""] 은 빈 목록 sentinel(rclpy 가 빈 리스트 타입을 추론하지 못한다).
        self.declare_parameter("flipped_cameras", [""])
        self.declare_parameter("model_path", DEFAULT_MODEL)
        self.declare_parameter("classes", DEFAULT_CLASSES)
        self.declare_parameter("confidence", 0.35)
        self.declare_parameter("iou", 0.45)
        self.declare_parameter("imgsz", 640)
        self.declare_parameter("device", "cuda")
        # 카메라 **한 대당** 검출률. 배치라 대수로 나누지 않는다(ADR 2026-08-06).
        self.declare_parameter("detect_hz", DEFAULT_DETECT_HZ)
        self.declare_parameter(LEGACY_TOTAL_HZ_PARAM, LEGACY_UNSET)

        self._topics = list(self.get_parameter("camera_topics").value)
        self._flipped = {n for n in self.get_parameter("flipped_cameras").value if n}
        model_path = str(self.get_parameter("model_path").value)
        wanted = list(self.get_parameter("classes").value)
        self._conf = float(self.get_parameter("confidence").value)
        self._iou = float(self.get_parameter("iou").value)
        self._imgsz = int(self.get_parameter("imgsz").value)
        self._device = str(self.get_parameter("device").value)
        detect_hz = self._resolve_detect_hz()

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
        # 토픽 → 최신 메시지. 한 틱이 통째로 비우므로 커서 같은 순서 상태가 없다.
        self._latest: dict[str, object] = {}
        self._counts: dict[str, int] = {}
        self._batch_sizes: list[int] = []      # log_stats 용 — 실제로 몇 장씩 묶였나
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

        period = 1.0 / detect_hz if detect_hz > 0 else 1.0
        self.create_timer(period, self._on_tick)
        self.create_timer(STATS_PERIOD_S, self.log_stats)

        self.get_logger().info(
            f"탐지 시작 — 모델 {model_path}, 카메라 {len(self._topics)}대, "
            f"카메라당 {detect_hz} Hz(목표 — 배치 추론이라 대수로 나뉘지 않는다. "
            f"실측은 log_stats 참조), "
            f"클래스 {wanted or '전체'} (인덱스 {self._class_filter or '전체'}), "
            f"conf {self._conf}, device {self._device}")

    def _resolve_detect_hz(self) -> float:
        """카메라당 검출률을 정한다 — 구 `total_hz` 가 오면 환산하고 경고한다.

        구 파라미터는 전 카메라 **합산** 률이었다. 그대로 받으면 카메라당 검출률이 조용히
        대수배로 뛴다(6대면 6배). 조용한 동작 변경을 막으려고 환산 + 경고로 처리한다.
        """
        detect_hz = float(self.get_parameter("detect_hz").value)
        legacy = float(self.get_parameter(LEGACY_TOTAL_HZ_PARAM).value)
        if legacy <= 0:                      # 설정 안 됨 — 정상 경로
            return detect_hz
        converted = per_camera_hz(legacy, len(self._topics))
        self.get_logger().warning(
            f"`{LEGACY_TOTAL_HZ_PARAM}`={legacy} 는 폐기된 파라미터다(전 카메라 합산률). "
            f"배치 추론에서는 카메라당 률을 쓰므로 {len(self._topics)}대로 나눠 "
            f"detect_hz={converted:.2f} 로 환산했다. 설정 파일을 `detect_hz` 로 고칠 것.")
        return converted

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
    def _on_image(self, topic: str, msg) -> None:
        """최신 프레임 보관만(추론 금지 — 콜백 starvation 방지).

        `msg` 는 `image_transport` 에 따라 `CompressedImage`(기본) 또는 `Image` 다.
        """
        self._latest[topic] = msg

    def _on_tick(self) -> None:
        """그때까지 들어온 프레임을 **전부 한 배치**로 추론한다.

        낱개로 나눠 부르면 커널 런치 고정비를 장마다 물어 프레임당 CPU 가 3.3배가 된다
        (18.83 vs 5.68 ms, 2026-08-06 실측). 한 틱이 `_latest` 를 통째로 비우므로
        라운드로빈 커서가 필요 없고, 타이머 주기가 곧 카메라당 검출률이 된다.
        """
        pending = [(t, self._latest.pop(t)) for t in self._topics if t in self._latest]
        if not pending:
            return
        self._infer_batch_and_publish(pending)

    def _decode(self, topic: str, msg):
        """메시지 → BGR 배열. 장착 보정(180° 회전)도 여기서 적용한다.

        실패하면 `None` 을 돌려 그 장만 배치에서 뺀다. 뒤집힌 카메라(`flipped_cameras`)는
        디코드 직후 회전하므로 이후 추론·검출 좌표는 전부 정립 프레임 기준이다.
        """
        try:
            if self._compressed:
                frame = cv2.imdecode(
                    np.frombuffer(msg.data, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    raise ValueError("JPEG 디코드 실패")
            else:
                frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            if camera_name_from_topic(topic) in self._flipped:
                frame = cv2.flip(frame, -1)  # 180° (상하+좌우) — line_vision 과 동일 관례
            return frame
        except Exception as exc:
            self.get_logger().warning(
                f"{camera_name_from_topic(topic)}: 변환 실패 — 건너뜀: {exc}")
            return None

    def _infer_batch_and_publish(self, pending) -> None:
        """`[(topic, msg), ...]` 를 한 번의 `predict` 로 처리하고 각각 발행한다."""
        items = []                       # (topic, msg, frame) — 디코드 성공분만
        for topic, msg in pending:
            frame = self._decode(topic, msg)
            if frame is not None:
                items.append((topic, msg, frame))
        if not items:
            return

        started = time.monotonic()
        try:
            results = self._model.predict(
                [f for _, _, f in items], imgsz=self._imgsz, conf=self._conf,
                iou=self._iou, device=self._device, verbose=False)
        except Exception as exc:
            self.get_logger().error(f"배치 추론 실패({len(items)}장): {exc}")
            return
        # 배치 1회의 비용을 장수로 나눠 **프레임당**으로 기록한다 — 배치 1 시절 수치와 비교 가능하게.
        per_frame_ms = (time.monotonic() - started) * MS_PER_S / len(items)

        if len(results) != len(items):
            # 결과 개수가 어긋나면 어느 결과가 어느 카메라인지 보장할 수 없다 — 발행하지 않는다.
            self.get_logger().error(
                f"배치 결과 개수 불일치: 입력 {len(items)}장 / 결과 {len(results)}건 — 이번 틱 폐기")
            return

        self._batch_sizes.append(len(items))
        for (topic, msg, frame), result in zip(items, results):
            self._publish_one(topic, msg, frame, result, per_frame_ms)

    def _publish_one(self, topic: str, msg, frame, result, infer_ms: float) -> None:
        camera = camera_name_from_topic(topic)
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
            / NS_PER_MS)
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
        """카메라별 추론 횟수·프레임당 평균 시간·실제 배치 크기.

        배치 크기를 함께 내는 이유: 설정상 6대라도 프레임이 늦게 오면 실제로는 2~3장씩
        묶일 수 있고, 그러면 프레임당 CPU 이득이 그만큼 줄어든다. 이 값이 카메라 수보다
        한참 작으면 타이머 주기나 발행률을 의심할 것.
        """
        mean_ms = self._infer_ms_sum / self._infer_n if self._infer_n else 0.0
        detail = " ".join(f"{c}:{self._counts[c]}" for c in sorted(self._counts))
        mean_batch = (sum(self._batch_sizes) / len(self._batch_sizes)
                      if self._batch_sizes else 0.0)
        self.get_logger().info(
            f"추론 누적 {self._infer_n}프레임({len(self._batch_sizes)}배치, "
            f"평균 {mean_batch:.1f}장/배치), 평균 {mean_ms:.1f} ms/frame | 카메라별 {detail}")


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
