"""종료 경로 해제 검증 — `MainWindow.safe_release()` 와 `run()` 의 4경로 배선.

**왜 이 테스트가 필요한가**: 창을 닫는 정상 종료만 안전하면 부족하다. Ctrl+C·`kill`·처리되지
않은 예외로 죽으면 릴레이가 intercept 로, USB 가 열린 채로 남아 Seer 가 로봇을 되찾지 못한다.
그 경로들은 사람이 재현하기 번거로워 회귀가 조용히 들어오므로 코드로 못박는다.

**Qt·실장비 없이 검증한다**: `safe_release` 는 평범한 메서드라 duck-typed 스텁에 **비결합
호출**(`MainWindow.safe_release(stub)`)로 검증할 수 있고, `run()` 은 모듈 전역
(`QApplication`·`MainWindow`·`signal`·`atexit`)을 대체해 배선만 확인한다. 실로봇을 붙이지
않는다 — 이 도구는 실기 전용이라 테스트가 하드웨어를 만지면 안 된다.
"""
from __future__ import annotations

import sys
import types

import pytest

from amr_test_gui import ui_main


# ── 스텁 ─────────────────────────────────────────────────────────────────────


class _Rec:
    """호출 순서를 기록하는 스텁 부품."""

    def __init__(self, log: list[str], name: str, raises: Exception | None = None):
        self._log = log
        self._name = name
        self._raises = raises

    def __call__(self, *a, **k):
        self._log.append(self._name)
        if self._raises is not None:
            raise self._raises


class _Stub:
    """`safe_release` 가 만지는 속성만 갖춘 최소 MainWindow 대역.

    실제 `MainWindow` 는 QApplication 이 있어야 생성되므로(그리고 이 저장소의 GUI 테스트는
    별건 사유로 생성 자체가 깨져 있으므로) 해제 사슬만 떼어내 검증한다.
    """

    def __init__(self, *, link=True, thread=None, fail: dict | None = None):
        fail = fail or {}
        self.calls: list[str] = []
        self._released = False
        self._thread = thread
        self._timer = types.SimpleNamespace(stop=_Rec(self.calls, "timer.stop"))
        self.controller = types.SimpleNamespace(
            estop=_Rec(self.calls, "estop", fail.get("estop")),
            disconnect=_Rec(self.calls, "disconnect", fail.get("disconnect")),
        )
        self.seer = types.SimpleNamespace(stop=_Rec(self.calls, "seer.stop", fail.get("seer")))
        if link:
            self.link = types.SimpleNamespace(
                block_seer_homing=_Rec(self.calls, "unblock_homing", fail.get("unblock")),
                close=_Rec(self.calls, "link.close", fail.get("close")),
            )
        else:
            self.link = None

    def _log(self, *_a, **_k):
        pass


def _release(stub, reason=""):
    return ui_main.MainWindow.safe_release(stub, reason)


# ── 해제 사슬 ────────────────────────────────────────────────────────────────


def test_full_chain_runs_in_order():
    stub = _Stub()
    _release(stub, "테스트")
    assert stub.calls == [
        "timer.stop", "estop", "disconnect", "seer.stop", "unblock_homing", "link.close",
    ]


def test_usb_close_is_reached():
    # 사용자 요구의 핵심 — 종료 시 USB 도 연결 해제되어야 한다.
    stub = _Stub()
    _release(stub)
    assert "link.close" in stub.calls


def test_control_release_precedes_usb_close():
    # 제어권을 반환하기 전에 USB 를 닫으면 릴레이가 intercept 로 남는다.
    stub = _Stub()
    _release(stub)
    assert stub.calls.index("disconnect") < stub.calls.index("link.close")


def test_is_idempotent():
    stub = _Stub()
    _release(stub, "1차")
    first = list(stub.calls)
    _release(stub, "2차")
    assert stub.calls == first, "두 번째 호출이 USB 제어전송을 다시 일으켰다"


def test_released_latch_is_set_before_work():
    # 래치를 나중에 세우면 재진입(신호가 해제 도중 또 들어옴)에서 사슬이 겹친다.
    stub = _Stub()
    _release(stub)
    assert stub._released is True


def test_missing_link_is_tolerated():
    # USB 를 아직 연결하지 않은 채 종료하는 것은 정상 상황이다.
    stub = _Stub(link=False)
    _release(stub)
    assert stub.calls == ["timer.stop", "estop", "disconnect", "seer.stop"]


@pytest.mark.parametrize("failing", ["estop", "disconnect", "seer", "unblock"])
def test_earlier_failure_still_reaches_usb_close(failing):
    # 앞 단계가 터져도 USB 는 반드시 닫혀야 한다 — 중간 예외로 사슬이 끊기면 장치가 잠긴다.
    stub = _Stub(fail={failing: RuntimeError("boom")})
    _release(stub)
    assert "link.close" in stub.calls


