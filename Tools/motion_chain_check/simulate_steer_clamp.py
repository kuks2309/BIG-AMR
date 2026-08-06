#!/usr/bin/env python3
"""조향 클램프 한계(±90° vs ±115°)가 실제 지령에 무엇을 바꾸는지 수치로 본다.

## 왜 시뮬레이션인가

「크랩 wrap 임계는 115° 인데 can_relay 는 90° 로 자른다」는 사실만으로는 **무엇이 얼마나
달라지는지** 알 수 없다. 실기로 확인하려면 3톤 차체를 움직여야 한다. 여기서는 저장소의
IK 코드를 **그대로 옮겨** 지령 각도를 재현하고, 두 한계에서 출력이 갈리는 구간과 그 크기를
계산한다.

## 이식 원본 (수식·상수를 바꾸지 않았다)

  normalizeAngle      qd_inverse_kinematics.cpp:77-91      임계 M_PI/2 (= 90°)
  wrapSteer           qd_crab_inverse_kinematics.cpp:36-50 임계 M_PI/2 + WRAP_MARGIN(25°)
  bring_into_region   qd_crab_inverse_kinematics.cpp:70-87 initial ± CLAMP_MARGIN(25°)

`initial_base_steer_` 는 Phase 0 의 DualSteerIK 결과가 들어간다
(`crab_linear_action_server.cpp:472` `setInitial(align_steer_f, …)`) → **[-90°, +90°]**.
따라서 cruise 출력은 `initial ± 25°` → 최대 **±115°** 다. 115 라는 수의 출처가 이것이다.

## 무엇을 판정하는가

  ① 일반 IK(translate/spin/turn/mpc/yaw) 가 90° 를 넘는 지령을 내는가
  ② 크랩에서 90° 를 넘는 구간이 어디이고, 90° 로 잘리면 무엇을 잃는가
  ③ 한계를 115° 로 열면 무엇이 달라지는가

사용:
    python3 Tools/motion_chain_check/simulate_steer_clamp.py
    python3 Tools/motion_chain_check/simulate_steer_clamp.py --selftest
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
GEOMETRY = REPO / "src/Control/Motion_Control/2WS/trnav_2ws_core/config/robot_geometry_2ws.yaml"

WRAP_MARGIN_DEG = 25.0      # qd_crab_inverse_kinematics.cpp:35
CLAMP_MARGIN_DEG = 25.0     # 같은 파일 :60
IK_HALF_PLANE_DEG = 90.0    # normalizeAngle 의 M_PI/2


# ── 이식 (C++ 그대로) ──────────────────────────────────────────────────────

def normalize_angle(angle_rad: float, direction: int):
    """qd_inverse_kinematics.cpp:77-91 — 반원(±90°) 정규화. 유일해 확정."""
    if angle_rad > math.pi / 2.0:
        angle_rad -= math.pi
        direction = -direction
    elif angle_rad < -math.pi / 2.0:
        angle_rad += math.pi
        direction = -direction
    return angle_rad, direction


def wrap_steer(steer: float, dir_: int, margin_rad: float):
    """qd_crab_inverse_kinematics.cpp:36-50 — ±(90°+margin) 에서만 접는다."""
    if steer > math.pi / 2.0 + margin_rad:
        steer -= math.pi
        dir_ = -dir_
    elif steer < -math.pi / 2.0 - margin_rad:
        steer += math.pi
        dir_ = -dir_
    return steer, dir_


def bring_into_region(raw: float, initial: float, margin_rad: float) -> float:
    """qd_crab_inverse_kinematics.cpp:70-87 — initial 영역으로 옮긴 뒤 ±margin clamp."""
    diff = raw - initial
    while diff > math.pi:
        diff -= 2.0 * math.pi
    while diff < -math.pi:
        diff += 2.0 * math.pi
    if diff > math.pi / 2.0:
        raw -= math.pi
    elif diff < -math.pi / 2.0:
        raw += math.pi
    diff = raw - initial
    while diff > math.pi:
        diff -= 2.0 * math.pi
    while diff < -math.pi:
        diff += 2.0 * math.pi
    diff = max(-margin_rad, min(margin_rad, diff))
    return initial + diff


def dual_steer_ik(vx: float, vy: float, omega: float, wheels) -> list:
    """qd_inverse_kinematics.cpp:11-31 + computeWheel — 휠별 (조향[deg], 속도, 방향)."""
    out = []
    for (x, y) in wheels:
        vx_i = vx - omega * y
        vy_i = vy + omega * x
        spd = math.hypot(vx_i, vy_i)
        if spd < 1e-6:
            out.append((0.0, 0.0, 0))
            continue
        steer, direction = normalize_angle(math.atan2(vy_i, vx_i), 1)
        out.append((math.degrees(steer), spd, direction))
    return out


def clamp_deg(deg: float, limit: float) -> float:
    return max(-limit, min(limit, deg))


# ── 판정 ①: 일반 IK 는 90° 를 넘는가 ──────────────────────────────────────

def probe_general_ik(wheels) -> dict:
    """(vx, vy, ω) 격자를 훑어 조향각 분포를 본다.

    `normalizeAngle` 이 수학적으로 ±90° 를 보장하므로 초과는 0 이어야 한다 —
    「보장된다」를 믿지 않고 격자로 확인한다.
    """
    worst = 0.0
    over90 = 0
    total = 0
    for i in range(-10, 11):
        for j in range(-10, 11):
            for k in range(-10, 11):
                vx, vy = i * 0.02, j * 0.02          # ±0.2 m/s
                omega = k * 0.03                      # ±0.3 rad/s
                for steer, spd, _d in dual_steer_ik(vx, vy, omega, wheels):
                    if spd < 1e-6:
                        continue
                    total += 1
                    worst = max(worst, abs(steer))
                    if abs(steer) > IK_HALF_PLANE_DEG + 1e-9:
                        over90 += 1
    return {"samples": total, "max_abs_deg": worst, "over_90": over90}


# ── 판정 ②③: 크랩에서 두 한계가 갈리는 구간 ──────────────────────────────

def probe_crab_cruise(step_deg: float = 1.0) -> dict:
    """cruise 는 `initial ± 25°` 다. 어디서 90° 를 넘고, 잘리면 얼마를 잃는가."""
    margin = math.radians(CLAMP_MARGIN_DEG)
    rows = []
    n_beyond90 = 0
    n_total = 0
    worst_loss = 0.0
    worst_at = None
    init = -90.0
    while init <= 90.0 + 1e-9:
        # 이 initial 에서 요구할 수 있는 보정 범위
        lo = bring_into_region(math.radians(init - CLAMP_MARGIN_DEG), math.radians(init), margin)
        hi = bring_into_region(math.radians(init + CLAMP_MARGIN_DEG), math.radians(init), margin)
        lo_d, hi_d = math.degrees(lo), math.degrees(hi)
        # ±90 클램프가 잘라내는 폭
        cut_hi = max(0.0, hi_d - IK_HALF_PLANE_DEG)
        cut_lo = max(0.0, -IK_HALF_PLANE_DEG - lo_d)
        cut = max(cut_hi, cut_lo)
        n_total += 1
        if cut > 1e-9:
            n_beyond90 += 1
            if cut > worst_loss:
                worst_loss = cut
                worst_at = init
        rows.append((init, lo_d, hi_d, cut))
        init += step_deg
    return {"rows": rows, "n_total": n_total, "n_beyond90": n_beyond90,
            "worst_loss_deg": worst_loss, "worst_at_initial_deg": worst_at}


def probe_crab_phase0(step_deg: float = 1.0) -> dict:
    """Phase 0(미초기화) 은 `wrapSteer` — ±115° 를 넘어야 접는다."""
    margin = math.radians(WRAP_MARGIN_DEG)
    beyond90 = 0
    worst = 0.0
    total = 0
    raw = -180.0
    while raw <= 180.0 + 1e-9:
        s, _d = wrap_steer(math.radians(raw), 1, margin)
        sd = math.degrees(s)
        total += 1
        if abs(sd) > IK_HALF_PLANE_DEG + 1e-9:
            beyond90 += 1
            worst = max(worst, abs(sd))
        raw += step_deg
    return {"samples": total, "beyond_90": beyond90, "max_abs_deg": worst}


def lateral_authority_loss(steer_deg: float, limit_deg: float) -> float:
    """조향 θ 를 요구했는데 limit 로 잘렸을 때, **의도한 방향 성분**이 얼마나 남는가.

    바퀴 속도벡터는 조향각 방향이다. 요구 θ 대신 θ' 로 가면 의도 방향 성분은 cos(θ−θ') 배다.
    """
    applied = clamp_deg(steer_deg, limit_deg)
    return math.cos(math.radians(steer_deg - applied))



# ── 정책 비교: 반원 고정(±90) vs 현재 조향 기준 최소 변화 ──────────────────

def wrap_pi(a: float) -> float:
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a


def select_min_change(desired: float, cur_steer: float, cur_dir: int,
                      hysteresis_rad: float) -> tuple:
    """등가 2해 중 **현재 조향에서 덜 움직이는 쪽**을 고른다.

    한 바퀴의 속도벡터는 `(θ,+v) ≡ (θ∓180°,−v)` 두 표현을 갖는다. 반원 고정(±90°)은
    **입력만 보고** 한쪽을 정하므로, 목표가 경계를 지날 때마다 조향이 180° 튀고 구동 부호가
    뒤집힌다. 최소 변화 선택은 **현재 상태까지 보고** 덜 움직이는 표현을 고른다 —
    유일해는 그대로다(상태가 주어지면 출력이 하나로 결정된다).

    `hysteresis_rad` 는 두 후보의 이동량이 비슷할 때 **현재 분기를 유지**시켜 경계
    떨림(chattering)을 막는다. 크랩의 `WRAP_MARGIN`(25°)이 하는 일과 같은 역할이다.
    """
    cands = [(wrap_pi(desired), +1), (wrap_pi(desired + math.pi), -1)]
    costs = [abs(wrap_pi(c[0] - cur_steer)) for c in cands]
    # 현재 구동 방향과 같은 분기를 기본으로 두고, 상대가 hysteresis 이상 유리할 때만 바꾼다.
    keep_i = 0 if cur_dir >= 0 else 1
    flip_i = 1 - keep_i
    if costs[flip_i] + hysteresis_rad < costs[keep_i]:
        return cands[flip_i][0], cands[flip_i][1], True
    return cands[keep_i][0], cands[keep_i][1], False


def run_policy(desired_seq, policy: str, hysteresis_deg: float = 25.0) -> dict:
    """목표 각 수열을 정책으로 돌려 조향 이동량·부호반전·필요 범위를 센다."""
    hyst = math.radians(hysteresis_deg)
    cur = 0.0
    cur_dir = 1
    travel = 0.0
    flips = 0
    peak = 0.0
    over90 = 0
    for d in desired_seq:
        if policy == "halfplane":
            out, direction = normalize_angle(wrap_pi(d), 1)
        else:
            out, direction, flipped = select_min_change(d, cur, cur_dir, hyst)
            if flipped:
                flips += 1
        if policy == "halfplane" and direction != cur_dir:
            flips += 1
        travel += abs(math.degrees(wrap_pi(out - cur)))
        cur, cur_dir = out, direction
        peak = max(peak, abs(math.degrees(out)))
        if abs(math.degrees(out)) > IK_HALF_PLANE_DEG + 1e-9:
            over90 += 1
    return {"travel_deg": travel, "flips": flips, "peak_deg": peak, "over_90": over90}


def scenarios() -> dict:
    """목표 조향각 수열 — 경계(±90°)를 지나는 상황을 포함한다."""
    out = {}
    # ① 직진 -> 좌측 크랩 90° -> 100° 까지 넘어감 -> 복귀
    seq = [math.radians(x) for x in
           list(range(0, 101, 2)) + list(range(100, -1, -2))]
    out["크랩 전환 0°→100°→0°"] = seq
    # ② 측면 크랩 유지 중 CTE 보정 ±10° 진동 (경계 걸침)
    seq = [math.radians(90.0 + 10.0 * math.sin(i * 0.4)) for i in range(120)]
    out["측면 크랩 88~100° 진동"] = seq
    # ③ 경계 바로 위에서 미세 떨림 (±2°)
    seq = [math.radians(90.0 + 2.0 * math.sin(i * 0.9)) for i in range(120)]
    out["경계 ±2° 미세 떨림"] = seq
    return out


def compare_policies() -> None:
    print("④ 정책 비교 — 반원 고정(±90) vs 최소 변화 선택")
    print("   조향이동 = 액추에이터가 실제로 돈 각도 총합 · 부호반전 = 구동 방향이 뒤집힌 횟수")
    print()
    print("   시나리오                    | 정책          | 조향이동  | 부호반전 | 최대각 | >90° 샘플")
    print("   ---------------------------+---------------+-----------+----------+--------+----------")
    for name, seq in scenarios().items():
        for pol, label in (("halfplane", "반원 고정"), ("minchange", "최소 변화")):
            r = run_policy(seq, pol)
            print(f"   {name:<27}| {label:<14}| {r['travel_deg']:8.0f}° | {r['flips']:8d} |"
                  f" {r['peak_deg']:5.0f}° | {r['over_90']:4d}/{len(seq)}")
        print("   " + "-" * 88)



def run_bounded(seq, bound_deg: float) -> dict:
    """**최소 변화 + 범위 상한** — 더 가까운 해가 상한을 넘으면 반대 해로 뒤집는다.

    이것이 `wrapSteer` 의 일반형이다(상한 = 90°+WRAP_MARGIN). 상한을 90° 로 주면
    반원 고정과 같아진다 — 즉 현행 두 정책은 **같은 식의 양 끝**이다.

    ⚠ 상한 없는 최소 변화는 쓸 수 없다 — 휠 각이 한 바퀴 도는 운동(스핀)에서 출력이
    ±180° 까지 간다(실측: 177.8°). 기구가 그만큼 돌지 않는다.
    """
    B = math.radians(bound_deg)
    cur, cur_dir = 0.0, 1
    travel, flips, peak = 0.0, 0, 0.0
    for d in seq:
        cands = [(wrap_pi(d), +1), (wrap_pi(d + math.pi), -1)]
        costs = [abs(wrap_pi(c[0] - cur)) for c in cands]
        order = sorted(range(2), key=lambda i: costs[i])
        pick = next((i for i in order if abs(cands[i][0]) <= B + 1e-12), order[0])
        out, direction = cands[pick]
        if direction != cur_dir:
            flips += 1
        travel += abs(math.degrees(wrap_pi(out - cur)))
        cur, cur_dir = out, direction
        peak = max(peak, abs(math.degrees(out)))
    return {"travel_deg": travel, "flips": flips, "peak_deg": peak}


def sweep_bound() -> None:
    """상한을 얼마로 두면 이득이 실현되는가."""
    sc = dict(scenarios())
    sc["제자리 스핀(휠 각 한 바퀴)"] = [math.radians(x) for x in range(0, 721, 5)]
    print("⑤ 상한 훑기 — 최소 변화 정책에서 조향 이동량·구동 부호반전")
    print("   (상한 90° = 현행 반원 고정과 동일하다 — 같은 식의 양 끝)")
    print()
    names = list(sc)
    print("   상한 | " + " | ".join(f"{n[:20]:<20}" for n in names))
    print("   -----+-" + "-+-".join(["-" * 20] * len(names)))
    for B in (90, 100, 110, 115, 120, 140):
        cells = []
        for n in names:
            r = run_bounded(sc[n], B)
            cells.append(f"이동{r['travel_deg']:5.0f}° 반전{r['flips']:2d}")
        print(f"   {B:4d}° | " + " | ".join(f"{c:<20}" for c in cells))
    print()
    print("   → 상한을 **100° 만 넘겨도 이득이 전부 실현**된다(100~140 차이 0).")
    print("   → 스핀은 어느 상한에서도 같다 — 휠 각이 한 바퀴 도는 운동은 반드시 뒤집어야 한다.")



# ── 부호 반전의 실제 대가: 구동륜 속도 계단 ────────────────────────────────

CRUISE_MPS = 0.2            # can_relay vel_max_units 4889 = 0.2 m/s
CONTROL_HZ = 50.0           # <action>_params.yaml control_rate_hz
WHEEL_RADIUS_M = 0.125      # 정본 robot_geometry_2ws.yaml
GEAR_WALK = 32.0


def flip_cost(flips: int, cruise_mps: float = CRUISE_MPS,
              control_hz: float = CONTROL_HZ) -> dict:
    """구동 부호가 뒤집힐 때 **지령이 요구하는** 속도 계단과 등가 가속도.

    조향 해를 바꾸면 같은 바퀴 운동을 `(θ∓180°, −v)` 로 표현하므로 **구동 속도 부호가
    반대로 나간다**. 지령은 한 제어주기 안에 `+v → −v` 를 요구한다 — 계단 `2v` 다.
    3톤 차체가 그 계단을 따를 수 없으므로 실제로는 드라이브가 포화·램프하고, 그 사이
    **실제 운동이 지령과 갈라진다**(무엇이 되는지는 지령이 정의하지 않는다).

    조향도 동시에 180° 튄다 — 두 액추에이터가 함께 불가능한 지령을 받는다.
    """
    step_mps = 2.0 * cruise_mps
    dt = 1.0 / control_hz
    accel = step_mps / dt
    motor_rpm = (cruise_mps / WHEEL_RADIUS_M) * 60.0 / (2.0 * math.pi) * GEAR_WALK
    return {"flips": flips, "step_mps": step_mps, "accel_mps2": accel,
            "accel_g": accel / 9.80665, "motor_rpm_step": 2.0 * motor_rpm}


def report_flip_cost() -> None:
    sc = dict(scenarios())
    sc["제자리 스핀(휠 각 한 바퀴)"] = [math.radians(x) for x in range(0, 721, 5)]
    c = flip_cost(1)
    print("⑥ 구동 부호 반전의 대가 — **바퀴 속도 제약**")
    print(f"   순항 {CRUISE_MPS} m/s · 제어주기 {CONTROL_HZ:.0f} Hz 기준, 반전 1회가 지령하는 것:")
    print(f"     속도 계단 {c['step_mps']:.2f} m/s (한 주기 {1000/CONTROL_HZ:.0f} ms 안에)")
    print(f"     등가 가속도 {c['accel_mps2']:.0f} m/s² = {c['accel_g']:.1f} g")
    print(f"     모터 회전수 계단 {c['motor_rpm_step']:,.0f} rpm (감속비 {GEAR_WALK:.0f})")
    print("   3톤 차체가 따를 수 없다 — 드라이브가 포화·램프하고 그 구간의 실제 운동은")
    print("   지령이 정의하지 않는다. 조향도 같은 순간 180° 튄다.")
    print()
    print("   시나리오                  | 반원 고정(±90) | 최소 변화(상한 100°+)")
    print("   -------------------------+----------------+----------------------")
    for name, seq in sc.items():
        a = run_bounded(seq, 90.0)
        b = run_bounded(seq, 100.0)
        print(f"   {name:<25}| 반전 {a['flips']:2d}회        | 반전 {b['flips']:2d}회")
    print()
    print("   → 경계에서 목표가 ±2° 떠는 것만으로 **반전 35회** — 정·역을 35번 요구한다.")
    print("     최소 변화면 0회다. 이것이 조향 이동량보다 큰 차이다.")



# ── ⑦ 액션별 실제 지령: 경계를 지나는 것은 어느 것인가 ────────────────────

CARRIER_AGV_GEOM = [(0.330, 0.135), (-0.330, -0.135)]   # 종전(대각) — 비교용


def probe_turn_radius(wheels, radii=None) -> list:
    """turn(R-turn) 은 `compute({v, 0, ω})`, `v = ω·R` 이다(turn_action_server.cpp:211-213).

    따라서 조향각 = `atan2(x_i, R − y_i)` — **R 과 y_i 의 대소가 경계 교차를 정한다.**
    `R < y_i` 이면 `vx_i` 부호가 뒤집혀 정규화 전 각이 90° 를 넘고, `normalizeAngle` 이
    접으면서 **조향 ~174° 점프 + 구동 부호 반전**이 난다.
    """
    radii = radii or [5.0, 2.0, 1.0, 0.5, 0.2, 0.135, 0.1, 0.05, 0.0]
    out = []
    for R in radii:
        w = 1.0
        raws = [math.degrees(math.atan2(w * x, w * R - w * y)) for (x, y) in wheels]
        norm = [a for a, _s, _d in dual_steer_ik(w * R, 0.0, w, wheels)]
        out.append((R, norm, sum(1 for r in raws if abs(r) > 90.0)))
    return out


def report_action_boundaries(geom) -> None:
    print("⑦ 액션별 실제 지령 — 경계(±90°)를 지나는 것은 어느 것인가")
    print()
    print("   spin  : computeSpin(ω) 뿐이라 **병진을 섞지 않는다**(spin_action_server.cpp:328).")
    for wheels, lab in ((CARRIER_AGV_GEOM, "종전 대각"), (geom, "현행 inline")):
        row = []
        for w in (+0.3, -0.3):
            o = dual_steer_ik(0.0, 0.0, w, wheels)
            row.append(f"ω={w:+.1f}→[{o[0][0]:+7.2f}°,{o[1][0]:+7.2f}°] dir[{o[0][2]:+d},{o[1][2]:+d}]")
        print(f"           {lab:<10} " + "  ".join(row))
    print("           ω 부호가 바뀌면 **조향각은 그대로, 구동 방향만** 뒤집힌다 — 역방향 스핀에")
    print("           물리적으로 필요한 동작이다(경계 문제가 아니다).")
    print()
    print("   turn  : v = ω·R 이라 조향각 = atan2(x_i, R − y_i). R 과 y_i 의 대소가 교차를 정한다.")
    print("           R[m]  |   종전 대각 기하        |   현행 inline 기하")
    for (R, n_old, c_old), (_R, n_new, c_new) in zip(
            probe_turn_radius(CARRIER_AGV_GEOM), probe_turn_radius(geom)):
        print(f"           {R:5.3f} | {n_old[0]:+7.2f}° {n_old[1]:+7.2f}° 교차{c_old} "
              f"| {n_new[0]:+7.2f}° {n_new[1]:+7.2f}° 교차{c_new}")
    print("           → 종전 대각 기하는 **R < y_1(0.135 m)** 에서 교차했다(조향 ~174° 점프 +")
    print("             구동 부호 반전). 현행 inline(y≈0)은 R=0 까지 교차 0 — 기하 정정이")
    print("             그 결함을 **없앴다**.")
    print()
    print("   crab  : 유일하게 90° 를 넘겨 요구한다(②③). 클램프를 여는 이유가 이것뿐이다.")


def main() -> int:
    ap = argparse.ArgumentParser(description="조향 클램프 ±90° vs ±115° 시뮬레이션")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    geom = None
    try:
        doc = yaml.safe_load(GEOMETRY.read_text(encoding="utf-8"))
        g = list(doc.values())[0]["ros__parameters"]
        geom = [(float(g["w1_x"]), float(g["w1_y"])), (float(g["w2_x"]), float(g["w2_y"]))]
    except Exception as exc:                                    # noqa: BLE001
        print(f"기하 정본을 읽지 못했다 ({exc}) — 격자 판정 생략")

    print("=== 조향 클램프 시뮬레이션 (±90° vs ±115°) ===")
    print(f"이식 원본: normalizeAngle(±90°) · wrapSteer(±{90 + WRAP_MARGIN_DEG:.0f}°) · "
          f"bring_into_region(initial±{CLAMP_MARGIN_DEG:.0f}°)")
    if geom:
        wb = abs(geom[0][0] - geom[1][0])
        print(f"기하: w1={geom[0]} w2={geom[1]}  휠베이스 {wb:.3f} m")
    print()

    if geom:
        r = probe_general_ik(geom)
        print("① 일반 IK (translate·spin·turn·mpc·yaw) — (vx,vy,ω) 격자 9,261점")
        print(f"   최대 |조향| = {r['max_abs_deg']:.3f}°  ·  90° 초과 샘플 = {r['over_90']}건 "
              f"/ {r['samples']:,}")
        print("   → 90° 클램프가 **한 번도 발동하지 않는다**. 한계를 115° 로 열어도 이 경로는 무변화.")
        print()

    c = probe_crab_cruise()
    print("② 크랩 cruise (initial ± 25°) — initial 을 −90°~+90° 로 훑음")
    print(f"   90° 를 넘는 initial 구간 = {c['n_beyond90']} / {c['n_total']}개 샘플 "
          f"(|initial| > {90 - CLAMP_MARGIN_DEG:.0f}° 일 때)")
    print(f"   최대 잘림 = {c['worst_loss_deg']:.1f}°  (initial = {c['worst_at_initial_deg']:+.0f}°)")
    print()
    print("   initial |  요구 가능 범위      | ±90 클램프가 자르는 폭 | 의도방향 성분 잔존")
    print("   --------+---------------------+------------------------+-------------------")
    for init, lo, hi, cut in c["rows"]:
        if abs(init) in (0.0, 30.0, 60.0, 70.0, 80.0, 85.0, 90.0):
            # 잘리는 쪽 경계로 계산한다 — initial 이 음수면 lo 쪽이 잘린다.
            cut_side = hi if (hi - IK_HALF_PLANE_DEG) >= (-IK_HALF_PLANE_DEG - lo) else lo
            keep = lateral_authority_loss(cut_side, IK_HALF_PLANE_DEG)
            mark = "  ←잘림" if cut > 1e-9 else ""
            print(f"   {init:+6.0f}° | {lo:+7.1f}° ~ {hi:+7.1f}° | {cut:6.1f}°"
                  f"{'':16}| {keep * 100:5.2f} %{mark}")
    print()

    compare_policies()
    print()

    sweep_bound()
    print()

    report_flip_cost()
    print()

    if geom:
        report_action_boundaries(geom)
        print()

    p = probe_crab_phase0()
    print("③ 크랩 Phase 0 (미초기화, wrapSteer)")
    print(f"   90° 초과 출력 = {p['beyond_90']} / {p['samples']}  ·  최대 |조향| = {p['max_abs_deg']:.1f}°")
    print()

    print("=== 판정 ===")
    print("· 한계를 115° 로 여는 것이 **바꾸는 것은 크랩뿐**이다 — 일반 IK 는 ±90° 를 넘지 않는다(①).")
    print("· 다만 ④⑤ 가 보이듯 **반원 고정 자체가 경계에서 chattering 을 만든다** — 목표가 90° 근처에서")
    print("  ±2° 떠는 것만으로 조향 6,404°·부호반전 35회다. 최소 변화(상한 100°+)면 222°·0회.")
    print("  크랩의 WRAP_MARGIN 은 그 문제를 크랩에서만 부분적으로 막고 있는 장치다.")
    print(f"· 크랩에서 갈리는 조건은 **|initial| > {90 - CLAMP_MARGIN_DEG:.0f}°** — 즉 거의 옆으로 가는")
    print("  게걸음일 때다. 그때 ±90 클램프는 **한쪽 방향 보정만** 잘라내므로 CTE 보정이 비대칭이 된다.")
    print(f"· 잘리는 최대 폭은 {c['worst_loss_deg']:.0f}° 이고, 그 지점에서도 의도방향 속도 성분은 "
          f"{lateral_authority_loss(115.0, 90.0) * 100:.1f}% 남는다(cos {c['worst_loss_deg']:.0f}°).")
    print("  즉 **진행은 거의 유지되고 잃는 것은 보정 여유**다 — 크랩 주석의 「motor saturate 로")
    print("  robot 진행은 거의 정확」과 일치한다.")
    print("· 열면 90~115° 구간에서 **등가해 2개가 공존**한다(ADR 유일해 구속 위반). 일반 IK 는")
    print("  여전히 ±90° 로 정규화하므로 두 계층의 기준이 갈린다.")
    print("· Foil_A082 의 기구 조향 한계는 저장소에 **실측 기록이 없다** — 115° 가 물리적으로")
    print("  가능한지는 미판정이다(±140° 는 Roll_A084 live_models 인용).")
    return 0


def selftest() -> int:
    """이식이 원본 수식을 지키는지 — 경계값으로 고정한다."""
    cases = []
    m = math.radians(WRAP_MARGIN_DEG)

    a, d = normalize_angle(math.radians(100.0), 1)
    cases.append(("normalizeAngle 100° → −80°, dir 반전",
                  abs(math.degrees(a) - (-80.0)) < 1e-9 and d == -1))
    a, d = normalize_angle(math.radians(89.0), 1)
    cases.append(("normalizeAngle 89° → 그대로", abs(math.degrees(a) - 89.0) < 1e-9 and d == 1))

    s, d = wrap_steer(math.radians(114.0), 1, m)
    cases.append(("wrapSteer 114° → 접지 않음", abs(math.degrees(s) - 114.0) < 1e-9 and d == 1))
    s, d = wrap_steer(math.radians(116.0), 1, m)
    cases.append(("wrapSteer 116° → −64°, dir 반전",
                  abs(math.degrees(s) - (-64.0)) < 1e-9 and d == -1))

    r = bring_into_region(math.radians(120.0), math.radians(90.0), m)
    cases.append(("bring_into_region(120°, init 90°) → 115° (initial+25)",
                  abs(math.degrees(r) - 115.0) < 1e-9))
    r = bring_into_region(math.radians(95.0), math.radians(90.0), m)
    cases.append(("bring_into_region(95°, init 90°) → 95° (마진 안)",
                  abs(math.degrees(r) - 95.0) < 1e-9))

    cases.append(("clamp 90 이 115° 를 90° 로", abs(clamp_deg(115.0, 90.0) - 90.0) < 1e-9))
    cases.append(("clamp 115 는 115° 를 통과", abs(clamp_deg(115.0, 115.0) - 115.0) < 1e-9))
    cases.append(("잘림 25° 의 잔존 성분 = cos25°",
                  abs(lateral_authority_loss(115.0, 90.0) - math.cos(math.radians(25.0))) < 1e-12))

    wheels = [(0.6039, 0.0), (-0.5961, 0.0)]
    cases.append(("일반 IK 는 ±90° 를 넘지 않는다", probe_general_ik(wheels)["over_90"] == 0))

    print("=== selftest (이식 정합) ===")
    bad = 0
    for name, ok in cases:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        bad += 0 if ok else 1
    print()
    print(f"{len(cases)}건 중 {len(cases) - bad}건 통과")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
