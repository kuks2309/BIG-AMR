"""실기 2단계 — 제어권 획득 + **읽기 폴링**. 버스 쓰기는 0x60FF=0(정지)뿐, 모터 무동작.

원본 `gui.py` 의 MainWindow 를 그대로 써서 실제 코드 경로(USB→제어권→폴링→해제)를 탄다.
"""
import os, sys, time, collections
sys.path.insert(0, "/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/amr_test_gui")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5 import QtWidgets
import gui

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
w = gui.MainWindow()
w._seer_run = False                      # Seer 폴링은 이번 검증 대상이 아니다
raw = collections.defaultdict(dict)
w.motor_data.connect(lambda d: [raw[n].update(v) for n, v in d.items()])

def pump(sec):
    t0 = time.time()
    while time.time() - t0 < sec:
        app.processEvents(); time.sleep(0.02)

try:
    w.btn_usb.setChecked(True); w._on_usb(True)
    if w.panda is None:
        raise SystemExit("USB 연결 실패 — 중단")
    print(f"[USB] fw={w.panda.get_version()} safety={w.panda.health()['safety_mode']}")

    w._on_take(True)
    print(f"[제어권] safety={w.panda.health()['safety_mode']} (30=SEER_GATE 이어야 함)")
    pump(4.0)

    print("\n--- 폴링 결과 (0x6064 위치 / 0x6041 상태워드) ---")
    for n in (1, 2, 3, 4):
        d = raw.get(n, {})
        pos, sw = d.get(0x6064), d.get(0x6041)
        print(f"  N{n}: 0x6064={pos}  0x6041={'0x%04X' % sw if sw is not None else None}"
              f"  0x606C={d.get(0x606C)}  0x6078={d.get(0x6078)}")
    print("\n--- 조향 실측각 (신선도 통과분만) ---")
    REF = {3: 7871816, 4: 7840087}      # 2026-08-03 11:44 확정 조향 0°
    for n in (3, 4):
        deg = w._meas_angle(n)
        pos = raw.get(n, {}).get(0x6064)
        d = f"{pos - REF[n]:+d} counts ({(pos - REF[n]) / gui.COUNTS_PER_DEG:+.2f}°)" if pos else "—"
        print(f"  N{n}: _meas_angle={deg}  기준(조향0°) 대비 {d}")
    print(f"\n  _rx_at 갱신됨 = {w._rx_at is not None}   _drive_units = {w._drive_units}")
finally:
    try:
        w._on_take(False); print(f"\n[반환] safety={w.panda.health()['safety_mode']} (0 이어야 함)")
    except Exception as e:
        print(f"반환 실패: {e}")
    try:
        w._on_usb(False)
    except Exception:
        pass
    w._run = False; w._seer_run = False
print("\n--- GUI 로그 ---")
print(w.txt_log.toPlainText())