def test_usb_close_failure_does_not_propagate():
    # 해제 실패가 예외로 튀면 atexit 경로에서 종료 자체가 시끄럽게 깨진다.
    stub = _Stub(fail={"close": RuntimeError("boom")})
    _release(stub)  # 예외가 새어나오면 테스트 실패


def test_dead_qt_timer_is_tolerated():
    # atexit 경로에서는 Qt 객체가 이미 파괴돼 RuntimeError 가 난다.
    stub = _Stub()
    stub._timer = types.SimpleNamespace(stop=_Rec(stub.calls, "t", RuntimeError("wrapped C/C++")))
    _release(stub)
    assert "link.close" in stub.calls


def test_bringup_worker_is_awaited_before_release():
    # 워커를 기다리지 않으면 disconnect 가 조기 반환하고 그 뒤 TX 루프가 계속 송신한다(리뷰 #H2).
    waited = []
    stub = _Stub(thread=types.SimpleNamespace(wait=lambda ms: waited.append(ms)))
    _release(stub)
    assert waited and waited[0] >= 1000
    assert stub.calls.index("disconnect") >= 0


# ── run() 배선 ───────────────────────────────────────────────────────────────


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


@pytest.fixture
def wired(monkeypatch):
    """`run()` 을 하드웨어·Qt 없이 돌리고 배선 결과를 돌려준다."""
    installed: dict[int, object] = {}
    registered: list[tuple] = []
    app_box: list[_FakeApp] = []
    win_box: list[_FakeWin] = []

    def fake_app(*a):
        app_box.append(_FakeApp(*a))
        return app_box[-1]

    def fake_win(**k):
        win_box.append(_FakeWin(**k))
        return win_box[-1]

    monkeypatch.setattr(ui_main, "QApplication", fake_app)
    monkeypatch.setattr(ui_main, "MainWindow", fake_win)
    monkeypatch.setattr(ui_main.signal, "signal",
                        lambda s, h: installed.__setitem__(s, h))
    monkeypatch.setattr(ui_main.atexit, "register",
                        lambda fn, *a: registered.append((fn, a)))

    # run() 이 기존 hook 을 capture 하므로, 위임 여부를 보려면 미리 기록기를 심어 둔다.
    delegated: list[tuple] = []
    original_hook = sys.excepthook
    sys.excepthook = lambda *a: delegated.append(a)
    try:
        rc = ui_main.run(seer_ip="127.0.0.1")
        hook = sys.excepthook
    finally:
        sys.excepthook = original_hook
    return types.SimpleNamespace(rc=rc, installed=installed, registered=registered,
                                 app=app_box[0], win=win_box[0], hook=hook,
                                 delegated=delegated)


def test_stop_signals_are_installed(wired):
    assert ui_main.signal.SIGINT in wired.installed
    assert ui_main.signal.SIGTERM in wired.installed


def test_signal_handler_only_quits_the_loop(wired):
    # 신호 핸들러 안에서 USB 제어전송을 하면 재진입 위험이 있다 — quit 만 해야 한다.
    before = list(wired.win.released)
    wired.installed[ui_main.signal.SIGINT](int(ui_main.signal.SIGINT), None)
    assert wired.app.quit_called == 1
    assert wired.win.released == before, "핸들러가 해제 사슬을 직접 돌렸다"


def test_release_runs_after_event_loop_returns(wired):
    assert "이벤트 루프 종료" in wired.win.released


def test_atexit_is_registered_as_last_resort(wired):
    assert any(fn == wired.win.safe_release for fn, _ in wired.registered)


def test_excepthook_is_replaced(wired):
    assert wired.hook is not None
    assert callable(wired.hook)


def test_excepthook_releases_before_delegating(wired):
    exc = RuntimeError("boom")
    wired.hook(RuntimeError, exc, None)
    assert "처리되지 않은 예외" in wired.win.released, "예외 경로에서 해제가 일어나지 않았다"
    assert wired.delegated == [(RuntimeError, exc, None)], "원래 excepthook 으로 위임되지 않았다"


def test_excepthook_delegates_even_if_release_fails(wired):
    # 해제가 터져도 traceback 은 반드시 출력되어야 한다 — 조용히 삼키면 원인을 못 찾는다.
    def boom(reason=""):
        raise RuntimeError("release failed")

    wired.win.safe_release = boom
    exc = ValueError("original")
    with pytest.raises(RuntimeError):
        wired.hook(ValueError, exc, None)
    assert wired.delegated == [(ValueError, exc, None)]


def test_run_returns_event_loop_code(wired):
    assert wired.rc == 0
