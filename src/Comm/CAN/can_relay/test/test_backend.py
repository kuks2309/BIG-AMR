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
    kw.setdefault("require_homed_for_steer", False)
    kw.setdefault("steer_home", {3: 7871815, 4: 7840086})   # 코드 기본값 없음 → 명시
    cfg = RelayConfig(cmd_hz=100.0, poll_hz=50.0, cmd_timeout_s=0.15, **kw)
    link = MockLink()
    link.open()
    link.acquire()
    return link, RelayBackend(link, cfg)


def make_homed(**kw):
    """호밍 **성공 경로**를 끝까지 도는 백엔드.

    `home()` 은 완료 후 조향 0° 복귀까지 확인하므로(ADR 2026-08-08), 폴마다 응답하는
    대역이 필요하다 — `MockLink.inbox` 는 한 번 소비되면 비어 「피드백 없음」이 된다.
    두 조향축을 0°(= `steer_home`)에 세워 둔다. 0° 복귀 자체의 회귀는
    `test_steer_zero_return.py` 소관이고, 여기서는 **호밍 경로가 막히지 않는 것**만 본다.
    """
    from conftest import FeedingLink

    kw.setdefault("require_homed_for_steer", False)
    home = kw.setdefault("steer_home", {3: 7871815, 4: 7840086})
    kw.setdefault("steer_zero_timeout_s", 1.0)
    cfg = RelayConfig(cmd_hz=100.0, poll_hz=50.0, cmd_timeout_s=0.15, **kw)
    link = FeedingLink()
    link.open()
    link.acquire()
    for n, counts in home.items():
        link.hold(n, counts)
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
        assert counts == {3: 7871815, 4: 7840086}[f.can_id - 0x600] + \
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
    feed(link, 3, P.OBJ_POSITION_ACTUAL, 7871815)
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
    feed(link, 3, P.OBJ_POSITION_ACTUAL, 7871815)
    feed(link, 3, P.OBJ_STATUSWORD, 0x9450, size=2)
    be._drain()
    assert be.steer_angles_deg()[3] is not None
    time.sleep(0.1)
    assert be.steer_angles_deg()[3] is None


def test_homing_zero_position_is_not_trusted_firmware_path():
    """홈이 0 이 아닌 기체(firmware 경로)에서 호밍 중 0x6064=0 은 ≈−137° 로 누설된다."""
    link, be = make(homing_method="firmware", steer_home={3: 7871815, 4: 7840086})
    feed(link, 3, P.OBJ_STATUSWORD, 0x1050, size=2)     # bit15=0 → 호밍 중
    feed(link, 3, P.OBJ_POSITION_ACTUAL, 0)
    be._drain()
    assert be.steer_angles_deg()[3] is None
    naive = (0 - 7871815) / S.COUNTS_PER_DEG
    assert naive < -130.0                               # 게이트가 없으면 이 값이 나간다


def test_homing_zero_position_is_not_trusted_method35_path():
    """method 35 에서는 홈이 0 이라 누설값이 0° 로 **그럴듯해 보인다** — 더 위험하다.

    숫자만 보면 정상이므로 사람이 못 걸러낸다. 상태워드 게이트가 유일한 방어다.
    """
    link, be = make(steer_home={3: 0, 4: 0})            # method 35 성립 시의 홈 = 0
    feed(link, 3, P.OBJ_STATUSWORD, 0x1050, size=2)     # bit15=0 → 호밍 중
    feed(link, 3, P.OBJ_POSITION_ACTUAL, 0)
    be._drain()
    naive = (0 - 0) / S.COUNTS_PER_DEG
    assert naive == 0.0                                 # 그럴듯하다
    assert be.steer_angles_deg()[3] is None             # 그래도 내보내지 않는다


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


# ── 펌웨어 호밍 시퀀서 (②) ───────────────────────────────────────────────
# 시험은 항상 유한 시간에 끝나야 한다 — 폴 주기·타임아웃을 작게 고정한다.
HOME_KW = dict(poll_s=0.01, timeout_s=2.0)


def test_home_uses_firmware_sequencer_not_direct_sdo():
    """SDO 로 0x60FB 를 직접 보내면 취소가 불가능해진다 — 그 경로를 쓰지 않는다."""
    link, be = make_homed(homing_method="firmware")
    be.start()
    try:
        link.homing_script = [MockLink.homing_state(1), MockLink.homing_state(4),
                              MockLink.homing_state(5, elapsed_s=31, reached_mask=3)]
        ok, why = be.home(**HOME_KW)
        assert ok is True and "DONE" in why
        assert not writes_to(link, P.OBJ_VENDOR_60FB)      # 직접 SDO 송신 0건
        assert any(s.startswith("homing_start") for s in link.log)
    finally:
        be.shutdown()


