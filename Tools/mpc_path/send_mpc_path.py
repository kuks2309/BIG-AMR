#!/usr/bin/env python3
"""`mpc`(Pure Pursuit) 액션에 map 프레임 경로를 만들어 보낸다 — 실기 검증용.

## 왜 필요한가

`mpc` 는 `nav_msgs/Path`(map 프레임, ≥2 pose)를 goal 로 받는데, **실기용 경로를 만들어
보내는 수단이 저장소에 없었다**(`csm/roads` 는 MES(Manufacturing Execution System)
시뮬레이터 좌표계라 이 맵에 못 쓴다). `mpc` 는 실기 검증 0 건이라 첫 주행이 필요하다.

## ⚠ 이 도구는 실기를 움직인다

- 경로는 **현재 자세에서 시작**한다. `mpc_max_lateral_offset`(1.0 m)이 시작점과 로봇의
  거리를 검사하므로, 다른 곳에서 시작하는 경로를 주면 액션이 거부한다.
- 보내기 전에 **라이다 여유**를 확인하고 부족하면 거부한다. 스캔이 없거나 낡으면
  `0.0`(fail-closed)으로 친다 — 「라이다가 죽으면 무한히 안전」이 되지 않게.
- 기본은 `--dry-run` 이 **아니다**. 실제로 보낸다. 계획만 보려면 `--dry-run` 을 붙인다.
- `SIGTERM`·`SIGHUP` 에서도 취소가 나가도록 핸들러를 건다. `SIGKILL` 은 막을 수 없다 —
  그때는 물리 E-STOP 이 유일한 백스톱이다.

## 사용

    # 계획만 출력 (로봇 미동작)
    python3 Tools/mpc_path/send_mpc_path.py --dry-run

    # 전방 2 m 직선, 0.10 m/s
    python3 Tools/mpc_path/send_mpc_path.py --distance 2.0 --speed 0.10

    # 좌로 굽는 호 (곡률 반경 5 m)
    python3 Tools/mpc_path/send_mpc_path.py --distance 2.0 --radius 5.0

종료코드 `0`=성공, `1`=액션 실패(status≠0), `2`=환경·사전조건 실패, `3`=여유 부족,
`4`=사용자 중단.
"""

from __future__ import annotations

import argparse
import math
import signal
import sys
import time

import numpy as np

# 라이다 배제영역(`dual_laser_merger/config/filter_config.yaml`) 때문에 전방 0.98 m
# 안쪽은 **관측되지 않는다**. 임계를 그 위로 잡아야 판정이 의미를 갖는다.
MIN_CLEARANCE_M = 1.5
SCAN_STALE_S = 0.5
POSE_STALE_S = 0.5


def trnav_wrap(a: float) -> float:
    return math.atan2(math.sin(a), math.cos(a))


def yaw_of(q) -> float:
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y ** 2 + q.z ** 2))


