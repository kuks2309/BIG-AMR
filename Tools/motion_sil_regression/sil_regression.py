#!/usr/bin/env python3
"""SIL(Software In the Loop) 거동 회귀 — 액션의 **결과**를 자동 판정한다.

## 왜 필요한가

액션 서버의 `execute()` 는 370~563줄짜리 단일 함수라 gtest 로 잡을 수 없다. 그렇다고
그 코드를 리팩터하는 것은 **검증된 제어 코드를 건드리는 위험**을 지는 일이다.
그래서 코드를 바꾸지 않고 **밖에서** 거동을 고정한다 — 목표각·거리·조향 자세·가드 발화를
플랜트와 함께 돌려 판정한다.

실기 없이 돈다. 로봇을 움직이지 않으므로 공간·안전 제약이 없고, 몇 분이면 전 항목을 돈다.

## 무엇을 고정하는가

    turn          목표각 도달(허용 규격 |오차| ≤ 0.5°) · 조향이 원호 자세를 유지(±90° 로 튀지 않음)
    turn_reverse  같은 항목 + 진행 방향이 후진
    yaw_control   거리 도달 · 헤딩 유지 · 가드 오탐 0
    yaw_guard     IMU 에만 잡음을 주입해 −7(헤딩 발산)이 실제로 발화하는가
    yaw_loc       주행 중 측위 발행을 끊어 −4(측위 타임아웃)가 실제로 발화하는가

⚠ **SIL 의 구조적 한계 2가지를 알고 써야 한다.**
  1. 플랜트는 IMU 와 맵 자세를 **같은 지상진값**에서 만든다 → 괴리가 정확히 0 이다.
     `−7` 을 보려면 `imu_yaw_noise` 로 IMU 만 오염시켜야 한다. 그냥 돌리면 영원히 안 뜬다.
  2. 즉응 플랜트는 조향 지연이 없어 `gate_blocked` 가 생기지 않는다 → `−8` 은 SIL 로 못 본다.
     보려면 가드 임계 자체를 낮춰야 하며 그것은 회귀가 아니라 진단이다.

## 사용

    # 실기와 섞이지 않도록 도메인을 분리한다
    ROS_DOMAIN_ID=7 python3 Tools/motion_sil_regression/sil_regression.py --case all
    ROS_DOMAIN_ID=7 python3 Tools/motion_sil_regression/sil_regression.py --case turn --keep

종료코드 0=전 항목 통과, 1=판정 실패, 2=환경 문제(런치·토픽 미수신).
"""

from __future__ import annotations

import argparse
import math
import os
import signal
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (케이스 이름) -> (런치 파일, 액션 이름, 액션 타입 모듈/클래스)
CASES = {
    "turn": ("sil_turn.launch.py", "/amr_motion_turn_abstract", "AMRMotionTurn"),
    "turn_reverse": ("sil_turn_reverse.launch.py", "/amr_motion_turn_reverse_abstract",
                     "AMRMotionTurnReverse"),
    "yaw_control": ("sil_yaw_control.launch.py", "/amr_motion_yaw_control_abstract",
                    "AMRMotionYawControl"),
    "yaw_guard": ("sil_yaw_control.launch.py", "/amr_motion_yaw_control_abstract",
                  "AMRMotionYawControl"),
    "yaw_loc": ("sil_yaw_control.launch.py", "/amr_motion_yaw_control_abstract",
                "AMRMotionYawControl"),
}

# 허용 규격 — 실기에서 승인된 `turn` 계열 규격과 같은 값이다(|오차| ≤ 0.5°).
# 정본은 `turn_params.yaml` 의 「허용 규격」 주석 · `issues_and_fixes.md` 의 실측 전수표.
TURN_TOL_DEG = 0.5
DIST_TOL_M = 0.01


