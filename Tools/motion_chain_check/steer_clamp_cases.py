#!/usr/bin/env python3
"""조향각 클램프 — **케이스별** 재도출.

조향 한계가 8개 계층에 흩어져 있어 「어느 기동에서 어느 클램프가 무는가」를 눈으로 쫓기 어렵다.
본 도구는 각 계층 값을 **설정·소스에서 읽어** 케이스별로 다시 계산한다. 문서에 적힌 숫자를
믿지 않는다.

## 계층 (상류 → 하류)

  ① IK 정규화        normalizeAngle 의 M_PI/2 = ±90°   (코드 고정, config 로 안 바뀜)
  ② 크랩 wrap        wrapSteer 임계 = 90° + WRAP_MARGIN
  ②' 크랩 cruise     initial ± CLAMP_MARGIN
  ③ 액션 δ 한계      <action>_params.yaml 의 max_delta / max_steer (bicycle 경로)
  ④ translator       클램프 **없음**. steer_offset 을 빼고 counts 로 환산
  ⑤ can_relay        체인 steer_limit_deg / 벤치 steer_limit_bench_deg (counts, 홈 기준)
  ⑥ 코드 기본        safety.STEER_LIMIT_DEG (config 미설정 시)
  ⑦ GUI              ui/app.py 슬라이더 · ui/backend_direct.py 자체 클램프
  ⑧ 기구 −리밋       호밍이 매번 실측 (SEER_HOME_ZERO / counts_per_deg)

## 핵심 — 영점 오프셋이 클램프를 **비대칭**으로 만든다

translator 는 `raw = (θ − offset)` 을 counts 로 만든다(offset = −1.676°). 즉 raw 각의 크기는
**+쪽에서 1.676° 커지고 −쪽에서 1.676° 작아진다.** can_relay 는 counts 로 판정하므로
같은 |θ| 라도 **부호에 따라 잘리는지가 갈린다.**

사용:
    python3 Tools/motion_chain_check/steer_clamp_cases.py
    python3 Tools/motion_chain_check/steer_clamp_cases.py --selftest
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
TR = REPO / "src/Control/Motion_Control/Common/amr_motor_cmd_translator/config/amr_motor_cmd_translator_qd.yaml"
RELAY = REPO / "src/Comm/CAN/can_relay/config/can_relay.yaml"
MACHINE = REPO / "src/Comm/CAN/can_relay/config/machine/foil_a082.yaml"
GEOM = REPO / "src/Control/Motion_Control/2WS/trnav_2ws_core/config/robot_geometry_2ws.yaml"
CRAB_SRC = REPO / "src/Control/Motion_Control/2WS/trnav_2ws_kinematics/src/qd_crab_inverse_kinematics.cpp"
ACT_CFG = REPO / "src/Control/Motion_Control/2WS/trnav_2ws_action_server/config"
GATE = REPO / "Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h"

IK_HALF_PLANE = 90.0    # normalizeAngle 의 M_PI/2


def ros_params(path: Path) -> dict:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    for v in doc.values():
        if isinstance(v, dict) and "ros__parameters" in v:
            return v["ros__parameters"]
    raise ValueError(f"{path}: ros__parameters 없음")


def const_deg(src: Path, name: str):
    """`constexpr double NAME = 25.0 * M_PI / 180.0;` 에서 25.0 을 꺼낸다."""
    if not src.exists():
        return None
    m = re.search(rf"{name}\s*=\s*([0-9.]+)\s*\*\s*M_PI\s*/\s*180", src.read_text(encoding="utf-8"))
    return float(m.group(1)) if m else None


def mech_limit_deg(cpd: float):
    if not GATE.exists():
        return None
    vals = [int(v) for v in re.findall(r"#define\s+SEER_HOME_ZERO_N\d+\s+(\d+)", GATE.read_text(encoding="utf-8"))]
    return min(vals) / cpd if vals else None


def action_limit(name: str):
    """`<action>_params.yaml` 의 δ 한계(있으면). 키 이름이 액션마다 다르다."""
    p = ACT_CFG / f"{name}_params.yaml"
    if not p.exists():
        return None
    try:
        pr = ros_params(p)
    except ValueError:
        return None
    for k, v in pr.items():
        if k.endswith("max_delta_deg") or k.endswith("max_steer_deg"):
            return float(v)
    return None


class Case:
    def __init__(self, name, kind, theta_deg, note=""):
        self.name, self.kind, self.theta, self.note = name, kind, theta_deg, note


def build_cases(geom, crab_wrap, crab_clamp) -> list:
    """각 기동이 **IK 계층에서 낼 수 있는 최대 |조향각|**."""
    w1x, w1y = float(geom["w1_x"]), float(geom["w1_y"])
    # 제자리 스핀: vx=vy=0 → atan2(ω·x, −ω·y)
    spin = math.degrees(math.atan2(w1x, -w1y))
    cases = [
        Case("translate_forward", "bicycle", action_limit("translate_forward"),
             "δ 한계는 params 의 max_delta"),
        Case("translate_reverse", "bicycle", action_limit("translate_reverse"), ""),
        Case("mpc", "bicycle", action_limit("mpc"), ""),
        Case("mpc_reverse", "bicycle", action_limit("mpc_reverse"), ""),
        Case("yaw_control", "bicycle", action_limit("yaw_control"), ""),
        Case("yaw_control_reverse", "bicycle", action_limit("yaw_control_reverse"), ""),
        Case("spin", "free IK", spin, "vx=vy=0 → 기하가 각을 결정(±90° 정규화 안쪽)"),
        Case("turn (R→0)", "free IK", spin, "R 이 작아질수록 spin 자세에 접근"),
        Case("turn (미세보정)", "free IK", spin, "computeSpin 사용 — spin 과 같은 자세"),
        Case("crab Phase 0", "크랩 wrap", IK_HALF_PLANE + (crab_wrap or 0.0),
             "wrapSteer 임계까지는 접지 않는다"),
        Case("crab cruise", "크랩 cruise", IK_HALF_PLANE + (crab_clamp or 0.0),
             "initial(≤90°) ± CLAMP_MARGIN"),
    ]
    return [c for c in cases if c.theta is not None]


def report() -> int:
    tr, relay, machine, geom = ros_params(TR), ros_params(RELAY), ros_params(MACHINE), ros_params(GEOM)
    cpd = float(machine["steer_counts_per_deg"])
    off = float(tr["steer_offset_front_deg"])
    chain = float(machine.get("steer_limit_deg", relay["steer_limit_deg"]))
    bench = float(machine.get("steer_limit_bench_deg", relay.get("steer_limit_bench_deg", chain)))
    crab_wrap = const_deg(CRAB_SRC, "WRAP_MARGIN")
    crab_clamp = const_deg(CRAB_SRC, "CLAMP_MARGIN")
    mech = mech_limit_deg(cpd)

    print("=== 계층별 한계 (설정·소스에서 읽음) ===")
    print(f"  ① IK 정규화           ±{IK_HALF_PLANE:.0f}°   (normalizeAngle, 코드 고정)")
    print(f"  ② 크랩 wrap 임계       ±{IK_HALF_PLANE + (crab_wrap or 0):.0f}°   (90 + WRAP_MARGIN {crab_wrap})")
    print(f"  ②' 크랩 cruise         initial ± {crab_clamp}°")
    print(f"  ④ translator 영점      offset {off}°  ·  {cpd:,.0f} counts/°  ·  dir {tr['direction_steer_front']}")
    print(f"  ⑤ can_relay            체인 ±{chain}°  ·  벤치 ±{bench}°")
    print(f"  ⑧ 기구 −리밋           ±{mech:.1f}°" if mech else "  ⑧ 기구 −리밋           미판정")
    print()
    print("=== 케이스별 — IK 각이 translator 를 지나 can_relay 클램프에 걸리는가 ===")
    print("  ⚠ 영점 오프셋 때문에 **부호에 따라 결과가 다르다**(+쪽이 1.676° 불리).")
    print()
    print("  기동                  계층        IK |θ|   raw(+θ)   raw(−θ)   체인±%-5s 판정" % f"{chain:.0f}")
    print("  " + "-" * 86)
    worst = []
    for c in build_cases(geom, crab_wrap, crab_clamp):
        raw_p = abs(c.theta - off)      # θ = +|θ|
        raw_n = abs(-c.theta - off)     # θ = −|θ|
        cut_p = max(0.0, raw_p - chain)
        cut_n = max(0.0, raw_n - chain)
        if cut_p > 1e-9 or cut_n > 1e-9:
            verdict = f"잘림 +{cut_p:.2f}° / −{cut_n:.2f}°"
            worst.append((c.name, max(cut_p, cut_n)))
        else:
            verdict = "통과"
        print(f"  {c.name:<21} {c.kind:<11} {c.theta:6.2f}°  {raw_p:7.2f}°  {raw_n:7.2f}°   {verdict}")
    print()
    print("  ※ raw = |θ − offset| — translator 가 counts 로 만드는 각. can_relay 는 이 값으로 판정한다.")
    print()

    print("=== 종전 ±90° 였다면 (비교) ===")
    for c in build_cases(geom, crab_wrap, crab_clamp):
        raw_p, raw_n = abs(c.theta - off), abs(-c.theta - off)
        if max(raw_p, raw_n) > IK_HALF_PLANE + 1e-9:
            print(f"  {c.name:<21} +θ {max(0.0, raw_p-IK_HALF_PLANE):.2f}° / "
                  f"−θ {max(0.0, raw_n-IK_HALF_PLANE):.2f}° 잘렸다")
    print()

    print("=== 벤치 직접 지령 (사람이 손으로 넣는 경로) ===")
    print(f"  ~/steer_deg · ~/steer_axis_deg  →  ±{bench}° 로 클램프(체인과 분리)")
    print(f"  GUI ui/app.py 슬라이더 · ui/backend_direct.py  →  자체 상수 90° (config 무관)")
    print()

    if mech:
        print(f"=== 여유 === 체인 {chain}° ≤ 기구 −리밋 {mech:.1f}°  →  여유 {mech - chain:.1f}°")
    return 0


def selftest() -> int:
    """계산 규칙을 경계값으로 고정한다."""
    off = -1.676
    cases = [
        ("+89.87° 는 오프셋 후 91.55° (90 초과)", abs(89.87 - off) > 90.0),
        ("−89.87° 는 오프셋 후 88.19° (90 이내)", abs(-89.87 - off) < 90.0),
        ("오프셋 비대칭 폭 = 2×|offset|",
         abs((abs(89.87 - off) - abs(-89.87 - off)) - 2 * abs(off)) < 1e-9),
        ("115° 클램프는 91.55° 를 통과시킨다", abs(89.87 - off) <= 115.0),
        ("크랩 cruise 최대 115° 는 오프셋 후 116.68° → 115 초과",
         abs(115.0 - off) > 115.0),
    ]
    print("=== selftest ===")
    bad = 0
    for n, ok in cases:
        print(f"[{'PASS' if ok else 'FAIL'}] {n}")
        bad += 0 if ok else 1
    print()
    print(f"{len(cases)}건 중 {len(cases)-bad}건 통과")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="조향각 클램프 케이스별 재도출")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    return selftest() if a.selftest else report()


if __name__ == "__main__":
    sys.exit(main())
