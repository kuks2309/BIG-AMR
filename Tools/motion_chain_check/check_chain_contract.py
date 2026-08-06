#!/usr/bin/env python3
"""모션→모터 체인의 단위·배선 계약을 **config 에서 재도출해** 대조한다.

## 왜 필요한가

같은 물리량이 네 곳에 흩어져 있고 서로를 모른다:

  · translator YAML          gear_steer · wheel_radius_m · gear_walk · pulses_per_rev
  · can_relay machine YAML   steer_counts_per_deg · drive_units_per_mmps
  · 2WS <action>_params.yaml wheel_radius · gear_walk (2WS 안에서는 RPM 표시용)
  · 코드 default             qd_action_server_base.hpp:189-194

QD(Carrier AGV) 스택에서 2WS 로 이식할 때 상류 값이 그대로 남아, translator 가
48,332.8 c/deg 로 환산하는데 이 기체 드라이브는 57,344.0 c/deg 였다(18.6% 과소).
값을 한 번 고쳐도 다음 이식에서 같은 일이 되풀이되므로, **문서에 적힌 숫자를 믿지 않고
매번 config 에서 다시 계산해 대조**한다.

## 무엇을 검사하는가

  C1 조향 스케일  ppr × gear_steer / 360              == steer_counts_per_deg
  C2 구동 스케일  60×gear_walk×10 / (2π×r) / 1000     == drive_units_per_mmps
  C3 배선(motor_id)  translator 1~4                   == can_relay drive_nodes+steer_nodes
  C4 조향 한계    can_relay steer_limit_deg           == 2WS <action>_params steer_limit_deg
                  (크랩 wrapSteer 의 실효 상한 90°+WRAP_MARGIN 은 초과 시 WARN)

불일치가 하나라도 있으면 exit 1. WARN 은 exit 코드에 영향을 주지 않는다.

## 사용

  python3 Tools/motion_chain_check/check_chain_contract.py
  python3 Tools/motion_chain_check/check_chain_contract.py --selftest   # 검출력 회귀

`--selftest` 는 합성 config 로 「정상이면 통과, 한 값만 틀리면 그 검사가 FAIL」을 확인한다.
검사기가 실제로 불일치를 잡는지 증명하지 않으면 통과 출력은 아무것도 보장하지 않는다
(근거: docs/claude-mistake/INDEX.md 2026-08-04-001 — 시험 추가와 검출은 다른 것).
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]

TRANSLATOR_YAML = REPO / "src/Control/Motion_Control/Common/amr_motor_cmd_translator/config/amr_motor_cmd_translator_qd.yaml"
CAN_RELAY_YAML = REPO / "src/Comm/CAN/can_relay/config/can_relay.yaml"
MACHINE_YAML = REPO / "src/Comm/CAN/can_relay/config/machine/foil_a082.yaml"
TWOWS_PARAMS_DIR = REPO / "src/Control/Motion_Control/2WS/trnav_2ws_action_server/config"
CRAB_SRC = REPO / "src/Control/Motion_Control/2WS/trnav_2ws_kinematics/src/qd_crab_inverse_kinematics.cpp"
GEOMETRY_CANONICAL = REPO / "src/Control/Motion_Control/2WS/trnav_2ws_core/config/robot_geometry_2ws.yaml"
SEER_GATE_SRC = REPO / "Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h"

# 허용오차는 **대조 대상이 config 에 적힌 정밀도**로 정한다.
#   C1 조향: 양쪽 다 정수로 떨어진다(57,344.0) → 사실상 완전일치를 요구한다.
#   C2 구동: foil_a082.yaml:24 이 `24.447` 로 **5 유효숫자 반올림** 표기다. 정확한 재도출값은
#           24.44619… 이라 상대차 3.3e-5 가 항상 남는다. 1e-6 을 쓰면 표기 반올림을
#           불일치로 오탐한다. 1e-4 는 그 반올림을 흡수하면서, 이 검사기가 실제로 잡아야 할
#           크기(이식 잔재 −2.3% = 2.3e-2)보다 230배 작아 검출력을 잃지 않는다.
REL_TOL = 1e-6
DRIVE_REL_TOL = 1e-4


class Result:
    """검사 1건의 결과. `ok=None` 은 WARN(판정 보류, exit 코드 무영향)."""

    def __init__(self, cid: str, title: str, ok, detail: str):
        self.cid, self.title, self.ok, self.detail = cid, title, ok, detail

    @property
    def mark(self) -> str:
        return {True: "PASS", False: "FAIL", None: "WARN"}[self.ok]


def load_ros_params(path: Path) -> dict:
    """ROS2 파라미터 YAML 에서 `ros__parameters` 블록을 꺼낸다.

    최상위 키는 노드명(`amr_motor_cmd_translator`)일 수도 와일드카드(`/**`)일 수도 있어
    이름으로 찾지 않고 `ros__parameters` 를 가진 첫 매핑을 쓴다.
    """
    with path.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: 최상위가 매핑이 아니다")
    for value in doc.values():
        if isinstance(value, dict) and "ros__parameters" in value:
            return value["ros__parameters"]
    raise ValueError(f"{path}: ros__parameters 블록이 없다")


def close(a: float, b: float, rel_tol: float = REL_TOL) -> bool:
    return math.isclose(a, b, rel_tol=rel_tol)


# ── 검사 본체 (config 값만 받는다 — selftest 가 같은 함수를 합성 값으로 돌린다) ──

def check_steer_scale(tr: dict, machine: dict) -> Result:
    ppr = float(tr["pulses_per_rev"])
    gear = float(tr["gear_steer"])
    derived = ppr * gear / 360.0
    required = float(machine["steer_counts_per_deg"])
    ok = close(derived, required)
    detail = (f"translator {ppr:.0f}×{gear}/360 = {derived:,.1f} c/deg  vs  "
              f"machine steer_counts_per_deg = {required:,.1f}")
    if not ok:
        need = required * 360.0 / ppr
        detail += (f"\n         비 {required / derived:.4f} — "
                   f"gear_steer 를 {need:g} 로 하면 일치한다")
    return Result("C1", "조향 스케일", ok, detail)


def check_drive_scale(tr: dict, machine: dict) -> Result:
    r = float(tr["wheel_radius_m"])
    gear = float(tr["gear_walk"])
    derived = 60.0 * gear * 10.0 / (2.0 * math.pi * r) / 1000.0
    required = float(machine["drive_units_per_mmps"])
    ok = close(derived, required, DRIVE_REL_TOL)
    diff_pct = (derived / required - 1) * 100
    detail = (f"translator 60×{gear}×10/(2π×{r}) = {derived:.4f} u/(mm/s)  vs  "
              f"machine drive_units_per_mmps = {required:.4f}  (차 {diff_pct:+.3f}%, "
              f"허용 ±{DRIVE_REL_TOL * 100:.2f}%)")
    return Result("C2", "구동 스케일", ok, detail)


def check_motor_ids(tr: dict, relay: dict) -> Result:
    tr_drive = [int(tr["motor_id_walk_front"]), int(tr["motor_id_walk_rear"])]
    tr_steer = [int(tr["motor_id_steer_front"]), int(tr["motor_id_steer_rear"])]
    relay_drive = [int(n) for n in relay["drive_nodes"]]
    relay_steer = [int(n) for n in relay["steer_nodes"]]
    ok = tr_drive == relay_drive and tr_steer == relay_steer
    detail = (f"translator drive {tr_drive} steer {tr_steer}  vs  "
              f"can_relay drive {relay_drive} steer {relay_steer}")
    return Result("C3", "배선(motor_id)", ok, detail)


def read_mech_limit_deg(counts_per_deg: float):
    """호밍이 실측하는 **기구 −리밋**을 펌웨어 상수에서 되도출한다.

    호밍 방식은 Home 1(−리밋 탐색, `0x6098`=1 실기 판독)이라 매 호밍이 기계 한계를 때린다.
    리밋에서 위치가 0 으로 리셋되고, 그 뒤 0° 로 복귀하는 거리가 `SEER_HOME_ZERO_N*` 다.
    즉 그 상수 자체가 「−리밋 ↔ 직진」 거리이며 counts/도로 나누면 각도가 된다.
    근거: `docs/homing/2026-08-03-can-relay-homing-assets.md` §리밋 도달(10/10, DI bit3).
    """
    if not SEER_GATE_SRC.exists():
        return None, "펌웨어 헤더 없음"
    txt = SEER_GATE_SRC.read_text(encoding="utf-8", errors="replace")
    vals = [int(m) for m in re.findall(r"#define\s+SEER_HOME_ZERO_N\d+\s+(\d+)", txt)]
    if not vals:
        return None, "SEER_HOME_ZERO_N* 미검출"
    return min(vals) / counts_per_deg, f"SEER_HOME_ZERO min={min(vals):,}"


def spin_requirement_deg(geom: dict, offset_deg: float) -> float:
    """**제자리 스핀이 요구하는 raw 조향각** — 클램프가 이보다 작으면 스핀이 잘린다.

    inline 2WS 는 `y ≈ 0` 이라 제자리 회전(vx=vy=0)이 구조상 ±90° 근처를 요구한다:
        θ_spin = atan2(x_i, −y_i)
    translator 가 영점 오프셋을 빼므로 can_relay 가 보는 raw 는 그보다 |offset| 만큼 크다
    (+θ 쪽). 사용자 요구(2026-08-06): **스핀은 허용할 것.**
    """
    th = math.degrees(math.atan2(float(geom["w1_x"]), -float(geom["w1_y"])))
    return abs(abs(th) + abs(offset_deg))


def check_steer_limits(clamp_deg: float, bench_deg: float, wrap_margin_deg,
                       mech_limit_deg, mech_note: str, twows_limits: dict,
                       spin_req_deg=None) -> Result:
    """하류 클램프가 **상류 요구치 이상, 기구 한계 이하**인가.

        90° + WRAP_MARGIN  ≤  can_relay steer_limit_deg  ≤  기구 −리밋

    ±90° 는 여전히 **유일해 구속의 기준**이다(ADR(Architecture Decision Record)
    `docs/adr/2026-07-26-qd-ik-pm90-unique-solution.md`) — IK 정규화는 `normalizeAngle` 의
    `M_PI/2` 로 코드에 박혀 있고 본 검사는 그것을 바꾸지 않는다. 여기서 보는 것은 **클램프**다.

    하한 근거: 크랩은 90° 자세에서 path follow 여유가 필요해 `WRAP_MARGIN`(25°)까지 접지
    않는다(`qd_crab_inverse_kinematics.cpp:35`). 클램프가 그보다 작으면 그 여유를 잘라내고,
    잘리면 대안 해로 넘어가 **구동 부호 반전**(0.2 m/s·50 Hz 에서 2.0 g 계단)이 요구된다.
    상한 근거: 호밍이 매번 때리는 −리밋(`read_mech_limit_deg`).

    ⚠ 2WS `<action>_params.yaml` 의 같은 키는 **2WS 코드가 읽지 않아** 판정에 쓰지 않는다.
    """
    lower = 90.0 + (wrap_margin_deg if wrap_margin_deg is not None else 0.0)
    lines = [f"체인 {clamp_deg}° / 벤치 {bench_deg}°  (can_relay 실효값)"]
    ok = True
    if clamp_deg + 1e-9 < lower:
        ok = False
        lines.append(f"         ⚠ 하한 미달 — 크랩이 요구하는 {lower:.0f}° 보다 작다. "
                     f"보정 여유가 최대 {lower - clamp_deg:.0f}° 잘리고, 잘리면 구동 부호 반전이 걸린다")
    else:
        lines.append(f"         하한 {lower:.0f}° (90° + WRAP_MARGIN) 충족 — 크랩 보정 여유 보존")
    # 사용자 요구(2026-08-06) — 스핀은 허용할 것. WRAP_MARGIN 이 낮아져도 이 하한은 남는다.
    if spin_req_deg is not None:
        if clamp_deg + 1e-9 < spin_req_deg:
            ok = False
            lines.append(f"         ⚠ **스핀이 잘린다** — 제자리 회전은 raw {spin_req_deg:.2f}° 를 "
                         f"요구하는데 클램프가 {clamp_deg}° 다(요구: 스핀 허용)")
        else:
            lines.append(f"         스핀 요구 {spin_req_deg:.2f}° ≤ {clamp_deg}° — 제자리 회전 허용")
    if mech_limit_deg is None:
        lines.append(f"         ⚠ 기구 −리밋 미판정 ({mech_note}) — 상한 확인 불가")
    elif clamp_deg > mech_limit_deg + 1e-9:
        ok = False
        lines.append(f"         ⚠ 상한 초과 — 기구 −리밋 {mech_limit_deg:.1f}° 를 넘는다 ({mech_note})")
    else:
        lines.append(f"         상한 {mech_limit_deg:.1f}° (호밍 실측 −리밋, {mech_note}) 이내 "
                     f"— 여유 {mech_limit_deg - clamp_deg:.1f}°")
    # 벤치(사람이 손으로 넣는 경로)는 체인보다 넓으면 가드 의미가 없다.
    if bench_deg > clamp_deg + 1e-9:
        ok = False
        lines.append(f"         ⚠ 벤치 상한 {bench_deg}° 가 체인 {clamp_deg}° 보다 넓다 — "
                     f"사람이 넣는 경로가 더 열려 있으면 분리한 의미가 없다")
    else:
        lines.append(f"         벤치 {bench_deg}° ≤ 체인 {clamp_deg}° — 직접 지령 가드 유지")
    if twows_limits:
        lines.append(f"         (참고) 2WS <action>_params {len(twows_limits)}개 = "
                     f"{sorted(set(twows_limits.values()))} — 2WS 코드가 읽지 않는 키")
    return Result("C4", "조향 클램프 범위", ok, "\n".join(lines))


def check_2ws_geometry(canonical: dict, twows: dict, tol: float = 1e-9) -> list:
    """2WS `<action>_params.yaml` 9종의 기하가 **정본과 같은가**.

    실행 시 실제로 로드되는 것은 `<action>_params.yaml` 이고
    `trnav_2ws_core/config/robot_geometry_2ws.yaml`(정본)은 **어떤 launch 도 읽지 않는다**.
    그래서 값이 9곳에 복제된 채 정본과 갈라질 수 있다 — 실제로 Carrier AGV 값이 그렇게 남아
    휠베이스가 0.660 m(실측 1.200 m)로 들어가 있었다. 매 실행마다 다시 대조한다.
    """
    keys = ("w1_x", "w1_y", "w2_x", "w2_y", "wheel_radius", "gear_walk")
    results = []
    for name in sorted(twows):
        params = twows[name]
        bad = []
        for k in keys:
            if k not in params:
                bad.append(f"{k} 없음")
                continue
            if not close(float(params[k]), float(canonical[k]), tol) and \
                    abs(float(params[k]) - float(canonical[k])) > 1e-9:
                bad.append(f"{k} {params[k]} != {canonical[k]}")
        wb = abs(float(params.get("w1_x", 0)) - float(params.get("w2_x", 0)))
        detail = f"휠베이스 {wb:.3f} m" + ("  불일치: " + ", ".join(bad) if bad else "  정본 일치")
        results.append(Result(f"C6-{name.replace('_params.yaml','')}", "2WS 기하", not bad, detail))
    return results


def read_wrap_margin_deg(src: Path):
    """`constexpr double WRAP_MARGIN = 25.0 * M_PI / 180.0;` 에서 25.0 을 꺼낸다."""
    if not src.exists():
        return None
    m = re.search(r"WRAP_MARGIN\s*=\s*([0-9.]+)\s*\*\s*M_PI\s*/\s*180", src.read_text(encoding="utf-8"))
    return float(m.group(1)) if m else None


def collect_twows_params() -> dict:
    """`<action>_params.yaml` 전부의 `ros__parameters` 를 파일명으로 키잉해 돌려준다."""
    out = {}
    for path in sorted(TWOWS_PARAMS_DIR.glob("*_params.yaml")):
        try:
            out[path.name] = load_ros_params(path)
        except ValueError:
            continue
    return out


def collect_twows_limits(twows: dict) -> dict:
    return {n: float(p["steer_limit_deg"]) for n, p in twows.items() if "steer_limit_deg" in p}


def run_checks() -> list:
    tr = load_ros_params(TRANSLATOR_YAML)
    relay = load_ros_params(CAN_RELAY_YAML)
    machine = load_ros_params(MACHINE_YAML)
    twows = collect_twows_params()
    # 실효 클램프는 machine_file 이다 — launch 가 나중에 로드해 can_relay.yaml 을 덮는다
    # (`can_relay.launch.py:41-42`). fallback 값을 보면 죽은 값을 검사하게 된다.
    effective_clamp = float(machine.get("steer_limit_deg", relay["steer_limit_deg"]))
    effective_bench = float(machine.get("steer_limit_bench_deg",
                                        relay.get("steer_limit_bench_deg", effective_clamp)))
    mech_limit, mech_note = read_mech_limit_deg(float(machine["steer_counts_per_deg"]))
    try:
        spin_req = spin_requirement_deg(load_ros_params(GEOMETRY_CANONICAL),
                                        float(tr["steer_offset_front_deg"]))
    except (OSError, ValueError, KeyError):
        spin_req = None
    out = [
        check_steer_scale(tr, machine),
        check_drive_scale(tr, machine),
        check_motor_ids(tr, relay),
        check_steer_limits(effective_clamp, effective_bench, read_wrap_margin_deg(CRAB_SRC),
                           mech_limit, mech_note, collect_twows_limits(twows), spin_req),
    ]
    try:
        canonical = load_ros_params(GEOMETRY_CANONICAL)
        out += check_2ws_geometry(canonical, twows)
    except (OSError, ValueError) as exc:
        out.append(Result("C6", "2WS 기하", None, f"정본을 읽지 못했다 ({exc}) — 미판정"))
    return out


def report(results: list) -> int:
    fails = [r for r in results if r.ok is False]
    print("=== 모션→모터 체인 계약 대조 (config 재도출) ===")
    for r in results:
        print(f"[{r.mark}] {r.cid} {r.title}")
        for line in r.detail.splitlines():
            print(f"       {line.strip() if line.startswith('         ') else line}")
    print()
    if fails:
        print(f"불일치 {len(fails)}건 — {', '.join(r.cid for r in fails)}")
        return 1
    print("불일치 0건")
    return 0


# ── selftest: 검사기가 실제로 불일치를 잡는지 ──────────────────────────────

_BASE_TR = {
    "pulses_per_rev": 65536.0, "gear_steer": 315.0,
    "wheel_radius_m": 0.125, "gear_walk": 32.0,
    "motor_id_walk_front": 1, "motor_id_walk_rear": 2,
    "motor_id_steer_front": 3, "motor_id_steer_rear": 4,
}
# 실제 config 와 같은 **반올림 표기**를 쓴다 — 그래야 selftest 가 허용오차까지 함께 지킨다.
_BASE_MACHINE = {"steer_counts_per_deg": 57344.0, "drive_units_per_mmps": 24.447}
_BASE_RELAY = {"drive_nodes": [1, 2], "steer_nodes": [3, 4], "steer_limit_deg": 90.0}


_BASE_GEOM = {"w1_x": 0.6039, "w1_y": -0.0014, "w2_x": -0.5961, "w2_y": -0.0014,
              "wheel_radius": 0.125, "gear_walk": 32.0}


def _all(tr, machine, relay, limits, margin, clamp=115.0, mech=137.1, bench=90.0,
         spin_req=91.55):
    return {r.cid: r for r in [
        check_steer_scale(tr, machine), check_drive_scale(tr, machine),
        check_motor_ids(tr, relay),
        check_steer_limits(clamp, bench, margin, mech, "시험", limits, spin_req),
    ]}


def selftest() -> int:
    limits = {"a_params.yaml": 90.0}
    cases = []

    base = _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, limits, 0.0)
    for cid in ("C1", "C2", "C3", "C4"):
        cases.append((f"정상 config → {cid} PASS", base[cid].ok is True))

    mut = dict(_BASE_TR, gear_steer=265.5)
    cases.append(("gear_steer 265.5 → C1 FAIL", _all(mut, _BASE_MACHINE, _BASE_RELAY, limits, 0.0)["C1"].ok is False))

    mut = dict(_BASE_TR, wheel_radius_m=0.08)
    cases.append(("wheel_radius 0.08 → C2 FAIL", _all(mut, _BASE_MACHINE, _BASE_RELAY, limits, 0.0)["C2"].ok is False))

    mut = dict(_BASE_TR, gear_walk=20.0)
    cases.append(("gear_walk 20.0 → C2 FAIL", _all(mut, _BASE_MACHINE, _BASE_RELAY, limits, 0.0)["C2"].ok is False))

    # 허용오차 경계: 표기 반올림은 통과시키고, 검출 대상 크기는 잡아야 한다.
    cases.append(("표기 반올림 24.447 vs 24.4462 → C2 PASS",
                  _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, limits, 0.0)["C2"].ok is True))
    near = dict(_BASE_MACHINE, drive_units_per_mmps=24.447 * 1.001)   # 0.1% — 반올림보다 30배 큼
    cases.append(("0.1% 어긋남 → C2 FAIL",
                  _all(_BASE_TR, near, _BASE_RELAY, limits, 0.0)["C2"].ok is False))

    mut = dict(_BASE_TR, motor_id_steer_front=4, motor_id_steer_rear=3)
    cases.append(("steer id 뒤바뀜 → C3 FAIL", _all(mut, _BASE_MACHINE, _BASE_RELAY, limits, 0.0)["C3"].ok is False))

    # C4 는 **범위 불변식**이다: 90°+WRAP_MARGIN ≤ clamp ≤ 기구 −리밋.
    # 2WS params 의 같은 키는 코드가 읽지 않으므로 그 값이 뭐든 판정이 흔들리면 안 된다.
    cases.append(("2WS 한계 130° 여도 → C4 PASS (죽은 키)",
                  _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, {"a.yaml": 130.0}, 25.0)["C4"].ok is True))

    r = _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, limits, 25.0, clamp=115.0)["C4"]
    cases.append(("clamp 115 · margin 25 · 리밋 137 → C4 PASS", r.ok is True))

    r = _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, limits, 25.0, clamp=90.0)["C4"]
    cases.append(("clamp 90 (크랩 여유 잘림) → C4 FAIL", r.ok is False))
    cases.append(("하한 미달 시 부호반전 경고 포함", "부호 반전" in r.detail))

    r = _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, limits, 25.0, clamp=140.0)["C4"]
    cases.append(("clamp 140 (기구 −리밋 초과) → C4 FAIL", r.ok is False))

    r = _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, limits, 25.0, clamp=115.0, mech=None)["C4"]
    cases.append(("기구 −리밋 미검출 → 상한 미판정 고지", "미판정" in r.detail))

    r = _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, limits, 25.0, clamp=115.0, bench=90.0)["C4"]
    cases.append(("벤치 90 ≤ 체인 115 → C4 PASS", r.ok is True))
    r = _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, limits, 25.0, clamp=115.0, bench=130.0)["C4"]
    cases.append(("벤치가 체인보다 넓으면 → C4 FAIL", r.ok is False))

    # 스핀 허용 요구 — WRAP_MARGIN 이 0 이어도 이 하한은 남아야 한다.
    r = _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, limits, 0.0, clamp=91.0)["C4"]
    cases.append(("clamp 91 < 스핀 요구 91.55 → C4 FAIL", r.ok is False))
    cases.append(("스핀 잘림 경고 문구 포함", "스핀이 잘린다" in r.detail))
    r = _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, limits, 0.0, clamp=92.0)["C4"]
    cases.append(("clamp 92 ≥ 스핀 요구 → C4 PASS", r.ok is True))
    g = {"w1_x": 0.6039, "w1_y": -0.0014}
    cases.append(("스핀 요구 = |atan2(x,−y)| + |offset|",
                  abs(spin_requirement_deg(g, -1.676) - 91.546) < 0.01))

    # C6 — 2WS 기하 ↔ 정본
    ok6 = check_2ws_geometry(_BASE_GEOM, {"a_params.yaml": dict(_BASE_GEOM)})
    cases.append(("정본과 같으면 → C6 PASS", ok6[0].ok is True))

    bad6 = check_2ws_geometry(_BASE_GEOM, {"a_params.yaml": dict(_BASE_GEOM, w1_x=0.330)})
    cases.append(("w1_x 0.330(Carrier AGV) → C6 FAIL", bad6[0].ok is False))
    cases.append(("C6 실패 시 휠베이스 표시", "휠베이스" in bad6[0].detail))

    r6 = check_2ws_geometry(_BASE_GEOM, {"a_params.yaml": dict(_BASE_GEOM, wheel_radius=0.080)})
    cases.append(("wheel_radius 0.080 → C6 FAIL", r6[0].ok is False))

    miss = dict(_BASE_GEOM); miss.pop("gear_walk")
    cases.append(("키 누락 → C6 FAIL",
                  check_2ws_geometry(_BASE_GEOM, {"a_params.yaml": miss})[0].ok is False))

    print("=== selftest (검출력 회귀) ===")
    bad = 0
    for name, ok in cases:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        bad += 0 if ok else 1
    print()
    print(f"{len(cases)}건 중 {len(cases) - bad}건 통과")
    return 1 if bad else 0


# ── C5: Seer 실측 캡처와의 대조 (독립 계측기) ──────────────────────────────

def check_against_seer_capture(path: Path, machine: dict, tol_deg: float = 0.01) -> list:
    """`orin_steer_crosscheck.py` 캡처로 **원점·스케일·부호를 동시에** 확인한다.

    캡처는 판다 SAFETY_SILENT passthrough(제어권 미취득, CAN 송신 0)에서 CAN `0x6064` 와
    Seer API 1040 각도를 동시 기록한 것이라 두 경로가 독립이다.

    대조식 — can_relay 가 수정 후 상류로 올리는 값:

        fb_pos = 0x6064 − steer_home_counts        (홈 기준 상대 counts)
        보고각 = fb_pos / steer_counts_per_deg × direction_steer   (translator 가 곱함)

    CAN counts 와 Seer 각도는 **음의 상관**이므로(foil_a082.yaml:55-61) `direction_steer = −1`
    이 맞다면 보고각이 Seer 각도와 같아야 한다. 로봇을 움직이지 않고 확인한다.
    """
    import json
    import statistics

    homes = machine["steer_home_counts"]
    nodes = [int(n) for n in machine.get("steer_nodes", [3, 4])]
    home = {n: int(c) for n, c in zip(nodes, homes)}
    cpd = float(machine["steer_counts_per_deg"])

    by = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        by.setdefault((d["src"], int(d["node"])), []).append(float(d["value"]))

    results = []
    for n in nodes:
        seer, can = by.get(("seer", n)), by.get(("can", n))
        if not seer or not can:
            results.append(Result(f"C5-{n}", f"Seer 대조 node{n}", None,
                                  f"캡처에 자료 부족 (seer={len(seer or [])} can={len(can or [])}) — 미판정"))
            continue
        s_deg = statistics.median(seer)
        c = statistics.median(can)
        fb = c - home[n]
        reported = -(fb / cpd)          # direction_steer = −1
        diff = reported - s_deg
        ok = abs(diff) <= tol_deg
        naive = c / cpd                 # 원점을 빼지 않았다면 상류가 읽었을 각
        results.append(Result(
            f"C5-{n}", f"Seer 대조 node{n}", ok,
            f"Seer {s_deg:+.6f}°  vs  보고 {reported:+.6f}° (fb_pos {fb:+,}c)  차 {diff:+.6f}° "
            f"(허용 ±{tol_deg}°)\n         원점 미적용이었다면 {naive:,.2f}° 로 읽혔다"))
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="모션→모터 체인 계약 대조")
    ap.add_argument("--selftest", action="store_true", help="검사기 자체의 검출력 회귀")
    ap.add_argument("--seer-capture", metavar="JSONL",
                    help="orin_steer_crosscheck 캡처로 원점·스케일·부호 동시 대조(C5)")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    results = run_checks()
    if args.seer_capture:
        results += check_against_seer_capture(Path(args.seer_capture),
                                              load_ros_params(MACHINE_YAML))
    return report(results)


if __name__ == "__main__":
    sys.exit(main())