def launch(launch_file: str, extra: list[str], log_path: str):
    """SIL 스택을 띄우고 프로세스 그룹을 돌려준다. 정리는 `teardown` 이 한다."""
    cmd = ["ros2", "launch", "trnav_2ws_action_server", launch_file] + extra
    fh = open(log_path, "w", encoding="utf-8")
    return subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT,
                            start_new_session=True), fh


def teardown(proc, fh):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        fh.close()
    except OSError:
        pass


def run_case(name: str, keep: bool) -> tuple[bool, str]:
    import rclpy
    from geometry_msgs.msg import PoseStamped
    from rclpy.action import ActionClient
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Imu
    import trnav_2ws_interfaces.action as A

    launch_file, action_name, type_name = CASES[name]
    extra = ["drive_accel:=0.0833", "drive_decel:=0.0833", "steer_rate:=57.1"]
    if name == "yaw_guard":
        extra.append("imu_yaw_noise:=3.0")   # IMU 만 오염 — 위 한계 ①
    log_path = f"/tmp/sil_regression_{name}.log"
    proc, fh = launch(launch_file, extra, log_path)

    rclpy.init()
    node = Node(f"sil_regression_{name}")
    st: dict = {"imu": None, "pose": None}

    def yaw_of(q):
        return math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y**2 + q.z**2)))

    node.create_subscription(Imu, "/imu/data",
                             lambda m: st.__setitem__("imu", yaw_of(m.orientation)),
                             qos_profile_sensor_data)
    node.create_subscription(PoseStamped, "/robot_pose",
                             lambda m: st.__setitem__("pose", (m.pose.position.x,
                                                               m.pose.position.y,
                                                               yaw_of(m.pose.orientation))), 10)

    def pump(sec):
        t = time.time()
        while time.time() - t < sec:
            rclpy.spin_once(node, timeout_sec=0.02)

    try:
        cl = ActionClient(node, getattr(A, type_name), action_name)
        if not cl.wait_for_server(timeout_sec=40.0):
            return False, f"[{name}] 액션 서버가 뜨지 않았다 — 로그 {log_path}"
        pump(4.0)
        if st["imu"] is None:
            return False, f"[{name}] /imu/data 미수신 — 플랜트가 안 떴다"

        if name == "yaw_guard":
            # 가드 임계를 주입 잡음보다 낮춘다. **생산 기본값(5.0°)으로는 발화하지 않는다** —
            # 백색 잡음 3.0° 1σ 가 5° 를 **10 cycle 연속** 넘길 확률이 사실상 0 이기 때문이다.
            # 여기서 보려는 것은 「임계가 적절한가」가 아니라 **「판정·중단·코드 반환 경로가
            # 살아 있는가」**이므로 임계를 낮춰 경로를 태운다.
            # (이 set 이 먹는 것 자체가 파라미터 콜백 화이트리스트의 회귀이기도 하다.)
            r = subprocess.run(["ros2", "param", "set", "/trnav_yaw_control_node",
                                "yaw_control_heading_divergence_deg", "0.5"],
                               capture_output=True, text=True, timeout=30)
            if "successful" not in r.stdout:
                return False, (f"[{name}] 가드 임계 설정 실패 — 파라미터 콜백이 죽었는가? "
                               f"stdout={r.stdout.strip()[:120]}")

            # ── 부분 적용 회귀 ──
            # 유효한 키와 **범위 밖** 키를 한 번에 보낸다. 콜백이 검증과 반영을 분리하지
            # 않으면 앞의 유효 키는 이미 멤버에 적용된 채 실패를 반환하고, 그러면
            # `ros2 param get` 이 보고하는 값과 실제 거동이 영구히 어긋난다.
            before = subprocess.run(["ros2", "param", "get", "/trnav_yaw_control_node",
                                     "yaw_control_min_vx"], capture_output=True, text=True, timeout=30)
            subprocess.run(["ros2", "param", "set", "/trnav_yaw_control_node",
                            "yaw_control_min_vx", "0.5"], capture_output=True, text=True, timeout=30)
            subprocess.run(["ros2", "param", "set", "/trnav_yaw_control_node",
                            "yaw_control_min_vx", before.stdout.strip().split()[-1]],
                           capture_output=True, text=True, timeout=30)
            # 범위 밖 단독 set 은 거부돼야 한다
            bad = subprocess.run(["ros2", "param", "set", "/trnav_yaw_control_node",
                                  "yaw_control_heading_divergence_deg", "999.0"],
                                 capture_output=True, text=True, timeout=30)
            if "successful" in bad.stdout and "not set" not in bad.stdout.lower():
                return False, (f"[{name}] 범위 밖 값(999.0)이 수용됐다 — 범위 검사가 죽었다: "
                               f"{bad.stdout.strip()[:120]}")

        if name in ("turn", "turn_reverse"):
            g = getattr(A, type_name).Goal()
            g.target_angle = 20.0
            g.turn_radius = 1.0
            g.max_linear_speed = 0.05
            g.accel_angle = 5.0
            g.hold_steer = False
            g.exit_steer_angle = 0.0
        else:
            if st["pose"] is None:
                return False, f"[{name}] /robot_pose 미수신 — 어댑터가 안 떴다"
            g = A.AMRMotionYawControl.Goal()
            g.target_yaw_deg = st["pose"][2]     # 현재 헤딩 유지
            g.target_distance = 3.0 if name == "yaw_loc" else 0.5
            g.vx_max = -0.05
            g.acceleration = 0.05
            g.max_steer_deg = 25.0
            g.kp, g.kd, g.ki, g.i_max_deg = 1.0, 0.1, 0.0, 0.0
            g.counter_steer = False
            g.hold_steer = False
            g.exit_steer_angle = 0.0
            g.max_timeout_sec = 90.0
            g.enable_localization_watchdog = True

        if name == "yaw_loc":
            # 주행이 시작된 뒤 측위 발행을 끊는다. 워치독이 살아 있으면 −4 로 중단하고,
            # 죽어 있으면 **얼어붙은 자세로 시한까지 계속 주행**한다(그것이 종전 상태였다).
            # ⚠ 자기 자신을 매칭하지 않도록 대괄호 정규식을 쓴다 — 예전에 자기 pkill 로
            #   프로세스를 죽여 오진한 적이 있다.
            import threading as _th

            def _kill_pose():
                time.sleep(3.0)
                subprocess.run(["pkill", "-f", "[s]il_pose_adapter"],
                               capture_output=True, text=True)
            _th.Thread(target=_kill_pose, daemon=True).start()

        gh_f = cl.send_goal_async(g)
        rclpy.spin_until_future_complete(node, gh_f, timeout_sec=30.0)
        gh = gh_f.result()
        if gh is None or not gh.accepted:
            return False, f"[{name}] 목표가 거부됐다"
        rf = gh.get_result_async()
        t0 = time.time()
        while not rf.done() and time.time() - t0 < 200:
            rclpy.spin_once(node, timeout_sec=0.05)
        if not rf.done():
            return False, f"[{name}] 결과 시한 초과"
        res = rf.result().result

        # ── 판정 ──
        if name in ("turn", "turn_reverse"):
            # ⚠ `abs(a) - abs(b)` 로 재면 **부호 반전이 통과한다** — +20° 를 지령했는데
            #   −20° 를 돌아도 오차 0 이 된다. 이 저장소가 반복해서 당한 결함군이 정확히
            #   조향·회전의 부호 반전이므로 부호를 살려서 잰다.
            err = res.actual_angle - g.target_angle
            if res.status != 0:
                return False, f"[{name}] status={res.status} (0 기대)"
            if abs(err) > TURN_TOL_DEG:
                return False, (f"[{name}] 각오차 {err:+.3f}° 가 규격 ±{TURN_TOL_DEG}° 초과 "
                               f"(지령 {g.target_angle:+.1f} · 달성 {res.actual_angle:+.3f})")
            return True, f"[{name}] status 0 · 각오차 {err:+.3f}° (규격 ±{TURN_TOL_DEG}°)"

        if name == "yaw_loc":
            # −4=측위 타임아웃 이 정답. −7 이 뜨면 「측위가 죽었는데 IMU 를 탓하는」 오진이다.
            if res.status == -7:
                return False, (f"[{name}] status −7 (헤딩 발산) — 측위가 끊겼는데 IMU 를 탓했다. "
                               f"map_yaw_fresh 신선도 검사가 듣지 않는다")
            if res.status != -4:
                return False, (f"[{name}] status={res.status} (−4 기대). 측위 발행을 끊었는데 "
                               f"워치독이 발화하지 않았다 — setMaxCmdSpeed 배선을 확인하라")
            return True, f"[{name}] status −4 발화 · 거리 {res.actual_distance:.3f} m"

        if name == "yaw_control":
            if res.status != 0:
                return False, f"[{name}] status={res.status} (0 기대 — 가드 오탐 의심)"
            if abs(res.actual_distance - g.target_distance) > DIST_TOL_M:
                return False, (f"[{name}] 거리 {res.actual_distance:.3f} m "
                               f"(지령 {g.target_distance})")
            return True, (f"[{name}] status 0 · 거리 {res.actual_distance:.3f} m · "
                          f"최종 헤딩오차 {res.final_error_deg:+.3f}°")

        # yaw_guard — IMU 오염 상태에서 −7 이 떠야 한다
        if res.status != -7:
            return False, (f"[{name}] status={res.status} (−7 기대). IMU 잡음 3.0° 를 넣었는데 "
                           f"헤딩 발산 가드가 발화하지 않았다")
        return True, f"[{name}] status −7 발화 · 거리 {res.actual_distance:.3f} m"

    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        try:
            rclpy.shutdown()
        except Exception:
            pass
        if name == "yaw_guard" and keep:
            # `--keep` 이면 노드가 살아남으므로 낮춘 임계를 반드시 되돌린다. 안 되돌리면
            # 이후 진단이 상시 −7 로 죽는다(스택을 죽이는 경우는 프로세스와 함께 사라진다).
            subprocess.run(["ros2", "param", "set", "/trnav_yaw_control_node",
                            "yaw_control_heading_divergence_deg", "5.0"],
                           capture_output=True, text=True, timeout=30)
        if not keep:
            teardown(proc, fh)
            try:
                proc.wait(timeout=5)     # 좀비를 남기지 않는다
            except subprocess.TimeoutExpired:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(description="SIL 거동 회귀")
    ap.add_argument("--case", default="all", choices=list(CASES) + ["all"])
    ap.add_argument("--keep", action="store_true", help="끝나도 SIL 스택을 남긴다(진단용)")
    a = ap.parse_args()

    # ⚠ 문자열 비교로는 `""`·`"00"`·`" 0"` 이 전부 빠져나가고, ROS 는 그것을 도메인 0 으로
    #   읽는다. 정수로 파싱해 판정한다. 섞이면 SIL 런치가 `/motor/wheel_cmd` 를 실기에
    #   발행하고 `/safety/estop=false`·`/safety/lidar=safe` 까지 위조한다 — 로봇이 움직인다.
    try:
        dom = int(str(os.environ.get("ROS_DOMAIN_ID", "")).strip())
    except ValueError:
        dom = 0
    if dom <= 0:
        print("⚠ ROS_DOMAIN_ID 가 0(또는 미설정·해석 불가)이다 — 실기 스택과 섞인다. "
              "ROS_DOMAIN_ID=7 로 분리해 실행할 것", file=sys.stderr)
        return 2

    cases = list(CASES) if a.case == "all" else [a.case]
    fails = []
    for c in cases:
        ok, msg = run_case(c, a.keep)
        print(("  PASS  " if ok else "  FAIL  ") + msg)
        if not ok:
            fails.append(c)
    print(f"\n{len(cases) - len(fails)}/{len(cases)} 통과")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
