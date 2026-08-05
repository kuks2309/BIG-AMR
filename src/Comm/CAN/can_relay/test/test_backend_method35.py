"""회귀 공백 메우기 — method 35 호밍 · stop_all · 버스 헬스 폴링.

2026-08-03 코드 리뷰가 잡은 시험 0건 함수들을 고정한다:
  `_home_method35` · `stop_all` · `_poll_bus_health` (같은 리뷰의 Medium 3건)

특히 `_home_method35` 는 `0x607A` 로 **바퀴를 실제로 움직이는** 경로다. 기본값이
`homing_method: firmware` 라 평시 비활성이지만, 비활성이라는 이유로 회귀가 없으면
설정 한 줄로 켜지는 날 아무 그물도 없다.

헬퍼(`make`·`feed`·`writes_to`)는 `test_backend.py` 것을 그대로 쓴다 — 같은 헬퍼를
파일마다 다시 만들지 않는다.
"""
import threading
import time

import pytest

from can_relay import protocol as P
from can_relay import safety as S
from can_relay.link import LinkError, MockLink
from test_backend import feed, make, wait, writes_to


def feed_abort(link, node, index, code=0x06090030, sub=0):
    """SDO abort 응답을 넣는다 — 드라이브가 쓰기를 거부한 경우."""
    data = bytes([0x80, index & 0xFF, index >> 8, sub]) + \
        (code & 0xFFFFFFFF).to_bytes(4, "little")
    link.inbox.append((0x580 + node, data, 2))


def m35(**kw):
    """method 35 기본 구성 — 홈이 0 인 좌표계(재영점 후 상태)."""
    kw.setdefault("homing_method", "35")
    kw.setdefault("steer_home", {3: 0, 4: 0})
    kw.setdefault("home_search_range", (-10_000, 10_000))
    kw.setdefault("home_reach_tol_counts", 50)
    return make(**kw)


def reached(link, be, nodes=(3, 4), pos=1000):
    """1단계 도착 상태(statusword bit10 + 위치 = 목표)를 피드백으로 넣는다.

    넣기만 하면 안 된다 — 제어 루프가 `_drain()` 하기 전에 `home()` 을 부르면
    "현재 위치를 모른다"로 거부되어 시험이 엉뚱한 이유로 실패한다. 반영까지 기다린다.
    """
    for n in nodes:
        feed(link, n, P.OBJ_POSITION_ACTUAL, pos)
        feed(link, n, P.OBJ_STATUSWORD, P.STATUSWORD_TARGET_REACHED, size=2)
    assert wait(lambda: all(be.snapshot()["nodes"][n]["fresh"] for n in nodes)), \
        "피드백이 백엔드에 반영되지 않았다"


# ── method 35: 움직이기 전에 걸리는 3가지 ────────────────────────────────
def test_method35_refuses_when_homing_disabled():
    """`homing_enabled=False` 면 프레임이 한 장도 나가면 안 된다."""
    link, be = m35(homing_enabled=False, steer_home_offset={3: 1000, 4: 1000})
    be.start()
    try:
        ok, why = be.home(poll_s=0.01, timeout_s=1.0)
        assert ok is False and "호밍 비활성" in why
        assert not writes_to(link, P.OBJ_TARGET_POSITION)
        assert not writes_to(link, P.OBJ_HOMING_METHOD)
    finally:
        be.shutdown()


def test_method35_refuses_without_home_offset():
    """오프셋이 없으면 어디로 갈지 모른다 — 거부한다."""
    link, be = m35(homing_enabled=True, steer_home_offset={})
    be.start()
    try:
        ok, why = be.home(poll_s=0.01, timeout_s=1.0)
        assert ok is False and "steer_home_offset" in why
        assert not writes_to(link, P.OBJ_TARGET_POSITION)
    finally:
        be.shutdown()


