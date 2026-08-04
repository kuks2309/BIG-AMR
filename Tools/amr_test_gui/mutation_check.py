#!/usr/bin/env python3
"""원본 GUI 수정분의 **검출력** 검사 — 고친 것을 되돌려 회귀가 잡는지 본다.

## 왜 필요한가

`pytest` 가 전부 통과한다는 사실은 「고쳤다」의 증거가 **아니다**. 회귀가 대상 코드를 실제로
건드리지 않으면 그 회귀는 고쳐도 통과하고 되돌려도 통과한다 — 아무것도 고정하지 못한다.

2026-08-04 에 실제로 그 일이 있었다. 리뷰 Medium ⑤(폴링 스레드가 죽으면 제어권 표시를
내린다)의 회귀 `test_poll_death_drops_the_control_toggle` 은 `_on_poll_died()` 를 **직접 부른다.**
그래서 `_loop` 안의 `self.poll_died.emit()` 을 통째로 지워도 **111개가 전부 통과**했다.
핸들러는 검증됐고 배선은 검증되지 않은 상태로 「11개 결함 회귀로 고정 완료」라고 보고했다.
(기록: `docs/claude-mistake/2026-08-04-001_regression-without-detection-power.md`)

## 무엇을 하는가

`gui.py` 를 한 번에 하나씩 **수정 전 상태로 되돌린 사본**을 만들고 전체 시험을 돌린다.
되돌렸는데도 통과하면(미검출) 그 항목의 회귀는 검출력이 없다 — `exit 1`.

⚠ 상수(`MEAS_TTL_S`·`RX_TTL_S`)를 지렛대로 쓰면 안 된다. 시험이 그 상수를 monkeypatch 하므로
   기본값을 바꿔도 무력하다. **로직 자체**를 되돌려야 한다(H1·H3b 항목 참조).

## 사용

    python3 Tools/amr_test_gui/mutation_check.py          # 전 항목
    python3 Tools/amr_test_gui/mutation_check.py H1 M5    # 지정 항목만

원본 `gui.py` 는 어떤 경로로 끝나도 복원한다(예외·중단 포함).
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
GUI = HERE / "gui.py"

# (id, 되돌리는 내용, [(찾을 문자열, 바꿀 문자열), …])
MUTATIONS = [
    ("H1", "`_meas_angle` 의 실측 신선도(TTL) 검사를 무력화 — 낡은 값으로 정착 판정", [
        ("        if at is None or (time.monotonic() - at) > MEAS_TTL_S:\n            return None",
         "        if False:\n            return None")]),
    ("H2", "heartbeat(0xf3) 를 `_can_lock` 밖으로 — USB 핸들 경합 복귀", [
        ('                with self._can_lock:\n'
         '                    self.panda._handle.controlWrite(P.REQUEST_OUT, 0xf3, 0, 0, b"")',
         '                if True:\n'
         '                    self.panda._handle.controlWrite(P.REQUEST_OUT, 0xf3, 0, 0, b"")')]),
    ("H3a", "폴 루프의 구동 재송신 제거 — 단발 송신 복귀", [
        ("                        self._sdo_write(n, 0x60FF, self._drive_units, 4)",
         "                        pass")]),
    ("H3b", "응답두절 워치독 분기를 죽임 — 버스가 조용해도 구동 유지", [
        ("                if self._rx_at and (time.monotonic() - self._rx_at) > RX_TTL_S \\\n"
         "                        and self._drive_units != 0:",
         "                if False:")]),
    ("M1", "조향 0° 정본 YAML 로드를 실패시켜 코드 사본으로 복귀", [
        ("def _load_steer_home():",
         "def _load_steer_home():\n    if True:\n        return dict(_STEER_HOME_FALLBACK), '코드 사본'")]),
    ("M2", "Seer 경로의 환경변수 주입 제거 — 절대경로 고정", [
        ('SEER_GUI = os.environ.get("SEER_GUI_PATH", "/home/nvidia/T-Robot_seer_gui")',
         'SEER_GUI = "/home/nvidia/T-Robot_seer_gui"')]),
    ("M3", "판다 2대 이상도 그중 1대를 열도록 복귀", [
        ("        elif len(serials) == 1:", "        elif len(serials) >= 1:")]),
    ("M4", "제어권 반환 시 정지 송신 실패를 조용히 삼킴", [
        ('                    self.log(f"⚠ 제어권 반환 전 정지 송신 실패 — ',
         '                    _ = (f"')]),
    ("M5", "폴링 스레드 사망 시 `poll_died` 방출 제거 (핸들러는 그대로)", [
        ("                self.poll_died.emit()", "                pass")]),
    ("L1", "`_can_lock` 을 재진입 불가 Lock 으로 — 확인·송신 단일 임계구역 붕괴", [
        ("self._can_lock = threading.RLock()", "self._can_lock = threading.Lock()")]),
    ("L2", "`_sdo_write` 의 판다 미연결 가드 제거", [
        ('            raise RuntimeError("판다 미연결 — USB 를 먼저 연결하세요")', "            pass")]),
    ("L3", "로그 위젯 쓰기 경로를 하나 더 만듦 — 단일 기록자 붕괴", [
        ("    def log(self, msg: str):",
         "    def log(self, msg: str):\n        self.txt_log.appendPlainText(msg)")]),
]


def main(argv: list[str]) -> int:
    want = {a.upper() for a in argv[1:]}
    pristine = GUI.read_text(encoding="utf-8")
    rows, misses, skipped = [], [], []
    try:
        for mid, what, subs in MUTATIONS:
            if want and mid.upper() not in want:
                continue
            src = pristine
            anchor_ok = True
            for old, new in subs:
                if old not in src:
                    anchor_ok = False
                    break
                src = src.replace(old, new, 1)
            if not anchor_ok:
                skipped.append(mid)
                rows.append((mid, what, "‼ 앵커 불일치", "코드가 바뀌었다 — 돌연변이를 갱신하라"))
                continue
            GUI.write_text(src, encoding="utf-8")
            run = subprocess.run(
                [sys.executable, "-m", "pytest", "test", "-q", "-p", "no:cacheprovider",
                 "--no-header", "--tb=no"],
                cwd=HERE, capture_output=True, text=True, timeout=900)
            caught = [ln.split("::")[-1].split()[0]
                      for ln in run.stdout.splitlines() if ln.startswith("FAILED")]
            if run.returncode:
                rows.append((mid, what, "✅ 검출", ", ".join(caught[:3])))
            else:
                misses.append(mid)
                rows.append((mid, what, "❌ 미검출", "이 수정을 고정하는 회귀가 없다"))
            GUI.write_text(pristine, encoding="utf-8")
    finally:
        GUI.write_text(pristine, encoding="utf-8")     # 어떤 경로로 끝나도 원본 복원

    width = max(len(r[1]) for r in rows) if rows else 0
    for mid, what, verdict, detail in rows:
        print(f"{verdict}  {mid:4s} {what:<{width}}  {detail}")
    if skipped:
        print(f"\n‼ 앵커 불일치 {len(skipped)}건({', '.join(skipped)}) — "
              f"코드가 바뀌었으면 이 파일의 MUTATIONS 를 함께 갱신한다.")
    if misses:
        print(f"\n❌ 검출력 없는 항목 {len(misses)}건: {', '.join(misses)}")
        print("   회귀가 통과하는 것과 결함을 잡는 것은 다르다. 회귀를 보강하라.")
        return 1
    if skipped:
        return 1
    print(f"\n✅ {len(rows)}개 항목 전부 검출 — 각 수정이 실제로 회귀로 고정돼 있다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
