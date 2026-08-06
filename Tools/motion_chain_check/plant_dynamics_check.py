#!/usr/bin/env python3
"""SIL 플랜트(`translate_sim_odom`) 동특성·엔코더 **실행 검증**.

두 가지를 실제로 돌려 증명한다 — 코드를 읽고 주장하지 않는다.

  A. **QD 회귀 없음** — 동특성 파라미터를 안 주면(기본 0) 플랜트는 종전과 같이
     지령을 즉시 따른다. 이 노드는 SIL·HIL 런치 19개가 공유하고 그중 8개가
     **검증 완료된 QD 런치**라, 기본 거동이 바뀌면 그 검증이 말없이 무효가 된다.

  B. **켜면 관성이 보인다** — `drive_decel_mps2` 를 주면 지령을 0 으로 끊어도
     바퀴가 계속 구르고, 그 이동이 **엔코더에 쌓인다**. 종전 플랜트는 지령을
     되울리기만 해서(cmd echo) 이 구간이 원리적으로 재현되지 않았고, 그래서
     상위 액션의 「정착 대기 후 잔여각 측정」이 SIL 에서 검증 불가였다.

기준값 출처:
  · 감속 0.0833 m/s² — 실측 50 mm/s 에서 정지까지 0.57~0.65 s
    (docs/verified_facts/2026-08-04-amr-test-gui-field-run.md:80-88) 에서 역산.
  · 엔코더 환산 — translator YAML 과 동일 (pulses_per_rev 65536 · gear_walk 32 · r 0.125).

사용:
    python3 Tools/motion_chain_check/plant_dynamics_check.py            # A·B 모두
    python3 Tools/motion_chain_check/plant_dynamics_check.py --selftest # 계산식만
"""

from __future__ import annotations

import argparse
import math
import os
import signal
import subprocess
import sys
import time

WHEEL_R = 0.125
PPR = 65536.0
GEAR_WALK = 32.0
COUNTS_PER_M = PPR * GEAR_WALK / (2.0 * math.pi * WHEEL_R)

CRUISE_MPS = 0.050          # 실측이 이뤄진 동작점
DECEL_MPS2 = 0.0833
EXPECT_COAST_S = CRUISE_MPS / DECEL_MPS2            # 0.600 s
EXPECT_COAST_M = CRUISE_MPS ** 2 / (2 * DECEL_MPS2)  # 0.0150 m

DOMAIN = "43"               # 다른 세션·실기와 격리


def _env() -> dict:
    e = dict(os.environ)
    e["ROS_DOMAIN_ID"] = DOMAIN
    return e


def run_case(label: str, params: list) -> dict:
    """플랜트를 띄우고 정속→정지를 지령한 뒤 관성 구간을 잰다."""
    cmd = ["ros2", "run", "translate_sim_odom", "translate_sim_odom_node",
           "--ros-args", "-p", "w1_x:=0.6039", "-p", "w1_y:=0.0",
           "-p", "w2_x:=-0.5961", "-p", "w2_y:=0.0"]
    for p in params:
        cmd += ["-p", p]

    proc = subprocess.Popen(cmd, env=_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            preexec_fn=os.setsid)
    try:
        time.sleep(3.0)   # 노드 기동 대기
        return _drive_and_measure(label)
    finally:
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)


def _drive_and_measure(label: str) -> dict:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from trnav_msgs.msg import WheelMotor, WheelMotorState, WheelSet, WheelSetArray

    rclpy.init()
    node = Node("plant_dynamics_probe")
    pub = node.create_publisher(WheelSetArray, "/motor/wheel_cmd",
                                QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE))
    samples = []      # (t, velocity_front)
    encoders = []     # (t, encoder_walk_front)
    node.create_subscription(WheelMotor, "/wheel_motor_state",
                             lambda m: samples.append((time.monotonic(), m.velocity_front)), 10)
    node.create_subscription(WheelMotorState, "/wheel_motor_state_detailed",
                             lambda m: encoders.append((time.monotonic(), m.encoder_walk_front)), 10)

    def send(v: float) -> None:
        msg = WheelSetArray()
        msg.wheels = [WheelSet(velocity=v, steering=0.0), WheelSet(velocity=v, steering=0.0)]
        pub.publish(msg)

    # ── 정속 구간 ── 동특성이 켜져 있으면 가속에도 시간이 걸리므로 넉넉히 준다.
    t_end = time.monotonic() + 3.0
    while time.monotonic() < t_end:
        send(CRUISE_MPS)
        rclpy.spin_once(node, timeout_sec=0.02)

    v_at_stop_cmd = samples[-1][1] if samples else 0.0
    enc_at_stop_cmd = encoders[-1][1] if encoders else 0
    t_stop_cmd = time.monotonic()

    # ── 정지 지령 ── 이후 실제로 멈출 때까지를 잰다.
    t_end = t_stop_cmd + 3.0
    while time.monotonic() < t_end:
        send(0.0)
        rclpy.spin_once(node, timeout_sec=0.02)

    node.destroy_node()
    rclpy.shutdown()

    coast_s = None
    for t, v in samples:
        if t > t_stop_cmd and abs(v) < 1e-9:
            coast_s = t - t_stop_cmd
            break
    enc_final = encoders[-1][1] if encoders else 0
    coast_counts = enc_final - enc_at_stop_cmd

    # 감속 구간에 **중간 속도값**이 몇 개 있었나.
    # 즉응 플랜트는 지령을 그대로 되울리므로 0.05 와 0 뿐 — 그 사이 값이 나올 수 없다.
    # 동특성 플랜트는 램프를 타므로 중간값이 다수 나온다. 「관성 거리」로 판정하면
    # 적분 한 틱(50Hz 에서 v·0.02 = 1.0 mm)에 걸려 오판하므로 이 지표를 쓴다.
    mid = [v for t, v in samples if t > t_stop_cmd and 1e-9 < abs(v) < CRUISE_MPS - 1e-9]

    return {
        "label": label,
        "v_at_stop_cmd": v_at_stop_cmd,
        "coast_s": coast_s,
        "coast_counts": coast_counts,
        "coast_m": coast_counts / COUNTS_PER_M,
        "encoder_seen": len(encoders) > 0,
        "intermediate": len(mid),
    }


