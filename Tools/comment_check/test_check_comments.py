#!/usr/bin/env python3
"""check_comments.py 회귀 테스트.

임시 저장소를 만들어 **잡아야 하는 것**과 **잡으면 안 되는 것**을 각각 넣고 대조한다.
잡으면 안 되는 쪽(오탐 사례)은 전부 2WS 실측에서 나온 것이다 — 단위 환산·유효숫자·범위
표현·멤버변수 접두를 값 불일치로 오독했던 실제 사례들이라, 여기서 고정해 재발을 막는다.

실행:  python3 Tools/comment_check/test_check_comments.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_comments.py")

# (파일 상대경로, 내용)
FIXTURES = [
    ("docs/real.md", "line1\nline2\nline3\n"),
    ("src/pkg/config/params.yaml", "\n".join([
        "/**:",
        "  ros__parameters:",
        "    # ── Platform (trnav_2ws_core::loadGeometry) ──",   # 심볼 부재 → 검출
        "    wheelbase: 1.1974   # m (1197.4 mm)",               # 단위 환산 → 통과
        "    lookahead: 0.6      # m — 종점 연장 (lookahead+0.2 m)",  # 증분 → 통과
        "    limit_deg: 115.0    # ±115°",                       # 일치 → 통과
        "    stale: 90.0         # ±20°",                        # 불일치 → 검출
        "",
    ])),
    ("src/pkg/src/thing.cpp", "\n".join([
        '#include "pkg/msg/wheel_motor.hpp"  // state feedback only',  # include 경로 → 통과
        "// 근거: docs/real.md:2",                                # 실재 앵커 → 통과
        "// 근거: docs/real.md:99",                               # 줄 초과 → 검출
        "// 근거: docs/gone/plan.md",                             # 경로 부재 → 검출",
        "// jump 관련: prev_jump_* 는 mutex 보호",                 # 멤버 접두(파라미터 문맥 없음) → 통과
        "// yaml 키는 ghost_prefix_* 다",                          # 파라미터 문맥 + 부재 접두 → 검출
        "constexpr double kMargin = 25.0 * M_PI / 180.0;  // 25°",       # 라디안↔도 → 통과
        "constexpr double kBad = 25.0 * M_PI / 180.0;  // 20°",          # 불일치 → 검출
        "constexpr double kEps = M_PI / 2.0 - 0.001;  // ~89.94 deg",    # 유효숫자 → 통과",
        "constexpr double kBand = 8.0;  // 3° 와 15° 사이",              # 범위 → 통과
        "// 위치가 틀린 인용: docs/WRONG/params.yaml",            # basename 만 같음 → 검출
        "// 실재 접미 인용: pkg/config/params.yaml",              # 경로 접미 일치 → 통과
        "// 예시 인용: docs/GONE/suppressed.md  (comment-check: ignore)",  # 억제 마커 → 통과
        "",
    ])),
    ("src/pkg/include/real.hpp", "\n".join([
        "namespace RealNs {",
        "void realFunc();",
        "}",
        "",
    ])),
    ("src/pkg/src/scope.cpp", "\n".join([
        "// 올바른 소속: RealNs::realFunc",          # 스코프 일치 → 통과
        "// 틀린 소속: WrongNs::realFunc",           # 이름은 있으나 소속 틀림 → 검출
        "// 종전에는 다른 값을 썼다",                 # 이력 서술 → history 로만 검출
        "",
    ])),
    ("src/pkg/src/codex_cases.cpp", "\n".join([
        "constexpr double kSign = 10.0;  // -10 m",            # 부호 반영 → 검출
        "constexpr double kHex = 0x10;  // 15 m",              # 16진수 평가 → 검출
        "constexpr double kSuf = 1.0L;  // 2 m",               # L 접미사 평가 → 검출
        "constexpr double kSup = 10.0;  // 기준값 999 m",       # 「기준」이 억제하면 안 됨 → 검출
        "constexpr double kInc = 0.6;  // lookahead+0.2 m",    # 증분식은 여전히 통과
        "/* first */ int x; /* docs/GONE/second.md */",        # 한 줄 두 번째 블록 주석 → 검출
        "",
    ])),
    ("src/pkg/pkg.xml", "\n".join([
        "<package>",
        "  <description>",
        "  docs/GONE/multiline.md",
        "  </description>",
        "</package>",
        "",
    ])),
    ("src/pkg/scripts/node.py", "\n".join([
        'label = "값 # docs/GONE/instr.md"',            # 문자열 안의 # → 통과 (주석 아님)
        'sep = "#"  # 진짜 주석: docs/GONE/real.md',     # 문자열 뒤의 진짜 주석 → 검출
        "",
    ])),
]

# (검사종류, 파일, 기대 문구 일부)
MUST_FLAG = [
    ("symbol", "params.yaml", "loadGeometry"),
    ("const", "params.yaml", "±20°"),
    ("anchor", "thing.cpp", "줄 범위 초과"),
    ("path", "thing.cpp", "docs/gone/plan.md"),
    ("symbol", "thing.cpp", "ghost_prefix_*"),
    ("const", "thing.cpp", "20°"),
    ("path", "thing.cpp", "docs/WRONG/params.yaml"),
    ("path", "node.py", "docs/GONE/real.md"),
    ("symbol", "scope.cpp", "WrongNs::realFunc"),
    ("const", "codex_cases.cpp", "-10m"),
    ("const", "codex_cases.cpp", "15m"),
    ("const", "codex_cases.cpp", "2m"),
    ("const", "codex_cases.cpp", "999m"),
    ("path", "codex_cases.cpp", "docs/GONE/second.md"),
    ("path", "pkg.xml", "docs/GONE/multiline.md"),
]
# 이 파일:줄 조합은 절대 나오면 안 된다 (오탐 고정)
MUST_NOT_FLAG_SNIPPETS = [
    "1197.4", "lookahead+0.2", "±115", "89.94", "3° 와 15°",
    "prev_jump_*", "wheel_motor.hpp", "docs/real.md:2",
    "docs/GONE/instr.md", "pkg/config/params.yaml", "RealNs::realFunc",
    "lookahead+0.2", "docs/GONE/suppressed.md",
]


def build_repo(root: str) -> None:
    for rel, body in FIXTURES:
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)


def main() -> int:
    with tempfile.TemporaryDirectory() as root:
        build_repo(root)
        r = subprocess.run(
            [sys.executable, CHECKER, os.path.join(root, "src"), "--repo-root", root],
            capture_output=True, text=True)
        out = r.stdout + r.stderr

    failures: list[str] = []
    for check, fname, needle in MUST_FLAG:
        hit = any(fname in ln and f"[{check}]" in ln for ln in out.splitlines()) and needle in out
        if not hit:
            failures.append(f"검출 실패: [{check}] {fname} — {needle!r}")
    for snip in MUST_NOT_FLAG_SNIPPETS:
        for ln in out.splitlines():
            # 파일 컬럼(`src/…:12  [check] `)이 아니라 **판정 사유**만 본다 —
            # 리포트된 파일 경로를 「플래그된 경로」로 오인하지 않기 위해서다.
            m = re.search(r"\[(?:const|symbol|path|anchor)\]\s*(?P<detail>.*)$", ln)
            if m and snip in m.group("detail"):
                failures.append(f"오탐: {snip!r} 가 플래그됨 — {ln.strip()[:110]}")
                break

    # history 는 기본 미포함이므로 별도 실행으로 확인한다.
    with tempfile.TemporaryDirectory() as root2:
        build_repo(root2)
        r2 = subprocess.run(
            [sys.executable, CHECKER, os.path.join(root2, "src"), "--repo-root", root2,
             "--checks", "history"], capture_output=True, text=True)
        hout = r2.stdout + r2.stderr
    if "[history]" not in hout or "종전" not in hout:
        failures.append("검출 실패: [history] scope.cpp — '종전'")
    if "[history]" in out:
        failures.append("history 가 기본 검사에 포함됐다 — 옵트인이어야 한다")

    print(out.rstrip())
    print("-" * 60)
    if failures:
        for f in failures:
            print("  ✗", f)
        print(f"\nFAILED — {len(failures)}건")
        return 1
    print(f"PASSED — 검출 {len(MUST_FLAG)}종 · 오탐 고정 {len(MUST_NOT_FLAG_SNIPPETS)}종")
    return 0


if __name__ == "__main__":
    sys.exit(main())