def test_home_reports_firmware_refusal_without_falling_back():
    """펌웨어가 거부하면 덜 안전한 경로로 미끄러지지 않는다."""
    link, be = make(homing_method="firmware")
    be.start()
    try:
        link.homing = MockLink.homing_state(4)      # 진행 중이라 재시작 거부
        ok, why = be.home(**HOME_KW)
        assert ok is False and "거부" in why
        assert not writes_to(link, P.OBJ_VENDOR_60FB)
    finally:
        be.shutdown()


def test_home_failure_when_link_lacks_sequencer_is_explicit():
    class NoSeq(MockLink):
        def homing_start(self, speed=0):
            raise NotImplementedError

    link = NoSeq(); link.open(); link.acquire()
    be = RelayBackend(link, RelayConfig(homing_method="firmware"))
    be.start()
    try:
        ok, why = be.home(**HOME_KW)
        assert ok is False and "취소 수단이 없다" in why
    finally:
        be.shutdown()


def test_home_times_out_and_cancels_instead_of_hanging():
    """종료 상태가 오지 않아도 무한 대기하지 않고 **취소를 걸고** 실패로 끝난다."""
    link, be = make(homing_method="firmware")
    be.start()
    try:
        link.homing_script = [MockLink.homing_state(4)]      # WAIT 에서 멈춤
        ok, why = be.home(poll_s=0.01, timeout_s=0.2)
        assert ok is False and "초과" in why and "취소" in why
        assert "homing_cancel" in link.log
    finally:
        be.shutdown()


@pytest.mark.parametrize("state,ok", [(5, True), (6, False), (7, False), (10, False)])
def test_only_done_is_success(state, ok):
    link, be = make_homed(homing_method="firmware")
    be.start()
    try:
        link.homing_script = [MockLink.homing_state(state, elapsed_s=5)]
        assert be.home(**HOME_KW)[0] is ok
    finally:
        be.shutdown()


def test_cancel_home_is_accepted_and_sends_cancel():
    link, be = make(homing_method="firmware")
    link.homing_start()
    ok, why = be.cancel_home()
    assert ok is True and "수리" in why
    assert "homing_cancel" in link.log
    assert link.homing_status()["state_name"] == "ERR_ABORT"


def test_cancel_home_survives_link_without_support():
    class NoSeq(MockLink):
        def homing_cancel(self):
            raise NotImplementedError

    link = NoSeq(); link.open(); link.acquire()
    be = RelayBackend(link, RelayConfig(homing_method="firmware"))
    ok, why = be.cancel_home()
    assert ok is False and "취소 요청 실패" in why


def test_steer_still_rejected_during_firmware_homing():
    link, be = make()
    be._homing = True
    with pytest.raises(S.UnsafeCommand):
        be.set_steer_deg(10.0)


# ── 모터 계층 계약 (/motor/low_cmd, raw) ─────────────────────────────────
def mc(mid, mode=None, tvel=0, tpos=0, pvel=30000):
    # 축 종류에 맞는 mode 를 기본값으로 — 상류 translator 가 그렇게 보낸다.
    if mode is None:
        mode = P.MODE_VELOCITY if mid in (1, 2) else P.MODE_POSITION
    return (mid, mode, tvel, tpos, pvel)


# ── H5·H6: 노드별 구동 · mode 분기 ───────────────────────────────────────
def test_drive_wheels_keep_independent_values():
    """제자리 선회는 두 구동륜이 **반대 부호**여야 성립한다(H5).

    예전에는 첫 값 하나로 뭉개서 node2 지령이 조용히 버려졌다 — 선회가 직진이 됐다.
    """
    link, be = homed()
    notes = be.set_motor_cmds([mc(1, tvel=+1000), mc(2, tvel=-1000)])
    assert notes == []
    assert be.snapshot()["drive_units_by_node"] == {1: 1000, 2: -1000}
    be.start()
    try:
        assert wait(lambda: len(writes_to(link, P.OBJ_TARGET_VELOCITY)) >= 2)
        vals = {f.can_id - 0x600: int.from_bytes(f.data[4:8], "little", signed=True)
                for f in writes_to(link, P.OBJ_TARGET_VELOCITY)}
        assert vals[1] == 1000 and vals[2] == -1000      # 부호가 살아서 나간다
    finally:
        be.shutdown()


def test_steer_rejects_velocity_mode():
    """조향축에 VELOCITY 가 오면 미설정 target_pos(0)가 위치 지령이 돼 한계까지 스윙한다(H6)."""
    link, be = homed()
    notes = be.set_motor_cmds([mc(3, mode=P.MODE_VELOCITY, tvel=500)])
    assert any("VELOCITY" in n and "거부" in n for n in notes)
    assert 3 not in be._steer_counts


def test_drive_rejects_position_mode():
    link, be = homed()
    notes = be.set_motor_cmds([mc(1, mode=P.MODE_POSITION, tpos=12345)])
    assert any("POSITION" in n and "거부" in n for n in notes)
    assert be.snapshot()["drive_units_by_node"] == {}