def report() -> int:
    print(f"=== 플랜트 동특성·엔코더 실행 검증 (ROS_DOMAIN_ID={DOMAIN}) ===\n")

    a = run_case("A 즉응(기본값 — QD 검증 런치가 쓰는 모드)", [])
    b = run_case("B 동특성 활성", [f"drive_accel_mps2:={DECEL_MPS2}", f"drive_decel_mps2:={DECEL_MPS2}",
                                   "steer_rate_dps:=57.1"])

    for r in (a, b):
        print(f"[{r['label']}]")
        print(f"  정지 지령 시점 실속도   {r['v_at_stop_cmd']:.4f} m/s")
        print(f"  정지까지 소요           {('%.3f s' % r['coast_s']) if r['coast_s'] is not None else '3초 내 미정지'}")
        print(f"  관성 구간 엔코더 증가   {r['coast_counts']:,} counts = {r['coast_m']*1000:.1f} mm")
        print(f"  감속 중 중간 속도값     {r['intermediate']} 개")
        print(f"  엔코더 토픽 수신        {'예' if r['encoder_seen'] else '아니오'}")
        print()

    bad = 0

    def check(name: str, ok: bool, detail: str) -> None:
        nonlocal bad
        print(f"[{'PASS' if ok else 'FAIL'}] {name} — {detail}")
        if not ok:
            bad += 1

    # A — 기본값에서는 종전과 같이 즉시 멈춰야 한다 (QD 검증 보존).
    #   판정은 **중간 속도값 0 개** — 지령을 되울리는 것 외에 아무 일도 하지 않았다는 뜻.
    #   (「관성 거리 0」으로 재면 적분 한 틱 1.0 mm 에 걸린다. 그 1 틱은 종전 플랜트에도
    #    있던 이산화이지 이번 변경이 만든 것이 아니다.)
    check("A 기본값은 즉응", a["coast_s"] is not None and a["coast_s"] < 0.15,
          f"정지까지 {a['coast_s']:.3f}s (제어주기 1~2틱 이내여야 함)")
    check("A 감속 램프 없음(지령 되울림 그대로)", a["intermediate"] == 0,
          f"중간 속도값 {a['intermediate']}개")

    # B — 켜면 실측 역산값(0.600 s / 15.0 mm) 근처가 나와야 한다
    ok_t = b["coast_s"] is not None and abs(b["coast_s"] - EXPECT_COAST_S) < 0.15
    check("B 관성 시간이 실측 역산과 일치", ok_t,
          f"관측 {b['coast_s']}s vs 기대 {EXPECT_COAST_S:.3f}s")
    ok_d = abs(b["coast_m"] - EXPECT_COAST_M) < 0.004
    check("B 관성 거리가 엔코더에 쌓임", ok_d,
          f"관측 {b['coast_m']*1000:.1f} mm vs 기대 {EXPECT_COAST_M*1000:.1f} mm")
    check("B 는 감속 램프를 탄다", b["intermediate"] >= 10,
          f"중간 속도값 {b['intermediate']}개 (A 는 {a['intermediate']}개)")

    # 엔코더는 양쪽 모두에서 나와야 한다 (토픽 추가는 거동 변경이 아니다)
    check("엔코더 토픽은 두 모드 모두 발행", a["encoder_seen"] and b["encoder_seen"],
          f"A={a['encoder_seen']} B={b['encoder_seen']}")

    print()
    print(f"{6-bad}/6 통과")
    return 1 if bad else 0


def selftest() -> int:
    """환산식만 검증 — ROS 없이 돈다."""
    cases = [
        ("counts/m = ppr×gear/(2πr)", abs(COUNTS_PER_M - 65536 * 32 / (2 * math.pi * 0.125)) < 1e-6),
        ("50 mm/s · 0.0833 m/s² → 0.600 s", abs(EXPECT_COAST_S - 0.600) < 0.005),
        ("관성 거리 = v²/2a = 15.0 mm", abs(EXPECT_COAST_M - 0.0150) < 1e-4),
        ("실측 0.57~0.65 s 구간 안", 0.57 <= EXPECT_COAST_S <= 0.65),
        ("15 mm 는 1 count(0.375 um) 보다 4자리 크다", EXPECT_COAST_M * COUNTS_PER_M > 1e4),
    ]
    print("=== selftest ===")
    bad = 0
    for n, ok in cases:
        print(f"[{'PASS' if ok else 'FAIL'}] {n}")
        bad += 0 if ok else 1
    print(f"\n{len(cases)-bad}/{len(cases)} 통과")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="SIL 플랜트 동특성·엔코더 실행 검증")
    ap.add_argument("--selftest", action="store_true", help="ROS 없이 환산식만 확인")
    a = ap.parse_args()
    return selftest() if a.selftest else report()


if __name__ == "__main__":
    sys.exit(main())
