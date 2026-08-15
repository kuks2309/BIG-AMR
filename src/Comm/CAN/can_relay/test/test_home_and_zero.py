"""호밍 → 조향 0° 복귀 절차 가드 회귀 (`can_relay.home_and_zero`).

고정하는 계약:

  ① **호밍이 실패하면 0° 지령을 보내지 않는다.** ← 이 파일의 존재 이유.
     드라이버는 막아주지 않는다 — `homed_effective()` 가 드라이브의 `0x6041` bit15 만으로도
     조향을 열기 때문에, 호밍 실패 뒤에도 `~/steer_deg` 는 수리된다. 호밍이 실패한 축은
     `0x6064` 가 0 을 읽어 실제 각도를 알 수 없는데도 그렇다.
  ② 호밍이 성공하면 0° 지령을 **실제로 보낸다**.
  ③ 도달 판정은 `tol_deg`(기본 0.1°) 다. 펌웨어 GOZERO 정착 편차(+0.178°/+0.331°)를
     통과시키면 안 된다 — 그러면 이 절차 전체가 무의미해진다.
  ④ 실측이 없는 축은 도달로 치지 않는다.

ROS·하드웨어 없이 돈다 — 전송을 `client` 로 주입하기 때문이다.
"""
import pytest

from can_relay.home_and_zero import (EXIT_HOME_FAILED, EXIT_OK,
                                     EXIT_ZERO_UNREACHED, ZeroReturnGuard)

# 펌웨어 GOZERO 정착값이 조향 0° 에서 벗어난 양(도). 실측 재현성 σ ≈ 3 counts.
GOZERO_OFFSET_DEG = {3: 0.178, 4: 0.331}


class FakeClient:
    """대역. 무엇을 보냈는지와 몇 번 물었는지를 기록한다."""

    def __init__(self, home_ok=True, home_msg="DONE", angle_script=None):
        self.home_ok, self.home_msg = home_ok, home_msg
        # angle_script: 매 조회마다 꺼내 쓸 {node: deg|None} 목록(마지막은 유지)
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


# ── ① 호밍 실패 → 0° 를 보내지 않는다 (핵심) ─────────────────────────────
def test_failed_homing_does_not_send_zero():
    c = FakeClient(home_ok=False, home_msg="ERR_GOZERO (30s, reached_mask=0x01)")
    rc = ZeroReturnGuard(c).run()
    assert rc == EXIT_HOME_FAILED
    assert c.zero_sent == 0, (
        "호밍이 실패했는데 0° 절대위치 지령이 나갔다 — 축의 실제 각도를 모르는 상태다")
    assert any("보내지 않습니다" in m for m in c.logs)


def test_failure_reason_is_carried_into_the_log():
    """무엇 때문에 멈췄는지 로그만 보고 알 수 있어야 한다(조용한 실패 금지)."""
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
    """순서가 뒤집히면 호밍이 그 목표를 덮어쓴다."""
    order = []
    c = FakeClient(home_ok=True)
    c.call_home = lambda: (order.append("home"), (True, "DONE"))[1]
    c.send_steer_zero = lambda: order.append("zero")
    ZeroReturnGuard(c).run()
    assert order == ["home", "zero"]


# ── ③ GOZERO 정착 편차를 도달로 인정하지 않는다 ──────────────────────────
@pytest.mark.parametrize("node,off", sorted(GOZERO_OFFSET_DEG.items()))
def test_gozero_offset_is_outside_default_tolerance(node, off):
    """기본 허용오차가 편차보다 크면 이 절차가 무의미해진다 — 전제를 숫자로 고정."""
    assert off > ZeroReturnGuard(FakeClient()).tol


def test_axis_left_at_gozero_settle_value_is_not_reached():
    c = FakeClient(home_ok=True, angle_script=[dict(GOZERO_OFFSET_DEG)])
    rc = ZeroReturnGuard(c, timeout_s=0.2).run()
    assert rc == EXIT_ZERO_UNREACHED, "정착 편차(+0.178°/+0.331°)를 0° 도달로 인정했다"
    assert c.zero_sent == 1        # 지령은 나갔다 — 도달만 미확인


def test_loose_tolerance_would_have_accepted_it():
    """왜 전용 허용오차가 필요한가 — 드라이버 `settle_tol_deg`(3.0°)면 통과한다."""
    c = FakeClient(home_ok=True, angle_script=[dict(GOZERO_OFFSET_DEG)])
    assert ZeroReturnGuard(c, tol_deg=3.0, timeout_s=0.2).run() == EXIT_OK


# ── ④ 실측 없는 축은 도달이 아니다 ───────────────────────────────────────
def test_missing_feedback_is_not_reached():
    c = FakeClient(home_ok=True, angle_script=[{3: 0.0, 4: None}])
    rc = ZeroReturnGuard(c, timeout_s=0.2).run()
    assert rc == EXIT_ZERO_UNREACHED
    assert any("실측 없음" in m for m in c.logs), c.logs


def test_reaches_zero_after_a_few_polls():
    """지령 직후 바로 0° 는 아니다 — 몇 주기 뒤 들어오면 성공이어야 한다."""
    c = FakeClient(home_ok=True, angle_script=[
        {3: 0.178, 4: 0.331}, {3: 0.05, 4: 0.09}, {3: 0.0, 4: 0.0}])
    assert ZeroReturnGuard(c, timeout_s=5.0).run() == EXIT_OK
