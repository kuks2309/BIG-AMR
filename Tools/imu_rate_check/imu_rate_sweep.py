#!/usr/bin/env python3
"""IMU 회전 추종을 **회전율의 함수**로 측정한다 (debt-054 규명 도구).

제자리 회전시키면서 **IMU** 와 **맵 기준 측위(mcl2d)** 의 회전량을 동시에 적산해
`IMU/맵` 비를 실측 회전율별로 낸다. 비가 1 에서 멀어지는 구간이 **IMU 를 믿을 수 없는 구간**이다.

## 왜 액션서버(spin)를 쓰지 않는가

`spin` 의 Stage 1 에는 `min_speed_dps`(기본 2.0) 하한이 있어
(`spin_action_server.cpp:319`) **저속 구간을 아예 만들 수 없다.** PID·프로파일이
끼면 무엇을 재는지도 흐려진다. 그래서 Seer 개루프(`19205 / 2010`)로 직접 돌린다 —
제어기 없이 **순수 센서 대조**가 된다.

## 계측 함정 — 반드시 연속 적산할 것

끝점 두 샘플의 차이에 `wrap()` 을 걸면 **|Δ| > 180° 에서 앨리어싱**되어 큰 회전이
작은 값(심하면 반대 부호)으로 접힌다. 본 도구는 매 샘플 델타를 unwrap 해 누적한다.

정지 후에도 `--settle` 만큼 더 적산한다 — AHRS 는 정지 직후 수 초간 자세추정이
되돌아가므로(기동 후 완화), 그것까지 포함해야 「기동 1회의 총 판독」이 된다.

## 사용

    # can_relay 는 반드시 반납 상태 (Seer 가 버스를 써야 한다)
    ros2 service call /can_relay_node/engage std_srvs/srv/SetBool "{data: false}"
    python3 Tools/imu_rate_check/imu_rate_sweep.py
    python3 Tools/imu_rate_check/imu_rate_sweep.py --w 0.05 -0.05 0.05 -0.05   # 반복 측정

실측 결과와 이력은 `Tools/imu_rate_check/README.md` 및
`docs/issues_and_fixes/issues_and_fixes.md` 에 둔다 — 주석은 현재 코드의 사실만 담는다.
"""

from __future__ import annotations

import argparse
import json
import math

import numpy as np
import socket
import struct
import sys
import time

# 스캔 신선도 상한 — 이보다 낡으면 「없는 것」으로 친다(fail-closed).
SCAN_STALE_S = 0.5
# 회전 시 차체 모서리가 쓸고 가는 반경(축거 1.2 m) + 라이다 배제영역 여유.
MIN_SWEPT_CLEARANCE_M = 1.3

REQ_MOTION = 2010
REQ_STOP = 2000


def pack(seq: int, code: int, payload: dict | None = None) -> bytes:
    body = json.dumps(payload).encode() if payload is not None else b""
    return struct.pack(">BBHIH6s", 0x5A, 0x01, seq & 0xFFFF, len(body), code, b"\x00" * 6) + body


def wrap(deg: float) -> float:
    return (deg + 180.0) % 360.0 - 180.0


