"""실기 3단계 — 전진 1초 / 정지 2초 / 후진 1초 @ 50 mm/s.

원본 `gui.py` 의 MainWindow 를 그대로 쓴다(=검증 대상 코드 경로).
안전: ① 조향이 0° 이고 실측이 **신선**할 때만 출발 ② 어떤 경로로 끝나도 `_drive(0)` + 제어권 반환.
"""
import os, sys, time, collections, csv
sys.path.insert(0, "/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/amr_test_gui")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5 import QtWidgets
import gui

MMPS, DUR, PAUSE = 50.0, 1.0, 2.0
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
w = gui.MainWindow(); w._seer_run = False
raw = collections.defaultdict(dict)
w.motor_data.connect(lambda d: [raw[n].update(v) for n, v in d.items()])
trace = []          # (t_mono, phase, N1_vel, N2_vel, N3_pos, N4_pos)

def pump(sec, phase):
    t0 = time.monotonic()
    while time.monotonic() - t0 < sec:
        app.processEvents(); time.sleep(0.02)
        trace.append((time.monotonic(), phase,
                      raw.get(1, {}).get(0x606C), raw.get(2, {}).get(0x606C),
                      raw.get(1, {}).get(0x6064), raw.get(2, {}).get(0x6064)))

try:
    w._on_usb(True)
    assert w.panda is not None, "USB 연결 실패"
    w._on_take(True)
    pump(2.0, "engage")

    d3, d4 = w._meas_angle(3), w._meas_angle(4)
    print(f"출발 전 조향 실측: N3={d3} N4={d4}")
    if d3 is None or d4 is None:
        raise SystemExit("중단 — 조향 실측이 신선하지 않다(정착 판정 불가)")
    if max(abs(d3), abs(d4)) > 1.0:
        raise SystemExit(f"중단 — 조향이 0° 가 아니다(N3={d3:.2f}° N4={d4:.2f}°)")

    fwd = gui.drive_units(MMPS, gui.JOG["전진"][1])
    bwd = gui.drive_units(MMPS, gui.JOG["후진"][1])
    print(f"지령 raw: 전진={fwd:+d}  후진={bwd:+d}  (50 mm/s, VEL_PER_MMPS={gui.VEL_PER_MMPS})")

    print(f"[{time.monotonic():.2f}] 전진 시작"); w._drive(fwd); pump(DUR, "fwd")
    print(f"[{time.monotonic():.2f}] 정지");     w._drive(0);   pump(PAUSE, "stop1")
    print(f"[{time.monotonic():.2f}] 후진 시작"); w._drive(bwd); pump(DUR, "bwd")
    print(f"[{time.monotonic():.2f}] 정지");     w._drive(0);   pump(2.0, "stop2")
finally:
    try: w._drive(0)
    except Exception as e: print(f"정지 송신 실패: {e}")
    try: w._on_take(False)
    except Exception as e: print(f"반환 실패: {e}")
    try: w._on_usb(False)
    except Exception: pass
    w._run = False; w._seer_run = False

with open(sys.argv[1], "w", newline="") as fh:
    wr = csv.writer(fh); wr.writerow(["t_mono", "phase", "n1_vel", "n2_vel", "n1_pos", "n2_pos"])
    wr.writerows(trace)
print(f"\n구동 트레이스 {len(trace)}행 저장")
print("\n--- GUI 로그 ---"); print(w.txt_log.toPlainText())
