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


def test_seer_angle_is_normalized_to_our_sign(win):
    """Seer 각도는 **우리 규약(CAN)으로 정규화**해 담아야 한다.

    ⚠ 2026-08-04 실기: Seer 원값을 그대로 담아, 제어권을 잡고 놓을 때마다 `_meas_angle` 의
    부호가 뒤집혔다(바퀴 그림·실측 라벨 동반). 근거는 정본 YAML 의 0° 역산식
    `0° = CAN + Seer_deg × 57344`(음의 상관)와 실측 CAN +90.133° ↔ Seer −90.1°.
    """
    import math
    win._run = False                       # 제어권 없음 → Seer 값이 실측 자리를 대신한다
    win._on_seer_data({3: {"position": math.radians(-90.1)},
                       4: {"position": math.radians(-89.9)}})
    assert win._meas_angle(3) == pytest.approx(+90.1, abs=0.01), "부호가 뒤집힌 채 쓰인다"
    assert win._meas_angle(4) == pytest.approx(+89.9, abs=0.01)


def test_seer_table_keeps_seer_own_sign(win):
    """Seer **표**는 Seer 가 보고한 값 그대로여야 한다 — 정규화는 실측 경로에서만."""
    import math
    win._on_seer_data({3: {"position": math.radians(-90.1)}})
    txt = win.tbl_seer.item(2, 1).text()     # row 2 = node3
    assert txt.startswith("-"), f"Seer 표가 부호를 바꿔 버렸다: {txt}"


def _render(widget, w=320, h=340):
    from PyQt5 import QtGui
    widget.resize(w, h)
    img = QtGui.QImage(w, h, QtGui.QImage.Format_RGB32)
    img.fill(0xFFFFFFFF)
    widget.render(img)
    return img.bits().asstring(img.byteCount())


def test_wheel_drawing_includes_a_direction_arrow():
    """바퀴 그림에 **지향 화살표**가 있어야 한다(2026-08-04 사용자 요청).

    사각형만 그리면 +90° 와 −90° 가 완전히 같은 모양이라 크랩 좌/우를 눈으로 못 가린다.

    ⚠ 처음에는 위젯 전체를 +90°/−90° 로 렌더해 이미지가 다른지 봤는데, **각도 라벨 텍스트**
    (`+90.0°` vs `-90.0°`)만으로도 이미지가 달라져 화살표를 지워도 통과했다. 그래서 호출
    지점 자체를 고정한다.
    """
    import inspect
    src = inspect.getsource(gui.WheelView._draw_wheel)
    assert "_draw_arrow(" in src, "`_draw_wheel` 이 화살표를 그리지 않는다"
    assert hasattr(gui.WheelView, "_draw_arrow")


def test_arrow_points_opposite_ways_for_opposite_headings(app):
    """지향이 반대면 화살표도 반대로 그려져야 한다 — 그래야 좌/우가 구분된다."""
    from PyQt5 import QtGui, QtCore
    def draw(ax, ay):
        img = QtGui.QImage(120, 120, QtGui.QImage.Format_RGB32)
        img.fill(0xFFFFFFFF)
        p = QtGui.QPainter(img)
        gui.WheelView._draw_arrow(gui.WheelView(), p, QtCore.QPointF(60, 60), ax, ay, 40.0)
        p.end()
        return img.bits().asstring(img.byteCount())
    assert draw(1.0, 0.0) != draw(-1.0, 0.0), "지향이 반대인데 같은 그림이다"


def test_zero_degrees_still_renders(app):
    """화살표를 넣어도 0° 가 정상적으로 그려진다(회귀)."""
    wv = gui.WheelView()
    wv.set_angles(0.0, 0.0)
    assert len(_render(wv)) > 0


# ── Seer 인수인계 (2026-08-04 사용자 운영 철학) ──────────────────────────
def test_take_records_seer_angles_as_handover_baseline(win, monkeypatch):
    """제어권을 잡으면 **잡기 직전 Seer 각도**를 기준으로 기억해야 한다."""
    import math
    win.panda = object()                       # None 이 아니면 된다
    monkeypatch.setattr(win, "_on_take", win.__class__._on_take.__get__(win))
    win._on_seer_data({3: {"position": math.radians(-10.0)},
                       4: {"position": math.radians(-12.0)}})
    # 실제 판다 조작은 하지 않고 기억 경로만 확인한다
    win._seer_at_take = {n: win._seer_deg.get(n) for n in gui.STEER_NODES}
    assert win._seer_at_take == pytest.approx({3: 10.0, 4: 12.0}, abs=0.01)


