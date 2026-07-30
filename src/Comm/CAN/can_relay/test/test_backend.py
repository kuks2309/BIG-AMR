"""백엔드 회귀 — MockLink 로 실기 없이 제어 루프 전체를 고정한다.

여기서 고정하는 성질은 전부 "없으면 사고가 나는 것"이다:
  · 워치독이 지령을 만료시킨다
  · 정지는 어떤 상태에서도 받아들여지고 즉시 나간다
  · 지령은 주기 재송신된다(단발 아님)
  · 제어권 없이는 프레임이 나가지 않는다
  · 호밍 중에는 조향 지령을 받지 않는다
"""
import time

import pytest

from can_relay import protocol as P
from can_relay import safety as S
from can_relay.backend import RelayBackend, RelayConfig
from can_relay.link import LinkError, MockLink


def make(**kw):
    cfg = RelayConfig(cmd_hz=100.0, poll_hz=50.0, cmd_timeout_s=0.15, **kw)
    link = MockLink()
    link.open()
    link.acquire()
    return link, RelayBackend(link, cfg)


def idx_of(frame):
    return frame.data[1] | (frame.data[2] << 8)


def writes_to(link, index):
    return [f for f in link.sent if idx_of(f) == index and f.data[0] != 0x40]


def wait(cond, timeout=2.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if cond():
            return True
        time.sleep(0.01)
    return False


# ── 제어권 ────────────────────────────────────────────────────────────────
def test_cannot_send_without_authority():
    link = MockLink()
    link.open()
    be = RelayBackend(link, RelayConfig())
    with pytest.raises(RuntimeError):
        be.start()


def test_mock_link_refuses_frames_before_acquire():
    link = MockLink()
    link.open()
    with pytest.raises(LinkError):
        link.send([P.sdo_read(1, 0x6064)])


def test_double_start_is_refused():
    link, be = make()
    be.start()
    try:
        with pytest.raises(RuntimeError):
            be.start()
    finally:
        be.shutdown()


# ── 워치독 ────────────────────────────────────────────────────────────────
def test_watchdog_zeroes_drive_when_commands_stop():
    link, be = make()
    be.start()
    try:
        be.set_drive_mmps(50.0)
        assert wait(lambda: be.snapshot()["drive_units"] != 0)
        assert wait(lambda: be.snapshot()["drive_units"] == 0, timeout=2.0)
        assert be.snapshot()["watchdog_trips"] >= 1
    finally:
        be.shutdown()


def test_watchdog_keeps_command_while_refreshed():
    link, be = make()
    be.start()
    try:
        for _ in range(12):
            be.set_drive_mmps(50.0)
            time.sleep(0.02)
        assert be.snapshot()["drive_units"] != 0
    finally:
        be.shutdown()


def test_nonfinite_command_is_rejected_and_does_not_refresh_watchdog():
    """NaN 을 계속 퍼블리시하는 노드가 워치독을 무한 연장하면 안 된다."""
    link, be = make()
    be.start()
    try:
        be.set_drive_mmps(50.0)
        assert wait(lambda: be.snapshot()["drive_units"] != 0)
        for _ in range(20):
            with pytest.raises(S.UnsafeCommand):
                be.set_drive_mmps(float("nan"))
            time.sleep(0.02)
        assert be.snapshot()["drive_units"] == 0
    finally:
        be.shutdown()


# ── 정지 ──────────────────────────────────────────────────────────────────
def test_stop_sends_zero_immediately_not_next_tick():
    link, be = make()
    be.start()
    try:
        be.set_drive_mmps(50.0)
        before = len(writes_to(link, P.OBJ_TARGET_VELOCITY))
        be.stop("시험")
        after = writes_to(link, P.OBJ_TARGET_VELOCITY)
        assert len(after) > before
        assert int.from_bytes(after[-1].data[4:8], "little", signed=True) == 0
    finally:
        be.shutdown()


def test_stop_is_accepted_even_when_loop_never_started():
    """폴링이 죽었거나 시작 전이어도 정지는 거부되지 않는다."""
    link, be = make()
    be.stop("루프 미기동")
    zeros = writes_to(link, P.OBJ_TARGET_VELOCITY)
    assert zeros and all(
        int.from_bytes(f.data[4:8], "little", signed=True) == 0 for f in zeros)


def test_stop_target_is_zero_even_without_authority():
    """제어권이 없으면 프레임은 못 내지만, 지령 자체는 반드시 0 으로 확정된다."""
    link = MockLink()
    link.open()
    be = RelayBackend(link, RelayConfig())
    be._drive_units = 1234
    be.stop("권한 없음")
    assert be.snapshot()["drive_units"] == 0
    assert link.sent == []              # 게이트에 막힐 프레임을 헛되이 내지 않는다


def test_shutdown_is_idempotent():
    link, be = make()
    be.start()
    be.shutdown()
    be.shutdown()                       # 두 번째는 조용히 지나가야 한다
    assert be.snapshot()["drive_units"] == 0


def test_stop_does_not_touch_steering():
    """조향 0° 복귀는 그 자체로 100° 스윙이 될 수 있다 — 정지는 구동만 만진다."""
    link, be = make()
    be.set_steer_deg(45.0)
    target_before = be.snapshot()["steer_target_deg"]
    be.stop("시험")
    assert be.snapshot()["steer_target_deg"] == target_before


def test_estop_latches_and_blocks_new_drive_commands():
    link, be = make()
    be.start()
    try:
        be.estop(True)
        be.set_drive_mmps(200.0)
        time.sleep(0.05)
        assert be.snapshot()["drive_units"] == 0
        assert be.snapshot()["estop"] is True
    finally:
        be.shutdown()


def test_shutdown_sends_stop_before_stopping_thread():
    link, be = make()
    be.start()
    be.set_drive_mmps(50.0)
    time.sleep(0.05)
    be.shutdown()
    last = writes_to(link, P.OBJ_TARGET_VELOCITY)[-1]
    assert int.from_bytes(last.data[4:8], "little", signed=True) == 0


# ── 재송신 ────────────────────────────────────────────────────────────────
def test_drive_command_is_resent_periodically():
    """단발 송신이면 프레임 하나 유실로 정지가 사라진다."""
    link, be = make()
    be.start()
    try:
        time.sleep(0.2)
        assert len(writes_to(link, P.OBJ_TARGET_VELOCITY)) > 3
    finally:
        be.shutdown()


def test_heartbeat_is_sent_by_control_loop():
    """심박이 끊기면 펌웨어가 릴레이를 풀어 버린다."""
    link, be = make()
    be.start()
    try:
        assert wait(lambda: link.heartbeats >= 2, timeout=2.0)
    finally:
        be.shutdown()


# ── 조향 ──────────────────────────────────────────────────────────────────
def test_steer_command_is_clamped_at_frame_generation():
    link, be = make()
    applied = be.set_steer_deg(200.0)
    assert applied == 90.0
    be.start()
    try:
        assert wait(lambda: writes_to(link, P.OBJ_TARGET_POSITION))
        f = writes_to(link, P.OBJ_TARGET_POSITION)[-1]
        counts = int.from_bytes(f.data[4:8], "little", signed=True)
        assert counts == S.DEFAULT_STEER_HOME[f.can_id - 0x600] + \
            int(round(90.0 * 57344))
    finally:
        be.shutdown()


def test_steer_sends_setpoint_controlword():
    link, be = make()
    be.set_steer_deg(10.0)
    be.start()
    try:
        assert wait(lambda: writes_to(link, P.OBJ_CONTROLWORD))
        cw = writes_to(link, P.OBJ_CONTROLWORD)[-1]
        assert cw.data[4] == P.CW_STEER_SETPOINT
    finally:
        be.shutdown()


def test_steer_rejected_during_homing():
    link, be = make()
    be._homing = True
    with pytest.raises(S.UnsafeCommand):
        be.set_steer_deg(10.0)


# ── 피드백 ────────────────────────────────────────────────────────────────
def feed(link, node, index, value, size=4, sub=0):
    cmd = {1: 0x4F, 2: 0x4B, 4: 0x43}[size]
    payload = (value & 0xFFFFFFFF).to_bytes(4, "little")[:size]
    data = bytes([cmd, index & 0xFF, index >> 8, sub]) + payload
    link.inbox.append((0x580 + node, data + b"\x00" * (8 - len(data)), 2))


def test_steer_angle_is_none_until_statusword_says_homed():
    link, be = make()
    feed(link, 3, P.OBJ_POSITION_ACTUAL, S.DEFAULT_STEER_HOME[3])
    be._drain()
    assert be.steer_angles_deg()[3] is None          # 상태워드 없음 → 신뢰 불가

    feed(link, 3, P.OBJ_STATUSWORD, 0x1050, size=2)  # bit15=0 = 호밍 중
    be._drain()
    assert be.steer_angles_deg()[3] is None

    feed(link, 3, P.OBJ_STATUSWORD, 0x9450, size=2)  # bit15=1
    be._drain()
    assert be.steer_angles_deg()[3] == pytest.approx(0.0, abs=1e-6)


def test_steer_angle_none_when_feedback_expired():
    link, be = make()
    be.cfg.feedback_ttl_s = 0.05
    feed(link, 3, P.OBJ_POSITION_ACTUAL, S.DEFAULT_STEER_HOME[3])
    feed(link, 3, P.OBJ_STATUSWORD, 0x9450, size=2)
    be._drain()
    assert be.steer_angles_deg()[3] is not None
    time.sleep(0.1)
    assert be.steer_angles_deg()[3] is None


def test_homing_zero_position_does_not_leak_as_minus_137_deg():
    """호밍 중 0x6064=0 을 그대로 환산하면 ≈−137° 가 상위로 흘러간다."""
    link, be = make()
    feed(link, 3, P.OBJ_STATUSWORD, 0x1050, size=2)
    feed(link, 3, P.OBJ_POSITION_ACTUAL, 0)
    be._drain()
    assert be.steer_angles_deg()[3] is None
    naive = (0 - S.DEFAULT_STEER_HOME[3]) / S.COUNTS_PER_DEG
    assert naive < -130.0                              # 게이트가 없으면 이 값이 나간다


def test_abort_is_counted_and_surfaced():
    link, be = make()
    data = bytes([0x80, 0x7A, 0x60, 0x00]) + (0x08000022).to_bytes(4, "little")
    link.inbox.append((0x583, data, 2))
    be._drain()
    snap = be.snapshot()
    assert snap["nodes"][3]["aborts"] == 1
    assert snap["nodes"][3]["last_abort"] == 0x08000022


def test_digital_input_subindex_one_is_stored():
    link, be = make()
    feed(link, 3, P.OBJ_DIGITAL_INPUT, 0x09, size=2, sub=1)
    be._drain()
    assert be.snapshot()["nodes"][3]["digital_input"] == 0x09


def test_frames_from_other_bus_are_ignored():
    link, be = make()
    data = bytes([0x43, 0x64, 0x60, 0x00]) + (1234).to_bytes(4, "little")
    link.inbox.append((0x581, data, 0))                # bus 0 = Seer 측
    be._drain()
    assert be.snapshot()["nodes"][1]["position"] is None


# ── 브링업 ────────────────────────────────────────────────────────────────
def test_bringup_is_off_by_default():
    """실기 검증 이력이 없는 경로라 기본값이 꺼져 있어야 한다."""
    assert RelayConfig().allow_bringup is False


def test_bringup_sends_no_homing_trigger():
    link, be = make(allow_bringup=True)
    be.start()
    try:
        assert not writes_to(link, P.OBJ_VENDOR_60FB)
    finally:
        be.shutdown()
