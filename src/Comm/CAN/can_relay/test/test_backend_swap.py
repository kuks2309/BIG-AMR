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
