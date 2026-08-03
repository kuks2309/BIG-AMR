#!/usr/bin/env python3
"""시험 GUI 진입점 — 백엔드를 골라 같은 UI 를 띄운다.

```bash
ros2 run can_relay can_relay_gui --backend ros2     # 드라이버(can_relay_node) 경유
ros2 run can_relay can_relay_gui --backend direct   # 판다 USB 직결(원본과 같은 경로)
```

설계 근거: `docs/adr/2026-08-04-amr-test-gui-swappable-backend.md`.
UI 는 `app.MainWindow` 1벌이고, 위젯 트리는 원본 `Tools/amr_test_gui/gui.py` 와 동일하다.

`--backend direct` 는 **시험 전용**이다 — 원본의 알려진 결함(정착 신선도 부재 · 단발 송신 ·
heartbeat 락 밖)을 **비교를 위해 그대로 옮겼다**(`backend_direct` docstring 참조).
운용은 `--backend ros2` 를 쓴다.

## 해제 배선 4경로 (원본과 동일 — 전부 `MainWindow.safe_release()` 로 수렴)

| 경로 | 배선 |
| --- | --- |
| 창 닫기·Alt+F4 | `closeEvent` |
| Ctrl+C(SIGINT)·`kill`(SIGTERM) | `signal.signal` → `app.quit()` |
| 이벤트 루프 정상 종료 | `app.exec_()` 반환 직후 |
| 인터프리터 종료·미처리 예외 | `atexit` + `sys.excepthook` |

⚠ `pump` 타이머가 없으면 정지 신호가 **아예 전달되지 않는다** — Qt C++ 루프가 도는 동안
파이썬 바이트코드가 실행되지 않기 때문이다(원본 `gui.py` 의 2026-07-28 실측 근거 그대로).
"""
from __future__ import annotations

import argparse
import atexit
import signal
import sys

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from .app import MainWindow

SIGNAL_PUMP_MS = 50


def _make_backend(name: str, log, ros_args):
    """이름으로 백엔드를 만든다. **여기서만 백엔드를 안다** — UI 는 모른다."""
    if name == "direct":
        from .backend_direct import DirectBackend
        return DirectBackend(log=log)
    if name == "ros2":
        from .backend_ros2 import Ros2Backend
        return Ros2Backend(log=log, args=ros_args)
    raise SystemExit(f"알 수 없는 백엔드: {name} (ros2 | direct)")


def main(args=None) -> int:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--backend", choices=("ros2", "direct"), default="ros2",
                    help="ros2=드라이버 경유(운용) · direct=판다 직결(시험 전용)")
    known, rest = ap.parse_known_args(args if args is not None else sys.argv[1:])

    pending = []
    backend = _make_backend(known.backend, pending.append, rest)

    seer = getattr(backend, "cfg", {}) or {}
    win_kwargs = {}
    if seer:
        win_kwargs = dict(seer_ip=str(seer.get("seer_ip", "192.168.44.82")),
                          seer_gui_path=str(seer.get("seer_gui_path",
                                                     "/home/nvidia/T-Robot_seer_gui")),
                          seer_enabled=bool(seer.get("seer_enabled", True)))

    backend.start()
    app = QApplication(sys.argv[:1])
    win = MainWindow(backend, **win_kwargs)
    for m in pending:                       # 백엔드 생성 중 쌓인 로그를 화면에 옮긴다
        win.log(m)
    backend._log = win.log_line.emit        # 이후 로그는 시그널로(스레드 안전)

    def _on_stop_signal(signum, _frame):
        print(f"[gui] 정지 신호({signal.Signals(signum).name}) 수신 — 해제 후 종료합니다.",
              flush=True)
        app.quit()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _on_stop_signal)

    pump = QTimer()                         # 참조를 유지해야 GC 되지 않는다
    pump.timeout.connect(lambda: None)
    pump.start(SIGNAL_PUMP_MS)

    _default_excepthook = sys.excepthook

    def _excepthook(exc_type, exc, tb):
        try:
            win.safe_release("처리되지 않은 예외")
        finally:
            _default_excepthook(exc_type, exc, tb)

    sys.excepthook = _excepthook
    atexit.register(win.safe_release, "인터프리터 종료")

    win.show()
    rc = app.exec_()
    win.safe_release("이벤트 루프 종료")
    return rc


if __name__ == "__main__":
    sys.exit(main())
