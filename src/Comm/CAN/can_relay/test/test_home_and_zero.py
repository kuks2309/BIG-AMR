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

from can_relay.home_and_zero import (EXIT_HOME_FAILED, EXIT_OK,
                                     EXIT_ZERO_UNREACHED, ZeroReturnGuard)

# 호밍 완료 위치가 조향 0° 에서 벗어나는 양(도) — 이 절차가 바로잡으려는 대상의 크기다.
# 기본 허용치가 이 값보다 작아야 판정이 성립하며, 그 관계를 아래 시험이 고정한다.
SETTLE_OFFSET_DEG = {3: 0.178, 4: 0.331}


class FakeClient:
    """`ZeroReturnGuard` 가 요구하는 client 계약의 대역. 호출 횟수를 기록한다."""

    def __init__(self, home_ok=True, home_msg="DONE", angle_script=None):
        self.home_ok, self.home_msg = home_ok, home_msg
        # 매 조회마다 앞에서 하나씩 꺼내 쓰고, 하나만 남으면 그것을 유지한다.
        self.angle_script = list(angle_script or [{3: 0.0, 4: 0.0}])
        self.zero_sent = 0
        self.home_calls = 0
        self.logs: list = []
        self._t = 0.0

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
