"""백엔드 2종이 **같은 계약**을 만족하는가 + `direct` 가 원본과 **같은 바이트**를 내는가.

ADR `docs/adr/2026-08-04-amr-test-gui-swappable-backend.md` §Verification 2·3.

`direct` 는 판다를 열어야 조작이 되지만, **프레임을 만드는 부분은 순수 계산**이라 하드웨어 없이
바이트를 검사할 수 있다. 여기서는 장치를 열지 않는다(`_send` 를 가로챈다).
"""
import importlib.util
import os

import pytest

from can_relay.link import _find_repo_root
from can_relay.ui import backend_base as B
from can_relay.ui.backend_direct import DirectBackend

pytest.importorskip("PyQt5", reason="PyQt5 미설치 — 원본 GUI 를 로드할 수 없다")

_ORIG = os.path.join(_find_repo_root(__file__), "Tools", "amr_test_gui", "gui.py")


def _load_original():
    if not os.path.isfile(_ORIG):
        raise AssertionError(f"원본을 찾지 못했다: {_ORIG}")
    spec = importlib.util.spec_from_file_location("orig_gui_swap", _ORIG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


orig = _load_original()


class _SpyDirect(DirectBackend):
    """`_send` 만 가로챈다 — 장치를 열지 않고 프레임을 모은다."""

    def __init__(self):
        super().__init__()
        self.frames = []

    def _send(self, frames):
        for f in frames:
            self.frames.append((f.can_id, bytes(f.data[:8])))


def _orig_bytes(node, idx, val, size, sub=0):
    """원본 `gui.py:840-849` 의 손조립 규칙 그대로."""
    cmd = {1: 0x2F, 2: 0x2B, 4: 0x23}[size]
    payload = (val & 0xFFFFFFFF).to_bytes(4, "little")[:size]
    data = bytes([cmd, idx & 0xFF, idx >> 8, sub]) + payload + b"\x00" * (4 - size)
    return (0x600 + node, data[:8])


# ── 계약 ──────────────────────────────────────────────────────────────────
def test_both_backends_implement_the_contract():
    """UI 가 부르는 메서드가 두 백엔드에 모두 있는가."""
    rclpy = pytest.importorskip("rclpy", reason="ROS2 미소싱 — ros2 백엔드 생략")
    from can_relay.ui.backend_ros2 import Ros2Backend
    need = ("meas_angle", "motor_rows", "status", "settled", "scan", "set_usb",
            "set_engaged", "stop", "home", "steer_axis", "steer_all", "drive",
            "start", "shutdown", "can", "why_not")
    for cls in (DirectBackend, Ros2Backend):
        for m in need:
            assert callable(getattr(cls, m, None)), f"{cls.__name__} 에 {m} 없음"
        assert isinstance(cls.capabilities, frozenset) and cls.capabilities
        assert cls.name in ("direct", "ros2")


def test_capabilities_differ_exactly_where_expected():
    """검색·USB 는 direct 만, 나머지 조작은 둘 다."""
    rclpy = pytest.importorskip("rclpy", reason="ROS2 미소싱 — ros2 백엔드 생략")
    from can_relay.ui.backend_ros2 import Ros2Backend
    only_direct = {B.CAP_SCAN, B.CAP_USB}
    assert only_direct <= DirectBackend.capabilities
    assert not (only_direct & Ros2Backend.capabilities)
    common = {B.CAP_ENGAGE, B.CAP_STOP, B.CAP_HOME, B.CAP_STEER_AXIS,
              B.CAP_STEER_ALL, B.CAP_DRIVE, B.CAP_MOTOR_TABLE}
    assert common <= DirectBackend.capabilities
    assert common <= Ros2Backend.capabilities


def test_homing_cancel_is_not_a_capability():
    """취소는 어느 백엔드에도 capability 로 없다 — UI 가 노출하지 않기로 했다."""
    assert not hasattr(B, "CAP_HOME_CANCEL")


# ── direct ↔ 원본 바이트 동일 ─────────────────────────────────────────────
@pytest.mark.parametrize("node", [3, 4])
@pytest.mark.parametrize("deg", [0.0, 15.0, -30.0, 45.0, 90.0, -90.0, 200.0])
def test_direct_steer_axis_matches_original(node, deg):
    be = _SpyDirect()
    be.steer_axis(node, deg)
    _applied, counts = orig.steer_counts(node, deg)
    assert be.frames == [_orig_bytes(node, 0x607A, counts, 4),
                         _orig_bytes(node, 0x6040, 0x3F, 2)]


@pytest.mark.parametrize("deg", [0.0, 45.0, 90.0])
def test_direct_steer_all_matches_original(deg):
    be = _SpyDirect()
    be.steer_all(deg)
    want = []
    for n in (3, 4):
        _a, counts = orig.steer_counts(n, deg)
        want += [_orig_bytes(n, 0x607A, counts, 4), _orig_bytes(n, 0x6040, 0x3F, 2)]
    assert be.frames == want


@pytest.mark.parametrize("mmps,sign", [(0, -1), (50, -1), (50, +1), (200, -1), (10_000, +1)])
def test_direct_drive_matches_original(mmps, sign):
    be = _SpyDirect()
    be.drive(sign * mmps)
    units = orig.drive_units(mmps, sign)
    assert be.frames == [_orig_bytes(1, 0x60FF, units, 4),
                         _orig_bytes(2, 0x60FF, units, 4)]


@pytest.mark.parametrize("label", list(orig.JOG))
def test_direct_jog_direction_matches_original(label):
    """조그 8방향 — 조향+구동 프레임이 원본과 같은 바이트·같은 순서인가."""
    steer_deg, sign, _v = orig.JOG[label]
    be = _SpyDirect()
    be.steer_all(steer_deg)
    be.drive(sign * 50.0)
    want = []
    for n in (3, 4):
        _a, counts = orig.steer_counts(n, steer_deg)
        want += [_orig_bytes(n, 0x607A, counts, 4), _orig_bytes(n, 0x6040, 0x3F, 2)]
    units = orig.drive_units(50.0, sign)
    want += [_orig_bytes(1, 0x60FF, units, 4), _orig_bytes(2, 0x60FF, units, 4)]
    assert be.frames == want


def test_direct_constants_match_original():
    """상수를 옮기면서 값이 바뀌지 않았는가."""
    from can_relay.ui import backend_direct as D
    assert D.STEER_HOME == orig.STEER_HOME
    assert D.COUNTS_PER_DEG == orig.COUNTS_PER_DEG
    assert (D.VEL_PER_MMPS, D.VEL_MAX_UNITS) == (orig.VEL_PER_MMPS, orig.VEL_MAX_UNITS)
    assert D.STEER_LIMIT_DEG == orig.STEER_LIMIT_DEG
    assert (D.SEER_GATE, D.CAN_KBPS) == (orig.SEER_GATE, orig.CAN_KBPS)
    assert (D.SEER_BUS, D.MOTOR_BUS) == (orig.SEER_BUS, orig.MOTOR_BUS)


def test_direct_jog_table_matches_original():
    """UI 의 조그 방향표가 원본과 같은 값인가(부호가 뒤집히면 로봇이 반대로 간다)."""
    from can_relay.ui.app import JOG
    assert JOG == orig.JOG


def test_direct_homing_frames_match_original():
    """호밍 3프레임 — 원본 `_homing_run` 과 같은 객체·값·순서."""
    be = _SpyDirect()
    be.panda = object()          # `_send` 를 가로챘으므로 내용은 쓰이지 않는다
    be._run = True
    try:
        be.home()
    except Exception:
        pass                     # `_wait_homed` 는 피드백이 없어 실패한다 — 프레임만 본다
    # 원본도 호밍 **전에 구동 0** 을 먼저 보낸다(`gui.py:954` `self._drive(0)`).
    # 그 2프레임을 빼먹으면 「시퀀스가 다르다」가 아니라 기대값이 틀린 것이다.
    want = [_orig_bytes(1, 0x60FF, 0, 4), _orig_bytes(2, 0x60FF, 0, 4)]
    for n in (3, 4):
        want += [_orig_bytes(n, 0x6040, 0x86, 2),
                 _orig_bytes(n, 0x6099, 2500, 4),
                 _orig_bytes(n, 0x60FB, 1, 1, sub=4)]
    assert be.frames[:len(want)] == want, "호밍 시퀀스가 원본과 다르다"


# ── 2026-08-04 리뷰 Medium·Low 조치 회귀 ────────────────────────────────
def test_scan_reports_actual_panda_count():
    """판다 2대 이상일 때 **대수와 시리얼**을 보고해야 한다(리뷰 Medium ①).

    비우기 전에 잡지 않으면 `len([]) or '여러'` 가 되어 실제 대수가 사라진다.
    """
    class _Two:
        @staticmethod
        def list():
            return ["AAA", "BBB", "CCC"]

    from can_relay.ui import backend_direct as D
    be = DirectBackend()
    orig_cls = D._panda_class
    D._panda_class = lambda: _Two
    try:
        ok, why = be.scan()
    finally:
        D._panda_class = orig_cls
    assert ok is False, "1 PC 1대 원칙 위반인데 통과시켰다"
    assert "3대" in why, f"실제 대수가 사라졌다: {why}"
    assert "AAA" in why and "CCC" in why, f"시리얼이 빠졌다: {why}"


def test_direct_steer_home_comes_from_canonical_yaml():
    """`--backend direct` 도 정본 YAML 을 봐야 한다 — 원본과 같은 출처(리뷰 Medium ②)."""
    from can_relay.ui import backend_direct as D
    assert "정본 YAML" in D.STEER_HOME_SOURCE, D.STEER_HOME_SOURCE
    assert D.STEER_HOME == orig.STEER_HOME, "원본과 이식본의 조향 0° 가 다르다"


def test_direct_steer_home_fallback_is_announced(monkeypatch):
    """정본을 못 읽으면 **그 사실이 출처에 남아야** 한다(조용한 사본 사용 금지)."""
    from can_relay.ui import backend_direct as D
    monkeypatch.setattr(D, "_find_repo_root", lambda _p: "/nonexistent")
    home, src = D._load_steer_home()
    assert home == D._STEER_HOME_FALLBACK
    assert "코드 사본" in src and "⚠" in src


def test_app_inner_thread_functions_have_distinct_names():
    """스택 트레이스에서 구분되도록 내부 함수 이름이 달라야 한다(리뷰 Low ④)."""
    import inspect
    from can_relay.ui import app as A
    src = inspect.getsource(A)
    assert src.count("def work(") == 0
    assert "def _op_work(" in src and "def _clearfatal_work(" in src


def test_ui_layer_has_no_estop_wiring():
    """UI 계층에 E-stop 배선이 **없어야** 한다(리뷰 Medium ③·④, 사용자 결정: 죽은 경로 삭제).

    원본 `gui.py` 에 E-stop 이 없고 이 이식본의 계약은 「UI 100% 동일」이다. 배선만 남아 있으면
    ① 아무도 호출하지 않는 죽은 코드이고 ② 누군가 버튼을 붙이면 ros2 는 되고 direct 는 죽었다.
    드라이버의 `~/estop` 은 별개 계약이라 살아 있다 — `test_estop_latch_blocks_drive` 가 고정한다.
    """
    import inspect
    from can_relay.ui import app as A, backend_base as B, backend_direct as D, backend_ros2 as R
    for mod in (A, B, D, R):
        code = "\n".join(l for l in inspect.getsource(mod).splitlines()
                         if not l.lstrip().startswith("#"))
        assert "estop" not in code.lower(), f"{mod.__name__} 에 E-stop 배선이 남아 있다"
    for cls in (B.BackendBase, D.DirectBackend, R.Ros2Backend):
        assert not hasattr(cls, "estop"), f"{cls.__name__}.estop 이 남아 있다"
    assert not hasattr(B, "CAP_ESTOP")


def test_driver_estop_contract_survives():
    """UI 배선을 지워도 **드라이버의 E-stop 은 그대로**여야 한다(범위를 넘겨 지우지 않았는지)."""
    from can_relay.backend import RelayBackend
    from can_relay import driver_node as DN
    assert hasattr(RelayBackend, "estop"), "드라이버 백엔드의 estop 을 잘못 지웠다"
    assert hasattr(DN.CanRelayNode, "_on_estop"), "드라이버의 estop 구독 콜백을 잘못 지웠다"


# ── Seer 인수인계 (2026-08-04 사용자 운영 철학) ──────────────────────────
def test_port_release_restores_steering_to_seer_baseline(monkeypatch):
    """이식본도 **반환 전에 Seer 기준으로 조향을 되돌린 뒤** 넘겨야 한다(원본과 같은 절차)."""
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PyQt5.QtWidgets")
    from can_relay.ui import app as A

    win = A.MainWindow.__new__(A.MainWindow)          # 위젯 생성 없이 로직만 본다
    sent, logs = [], []
    class _Be:
        def meas_angle(self, n): return {3: 10.0, 4: 12.0}[n]
        def steer_axis(self, n, d): sent.append((n, d))
        def set_engaged(self, on): return (True, f"engaged={on}")
    win.be = _Be()
    win._seer_at_take = {3: 10.0, 4: 12.0}
    win.log_line = type("S", (), {"emit": staticmethod(lambda m: logs.append(m))})()
    ok, why = win._release_with_handover()
    assert sorted(sent) == [(3, 10.0), (4, 12.0)], f"복원 지령이 나가지 않았다: {sent}"
    assert ok and "engaged=False" in why, (ok, why)
    assert any("인수인계 복원" in m for m in logs), logs


def test_port_release_does_not_move_without_baseline():
    """기준이 없으면 움직이지 않고 반환한다 — 모르는 채로 3톤 차체를 돌리지 않는다."""
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PyQt5.QtWidgets")
    from can_relay.ui import app as A

    win = A.MainWindow.__new__(A.MainWindow)
    sent, logs = [], []
    class _Be:
        def meas_angle(self, n): return 0.0
        def steer_axis(self, n, d): sent.append((n, d))
        def set_engaged(self, on): return (True, "ok")
    win.be = _Be()
    win._seer_at_take = {}
    win.log_line = type("S", (), {"emit": staticmethod(lambda m: logs.append(m))})()
    win._release_with_handover()
    assert sent == [], f"기준이 없는데 조향을 움직였다: {sent}"
    assert any("생략" in m for m in logs), logs


def test_port_take_path_records_baseline_and_release_path_uses_handover():
    """**배선** 확인 — `_on_take` 가 획득 시 기준을 기억하고 반환 시 인수인계 경로를 탄다.

    ⚠ 같은 날 두 번(M5·원본 복원) 「함수는 있는데 배선이 없어」 돌연변이를 못 잡았다.
    """
    import inspect
    from can_relay.ui import app as A
    src = inspect.getsource(A.MainWindow._on_take)
    assert "_seer_at_take" in src, "획득 시 Seer 기준을 기억하지 않는다"
    assert "_release_with_handover" in src, "반환이 인수인계 경로를 타지 않는다"


def test_port_refresh_runs_the_agreement_check():
    """이식본도 **주기 갱신마다** CAN ↔ Seer 를 대조해야 한다(원본과 같은 절차).

    ⚠ 배선을 본다 — 오늘만 세 번, 함수는 있는데 호출이 없어 돌연변이를 못 잡았다.
    """
    import inspect
    from can_relay.ui import app as A
    src = inspect.getsource(A.MainWindow._refresh)
    assert "_check_seer_agreement" in src, "주기 갱신이 대조를 부르지 않는다"
    assert hasattr(A.MainWindow, "_check_seer_agreement")


def test_every_steer_send_site_marks_the_flag():
    """조향을 보내는 **모든 지점**이 `_steer_commanded` 를 세워야 한다.

    ⚠ 2026-08-05: 축별 경로에만 넣고 조그 경로(`steer_all`)를 빠뜨렸다. 한 곳이라도 빠지면
    그 경로로 움직인 뒤 대조가 계속 열려 거짓 경보가 난다.
    """
    import inspect, re
    from can_relay.ui import app as A
    src = inspect.getsource(A)
    sites = [(i, ln) for i, ln in enumerate(src.splitlines())
             if re.search(r"self\.be\.steer_(axis|all)\(", ln)]
    assert sites, "조향 송신 지점을 찾지 못했다 — 이 시험을 갱신하라"
    lines = src.splitlines()
    for i, ln in sites:
        window = "\n".join(lines[max(0, i - 4):i + 1])
        assert "_steer_commanded = True" in window, (
            f"{i+1}행 조향 송신에 `_steer_commanded = True` 가 없다: {ln.strip()}")


def test_direct_backend_ttl_is_adjustable_like_ros2(monkeypatch):
    """신선도 TTL 은 **백엔드와 무관하게 같은 방식으로 조정**돼야 한다(리뷰 Low ③).

    ros2 는 ROS 파라미터를 매 호출 재조회해 `ros2 param set` 이 즉시 먹는다. direct 는
    모듈 상수를 직접 읽어 런타임 조정이 불가능했다 — 같은 개념인데 한쪽만 바뀌었다.
    """
    import time as _t
    from can_relay.ui.backend_direct import DirectBackend, MEAS_TTL_S

    be = DirectBackend.__new__(DirectBackend)
    be.meas_ttl_s = 10.0
    be._meas_deg = {3: 5.0}
    be._meas_at = {3: _t.monotonic() - 2.0}          # 2초 전 값
    assert be.meas_angle(3) == 5.0, "TTL 10초인데 2초 된 값을 버렸다"

    be.meas_ttl_s = 1.0                              # 런타임 조정
    assert be.meas_angle(3) is None, "TTL 을 줄였는데 여전히 옛 값을 쓴다"

    # 생성자 기본값은 모듈 상수와 같다(계약 유지)
    import inspect
    sig = inspect.signature(DirectBackend.__init__)
    assert sig.parameters["meas_ttl_s"].default == MEAS_TTL_S


# ── 백엔드 연결 표시 (2026-08-05 사용자 지적) ─────────────────────────────
def test_both_backends_expose_link_status():
    """두 백엔드 모두 `link_status()` 로 **연결 여부**를 내놔야 한다.

    ⚠ 사용자 지적: 「can relay 연결 확인이 없음 — 연결 표시되어야 함 화면에」.
    예전에는 백엔드 상태가 로그에만 나가 드라이버가 죽었는지 로봇이 이상한지 구분이 안 됐다.
    `status()`(로봇이 정상인가) 와 `link_status()`(말이 통하는가) 는 다른 질문이다.
    """
    from can_relay.ui.backend_base import BackendBase
    from can_relay.ui.backend_direct import DirectBackend
    from can_relay.ui.backend_ros2 import Ros2Backend
    assert hasattr(BackendBase, "link_status")
    for cls in (DirectBackend, Ros2Backend):
        assert cls.link_status is not BackendBase.link_status, f"{cls.__name__} 미구현"


def test_direct_link_status_follows_the_panda():
    be = DirectBackend.__new__(DirectBackend)
    be.panda = None
    ok, text = be.link_status()
    assert ok is False and "미연결" in text, (ok, text)
    be.panda = object(); be._serials = ["1e003e00"]
    ok, text = be.link_status()
    assert ok is True and "연결됨" in text and "1e003e00" in text, (ok, text)


def test_ros2_link_status_follows_diagnostics_freshness():
    from can_relay.ui.backend_ros2 import Ros2Backend
    be = Ros2Backend.__new__(Ros2Backend)

    class _Node:
        cfg = {"driver_ns": "/can_relay_node"}
        def __init__(self, fresh): self._fresh = fresh
        def diagnostics(self): return (0, "ok", self._fresh, {})
    be.node = _Node(True)
    ok, text = be.link_status()
    assert ok is True and "연결됨" in text and "/can_relay_node" in text, (ok, text)
    be.node = _Node(False)
    ok, text = be.link_status()
    assert ok is False and "끊김" in text, (ok, text)


def test_status_bar_shows_the_link():
    """상태 바가 **화면에** 연결을 보여야 한다 — 로그에만 있으면 안 된다(배선)."""
    import inspect
    from can_relay.ui import app as A
    assert "lab_link" in inspect.getsource(A.MainWindow._build_status)
    assert "_refresh_link" in inspect.getsource(A.MainWindow._refresh), \
        "주기 갱신이 연결 표시를 갱신하지 않는다"
    assert "link_status" in inspect.getsource(A.MainWindow._refresh_link)


# ── 탭 2개 구성 (2026-08-05 사용자 요청) ─────────────────────────────────
@pytest.fixture(scope="module")
def qapp():
    """위젯을 만들려면 QApplication 이 **먼저** 있어야 한다 — 없으면 프로세스가 죽는다."""
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
    yield QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _fake_panel(holds=False, seer_enabled=True):
    """MainWindow 대신 쓰는 최소 대역 — 탭 컨테이너의 규칙만 본다."""
    from PyQt5.QtWidgets import QWidget

    class _P(QWidget):
        def __init__(self):
            super().__init__()
            self.seer_on = None
            self.released = []
            self._holds = holds
        def set_seer_polling(self, on): self.seer_on = bool(on)
        def holds_hardware(self): return self._holds
        def log(self, msg): pass
        def safe_release(self, reason=""): self.released.append(reason)
    return _P()


def test_tabs_poll_seer_only_on_the_visible_tab(qapp):
    """Seer API 를 두 곳에서 두드리지 않는다 — **보이는 탭만** 폴링한다."""
    from can_relay.ui.app import RelayTabs
    a, b = _fake_panel(), _fake_panel()
    tabs = RelayTabs({"A": a, "B": b})
    assert (a.seer_on, b.seer_on) == (True, False), (a.seer_on, b.seer_on)
    tabs.tabs.setCurrentIndex(1)
    assert (a.seer_on, b.seer_on) == (False, True), (a.seer_on, b.seer_on)


def test_tabs_lock_the_other_tab_while_one_holds_the_panda(qapp):
    """**판다는 한 곳만 열 수 있다.** 한 탭이 붙들면 다른 탭을 잠근다.

    ⚠ 근거: 2026-08-05 실기에서 다른 제어 주체와 겹쳐 USB 송신이 **36회 연속 실패**했다.
    """
    from can_relay.ui.app import RelayTabs
    a, b = _fake_panel(holds=True), _fake_panel()
    tabs = RelayTabs({"A": a, "B": b})
    tabs._apply_exclusive_lock()
    assert tabs.tabs.isTabEnabled(0) is True, "붙든 탭이 잠겼다"
    assert tabs.tabs.isTabEnabled(1) is False, "다른 탭이 잠기지 않았다"
    a._holds = False                                   # 해제하면 풀린다
    tabs._apply_exclusive_lock()
    assert tabs.tabs.isTabEnabled(1) is True


def test_tabs_release_both_panels(qapp):
    """종료는 한 곳으로 모으고 **양쪽을 다** 해제한다."""
    from can_relay.ui.app import RelayTabs
    a, b = _fake_panel(), _fake_panel()
    RelayTabs({"A": a, "B": b}).safe_release("시험")
    assert a.released == ["시험"] and b.released == ["시험"]


def test_entry_point_defaults_to_two_tabs():
    """진입점 기본이 탭 2개여야 한다(배선)."""
    import inspect
    from can_relay.ui import gui_node
    src = inspect.getsource(gui_node.main)
    assert 'default="both"' in inspect.getsource(gui_node) or '"both"' in src
    assert "RelayTabs" in src, "진입점이 탭 컨테이너를 쓰지 않는다"


# ── 조향 재송신 (2026-08-05 실기 관측) ───────────────────────────────────
def test_direct_backend_resends_the_steer_target():
    """조향 목표를 **상태로 남겨 재송신**해야 한다 — 단발이면 프레임 1장 유실이 지령 소실이다.

    ⚠ 2026-08-05 실기: 조그 첫 지령에서 N4 가 움직이지 않았다(SDO 거부 없음, 코드 경로 정상).
    마스터 Seer 는 조향 목표를 **28 ms 주기로 연속 재송신**한다(캡처 12,928회/180초).
    구동은 이미 재송신하고 있었는데(원본 High ③ 조치) 조향만 빠져 있었다.
    """
    from can_relay.ui.backend_direct import DirectBackend
    be = DirectBackend.__new__(DirectBackend)
    be._steer_counts = {}
    sent = []
    be._send = lambda frames: sent.extend(frames)
    be.steer_axis(3, 10.0)
    assert be._steer_counts and 3 in be._steer_counts, "조향 목표를 상태로 남기지 않는다"
    assert sent, "즉시 송신도 해야 한다"


def test_direct_backend_releases_steer_target_on_stop():
    """정지하면 조향 목표 **재송신을 멈춘다** — 안 멈추면 정지 후에도 계속 나간다."""
    from can_relay.ui.backend_direct import DirectBackend
    be = DirectBackend.__new__(DirectBackend)
    be._steer_counts = {3: 1, 4: 2}
    be._run = False                       # 제어권 없음 경로로 빠져도 해제는 먼저다
    be.stop()
    assert be._steer_counts == {}, "정지 후에도 조향 목표가 남아 재송신된다"


def test_poll_loop_resends_steer_in_source():
    """폴 루프가 실제로 재송신하는가(배선)."""
    import inspect
    from can_relay.ui import backend_direct as D
    src = inspect.getsource(D.DirectBackend._loop)
    assert "_steer_counts" in src and "steer_target_frames" in src, \
        "폴 루프가 조향을 재송신하지 않는다"


# ── 호밍 버튼은 제어권을 쥐고 있을 때만 (2026-08-15 사용자 요청) ──────────────
# 호밍은 조향 드라이브의 내부 루틴(0x60FB:04)이라 릴레이로 버스를 쥐고 있어야 성립하고,
# 조그와 달리 Seer 쪽 대체 경로가 없다 — Seer 제어 API(2000·2001·2002·2003·2010·
# 2022~2025)에 조향 호밍이 없다. 그래서 못 누르게 하고 이유를 보여 준다.
class _Btn:
    """`btn_home` 대역 — 위젯 트리 없이 활성/툴팁만 본다."""
    def __init__(self, enabled=False):
        self._on, self.tip = enabled, None
    def isEnabled(self): return self._on
    def setEnabled(self, on): self._on = bool(on)
    def setToolTip(self, t): self.tip = t


def _win_with_home_button(can_home=True, homing=False):
    from can_relay.ui import app as A
    win = A.MainWindow.__new__(A.MainWindow)        # 위젯 생성 없이 로직만 본다
    win.btn_home = _Btn()
    win._homing = homing
    win.be = type("BE", (), {"can": staticmethod(lambda cap: can_home)})()
    return win


def test_home_button_is_disabled_until_control_is_acquired():
    win = _win_with_home_button()
    win._sync_home_button(False)
    assert win.btn_home.isEnabled() is False
    assert "제어권" in win.btn_home.tip, win.btn_home.tip
    win._sync_home_button(True)
    assert win.btn_home.isEnabled() is True
    assert not win.btn_home.tip, "누를 수 있으면 사유가 남아 있으면 안 된다"


def test_home_button_stays_disabled_while_homing():
    """제어권이 있어도 호밍 중에는 못 누른다 — 재진입을 버튼 단에서 막는다."""
    win = _win_with_home_button(homing=True)
    win._sync_home_button(True)
    assert win.btn_home.isEnabled() is False
    assert "호밍 진행 중" in win.btn_home.tip, win.btn_home.tip


def test_home_button_untouched_when_backend_cannot_home():
    """capability 로 이미 막힌 버튼은 건드리지 않는다 — 그 사유 툴팁을 덮으면 안 된다."""
    win = _win_with_home_button(can_home=False)
    win.btn_home.setToolTip("이 백엔드는 호밍을 쓰지 않습니다")
    win._sync_home_button(True)
    assert win.btn_home.isEnabled() is False
    assert win.btn_home.tip == "이 백엔드는 호밍을 쓰지 않습니다"


def test_homing_click_without_control_says_what_to_do():
    """버튼을 우회해 들어와도 막고, **백엔드 내부 사정이 아니라** 할 일을 말한다."""
    from can_relay.ui import app as A
    win = A.MainWindow.__new__(A.MainWindow)
    win._homing, win._jog_th, win._ops = False, None, []
    win._engaged = lambda: False
    win.log = win._ops.append
    win._run_op = lambda *a, **k: win._ops.append(("run_op", a))
    win._homing_clicked()
    assert any("제어권을 먼저 획득" in str(m) for m in win._ops), win._ops
    assert not any(isinstance(m, tuple) for m in win._ops), "호밍이 실제로 나가면 안 된다"


def test_home_button_state_has_a_single_owner():
    """`_on_op_done` 이 버튼을 다시 켜면 안 된다 — 제어권을 놓은 뒤 켜져 버린다."""
    import inspect
    from can_relay.ui import app as A
    src = inspect.getsource(A.MainWindow._on_op_done)
    tail = src.split('"호밍"')[-1]
    assert "btn_home.setEnabled" not in tail, \
        "호밍 완료 분기가 버튼을 직접 켠다 — 상태 소유자가 둘이 된다"


def test_refresh_drives_the_home_button_every_cycle():
    """상태 동기를 주기 갱신이 돌려야 한다 — 이벤트에만 걸면 제어권 상실을 놓친다."""
    import inspect
    from can_relay.ui import app as A
    assert "_sync_home_button" in inspect.getsource(A.MainWindow._refresh)
