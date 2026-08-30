"""USB 핸들이 두 스레드에서 겹치지 않는지 — 2026-08-03 리뷰 High ② 재발 방지.

## 무엇이 문제였나

폴링 스레드의 heartbeat(`controlWrite 0xf3`)만 `_can_lock` **밖**에 있었다. 조그·호밍 스레드가
`_sdo_write` 로 락을 쥐고 `can_send` 하는 동안 폴링이 같은 핸들에 심박을 낼 수 있었다.
심박이 실패하면 펌웨어 fail-safe 가 걸려 **주행 중 예고 없이 정지**한다.

여기서는 판다를 흉내내는 대역으로 **동시 진입 수를 직접 센다.** 하드웨어는 열지 않는다.
"""
from __future__ import annotations

import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
import gui  # noqa: E402


class _CountingPanda:
    """USB 대역 — 동시에 몇 개의 전송이 진행 중이었는지 센다."""

    class _Handle:
        def __init__(self, outer):
            self.outer = outer

        def controlWrite(self, *_a, **_kw):
            self.outer._enter(); time.sleep(0.004); self.outer._leave()
            return 0

    def __init__(self, delay=0.004):
        self._lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.calls = 0
        self._delay = delay
        self._handle = self._Handle(self)

    def _enter(self):
        with self._lock:
            self.active += 1
            self.calls += 1
            self.max_active = max(self.max_active, self.active)

    def _leave(self):
        with self._lock:
            self.active -= 1

    def can_send(self, *_a, **_kw):
        self._enter(); time.sleep(self._delay); self._leave()

    def can_recv(self):
        return []


@pytest.fixture(scope="module")
def app():
    yield QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def win(app):
    w = gui.MainWindow()
    yield w
    w._run = False
    w._seer_run = False


def test_heartbeat_and_sdo_do_not_overlap(win):
    """폴링 스레드(심박+폴)와 조그 스레드(SDO 쓰기)가 같은 핸들에서 겹치면 안 된다."""
    fake = _CountingPanda()
    win.panda = fake
    win._run = True
    poll = threading.Thread(target=win._loop, daemon=True)
    poll.start()

    errors = []

    def jog():
        try:
            for _ in range(40):
                win._sdo_write(3, 0x607A, 7_871_815, 4)
        except Exception as exc:                      # pragma: no cover - 진단용
            errors.append(exc)

    th = threading.Thread(target=jog, daemon=True)
    th.start()
    th.join(timeout=10.0)
    time.sleep(0.3)
    win._run = False
    poll.join(timeout=3.0)

    assert not errors, f"동시 호출 중 예외: {errors}"
    assert fake.calls > 40, f"대역이 실제로 호출되지 않았다({fake.calls}회) — 위양성"
    assert fake.max_active == 1, (
        f"USB 핸들에 동시 전송 {fake.max_active} 건이 겹쳤다 — "
        f"heartbeat 가 _can_lock 밖이면 이 조합이 성립한다")


def test_heartbeat_is_inside_the_lock_in_source(win):
    """구조 고정 — 심박 줄이 락 블록 **안**에 있는지 원문으로 확인한다.

    행위 시험만으로는 타이밍에 따라 우연히 통과할 수 있다.
    """
    src = open(gui.__file__, encoding="utf-8").read()
    i_lock = src.index("with self._can_lock:\n                    self.panda._handle.controlWrite")
    assert i_lock > 0, "심박이 `with self._can_lock:` 바로 안에 있지 않다"
