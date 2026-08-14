#!/usr/bin/env python3
"""시험 GUI 진입점 — 백엔드를 골라 같은 UI 를 띄운다.

```bash
ros2 run can_relay can_relay_gui                    # 탭 2개(기본)
ros2 run can_relay can_relay_gui --backend ros2     # 드라이버(can_relay_node) 경유
ros2 run can_relay can_relay_gui --backend direct   # 판다 USB 직결
```

운용에는 `ros2` 경로를 쓴다. `direct` 는 드라이버 없이 판다에 직접 지령해 비교하는
시험 경로다.
"""
from __future__ import annotations

import argparse
import atexit
import signal
import sys

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from .app import MainWindow, RelayTabs

SIGNAL_PUMP_MS = 50


def _make_backend(name: str, log, ros_args):
    """이름으로 백엔드 객체를 만든다. 백엔드 종류를 아는 곳은 여기뿐이고 UI 는 모른다."""
    if name == "direct":
        from .backend_direct import DirectBackend
        return DirectBackend(log=log)
    if name == "ros2":
        from .backend_ros2 import Ros2Backend
        return Ros2Backend(log=log, args=ros_args)
    raise SystemExit(f"알 수 없는 백엔드: {name} (ros2 | direct)")


def main(args=None) -> int:
    """창을 띄우고 이벤트 루프를 돈다. 반환은 Qt 종료 코드.

    `--backend both`(기본)면 두 백엔드를 만들어 탭 하나씩 붙인다. 한쪽 생성이 실패해도
    나머지는 띄우고 사유를 로그에 남긴다.

    **어느 경로로 죽어도 제어권·USB 가 풀리도록** 해제를 네 곳에 건다: 창 닫기(`closeEvent`),
    SIGINT/SIGTERM(`app.quit()`), 이벤트 루프 정상 종료, 인터프리터 종료·미처리 예외
    (`atexit`·`sys.excepthook`). 모두 `safe_release()` 한 곳으로 모인다.

    `pump` 타이머는 Qt C++ 루프가 도는 동안에도 파이썬 바이트코드가 실행되게 해서
    신호 핸들러가 돌 수 있게 한다. 없으면 정지 신호가 전달되지 않는다.
    """
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--backend", choices=("both", "ros2", "direct"), default="both",
                    help="both=탭 2개(기본) · ros2=드라이버 경유(운용) · direct=판다 직결(시험 전용)")
    known, rest = ap.parse_known_args(args if args is not None else sys.argv[1:])

    pending = []

    def _seer_kwargs(be):
        """백엔드가 들고 있는 파라미터에서 Seer 접속 설정만 뽑아 준다."""
        cfg = getattr(be, "cfg", {}) or {}
        if not cfg:
            return {}
        return dict(seer_ip=str(cfg.get("seer_ip", "192.168.44.82")),
                    seer_gui_path=str(cfg.get("seer_gui_path",
                                              "/home/nvidia/T-Robot_seer_gui")),
                    seer_enabled=bool(cfg.get("seer_enabled", True)))

    app = QApplication(sys.argv[:1])

    if known.backend == "both":
        # 탭을 만드는 것만으로는 판다가 열리지 않는다 — `start()` 는 하드웨어를 열지 않고
        # USB 버튼으로만 연다. 동시 점유는 `RelayTabs` 가 탭 잠금으로 막는다.
        panels, made = {}, []
        for label, name in (("ROS2 (운용)", "ros2"), ("판다 직결 (시험)", "direct")):
            try:
                be = _make_backend(name, pending.append, rest)
            except Exception as exc:
                pending.append(f"⚠ '{name}' 백엔드를 만들지 못했습니다: "
                               f"{type(exc).__name__}: {exc}")
                continue
            be.start()
            made.append(be)
            panels[label] = MainWindow(be, **_seer_kwargs(be))
        if not panels:
            raise SystemExit("백엔드를 하나도 만들지 못했습니다")
        win = RelayTabs(panels)
        first = next(iter(panels.values()))
        for m in pending:
            first.log(m)
        for be, panel in zip(made, panels.values()):
            be._log = panel.log_line.emit
    else:
        backend = _make_backend(known.backend, pending.append, rest)
        backend.start()
        win = MainWindow(backend, **_seer_kwargs(backend))
        for m in pending:                   # 생성 중 쌓인 로그를 화면으로 옮긴다
            win.log(m)
        backend._log = win.log_line.emit    # 이후 로그는 시그널로(스레드 안전)

    def _on_stop_signal(signum, _frame):
        """SIGINT·SIGTERM 처리 — 로그 한 줄만 남기고 루프 종료를 요청한다."""
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
        """미처리 예외에서도 하드웨어를 놓고 나가도록 해제 후 기본 훅에 넘긴다."""
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
