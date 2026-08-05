"""종료 경로 해제 검증 — `MainWindow.safe_release()` 와 `main()` 의 4경로 배선.

**왜 필요한가**: 창을 닫는 정상 종료만 안전하면 부족하다. Ctrl+C·`kill`·미처리 예외로 죽으면
릴레이가 intercept 로, USB 가 열린 채로 남아 Seer 가 로봇을 되찾지 못한다. 그 경로들은 사람이
재현하기 번거로워 회귀가 조용히 들어오므로 코드로 못박는다.

**Qt 창·실장비 없이 검증한다**: `safe_release` 는 평범한 메서드라 duck-typed 스텁에 **비결합
호출**(`MainWindow.safe_release(stub)`)로 검증하고, `main()` 은 모듈 전역
(`QApplication`·`MainWindow`·`signal`·`atexit`·`QTimer`)을 대체해 배선만 확인한다.
이 도구는 실기 전용이라 테스트가 하드웨어를 만져서는 안 된다.
"""
from __future__ import annotations

import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import gui  # noqa: E402


# ── 스텁 ─────────────────────────────────────────────────────────────────────


class _Stub:
    """`safe_release` 가 만지는 속성만 갖춘 최소 MainWindow 대역."""

    def __init__(self, *, panda=True, take_raises=None, close_raises=None):
        self.calls: list[str] = []
        self._released = False
        self._seer_run = True
        self._jog_stop = False
        self._take_raises = take_raises
        self._close_raises = close_raises
        if panda:
            outer = self

            class _Panda:
                def close(self):
                    outer.calls.append("panda.close[USB 해제]")
                    if outer._close_raises:
                        raise outer._close_raises

            self.panda = _Panda()
        else:
            self.panda = None

    def _on_take(self, on):
        self.calls.append(f"_on_take({on})[제어권 반환]")
        if self._take_raises:
            raise self._take_raises


def _release(stub, reason="테스트"):
    return gui.MainWindow.safe_release(stub, reason)


# ── 해제 사슬 ────────────────────────────────────────────────────────────────


def test_chain_releases_control_then_usb():
    # 제어권을 반환하기 전에 USB 를 닫으면 릴레이가 intercept 로 남는다.
    stub = _Stub()
    _release(stub)
    assert stub.calls == ["_on_take(False)[제어권 반환]", "panda.close[USB 해제]"]


def test_seer_polling_and_jog_are_stopped():
    stub = _Stub()
    _release(stub)
    assert stub._seer_run is False
    assert stub._jog_stop is True


def test_panda_handle_is_dropped():
    # 참조를 남기면 이후 경로가 닫힌 핸들을 다시 만질 수 있다.
    stub = _Stub()
    _release(stub)
    assert stub.panda is None


def test_does_not_depend_on_btn_take():
    """`btn_take` 위젯이 없어도 해제가 되어야 한다.

    `setChecked(False)` 경유는 Qt 시그널 전달에 의존해 `atexit` 시점에 조용히 누락된다.
    스텁에 `btn_take` 를 두지 않았는데 통과한다는 것이 그 의존이 없다는 증거다.
    """
    stub = _Stub()
    assert not hasattr(stub, "btn_take")
    _release(stub)
    assert "_on_take(False)[제어권 반환]" in stub.calls


def test_is_idempotent():
    stub = _Stub()
    _release(stub, "1차")
    first = list(stub.calls)
    _release(stub, "2차")
    assert stub.calls == first, "두 번째 호출이 USB 제어전송을 다시 일으켰다"


def test_latch_is_set_before_work():
    # 래치를 나중에 세우면 재진입(해제 도중 신호 재수신)에서 사슬이 겹친다.
    stub = _Stub()
    _release(stub)
    assert stub._released is True


def test_no_panda_is_tolerated():
    # USB 를 연결하지 않은 채 종료하는 것은 정상 상황이다.
    stub = _Stub(panda=False)
    _release(stub)
    assert stub.calls == []
    assert stub._seer_run is False


def test_take_failure_still_closes_usb():
    # 제어권 반환이 터져도 USB 는 반드시 닫아야 한다.
    stub = _Stub(take_raises=RuntimeError("boom"))
    _release(stub)
    assert "panda.close[USB 해제]" in stub.calls


