"""ROS 계층 생존 게이트 회귀 — 「살아 있는 채 멈춘」 노드가 정지로 수렴하는가.

고정하는 성질:
  · ROS 계층 표시가 낡으면 심박이 끊긴다 (= 펌웨어 fail-safe 에 정지를 넘긴다)
  · 표시가 갱신되면 심박이 되살아난다 (일시 정체가 영구 정지가 되지 않는다)
  · 임계 0 이면 판정하지 않는다 (도입 전 동작 = Rollback 경로)
  · `start()` 가 표시를 찍어 기동 직후 오작동하지 않는다

왜 필요한가: 심박은 제어 스레드가 낸다. ROS 실행기만 정체하면 지령도 정지 요청도
도달하지 못하는데 심박은 계속 나가 펌웨어가 정상으로 본다 — 제어권을 쥔 채 아무도
못 뺏는 상태가 무기한 유지된다. 이 파일이 그 구간이 닫혀 있음을 고정한다.
"""
import time

from can_relay.backend import RelayBackend, RelayConfig
from can_relay.link import MockLink


def make(**kw):
    """짧은 임계로 백엔드 하나. 제어권까지 잡아 둔 상태로 돌려준다."""
    kw.setdefault("require_homed_for_steer", False)
    kw.setdefault("ros_alive_timeout_s", 0.3)
    cfg = RelayConfig(cmd_hz=100.0, poll_hz=50.0, **kw)
    link = MockLink()
    link.open()
    link.acquire()
    return link, RelayBackend(link, cfg)


def wait(cond, timeout=2.0):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if cond():
            return True
        time.sleep(0.01)
    return False


def test_start_marks_ros_alive():
    """기동 직후에는 표시가 신선하다 — 첫 진단 타이머 전에 심박이 끊기면 안 된다."""
    link, be = make()
    be.start()
    try:
        assert be.snapshot()["hb_suppressed"] is False
        assert be.ros_alive_age() is not None
        assert be.ros_alive_age() < 0.3
    finally:
        be._running = False


def test_stale_ros_layer_suppresses_heartbeat():
    """표시가 임계를 넘으면 심박이 끊긴다 — 이것이 형태 ③을 ①로 환원시키는 지점이다."""
    link, be = make(ros_alive_timeout_s=0.2)
    be.start()
    try:
        assert wait(lambda: be.snapshot()["hb_suppressed"] is True, timeout=2.0), \
            "ROS 계층이 멈췄는데 심박이 계속 나갔다"
        snap = be.snapshot()
        assert "ROS 계층 정체" in snap["hb_block_note"], snap["hb_block_note"]
        hb = link.heartbeats
        time.sleep(0.2)
        assert link.heartbeats == hb, "억제 판정 후에도 심박이 나갔다"
    finally:
        be._running = False


def test_marking_alive_restores_heartbeat():
    """정체가 풀리면 심박이 되살아난다 — 일시 지연이 영구 정지가 되면 안 된다.

    갱신은 **주기적**이어야 한다. 실기에서 표시를 찍는 것은 진단 타이머이고,
    `CanRelayNode.__init__` 이 `ros_alive_timeout_s ≥ 2/diag_hz` 를 강제해 임계 창 안에
    최소 2회 찍히도록 보장한다. 여기서도 같은 조건으로 시험한다 — 단발 갱신은 임계와
    심박 주기가 같은 크기일 때 슬롯을 놓칠 수 있고, 그것은 설계가 배제한 설정이다.
    """
    link, be = make(ros_alive_timeout_s=0.4)
    be.start()
    try:
        assert wait(lambda: be.snapshot()["hb_suppressed"] is True, timeout=2.0)
        hb_at_block = link.heartbeats

        def keep_marking(seconds):
            t0 = time.monotonic()
            while time.monotonic() - t0 < seconds:
                be.mark_ros_alive()
                time.sleep(0.02)

        keep_marking(0.5)
        assert be.snapshot()["hb_suppressed"] is False, \
            "표시를 주기적으로 갱신했는데 심박이 돌아오지 않았다"
        assert be.snapshot()["hb_block_note"] == ""
        assert link.heartbeats > hb_at_block, "심박이 재개되지 않았다"
    finally:
        be._running = False


def test_zero_timeout_disables_the_gate():
    """임계 0 = 판정하지 않는다. ADR §Rollback 이 약속한 되돌림 경로다."""
    link, be = make(ros_alive_timeout_s=0.0)
    be.start()
    try:
        time.sleep(0.4)          # 표시를 한 번도 갱신하지 않는다
        snap = be.snapshot()
        assert snap["hb_suppressed"] is False, "임계 0 인데 심박이 끊겼다"
        hb = link.heartbeats
        time.sleep(0.15)
        assert link.heartbeats > hb, "임계 0 인데 심박이 멈췄다"
    finally:
        be._running = False


def test_tx_failure_reason_wins_over_ros_stale():
    """두 사유가 동시에 서면 송신 실패가 먼저 보고된다 — 원인 추적이 갈리지 않게."""
    from can_relay.link import LinkError

    class DeadTx(MockLink):
        def send(self, frames):
            raise LinkError("송신 불가(시험)")

    link = DeadTx()
    link.open()
    link.acquire()
    be = RelayBackend(link, RelayConfig(cmd_hz=100.0, tx_fail_halt=3,
                                        ros_alive_timeout_s=0.2,
                                        require_homed_for_steer=False))
    be.start()
    try:
        assert wait(lambda: be.snapshot()["hb_suppressed"] is True, timeout=2.0)
        assert "송신 연속 실패" in be.snapshot()["hb_block_note"]
    finally:
        be._running = False


def test_ros_alive_age_is_none_before_any_mark():
    """한 번도 안 찍혔으면 나이는 `None`(모름)이고, 모름을 정체로 치지 않는다."""
    _link, be = make()
    assert be.ros_alive_age() is None
    assert be._hb_block_reason(time.monotonic()) is None
