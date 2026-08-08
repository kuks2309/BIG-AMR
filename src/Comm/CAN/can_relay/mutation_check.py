#!/usr/bin/env python3
"""can_relay 조향 0° 복귀 수정분의 **검출력** 검사.

`Tools/amr_test_gui/mutation_check.py` 와 같은 원리 — 고친 것을 하나씩 되돌리고
`test/test_steer_zero_return.py` 를 돌려 회귀가 잡는지 본다. 되돌렸는데 통과하면 미검출.
원본은 어떤 경로로 끝나도 복원한다.
"""
import os
import pathlib
import re
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parent
BE = PKG / "can_relay" / "backend.py"
DN = PKG / "can_relay" / "driver_node.py"

# 항목은 (id, 설명, [(찾을 문자열, 바꿀 문자열), …]) 이며 대상 파일은 기본 BE 다.
# 4번째 원소로 대상 파일을 지정할 수 있다.

MUTATIONS = [
    ("Z1", "호밍 뒤 0° 복귀 호출 제거 — 종전 동작(정착값에 정지)으로 복귀", [
        ("        zok, zwhy = self.steer_to_zero()\n        return zok, f\"{why} · {zwhy}\"",
         "        return ok, why")]),
    ("Z2", "0° 지령을 빼고 대기만 함 — 「기다리면 알아서 온다」", [
        ("        try:\n            self.set_steer_deg(0.0)\n        except S.UnsafeCommand as exc:\n"
         "            return False, f\"조향 0° 복귀 지령 거부 — {exc}\"",
         "        try:\n            pass\n        except S.UnsafeCommand as exc:\n"
         "            return False, f\"조향 0° 복귀 지령 거부 — {exc}\"")]),
    ("Z3", "판정 허용오차를 settle_tol_deg 로 되돌림 — GOZERO 정착값이 0° 로 통과", [
        ("        tol = float(self.cfg.steer_zero_tol_deg)",
         "        tol = float(self.cfg.settle_tol_deg)")]),
    ("Z4", "0° 미도달을 성공으로 보고 — 호밍 성공만으로 완료 처리", [
        ("        return zok, f\"{why} · {zwhy}\"",
         "        return ok, f\"{why} · {zwhy}\"")]),
    ("Z6", "호밍 결과 로그 줄 제거 — 응답에만 남기고 노드 로그는 조용 (2026-08-08 실기 조사 실패 재발)", [
        ('        (self.get_logger().info if ok else self.get_logger().error)(f"호밍 결과 — {why}")',
         "        pass")], (DN, "test/test_gui_node.py::test_home_result_is_logged_not_only_returned")),
    ("Z5", "피드백 없어도 도달로 인정 — 「모르면 됐다고 친다」", [
        ("            if not missing and all(abs(measured[n]) <= tol for n in self.cfg.steer_nodes):",
         "            if all(abs(measured[n]) <= tol for n in measured):")]),
]


def run_tests(target="test/test_steer_zero_return.py"):
    """대상 시험을 돌리고 `(검출됨, 요약줄)` 반환.

    ⚠ **「안 돈 것」을 「검출」로 세면 안 된다.** 환경을 깎아 만들면 rclpy 를 쓰는 시험이
    통째로 `skipped` 되는데, 그때도 종료코드가 0 이 아닐 수 있어 그대로는 검출로 집계된다
    (2026-08-08 Z6 에서 실제로 그렇게 나왔다 — `1 skipped` 인데 ✅ 로 찍혔다).
    그래서 ① 부모 환경을 그대로 물려주고(ROS 소싱 포함) ② **실패가 1건 이상 보고된
    경우에만** 검출로 인정한다. 0 건 실행·전량 skip 은 검출이 아니라 **검사 불가**다.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = "." + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, "-m", "pytest", target,
                        "-q", "--no-header", "-x", "--tb=no"],
                       cwd=PKG, capture_output=True, text=True, env=env)
    out = r.stdout.strip()
    last = out.splitlines()[-1] if out else ""
    ran = re.search(r"(\d+) (?:failed|passed)", last)
    if not ran:
        return None, f"검사 불가 — 시험이 실행되지 않았다 ({last!r})"
    if " failed" not in last:
        return False, last
    return True, last


def main():
    originals = {BE: BE.read_text(encoding="utf-8"),
                 DN: DN.read_text(encoding="utf-8")}
    failures = []
    try:
        for entry in MUTATIONS:
            mid, what, subs = entry[:3]
            f, tgt = entry[3] if len(entry) > 3 else (BE, "test/test_steer_zero_return.py")
            original = originals[f]
            text = original
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
    print(f"\n✅ {len(MUTATIONS)}개 항목 전부 검출 — 각 수정이 실제로 회귀로 고정돼 있다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