def test_mode_disabled_is_ignored():
    link, be = homed()
    notes = be.set_motor_cmds([mc(1, mode=P.MODE_DISABLED, tvel=999)])
    assert any("DISABLED" in n for n in notes)
    assert be.snapshot()["drive_units_by_node"] == {}


def test_mode_constants_match_upstream_msg():
    """상류 `trnav_msgs/MotorCmd.msg` 의 enum 과 값이 같아야 한다."""
    assert (P.MODE_DISABLED, P.MODE_VELOCITY, P.MODE_POSITION, P.MODE_TORQUE) == (0, 1, 2, 3)


def test_watchdog_clears_per_node_drive():
    link, be = homed()
    be.start()
    try:
        be.set_motor_cmds([mc(1, tvel=500), mc(2, tvel=-500)])
        assert wait(lambda: be.snapshot()["drive_units_by_node"] != {})
        assert wait(lambda: be.snapshot()["drive_units_by_node"] == {}, timeout=2.0)
    finally:
        be.shutdown()


def homed(**kw):
    kw.setdefault("steer_home", {3: 0, 4: 0})   # raw 계산을 읽기 쉽게 — 기본값 변경 무관
    link, be = make(require_homed_for_steer=True, **kw)
    be._homed = True
    return link, be


def test_low_cmd_accepts_differential_steer_angles():
    """**선회가 통과해야 한다** — bicycle 정의가 전·후 각이 다른 것이다.

    구 cmd_vel 경로의 1.0° 편차 게이트는 최소 선회반경 68.8 m 를 강제해
    액션 서버 9종 중 6종을 무력화했다(2026-07-31-004). 그 게이트가 없어야 한다.
    """
    link, be = homed()
    notes = be.set_motor_cmds([mc(3, tpos=+1_000_000), mc(4, tpos=-1_000_000)])
    assert notes == []                       # 편차 때문에 거부하지 않는다
    snap = be.snapshot()
    assert snap["nodes"] is not None
    be.start()
    try:
        assert wait(lambda: len(writes_to(link, P.OBJ_TARGET_POSITION)) >= 2)
        vals = {f.can_id - 0x600: int.from_bytes(f.data[4:8], "little", signed=True)
                for f in writes_to(link, P.OBJ_TARGET_POSITION)}
        assert vals[3] != vals[4]             # 전·후 각이 다르게 나간다
    finally:
        be.shutdown()


def test_low_cmd_is_raw_no_unit_conversion():
    """환산하지 않는다 — 받은 raw 가 그대로 0x60FF/0x607A 로 나간다."""
    link, be = homed()
    be.set_motor_cmds([mc(1, mode=1, tvel=1234), mc(3, tpos=55555)])
    be.start()
    try:
        assert wait(lambda: writes_to(link, P.OBJ_TARGET_VELOCITY))
        v = writes_to(link, P.OBJ_TARGET_VELOCITY)[-1]
        assert int.from_bytes(v.data[4:8], "little", signed=True) == 1234
        p = [f for f in writes_to(link, P.OBJ_TARGET_POSITION) if f.can_id == 0x603][-1]
        assert int.from_bytes(p.data[4:8], "little", signed=True) == 55555
    finally:
        be.shutdown()


def test_low_cmd_still_clamps_steering_in_raw():
    """계층이 내려가도 ±steer_limit 보호는 유지된다 (raw counts 로)."""
    link, be = homed()
    huge = 99_000_000
    notes = be.set_motor_cmds([mc(3, tpos=huge)])
    assert any("클램프" in n for n in notes)
    limit_c = int(round(90.0 * S.COUNTS_PER_DEG))
    assert be._steer_counts[3] == 0 + limit_c          # 홈 0 기준 +90°


def test_low_cmd_still_clamps_drive_in_raw():
    link, be = homed()
    notes = be.set_motor_cmds([mc(1, mode=1, tvel=999_999)])
    assert any("클램프" in n for n in notes)
    assert be.snapshot()["drive_units"] == S.VEL_MAX_UNITS


def test_low_cmd_rejects_steer_before_homing():
    link, be = make(require_homed_for_steer=True)       # _homed = False
    notes = be.set_motor_cmds([mc(3, tpos=1000)])
    assert any("호밍 미완료" in n for n in notes)
    assert 3 not in be._steer_counts


def test_low_cmd_ignores_unknown_motor_id():
    link, be = homed()
    notes = be.set_motor_cmds([mc(9, tpos=1000)])
    assert any("배선에 없다" in n for n in notes)


def test_low_cmd_refreshes_watchdog():
    link, be = homed()
    be.start()
    try:
        for _ in range(12):
            be.set_motor_cmds([mc(1, mode=1, tvel=500)])
            time.sleep(0.02)
        assert be.snapshot()["drive_units"] == 500
    finally:
        be.shutdown()


