#!/usr/bin/env python3
"""scan_gate 계약 시험.

핵심은 하나다 — **판정이 훅에서 온다**. 패턴을 복사해 두면 훅이 바뀌어도 이 도구는
옛 규칙으로 통과를 찍고, 그 통과가 근거로 쓰인다. 그래서 훅을 임시로 바꿔 놓고
도구 판정이 따라 바뀌는지 확인한다.

⚠ 픽스처는 조각으로 조립한다. 위반 문구를 주석 마커와 같은 줄에 적으면 이 파일 자신이
   게이트에 걸린다 — 게이트를 시험하는 파일의 숙명이다.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "scan_gate.py")
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
HOOK = os.path.join(ROOT, "docs", "claude_guideline", "coding", "hooks", "coding-comment-gate.py")

# 가이드라인 번들은 git 미추적이라 **새 워크트리·새 클론에는 없다.** 그때 이 도구는
#   「규칙 비활성」로 판정을 거부하는 것이 옳은 동작이므로, 시험도 실패가 아니라 건너뛴다.
#   시험이 여기서 죽으면 번들 부재가 도구 결함으로 오독된다.
if not os.path.isfile(HOOK):
    print(f"[SKIP] 게이트 훅이 없다({HOOK}) — 규칙 비활성 환경이라 건너뛴다")
    sys.exit(0)

MARK = "/" + "/"
DATE_BODY = "2026" + "-08-17 에 고쳤다."
ARROW_BODY = "값이 3 " + "-" + "> 5 로 간다."
HIST_BODY = "기" + "존 방식은 달랐다."
STRICT_BODY = "종" + "전 방식으로 둔다."

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print(f"[FAIL] {msg}")


def run(*args):
    r = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True, cwd=ROOT)
    return r.returncode, r.stdout + r.stderr


def write(d, name, body, suppress=False):
    tail = "  comment-check: ignore" if suppress else ""
    p = os.path.join(d, name)
    open(p, "w").write(f"{MARK} {body}{tail}\nint x = 1;\n")
    return p


with tempfile.TemporaryDirectory(dir=ROOT) as d:
    clean = write(d, "clean.cpp", "게이트를 통과하는 주석이다.")
    dated = write(d, "dated.cpp", DATE_BODY)
    arrow = write(d, "arrow.cpp", ARROW_BODY)
    hist = write(d, "hist.cpp", HIST_BODY)
    strict = write(d, "strict.cpp", STRICT_BODY)
    supp = write(d, "supp.cpp", DATE_BODY, suppress=True)

    rc, out = run(clean)
    check(rc == 0 and "위반 0건" in out, "깨끗한 파일을 위반으로 잡았다")

    for path, label in ((dated, "날짜"), (arrow, "값 변천"), (hist, "이력")):
        rc, out = run(path)
        check(rc == 1, f"{label} 위반을 잡지 못했다")

    rc, out = run(strict)
    check(rc == 0, "게이트에 없는 서술어를 기본 모드에서 잡았다 — 기본은 게이트와 같아야 한다")
    rc, out = run("--strict", strict)
    check(rc == 1, "--strict 에서 넓은 서술어를 잡지 못했다")

    rc, out = run(supp)
    check(rc == 0, "억제 마커가 있는 줄을 잡았다")

    rc, out = run(d)
    check("파일 6개" in out, f"디렉터리 순회가 6개를 못 찾았다: {out.strip().splitlines()[-1]}")

    # 훅이 판정 근원임을 확인한다 — 패턴을 임시로 지우면 도구도 통과해야 한다.
    original = open(HOOK).read()
    try:
        target = '(re.compile(r"\\b20\\d{2}\\s?[-./년]\\s?\\d{1,2}\\s?([-./월]\\s?\\d{1,2})?"), "날짜"),'
        check(target in original, "훅에서 날짜 패턴을 찾지 못했다 — 시험이 낡았다")
        open(HOOK, "w").write(original.replace(target, ""))
        rc, out = run(dated)
        check(rc == 0, "훅에서 패턴을 뺐는데도 도구가 잡았다 — 판정이 훅에서 오지 않는다(복사본 사용)")
    finally:
        open(HOOK, "w").write(original)

    rc, out = run(dated)
    check(rc == 1, "훅 원복 후에도 잡지 못했다")

if fails:
    print(f"\n[FAIL] {len(fails)} 건 실패")
    sys.exit(1)
print("[PASS] scan_gate 계약 시험 통과")
