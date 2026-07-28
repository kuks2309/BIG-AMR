"""2026-07-27 코드 리뷰(REQUEST CHANGES)에서 나온 안전 결함의 회귀 고정.

검증 등급(과장 금지 — 무엇을 실제로 확인했는지 구분해 적는다):
  - **수정 전 실패를 직접 재현 확인**: `#C1`(Space 키 — 수정 전 E-STOP 미체결 + 주행 버튼 재클릭 1회
    관측), `#H1`(staleness — `FEEDBACK_STALE_S` 를 무력화하면 RX 사망 7 s 후에도
    `SETTLED`/`raw=-1222`/구동 허용이 그대로 재현됨).
  - **수정 후 통과만 확인**(수정 전 거동은 코드 판독 + 리뷰 보고로 확정): `#H2`·`#H3`·`#H4`·`#M3`·`#M9`.

GUI 계열은 offscreen 으로 돌아가므로 디스플레이가 없어도 실행된다.
"""
import os
import sys
import threading
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from amr_test_gui.controller import AmrTestController        # noqa: E402
from amr_test_gui.motor_control_import import NodeSilent      # noqa: E402
from amr_test_gui.ramp import FAULT, SteerRamp                # noqa: E402
from amr_test_gui.sim_bus import SimBus                       # noqa: E402

QUIET = (lambda *_: None)


def _drive_until(c, pred, timeout_s=6.0):
    t0 = time.monotonic()
    st = c.tick()
    while not pred(st) and time.monotonic() - t0 < timeout_s:
        time.sleep(0.03)
        st = c.tick()
    return st


# ── #H1 피드백 staleness ────────────────────────────────────────────────────
def test_stale_feedback_faults_and_cuts_drive():
    """RX 가 죽어 실측이 굳으면 램프가 FAULT 로 수렴하고 구동이 끊겨야 한다.

    수정 전: backend 가 pos 를 None 으로 되돌리지 않아 SETTLED·구동 허용이 영구 유지됐다.
    """
    c = AmrTestController(logger=QUIET)
    bus = SimBus(steer_rate_dps=2000.0, logger=QUIET)
    c.connect(lambda: bus)
    try:
        c.set_speed_mmps(50.0)
        c.set_mode("forward")
        st = _drive_until(c, lambda s: s["ramp_state"] == "SETTLED")
        assert st["raw_units"] != 0, "선행 조건(주행 중) 미충족"
        bus.recv = lambda timeout=0.1: None            # RX 사망 주입
        st = _drive_until(c, lambda s: s["ramp_state"] == FAULT, timeout_s=10.0)
        assert st["ramp_state"] == FAULT, "낡은 피드백으로 계속 주행했다"
        assert st["raw_units"] == 0 and not st["drive_allowed"]
        assert "피드백 미수신" in st["ramp_detail"]
    finally:
        c.disconnect()


def test_ramp_sets_deadline_when_feedback_lost_while_settled():
    """SETTLED 에서 피드백이 끊겨도 기한이 서서 FAULT 로 간다(수정 전엔 영구 SETTLED)."""
    r = SteerRamp(step_deg=30.0, step_timeout_s=2.0)
    r.tick(0.0, 0.0)                                   # 0° 정착 → SETTLED
    assert r.state == "SETTLED"
    r.tick(None, 1.0)
    out = r.tick(None, 10.0)
    assert out.state == FAULT and "피드백 미수신" in out.detail


# ── #H3 브링업 중 E-STOP 보존 ───────────────────────────────────────────────
def test_estop_survives_connect_and_is_applied_to_backend():
    c = AmrTestController(logger=QUIET)
    c.estop(True)
    c.connect(lambda: SimBus(logger=QUIET))
    try:
        assert c._estop is True, "connect 가 E-STOP 을 지웠다"
        st = c.tick()
        assert st["estop"] is True and st["raw_units"] == 0
        c.set_mode("forward")                          # E-stop 중 모드 전환을 시도해도
        st = _drive_until(c, lambda s: True, timeout_s=1.0)
        assert st["raw_units"] == 0, "E-STOP 중인데 구동 지령이 나갔다"
    finally:
        c.disconnect()


# ── #H4 브링업 실패 시 backend 정리 ─────────────────────────────────────────
def test_failed_bringup_leaves_no_backend_threads():
    before = {t.name for t in threading.enumerate()}
    c = AmrTestController(logger=QUIET)
    with pytest.raises(NodeSilent):
        c.connect(lambda: SimBus(silent_nodes=(4,), logger=QUIET))
    time.sleep(0.6)
    leaked = [t.name for t in threading.enumerate()
              if t.name.startswith("tongyi") and t.name not in before]
    assert leaked == [], f"브링업 실패 후 backend 스레드 잔존: {leaked}"


