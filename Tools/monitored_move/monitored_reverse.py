#!/usr/bin/env python3
"""감시하면서 후진한다 — 액션 자기보고를 믿지 않는다.

## 왜 액션 자기보고를 감시로 쓰지 않는가

액션의 진행거리·상태는 **액션이 측위 입력으로 계산한 값**이다. 그 입력이 고장나면 보고도
같이 고장난다. 측위 값이 얼어붙으면 진행거리가 `0.00 m` 에 머물고, 액션은 「아직 목표에
못 갔다」고 판단해 **지령을 계속 낸다** — 로봇은 개루프로 달리는데 보고는 「제자리」다.
그래서 여기서는 **독립 관측**(측위 좌표값·라이다)으로만 판정한다.

## 왜 stamp 가 아니라 좌표값을 보는가

`seer_pose_publisher` 는 값이 바뀌지 않아도 **매 주기 새 stamp 를 찍는다.** stamp 나이만
보는 신선도 검사는 「신선하지만 얼어붙은」 자세를 통과시킨다. **신선도 ≠ 살아있음** 이므로
이 도구는 좌표값이 마지막으로 **변한 시각**을 따로 기록해 판정한다.

## 감시 조건 (하나라도 걸리면 즉시 취소)

- 측위 **값**이 `--freeze-sec` 이상 변하지 않는다(정지 지령 전인데 안 움직인다)
- 후방 여유가 `--min-clearance` 미만 (스캔 없거나 낡으면 0.0 = fail-closed)
- 실제 이동량이 지령의 `--overrun` 배를 넘는다
- 측위 메시지가 `--pose-stale` 이상 끊긴다

`SIGTERM`·`SIGHUP` 에서도 취소가 나간다. `SIGKILL` 은 막을 수 없다 — 물리 E-STOP 뿐이다.

## 사용

    python3 Tools/monitored_move/monitored_reverse.py --distance 1.0 --speed 0.05
"""

from __future__ import annotations

import argparse
import math
import signal
import sys
import time

import numpy as np


def yaw_of(q) -> float:
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y ** 2 + q.z ** 2))


