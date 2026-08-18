#!/usr/bin/env python3
"""함수표의 `파일:시작-끝` 앵커를 소스에서 재계산해 갱신한다.

표의 줄 앵커는 코드를 한 줄만 끼워 넣어도 전부 밀린다. 손으로 맞추면 반드시 어긋나고,
어긋난 앵커는 **그 표를 읽는 다음 작업자를 엉뚱한 코드로 보낸다**(coding SOP §2 가 이 표를
선독하게 하므로 비용이 곧바로 발생한다).

    python3 Tools/comment_check/refresh_anchors.py <표.md> <소스디렉터리>...
    python3 Tools/comment_check/refresh_anchors.py --check <표.md> <소스디렉터리>...

`--check` 는 고치지 않고 어긋난 것만 보고한다(종료코드 1).

찾는 방식:
  - 함수: 정의 줄을 찾아 **바로 위에 붙은 주석 블록까지** 시작으로, 같은 들여쓰기의 닫는
    중괄호를 끝으로 잡는다. 호출부와 헷갈리지 않도록 `return`·`;` 로 끝나는 줄은 뺀다.
  - 멤버 변수: 선언 블록에 있으므로 **마지막** 일치를 쓴다. 한 행이 여러 이름을 묶으면
    첫 이름의 줄부터 마지막 이름의 줄까지.
"""
import argparse
import os
import re
import sys

# 한 행이 이름을 여러 개 묶기도 한다(`a` / `b` / `c`). 첫 백틱에서 끊으면 나머지가
#   범위에서 빠져 앵커가 좁아진다 — 이름 칸 전체를 잡고 그 안의 백틱을 모두 훑는다.
ROW = re.compile(r"^\| (`[^|]*?`[^|]*?)\| ([A-Za-z_0-9]+\.(?:cpp|hpp|py)):(\d+)-(\d+) \|")
NAME = re.compile(r"`([^`]+)`")


def find_sources(dirs):
    out = {}
    for d in dirs:
        if os.path.isfile(d):
            out.setdefault(os.path.basename(d), d)
            continue
        for dirpath, dirnames, names in os.walk(d):
            dirnames[:] = [x for x in dirnames
                           if x not in (".git", "build", "install", "log", "__pycache__")]
            for n in names:
                if n.rsplit(".", 1)[-1] in ("cpp", "hpp", "py"):
                    out.setdefault(n, os.path.join(dirpath, n))
    return out


def func_span(lines, ident):
    # 이름 앞에 반환형이 **없을 수도** 있다(생성자). 앞부분을 필수로 두면 생성자에서
    #   그 첫 글자가 먹혀 영영 못 찾는다 — 그래서 이름 자체를 검색한다.
    define = re.compile(r"\b" + re.escape(ident) + r"\s*\(")
    for i, ln in enumerate(lines):
        st = ln.lstrip()
        if st.startswith("//") or st.startswith("#") or st.startswith("*"):
            continue
        m = define.search(ln)
        if not m:
            continue
        # 호출부 배제 — 정의 줄은 `;` 로 끝나지 않고, `return`·멤버 접근으로 시작하지 않는다.
        if st.startswith("return ") or ln.rstrip().endswith(";"):
            continue
        if m.start() > 0 and ln[m.start() - 1] in ".>":
            continue
        # 생성자 초기화 리스트 배제 — `Widget() : count_(0), spare_(1)` 의 `count_(` 는
        #   함수 정의처럼 보이지만 멤버 초기화다. 단 `::` 는 클래스 밖 정의의 스코프이므로
        #   남긴다(`void Ekf::addOdom(...)`).
        before = ln[:m.start()].rstrip()
        if before.endswith(",") or (before.endswith(":") and not before.endswith("::")):
            continue
        start = i
        while start > 0 and lines[start - 1].lstrip().startswith("//"):
            start -= 1
        indent = len(ln) - len(ln.lstrip())
        closing = " " * indent + "}"
        for j in range(i + 1, len(lines)):
            if lines[j].rstrip() in (closing, closing + ";"):
                return start + 1, j + 1
        return start + 1, i + 1
    return None


def member_line(lines, ident):
    # 들여쓰기를 요구하지 않는다 — 이름공간 스코프 상수(`inline constexpr … kFoo = 1;`)는
    #   줄 맨 앞에서 시작해 멤버 규칙으로는 영영 안 잡힌다.
    decl = re.compile(r"^\s*[A-Za-z_].*\b" + re.escape(ident) + r"\b\s*(=|;|,|\{)")
    hit = None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("//"):
            continue
        if decl.match(ln):
            hit = i + 1
    return hit


def resolve(lines, names):
    """함수로 먼저 찾고, 없으면 멤버 선언으로 찾는다."""
    spans = []
    for n in names:
        s = func_span(lines, n)
        if s is None:
            m = member_line(lines, n)
            s = (m, m) if m else None
        if s is None:
            return None
        spans.append(s)
    return min(a for a, _ in spans), max(b for _, b in spans)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("table")
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--check", action="store_true", help="고치지 않고 보고만 한다")
    args = ap.parse_args()

    sources = find_sources(args.sources)
    cache = {}
    out, changed, unresolved = [], 0, 0

    for line in open(args.table).read().split("\n"):
        m = ROW.match(line)
        if not m:
            out.append(line)
            continue
        cell, fname, a, b = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        path = sources.get(fname)
        if not path:
            out.append(line)
            continue
        if path not in cache:
            cache[path] = open(path, errors="replace").read().split("\n")
        names = [n.split("(")[0].split("::")[-1].strip() for n in NAME.findall(cell)]
        names = [n for n in names if n]
        sym = " / ".join(names)
        span = resolve(cache[path], names)
        if span is None:
            print(f"  ⚠ {sym}: 소스에서 찾지 못했다 ({fname}) — 표가 낡았거나 이름이 바뀌었다")
            unresolved += 1
            out.append(line)
            continue
        if (a, b) != span:
            print(f"  {'어긋남' if args.check else '갱신'}  {sym}: {fname}:{a}-{b} -> {span[0]}-{span[1]}")
            changed += 1
            line = f"| {cell}| {fname}:{span[0]}-{span[1]} |" + line[m.end():]
        out.append(line)

    if not args.check and changed:
        open(args.table, "w").write("\n".join(out))
    print(f"-- 앵커 {'어긋남' if args.check else '갱신'} {changed}건 · 미해결 {unresolved}건")
    return 1 if (unresolved or (args.check and changed)) else 0


if __name__ == "__main__":
    sys.exit(main())
