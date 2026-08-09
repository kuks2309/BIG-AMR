#!/usr/bin/env python3
"""Seer 개루프 운동(19205/2010) + 맵 측위 폐루프로 목표 자세까지 조그 복귀.

**용도** — PC 측 모션(`turn`·`spin`·`yaw_control`)이 실패했거나 믿을 수 없을 때
로봇을 알려진 자세로 되돌리는 **복구 도구**. 상시 운용용이 아니다.

**왜 IMU 를 쓰지 않는가**
`turn`·`spin`·`yaw_control` 은 전부 IMU 로 루프를 닫는다. 2026-08-10 실기에서
저속 회전(약 0.5 °/s) 구간에 IMU 가 실제 회전 +24.7° 를 +1.7° 로만 읽어 로봇이
25° 틀어진 채 `status 0` 로 종료한 사례가 있다(`debt-054`). 복구 도구가 같은
센서로 루프를 닫으면 **고장 원인으로 고장을 고치려는** 꼴이 되므로, 본 도구는
**맵 기준 측위(`/robot_pose`)만** 되먹인다.

**동작 순서 — 스핀 → 크랩** (2026-08-10 사용자 제안)

    Phase 1  제자리 회전으로 **최종 헤딩**을 먼저 맞춘다
    Phase 2  헤딩을 유지한 채 `vx`(전후) · `vy`(크랩)로 **위치만** 잡는다

헤딩을 먼저 확정하므로 자세를 두 번 흔들지 않는다. 종전 방식
(정렬 회전 → 전진 → 최종 회전)은 회전이 2회였다.
이 기체는 inline dual-steer(2WS)라 크랩이 가능하다 — `vy` 를 쓸 수 있다.

**안전**
  · 매 주기 전방/진행방향 라이다 여유를 확인하고 임계 미만이면 즉시 정지
  · 오차가 늘어나면(부호 규약 불일치 등) 즉시 정지 — 발산 방지
  · 전체 시한 초과 시 정지
  · `finally` 에서 반드시 `2000`(stop) 송신 — 예외·중단에도 로봇이 계속 가지 않게 한다
  · `can_relay` 가 제어권을 쥐고 있으면 Seer 는 버스를 못 쓴다 — **먼저 반납할 것**

⚠ **검증 상태 (2026-08-10 기준)**
  · Phase 1(제자리 회전)과 `vx` 병진, 그리고 맵 측위 폐루프·정지 처리는 **실기 확인됨**
    — 같은 논리의 인라인 스크립트로 2.02 m / 28.7° 복귀를 수행해 잔차 36 mm / 0.76° 를 얻었다.
  · **Phase 2 의 `vy`(크랩)는 미검증이다.** Seer 에 `vy` 를 보낸 적이 없어 **부호 규약조차
    확인되지 않았다.** 첫 사용 시 `--pos-tol` 을 크게 잡고 짧은 거리로 시작하라.
    부호가 반대면 오차가 커지므로 발산 가드가 걸려 즉시 정지한다(설계상 안전하나 미실증).

사용:
    python3 Tools/seer_jog/seer_jog.py --x -12.5707 --y 9.6183 --yaw -1.86
    python3 Tools/seer_jog/seer_jog.py --x ... --y ... --yaw ... --dry-run   # 계획만 출력
"""

from __future__ import annotations

import argparse
import json
import math
import socket
import struct
import time

SYNC = 0x5A
VERSION = 0x01
REQ_MOTION = 2010  # robot_control_motion_req — 개루프 vx, vy, w
REQ_STOP = 2000    # robot_control_stop_req


def pack(seq: int, code: int, payload: dict | None = None) -> bytes:
    """Seer NetProtocol 프레임. 헤더 16바이트 + JSON 본문.

    정본: References/Seer-Driver/robokit_tcp_api.md §4-2.
    """
    body = json.dumps(payload).encode() if payload is not None else b""
    return struct.pack(">BBHIH6s", SYNC, VERSION, seq & 0xFFFF, len(body), code, b"\x00" * 6) + body


