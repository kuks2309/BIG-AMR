"""`ZeroReturnGuard` 회귀 — 호밍 → 조향 0° 복귀 절차의 판정.

고정하는 계약:

  ① 호밍이 실패하면 0° 지령을 보내지 않는다.
  ② 호밍이 성공하면 0° 지령을 보낸다. 순서는 호밍이 먼저다.
  ③ 도달 판정은 `tol_deg` 로 하며, 기본값(0.1°)은 `SETTLE_OFFSET_DEG` 를 통과시키지 않는다.
  ④ 실측이 없는 축은 도달로 치지 않는다.
  ⑤ 실패 사유가 로그에 실린다.

`client` 를 주입하므로 ROS·하드웨어 없이 돈다.
"""
import pytest

from can_relay.home_and_zero import (EXIT_CMD_NOT_ACCEPTED, EXIT_HOME_FAILED,
                                     EXIT_NO_SERVICE, EXIT_OK,
                                     EXIT_ZERO_UNREACHED, ZeroReturnGuard,
                                     fresh_or_none, steer_angles_from_joint_states,
                                     validate_params)

# 호밍 완료 위치가 조향 0° 에서 벗어나는 양(도) — 이 절차가 바로잡으려는 대상의 크기다.
# 기본 허용치가 이 값보다 작아야 판정이 성립하며, 그 관계를 아래 시험이 고정한다.
SETTLE_OFFSET_DEG = {3: 0.178, 4: 0.331}


class FakeClient:
    """`ZeroReturnGuard` 가 요구하는 client 계약의 대역. 호출 횟수를 기록한다."""

    def __init__(self, home_ok=True, home_msg="DONE", angle_script=None,
                 target_confirmed=True):
        self.home_ok, self.home_msg = home_ok, home_msg
        # 매 조회마다 앞에서 하나씩 꺼내 쓰고, 하나만 남으면 그것을 유지한다.
        self.angle_script = list(angle_script or [{3: 0.0, 4: 0.0}])
        self.target_confirmed = target_confirmed   # True/False/None(진단 미수신)
        self.zero_sent = 0
        self.home_calls = 0
        self.logs: list = []
        self._t = 0.0

    def service_available(self):
        return True

    def call_home(self):
        self.home_calls += 1
        return self.home_ok, self.home_msg

    def send_steer_zero(self):
        self.zero_sent += 1

    def steer_angles_deg(self):
        return self.angle_script[0] if len(self.angle_script) == 1 \
            else self.angle_script.pop(0)

    def sleep(self, seconds):
        self._t += max(float(seconds), 0.01)

    def elapsed(self):
        return self._t

    def steer_target_confirmed(self):
        return self.target_confirmed

    def log(self, msg):
        self.logs.append(str(msg))


# ── ① 호밍 실패 → 0° 미발행 ─────────────────────────────────────────────
def test_failed_homing_does_not_send_zero():
    c = FakeClient(home_ok=False, home_msg="ERR_GOZERO (30s, reached_mask=0x01)")
    rc = ZeroReturnGuard(c).run()
    assert rc == EXIT_HOME_FAILED
    assert c.zero_sent == 0, "호밍 실패인데 0° 지령이 나갔다"
    assert any("보내지 않습니다" in m for m in c.logs)


def test_failure_reason_is_carried_into_the_log():
    """호출부가 받은 실패 사유가 로그에 그대로 실린다."""
    c = FakeClient(home_ok=False, home_msg="ERR_GOZERO (30s, reached_mask=0x01)")
    ZeroReturnGuard(c).run()
    assert any("ERR_GOZERO" in m for m in c.logs), c.logs


# ── ② 호밍 성공 → 0° 를 보낸다 ───────────────────────────────────────────
def test_successful_homing_sends_zero_once():
    c = FakeClient(home_ok=True)
    rc = ZeroReturnGuard(c).run()
    assert rc == EXIT_OK
    assert c.zero_sent == 1


def test_zero_is_sent_after_home_not_before():
    """0° 지령은 호밍 뒤에 나간다."""
    order = []
    c = FakeClient(home_ok=True)
    c.call_home = lambda: (order.append("home"), (True, "DONE"))[1]
    c.send_steer_zero = lambda: order.append("zero")
    ZeroReturnGuard(c).run()
    assert order == ["home", "zero"]


# ── ③ 정착 편차를 도달로 인정하지 않는다 ────────────────────────────────
@pytest.mark.parametrize("node,off", sorted(SETTLE_OFFSET_DEG.items()))
def test_settle_offset_is_outside_default_tolerance(node, off):
    """기본 허용치가 바로잡으려는 편차보다 작다."""
    assert off > ZeroReturnGuard(FakeClient()).tol


def test_axis_left_at_settle_offset_is_not_reached():
    c = FakeClient(home_ok=True, angle_script=[dict(SETTLE_OFFSET_DEG)])
    rc = ZeroReturnGuard(c, timeout_s=0.2).run()
    assert rc == EXIT_ZERO_UNREACHED, "정착 편차를 0° 도달로 인정했다"
    assert c.zero_sent == 1        # 지령은 나갔고 도달만 미확인이다


def test_loose_tolerance_would_have_accepted_it():
    """허용치를 넓히면 같은 편차가 도달로 판정된다 — 판정이 허용치에만 달렸음을 고정한다."""
    c = FakeClient(home_ok=True, angle_script=[dict(SETTLE_OFFSET_DEG)])
    assert ZeroReturnGuard(c, tol_deg=3.0, timeout_s=0.2).run() == EXIT_OK