def test_motor_states_shape_matches_contract():
    """MotorState 필드를 빠짐없이 채운다 — 상류 translator 가 그대로 읽는다."""
    link, be = make()
    s = be.motor_states()
    assert [d["motor_id"] for d in s] == [1, 2, 3, 4]
    need = {"motor_id", "fb_vel", "fb_pos", "error_code", "amps", "voltage",
            "home_comp", "homing", "motor_enabled", "can_reset"}
    assert need <= set(s[0])
    assert s[0]["can_reset"] is True          # 피드백 없으면 리셋으로 표시


# ── homing method 35 (상류식, 장비별 캘리브레이션) ───────────────────────
M35 = dict(homing_method="35", homing_enabled=True,
           steer_home_offset={3: 7871815, 4: 7840086},
           home_search_range=(-10_000_000, 10_000_000))


# 실기 실측 상태워드는 조향축 정지 시 **0x9450** 이다(bit15·12·10·6·4).
# ⚠ 기본값에 **bit15 를 반드시 넣는다.** 예전 기본값은 bit10 만이라 `position_trustworthy` 가
#   False 를 냈고, debt-040 게이트를 넣자 「위치를 믿을 수 없다」로 걸렸다 — 픽스처가 실기와
#   달랐던 것이지 코드가 틀린 게 아니었다(2026-08-05).
STATUSWORD_STEER_IDLE = 0x9450


def at(link, node, pos, sw=STATUSWORD_STEER_IDLE):
    feed(link, node, P.OBJ_POSITION_ACTUAL, pos)
    feed(link, node, P.OBJ_STATUSWORD, sw, size=2)


def test_m35_refused_until_home_offset_is_measured():
    """`homing_enabled: false` 면 바퀴를 **움직이기 전에** 막힌다."""
    link, be = make(homing_method="35", homing_enabled=False,
                    steer_home_offset={3: 1, 4: 2})
    be.start()
    try:
        ok, why = be.home(**HOME_KW)
        assert ok is False and "실측 확정되지 않았다" in why
        assert not writes_to(link, P.OBJ_TARGET_POSITION)   # 이동 프레임 0건
    finally:
        be.shutdown()


def test_m35_refused_when_encoder_outside_expected_range():
    """미측정 전제(전원 사이클 재현성)를 검출하는 게이트 — 범위 밖이면 안 움직인다."""
    link, be = make(**{**M35, "home_search_range": (0, 100)})
    be.start()
    try:
        at(link, 3, 9_000_000); at(link, 4, 9_000_000)
        be._drain()
        ok, why = be.home(**HOME_KW)
        assert ok is False and "예상 범위" in why
        assert not writes_to(link, P.OBJ_TARGET_POSITION)
    finally:
        be.shutdown()


def test_m35_refused_when_position_unknown():
    """피드백이 없으면 호밍하지 않는다 — 모르는 것을 안다고 치지 않는다."""
    link, be = make(**M35)
    be.start()
    try:
        ok, why = be.home(**HOME_KW)
        assert ok is False and "현재 위치를 모른다" in why
    finally:
        be.shutdown()


def test_m35_refuses_to_unlock_when_rezero_unverified():
    """0x6098=35 를 보냈어도 0x6064 가 0 근처가 아니면 **잠금을 유지한다**(C4)."""
    link, be = make(**M35)
    be.start()
    try:
        at(link, 3, 7871815); at(link, 4, 7840086)
        be._drain()
        ok, why = be.home(poll_s=0.01, timeout_s=2.0)
        assert ok is False and "재영점 미확인" in why
        assert be.snapshot()["homed"] is False
    finally:
        be.shutdown()


def test_m35_refuses_to_unlock_when_drive_aborts_0x6098():
    """드라이브가 0x6098 을 거부하면 성공으로 보고하지 않는다(C4)."""
    link, be = make(**M35)
    be.start()
    try:
        at(link, 3, 7871815); at(link, 4, 7840086)
        be._drain()
        import threading as _th
        def _abort():
            time.sleep(0.15)
            d = bytes([0x80, 0x98, 0x60, 0x00]) + (0x08000022).to_bytes(4, "little")
            link.inbox.append((0x583, d, 2)); be._drain()
        _th.Thread(target=_abort, daemon=True).start()
        ok, why = be.home(poll_s=0.01, timeout_s=2.0)
        assert ok is False and "거부" in why
        assert be.snapshot()["homed"] is False
    finally:
        be.shutdown()


def test_m35_rezero_discards_stale_steer_target():
    """재영점 시 구 절대목표를 버린다 — 안 버리면 새 좌표계에서 수십 도로 재해석된다(C3)."""
    link, be = make(**M35)
    be._steer_counts = {3: 5_000_000, 4: 5_000_000}
    be.start()
    try:
        at(link, 3, 7871815); at(link, 4, 7840086); be._drain()
        import threading as _th
        def _rezero():
            time.sleep(0.15); at(link, 3, 0); at(link, 4, 0); be._drain()
        _th.Thread(target=_rezero, daemon=True).start()
        be.home(poll_s=0.01, timeout_s=2.0)
        assert 5_000_000 not in be._steer_counts.values()
    finally:
        be.shutdown()


