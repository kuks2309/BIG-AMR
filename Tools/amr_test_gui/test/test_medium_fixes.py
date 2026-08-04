"""2026-08-03 리뷰 Medium 5건 재발 방지.

① STEER_HOME 이 정본 YAML 에서 오는가(사본 드리프트 차단)
② SEER_GUI 경로를 환경변수로 덮을 수 있는가
③ 판다 2대 이상이면 **진행을 막는가**
④ 제어권 반환 시 정지 실패를 **알리는가**
⑤ 폴링이 죽으면 **제어권 표시를 내리는가**
"""
from __future__ import annotations

import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
import gui  # noqa: E402


@pytest.fixture(scope="module")
def app():
    yield QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def win(app):
    w = gui.MainWindow()
    yield w
    w._run = False
    w._seer_run = False


# ── ① 정본 YAML ──────────────────────────────────────────────────────────
def test_steer_home_comes_from_canonical_yaml():
    """사본이 아니라 정본에서 읽어야 한다 — 두 곳이 갈리면 조향이 통째로 어긋난다."""
    assert "정본 YAML" in gui.STEER_HOME_SOURCE, gui.STEER_HOME_SOURCE
    assert os.path.isfile(gui._MACHINE_YAML), gui._MACHINE_YAML


def test_steer_home_matches_the_yaml_content():
    """실제 파일 내용과 일치하는지 직접 대조한다(자기참조 방지)."""
    yaml = pytest.importorskip("yaml")
    with open(gui._MACHINE_YAML, encoding="utf-8") as fh:
        params = yaml.safe_load(fh)["/**"]["ros__parameters"]
    assert list(gui.STEER_HOME.values()) == [int(c) for c in params["steer_home_counts"]]


def test_fallback_is_reported_not_silent(monkeypatch):
    """정본을 못 읽으면 **그 사실이 출처 문자열에 남아야** 한다."""
    monkeypatch.setattr(gui, "_MACHINE_YAML", "/nonexistent/foil.yaml")
    home, src = gui._load_steer_home()
    assert home == gui._STEER_HOME_FALLBACK
    assert "코드 사본" in src and "⚠" in src


# ── ② Seer 경로 ──────────────────────────────────────────────────────────
def test_seer_path_is_overridable_by_env(monkeypatch):
    monkeypatch.setenv("SEER_GUI_PATH", "/tmp/seer-elsewhere")
    reloaded = importlib.reload(gui)
    try:
        assert reloaded.SEER_GUI == "/tmp/seer-elsewhere"
    finally:
        monkeypatch.delenv("SEER_GUI_PATH", raising=False)
        importlib.reload(gui)


# ── ③ 판다 2대 이상 차단 ─────────────────────────────────────────────────
def test_two_pandas_block_usb(win, monkeypatch):
    """어느 장치에 지령이 갈지 모르는 채로 진행할 수 없어야 한다."""
    class _P:
        @staticmethod
        def list():
            return ["AAA", "BBB"]

    monkeypatch.setattr(gui, "_panda_class", lambda: _P)
    win.btn_usb.setEnabled(True)
    win.scan()
    assert win.btn_usb.isEnabled() is False, "판다 2대인데 USB 연결이 열려 있다"
    assert "진행 불가" in win.lab_panda.text()


def test_single_panda_allows_usb(win, monkeypatch):
    class _P:
        @staticmethod
        def list():
            return ["AAA"]

    monkeypatch.setattr(gui, "_panda_class", lambda: _P)
    win.scan()
    assert win.btn_usb.isEnabled() is True


# ── ④ 정지 실패 고지 ─────────────────────────────────────────────────────
def test_stop_failure_on_release_is_logged(win, monkeypatch):
    """정지 프레임이 못 나갔는데 조용히 넘어가면 안 된다."""
    logs = []
    monkeypatch.setattr(win, "log", lambda m: logs.append(m))

    class _Boom:
        class _H:
            def controlWrite(self, *_a, **_kw):
                return 0
        _handle = _H()

        def can_send(self, *_a, **_kw):
            raise RuntimeError("송신 불가(시험)")

        def set_safety_mode(self, *_a, **_kw):
            return None

    win.panda = _Boom()
    win._cls = None
    monkeypatch.setattr(gui, "_panda_class", lambda: type("P", (), {"REQUEST_OUT": 0x40}))
    win._run = True
    win._on_take(False)
    assert any("정지 송신 실패" in m for m in logs), logs


# ── ⑤ 폴링 사망 표시 ─────────────────────────────────────────────────────
def test_poll_death_drops_the_control_toggle(win):
    """표시와 동작이 어긋나면 안 된다 — 폴링이 죽으면 제어권 표시도 내려간다."""
    win.btn_take.blockSignals(True)
    win.btn_take.setChecked(True)
    win.btn_take.blockSignals(False)
    win._on_poll_died()
    assert win.btn_take.isChecked() is False
    assert "폴링 중단" in win.lab_status.text()