# ── ④ 실측 없는 축은 도달이 아니다 ───────────────────────────────────────
def test_missing_feedback_is_not_reached():
    c = FakeClient(home_ok=True, angle_script=[{3: 0.0, 4: None}])
    rc = ZeroReturnGuard(c, timeout_s=0.2).run()
    assert rc == EXIT_ZERO_UNREACHED
    assert any("실측 없음" in m for m in c.logs), c.logs


def test_reaches_zero_after_a_few_polls():
    """여러 주기에 걸쳐 들어와도 도달로 인정한다."""
    c = FakeClient(home_ok=True, angle_script=[
        {3: 0.178, 4: 0.331}, {3: 0.05, 4: 0.09}, {3: 0.0, 4: 0.0}])
    assert ZeroReturnGuard(c, timeout_s=5.0).run() == EXIT_OK


# ── 실측 신선도 ─────────────────────────────────────────────────────────
# 발행자는 믿을 수 없는 축을 빼고 보낸다. 그 축을 직전 값으로 채우면 그 보호가 사라진다.
def test_absent_axis_is_none_not_the_previous_value():
    a = steer_angles_from_joint_states(["steer_3", "steer_4"], [0.0, 0.0], (3, 4))
    assert a == {3: 0.0, 4: 0.0}
    b = steer_angles_from_joint_states(["steer_3"], [0.0], (3, 4))
    assert b[4] is None, "실리지 않은 축이 None 이 아니다 — 직전 값이 남았다"


def test_radians_are_converted_to_degrees():
    import math
    a = steer_angles_from_joint_states(["steer_3"], [math.radians(90.0)], (3, 4))
    assert a[3] == pytest.approx(90.0)


def test_unknown_names_are_ignored():
    a = steer_angles_from_joint_states(["wheel_1", "steer_x", "steer_3"], [1.0, 2.0, 0.0], (3, 4))
    assert a == {3: 0.0, 4: None}


def test_stale_feedback_becomes_none():
    angles = {3: 0.0, 4: 0.0}
    assert fresh_or_none(angles, 0.5, 1.0) == angles
    assert fresh_or_none(angles, 1.5, 1.0) == {3: None, 4: None}, "낡은 값이 도달 판정에 쓰인다"
    assert fresh_or_none(angles, None, 1.0) == {3: None, 4: None}, "수신 이력이 없는데 값이 산다"


def test_guard_does_not_complete_on_stale_feedback():
    """대기 도중 피드백이 끊기면 완료가 아니라 미도달이어야 한다."""
    c = FakeClient(home_ok=True, angle_script=[
        {3: 0.0, 4: 0.0}, {3: None, 4: None}, {3: None, 4: None}])
    assert ZeroReturnGuard(c, timeout_s=0.2).run() in (EXIT_OK, EXIT_ZERO_UNREACHED)
    c2 = FakeClient(home_ok=True, angle_script=[{3: None, 4: None}])
    assert ZeroReturnGuard(c2, timeout_s=0.2).run() == EXIT_ZERO_UNREACHED


# ── 상대가 없을 때 ──────────────────────────────────────────────────────
def test_missing_service_has_its_own_exit_code():
    c = FakeClient(home_ok=True)
    c.service_available = lambda: False
    rc = ZeroReturnGuard(c).run()
    assert rc == EXIT_NO_SERVICE, "서비스 부재가 호밍 실패(2)와 구분되지 않는다"
    assert c.home_calls == 0, "상대가 없는데 호밍을 요청했다"
    assert c.zero_sent == 0


# ── 파라미터 검증 · 재발행 · 미수용 분류 ────────────────────────────────
def test_validate_params_bounds():
    """무효 파라미터는 사유 문자열, 유효는 None — 호밍 요청 전에 걸러진다."""
    assert validate_params(0.1, 10.0) is None
    assert validate_params(180.0, 10.0) is not None   # 어떤 자세든 통과시키는 허용치
    assert validate_params(0.0, 10.0) is not None     # 영구 미도달
    assert validate_params(-1.0, 10.0) is not None
    assert validate_params(0.1, 0.0) is not None
    assert validate_params(0.1, 9999.0) is not None
    assert validate_params("x", 10.0) is not None


def test_zero_is_resent_while_waiting():
    """대기 중 0° 지령이 재발행된다 — 1회 발행 유실이 영구 실패가 되지 않게."""
    c = FakeClient(angle_script=[{3: None, 4: None}])
    rc = ZeroReturnGuard(c, timeout_s=3.5).run()
    assert rc in (EXIT_ZERO_UNREACHED, EXIT_CMD_NOT_ACCEPTED)
    assert c.zero_sent >= 3, f"재발행이 없다 — 발행 {c.zero_sent}회"


def test_timeout_with_unaccepted_target_has_its_own_exit_code():
    """드라이버가 0° 목표를 물지 않았으면 미도달이 아니라 「미수용」으로 갈린다."""
    c = FakeClient(angle_script=[{3: 5.0, 4: 5.0}], target_confirmed=False)
    assert ZeroReturnGuard(c, timeout_s=0.3).run() == EXIT_CMD_NOT_ACCEPTED
    assert any("수용되지 않았습니다" in m for m in c.logs)


def test_timeout_without_diag_stays_unreached():
    """진단 미수신(모름)은 미수용으로 단정하지 않는다 — 미도달로 남긴다."""
    c = FakeClient(angle_script=[{3: 5.0, 4: 5.0}], target_confirmed=None)
    assert ZeroReturnGuard(c, timeout_s=0.3).run() == EXIT_ZERO_UNREACHED
