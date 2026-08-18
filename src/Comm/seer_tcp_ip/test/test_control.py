"""제어권 세션·dead-man jog 회귀 시험.

고정 대상: 획득/반납의 짝, 예외 경로에서도 반납, 반납 전 정지, dead-man 주기 불변식.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from seer_tcp_ip import ports  # noqa: E402
from seer_tcp_ip.control import (  # noqa: E402
    JogKeepalive,
    SeerControlError,
    SeerControlSession,
    describe_owner,
    preempted_by_control,
)


class FakeApi:
    """SeerApi 대역 — 호출 순서를 기록한다. 순서가 이 모듈의 계약이다."""

    def __init__(self, owner=None, owner_raises=False):
        self.calls = []
        self._owner = owner if owner is not None else {"locked": False}
        self._owner_raises = owner_raises
        self.stop_raises = False

    def get_control_owner(self):
        self.calls.append(("owner", None))
        if self._owner_raises:
            raise RuntimeError("1060 실패")
        return self._owner

    def seize_control(self, nick_name):
        self.calls.append(("seize", nick_name))
        return {"ret_code": 0}

    def release_control(self):
        self.calls.append(("release", None))
        return {"ret_code": 0}

    def stop(self):
        self.calls.append(("stop", None))
        if self.stop_raises:
            raise RuntimeError("2000 실패")
        return {"ret_code": 0}

    def open_loop_move(self, vx, vy, w, duration_ms):
        self.calls.append(("jog", (vx, vy, w, duration_ms)))
        return {"ret_code": 0}

    def names(self):
        return [c[0] for c in self.calls]


# ---------- 제어권 세션 ----------

def test_session_order_is_owner_seize_stop_release():
    """계약: 소유자 조회 → 획득 → (사용) → 정지 → 반납."""
    api = FakeApi()
    with SeerControlSession(api, "big-amr") as sess:
        assert sess.held
        api.open_loop_move(0.1, 0.0, 0.0, 600)
    assert api.names() == ["owner", "seize", "jog", "stop", "release"]
    assert not sess.held


def test_session_releases_on_exception():
    """예외로 빠져나가도 반납한다 — 제어권을 쥔 채 죽으면 다음 클라이언트가 40020 으로 막힌다."""
    api = FakeApi()
    with pytest.raises(ValueError):
        with SeerControlSession(api, "big-amr"):
            raise ValueError("작업 중 실패")
    assert api.names() == ["owner", "seize", "stop", "release"]


def test_session_releases_even_if_stop_fails():
    """정지가 실패해도 반납은 시도한다 — 쥔 채 남는 것이 더 나쁘다."""
    api = FakeApi()
    api.stop_raises = True
    sess = SeerControlSession(api, "big-amr")
    sess.acquire()
    with pytest.raises(RuntimeError):
        sess.release()
    assert "release" in api.names()
    assert not sess.held


def test_session_records_previous_owner():
    api = FakeApi(owner={"locked": True, "nick_name": "operator-0.1", "ip": "192.168.44.49"})
    with SeerControlSession(api, "big-amr") as sess:
        assert sess.previous_owner["nick_name"] == "operator-0.1"


def test_session_survives_owner_query_failure():
    """1060 이 실패해도 획득은 진행한다 — 진단 조회가 본 작업을 막지 않는다."""
    api = FakeApi(owner_raises=True)
    with SeerControlSession(api, "big-amr") as sess:
        assert sess.previous_owner == {}
    assert api.names() == ["owner", "seize", "stop", "release"]


def test_double_acquire_rejected():
    api = FakeApi()
    sess = SeerControlSession(api, "big-amr")
    sess.acquire()
    with pytest.raises(SeerControlError, match="이중 획득"):
        sess.acquire()


def test_release_without_hold_is_noop():
    api = FakeApi()
    SeerControlSession(api, "big-amr").release()
    assert api.calls == []


def test_empty_nick_name_rejected():
    """소유자 이름이 비면 로봇 화면에서 누가 잡았는지 식별할 수 없다."""
    for bad in ("", "   "):
        with pytest.raises(ValueError, match="nick_name"):
            SeerControlSession(FakeApi(), bad)


def test_stop_on_exit_can_be_disabled():
    api = FakeApi()
    with SeerControlSession(api, "big-amr", stop_on_exit=False):
        pass
    assert api.names() == ["owner", "seize", "release"]


# ---------- dead-man jog ----------

def test_interval_must_be_shorter_than_duration():
    """주기가 dead-man 이상이면 매 주기 만료돼 로봇이 섰다 갔다 한다 — 생성 시 거부."""
    api = FakeApi()
    with pytest.raises(ValueError, match="이상이다"):
        JogKeepalive(api, vx=0.1, duration_ms=200, interval_s=0.2)
    with pytest.raises(ValueError, match="이상이다"):
        JogKeepalive(api, vx=0.1, duration_ms=100, interval_s=0.2)
    JogKeepalive(api, vx=0.1, duration_ms=600, interval_s=0.2)  # 정상


def test_zero_duration_rejected():
    """0 = 무한이라 dead-man 이 사라진다.

    ⚠ match 를 "duration_ms" 로 두면 안 된다 — 그 가드를 지워도 뒤의 interval 가드가
    `duration_ms(0ms)` 를 담은 메시지로 걸려 **같은 문자열에 걸려 통과한다.**
    그래서 이 가드만의 문구로 판정한다.
    """
    for bad in (0, -1):
        with pytest.raises(ValueError, match="0 은 무한"):
            JogKeepalive(FakeApi(), duration_ms=bad, interval_s=0.2)


def test_negative_interval_rejected():
    with pytest.raises(ValueError, match="interval_s"):
        JogKeepalive(FakeApi(), duration_ms=600, interval_s=0)


def test_tick_sends_duration_every_time():
    """모든 재송신이 duration 을 싣는다 — 하나라도 빠지면 그 지령이 무한이 된다."""
    now = [0.0]
    api = FakeApi()
    jog = JogKeepalive(api, vx=0.1, w=-0.2, duration_ms=600, interval_s=0.2,
                       clock=lambda: now[0])
    assert jog.tick() is True          # 첫 호출은 즉시
    assert jog.tick() is False         # 아직 시점 아님
    now[0] += 0.2
    assert jog.tick() is True
    now[0] += 0.5
    assert jog.tick() is True
    jogs = [c[1] for c in api.calls if c[0] == "jog"]
    assert len(jogs) == 3 == jog.sent_count
    assert all(j[3] == 600 for j in jogs), "duration 이 빠진 지령이 있다"
    assert all(j[0] == 0.1 and j[2] == -0.2 for j in jogs)


def test_set_velocity_applies_next_tick_only():
    """속도 변경이 즉시 송신되지 않는다 — 과송신은 로봇이 연결을 정리하는 사유다."""
    now = [0.0]
    api = FakeApi()
    jog = JogKeepalive(api, vx=0.1, duration_ms=600, interval_s=0.2, clock=lambda: now[0])
    jog.tick()
    now[0] += 0.5                      # 재송신 시점을 지나게 둔다 — 이래야 「즉시 송신」이 드러난다
    jog.set_velocity(vx=0.3)
    assert len([c for c in api.calls if c[0] == "jog"]) == 1, \
        "set_velocity 가 스스로 송신했다 — 송신 시점은 tick() 만 정한다"
    jog.tick()
    sent = [c[1] for c in api.calls if c[0] == "jog"]
    assert len(sent) == 2 and sent[-1][0] == 0.3


def test_stop_zeroes_velocity_and_resets_schedule():
    now = [0.0]
    api = FakeApi()
    jog = JogKeepalive(api, vx=0.5, duration_ms=600, interval_s=0.2, clock=lambda: now[0])
    jog.tick()
    jog.stop()
    assert api.names()[-1] == "stop"
    assert (jog.vx, jog.vy, jog.w) == (0.0, 0.0, 0.0)
    assert jog.due() is True, "정지 후 다음 tick 은 즉시 보낼 수 있어야 한다"


def test_jog_context_manager_stops():
    api = FakeApi()
    with JogKeepalive(api, vx=0.1, duration_ms=600, interval_s=0.2):
        pass
    assert api.names() == ["stop"]


# ---------- 진단 ----------

def test_preempted_by_control_detects_40020():
    assert preempted_by_control(RuntimeError("API 2010 ret_code=40020 err_msg='...'"))
    assert not preempted_by_control(RuntimeError("API 2010 ret_code=8 err_msg='...'"))


def test_describe_owner_both_states():
    free = describe_owner(FakeApi(owner={"locked": False}))
    assert "비어 있음" in free
    held = describe_owner(FakeApi(owner={"locked": True, "nick_name": "op", "ip": "1.2.3.4"}))
    assert "op" in held and "1.2.3.4" in held and str(ports.API_PORT_CONFIG) in held