def test_close_failure_does_not_propagate():
    # 해제 실패가 예외로 튀면 atexit 경로에서 종료가 시끄럽게 깨진다.
    stub = _Stub(close_raises=RuntimeError("boom"))
    _release(stub)
    assert stub.panda is None


# ── main() 배선 ──────────────────────────────────────────────────────────────


class _FakeApp:
    def __init__(self, *_a):
        self.quit_called = 0

    def quit(self):
        self.quit_called += 1

    def exec_(self):
        return 0


class _FakeWin:
    def __init__(self, **_k):
        self.released: list[str] = []

    def show(self):
        pass

    def safe_release(self, reason=""):
        self.released.append(reason)


class _FakeTimer:
    instances: list["_FakeTimer"] = []

    def __init__(self):
        self.started_ms = None
        self.connected = 0
        _FakeTimer.instances.append(self)

    @property
    def timeout(self):
        holder = self

        class _Sig:
            def connect(self, _fn):
                holder.connected += 1

        return _Sig()

    def start(self, ms):
        self.started_ms = ms


@pytest.fixture
def wired(monkeypatch):
    """`main()` 을 하드웨어·Qt 없이 돌리고 배선 결과를 돌려준다."""
    installed: dict = {}
    registered: list = []
    apps: list = []
    wins: list = []
    _FakeTimer.instances.clear()

    monkeypatch.setattr(gui, "QApplication", lambda *a: apps.append(_FakeApp()) or apps[-1])
    monkeypatch.setattr(gui, "MainWindow", lambda **k: wins.append(_FakeWin()) or wins[-1])
    monkeypatch.setattr(gui, "QTimer", _FakeTimer)
    monkeypatch.setattr(gui.signal, "signal", lambda s, h: installed.__setitem__(s, h))
    monkeypatch.setattr(gui.atexit, "register", lambda fn, *a: registered.append((fn, a)))

    delegated: list = []
    original = sys.excepthook
    sys.excepthook = lambda *a: delegated.append(a)
    try:
        rc = gui.main()
        hook = sys.excepthook
    finally:
        sys.excepthook = original
    return types.SimpleNamespace(rc=rc, installed=installed, registered=registered,
                                 app=apps[0], win=wins[0], hook=hook, delegated=delegated,
                                 timers=list(_FakeTimer.instances))


def test_stop_signals_are_installed(wired):
    assert gui.signal.SIGINT in wired.installed
    assert gui.signal.SIGTERM in wired.installed


def test_signal_pump_timer_is_started(wired):
    """pump 타이머가 없으면 Qt 루프 중 신호가 아예 전달되지 않는다(실측 확인된 함정)."""
    assert wired.timers, "QTimer 가 생성되지 않았다"
    pump = wired.timers[0]
    assert pump.connected >= 1, "timeout 에 파이썬 콜러블이 연결되지 않았다"
    assert pump.started_ms == gui.SIGNAL_PUMP_MS
    assert 0 < gui.SIGNAL_PUMP_MS <= 200, "pump 주기가 너무 길면 신호 반응이 늦다"


def test_signal_handler_only_quits_the_loop(wired):
    # 핸들러 안에서 USB 제어전송을 하면 재진입 위험이 있다 — quit 만 해야 한다.
    before = list(wired.win.released)
    wired.installed[gui.signal.SIGINT](int(gui.signal.SIGINT), None)
    assert wired.app.quit_called == 1
    assert wired.win.released == before, "핸들러가 해제 사슬을 직접 돌렸다"


def test_release_runs_after_event_loop_returns(wired):
    assert "이벤트 루프 종료" in wired.win.released


def test_atexit_is_registered_as_last_resort(wired):
    assert any(fn == wired.win.safe_release for fn, _ in wired.registered)


def test_excepthook_releases_before_delegating(wired):
    exc = RuntimeError("boom")
    wired.hook(RuntimeError, exc, None)
    assert "처리되지 않은 예외" in wired.win.released
    assert wired.delegated == [(RuntimeError, exc, None)]


def test_main_returns_event_loop_code(wired):
    assert wired.rc == 0