def main() -> int:
    ap = argparse.ArgumentParser(description="감시 후진")
    ap.add_argument("--distance", type=float, default=1.0, help="후진 거리 [m]")
    ap.add_argument("--speed", type=float, default=0.05, help="속도 크기 [m/s]")
    ap.add_argument("--min-clearance", type=float, default=1.2, help="후방 최소 여유 [m]")
    ap.add_argument("--freeze-sec", type=float, default=1.5, help="측위 값 정지 허용 [s]")
    ap.add_argument("--pose-stale", type=float, default=0.5, help="측위 메시지 두절 허용 [s]")
    ap.add_argument("--overrun", type=float, default=1.3, help="지령 대비 이동량 상한 배수")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    import rclpy
    from geometry_msgs.msg import PoseStamped
    from rclpy.action import ActionClient
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan
    from trnav_2ws_interfaces.action import AMRMotionYawControl

    rclpy.init()
    node = Node("monitored_reverse")
    st: dict = {"pose": None, "pose_at": 0.0, "moved_at": 0.0,
                "scan": None, "scan_at": 0.0}

    def on_pose(m):
        p = (m.pose.position.x, m.pose.position.y, yaw_of(m.pose.orientation))
        prev = st["pose"]
        now = time.time()
        # ⚠ **값이 바뀐 시각**을 따로 기록한다. stamp 나이가 아니라 이것이 「살아있음」이다.
        if prev is None or math.hypot(p[0] - prev[0], p[1] - prev[1]) > 1e-4:
            st["moved_at"] = now
        st["pose"], st["pose_at"] = p, now

    node.create_subscription(PoseStamped, "/robot_pose", on_pose, 10)
    node.create_subscription(
        LaserScan, "/scan_merged",
        lambda m: (st.__setitem__("scan", m), st.__setitem__("scan_at", time.time())),
        qos_profile_sensor_data)

    def pump(sec: float) -> None:
        t = time.time()
        while time.time() - t < sec:
            rclpy.spin_once(node, timeout_sec=0.02)

    def clearance(direction_rad: float, half_deg: float = 25.0) -> float:
        sc = st["scan"]
        if sc is None or (time.time() - st["scan_at"]) > 0.5:
            return 0.0
        r = np.array(sc.ranges)
        ang = sc.angle_min + np.arange(len(r)) * sc.angle_increment
        ok = np.isfinite(r) & (r > sc.range_min) & (r < sc.range_max)
        d = np.abs((ang - direction_rad + math.pi) % (2 * math.pi) - math.pi)
        m = ok & (d < math.radians(half_deg))
        return float(np.min(r[m])) if m.any() else 0.0

    pump(3.0)
    if st["pose"] is None:
        print("⚠ /robot_pose 미수신", file=sys.stderr)
        return 2
    x0, y0, th0 = st["pose"]
    rear = clearance(math.pi)
    print(f"현재     : ({x0:+.4f}, {y0:+.4f}) yaw {math.degrees(th0):+.2f}°")
    print(f"후진     : {a.distance:.2f} m · {a.speed:.3f} m/s")
    print(f"후방 여유: {rear:.3f} m (임계 {a.min_clearance:.2f})")
    if rear < a.min_clearance:
        print("⚠ 여유 부족 — 보내지 않는다", file=sys.stderr)
        return 3
    if a.dry_run:
        print("[dry-run] 보내지 않음")
        return 0

    cl = ActionClient(node, AMRMotionYawControl, "/amr_motion_yaw_control_abstract")
    if not cl.wait_for_server(timeout_sec=15.0):
        print("⚠ yaw_control 서버 없음", file=sys.stderr)
        return 2

    g = AMRMotionYawControl.Goal()
    g.target_yaw_deg = math.degrees(th0)      # 현재 헤딩 유지
    g.target_distance = a.distance
    g.vx_max = -abs(a.speed)                  # 음수 = 후진
    g.acceleration = 0.05
    g.max_steer_deg = 10.0
    g.kp, g.kd, g.ki, g.i_max_deg = 1.0, 0.1, 0.0, 0.0
    g.counter_steer = False
    g.hold_steer = False
    g.exit_steer_angle = 0.0
    g.max_timeout_sec = 90.0
    g.enable_localization_watchdog = True

    box: dict = {"gh": None, "stop": None}

    def cancel(why: str) -> bool:
        """취소를 보내고 **보냈는지**를 돌려준다(보고와 사실을 어긋나지 않게)."""
        if box["stop"] is None:
            box["stop"] = why
        gh = box["gh"]
        if gh is None:
            return False
        try:
            gh.cancel_goal_async()
            return True
        except Exception:
            return False

    def on_sig(signum, frame):
        cancel(f"signal {signum}")
        raise KeyboardInterrupt(f"signal {signum}")

    # ⚠ **SIGINT(Ctrl-C) 포함.** 종전에는 빠져 있어 `except KeyboardInterrupt` 가
    #   「취소 송신」이라 출력만 하고 실제로는 보내지 않았다 — 거짓 보고였다.
    for sg in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sg, on_sig)

    rc = 0
    try:
        gf = cl.send_goal_async(g)
        rclpy.spin_until_future_complete(node, gf, timeout_sec=20.0)
        gh = gf.result()
        if gh is None or not gh.accepted:
            print("⚠ 목표 거부", file=sys.stderr)
            return 1
        box["gh"] = gh
        print("접수 — 감시 시작")

        rf = gh.get_result_async()
        t0 = time.time()
        last_print = 0.0
        st["moved_at"] = time.time()
        while not rf.done() and time.time() - t0 < 120:
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.time()
            x, y, th = st["pose"]
            d = math.hypot(x - x0, y - y0)
            rear = clearance(math.pi)

            if now - st["pose_at"] > a.pose_stale:
                cancel(f"측위 메시지 {a.pose_stale}s 두절"); break
            if now - st["moved_at"] > a.freeze_sec:
                cancel(f"측위 **값**이 {a.freeze_sec}s 동안 변하지 않음 — 얼어붙은 자세로 개루프 주행 의심")
                break
            if rear < a.min_clearance:
                cancel(f"후방 여유 {rear:.2f} m < {a.min_clearance:.2f} m"); break
            if d > a.distance * a.overrun:
                cancel(f"이동 {d:.2f} m 가 지령 {a.distance:.2f} m 의 {a.overrun}배 초과"); break

            if now - last_print > 0.5:
                last_print = now
                print(f"  이동 {d:5.2f}/{a.distance:.2f} m · 후방 {rear:5.2f} m · "
                      f"({x:+.3f},{y:+.3f}) yaw {math.degrees(th):+6.2f}°")

        if box["stop"]:
            print(f"\n⚠ 감시 발동 — 취소: {box['stop']}", file=sys.stderr)
            pump(4.0)
            rc = 5
        elif rf.done():
            res = rf.result().result
            x, y, th = st["pose"]
            print(f"\n결과 : status {res.status} · 액션보고 {res.actual_distance:.3f} m")
            print(f"  실제 이동(측위) {math.hypot(x-x0, y-y0):.3f} m · "
                  f"({x:+.4f},{y:+.4f}) yaw {math.degrees(th):+.2f}°")
            rc = 0 if res.status == 0 else 1
        else:
            cancel("결과 시한 초과"); pump(4.0); rc = 1
    except KeyboardInterrupt:
        sent = cancel("사용자 중단")
        print(f"\n중단 — 취소 {'송신함' if sent else '**미송신**(목표 미접수)'}", file=sys.stderr)
        pump(4.0)
        rc = 4
    except BaseException as exc:
        sent = cancel(f"예외 {type(exc).__name__}")
        print(f"\n⚠ 예외 {type(exc).__name__}: {exc} — 취소 "
              f"{'송신함' if sent else '**미송신**'}", file=sys.stderr)
        pump(4.0)
        rc = 1
    finally:
        try:
            node.destroy_node(); rclpy.shutdown()
        except Exception:
            pass
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
