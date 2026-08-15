#!/usr/bin/env python3
"""회귀의 **검출력** 검사 — 고친 것을 하나씩 되돌리고 시험이 잡는지 본다.

`pytest` 가 통과한다는 사실은 「고정했다」의 증거가 아니다. 회귀가 대상 코드를 지나가지
않으면 고쳐도 통과하고 되돌려도 통과한다. 그래서 각 항목을 수정 전 상태로 되돌린 사본을
만들어 시험을 돌리고, **그 사본에서도 통과하면 미검출**로 `exit 1` 한다.

⚠ 「안 돈 것」을 「검출」로 세지 않는다 — 실패가 1건 이상 보고된 경우에만 검출로 인정하고,
0건 실행·전량 skip 은 `검사 불가`(실패로 집계)다. 환경은 부모에게서 그대로 물려받는다.

사용:
    python3 src/Comm/CAN/can_relay/mutation_check.py         # 전 항목
    python3 src/Comm/CAN/can_relay/mutation_check.py Z1 Z3   # 지정 항목만
"""
import os
import pathlib
import re
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parent
HZ = PKG / "can_relay" / "home_and_zero.py"
T_HZ = "test/test_home_and_zero.py"

# (id, 되돌리는 내용, [(찾을 문자열, 바꿀 문자열), …], 대상 파일, 시험)
MUTATIONS = [
    ("Z1", "호밍 실패에도 0° 를 보낸다 — 가드 제거(이 도구가 지키는 핵심)", [
        ('        if not ok:\n'
         '            self.c.log(f"호밍 실패 — 조향 0° 지령을 보내지 않습니다: {why}")\n'
         '            return EXIT_HOME_FAILED\n',
         '        if False:\n'
         '            self.c.log("")\n'
         '            return EXIT_HOME_FAILED\n')], HZ, T_HZ),
    ("Z2", "도달 허용오차를 느슨하게 — 정착 편차가 0° 도달로 통과", [
        ("    def __init__(self, client, tol_deg: float = 0.1, timeout_s: float = 10.0,",
         "    def __init__(self, client, tol_deg: float = 3.0, timeout_s: float = 10.0,")],
     HZ, T_HZ),
    ("Z3", "실측 없는 축을 도달로 인정 — 「모르면 됐다고 친다」", [
        ("            if not missing and all(abs(angles[n]) <= self.tol for n in self.nodes):",
         "            if all(abs(angles[n]) <= self.tol for n in self.nodes if angles.get(n) is not None):")],
     HZ, T_HZ),
    ("Z4", "0° 를 호밍보다 먼저 보낸다 — 호밍이 그 목표를 덮어쓴다", [
        ("        ok, why = self.c.call_home()",
         "        self.c.send_steer_zero()\n        ok, why = self.c.call_home()")],
     HZ, T_HZ),
    ("Z5", "실패 사유를 로그에서 지운다 — 조용한 실패", [
        ('            self.c.log(f"호밍 실패 — 조향 0° 지령을 보내지 않습니다: {why}")',
         '            self.c.log("호밍 실패 — 조향 0° 지령을 보내지 않습니다")')], HZ, T_HZ),
]


def run_tests(target):
    """`(검출됨|None, 요약줄)` — None 은 검사 불가(시험이 실행되지 않음)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = "." + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, "-m", "pytest", target,
                        "-q", "--no-header", "--tb=no"],
                       cwd=PKG, capture_output=True, text=True, env=env)
    out = r.stdout.strip()
    last = out.splitlines()[-1] if out else ""
    if not re.search(r"\d+ (?:failed|passed)", last):
        return None, f"검사 불가 — 시험이 실행되지 않았다 ({last!r})"
    return (" failed" in last), last


def main(argv):
    want = {a.upper() for a in argv[1:]}
    originals = {f: f.read_text(encoding="utf-8") for _, _, _, f, _ in MUTATIONS}
    failures = []
    try:
        for mid, what, subs, f, tgt in MUTATIONS:
            if want and mid not in want:
                continue
            text = original = originals[f]
            for old, new in subs:
                if old not in text:
                    print(f"❗ 앵커 불일치 {mid} — 코드가 바뀌었으면 이 파일을 갱신하라")
                    return 1
                text = text.replace(old, new, 1)
            f.write_text(text, encoding="utf-8")
            detected, last = run_tests(tgt)
            f.write_text(original, encoding="utf-8")
            if detected is None:
                print(f"❗ 검사불가 {mid:<4} {what}   ({last})")
                failures.append(mid)
            elif not detected:
                print(f"❌ 미검출 {mid:<4} {what}   ({last})")
                failures.append(mid)
            else:
                print(f"✅ 검출  {mid:<4} {what}   ({last})")
    finally:
        for f, src in originals.items():
            f.write_text(src, encoding="utf-8")
    if failures:
        print(f"\n❌ 미검출 {len(failures)}건: {', '.join(failures)}")
        return 1
    print("\n✅ 전 항목 검출 — 각 수정이 실제로 회귀로 고정돼 있다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
