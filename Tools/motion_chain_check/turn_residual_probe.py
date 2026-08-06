#!/usr/bin/env python3
"""turn 잔여각 바닥값 측정 — Phase 3.5(미세보정) 존치 판단용 **진단 도구**.

`fine_correction_threshold_deg: 0.3` 이 달성 가능한 값인지 실행으로 확인한다.
현행 SIL 플랜트는 기본이 즉응(관성 없음)이라 이 질문에 답할 수 없다 —
`drive_decel_mps2` 를 실기 유래값으로 켠 상태와 끈 상태를 **같은 목표로 비교**한다.

측정값:
  · `actual_angle` — 액션이 보고한 달성각. 목표와의 차가 **액션이 자기 기준으로 남긴 오차**
  · `elapsed_time` — Phase 3.5 가 타임아웃(3.0 s)까지 도는지 판별. 보정이 수렴하면 짧다
  · IMU 지상진값 yaw — 액션 보고와 **독립적인** 실제 회전량. 둘의 차 = 액션 측정 오차

⚠ 본 도구는 진단만 한다. 임계값 변경·Phase 3.5 제거 같은 처방은 **하지 않는다**.

사용 (플랜트·액션은 sil_turn.launch.py 로 미리 띄운다):
    ros2 launch trnav_2ws_action_server sil_turn.launch.py                       # 즉응
    ros2 launch trnav_2ws_action_server sil_turn.launch.py \
        drive_accel:=0.0833 drive_decel:=0.0833 steer_rate:=57.1                 # 동특성

    python3 Tools/motion_chain_check/turn_residual_probe.py --runs 3 --angle 45 --radius 1.0
"""

from __future__ import annotations

import argparse
import math
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="turn 잔여각 바닥값 측정")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--angle", type=float, default=45.0)
    ap.add_argument("--radius", type=float, default=1.0)
    ap.add_argument("--speed", type=float, default=0.15)
    ap.add_argument("--label", default="")
    a = ap.parse_args()

    import rclpy
    from rclpy.action import ActionClient
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Imu
    from trnav_2ws_interfaces.action import AMRMotionTurn

    rclpy.init()
    node = Node("turn_residual_probe")
    client = ActionClient(node, AMRMotionTurn, "/amr_motion_turn_abstract")

    yaw = {"v": None}

    def on_imu(m: Imu) -> None:
        q = m.orientation
        yaw["v"] = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                              1.0 - 2.0 * (q.y * q.y + q.z * q.z))

    node.create_subscription(Imu, "/imu/data", on_imu, qos_profile_sensor_data)

    if not client.wait_for_server(timeout_sec=15.0):
        print("액션 서버 없음 — sil_turn.launch.py 를 먼저 띄우세요", file=sys.stderr)
        return 2

    # IMU 첫 수신 대기
    for _ in range(200):
        rclpy.spin_once(node, timeout_sec=0.05)
        if yaw["v"] is not None:
            break
    if yaw["v"] is None:
        print("/imu/data 미수신", file=sys.stderr)
        return 2

    rows = []
    for i in range(a.runs):
        yaw_before = yaw["v"]

        goal = AMRMotionTurn.Goal()
        goal.target_angle = float(a.angle)
        goal.turn_radius = float(a.radius)
        goal.max_linear_speed = float(a.speed)
        goal.accel_angle = 10.0
        goal.hold_steer = False
        goal.exit_steer_angle = 0.0

        fut = client.send_goal_async(goal)
        rclpy.spin_until_future_complete(node, fut)
        gh = fut.result()
        if gh is None or not gh.accepted:
            print(f"run {i+1}: 목표 거부", file=sys.stderr)
            continue
        rfut = gh.get_result_async()
        rclpy.spin_until_future_complete(node, rfut)
        res = rfut.result().result

        # 관성이 끝날 때까지 조금 더 돌려 지상진값을 안정시킨다
        for _ in range(60):
            rclpy.spin_once(node, timeout_sec=0.05)

        d = math.degrees(yaw["v"] - yaw_before)
        while d > 180.0:
            d -= 360.0
        while d < -180.0:
            d += 360.0

        rows.append({
            "run": i + 1,
            "status": res.status,
            "reported": res.actual_angle,
            "truth": d,
            "elapsed": res.elapsed_time,
        })

    node.destroy_node()
    rclpy.shutdown()

    if not rows:
        return 1

    tag = f" [{a.label}]" if a.label else ""
    print(f"=== turn 잔여각{tag} — 목표 {a.angle}° · R={a.radius} m · {a.runs}회 ===\n")
    print("  run  status  액션보고각    지상진값     보고오차    실제오차   측정오차   소요")
    print("  " + "-" * 76)
    for r in rows:
        rep_err = r["reported"] - a.angle
        tru_err = r["truth"] - a.angle
        meas_err = r["reported"] - r["truth"]
        print(f"  {r['run']:>3}  {r['status']:>6}  {r['reported']:>9.3f}°  {r['truth']:>9.3f}°  "
              f"{rep_err:>+8.3f}°  {tru_err:>+8.3f}°  {meas_err:>+8.3f}°  {r['elapsed']:>5.2f}s")

    rep = [r["reported"] - a.angle for r in rows]
    tru = [r["truth"] - a.angle for r in rows]
    mea = [r["reported"] - r["truth"] for r in rows]
    ela = [r["elapsed"] for r in rows]

    def stat(xs):
        m = sum(xs) / len(xs)
        sd = (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5
        return m, sd, max(abs(x) for x in xs)

    print()
    for name, xs in (("보고오차(액션 자기기준)", rep), ("실제오차(IMU 지상진값)", tru),
                     ("측정오차(보고−지상진값)", mea)):
        m, sd, mx = stat(xs)
        print(f"  {name:<26} 평균 {m:+.3f}°  σ {sd:.3f}°  |최대| {mx:.3f}°")
    print(f"  {'소요':<26} 평균 {sum(ela)/len(ela):.2f}s  최대 {max(ela):.2f}s")

    print()
    print("  판정 재료 — 처방은 하지 않는다:")
    _, _, tru_max = stat(tru)
    print(f"    · 임계 0.3° 대비 실제오차 |최대| = {tru_max:.3f}°  "
          f"({'임계 안' if tru_max <= 0.3 else '**임계 초과** — 0.3° 는 이 조건에서 달성 불가'})")
    long_runs = sum(1 for e in ela if e > 9.0)
    print(f"    · 소요 9초 초과 {long_runs}/{len(ela)}회  "
          f"(Phase 3.5 타임아웃 3.0s 를 태웠는지의 간접 지표)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