def test_method35_refuses_when_position_unknown():
    """피드백이 없으면 현재 위치를 모른다 — 그 상태로 절대이동을 보내지 않는다."""
    link, be = m35(homing_enabled=True, steer_home_offset={3: 1000, 4: 1000})
    be.start()
    try:
        ok, why = be.home(poll_s=0.01, timeout_s=1.0)
        assert ok is False and "현재 위치를 모른다" in why
        assert not writes_to(link, P.OBJ_TARGET_POSITION)
    finally:
        be.shutdown()


def test_method35_refuses_when_position_out_of_search_range():
    """엔코더 기준이 달라졌을 수 있는 위치에서는 움직이지 않는다(debt-007 전제)."""
    link, be = m35(homing_enabled=True, steer_home_offset={3: 1000, 4: 1000},
                   home_search_range=(-100, 100))
    be.start()
    try:
        for n in (3, 4):
            feed(link, n, P.OBJ_POSITION_ACTUAL, 5_000)     # 범위 밖
        time.sleep(0.05)                                    # 루프가 drain 하도록
        ok, why = be.home(poll_s=0.01, timeout_s=1.0)
        assert ok is False and "예상 범위" in why
        assert not writes_to(link, P.OBJ_TARGET_POSITION)
    finally:
        be.shutdown()


# ── method 35: 성공 경로 ─────────────────────────────────────────────────
def test_method35_completes_and_marks_homed():
    """1단계 이동 → 도착 → 2단계 재영점 → 0x6064≈0 확인까지 가야 완료다."""
    link, be = m35(homing_enabled=True, steer_home_offset={3: 1000, 4: 1000})
    be.start()
    done = threading.Event()

    def rezero():
        """드라이브가 `0x6098=35` 를 받으면 현재 위치를 0 으로 재선언한다 — 그 응답 대역."""
        while not done.is_set():
            if writes_to(link, P.OBJ_HOMING_METHOD):
                for n in (3, 4):
                    feed(link, n, P.OBJ_POSITION_ACTUAL, 0)
                return
            time.sleep(0.005)

    watcher = threading.Thread(target=rezero, daemon=True)
    watcher.start()
    try:
        reached(link, be, pos=1000)
        ok, why = be.home(poll_s=0.01, timeout_s=3.0)
        done.set()
        assert ok is True, why
        assert be.snapshot()["homed"] is True
        assert writes_to(link, P.OBJ_TARGET_POSITION), "1단계 절대이동 미송신"
        assert writes_to(link, P.OBJ_HOMING_METHOD), "2단계 재영점 미송신"
    finally:
        done.set()
        be.shutdown()


def test_method35_discards_stale_steer_target_before_rezero():
    """재영점은 좌표계를 바꾼다 — 구 절대목표를 안 버리면 다음 틱에 수십 도로 재해석된다."""
    link, be = m35(homing_enabled=True, steer_home_offset={3: 1000, 4: 1000})
    be.start()
    done = threading.Event()

    def rezero():
        while not done.is_set():
            if writes_to(link, P.OBJ_HOMING_METHOD):
                for n in (3, 4):
                    feed(link, n, P.OBJ_POSITION_ACTUAL, 0)
                return
            time.sleep(0.005)

    threading.Thread(target=rezero, daemon=True).start()
    try:
        be._steer_counts = {3: 5_000_000, 4: 5_000_000}     # 구 좌표계의 목표
        reached(link, be, pos=1000)
        ok, _why = be.home(poll_s=0.01, timeout_s=3.0)
        done.set()
        assert ok is True
        assert be._steer_counts == {}, "구 절대목표가 남아 있다"
    finally:
        done.set()
        be.shutdown()


def test_method35_keeps_steering_locked_when_drive_rejects_rezero():
    """`0x6098=35` 를 드라이브가 거부하면 홈이 설정되지 않았다 — 완료로 치면 안 된다."""
    link, be = m35(homing_enabled=True, steer_home_offset={3: 1000, 4: 1000})
    be.start()
    done = threading.Event()

    def reject():
        while not done.is_set():
            if writes_to(link, P.OBJ_HOMING_METHOD):
                for n in (3, 4):
                    feed_abort(link, n, P.OBJ_HOMING_METHOD)
                return
            time.sleep(0.005)

    threading.Thread(target=reject, daemon=True).start()
    try:
        reached(link, be, pos=1000)
        ok, why = be.home(poll_s=0.01, timeout_s=3.0)
        done.set()
        assert ok is False and "거부" in why
        assert be.snapshot()["homed"] is False, "거부됐는데 완료로 표시됐다"
    finally:
        done.set()
        be.shutdown()