# ── #M3 E-STOP 중 램프 동결 ─────────────────────────────────────────────────
def test_estop_freezes_ramp_instead_of_faulting():
    """E-STOP 은 정상 조작이다 — 그 자체로 추종 실패 FAULT 를 만들면 안 된다."""
    c = AmrTestController(logger=QUIET)
    c.connect(lambda: SimBus(steer_rate_dps=25.0, logger=QUIET))
    try:
        c.set_mode("crab_left")
        _drive_until(c, lambda s: s["ramp_state"] == "RAMPING", timeout_s=2.0)
        c.estop(True)
        t0 = time.monotonic()
        st = None
        while time.monotonic() - t0 < 6.0:             # 기한(4s)보다 길게 유지
            st = c.tick()
            assert st["ramp_state"] != FAULT, f"E-STOP 중 spurious FAULT: {st['ramp_detail']}"
            time.sleep(0.03)
        assert st["raw_units"] == 0
    finally:
        c.disconnect()


def test_freeze_holds_command_and_blocks_drive():
    r = SteerRamp(step_deg=30.0, step_timeout_s=2.0)
    r.set_target(90.0)
    r.tick(0.0, 0.0)                                   # → 지령 30°
    cmd = r.commanded_deg
    for t in range(1, 60):                             # 기한을 훌쩍 넘겨 동결 유지
        out = r.freeze(float(t))
        assert out.state != FAULT
        assert out.commanded_deg == cmd and not out.drive_allowed
    assert r.tick(cmd, 60.0).state != FAULT, "동결 해제 직후 기한이 이미 만료돼 있었다"


# ── #C1 Space 키 E-STOP (포커스 무관) ───────────────────────────────────────
@pytest.fixture(scope="module")
def qapp():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_space_engages_estop_regardless_of_focus(qapp):
    """모드 버튼에 포커스가 있어도 Space 는 E-STOP 을 체결해야 한다.

    수정 전: QPushButton 이 Space 를 소비해 E-STOP 미체결 + **직전 주행 지령 재발행**.
    """
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest

    from amr_test_gui.ui_main import MainWindow
    w = MainWindow(dry_run=True, seer_ip="127.0.0.1")
    w.dialogs_enabled = False   # 모달 대화상자는 이벤트 루프를 블로킹한다
    try:
        w.show()
        w._set_controls_enabled(True)
        btn = w.mode_buttons["forward"]
        clicks = []
        btn.clicked.connect(lambda: clicks.append(1))
        btn.setFocus()
        QTest.qWait(50)
        QTest.keyClick(w, Qt.Key_Space)
        QTest.qWait(60)
        assert w.btn_estop.isChecked(), "포커스가 버튼에 있으면 Space 가 E-STOP 에 닿지 않는다"
        assert clicks == [], "Space 가 주행 버튼을 재클릭했다(정지 대신 지령 재발행)"
    finally:
        w.close()


