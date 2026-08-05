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


def check_steer_limits(relay_limit: float, twows_limits: dict, wrap_margin_deg) -> Result:
    """can_relay 클램프 한계와 2WS 상한이 같은 값인지.

    ±90° 는 하드웨어 한계가 아니라 **유일해(canonical) 구속**이다 — 독립조향 바퀴는
    `(θ,+v) ≡ (θ∓180°,−v)` 로 항상 등가해가 2개라, 반원(180° 폭)으로 정규화해야 지령이
    비결정·chattering 을 일으키지 않는다(ADR `docs/adr/2026-07-26-qd-ik-pm90-unique-solution.md`,
    `config/machine/foil_a082.yaml:162-166` 「±90° 로 묶어 이중해를 없앤다(합의)」).

    크랩 `wrapSteer` 의 `WRAP_MARGIN`(25°)은 결함이 아니라 **경계 chattering 회피 히스테리시스**다.
    그 주석 자체가 「motor saturate 로 robot 진행은 거의 정확」이라 적어 **하류 포화를 전제**한다
    (`qd_crab_inverse_kinematics.cpp:20-35`). 즉 can_relay 의 ±90° 클램프는 크랩 설계가
    가정하는 동작이므로 **경고 대상이 아니다** — 마진 값만 정보로 표시한다.
    """
    mismatched = {name: v for name, v in twows_limits.items() if not close(v, relay_limit)}
    lines = [f"can_relay steer_limit_deg = {relay_limit}  vs  2WS <action>_params {len(twows_limits)}개"]
    if mismatched:
        for name, v in sorted(mismatched.items()):
            lines.append(f"         불일치 {name}: {v}")
    else:
        lines.append(f"         전부 일치 ({relay_limit})")
    if wrap_margin_deg is not None:
        lines.append(f"         (참고) 크랩 wrapSteer 히스테리시스 마진 {wrap_margin_deg:.0f}° "
                     f"→ wrap 임계 {90.0 + wrap_margin_deg:.0f}°. 경계 chattering 회피용이며 "
                     f"하류 ±{relay_limit:.0f}° 포화를 전제한 설계다(결함 아님)")
    else:
        lines.append("         (참고) WRAP_MARGIN 을 소스에서 읽지 못했다 — 마진 값 미표시")
    return Result("C4", "조향 한계", not mismatched, "\n".join(lines))


def read_wrap_margin_deg(src: Path):
    """`constexpr double WRAP_MARGIN = 25.0 * M_PI / 180.0;` 에서 25.0 을 꺼낸다."""
    if not src.exists():
        return None
    m = re.search(r"WRAP_MARGIN\s*=\s*([0-9.]+)\s*\*\s*M_PI\s*/\s*180", src.read_text(encoding="utf-8"))
    return float(m.group(1)) if m else None


def collect_twows_limits() -> dict:
    out = {}
    for path in sorted(TWOWS_PARAMS_DIR.glob("*_params.yaml")):
        try:
            params = load_ros_params(path)
        except ValueError:
            continue
        if "steer_limit_deg" in params:
            out[path.name] = float(params["steer_limit_deg"])
    return out


def run_checks() -> list:
    tr = load_ros_params(TRANSLATOR_YAML)
    relay = load_ros_params(CAN_RELAY_YAML)
    machine = load_ros_params(MACHINE_YAML)
    return [
        check_steer_scale(tr, machine),
        check_drive_scale(tr, machine),
        check_motor_ids(tr, relay),
        check_steer_limits(float(relay["steer_limit_deg"]), collect_twows_limits(),
                           read_wrap_margin_deg(CRAB_SRC)),
    ]


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


def _all(tr, machine, relay, limits, margin):
    return {r.cid: r for r in [
        check_steer_scale(tr, machine), check_drive_scale(tr, machine),
        check_motor_ids(tr, relay), check_steer_limits(relay["steer_limit_deg"], limits, margin),
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

    cases.append(("2WS 한계 130° → C4 FAIL",
                  _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, {"a.yaml": 130.0}, 0.0)["C4"].ok is False))

    r = _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, limits, 25.0)["C4"]
    cases.append(("WRAP_MARGIN 25° → C4 마진 정보 표시", "wrap 임계 115" in r.detail))

    r = _all(_BASE_TR, _BASE_MACHINE, _BASE_RELAY, limits, None)["C4"]
    cases.append(("WRAP_MARGIN 미검출 → 미표시 고지", "미표시" in r.detail))

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