def test_m35_full_sequence_matches_upstream_order():
    """상류 can_open.hpp:483-486 → :489 → :461 과 같은 순서·같은 객체."""
    link, be = make(**M35)
    be.start()
    try:
        at(link, 3, 7871815); at(link, 4, 7840086)      # 이미 목표에 도착해 있는 상태
        be._drain()
        # 0x6098=35 후 드라이브가 각도를 0 으로 만드는 것을 흉내낸다 —
        # 새 계약은 **재영점을 확인한 뒤에만** 잠금을 푼다(C4).
        import threading as _th
        def _rezero():
            time.sleep(0.15)
            at(link, 3, 0); at(link, 4, 0); be._drain()
        _th.Thread(target=_rezero, daemon=True).start()
        ok, why = be.home(poll_s=0.01, timeout_s=3.0)
        assert ok is True and "method 35" in why

        pos = writes_to(link, P.OBJ_TARGET_POSITION)
        vel = writes_to(link, P.OBJ_PROFILE_VELOCITY)
        cw = writes_to(link, P.OBJ_CONTROLWORD)
        method = writes_to(link, P.OBJ_HOMING_METHOD)
        assert int.from_bytes(pos[0].data[4:8], "little", signed=True) == 7871815
        assert int.from_bytes(vel[0].data[4:8], "little", signed=True) == 2500
        assert cw[0].data[4] == P.CW_STEER_SETPOINT
        assert len(method) == 2 and method[0].data[4] == 35   # 조향 2축 모두
        # 0x6098 은 반드시 이동·도착 **뒤에** 나가야 한다
        assert link.sent.index(method[0]) > link.sent.index(pos[0])
        assert be.snapshot()["homed"] is True
    finally:
        be.shutdown()


def test_m35_does_not_declare_home_before_arrival():
    """도착 못 하면 0x6098=35 를 절대 보내지 않는다 — 엉뚱한 자세가 0° 가 된다."""
    link, be = make(**M35)
    be.start()
    try:
        at(link, 3, 0); at(link, 4, 0)          # 목표에서 멀다
        be._drain()
        ok, why = be.home(poll_s=0.01, timeout_s=0.3)
        assert ok is False and "도착하지 못했다" in why
        assert not writes_to(link, P.OBJ_HOMING_METHOD)
        assert be.snapshot()["homed"] is False
    finally:
        be.shutdown()


def test_m35_requires_both_conditions_for_arrival():
    """상류와 같은 2조건 — bit10 만 서거나 위치만 맞아서는 도착이 아니다."""
    assert P.home35_reached(P.STATUSWORD_TARGET_REACHED, 100, 100, 50) is True
    assert P.home35_reached(0, 100, 100, 50) is False                # bit10 미설정
    assert P.home35_reached(P.STATUSWORD_TARGET_REACHED, 300, 100, 50) is False
    assert P.home35_reached(None, 100, 100, 50) is False             # 상태워드 미상
    assert P.home35_reached(P.STATUSWORD_TARGET_REACHED, None, 100, 50) is False


def test_steer_blocked_until_homed():
    """호밍 근거가 **하나도 없으면** 막는다.

    ⚠ 2026-08-04 계약 변경: 판정이 `_homed`(우리가 호밍했는가) 단독에서
    `homed_effective()`(우리 호밍 **또는** 드라이브가 보고하는 bit15)로 바뀌었다.
    Seer 가 호밍해 둔 상태를 놓쳐 실기에서 조향이 통째로 거부됐기 때문이다.
    여기서는 피드백 자체가 없어 두 근거 모두 없는 경우를 고정한다.
    """
    link, be = make(require_homed_for_steer=True)
    assert be.homed_effective() is False
    with pytest.raises(S.UnsafeCommand) as e:
        be.set_steer_deg(10.0)
    assert "조향 0° 기준을 확인할 수 없다" in str(e.value)
    assert "피드백 없음" in str(e.value) or "미수신" in str(e.value), str(e.value)
    be._homed = True
    assert be.set_steer_deg(10.0) == 10.0        # 우리가 호밍하면 통과


def test_m35_cancel_releases_our_steer_target_without_sending():
    """호밍 취소는 **우리 조향 목표를 놓는다** — 조향축에 프레임은 보내지 않는다.

    ⚠ 2026-08-05 계약 변경. 예전에는 현재 실측 위치를 새 목표로 써 넣어 축을 붙들었는데,
    그 방식은 벤더 매뉴얼·상류 구현·마스터 캡처 **어디에도 없는 것**이었다
    (`docs/claude-mistake/2026-08-05-001`). 이제 재송신만 멈춘다.
    ⚠ 드라이브가 이미 받은 목표까지는 못 세운다 — 알려진 제약이다.
    """
    link, be = make(**M35)
    at(link, 3, 7_871_815); at(link, 4, 7_840_086); be._drain()
    be._steer_counts = {3: 9_999_999, 4: 9_999_999}
    n_before = len(writes_to(link, P.OBJ_TARGET_POSITION))
    ok, why = be.cancel_home()
    assert ok is True
    assert len(writes_to(link, P.OBJ_TARGET_POSITION)) == n_before, \
        "조향축에 프레임을 보냈다 — 이제 보내지 않는 계약이다"
    assert be._steer_counts == {}, "우리 조향 목표가 남아 재송신된다"
    assert "homing_cancel" not in link.log


