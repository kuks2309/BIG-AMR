"""verify_live — 실카메라 스트림으로 탐지 파이프라인을 검증하고 증거를 남긴다.

가짜 발행자로 한 2026-07-28 검증(총 23.0 Hz)은 발행자가 같은 프로세스·같은 executor 에 있어
처리량을 **과소평가한 것으로 확인됐다** — 실카메라 측정은 총 29.0 Hz·카메라당 4.77~4.87 Hz·
추론 22.1~24.2 ms·지연 55.4~67.4 ms 다. 본 도구는 **실제 카메라가 뜬 상태**에서 카메라별
갱신률·지연·추론시간을 측정한다.

**화면 확인은 이 도구의 일이 아니다** — 표시는 GUI(`vision_guard`) 소관이므로 여기서는 수치만
낸다(2026-07-29 구조 정정: 탐지기는 결과만, 표시는 GUI).

전제: `usb_cam_publisher` 와 `yolo_detector` 가 이미 떠 있어야 한다(본 도구는 둘 다 띄우지 않는다).

  ros2 run yolo_detector verify_live
  ros2 run yolo_detector verify_live --ros-args -p duration_s:=60.0

판정:
  - 침묵 카메라(검출 메시지 0건)가 하나라도 있으면 실패로 본다.
  - 검출 0건은 실패가 아니다 — 카메라 앞에 사람이 없으면 정상이다.
"""
from __future__ import annotations

import statistics
import sys
from collections import Counter, defaultdict

import rclpy
from ai_msgs.msg import DetectionArray
from rclpy.node import Node

DEFAULT_CAMERAS = [f"cam{i}" for i in range(6)]
DEFAULT_DURATION_S = 30.0


class LiveVerifier(Node):
    """검출 토픽을 받아 카메라별 수신 횟수·추론시간·지연 통계를 모아 콘솔로 보고한다."""

    def __init__(self) -> None:
        super().__init__("verify_live")
        self.declare_parameter("cameras", DEFAULT_CAMERAS)
        self.declare_parameter("duration_s", DEFAULT_DURATION_S)

        self._cameras = list(self.get_parameter("cameras").value)
        self._duration_s = float(self.get_parameter("duration_s").value)

        self._msg_count: Counter = Counter()
        self._infer_ms: dict[str, list[float]] = defaultdict(list)
        self._latency_ms: dict[str, list[float]] = defaultdict(list)
        self._classes: dict[str, Counter] = defaultdict(Counter)
        self._max_dets: Counter = Counter()

        for camera in self._cameras:
            self.create_subscription(
                DetectionArray, f"/{camera}/detections",
                lambda m, c=camera: self._on_detections(c, m), 10)

        self._started_ns = self.get_clock().now().nanoseconds
        self.get_logger().info(
            f"실스트림 검증 시작 — 카메라 {len(self._cameras)}대, {self._duration_s:.0f}초")

    # ── 콜백 ────────────────────────────────────────────────────────────────
    def _on_detections(self, camera: str, msg: DetectionArray) -> None:
        self._msg_count[camera] += 1
        self._infer_ms[camera].append(msg.inference_ms)
        self._latency_ms[camera].append(msg.latency_ms)
        self._max_dets[camera] = max(self._max_dets[camera], len(msg.detections))
        for det in msg.detections:
            self._classes[camera][det.class_name] += 1

    # ── 판정 ────────────────────────────────────────────────────────────────
    def elapsed_s(self) -> float:
        return (self.get_clock().now().nanoseconds - self._started_ns) / 1e9

    def is_done(self) -> bool:
        return self.elapsed_s() >= self._duration_s

    def report(self) -> int:
        """콘솔 보고. 침묵 카메라가 있으면 1, 없으면 0 을 돌려준다."""
        elapsed = max(self.elapsed_s(), 1e-6)
        total = sum(self._msg_count.values())
        print("\n" + "=" * 68)
        print(f"실스트림 검증 결과 — {elapsed:.1f}초")
        print("=" * 68)
        print(f"전체 처리량: {total}회 ({total / elapsed:.1f} Hz)")
        print(f"{'카메라':<8}{'수신':>6}{'Hz':>7}{'추론ms':>9}{'지연ms':>9}  검출 클래스")
        for camera in self._cameras:
            count = self._msg_count[camera]
            infer = statistics.mean(self._infer_ms[camera]) if self._infer_ms[camera] else 0.0
            lat = statistics.mean(self._latency_ms[camera]) if self._latency_ms[camera] else 0.0
            classes = dict(self._classes[camera]) or "-"
            print(f"{camera:<8}{count:>6}{count / elapsed:>7.2f}{infer:>9.1f}{lat:>9.1f}  {classes}")

        silent = [c for c in self._cameras if self._msg_count[c] == 0]
        counts = [self._msg_count[c] for c in self._cameras if self._msg_count[c] > 0]
        if counts:
            print(f"\n공평성: 최소 {min(counts)} / 최대 {max(counts)} (차이 {max(counts) - min(counts)}회)")
        print(f"최대 동시 검출: " + " ".join(
            f"{c}:{self._max_dets[c]}" for c in self._cameras))

        if silent:
            print(f"\n❌ 침묵 카메라: {silent}")
            print("   → 발행자가 안 떴거나(ros2 topic list 확인), 탐지 노드의 camera_topics 설정 불일치.")
            return 1
        print("\n✅ 전 카메라 수신 확인. (검출 0건은 정상 — 카메라 앞에 대상이 없으면 그렇다.)")
        print("   ⚠ 이 결과는 파이프라인 동작 증거이지 검출 '정확도' 보증이 아니다.")
        print("     COCO 사전학습은 일반 사진 기반이라 CCTV 각도·광각·산업 조명에서 성능이")
        print("     떨어질 수 있다. 정확도는 자체 라벨링한 검증셋으로만 정량화된다.")
        return 0


def main(args=None) -> int:
    rclpy.init(args=args)
    node = LiveVerifier()
    exit_code = 1
    try:
        while rclpy.ok() and not node.is_done():
            rclpy.spin_once(node, timeout_sec=0.1)
        exit_code = node.report()
    except KeyboardInterrupt:
        exit_code = node.report()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