def test_method35_timeout_sends_steer_stop():
    """도착하지 않으면 타임아웃에서 **조향을 세우고** 실패로 끝난다."""
    link, be = m35(homing_enabled=True, steer_home_offset={3: 1000, 4: 1000})
    be.start()
    try:
        for _ in range(2):
            for n in (3, 4):
                feed(link, n, P.OBJ_POSITION_ACTUAL, 0)   # 범위 안 · 도착은 아님 · 정지 상태
            time.sleep(0.08)
        ok, why = be.home(poll_s=0.01, timeout_s=0.3)
        assert ok is False and "도착하지 못했다" in why
        assert "조향 정지 송신" in why
    finally:
        be.shutdown()


# ── stop_all — `~/stop` 의 실제 경로 ─────────────────────────────────────
def test_stop_all_stops_drive_and_steering():
    link, be = make()
    be.start()
    try:
        for _ in range(2):          # 표본 2개 = 정지 확인(캡처된 상황으로 제한)
            for n in (3, 4):
                feed(link, n, P.OBJ_POSITION_ACTUAL, 7_871_000)
            time.sleep(0.08)
        be.set_drive_mmps(50.0)
        n_before = len(writes_to(link, P.OBJ_TARGET_POSITION))
        assert be.stop_all("시험") is True
        assert be.snapshot()["drive_units"] == 0
        assert len(writes_to(link, P.OBJ_TARGET_POSITION)) > n_before, \
            "조향축에 정지(현재위치 유지) 프레임이 나가지 않았다"
    finally:
        be.shutdown()


def test_stop_all_reports_failure_when_steer_position_unknown():
    """실측 위치를 모르면 조향을 세울 수 없다 — 성공이라고 하지 않는다."""
    link, be = make()
    be.start()
    try:
        be.set_drive_mmps(50.0)
        assert be.stop_all("시험") is False
        assert be.snapshot()["drive_units"] == 0        # 구동은 그래도 선다
    finally:
        be.shutdown()


# ── 버스 헬스 폴링 (0xc3) ────────────────────────────────────────────────
def test_bus_health_populates_snapshot_and_fault():
    link, be = make()
    link.health_fixture = {0: dict(bus_off=0, error_passive=0, error_warning=0,
                                   last_error_code=0, rec=0, tec=0, esr_reg=0),
                           2: dict(bus_off=0, error_passive=0, error_warning=1,
                                   last_error_code=3, rec=100, tec=96, esr_reg=0x1234)}
    be._poll_bus_health()
    snap = be.snapshot()
    assert snap["health_supported"] is True
    assert snap["bus_health"][2]["rec"] == 100
    assert "error-warning" in be.bus_fault()


def test_bus_off_outranks_error_warning():
    link, be = make()
    link.health_fixture = {0: dict(bus_off=0, error_passive=0, error_warning=1,
                                   last_error_code=0, rec=10, tec=10, esr_reg=0),
                           2: dict(bus_off=1, error_passive=1, error_warning=1,
                                   last_error_code=6, rec=255, tec=255, esr_reg=0)}
    be._poll_bus_health()
    assert "BUS-OFF" in be.bus_fault()


def test_bus_health_unsupported_link_disables_polling_permanently():
    """기능 자체가 없으면 영구 비활성 — 매 틱 예외를 삼키며 재시도하지 않는다."""
    class NoHealth(MockLink):
        calls = 0

        def can_health(self, bus):
            NoHealth.calls += 1
            raise NotImplementedError

    link = NoHealth(); link.open(); link.acquire()
    _l, be = make()
    be.link = link
    be._poll_bus_health()
    assert be.snapshot()["health_supported"] is False
    first = NoHealth.calls
    be._poll_bus_health()
    assert NoHealth.calls == first, "영구 비활성인데 다시 조회했다"