def test_release_steer_target_stops_resending():
    """놓으면 폴 루프가 우리 목표를 더 이상 재송신하지 않는다 — 이것이 실제 효과다."""
    link, be = make(**M35)
    be._steer_counts = {3: 9_999_999, 4: 9_999_999}
    n_before = len(writes_to(link, P.OBJ_TARGET_POSITION))
    assert be.release_steer_target("시험") is True        # 놓을 목표가 있었다
    assert be._steer_counts == {}
    assert len(writes_to(link, P.OBJ_TARGET_POSITION)) == n_before, "프레임을 보냈다"
    assert be.release_steer_target("두 번째") is False     # 이제 없다
    assert "걸어 둔 조향 목표가 없었다" in be.halt_note()


# ── E-stop 이 조향도 막는가 (H7) ─────────────────────────────────────────
def test_estop_blocks_steer_in_raw_path():
    link, be = homed()
    be.estop(True)
    notes = be.set_motor_cmds([mc(3, tpos=1000)])
    assert any("E-stop" in n for n in notes)
    assert 3 not in be._steer_counts


def test_estop_blocks_set_steer_deg():
    link, be = homed()
    be.estop(True)
    with pytest.raises(S.UnsafeCommand):
        be.set_steer_deg(10.0)


def test_estop_stops_resending_steer_setpoints():
    """E-stop 중에는 조향 setpoint 를 능동 재송신하지 않는다."""
    link, be = homed()
    be.set_motor_cmds([mc(3, tpos=1000), mc(4, tpos=1000)])
    be.start()
    try:
        assert wait(lambda: writes_to(link, P.OBJ_TARGET_POSITION))
        be.estop(True)
        n = len(writes_to(link, P.OBJ_TARGET_POSITION))
        time.sleep(0.3)
        assert len(writes_to(link, P.OBJ_TARGET_POSITION)) == n
    finally:
        be.shutdown()


# ── 송신 실패 시 심박 중단 (C1) ──────────────────────────────────────────
def test_heartbeat_stops_after_repeated_tx_failure():
    """지령을 못 내보내면 **심박도 끊어** 펌웨어 fail-safe 에 정지를 넘긴다."""
    class DeadTx(MockLink):
        def send(self, frames):
            raise LinkError("송신 불가(시험)")

    link = DeadTx(); link.open(); link.acquire()
    be = RelayBackend(link, RelayConfig(cmd_hz=100.0, tx_fail_halt=3,
                                        require_homed_for_steer=False))
    be.start()
    try:
        assert wait(lambda: be.snapshot()["hb_suppressed"] is True, timeout=3.0)
        hb = link.heartbeats
        time.sleep(0.3)
        assert link.heartbeats == hb            # 더 이상 심박이 나가지 않는다
        assert be.snapshot()["tx_fail_streak"] >= 3
    finally:
        be._running = False


def test_heartbeat_resumes_when_tx_recovers():
    link, be = make(tx_fail_halt=3)
    be.start()
    try:
        assert wait(lambda: link.heartbeats >= 2)
        assert be.snapshot()["hb_suppressed"] is False
    finally:
        be.shutdown()


# ── per-bus CAN 헬스 (③) ─────────────────────────────────────────────────
def health(**kw):
    d = {"bus_off": 0, "error_passive": 0, "error_warning": 0,
         "last_error_code": 0, "rec": 0, "tec": 0, "esr_reg": 0}
    d.update(kw)
    return d


def test_bus_health_is_polled_into_snapshot():
    link, be = make()
    link.health_fixture = {0: health(rec=3), 2: health(rec=7, tec=9)}
    be.start()
    try:
        assert wait(lambda: be.snapshot().get("bus_health"))
        snap = be.snapshot()
        assert snap["bus_health"][2]["rec"] == 7
        assert snap["health_supported"] is True
    finally:
        be.shutdown()


def test_health_polling_permanently_off_when_link_lacks_feature():
    """기능 부재(NotImplementedError)는 영구 비활성 — 매 틱 재시도할 이유가 없다."""
    class NoHealth(MockLink):
        def can_health(self, bus):
            raise NotImplementedError

    link = NoHealth(); link.open(); link.acquire()
    be = RelayBackend(link, RelayConfig(cmd_hz=100.0, health_hz=50.0))
    be.start()
    try:
        assert wait(lambda: be.snapshot().get("health_supported") is False)
        assert "지원하지 않는다" in be.snapshot()["health_error"]
    finally:
        be.shutdown()


