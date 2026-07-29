"""dataset_collector — Orbbec 6대 영상 토픽에서 학습용 정지영상을 수집하는 ROS2 노드.

카메라 장치를 **직접 열지 않는다.** `usb_cam_publisher` 가 `/dev/video*` 를 점유한 채
`/camN/image_raw` 로 발행하고 있으므로(2026-07-27 24 h 내구 시험 중), 장치를 다시 열면 그
시험이 깨진다. 본 노드는 토픽 구독만 한다 — 기존 발행자에 무해하다.

설계 결정 두 가지:
  ① **구독 콜백은 메시지 보관만** 한다. cv_bridge 변환·JPEG 인코딩·파일 쓰기는 전부 타이머로
     옮겼다. 6대 × ~29 Hz 콜백 안에서 인코딩하면 실행기가 굶어(starvation) 프레임을 놓친다
     (실측 29.5~29.9 fps — `Log/usb_cctv_soak_2026-07-27/soak_samples.csv` 23:14~23:19,
     ros2-coding.md §2).
  ② 기본 executor(단일 스레드)를 쓴다 — 콜백과 타이머가 직렬 실행되므로 `_latest` 공유에
     락이 필요 없다. 다중 스레드 executor 로 바꾸면 락을 추가해야 한다.

QoS 는 발행자와 맞춘 **BEST_EFFORT** 다. RELIABLE 로 구독하면 호환되지 않아 메시지가 0이 된다
(ros2-coding.md §1).

실행:
  ros2 run dataset_collector collector
  ros2 launch dataset_collector collect.launch.py out_dir:=/path/to/out interval_s:=2.0
"""
from __future__ import annotations

import os
from datetime import datetime

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import Image

from .sampling import (MIN_FREE_GB_DEFAULT, MIN_MEAN_ABS_DIFF_DEFAULT,
                       camera_name_from_topic, disk_free_gb, frame_filename,
                       judge_frame)

DEFAULT_TOPICS = [f"/cam{i}/image_raw" for i in range(6)]
DEFAULT_INTERVAL_S = 1.0
DEFAULT_JPEG_QUALITY = 92
# 구독 큐 깊이 1 — 최신 프레임만 쓰므로 밀린 프레임을 쌓아둘 이유가 없다.
SUBSCRIPTION_DEPTH = 1
# 통계 로그 주기(초). 매 저장마다 찍으면 로그가 초당 6줄씩 불어난다.
STATS_PERIOD_S = 30.0


def sensor_qos() -> QoSProfile:
    """`usb_cam_publisher` 발행 프로파일과 호환되는 센서 스트림 QoS."""
    return QoSProfile(
        reliability=QoSReliabilityPolicy.BEST_EFFORT,
        durability=QoSDurabilityPolicy.VOLATILE,
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=SUBSCRIPTION_DEPTH,
    )


