#!/usr/bin/env python3
"""turn 의 각도 계상이 **세 곳 모두 방향을 보는지** 소스에서 재도출한다.

`turn` 은 목표 진행량을 IMU(Inertial Measurement Unit) yaw 델타 누적으로 재며, 계상 지점이
**세 곳**이다 — 주 루프 · 정착 블록 · 미세보정 루프. 셋 중 하나라도 `std::abs(delta)` 로
방향을 무시하면 **역방향 잡음 델타까지 전진으로 계상**되어 편향이 한 방향으로만 쌓이고,
결과적으로 「덜 돌았는데 다 돌았다」가 된다.

2026-08-06 SIL 실측(목표 45° · R=1.0 m · 관성 0.6 s · IMU yaw 잡음 0.05° 1σ):

    주 루프 std::abs (종전)   실제오차 평균 −0.536° · |최대| 0.846° · σ 0.221°
    주 루프 부호 반영 (현행)   실제오차 평균 −0.211° · |최대| 0.298° · σ 0.065°

종전은 미세보정 임계 0.3° 를 **원리적으로 달성할 수 없었다**. 무잡음·즉응 플랜트에서는
측정오차가 정확히 0.000° 라 이 결함이 보이지 않는다 — **시험이 통과해도 근거가 아니다.**
그래서 소스 앵커로 고정한다.

⚠ 이 검사기는 **부호 처리 유무만** 본다. 정확도 자체는 실행으로 재야 한다:
   `Tools/motion_chain_check/turn_residual_probe.py`

사용:
    python3 Tools/motion_chain_check/turn_angle_accounting_check.py
    python3 Tools/motion_chain_check/turn_angle_accounting_check.py --selftest
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TURN = REPO / "src/Control/Motion_Control/2WS/trnav_2ws_action_server/src/turn/turn_action_server.cpp"

# 계상 문장: `accumulated_angle += …` / `-= …`
ACC = re.compile(r"accumulated_angle\s*(\+=|-=)\s*(.+?);")


def classify(expr: str, guarded_by_sign: bool) -> str:
    """한 계상 문장이 방향을 보는지 판정.

    두 형태를 모두 인정한다(수학적으로 동일):
      ① `+= sign * delta_deg`                       — 부호를 곱해 직접 반영
      ② `if (sign * delta_deg > 0) += |d|; else -= |d|` — if/else 로 분기
    """
    if "sign" in expr:
        return "부호반영(곱)"
    if guarded_by_sign:
        return "부호반영(분기)"
    if "std::abs" in expr or "fabs" in expr:
        return "**방향무시**"
    return "판정불가"


def scan(path: Path) -> list:
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for i, line in enumerate(lines):
        m = ACC.search(line)
        if not m:
            continue
        # 이 문장을 감싼 가장 가까운 위쪽 12줄 안에 `sign * … > 0` 분기가 있는가
        window = "\n".join(lines[max(0, i - 12):i])
        guarded = re.search(r"sign\s*\*\s*\w+\s*>\s*0", window) is not None
        out.append({
            "line": i + 1,
            "expr": m.group(0).strip(),
            "verdict": classify(m.group(2), guarded),
        })
    return out


def report(target: Path | None = None) -> int:
    path = target or TURN
    if not path.exists():
        print(f"대상 없음: {path}", file=sys.stderr)
        return 2

    sites = scan(path)
    rel = path.relative_to(REPO) if REPO in path.parents else path
    print("=== turn 각도 계상 지점 — 방향 판정 여부 ===\n")
    print(f"  대상: {rel}\n")
    bad = 0
    for s in sites:
        mark = "OK  " if s["verdict"].startswith("부호반영") else "FAIL"
        if mark == "FAIL":
            bad += 1
        print(f"  [{mark}] :{s['line']:<4} {s['verdict']:<14} {s['expr']}")

    print()
    # 논리 지점은 3곳(주 루프·정착·미세보정)이나, if/else 분기형은 `+=`·`-=` 두 문장이
    # 되므로 문장 수는 3~5 가 정상이다. 그보다 적으면 구조가 바뀐 것이다.
    if len(sites) < 3:
        print(f"⚠ 계상 문장이 {len(sites)}개다 — 최소 3개(주 루프·정착·미세보정)를 기대했다.")
        print("  구조가 바뀌었다면 본 검사기의 기대치를 함께 갱신할 것.")
        bad += 1

    if bad:
        print(f"✗ 방향을 무시하는 계상 {bad}건 — 잡음이 한 방향 편향을 만든다.")
        print("  실측: 잡음 0.05° 1σ 에서 실제오차 |최대| 0.846° (임계 0.3° 초과).")
        print("  정확도 재측정: Tools/motion_chain_check/turn_residual_probe.py")
        return 1

    print(f"✓ 계상 {len(sites)}곳 모두 방향을 본다.")
    print("  ※ 본 검사는 **부호 처리 유무**만 본다 — 정확도는 turn_residual_probe.py 로 잰다.")
    return 0


def selftest() -> int:
    """판정 규칙을 합성 입력으로 고정한다(저장소 상태와 무관)."""
    cases = [
        ("곱 형태를 부호반영으로 본다",
         classify("sign * delta_deg", False) == "부호반영(곱)"),
        ("분기 안의 std::abs 를 부호반영으로 본다",
         classify("std::abs(delta_deg)", True) == "부호반영(분기)"),
        ("분기 없는 std::abs 를 방향무시로 본다",
         classify("std::abs(delta_yaw) * 180.0 / M_PI", False) == "**방향무시**"),
        ("fabs 도 방향무시로 본다",
         classify("std::fabs(delta_yaw)", False) == "**방향무시**"),
        ("정규식이 += 와 -= 를 모두 잡는다",
         bool(ACC.search("accumulated_angle -= std::abs(delta_deg);"))
         and bool(ACC.search("accumulated_angle += sign * delta_deg;"))),
    ]
    print("=== selftest ===")
    bad = 0
    for n, ok in cases:
        print(f"[{'PASS' if ok else 'FAIL'}] {n}")
        bad += 0 if ok else 1
    print(f"\n{len(cases)-bad}/{len(cases)} 통과")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="turn 각도 계상 방향 판정 재도출")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--path", type=Path, default=None,
                    help="다른 파일을 검사한다. 검출력 확인용 — QD 상류를 지정하면 "
                         "종전 형태가 남아 있어 exit 1 이 나와야 한다")
    a = ap.parse_args()
    return selftest() if a.selftest else report(a.path)


if __name__ == "__main__":
    sys.exit(main())