def test_transient_health_failure_recovers_instead_of_latching_off():
    """일시적 실패 하나로 진단이 영구히 꺼지면 안 된다 — 픽스처가 붙으면 회복한다."""
    link, be = make(health_hz=50.0)        # 처음엔 픽스처 없음 → LinkError
    be.start()
    try:
        assert wait(lambda: be.snapshot().get("health_error"))
        assert be.snapshot()["health_supported"] is not False   # 영구 래치 아님
        link.health_fixture = {0: health(), 2: health(rec=5)}
        assert wait(lambda: be.snapshot().get("health_supported") is True)
        assert be.snapshot()["health_error"] is None
        assert be.snapshot()["bus_health"][2]["rec"] == 5
    finally:
        be.shutdown()


def test_health_polling_never_blocks_control_path():
    """읽기 전용이므로 실패해도 지령·정지는 계속 돈다."""
    link, be = make()          # 헬스 폴링은 실패한다
    be.start()
    try:
        be.set_drive_mmps(50.0)
        assert wait(lambda: be.snapshot()["drive_units"] != 0)
        be.stop("시험")
        assert be.snapshot()["drive_units"] == 0
    finally:
        be.shutdown()


@pytest.mark.parametrize("kw,expect", [
    (dict(bus_off=1, rec=255), "BUS-OFF"),
    (dict(error_passive=1, rec=140), "error-passive"),
    (dict(error_warning=1, rec=100), "error-warning"),
    (dict(), None),
])
def test_bus_fault_priority(kw, expect):
    link, be = make()
    be._bus_health = {2: health(**kw)}
    got = be.bus_fault()
    assert (expect in got) if expect else (got is None)


def test_bus_off_outranks_error_passive_on_other_bus():
    link, be = make()
    be._bus_health = {0: health(error_passive=1), 2: health(bus_off=1)}
    assert "BUS-OFF" in be.bus_fault()


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


# ── home() 진입·이탈 가드 (2026-08-03: 미검증 분기 4종) ────────────────────
#
# 아래 넷은 `backend.home()` 의 분기인데 회귀가 하나도 없었다. 전부 "없으면 사고가
# 나거나 오판정이 나는 것"이라 고정한다.

def test_home_refused_while_already_homing():
    """재진입 금지 — 진행 중 두 번째 호출이 시퀀서를 **건드리지 않고** 거부돼야 한다.

    통과시키면 같은 축에 개시 프레임이 두 번 나가고, 두 폴 루프가 같은 종료 상태를
    각자 소비해 완료 판정이 엇갈린다.
    """
    link, be = make(homing_method="firmware")
    be.start()
    try:
        be._homing = True
        before = len(link.log)
        ok, why = be.home(**HOME_KW)
        assert ok is False and "이미 호밍 중" in why
        assert len(link.log) == before, "거부인데 링크를 건드렸다"
    finally:
        be._homing = False
        be.shutdown()


def test_home_refused_when_backend_not_started():
    """미기동 상태 거부 — TX 루프가 없으면 취소도 못 내므로 개시해서는 안 된다."""
    link, be = make(homing_method="firmware")
    ok, why = be.home(**HOME_KW)
    assert ok is False and "기동" in why
    assert "homing_start" not in link.log


def test_home_cancels_when_backend_goes_down_mid_loop():
    """폴 도중 백엔드가 내려가면 **취소를 걸고** 실패로 끝난다 — 방치 금지.

    호스트가 사라져도 펌웨어가 스스로 취소를 내지만(`safety_seer_gate.h:360`),
    우리가 먼저 명시적으로 낸다. 그래야 종료 사유가 로그에 남는다.
    """
    link, be = make(homing_method="firmware")
    be.start()
    try:
        link.homing_script = [MockLink.homing_state(4)]      # WAIT 에서 계속 머문다
        # ⚠ `_running=False` 를 **미리** 두면 진입 가드("기동돼 있지 않다")에 걸려
        #   폴 루프까지 가지 않는다. 첫 폴이 끝난 뒤에 내려가야 이 분기가 검증된다.
        orig_status = link.homing_status

        def drop_after_first_poll():
            be._running = False
            return orig_status()

        link.homing_status = drop_after_first_poll
        ok, why = be.home(poll_s=0.01, timeout_s=5.0)
        assert ok is False and "내려갔" in why
        assert "homing_cancel" in link.log
    finally:
        be._running = True
        be.shutdown()


