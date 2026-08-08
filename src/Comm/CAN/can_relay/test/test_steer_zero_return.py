"""호밍 완료 후 조향 0° 복귀 회귀.

고정하는 계약(ADR `docs/adr/2026-08-08-steer-zero-return-after-homing.md`):

  ① 호밍이 성공하면 **조향 0°(= `steer_home`) 지령이 실제로 나간다.**
  ② **펌웨어 GOZERO 정착값(`7882020` / `7859062`)에 서 있는 것은 「0° 도달」이 아니다.**
     ← 이 시험이 이 작업의 존재 이유다. 이 편차(+0.178° / +0.331°)를 통과시키면
       바뀐 것이 아무것도 없다.
  ③ 0° 미도달은 **`home()` 전체를 실패**로 만든다 — 호밍만 성공했다고 보고하지 않는다.
  ④ 판정 허용오차는 `steer_zero_tol_deg` 이고 `settle_tol_deg`(3.0°)가 **아니다.**
     후자로 되돌리면 ②가 통과해 버린다(그 사실 자체를 시험으로 적어 둔다).

⚠ 실기 미검증 — 전부 `FeedingLink` 대역이다. 실제 축이 0° 지령에 얼마 만에 정착하는지는
   이 파일이 말하지 않는다.
"""
import pytest

from can_relay import protocol as P
from can_relay import safety as S
from can_relay.backend import RelayBackend, RelayConfig
from can_relay.link import MockLink

from conftest import FeedingLink

# 정본 — `config/machine/foil_a082.yaml` `steer_home_counts`
ZERO = {3: 7871815, 4: 7840086}
# 펌웨어 GOZERO 목표(`safety_seer_gate.h:212-213`) = 호밍 후 정착값. **0° 가 아니다.**
GOZERO = {3: 7882020, 4: 7859062}
CPD = 57344.0


def make(**kw):
    kw.setdefault("steer_home", dict(ZERO))
    kw.setdefault("steer_counts_per_deg", CPD)
    kw.setdefault("require_homed_for_steer", True)
    kw.setdefault("steer_zero_timeout_s", 1.0)
    cfg = RelayConfig(cmd_hz=200.0, poll_hz=200.0, cmd_timeout_s=10.0, **kw)
    link = FeedingLink()
    link.open()
    link.acquire()
    return link, RelayBackend(link, cfg)


def run_home(link, be, hold: dict):
    """호밍 대본을 DONE 으로 깔고, 축을 `hold` 위치에 세워 둔 채 `home()` 을 돌린다."""
    for n, pos in hold.items():
        link.hold(n, pos)
    link.homing_script = [MockLink.homing_state(5, elapsed_s=31, reached_mask=3)]
    be.start()
    try:
        return be.home(poll_s=0.01, timeout_s=2.0)
    finally:
        be.shutdown()


def target_writes(link):
    """`0x607A` 쓰기 프레임에서 (node, counts) 목록. 마지막 것이 최종 목표다."""
    out = []
    for f in link.sent:
        idx = f.data[1] | (f.data[2] << 8)
        if idx == P.OBJ_TARGET_POSITION and f.data[0] != 0x40:
            node = f.can_id - 0x600
            out.append((node, int.from_bytes(f.data[4:8], "little")))
    return out


# ── ① 0° 지령이 실제로 나간다 ────────────────────────────────────────────
def test_home_commands_steer_zero_counts():
    link, be = make()
    ok, why = run_home(link, be, ZERO)
    assert ok is True, why

    sent = target_writes(link)
    assert sent, "호밍 후 0x607A 지령이 한 장도 나가지 않았다 — 0° 복귀가 없다"
    last = {n: c for n, c in sent}
    assert last == ZERO, f"최종 조향 목표가 0°(={ZERO}) 가 아니다: {last}"


def test_zero_command_carries_the_setpoint_controlword():
    """`0x607A` 만으로는 축이 움직이지 않는다 — `0x6040=0x3F` 가 따라붙어야 한다."""
    link, be = make()
    run_home(link, be, ZERO)
    cw = [f for f in link.sent
          if (f.data[1] | (f.data[2] << 8)) == P.OBJ_CONTROLWORD and f.data[0] != 0x40]
    assert any(f.data[4] == 0x3F for f in cw), "0x6040=0x3F 가 없다 — 목표가 적용되지 않는다"


