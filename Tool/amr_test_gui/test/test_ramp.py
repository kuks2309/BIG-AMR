"""SteerRamp 단위 테스트 — 2026-07-27 node4 급점프 사고 유형의 회귀 방지.

실차 무관(순수 로직, 시간 주입). `pytest Tool/amr_test_gui/test -q`
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from amr_test_gui.ramp import FAULT, RAMPING, SETTLED, STEER_LIMIT_DEG, SteerRamp  # noqa: E402


def settle(ramp, deg, t0=0.0, dt=0.1, max_ticks=200):
    """실측이 지령을 완벽히 추종하는 이상적 액추에이터로 램프를 끝까지 돌린다."""
    t = t0
    out = None
    for _ in range(max_ticks):
        out = ramp.tick(ramp.commanded_deg, t)   # 실측 = 지령 (즉시 추종)
        t += dt
        if out.state in (SETTLED, FAULT):
            break
    return out, t


# ── ① 하드 클램프: ±90° 를 넘는 지령은 생성 불가 ────────────────────────────
@pytest.mark.parametrize("req,expect", [(137.0, 90.0), (-137.0, -90.0),
                                        (1e9, 90.0), (45.0, 45.0)])
def test_target_hard_clamped(req, expect):
    r = SteerRamp()
    assert r.set_target(req) == expect
    assert abs(r.target_deg) <= STEER_LIMIT_DEG


def test_commanded_never_exceeds_limit_during_ramp():
    r = SteerRamp(step_deg=30.0)
    r.set_target(137.0)      # 사고 재현 시도 — 137° 지령
    t = 0.0
    for _ in range(100):
        out = r.tick(r.commanded_deg, t)
        assert abs(out.commanded_deg) <= STEER_LIMIT_DEG, "램프가 하드 리밋을 넘겼다"
        t += 0.1
        if out.state == SETTLED:
            break
    assert r.commanded_deg == 90.0


# ── ② 단계 전진: 한 tick 에 step_deg 를 넘지 않는다 ─────────────────────────
def test_advances_in_steps_not_jumps():
    r = SteerRamp(step_deg=30.0)
    r.set_target(90.0)
    seen = [r.commanded_deg]
    t = 0.0
    for _ in range(100):
        out = r.tick(r.commanded_deg, t)
        if out.commanded_deg != seen[-1]:
            seen.append(out.commanded_deg)
        t += 0.1
        if out.state == SETTLED:
            break
    assert seen == [0.0, 30.0, 60.0, 90.0], f"단계 램프가 아님: {seen}"
    for a, b in zip(seen, seen[1:]):
        assert abs(b - a) <= 30.0 + 1e-9


def test_partial_last_step():
    r = SteerRamp(step_deg=30.0)
    r.set_target(70.0)
    out, _ = settle(r, 70.0)
    assert out.state == SETTLED
    assert r.commanded_deg == pytest.approx(70.0)


# ── ③ 정착 전 구동 금지 ─────────────────────────────────────────────────────
def test_drive_blocked_until_settled():
    r = SteerRamp(step_deg=30.0)
    r.set_target(90.0)
    t = 0.0
    allowed_before_target = []
    for _ in range(100):
        out = r.tick(r.commanded_deg, t)
        if out.state != SETTLED:
            allowed_before_target.append(out.drive_allowed)
        t += 0.1
        if out.state == SETTLED:
            break
    assert not any(allowed_before_target), "목표 도달 전에 구동이 허용됐다"
    assert out.drive_allowed and out.commanded_deg == 90.0


def test_drive_blocked_while_measured_lags():
    """실측이 지령을 못 따라오면(정착 미달) 기한 내에도 구동은 금지된다."""
    r = SteerRamp(step_deg=30.0, settle_tol_deg=3.0, step_timeout_s=10.0)
    r.set_target(30.0)
    out = r.tick(0.0, 0.0)          # 0° 정착 → 30° 로 단계 전진
    assert out.commanded_deg == 30.0
    out = r.tick(10.0, 1.0)         # 실측 10° — 지령 30° 에 미달
    assert out.state == RAMPING and not out.drive_allowed


# ── ④ 추종 실패 → FAULT 래치 + 즉시 home ────────────────────────────────────
def test_fault_on_follow_failure_latches_and_homes():
    r = SteerRamp(step_deg=30.0, settle_tol_deg=3.0, step_timeout_s=2.0)
    r.set_target(90.0)
    r.tick(0.0, 0.0)                       # → 지령 30°
    out = r.tick(0.0, 1.0)                 # 실측 0° 고착, 기한 내
    assert out.state == RAMPING
    out = r.tick(0.0, 5.0)                 # 기한 초과 → FAULT
    assert out.state == FAULT
    assert out.commanded_deg == 0.0, "FAULT 시 즉시 home(0°) 지령이어야 한다"
    assert not out.drive_allowed
    assert "추종 실패" in out.detail
    # 래치: 이후 어떤 입력에도 FAULT 유지, 목표 변경 무시
    r.set_target(45.0)
    out = r.tick(45.0, 6.0)
    assert out.state == FAULT and out.commanded_deg == 0.0 and not out.drive_allowed


def test_fault_reset_requires_explicit_call():
    r = SteerRamp(step_deg=30.0, step_timeout_s=1.0)
    r.set_target(60.0)
    r.tick(0.0, 0.0)
    assert r.tick(0.0, 5.0).state == FAULT
    r.reset()
    assert r.state != FAULT
    assert r.target_deg == r.commanded_deg, "reset 후 잔류목표가 남으면 급발진 위험"


def test_fault_on_missing_feedback_after_deadline():
    r = SteerRamp(step_deg=30.0, step_timeout_s=2.0)
    r.set_target(30.0)
    r.tick(0.0, 0.0)                       # → 지령 30°, 기한 2s
    out = r.tick(None, 1.0)
    assert out.state != FAULT and not out.drive_allowed
    out = r.tick(None, 5.0)
    assert out.state == FAULT and "피드백 미수신" in out.detail


# ── ⑤ 양 부호 대칭 (실측: +90°·−90° 둘 다 정상) ─────────────────────────────
@pytest.mark.parametrize("target", [90.0, -90.0])
def test_symmetric_both_signs(target):
    r = SteerRamp(step_deg=30.0)
    r.set_target(target)
    out, _ = settle(r, target)
    assert out.state == SETTLED and out.commanded_deg == pytest.approx(target)


def test_target_change_midramp_does_not_jump():
    r = SteerRamp(step_deg=30.0)
    r.set_target(90.0)
    r.tick(0.0, 0.0)                       # 지령 30°
    r.set_target(-90.0)                    # 반대편으로 목표 급변
    prev = r.commanded_deg
    t = 1.0
    for _ in range(100):
        out = r.tick(r.commanded_deg, t)
        assert abs(out.commanded_deg - prev) <= 30.0 + 1e-9, "목표 급변이 지령 급점프로 샜다"
        prev = out.commanded_deg
        t += 0.1
        if out.state == SETTLED:
            break
    assert r.commanded_deg == -90.0


def test_invalid_params_rejected():
    with pytest.raises(ValueError):
        SteerRamp(step_deg=0)
    with pytest.raises(ValueError):
        SteerRamp(settle_tol_deg=-1)