def test_home_clears_stale_statusword_before_starting():
    """개시 직전에 직전 상태워드를 **버린다** — 이게 없으면 지난 호밍의 완료를
    이번 호밍의 완료로 오독한다.

    완료 판정은 `0x6041` bit15 의 **하강 후 상승** 에지다(test_safety 의
    `test_homing_completes_only_after_seeing_zero_then_one`). 직전 값 bit15=1 이
    남아 있으면 에지 검출기가 이미 올라간 것으로 보고 첫 폴에서 완료를 선언할 수 있다.
    """
    link, be = make(homing_method="firmware")
    be.start()
    try:
        seen = {}

        orig = link.homing_start

        def spy(speed):
            # 시퀀서가 실제로 개시되는 순간의 상태워드를 잡는다
            seen["at_start"] = {n: st.statusword for n, st in be.nodes.items()}
            return orig(speed)

        link.homing_start = spy
        for st in be.nodes.values():
            st.statusword = 0x9450          # bit15=1 — 「호밍 완료」로 읽히는 직전 값
        link.homing_script = [MockLink.homing_state(5, elapsed_s=35)]
        be.home(**HOME_KW)

        assert seen, "homing_start 가 호출되지 않았다"
        assert all(v is None for v in seen["at_start"].values()), \
            f"개시 시점에 직전 상태워드가 남아 있다: {seen['at_start']}"
    finally:
        be.shutdown()


# ── 조향 게이트: 호밍의 **출처를 가리지 않는다** (2026-08-04 실기 발견) ──────
def _mark_homed_by_drive(be, homed=True, age_s=0.0):
    """드라이브가 0x6041 bit15 로 「호밍 완료」를 보고하는 상태를 만든다(= Seer 가 호밍한 경우)."""
    import time as _t
    from can_relay import safety as _S
    for n in be.cfg.steer_nodes:
        st = be.nodes[n]
        st.statusword = (_S.STATUSWORD_HOMED_BIT if homed else 0) | 0x0450
        st.position = be.cfg.steer_home[n]
        st.last_seen = _t.monotonic() - age_s


def test_steer_allowed_when_drive_reports_homed():
    """**Seer 가 호밍했으면 우리가 호밍하지 않았어도 조향할 수 있어야 한다.**

    2026-08-04 실기: 호밍 전 판독에서 N3·N4 상태워드가 이미 `0x9450`(bit15=1)이었는데도
    드라이버가 자기 프로세스 변수만 보고 조향을 통째로 거부해 **바퀴가 한 카운트도 움직이지
    않았다.** 「0° 기준을 모른다」는 전제도 같은 날 반증됐다 — 판다 직독과 Seer 판독이 0° 로
    교차 일치(−0.0° ↔ +0.0°)했고 정본 YAML 과 ±6 counts 였다.
    """
    link, be = make(require_homed_for_steer=True)
    assert be._homed is False, "우리가 호밍한 적은 없는 상태여야 한다"
    _mark_homed_by_drive(be)
    assert be.homed_effective() is True
    be.set_steer_deg(10.0)              # 예외가 나면 실패
    assert be.snapshot()["homed_effective"] is True


def test_steer_still_blocked_when_drive_says_not_homed():
    """드라이브가 bit15=0 이면 여전히 막는다 — 게이트를 없앤 것이 아니다."""
    link, be = make(require_homed_for_steer=True)
    _mark_homed_by_drive(be, homed=False)
    assert be.homed_effective() is False
    with pytest.raises(S.UnsafeCommand) as e:
        be.set_steer_deg(10.0)
    assert "bit15=0" in str(e.value), str(e.value)


def test_steer_blocked_when_statusword_is_stale():
    """낡은 상태워드로 「호밍됐다」고 하면 안 된다 — 통신이 끊긴 뒤에도 조향이 열린다."""
    link, be = make(require_homed_for_steer=True)
    _mark_homed_by_drive(be, homed=True, age_s=be.cfg.feedback_ttl_s + 1.0)
    assert be.homed_effective() is False
    with pytest.raises(S.UnsafeCommand) as e:
        be.set_steer_deg(10.0)
    assert "낡음" in str(e.value), str(e.value)


def test_steer_axis_uses_the_same_gate():
    """축별 조향도 같은 판정을 쓴다 — 한쪽만 고치면 우회로가 생긴다."""
    link, be = make(require_homed_for_steer=True)
    _mark_homed_by_drive(be)
    be.set_steer_axis_deg(3, 10.0)


def test_home_comp_reports_the_drive_not_our_flag():
    """`MotorState.home_comp` 는 **드라이브의 0x6041 bit15** 를 실어야 한다.

    예전에는 `self._homed`(우리가 호밍했는가)를 실어, Seer 가 호밍해 둔 상태인데도
    `home_comp=False` 로 나갔다(2026-08-04 실기: 조향은 통과했는데 표시만 False).
    """
    link, be = make(require_homed_for_steer=True)
    assert be._homed is False
    _mark_homed_by_drive(be)                      # 드라이브만 「완료」 보고
    rows = {d["motor_id"]: d for d in be.motor_states()}
    for n in be.cfg.steer_nodes:
        assert rows[n]["home_comp"] is True, f"N{n} 이 드라이브 보고를 반영하지 않는다"
    _mark_homed_by_drive(be, homed=False)
    rows = {d["motor_id"]: d for d in be.motor_states()}
    for n in be.cfg.steer_nodes:
        assert rows[n]["home_comp"] is False
