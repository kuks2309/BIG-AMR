#!/usr/bin/env python3
"""세션 브랜치가 **이미 추월당했는지** 판정한다 — 병합 전 필수 게이트.

## 왜 필요한가 (2026-08-06-001)

`session/520bf3ab` 4커밋을 병합하려다 충돌 4파일을 만났다. 그때 나는 **주석 문구를
비교해서** "내 브랜치는 호밍 취소 가능 / origin 은 불가"라는 대립을 만들고 사용자에게
승인을 요청했다. 실제로는 **공유 워킹트리에 이미 `cancel_home()` 이 구현돼 있었고**
시험도 5개 대 14개로 저쪽이 앞서 있었다. 병합했으면 시험 9개와 줄번호 정정이 사라졌다.

두 가지가 틀렸다:
  ① 비교 대상을 `origin/main` 하나로 한정했다 — 공유 워킹트리·타 세션 작업을 안 봤다.
  ② 구현 여부를 **주석으로** 판단했다. `def cancel_home` 이 있는지는 정의를 보면 끝난다.

이 도구는 그 둘을 기계로 막는다:
  · 비교 기준을 **공유 워킹트리**로 둔다(원격 브랜치가 아니라 실제로 사람이 읽는 트리).
  · `.py` 는 **정의된 심볼 집합**(ast)으로 비교한다 — 주석·docstring 은 보지 않는다.

## 사용

    python3 Tools/repo_tools/branch_superseded.py <branch> [--tree <공유트리경로>]

종료코드
    0  미사용. 확인: `grep -cE '^\s*return 0' Tools/repo_tools/branch_superseded.py` → 0
    1  **사람 확인 필요** — 세 경우 모두 여기로 온다:
         · 추월당함(브랜치 전용 파일·심볼 0 + 공유트리 전용 심볼 존재)
         · 고유 내용 미확인(심볼 차이 없음 — 본문만 다름)
         · 미정(브랜치 전용 심볼 존재 — 개명·의도적 제거일 수 있음)
    2  실행 오류

⚠ **이 도구는 「병합해도 된다」를 말하지 않는다.** 심볼 차이만으로는 「아직 안 옮겨진
자산」과 「공유트리가 의도적으로 제거한 것」을 구분할 수 없기 때문이다(§판정 주석의
`halt_steer` 사례). 출력은 **읽어야 할 지점의 목록**이며 판정은 사람이 한다.
"""
from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys


def git(*args: str, cwd: str | None = None) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} → {r.stderr.strip()}")
    return r.stdout


def symbols(src: str) -> set[str]:
    """정의된 최상위·클래스 내 심볼 이름 집합. **주석·docstring 은 무시된다.**"""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
    return out


def read_branch(repo: str, branch: str, path: str) -> str | None:
    try:
        return git("show", f"{branch}:{path}", cwd=repo)
    except RuntimeError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("branch")
    ap.add_argument("--tree", default=None,
                    help="공유 워킹트리 경로(기본: 현재 저장소 최상위)")
    ap.add_argument("--base", default="origin/main")
    a = ap.parse_args()

    repo = git("rev-parse", "--show-toplevel").strip()
    tree = os.path.abspath(a.tree) if a.tree else repo

    try:
        changed = [p for p in git("diff", "--name-only",
                                  f"{a.base}...{a.branch}", cwd=repo).split("\n") if p]
    except RuntimeError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2
    if not changed:
        print("브랜치가 base 대비 바꾼 파일이 없다.")
        return 1

    only_branch: list[str] = []      # 공유트리에 아예 없는 파일 = 병합 가치
    tree_ahead: list[tuple[str, list[str]]] = []   # 공유트리에만 있는 심볼
    branch_ahead: list[tuple[str, list[str]]] = []  # 브랜치에만 있는 심볼
    same = 0

    for p in changed:
        fs = os.path.join(tree, p)
        if not os.path.exists(fs):
            only_branch.append(p)
            continue
        b = read_branch(repo, a.branch, p)
        if b is None:
            continue
        try:
            t = open(fs, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        if b == t:
            same += 1
            continue
        if p.endswith(".py"):
            sb, st = symbols(b), symbols(t)
            if st - sb:
                tree_ahead.append((p, sorted(st - sb)))
            if sb - st:
                branch_ahead.append((p, sorted(sb - st)))

    print(f"브랜치 {a.branch} — base {a.base} 대비 {len(changed)}파일 변경")
    print(f"  공유트리와 동일        : {same}")
    print(f"  공유트리에 없음(전용)  : {len(only_branch)}")
    for p in only_branch:
        print(f"      + {p}")
    print(f"  공유트리에만 있는 심볼 : {len(tree_ahead)}파일")
    for p, s in tree_ahead:
        print(f"      ▲ {p}: {', '.join(s[:8])}{' …' if len(s) > 8 else ''}")
    print(f"  브랜치에만 있는 심볼   : {len(branch_ahead)}파일")
    for p, s in branch_ahead:
        print(f"      ▼ {p}: {', '.join(s[:8])}{' …' if len(s) > 8 else ''}")

    # ── 판정 ─────────────────────────────────────────────────────────────
    # ⚠ **「브랜치 전용 심볼 = 병합 가치」로 단정하지 않는다.**
    #   2026-08-06 실사례: 폐기한 브랜치의 전용 심볼 `halt_steer` 는 공유트리에서
    #   `release_steer_target` 으로 **개명 + 거동 반전**된 것이었다(실측 위치를
    #   `0x607A` 로 써넣어 축을 붙들던 동작을 **의도적으로 제거**한 것이다. 사유는
    #   ① 벤더 Handbook V7.0 `:8467-8469` 와 상류 `can_open.hpp:36-37,468-469` 는 정지를
    #      `0x6040` 으로 내고, 마스터 캡처 253,510 프레임에 `0x03`·`0x05` 0회
    #      (집계 `Tools/docking_field_kit/master_command_census.py`) — 그 범위에서 이 방식은
    #      확인되지 않았다,
    #   ② engage 직후 위치 0 구간(실측 132 ms)에 걸리면 축을 +69.3° 돌리는 통로였다.
    #   근거 `backend.py` `release_steer_target` docstring · `docs/claude-mistake/2026-08-05-001`).
    #   그 전용 시험 3건을 「고유 자산」이라고 옮겼다면 **제거된 위험 거동을 되살리라고
    #   강제하는 시험**을 심었을 것이다.
    #   ⇒ 심볼 차이는 **「사람이 구현을 읽어야 하는 지점」의 목록**이지 판정이 아니다.
    if not only_branch and not branch_ahead and tree_ahead:
        print("\n판정: **추월당했다** — 브랜치 전용 파일·심볼이 없고 "
              "공유트리에만 있는 심볼이 존재한다.")
        print("      병합하면 공유트리 쪽 구현이 사라질 수 있다.")
        return 1
    if not only_branch and not branch_ahead:
        print("\n판정: 브랜치 고유 내용이 확인되지 않는다(심볼 기준). "
              "본문 변경만 있는지 diff 로 확인할 것.")
        return 1
    print("\n판정: **미정 — 사람이 확인해야 한다.**")
    print("      브랜치 전용 파일·심볼이 있으나, 그것이 「아직 안 옮겨진 자산」인지")
    print("      「공유트리가 의도적으로 제거·개명한 것」인지 이 도구는 구분하지 못한다.")
    print("      위 ▼ 목록의 각 심볼에 대해 **공유트리 구현을 직접 읽고** 판단할 것")
    print("      (개명 흔적은 보통 새 함수 docstring 의 「옛 이름 …」에 남는다).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