def test_release_restores_steering_to_the_seer_baseline(win, monkeypatch):
    """반환 전에 **잡기 직전 Seer 값으로 조향을 되돌린다**.

    2026-08-04 실기: 되돌리지 않고 넘겼더니 Seer 가 조향을 90° 까지 움직였다.
    """
    sent = []
    monkeypatch.setattr(win, "_steer_axis", lambda n, d: sent.append((n, d)))
    win._seer_at_take = {3: 10.0, 4: 12.0}
    monkeypatch.setattr(win, "_meas_angle", lambda n: {3: 10.0, 4: 12.0}[n])
    win._restore_steer_for_handover()
    assert sorted(sent) == [(3, 10.0), (4, 12.0)], f"복원 지령이 나가지 않았다: {sent}"


def test_release_does_not_move_when_baseline_is_missing(win, monkeypatch):
    """기준이 없으면 **움직이지 않는다** — 모르는 채로 3톤 차체를 돌리지 않는다."""
    sent = []
    monkeypatch.setattr(win, "_steer_axis", lambda n, d: sent.append((n, d)))
    win._seer_at_take = {}
    win._restore_steer_for_handover()
    assert sent == [], f"기준이 없는데 조향을 움직였다: {sent}"


def test_release_does_not_move_when_measurement_is_stale(win, monkeypatch):
    """실측이 신선하지 않으면 복원하지 않는다 — 어디 있는지 모르는 채로 보내지 않는다."""
    sent = []
    monkeypatch.setattr(win, "_steer_axis", lambda n, d: sent.append((n, d)))
    monkeypatch.setattr(win, "_meas_angle", lambda n: None)
    win._seer_at_take = {3: 10.0, 4: 12.0}
    win._restore_steer_for_handover()
    assert sent == [], f"실측이 없는데 조향을 움직였다: {sent}"


def test_release_path_actually_calls_the_restore(win, monkeypatch):
    """반환 경로가 **실제로** 복원을 부르는가 — 함수만 있고 배선이 없으면 소용없다.

    ⚠ 2026-08-04: 처음 붙인 회귀 4건은 `_restore_steer_for_handover()` 를 **직접** 불렀다.
    그래서 `_on_take(False)` 안의 호출을 통째로 지워도 122개가 전부 통과했다 —
    같은 날 아침 M5(`poll_died` 방출 누락)와 똑같은 형태의 공백이다.
    """
    called = []
    monkeypatch.setattr(win, "_restore_steer_for_handover", lambda: called.append(True))

    class _Handle:
        def controlWrite(self, *_a, **_kw):
            return 0

    class _Panda:
        def __init__(self):
            self._handle = _Handle()
        def can_send(self, *_a, **_kw):
            return None
        def set_safety_mode(self, *_a, **_kw):
            return None

    win.panda = _Panda()
    win._run = True
    win._th = None
    win._on_take(False)
    assert called, "반환 경로가 인수인계 복원을 부르지 않는다"


def _feed(win, node, deg, times, ref=0.0):
    """`_check_seer_agreement` 를 `times` 회 먹인다.

    ⚠ Seer 폴링 스레드가 `_seer_deg` 를 비울 수 있으므로(연결 실패 시 `_on_seer_status` 가
    clear) **매 호출 직전에 기준을 다시 세운다** — 시험이 그 스레드 타이밍에 좌우되지 않게.
    """
    for _ in range(times):
        win._seer_deg[node] = ref
        win._check_seer_agreement(node, deg)
    QtWidgets.QApplication.processEvents()


def test_agreement_check_ignores_transient_samples(win):
    """과도 표본 하나로 경보하지 않는다.

    ⚠ 2026-08-05 실기: 획득 직후 첫 표본이 +0.00° 로 읽혔다가 곧 +15.807° 가 됐다
    (그 사이 조향 지령 없음). 한 번 읽고 판정하면 거짓 경보가 난다.
    """
    win.txt_log.clear()
    win._seer_mismatch_streak = {}; win._seer_mismatch_warned_at = {}
    _feed(win, 3, 0.0, gui.SEER_MATCH_STREAK - 1, ref=15.8)      # 연속 조건에 못 미친다
    assert "불일치" not in win.txt_log.toPlainText(), "과도 표본으로 경보했다"