# ── Low ①②③ ─────────────────────────────────────────────────────────────
def test_sdo_write_guards_missing_panda(win):
    """판다가 없으면 **정확한 사유**로 실패해야 한다 — AttributeError 로 뭉뚱그리지 않는다."""
    win.panda = None
    with pytest.raises(RuntimeError) as e:
        win._sdo_write(3, 0x607A, 1, 4)
    assert "판다 미연결" in str(e.value)


def test_can_lock_is_reentrant(win):
    """확인과 송신을 한 임계구역에 넣으려면 재진입이 가능해야 한다(리뷰 Low ①)."""
    import threading
    assert isinstance(win._can_lock, type(threading.RLock()))
    with win._can_lock:
        with win._can_lock:          # 같은 스레드 재진입 — 일반 Lock 이면 여기서 멈춘다
            pass


def test_log_widget_has_single_writer():
    """위젯을 만지는 지점이 하나여야 한다 — 호출부가 스레드를 고를 일이 없어진다."""
    src = open(gui.__file__, encoding="utf-8").read()
    assert src.count("self.txt_log.appendPlainText") == 1
    assert "def _append_log" in src


def test_log_is_thread_safe_from_worker(win):
    """작업 스레드에서 `log()` 를 불러도 위젯에 도달한다."""
    import threading
    win.txt_log.clear()
    t = threading.Thread(target=lambda: win.log("작업 스레드에서"), daemon=True)
    t.start()
    t.join(timeout=3.0)
    QtWidgets.QApplication.processEvents()
    assert "작업 스레드에서" in win.txt_log.toPlainText()


def test_poll_thread_death_actually_emits_the_signal(win):
    """⑤의 **배선**을 고정한다 — 핸들러가 아니라 「스레드가 죽으면 알리는가」.

    ⚠ 2026-08-04 돌연변이 검사에서 드러난 공백: `test_poll_death_drops_the_control_toggle` 은
    `_on_poll_died()` 를 **직접 부른다.** 그래서 `_loop` 안의 `self.poll_died.emit()` 을 통째로
    지워도 111개가 전부 통과했다 — 핸들러는 검증되고 **배선은 검증되지 않는** 상태였다.
    여기서는 폴링을 실제로 죽여서 신호가 나오는지 본다.
    """
    import threading
    import time as _t

    class _DeadPanda:
        class _Handle:
            def controlWrite(self, *_a, **_kw):
                raise OSError("USB 가 빠졌다")
        def __init__(self):
            self._handle = self._Handle()
        def can_send(self, *_a, **_kw):
            raise OSError("USB 가 빠졌다")
        def can_recv(self):
            raise OSError("USB 가 빠졌다")

    fired = threading.Event()
    # ⚠ **직접 연결**이어야 한다. PyQt5 는 평범한 콜러블을 송신자(GUI) 스레드로 **큐잉**하므로
    #   기본 연결로는 `th.join()` 이 끝날 때까지 호출되지 않아 「방출됐는가」를 볼 수 없다.
    from PyQt5 import QtCore
    win.poll_died.connect(lambda: fired.set(), QtCore.Qt.DirectConnection)

    # Seer 폴링을 먼저 세운다. 같은 `lab_status` 라벨을 그쪽도 쓰기 때문에, 켜 둔 채로 문구를
    # 단언하면 「Seer … 폴링 실패(RobokitError)」가 나중에 덮어써 무작위로 깨진다(2026-08-04 실측).
    win._seer_run = False
    win.btn_take.blockSignals(True)
    win.btn_take.setChecked(True)          # 「제어권 보유」 표시 상태에서 시작
    win.btn_take.blockSignals(False)

    win.panda = _DeadPanda()
    win._run = True
    th = threading.Thread(target=win._loop, daemon=True)
    th.start()
    th.join(timeout=3.0)

    assert not th.is_alive(), "폴링 스레드가 예외에도 끝나지 않았다"
    assert fired.wait(timeout=1.0), "폴링이 죽었는데 poll_died 가 방출되지 않았다"
    assert win._run is False, "폴링이 죽었는데 제어권 플래그가 남아 있다"

    # 신호가 핸들러까지 도달해 화면 상태가 실제로 내려가는지 (큐 연결이므로 이벤트 처리 필요).
    # 판정은 **토글**로 한다 — 상태 라벨은 Seer 쪽도 쓰는 공유 위젯이라 판정 근거로 못 쓴다.
    for _ in range(20):
        QtWidgets.QApplication.processEvents()
        if not win.btn_take.isChecked():
            break
        _t.sleep(0.05)
    assert win.btn_take.isChecked() is False, "신호는 났는데 제어권 표시가 내려가지 않았다"
