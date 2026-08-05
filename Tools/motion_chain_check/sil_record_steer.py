#!/usr/bin/env python3
"""SIL 중 `/motion/wheel_cmd/<action>` 의 조향 지령을 기록해 요약한다.

무엇을 답하려는가 — **크랩이 실제로 90° 를 넘겨 요구하는가.**
시뮬레이션(`simulate_steer_clamp.py`)은 IK 식을 이식해 계산한 것이고, 여기서는
실제로 돌아가는 액션 서버가 낸 지령을 받는다. 둘이 어긋나면 이식이 틀린 것이다.

출력: 표본 수 · 조향 |최대| · 90° 초과 표본 수 · 구동 부호 반전 횟수 ·
      두 클램프(90°/115°)에서 잘렸을 각도량.

사용:
    python3 sil_record_steer.py --topic /motion/wheel_cmd/crab_linear --seconds 60
"""

from __future__ import annotations

import argparse
import math
import sys

import rclpy
from rclpy.node import Node
from trnav_msgs.msg import WheelSetArray


class Recorder(Node):
    def __init__(self, topic: str):
        super().__init__("sil_steer_recorder")
        self.samples = []          # (t, [steer_deg], [vel])
        self.create_subscription(WheelSetArray, topic, self._cb, 10)
        self.get_logger().info(f"구독: {topic}")

    def _cb(self, msg: WheelSetArray):
        t = self.get_clock().now().nanoseconds * 1e-9
        self.samples.append((t,
                             [math.degrees(w.steering) for w in msg.wheels],
                             [w.velocity for w in msg.wheels]))


def summarize(samples, limits=(90.0, 115.0)) -> int:
    if not samples:
        print("표본 0 — 지령이 오지 않았다(액션이 실행되지 않았거나 토픽명이 다르다)")
        return 1
    n_w = len(samples[0][1])
    print(f"표본 {len(samples):,}개 · 휠 {n_w}개 · 구간 {samples[-1][0] - samples[0][0]:.1f} s")
    print()
    for i in range(n_w):
        st = [s[1][i] for s in samples]
        vel = [s[2][i] for s in samples]
        peak = max(abs(a) for a in st)
        over90 = sum(1 for a in st if abs(a) > 90.0 + 1e-9)
        flips = sum(1 for a, b in zip(vel, vel[1:])
                    if a * b < 0 and abs(a) > 1e-6 and abs(b) > 1e-6)
        print(f"  W{i + 1}: 조향 {min(st):+7.2f}° ~ {max(st):+7.2f}° (|최대| {peak:6.2f}°) · "
              f"90° 초과 {over90:,}표본 · 구동 부호반전 {flips}회")
        for lim in limits:
            cut = [abs(a) - lim for a in st if abs(a) > lim + 1e-9]
            if cut:
                print(f"        ±{lim:.0f}° 클램프 시 {len(cut):,}표본이 최대 {max(cut):.2f}° 잘린다")
            else:
                print(f"        ±{lim:.0f}° 클램프 시 잘리는 표본 없음")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="/motion/wheel_cmd/crab_linear")
    ap.add_argument("--seconds", type=float, default=60.0)
    args = ap.parse_args()

    rclpy.init()
    node = Recorder(args.topic)
    t0 = node.get_clock().now().nanoseconds * 1e-9
    try:
        while rclpy.ok() and (node.get_clock().now().nanoseconds * 1e-9 - t0) < args.seconds:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        samples = node.samples
        node.destroy_node()
        rclpy.shutdown()
    return summarize(samples)


if __name__ == "__main__":
    sys.exit(main())