def test_bus_health_transient_failure_keeps_retrying():
    """일시적 실패는 기능 부재와 다르다 — 계속 재시도하고 회복하면 다시 채운다."""
    link, be = make()
    link.health_fixture = None                  # MockLink 는 픽스처 없으면 LinkError
    be._poll_bus_health()
    assert be.snapshot()["health_supported"] is not False, "일시 실패를 영구 비활성으로 처리했다"
    assert be.snapshot()["health_error"] is not None

    link.health_fixture = {0: dict(bus_off=0, error_passive=0, error_warning=0,
                                   last_error_code=0, rec=0, tec=0, esr_reg=0),
                           2: dict(bus_off=0, error_passive=0, error_warning=0,
                                   last_error_code=0, rec=0, tec=0, esr_reg=0)}
    be._poll_bus_health()
    assert be.snapshot()["health_supported"] is True
    assert be.snapshot()["health_error"] is None
    assert be.bus_fault() is None


def test_bus_health_failure_does_not_stop_commands():
    """읽기 전용 진단이 제어 경로를 죽이면 안 된다."""
    link, be = make()
    link.health_fixture = None
    be.start()
    try:
        be._poll_bus_health()                   # 실패
        be.set_drive_mmps(50.0)
        assert be.snapshot()["drive_units"] != 0
        assert isinstance(be.link, MockLink)
    finally:
        be.shutdown()


def test_can_health_raises_linkerror_without_fixture():
    link = MockLink()
    try:
        link.can_health(2)
    except LinkError:
        return
    raise AssertionError("픽스처 없이 can_health 가 값을 돌려줬다")


# ── 2026-08-03 리뷰 Medium 조치 회귀 ─────────────────────────────────────
def test_recv_failure_does_not_suppress_heartbeat():
    """수신이 죽어도 심박은 유지된다 — 심박 중단은 **송신 불가**의 신호여야 한다.

    예전에는 루프 전체를 한 카운터로 세어, 읽기 경로의 일시 오류가 10회 쌓이면
    로봇이 서면서 원인은 "송신 연속 실패"로 표시됐다(리뷰 M2).
    """
    class DeadRx(MockLink):
        def recv(self):
            raise LinkError("수신 불가(시험)")

    from can_relay.backend import RelayBackend, RelayConfig

    link = DeadRx(); link.open(); link.acquire()
    be = RelayBackend(link, RelayConfig(cmd_hz=100.0, tx_fail_halt=3,
                                        require_homed_for_steer=False))
    be.start()
    try:
        assert wait(lambda: be.snapshot()["loop_fail_streak"] >= 5, timeout=3.0), \
            "수신 실패가 루프 카운터에 잡히지 않았다"
        snap = be.snapshot()
        assert snap["tx_fail_streak"] == 0, "수신 실패가 송신 카운터로 샜다"
        assert snap["hb_suppressed"] is False, "수신 실패로 심박이 끊겼다"
        assert "루프" in snap["fault"]
        hb = link.heartbeats
        time.sleep(0.2)
        assert link.heartbeats > hb, "심박이 멈췄다"
    finally:
        be._running = False


def test_send_failure_still_suppresses_heartbeat():
    """반대 방향 고정 — 송신 실패는 여전히 심박을 끊어야 한다(정지 근간)."""
    class DeadTx(MockLink):
        def send(self, frames):
            raise LinkError("송신 불가(시험)")

    from can_relay.backend import RelayBackend, RelayConfig

    link = DeadTx(); link.open(); link.acquire()
    be = RelayBackend(link, RelayConfig(cmd_hz=100.0, tx_fail_halt=3,
                                        require_homed_for_steer=False))
    be.start()
    try:
        assert wait(lambda: be.snapshot()["hb_suppressed"] is True, timeout=3.0)
        assert be.snapshot()["tx_fail_streak"] >= 3
        assert "송신" in be.snapshot()["fault"]
    finally:
        be._running = False