def main() -> int:
    ap = argparse.ArgumentParser(description="mpc 경로 생성·송신")
    ap.add_argument("--distance", type=float, default=2.0, help="경로 길이 [m]")
    ap.add_argument("--radius", type=float, default=0.0,
                    help="곡률 반경 [m] (0=직선, +좌선회 −우선회)")
    ap.add_argument("--points", type=int, default=21, help="waypoint 수 (>=2)")
    ap.add_argument("--speed", type=float, default=0.10, help="최대 선속도 [m/s]")
    ap.add_argument("--accel", type=float, default=0.05, help="가속도 [m/s^2]")
    ap.add_argument("--min-clearance", type=float, default=MIN_CLEARANCE_M,
                    help="진행방향 최소 여유 [m]")
    ap.add_argument("--pose-topic", default="/robot_pose")
    ap.add_argument("--reverse", action="store_true",
                    help="후진(mpc_reverse). 경로를 로봇 **뒤쪽**으로 만들고 pose 방향을 yaw+π 로 둔다 "
                         "— 서버가 effective_yaw = robot_yaw + π 로 보정한 뒤 Pure Pursuit 을 돌리므로 "
                         "경로 접선이 그 방향과 맞아야 validateInitialPose 를 통과한다.")
    ap.add_argument("--dry-run", action="store_true", help="계획만 출력하고 보내지 않는다")
    ap.add_argument("--timeout", type=float, default=180.0, help="결과 대기 상한 [s]")
    ap.add_argument("--freeze-sec", type=float, default=1.5, help="측위 값 정지 허용 [s]")
    ap.add_argument("--pose-stale", type=float, default=0.5, help="측위 두절 허용 [s]")
    ap.add_argument("--overrun", type=float, default=1.3, help="지령 대비 이동량 상한 배수")
    a = ap.parse_args()

    if a.points < 2:
        print("⚠ --points 는 2 이상이어야 한다(액션이 거부한다)", file=sys.stderr)
        return 2
    if a.distance <= 0 or a.speed <= 0 or a.accel <= 0:
        print("⚠ distance·speed·accel 은 모두 > 0 이어야 한다", file=sys.stderr)
        return 2

    import rclpy
    from geometry_msgs.msg import PoseStamped
    from nav_msgs.msg import Path
    from rclpy.action import ActionClient
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan
    from trnav_2ws_interfaces.action import AMRMotionMpc, AMRMotionMpcReverse

    rclpy.init()
    node = Node("send_mpc_path")
    st: dict = {"pose": None, "pose_at": 0.0, "moved_at": 0.0,
                "scan": None, "scan_at": 0.0}

    def on_pose(m):
        p = (m.pose.position.x, m.pose.position.y, yaw_of(m.pose.orientation))
        prev = st["pose"]
        now = time.time()
        # 값이 **변한** 시각을 따로 둔다 — stamp 나이는 「살아있음」을 뜻하지 않는다.
        if prev is None or math.hypot(p[0] - prev[0], p[1] - prev[1]) > 1e-4:
            st["moved_at"] = now
        st["pose"], st["pose_at"] = p, now

    node.create_subscription(PoseStamped, a.pose_topic, on_pose, 10)
    node.create_subscription(
        LaserScan, "/scan_merged",
        lambda m: (st.__setitem__("scan", m), st.__setitem__("scan_at", time.time())),
        qos_profile_sensor_data)

    def pump(sec: float) -> None:
        t = time.time()
        while time.time() - t < sec:
            rclpy.spin_once(node, timeout_sec=0.02)

    def clearance(direction_rad: float, half_deg: float = 30.0) -> float:
        """진행 방향 부채꼴 최소 거리. 스캔이 없거나 낡으면 **0.0**(fail-closed)."""
        sc = st["scan"]
        if sc is None or (time.time() - st["scan_at"]) > SCAN_STALE_S:
            return 0.0
        r = np.array(sc.ranges)
        ang = sc.angle_min + np.arange(len(r)) * sc.angle_increment
        ok = np.isfinite(r) & (r > sc.range_min) & (r < sc.range_max)
        d = np.abs((ang - direction_rad + math.pi) % (2 * math.pi) - math.pi)
        m = ok & (d < math.radians(half_deg))
        return float(np.min(r[m])) if m.any() else 0.0

    pump(3.0)
    if st["pose"] is None:
        print(f"⚠ {a.pose_topic} 미수신 — 측위 발행자를 확인하라", file=sys.stderr)
        return 2
    if st["scan"] is None:
        print("⚠ /scan_merged 미수신 — 라이다를 확인하라", file=sys.stderr)
        return 2

    x0, y0, th0_raw = st["pose"]
    # 후진은 서버가 robot_yaw + π 로 보정하므로 경로도 그 방향으로 만든다.
    th0 = trnav_wrap(th0_raw + math.pi) if a.reverse else th0_raw
    travel_dir = math.pi if a.reverse else 0.0     # 여유를 볼 차체 기준 방향

    # ── 경로 생성: 현재 자세에서 시작하는 직선 또는 정곡률 호 ──
    poses = []
    for i in range(a.points):
        s = a.distance * i / (a.points - 1)
        if abs(a.radius) < 1e-6:
            dx, dy, dth = s, 0.0, 0.0
        else:
            k = 1.0 / a.radius
            dth = k * s
            dx = math.sin(dth) / k
            dy = (1.0 - math.cos(dth)) / k
        poses.append((x0 + dx * math.cos(th0) - dy * math.sin(th0),
                      y0 + dx * math.sin(th0) + dy * math.cos(th0),
                      th0 + dth))

    xe, ye, the = poses[-1]
    clr = clearance(travel_dir)
    print(f"현재 자세 : ({x0:+.4f}, {y0:+.4f}) yaw {math.degrees(th0_raw):+.2f}°"
          + (f"  (경로 기준 {math.degrees(th0):+.2f}° = yaw+180°)" if a.reverse else ""))
    print(f"방향      : {'후진(mpc_reverse)' if a.reverse else '전진(mpc)'}")
    print(f"경로      : {'직선' if abs(a.radius) < 1e-6 else f'호 R={a.radius:+.1f} m'} "
          f"· 길이 {a.distance:.2f} m · waypoint {a.points}")
    print(f"종점      : ({xe:+.4f}, {ye:+.4f}) yaw {math.degrees(the):+.2f}°")
    print(f"속도      : 최대 {a.speed:.3f} m/s · 가속 {a.accel:.3f} m/s²")
    print(f"{'후방' if a.reverse else '전방'} 여유 : {clr:.3f} m (임계 {a.min_clearance:.2f} m)")

    if clr < a.min_clearance:
        print(f"⚠ 여유 부족 — 보내지 않는다", file=sys.stderr)
        return 3
    if a.dry_run:
        print("[dry-run] 보내지 않음")
        return 0

    act_type = AMRMotionMpcReverse if a.reverse else AMRMotionMpc
    act_name = "/amr_motion_mpc_reverse_abstract" if a.reverse else "/amr_motion_mpc_abstract"
    cl = ActionClient(node, act_type, act_name)
    if not cl.wait_for_server(timeout_sec=15.0):
        print(f"⚠ {act_name} 서버 없음", file=sys.stderr)
        return 2

    path = Path()
    path.header.frame_id = "map"          # 액션이 'map' 이 아니면 거부한다
    path.header.stamp = node.get_clock().now().to_msg()
    for px, py, pth in poses:
        p = PoseStamped()
        p.header.frame_id = "map"
        p.pose.position.x, p.pose.position.y = px, py
        p.pose.orientation.z = math.sin(pth / 2.0)
        p.pose.orientation.w = math.cos(pth / 2.0)
        path.poses.append(p)

    g = act_type.Goal()
    g.path = path
    g.max_linear_speed = a.speed
    g.acceleration = a.accel
    g.hold_steer = False
    g.exit_steer_angle = 0.0
    g.exit_speed = 0.0
    g.entry_speed = 0.0
    g.has_next = False
    g.control_mode = 0
    g.enable_localization_watchdog = True

    gh_box: dict = {"gh": None}

    def cancel_and_exit(signum, frame):
        gh = gh_box.get("gh")
        if gh is not None:
            try:
                gh.cancel_goal_async()
            except Exception:
                pass
        raise KeyboardInterrupt(f"signal {signum}")

    # SIGTERM(kill)·SIGHUP(ssh 끊김)에서도 취소가 나가게 한다. SIGKILL 은 막을 수 없다.
    for sg in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sg, cancel_and_exit)

    rc = 0
    try:
        fb_last = {"t": 0.0}

        def on_fb(msg):
            f = msg.feedback
            if time.time() - fb_last["t"] < 0.5:
                return
            fb_last["t"] = time.time()
            print(f"  진행 {f.current_distance:5.2f} m · 횡오차 {f.current_lateral_error:+.3f} m "
                  f"· 헤딩오차 {f.current_heading_error:+5.1f}° · vx {f.current_vx:+.3f} m/s")

        gf = cl.send_goal_async(g, feedback_callback=on_fb)
        rclpy.spin_until_future_complete(node, gf, timeout_sec=20.0)
        gh = gf.result()
        if gh is None or not gh.accepted:
            print("⚠ 목표가 거부됐다 — 서버 로그를 확인하라", file=sys.stderr)
            return 1
        gh_box["gh"] = gh
        print("목표 접수 — 주행 시작")

        rf = gh.get_result_async()
        t0 = time.time()
        st["moved_at"] = time.time()
        stop_why = None
        x0, y0, _ = st["pose"]
        while not rf.done() and time.time() - t0 < a.timeout:
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.time()
            x, y, _th = st["pose"]
            d = math.hypot(x - x0, y - y0)
            # ⚠ 액션 자기보고를 감시로 쓰지 않는다 — 그 보고의 입력이 고장나면 보고도
            #   같이 고장난다(진행 0 으로 보고하며 개루프 주행). 독립 관측으로만 판정한다.
            if now - st["pose_at"] > a.pose_stale:
                stop_why = f"측위 메시지 {a.pose_stale}s 두절"
            elif now - st["moved_at"] > a.freeze_sec:
                stop_why = (f"측위 **값**이 {a.freeze_sec}s 동안 변하지 않음 — "
                            f"얼어붙은 자세로 개루프 주행 의심")
            elif clearance(travel_dir) < a.min_clearance:
                stop_why = (f"{'후방' if a.reverse else '전방'} 여유 "
                            f"{clearance(travel_dir):.2f} m < {a.min_clearance:.2f} m")
            elif d > a.distance * a.overrun:
                stop_why = f"이동 {d:.2f} m 가 지령 {a.distance:.2f} m 의 {a.overrun}배 초과"
            if stop_why:
                print(f"\n⚠ 감시 발동 — 취소: {stop_why}", file=sys.stderr)
                gh.cancel_goal_async()
                pump(4.0)
                return 5
        if not rf.done():
            print("⚠ 결과 시한 초과 — 취소 요청", file=sys.stderr)
            gh.cancel_goal_async()
            pump(3.0)
            return 1

        res = rf.result().result
        print(f"\n결과      : status {res.status}")
        print(f"  주행거리 {res.actual_distance:.3f} m (지령 {a.distance:.3f})")
        print(f"  최종 횡오차 {res.final_lateral_error:+.4f} m · "
              f"헤딩오차 {res.final_heading_error:+.2f}°")
        xf, yf, _ = st["pose"]
        print(f"  실제 이동(측위) {math.hypot(xf-x0, yf-y0):.3f} m ← 액션보고와 대조할 것")
        print(f"  소요 {res.elapsed_time:.2f} s")
        rc = 0 if res.status == 0 else 1
    except KeyboardInterrupt:
        print("\n중단 — 취소 요청을 보냈다", file=sys.stderr)
        pump(3.0)
        rc = 4
    finally:
        try:
            node.destroy_node()
            rclpy.shutdown()
        except Exception:
            pass
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