def test_space_never_releases_estop(qapp):
    """키보드는 체결 전용 — 이미 체결된 E-STOP 을 Space 로 풀 수 없어야 한다."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest

    from amr_test_gui.ui_main import MainWindow
    w = MainWindow(dry_run=True, seer_ip="127.0.0.1")
    w.dialogs_enabled = False   # 모달 대화상자는 이벤트 루프를 블로킹한다
    try:
        w.show()
        w.btn_estop.setChecked(True)
        w._on_estop()
        assert w.controller._estop is True
        QTest.keyClick(w, Qt.Key_Space)
        QTest.qWait(60)
        assert w.btn_estop.isChecked() and w.controller._estop is True, \
            "Space 가 E-STOP 을 해제했다"
    finally:
        w.close()


def test_control_takeover_requires_usb_connection_first(qapp):
    """USB 연결과 제어권 획득은 분리되어야 하고, 순서가 강제되어야 한다.

    한 버튼이 둘을 동시에 하면 운전자가 판다 상태를 보기도 전에 릴레이를 뺏게 된다
    (사용자 지시 2026-07-27 "기본적으로 연결과 제어권 획득은 분리되어야 함").
    """
    from amr_test_gui.ui_main import MainWindow
    w = MainWindow(dry_run=True, seer_ip="127.0.0.1")
    w.dialogs_enabled = False   # 모달 대화상자는 이벤트 루프를 블로킹한다
    try:
        w.show()
        assert not w.btn_connect.isEnabled(), "USB 연결 전인데 제어권 획득 버튼이 활성이다"
        assert w.btn_usb_on.isEnabled() and not w.btn_usb_off.isEnabled()
        w._on_connect()                       # 순서를 어긴 직접 호출
        assert not w.controller.connected, "USB 없이 제어권을 획득했다"
        w._on_usb_connect()
        assert w._usb_ok and w.btn_connect.isEnabled(), "USB 연결 후 제어권 버튼이 열리지 않았다"
    finally:
        w.close()


def test_usb_disconnect_refused_while_holding_control(qapp):
    """제어권을 쥔 채 USB 를 닫으면 릴레이가 intercept 로 남는다 → 거부해야 한다."""
    from amr_test_gui.ui_main import MainWindow
    w = MainWindow(dry_run=True, seer_ip="127.0.0.1")
    w.dialogs_enabled = False   # 모달 대화상자는 이벤트 루프를 블로킹한다
    try:
        w.show()
        w._on_usb_connect()
        w.controller.connect(lambda: SimBus(logger=QUIET))
        assert w.controller.connected
        w._on_usb_disconnect()                 # 거부되어야 함
        assert w._usb_ok, "제어권 보유 중인데 USB 가 해제됐다"
        w.controller.disconnect()
        w._on_usb_disconnect()                 # release 후에는 허용
        assert not w._usb_ok
    finally:
        w.close()


def test_buttons_do_not_take_focus(qapp):
    """Space 소비 자체를 없애는 2차 방어."""
    from PyQt5.QtCore import Qt

    from amr_test_gui.ui_main import MainWindow
    w = MainWindow(dry_run=True, seer_ip="127.0.0.1")
    w.dialogs_enabled = False   # 모달 대화상자는 이벤트 루프를 블로킹한다
    try:
        for name, b in [(k, v) for k, v in w.mode_buttons.items()] + \
                       [("home", w.btn_home), ("estop", w.btn_estop)]:
            assert b.focusPolicy() == Qt.NoFocus, f"{name} 버튼이 포커스를 가져간다"
    finally:
        w.close()


# ── #H2 브링업 중 창 종료 ───────────────────────────────────────────────────
def test_close_during_bringup_still_releases_bus(qapp):
    """연결 중 창을 닫아도 제어권이 반환되고 backend 스레드가 남지 않아야 한다."""
    from PyQt5.QtCore import QTimer

    from amr_test_gui.ui_main import MainWindow

    class SlowBus(SimBus):
        def __init__(self, **kw):
            super().__init__(**kw)
            time.sleep(1.2)

    shut = []
    w = MainWindow(dry_run=True, seer_ip="127.0.0.1")
    w.dialogs_enabled = False   # 모달 대화상자는 이벤트 루프를 블로킹한다
    before = {t.name for t in threading.enumerate()}
    try:
        def factory():
            b = SlowBus(logger=QUIET)
            orig = b.shutdown
            b.shutdown = lambda: (shut.append(1), orig())
            return b
        w._bus_factory = factory
        w.show()
        w._on_usb_connect()          # 1단계 — 제어권 획득의 선행 조건
        w._on_connect()
        QTimer.singleShot(250, w.close)
        QTimer.singleShot(9000, qapp.quit)
        qapp.exec_()
        time.sleep(0.4)
        assert shut, "브링업 중 종료했는데 bus.shutdown(=release) 이 호출되지 않았다"
        assert not w.controller.connected
        leaked = [t.name for t in threading.enumerate()
                  if t.name.startswith("tongyi") and t.name not in before]
        assert leaked == [], f"backend 스레드 잔존: {leaked}"
    finally:
        w.close()


# ── #M9 dry-run 이 PP 컨트롤워드를 요구하는가 ───────────────────────────────
def test_simbus_requires_controlword_to_latch_steer_target():
    """0x607A 만으로 조향이 움직이면 컨트롤워드 누락 회귀를 dry-run 이 못 잡는다."""
    from types import SimpleNamespace

    from amr_test_gui.motor_control_import import protocol as P
    bus = SimBus(logger=QUIET)
    tgt = 7871815 + 1000
    f = P.sdo_write(3, P.OBJ_TARGET_POSITION, tgt, size=4)
    bus.send(SimpleNamespace(arbitration_id=f.can_id, data=f.data, is_remote_frame=False))
    assert bus._steer_target[3] != tgt, "0x6040 없이 0x607A 만으로 목표가 적용됐다"
    f2 = P.sdo_write(3, P.OBJ_CONTROLWORD, P.CW_STEER_SETPOINT, size=2)
    bus.send(SimpleNamespace(arbitration_id=f2.can_id, data=f2.data, is_remote_frame=False))
    assert bus._steer_target[3] == tgt, "0x6040=0x3F 를 받고도 목표가 래치되지 않았다"