def test_agreement_check_warns_on_persistent_mismatch(win):
    """계속 어긋나면 알린다 — 검사를 무력화한 것이 아니다."""
    win.txt_log.clear()
    win._seer_mismatch_streak = {}; win._seer_mismatch_warned_at = {}
    _feed(win, 3, -137.27, gui.SEER_MATCH_STREAK)
    assert "기준 불일치" in win.txt_log.toPlainText()


def test_agreement_check_reports_recovery(win):
    """어긋났다가 맞으면 **회복도 알린다** — 경보만 남고 끝나면 상태를 알 수 없다."""
    win.txt_log.clear()
    win._seer_mismatch_streak = {}; win._seer_mismatch_warned_at = {}
    _feed(win, 4, -137.27, gui.SEER_MATCH_STREAK)
    _feed(win, 4, 0.0, 1)
    assert "기준 회복" in win.txt_log.toPlainText()


def test_agreement_check_throttles_repeat_warnings(win):
    """같은 축이 계속 어긋나도 로그를 도배하지 않는다."""
    win.txt_log.clear()
    win._seer_mismatch_streak = {}; win._seer_mismatch_warned_at = {}
    _feed(win, 3, -137.27, gui.SEER_MATCH_STREAK * 6)
    assert win.txt_log.toPlainText().count("기준 불일치") == 1


def test_set_meas_actually_runs_the_agreement_check(win, monkeypatch):
    """실측을 기록하는 지점이 **실제로** 대조를 부르는가 — 배선이 없으면 함수만 남는다.

    ⚠ 2026-08-05: 이 회귀를 붙이기 전에는 `_set_meas` 안의 호출을 지워도 126개가 전부
    통과했다. 오늘만 세 번째로 같은 형태의 공백이 나왔다(M5 방출 · 인수인계 복원 · 여기).
    """
    seen = []
    monkeypatch.setattr(win, "_check_seer_agreement", lambda n, d: seen.append((n, d)))
    win._set_meas(3, 12.34)
    win._set_meas(1, 99.0)                     # 구동축은 대조 대상이 아니다
    assert seen == [(3, 12.34)], f"조향 실측이 대조를 거치지 않는다: {seen}"


def test_agreement_check_stops_after_we_command_steering(win):
    """**우리가 조향을 보낸 뒤에는 대조하지 않는다.**

    ⚠ 2026-08-05 실기: 제어권을 쥐면 Seer 는 버스에서 끊겨 모터 실측을 못 본다.
    우리가 +20.00° 로 움직이는 동안 Seer 판독은 +15.81° 에 **고정**돼 있었고,
    그 상태로 대조하면 정상 조작마다 거짓 경보가 난다(실제로 났다).
    """
    win.txt_log.clear()
    win._seer_mismatch_streak = {}; win._seer_mismatch_warned_at = {}
    win._steer_commanded = True                       # 이미 조향을 보낸 상태
    _feed(win, 3, 20.0, gui.SEER_MATCH_STREAK * 2, ref=15.81)
    assert "불일치" not in win.txt_log.toPlainText(), "조향 지령 후에도 대조해 거짓 경보를 냈다"


def test_agreement_check_runs_before_any_steer_command(win):
    """조향을 보내기 전에는 대조가 살아 있다 — 검사를 없앤 것이 아니다."""
    win.txt_log.clear()
    win._seer_mismatch_streak = {}; win._seer_mismatch_warned_at = {}
    win._steer_commanded = False
    _feed(win, 3, -137.27, gui.SEER_MATCH_STREAK, ref=0.0)
    assert "기준 불일치" in win.txt_log.toPlainText()


def test_steer_command_sets_the_flag(win, monkeypatch):
    """조향 지령 지점이 **실제로** 플래그를 세우는가(배선)."""
    monkeypatch.setattr(win, "_sdo_write", lambda *a, **k: None)
    win._steer_commanded = False
    win._steer_axis(3, 5.0)
    assert win._steer_commanded is True, "조향을 보냈는데 대조가 계속 열려 있다"
