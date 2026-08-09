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
import socket
import struct
import time

REQ_MOTION = 2010
REQ_STOP = 2000


def pack(seq: int, code: int, payload: dict | None = None) -> bytes:
    body = json.dumps(payload).encode() if payload is not None else b""
    return struct.pack(">BBHIH6s", 0x5A, 0x01, seq & 0xFFFF, len(body), code, b"\x00" * 6) + body


def wrap(deg: float) -> float:
    return (deg + 180.0) % 360.0 - 180.0


def main() -> int:
    ap = argparse.ArgumentParser(description="IMU 회전 추종 대 회전율 특성 측정")
    ap.add_argument("--w", type=float, nargs="+", default=[0.005, -0.010, 0.020, -0.050, 0.100],
                    help="Seer w 지령 목록 (부호 교대 권장 — 원점 근처 유지)")
    ap.add_argument("--target-deg", type=float, default=25.0, help="점당 목표 회전량 [deg]")
    ap.add_argument("--tmax", type=float, default=70.0, help="점당 시간 상한 [s]")
    ap.add_argument("--settle", type=float, default=4.0, help="정지 후 추가 적산 [s] (AHRS 완화 포함)")
    ap.add_argument("--host", default="192.168.44.82")
    ap.add_argument("--port", type=int, default=19205)
    a = ap.parse_args()

    import rclpy
    from geometry_msgs.msg import PoseStamped
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Imu

    rclpy.init()
    node = Node("imu_rate_sweep")
    cur: dict = {"imu": None, "map": None}

    def yaw_of(q) -> float:
        return math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y**2 + q.z**2)))

    node.create_subscription(Imu, "/imu/data", lambda m: cur.__setitem__("imu", yaw_of(m.orientation)),
                             qos_profile_sensor_data)
    node.create_subscription(PoseStamped, "/robot_pose",
                             lambda m: cur.__setitem__("map", yaw_of(m.pose.orientation)), 10)

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
            while time.time() - t0 < a.tmax and abs(acc_m) < a.target_deg:
                send(w)
                pump(0.1)
                acc_m += wrap(cur["map"] - prev_m)
                acc_i += wrap(cur["imu"] - prev_i)
                prev_m, prev_i = cur["map"], cur["imu"]
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