def test_estop_rejection_of_drive_command_is_reported():
    """E-stop 중 구동 지령이 조용히 사라지면 상위가 수리된 줄 안다(리뷰 M5)."""
    link, be = make()
    be.estop(True)
    notes = be.set_motor_cmds([(1, P.MODE_VELOCITY, 1000, 0, 0)])
    assert any("구동 지령 거부" in n for n in notes)
    assert be.snapshot()["drive_units"] == 0


def test_estop_rejection_of_steer_command_is_still_reported():
    """조향 쪽 고지는 그대로 유지된다(회귀 보호)."""
    link, be = make(steer_home={3: 0, 4: 0})
    be.estop(True)
    notes = be.set_motor_cmds([(3, P.MODE_POSITION, 0, 100, 0)])
    assert any("조향 지령 거부" in n for n in notes)


def test_profile_vel_notice_is_logged_not_counted_as_rejection():
    """미반영 고지는 로그로만 — `notes` 에 섞이면 정상 지령이 거부로 집계된다."""
    logged = []
    link, be = make(steer_home={3: 0, 4: 0})
    be._log = logged.append
    notes = be.set_motor_cmds([(3, P.MODE_POSITION, 0, 100, 30000)])
    assert notes == [], f"정상 지령인데 거부 사유가 생겼다: {notes}"
    assert any("profile_vel=30000 미반영" in m for m in logged)


def test_profile_vel_notice_is_edge_triggered():
    """같은 값이 20~50 Hz 로 계속 와도 로그는 한 번이다."""
    logged = []
    link, be = make(steer_home={3: 0, 4: 0})
    be._log = logged.append
    for _ in range(10):
        be.set_motor_cmds([(3, P.MODE_POSITION, 0, 100, 30000)])
    assert sum("profile_vel" in m for m in logged) == 1
    be.set_motor_cmds([(3, P.MODE_POSITION, 0, 100, 12000)])   # 값이 바뀌면 다시 고지
    assert sum("profile_vel" in m for m in logged) == 2


# ── 축별 조향 `~/steer_axis_deg` (ADR 2026-08-03 이식본 ⓑ) ────────────────
def test_steer_axis_moves_only_that_axis():
    """한 축만 세운다 — 다른 축의 목표는 건드리지 않는다."""
    link, be = make(steer_home={3: 0, 4: 0})
    be.start()
    try:
        be.set_steer_axis_deg(3, 10.0)
        assert set(be._steer_counts) == {3}
        be.set_steer_axis_deg(4, -20.0)
        assert be._steer_counts[3] == int(round(10.0 * be.cfg.steer_counts_per_deg))
        assert be._steer_counts[4] == int(round(-20.0 * be.cfg.steer_counts_per_deg))
        assert wait(lambda: len(writes_to(link, P.OBJ_TARGET_POSITION)) >= 2)
    finally:
        be.shutdown()


def test_steer_axis_clamps_beyond_limit():
    """축이 하나라고 클램프를 빼지 않는다 — 2026-07-27-002 재발 방지."""
    link, be = make(steer_home={3: 0, 4: 0})
    applied = be.set_steer_axis_deg(3, 200.0)
    assert applied == 90.0
    assert be._steer_counts[3] == int(round(90.0 * be.cfg.steer_counts_per_deg))


def test_steer_axis_rejects_non_steer_node():
    """구동축에 위치 지령이 가면 안 된다."""
    link, be = make(steer_home={3: 0, 4: 0})
    with pytest.raises(S.UnsafeCommand) as e:
        be.set_steer_axis_deg(1, 10.0)
    assert "조향축이 아니다" in str(e.value)
    assert be._steer_counts == {}


def test_steer_axis_rejected_during_homing():
    link, be = make(steer_home={3: 0, 4: 0})
    be._homing = True
    with pytest.raises(S.UnsafeCommand):
        be.set_steer_axis_deg(3, 10.0)


def test_steer_axis_rejected_under_estop():
    link, be = make(steer_home={3: 0, 4: 0})
    be.estop(True)
    with pytest.raises(S.UnsafeCommand) as e:
        be.set_steer_axis_deg(3, 10.0)
    assert "E-stop" in str(e.value)