def main() -> int:
    ap = argparse.ArgumentParser(description="IMU 회전 추종 대 회전율 특성 측정")
    # ⚠ 상한이 없어 `--w 5.0` 오타(0.05 의도)면 **286 °/s** 가 그대로 개루프로 나간다.
    #   이 도구는 저속 회전 특성을 재는 것이므로 큰 값은 목적상으로도 무의미하다.
    ap.add_argument("--w-limit", type=float, default=0.2,
                    help="각 |w| 의 상한 [rad/s] (기본 0.2 = 11.5 °/s)")
    ap.add_argument("--w", type=float, nargs="+", default=[0.005, -0.010, 0.020, -0.050, 0.100],
                    help="Seer w 지령 목록 (부호 교대 권장 — 원점 근처 유지)")
    ap.add_argument("--target-deg", type=float, default=25.0, help="점당 목표 회전량 [deg]")
    ap.add_argument("--tmax", type=float, default=70.0, help="점당 시간 상한 [s]")
    ap.add_argument("--settle", type=float, default=4.0, help="정지 후 추가 적산 [s] (AHRS 완화 포함)")
    ap.add_argument("--host", default="192.168.44.82")
    ap.add_argument("--port", type=int, default=19205)
    a = ap.parse_args()

    # ⚠ 실행 **전에** 거부한다. 개루프 지령이라 한 번 나가면 정지(2000)가 도달할 때까지
    #   그 속도로 계속 돈다 — 벤더 API 에 워치독도 지속시간 필드도 없다.
    bad = [w for w in a.w if abs(w) > a.w_limit]
    if bad:
        print(f"⚠ |w| 가 상한 {a.w_limit} rad/s 를 넘는 값이 있다: {bad}\n"
              f"   단위는 **rad/s** 다(0.05 rad/s = 2.9 °/s). 큰 값이 정말 필요하면 "
              f"--w-limit 을 함께 올릴 것.", file=sys.stderr)
        return 2



    import rclpy
    from geometry_msgs.msg import PoseStamped
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Imu, LaserScan

    rclpy.init()
    node = Node("imu_rate_sweep")
    cur: dict = {"imu": None, "map": None, "scan": None, "scan_at": 0.0}

    def yaw_of(q) -> float:
        return math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y**2 + q.z**2)))

    node.create_subscription(Imu, "/imu/data", lambda m: cur.__setitem__("imu", yaw_of(m.orientation)),
                             qos_profile_sensor_data)
    # ⚠ 이 도구도 **실기를 회전시킨다.** 종전에는 여유 판정이 전혀 없었다.
    #   제자리 회전이라 진행 방향이 없으므로 **전방위 최소**를 본다. 차체(축거 1.2 m)는
    #   회전 시 모서리가 반경 0.75~0.85 m 를 쓸고 지나간다. `/scan_merged` 는 배제영역
    #   (x∈[-0.96,0.98])을 삭제하고 `use_inf: True` 라 그보다 가까운 점은 관측되지 않으므로
    #   임계를 그 위로 잡는다. 스캔이 없거나 낡으면 **0.0(fail-closed)** 이다.
    node.create_subscription(LaserScan, "/scan_merged",
                             lambda m: (cur.__setitem__("scan", m),
                                        cur.__setitem__("scan_at", time.time())),
                             qos_profile_sensor_data)
    node.create_subscription(PoseStamped, "/robot_pose",
                             lambda m: cur.__setitem__("map", yaw_of(m.pose.orientation)), 10)

    def swept_clearance() -> float:
        """전방위 최소 거리. 스캔이 없거나 낡으면 **0.0**(fail-closed)."""
        sc = cur["scan"]
        if sc is None or (time.time() - cur["scan_at"]) > SCAN_STALE_S:
            return 0.0
        r = np.array(sc.ranges)
        ok = np.isfinite(r) & (r > sc.range_min) & (r < sc.range_max)
        return float(np.min(r[ok])) if ok.any() else 0.0

    def pump(sec: float) -> None:
        t = time.time()
        while time.time() - t < sec:
            rclpy.spin_once(node, timeout_sec=0.02)

    pump(2.0)
    if cur["imu"] is None or cur["map"] is None:
        print("⚠ /imu/data 또는 /robot_pose 미수신")
        return 2

    sock = socket.create_connection((a.host, a.port), timeout=5)
    seq = [1]

    def send(w: float) -> None:
        sock.send(pack(seq[0], REQ_MOTION, {"vx": 0.0, "vy": 0.0, "w": float(w)}))
        seq[0] += 1
        try:
            sock.settimeout(0.03)
            sock.recv(4096)
        except OSError:
            pass

    def stop() -> None:
        sock.send(pack(seq[0], REQ_STOP))
        seq[0] += 1
        try:
            sock.settimeout(0.3)
            sock.recv(4096)
        except OSError:
            pass

    print(f"{'w_cmd':>7} {'맵 적산':>10} {'IMU 적산':>10} {'실측 회전율':>13} {'IMU/맵':>8} {'소요':>7}")
    rows = []
    try:
        for w in a.w:
            pump(2.5)
            acc_m = acc_i = 0.0
            prev_m, prev_i = cur["map"], cur["imu"]
            t0 = time.time()
            stalled_since = time.time()
            while time.time() - t0 < a.tmax and abs(acc_m) < a.target_deg:
                # ⚠ 회전 **전·중** 매 주기 전방위 여유를 본다(제자리 회전이라 방향이 없다).
                clr = swept_clearance()
                if clr < MIN_SWEPT_CLEARANCE_M:
                    print(f"⚠ 회전 반경 안 여유 {clr:.2f} m < {MIN_SWEPT_CLEARANCE_M} m — 정지",
                          file=sys.stderr)
                    stop()
                    return 4
                send(w)
                pump(0.1)
                d_m = wrap(cur["map"] - prev_m)
                acc_m += d_m
                acc_i += wrap(cur["imu"] - prev_i)
                prev_m, prev_i = cur["map"], cur["imu"]
                # ⚠ 적산이 멈추면 **tmax 를 다 채우며 계속 돈다** — w=0.100 이면 약 400°.
                #   측위가 죽었는데 「목표 각에 도달하지 못했다」로 읽고 버티는 형태다.
                if abs(d_m) > 1e-4:
                    stalled_since = time.time()
                elif time.time() - stalled_since > 5.0:
                    print("⚠ 맵 적산이 5 s 동안 변하지 않는다 — 측위 두절 의심, 정지", file=sys.stderr)
                    stop()
                    return 3
            elapsed = time.time() - t0
            stop()
            t1 = time.time()
            while time.time() - t1 < a.settle:   # 정지 후 완화분까지 포함
                pump(0.1)
                acc_m += wrap(cur["map"] - prev_m)
                acc_i += wrap(cur["imu"] - prev_i)
                prev_m, prev_i = cur["map"], cur["imu"]
            rate = acc_m / elapsed
            ratio = acc_i / acc_m if abs(acc_m) > 1.0 else float("nan")
            print(f"{w:>+7.3f} {acc_m:>+10.3f} {acc_i:>+10.3f} {rate:>+12.3f}° /s {ratio:>8.3f} {elapsed:>6.1f}s")
            rows.append((abs(rate), ratio))
    finally:
        stop()
        time.sleep(0.3)
        sock.close()

    print("\n실측 회전율[°/s] → IMU/맵 비")
    for r, q in sorted(rows):
        print(f"  {r:>6.3f}  →  {q:>6.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