def wrap(deg: float) -> float:
    """각도를 (-180, +180] 로 정규화."""
    return (deg + 180.0) % 360.0 - 180.0


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def main() -> int:
    ap = argparse.ArgumentParser(description="Seer 조그 복귀 (맵 측위 폐루프)")
    ap.add_argument("--x", type=float, required=True, help="목표 x [m, map]")
    ap.add_argument("--y", type=float, required=True, help="목표 y [m, map]")
    ap.add_argument("--yaw", type=float, required=True, help="목표 heading [deg, map]")
    ap.add_argument("--host", default="192.168.44.82")
    ap.add_argument("--port", type=int, default=19205)
    ap.add_argument("--pose-topic", default="/robot_pose")
    ap.add_argument("--pos-tol", type=float, default=0.02, help="위치 허용 [m]")
    ap.add_argument("--yaw-tol", type=float, default=0.5, help="헤딩 허용 [deg]")
    ap.add_argument("--v-max", type=float, default=0.08, help="병진 속도 상한 [m/s]")
    ap.add_argument("--w-max", type=float, default=0.15, help="회전 속도 상한 [Seer 단위]")
    ap.add_argument("--min-clearance", type=float, default=0.5, help="진행방향 최소 여유 [m]")
    ap.add_argument("--deadline", type=float, default=240.0, help="전체 시한 [s]")
    ap.add_argument("--dry-run", action="store_true", help="계획만 출력하고 움직이지 않는다")
    a = ap.parse_args()

    import numpy as np
    import rclpy
    from geometry_msgs.msg import PoseStamped
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan

    rclpy.init()
    node = Node("seer_jog")
    state: dict = {"pose": None, "scan": None}

    def yaw_of(q) -> float:
        return math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y**2 + q.z**2)))

    node.create_subscription(
        PoseStamped, a.pose_topic,
        lambda m: state.__setitem__("pose", (m.pose.position.x, m.pose.position.y, yaw_of(m.pose.orientation))), 10)
    node.create_subscription(LaserScan, "/scan_merged", lambda m: state.__setitem__("scan", m),
                             qos_profile_sensor_data)

    def pump(sec: float) -> None:
        t = time.time()
        while time.time() - t < sec:
            rclpy.spin_once(node, timeout_sec=0.02)

    def clearance(direction_rad: float, half_width_deg: float = 25.0) -> float:
        """차체 기준 `direction_rad` 방향 부채꼴의 최소 거리. 스캔 없으면 큰 값."""
        sc = state["scan"]
        if sc is None:
            return 99.0
        r = np.array(sc.ranges)
        ang = sc.angle_min + np.arange(len(r)) * sc.angle_increment
        ok = np.isfinite(r) & (r > sc.range_min) & (r < sc.range_max)
        d = np.abs((ang - direction_rad + math.pi) % (2 * math.pi) - math.pi)
        m = ok & (d < math.radians(half_width_deg))
        return float(np.min(r[m])) if m.any() else 99.0

    pump(2.0)
    if state["pose"] is None:
        print(f"⚠ {a.pose_topic} 미수신 — 측위가 살아 있는지 먼저 확인하세요")
        return 2
    p0 = state["pose"]
    dx, dy = a.x - p0[0], a.y - p0[1]
    print(f"현재 ({p0[0]:+.4f}, {p0[1]:+.4f}) yaw {p0[2]:+.3f}°")
    print(f"목표 ({a.x:+.4f}, {a.y:+.4f}) yaw {a.yaw:+.3f}°")
    print(f"계획  Phase1 제자리 회전 {wrap(a.yaw - p0[2]):+.2f}°  →  Phase2 크랩 이동 {math.hypot(dx, dy) * 1000:.0f} mm")
    if a.dry_run:
        print("(dry-run — 움직이지 않음)")
        return 0

    sock = socket.create_connection((a.host, a.port), timeout=5)
    seq = [1]

    def send(vx: float, vy: float, w: float) -> None:
        sock.send(pack(seq[0], REQ_MOTION, {"vx": float(vx), "vy": float(vy), "w": float(w)}))
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

    t_start = time.time()
    rc = 0
    try:
        # ── Phase 1: 최종 헤딩으로 제자리 회전 ──
        worst = None
        while True:
            if time.time() - t_start > a.deadline:
                print("⚠ 시한 초과 — 정지")
                rc = 3
                break
            pump(0.1)
            p = state["pose"]
            yerr = wrap(a.yaw - p[2])
            if abs(yerr) < a.yaw_tol:
                break
            if worst is None or abs(yerr) < worst:
                worst = abs(yerr)
            elif abs(yerr) > worst * 1.3 + 0.5:
                print(f"⚠ 헤딩 오차가 커진다({worst:.2f}° → {abs(yerr):.2f}°) — 부호 규약 의심, 정지")
                rc = 4
                break
            send(0.0, 0.0, clamp(math.radians(yerr) * 1.2, -a.w_max, a.w_max))
        stop()
        pump(1.5)
        p = state["pose"]
        print(f"── Phase1 완료  yaw {p[2]:+.3f}°  (오차 {wrap(a.yaw - p[2]):+.2f}°)")

        # ── Phase 2: 헤딩 유지한 채 크랩+전후진으로 위치 ──
        worst = None
        while rc == 0:
            if time.time() - t_start > a.deadline:
                print("⚠ 시한 초과 — 정지")
                rc = 3
                break
            pump(0.1)
            p = state["pose"]
            ex, ey = a.x - p[0], a.y - p[1]
            dist = math.hypot(ex, ey)
            if dist < a.pos_tol:
                break
            if worst is None or dist < worst:
                worst = dist
            elif dist > worst * 1.3 + 0.02:
                print(f"⚠ 위치 오차가 커진다({worst * 1000:.0f} → {dist * 1000:.0f} mm) — vy 부호 의심, 정지")
                rc = 4
                break
            th = math.radians(p[2])
            vx_b = ex * math.cos(th) + ey * math.sin(th)   # 차체 전방 성분
            vy_b = -ex * math.sin(th) + ey * math.cos(th)  # 차체 좌측 성분
            head = math.atan2(vy_b, vx_b)
            clr = clearance(head)
            if clr < a.min_clearance:
                print(f"⚠ 진행방향 여유 {clr:.2f} m — 정지")
                rc = 5
                break
            gain = clamp(dist * 0.6, 0.015, a.v_max) / max(dist, 1e-6)
            yerr = wrap(a.yaw - p[2])
            send(vx_b * gain, vy_b * gain, clamp(math.radians(yerr) * 0.8, -0.05, 0.05))
        stop()
    finally:
        stop()
        time.sleep(0.3)
        sock.close()

    pump(2.0)
    p = state["pose"]
    print(f"\n최종 ({p[0]:+.4f}, {p[1]:+.4f}) yaw {p[2]:+.3f}°")
    print(f"목표 대비  {math.hypot(p[0] - a.x, p[1] - a.y) * 1000:.0f} mm / {wrap(p[2] - a.yaw):+.2f}°")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