def test_steer_axis_rejected_before_homing_when_required():
    """호밍 미완료면 0° 기준이 없다 — 전축 경로와 같은 게이트."""
    link, be = make(require_homed_for_steer=True, steer_home={3: 0, 4: 0})
    with pytest.raises(S.UnsafeCommand) as e:
        be.set_steer_axis_deg(3, 10.0)
    # 2026-08-04: 문구가 바뀌었다 — 판정이 `_homed` 단독에서 `homed_effective()`(드라이브
    # bit15 포함)로 확장됐다. Seer 가 호밍한 경우를 인정하기 위해서다.
    assert "조향 0° 기준을 확인할 수 없다" in str(e.value)


def test_steer_axis_rejected_without_home_config():
    """홈이 없으면 조용히 0 으로 대체하지 않는다."""
    link, be = make(steer_home={})
    with pytest.raises(S.UnsafeCommand):
        be.set_steer_axis_deg(3, 10.0)


def test_steer_axis_does_not_claim_single_target_angle():
    """앞뒤가 다를 수 있으므로 단일 목표각을 주장하지 않는다."""
    link, be = make(steer_home={3: 0, 4: 0})
    be.set_steer_deg(30.0)
    assert be.snapshot()["steer_target_deg"] == 30.0
    be.set_steer_axis_deg(3, 10.0)
    assert be.snapshot()["steer_target_deg"] is None
    assert be.settled() is False


# ── 「캡처된 상황에서만」 제한 (2026-08-03 사용자 결정) ──────────────────
def test_hold_steer_at_measured_refuses_while_axis_is_moving():
    """움직이는 축에는 보내지 않는다 — 이동 중 사용은 마스터 캡처에 0건이다."""
    link, be = make(steer_home={3: 0, 4: 0})
    for n in (3, 4):                       # 두 표본이 크게 다르다 = 이동 중
        feed(link, n, P.OBJ_POSITION_ACTUAL, 1_000_000)
    be._drain()
    for n in (3, 4):
        feed(link, n, P.OBJ_POSITION_ACTUAL, 1_500_000)
    be._drain()
    n_before = len(writes_to(link, P.OBJ_TARGET_POSITION))
    assert be.hold_steer_at_measured("이동 중") is False
    assert len(writes_to(link, P.OBJ_TARGET_POSITION)) == n_before, \
        "이동 중인데 조향 목표를 보냈다"


def test_hold_steer_at_measured_refuses_with_single_sample():
    """표본이 하나면 정지인지 **모른다** — 모르면 보내지 않는다."""
    link, be = make(steer_home={3: 0, 4: 0})
    for n in (3, 4):
        feed(link, n, P.OBJ_POSITION_ACTUAL, 1_000_000)
    be._drain()
    n_before = len(writes_to(link, P.OBJ_TARGET_POSITION))
    assert be.hold_steer_at_measured("표본 1개") is False
    assert len(writes_to(link, P.OBJ_TARGET_POSITION)) == n_before


def test_hold_steer_at_measured_sends_when_stationary_within_master_band():
    """마스터가 실제로 쓰던 대역(|Δ| ≤ 200 c) 안이면 보낸다."""
    link, be = make(steer_home={3: 0, 4: 0})
    for n in (3, 4):
        feed(link, n, P.OBJ_POSITION_ACTUAL, 1_000_000)
    be._drain()
    for n in (3, 4):
        feed(link, n, P.OBJ_POSITION_ACTUAL, 1_000_150)      # Δ=150 c < 200 c
    be._drain()
    assert be.hold_steer_at_measured("정지") is True
    assert {f.can_id - 0x600 for f in writes_to(link, P.OBJ_TARGET_POSITION)} == {3, 4}


def test_stationary_band_matches_master_capture_constant():
    """임계 200 c 는 임의 값이 아니라 마스터 캡처에서 관측된 대역폭이다."""
    from can_relay.backend import RelayConfig
    assert RelayConfig().stationary_tol_counts == 200