class DatasetCollectorNode(Node):
    """토픽을 구독해 주기적으로 프레임을 JPEG 로 저장한다."""

    def __init__(self) -> None:
        super().__init__("dataset_collector")

        default_out = os.path.join(
            os.path.expanduser("~"), "dataset_capture", datetime.now().strftime("%Y-%m-%d"))
        self.declare_parameter("camera_topics", DEFAULT_TOPICS)
        self.declare_parameter("out_dir", default_out)
        self.declare_parameter("interval_s", DEFAULT_INTERVAL_S)
        self.declare_parameter("min_free_gb", MIN_FREE_GB_DEFAULT)
        self.declare_parameter("min_mean_abs_diff", MIN_MEAN_ABS_DIFF_DEFAULT)
        self.declare_parameter("jpeg_quality", DEFAULT_JPEG_QUALITY)

        self._topics = list(self.get_parameter("camera_topics").value)
        self._out_dir = str(self.get_parameter("out_dir").value)
        interval_s = float(self.get_parameter("interval_s").value)
        self._min_free_gb = float(self.get_parameter("min_free_gb").value)
        self._min_diff = float(self.get_parameter("min_mean_abs_diff").value)
        self._jpeg_quality = int(self.get_parameter("jpeg_quality").value)

        self._bridge = CvBridge()
        self._latest: dict[str, Image] = {}
        self._prev_gray: dict[str, object] = {}
        self._saved: dict[str, int] = {}
        self._skipped: dict[str, int] = {}
        self._disk_low_announced = False

        os.makedirs(self._out_dir, exist_ok=True)
        for topic in self._topics:
            camera = camera_name_from_topic(topic)
            os.makedirs(os.path.join(self._out_dir, camera), exist_ok=True)
            self._saved[camera] = 0
            self._skipped[camera] = 0
            # 기본 인자로 topic 을 묶는다 — 늦은 바인딩이면 모든 콜백이 마지막 토픽을 가리킨다.
            self.create_subscription(
                Image, topic,
                lambda msg, t=topic: self._on_image(t, msg),
                sensor_qos())

        self.create_timer(interval_s, self._on_sample)
        self.create_timer(STATS_PERIOD_S, self.log_stats)
        self.get_logger().info(
            f"수집 시작 — 토픽 {len(self._topics)}개, 간격 {interval_s}s, 출력 {self._out_dir}, "
            f"여유 하한 {self._min_free_gb} GB, 신규 임계 {self._min_diff}")

    # ── 콜백 ────────────────────────────────────────────────────────────────
    def _on_image(self, topic: str, msg: Image) -> None:
        """최신 프레임 보관만 한다(변환·저장 금지 — 실행기 starvation 방지)."""
        self._latest[topic] = msg

    def _on_sample(self) -> None:
        """샘플 주기마다 카메라별로 한 장씩 판정·저장한다."""
        try:
            free_gb = disk_free_gb(self._out_dir)
        except OSError as exc:
            self.get_logger().error(f"디스크 조회 실패 — 이번 주기 저장 생략: {exc}")
            return

        if free_gb <= self._min_free_gb and not self._disk_low_announced:
            self.get_logger().error(
                f"여유 공간 {free_gb:.1f} GB ≤ 하한 {self._min_free_gb} GB — 저장을 중단한다. "
                f"공간 확보 전까지 프레임을 버린다.")
            self._disk_low_announced = True
        elif free_gb > self._min_free_gb:
            self._disk_low_announced = False

        for topic in self._topics:
            msg = self._latest.pop(topic, None)
            if msg is not None:
                self._process(topic, msg, free_gb)

    def _process(self, topic: str, msg: Image, free_gb: float) -> None:
        """한 프레임을 판정하고, 저장 대상이면 JPEG 로 쓴다."""
        camera = camera_name_from_topic(topic)
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:                      # cv_bridge 는 여러 예외형을 던진다
            self.get_logger().warning(f"{camera}: 변환 실패 — 건너뜀: {exc}")
            self._skipped[camera] += 1
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        verdict = judge_frame(
            free_gb=free_gb, min_free_gb=self._min_free_gb,
            prev_gray=self._prev_gray.get(camera), cur_gray=gray,
            min_mean_abs_diff=self._min_diff)
        if not verdict.keep:
            self._skipped[camera] += 1
            return

        stamp_ns = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
        name = frame_filename(camera, self._saved[camera], stamp_ns)
        path = os.path.join(self._out_dir, camera, name)
        ok = cv2.imwrite(path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), self._jpeg_quality])
        if not ok:
            self.get_logger().warning(f"{camera}: 저장 실패 {path}")
            self._skipped[camera] += 1
            return

        # 저장에 성공한 프레임만 기준으로 삼는다 — 버린 프레임을 기준으로 두면
        # 느린 변화가 영원히 '중복'으로 남는다.
        self._prev_gray[camera] = gray
        self._saved[camera] += 1

    def log_stats(self) -> None:
        """카메라별 누적 저장·생략 건수. 주기 타이머와 종료 시 호출된다.

        ⚠ 분모는 **수신 총량이 아니다.** `_skipped` 는 `_process()` 안에서만 오르고
        `_process()` 는 샘플 주기당 카메라별 최대 1회 호출되므로, 주기 사이에 도착한
        프레임은 `_latest` 에서 덮어써져 어느 카운터에도 잡히지 않는다.
        카메라 29.7 Hz · `interval_s=1.0` 이면 분모는 실수신의 약 1/30 이다.
        """
        total = sum(self._saved.values())
        detail = " ".join(f"{c}:{self._saved[c]}/{self._saved[c] + self._skipped[c]}"
                          for c in sorted(self._saved))
        self.get_logger().info(f"누적 저장 {total}장 (카메라별 저장/샘플처리) {detail}")


def main(args=None) -> None:
    rclpy.init(args=args)
    node = DatasetCollectorNode()
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