# ── ② GOZERO 정착값은 0° 가 아니다 (이 작업의 핵심) ──────────────────────
@pytest.mark.parametrize("node", [3, 4])
def test_gozero_settle_value_is_not_zero_degrees(node):
    """정착값이 0° 라면 애초에 이 작업이 필요 없다 — 그 전제를 숫자로 고정한다."""
    off_deg = (GOZERO[node] - ZERO[node]) / CPD
    expected = {3: 0.178, 4: 0.331}[node]
    assert off_deg == pytest.approx(expected, abs=0.001)
    assert off_deg > 0.1, "편차가 steer_zero_tol_deg 기본값 안이면 시험이 무의미해진다"


def test_home_fails_when_axis_stays_at_gozero_settle_value():
    """축이 GOZERO 정착값에 남아 있으면 **0° 도달이 아니다** → `home()` 실패."""
    link, be = make()
    ok, why = run_home(link, be, GOZERO)
    assert ok is False, f"정착값(+0.178°/+0.331°)을 0° 도달로 인정했다: {why}"
    assert "0° 복귀 미확인" in why


def test_settle_tol_would_have_accepted_the_offset():
    """왜 `settle_tol_deg` 를 쓰지 않는가 — 그 값이면 위 편차가 통과한다.

    허용오차를 `settle_tol_deg`(3.0°)로 되돌리는 변경은
    `test_home_fails_when_axis_stays_at_gozero_settle_value` 를 깨뜨린다. 그 이유가 이것이다.
    """
    worst = max(abs(GOZERO[n] - ZERO[n]) / CPD for n in ZERO)
    assert worst < RelayConfig().settle_tol_deg      # 3.0° 안 → 검출 불가
    assert worst > RelayConfig().steer_zero_tol_deg  # 0.1° 밖 → 검출 가능


# ── ③ 미도달은 전체 실패 ─────────────────────────────────────────────────
def test_home_fails_without_steer_feedback():
    """피드백이 없으면 「0° 에 섰다」고 말할 근거가 없다 — 성공으로 적지 않는다."""
    link, be = make()
    ok, why = run_home(link, be, {})          # hold 없음 → 위치·상태워드 미공급
    assert ok is False
    assert "피드백 없음" in why


def test_homing_success_alone_is_not_reported_as_success():
    """호밍 시퀀서는 DONE 인데 0° 는 미도달인 상황. 종합 판정이 실패여야 한다."""
    link, be = make()
    ok, why = run_home(link, be, GOZERO)
    assert "DONE" in why, "호밍 시퀀서 결과가 메시지에서 사라지면 원인 추적이 끊긴다"
    assert ok is False


# ── ④ 끌 수 있다 (종전 동작) ─────────────────────────────────────────────
def test_disabled_flag_restores_previous_behaviour():
    link, be = make(steer_zero_after_home=False)
    ok, why = run_home(link, be, GOZERO)
    assert ok is True, why
    assert not target_writes(link), "0° 복귀를 껐는데 0x607A 지령이 나갔다"


def test_method35_path_does_not_get_the_zero_return():
    """method 35 는 현재 위치를 홈으로 **재선언**한다 — 0° 지령은 그 설계와 충돌한다.

    그 경로는 좌표계가 바뀌었으므로 구 절대목표를 일부러 비운다
    (`test_backend_method35.py::test_method35_discards_stale_steer_target_before_rezero`).
    거기에 0° 목표를 새로 걸면 그 시험이 지키는 성질이 깨진다.
    """
    link, be = make(homing_method="35", homing_enabled=False,
                    steer_home_offset={3: 1000, 4: 1000})
    ok, why = run_home(link, be, GOZERO)     # 정착값에 서 있어도 0° 판정을 하지 않는다
    assert "0° 복귀" not in why, f"method 35 경로에 0° 복귀가 붙었다: {why}"
    assert not target_writes(link)


# ── 안전 게이트를 우회하지 않는다 ────────────────────────────────────────
def test_zero_return_is_refused_under_estop():
    link, be = make()
    for n, pos in ZERO.items():
        link.hold(n, pos)
    link.homing_script = [MockLink.homing_state(5, elapsed_s=31, reached_mask=3)]
    be.start()
    try:
        be.estop(True)
        ok, why = be.home(poll_s=0.01, timeout_s=2.0)
    finally:
        be.shutdown()
    assert ok is False
    assert "E-stop" in why


def test_steer_to_zero_targets_the_canonical_home_constant():
    """0° 는 `steer_home` 에서 나온다 — 이 경로가 자기 상수를 갖지 않는다."""
    for n in ZERO:
        applied, counts = S.steer_deg_to_counts(n, 0.0, ZERO, 90.0, CPD)
        assert applied == 0.0
        assert counts == ZERO[n]
