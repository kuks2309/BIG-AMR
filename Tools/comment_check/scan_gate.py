#!/usr/bin/env python3
"""이미 들어가 있는 주석을 게이트 규칙으로 전수 훑는다.

훅 `coding-comment-gate.py` 는 **이번에 추가된 텍스트만** 본다. 그래서 규칙이 생기기 전에
들어간 주석이나 다른 경로로 들어온 주석은 아무도 훑지 않는다 — 이 도구가 그 구멍을 메운다.

판정 규칙은 **훅에서 직접 불러 쓴다.** 패턴을 복사해 두면 훅이 바뀌는 순간 조용히 어긋나고,
그때부터 이 도구는 「통과」를 근거로 쓸 수 없게 된다.

    python3 Tools/comment_check/scan_gate.py src/Navigation
    python3 Tools/comment_check/scan_gate.py --strict src/Navigation/mcl2d_ros2/src/foo.cpp

--strict 는 게이트보다 **넓게** 본다(게이트가 막지는 않지만 규약상 이력인 서술어).
근거로 인용할 때는 어느 모드였는지 함께 적어야 한다 — 기본 모드만이 게이트와 같다.
"""
import argparse
import importlib.util
import os
import re
import sys

HOOK_REL = os.path.join("docs", "claude_guideline", "coding", "hooks", "coding-comment-gate.py")

# 게이트가 막지는 않지만 conventions.md §4 상 이력 서술인 것들. --strict 에서만 본다.
STRICT_EXTRA = [
    (re.compile(r"종전|폐기했|삭제했|추가했|되돌렸|교체했"), "이력 서술어(strict)"),
]

# 원본 심볼·좌표 인용처럼 정당한 예외는 comment_check 와 같은 마커로 억제한다.
SUPPRESS = re.compile(r"comment-check:\s*ignore")


def repo_root(start):
    d = os.path.abspath(start)
    while d != "/":
        if os.path.isfile(os.path.join(d, HOOK_REL)):
            return d
        d = os.path.dirname(d)
    return None


def load_hook(root):
    path = os.path.join(root, HOOK_REL)
    spec = importlib.util.spec_from_file_location("coding_comment_gate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for attr in ("scan", "is_code_file", "COMMENT_MARKER", "WHITELIST"):
        if not hasattr(mod, attr):
            raise AttributeError(f"훅에 {attr} 가 없다 — 계약이 바뀌었다: {path}")
    return mod


def iter_files(hook, targets):
    for t in targets:
        if os.path.isfile(t):
            yield t
        else:
            for dirpath, dirnames, names in os.walk(t):
                dirnames[:] = [d for d in dirnames
                               if d not in (".git", "build", "install", "log", "__pycache__")]
                for n in names:
                    p = os.path.join(dirpath, n)
                    if hook.is_code_file(p):
                        yield p


def scan_strict(hook, line):
    m = hook.COMMENT_MARKER.search(line)
    if not m:
        return None
    comment = line[m.start():]
    if hook.WHITELIST.search(comment):
        return None
    for pat, label in STRICT_EXTRA:
        if pat.search(comment):
            return label
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+", help="파일 또는 디렉터리")
    ap.add_argument("--strict", action="store_true",
                    help="게이트보다 넓게 본다(게이트 미차단 서술어 포함)")
    args = ap.parse_args()

    root = repo_root(args.targets[0]) or repo_root(os.getcwd())
    if not root:
        print(f"게이트 훅을 찾을 수 없다({HOOK_REL}) — 규칙 비활성이라 판정하지 않는다",
              file=sys.stderr)
        return 2
    hook = load_hook(root)

    total = files = 0
    for path in sorted(iter_files(hook, args.targets)):
        files += 1
        try:
            lines = open(path, errors="replace").read().split("\n")
        except OSError as e:
            print(f"{path}: 읽기 실패 {e}", file=sys.stderr)
            continue
        for num, line in enumerate(lines, 1):
            if SUPPRESS.search(line):
                continue
            hits = hook.scan(line)
            label = hits[0][0] if hits else (scan_strict(hook, line) if args.strict else None)
            if label:
                print(f"{path}:{num}  [{label}]  {line.strip()[:100]}")
                total += 1

    mode = "strict(게이트보다 넓음)" if args.strict else "게이트 동일"
    print(f"-- 파일 {files}개 · 위반 {total}건 · 모드 {mode}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
