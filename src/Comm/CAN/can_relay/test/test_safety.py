"""안전 게이트 회귀 — 이 파일이 깨지면 로봇이 손상될 수 있다.

각 시험은 실제 사고·실측에 대응한다:
  · NaN 클램프 우회      → cmd_vel 오염 1개가 최대속도 지령이 되는 경로
  · 조향 ±90° 클램프     → 2026-07-27 node4 물리 손상과 같은 범위 이탈
  · bit15 위치 신뢰 게이트 → 호밍 중 0x6064=0 이 ≈−137° 로 상위에 흘러가는 문제
  · 호밍 2상 판정        → 이미 호밍된 축을 즉시 완료로 오독하는 문제
"""
import math

import pytest

from can_relay import safety as S


# ── NaN / inf ─────────────────────────────────────────────────────────────
def test_python_clamp_idiom_is_broken_for_nan():
    """왜 finite() 가 필요한지 고정한다 — 이 동작이 사고의 원인이다."""
    assert max(-0.2, min(0.2, float("nan"))) == 0.2


def test_finite_rejects_nan_and_inf():
    assert S.finite(1.0, -2.0, 0.0)
    assert not S.finite(float("nan"))
    assert not S.finite(float("inf"))
    assert not S.finite(1.0, float("-inf"))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_clamp_refuses_nonfinite(bad):
    with pytest.raises(S.UnsafeCommand):
        S.clamp(bad, 0.2)


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_drive_conversion_refuses_nonfinite(bad):
    with pytest.raises(S.UnsafeCommand):
        S.drive_mmps_to_units(bad)


def test_steer_conversion_refuses_nonfinite():
    with pytest.raises(S.UnsafeCommand):
        S.steer_deg_to_counts(3, float("nan"))


# ── 조향 클램프 ───────────────────────────────────────────────────────────
def test_steer_zero_is_home_counts():
    applied, counts = S.steer_deg_to_counts(3, 0.0)
    assert applied == 0.0
    assert counts == S.DEFAULT_STEER_HOME[3]


def test_steer_90deg_uses_counts_per_deg():
    _applied, counts = S.steer_deg_to_counts(4, 90.0)
    assert counts == S.DEFAULT_STEER_HOME[4] + int(round(90.0 * 57344))


@pytest.mark.parametrize("deg,expect", [
    (91.0, 90.0), (140.0, 90.0), (1000.0, 90.0),
    (-91.0, -90.0), (-140.0, -90.0), (-1000.0, -90.0),
])
def test_steer_clamps_beyond_verified_range(deg, expect):
    """90~140° 는 미검증 구간이다. 접는 게 아니라 자른다."""
    applied, counts = S.steer_deg_to_counts(3, deg)
    assert applied == expect
    assert counts == S.DEFAULT_STEER_HOME[3] + int(round(expect * 57344))


def test_steer_rejects_unknown_node():
    with pytest.raises(S.UnsafeCommand):
        S.steer_deg_to_counts(9, 0.0)


def test_steer_home_override_is_honored():
    applied, counts = S.steer_deg_to_counts(3, 0.0, {3: 7882020})
    assert (applied, counts) == (0.0, 7882020)


# ── 구동 상한 ─────────────────────────────────────────────────────────────
def test_drive_units_conversion():
    assert S.drive_mmps_to_units(50.0, 1) == int(round(50.0 * 24.447))


def test_drive_units_clamped_both_directions():
    assert S.drive_mmps_to_units(10000.0, 1) == S.VEL_MAX_UNITS
    assert S.drive_mmps_to_units(10000.0, -1) == -S.VEL_MAX_UNITS


def test_drive_zero_is_zero():
    assert S.drive_mmps_to_units(0.0) == 0


# ── 위치 신뢰 게이트 ──────────────────────────────────────────────────────
def test_position_untrusted_while_homing():
    """bit15=0(호밍 중) 이면 0x6064 는 0 고정이라 쓰면 안 된다."""
    assert S.position_trustworthy(0x1050) is False      # bit15=0
    assert S.position_trustworthy(0x9450) is True       # bit15=1


def test_position_untrusted_when_statusword_unknown():
    assert S.position_trustworthy(None) is False


def test_is_homed_returns_none_without_statusword():
    assert S.is_homed(None) is None


# ── 호밍 2상 판정 ─────────────────────────────────────────────────────────
def test_already_homed_axis_is_not_reported_complete():
    """시작 전부터 bit15=1 인 축을 곧바로 완료로 읽으면 안 된다."""
    j = S.HomingJudge([3, 4])
    result, _why = j.update({3: 0x9450, 4: 0x9450}, 0.5)
    assert result is None                                # 아직 판단하지 않는다


def test_homing_completes_only_after_seeing_zero_then_one():
    j = S.HomingJudge([3, 4])
    assert j.update({3: 0x9450, 4: 0x9450}, 0.1)[0] is None
    assert j.update({3: 0x1050, 4: 0x1050}, 1.0)[0] is None     # 개시 관측
    result, why = j.update({3: 0x9450, 4: 0x9450}, 31.0)
    assert result is True and "31" in why


def test_homing_fails_when_start_never_observed():
    j = S.HomingJudge([3, 4], start_window_s=5.0)
    assert j.update({3: 0x9450, 4: 0x9450}, 1.0)[0] is None
    result, why = j.update({3: 0x9450, 4: 0x9450}, 5.1)
    assert result is False and "개시" in why


def test_homing_requires_both_axes_to_start():
    j = S.HomingJudge([3, 4], start_window_s=5.0)
    j.update({3: 0x1050, 4: 0x9450}, 1.0)               # node3 만 개시
    result, why = j.update({3: 0x1050, 4: 0x9450}, 5.1)
    assert result is False and "4" in why


def test_homing_times_out():
    j = S.HomingJudge([3, 4], start_window_s=5.0, timeout_s=30.0)
    j.update({3: 0x1050, 4: 0x1050}, 1.0)
    result, why = j.update({3: 0x1050, 4: 0x1050}, 30.1)
    assert result is False and "30" in why


# ── 정착 판정 ─────────────────────────────────────────────────────────────
def test_settle_requires_all_axes():
    """crab 은 앞뒤가 같은 각이어야 한다 — 한 축만 보면 뒷바퀴가 어긋난 채 달린다."""
    assert S.settled(90.0, {3: 90.1, 4: 89.9}, [3, 4], 3.0)
    assert not S.settled(90.0, {3: 90.1, 4: 60.0}, [3, 4], 3.0)


def test_settle_false_when_axis_missing():
    assert not S.settled(90.0, {3: 90.0}, [3, 4], 3.0)


def test_settle_false_when_measurement_nonfinite():
    assert not S.settled(90.0, {3: 90.0, 4: float("nan")}, [3, 4], 3.0)


# ── 상수 근거 ─────────────────────────────────────────────────────────────
def test_counts_per_deg_matches_measured_90deg_delta():
    """실측 홈↔90° Δ = +5,160,960 counts = 정확히 90.00°."""
    assert 90.0 * S.COUNTS_PER_DEG == 5160960


def test_limit_is_verified_range_not_mechanical_range():
    """기구 한계(±140°)가 아니라 실측 검증 범위(±90°)를 한계로 쓴다."""
    assert S.STEER_LIMIT_DEG == 90.0
    assert math.isclose(S.VEL_MAX_UNITS / S.VEL_PER_MMPS, 199.98, abs_tol=0.05)
