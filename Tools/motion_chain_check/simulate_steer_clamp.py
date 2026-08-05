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

    p = probe_crab_phase0()
    print("③ 크랩 Phase 0 (미초기화, wrapSteer)")
    print(f"   90° 초과 출력 = {p['beyond_90']} / {p['samples']}  ·  최대 |조향| = {p['max_abs_deg']:.1f}°")
    print()

    print("=== 판정 ===")
    print("· 한계를 115° 로 여는 것이 **바꾸는 것은 크랩뿐**이다 — 일반 IK 는 ±90° 를 넘지 않는다(①).")
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

    wheels = [(0.6039, -0.0014), (-0.5961, -0.0014)]
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
