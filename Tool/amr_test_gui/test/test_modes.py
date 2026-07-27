"""주행 모드 테이블 — 실측 재현성과 도출 정합 검증.

핵심: 도출 모델(`motion_unit_vector`)이 **확정 실측 2건을 실제로 재현**하는지 고정한다.
모델이 실측을 못 맞추면 대각 45° 모드 전체의 근거가 무너지므로 여기서 깨져야 한다.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from amr_test_gui import modes as M  # noqa: E402

SQ = math.sqrt(0.5)


def approx_vec(v, ex, ey, tol=1e-9):
    return abs(v[0] - ex) < tol and abs(v[1] - ey) < tol


# ── ① 모델이 확정 실측 2건을 재현하는가 (근거의 뿌리) ───────────────────────
def test_model_reproduces_measurement_1_forward():
    """실측 ①: 조향 홈(0°) + raw 음수 → 전진(+x)."""
    v = M.motion_unit_vector(M.FORWARD)
    assert M.FORWARD.steer_deg == 0.0 and M.FORWARD.raw_sign == -1
    assert approx_vec(v, 1.0, 0.0), f"모델이 실측 ①을 재현 못함: {v}"


def test_model_reproduces_measurement_2_crab_left():
    """실측 ②: 조향 +90° + raw 양수 → 왼쪽(+y)."""
    v = M.motion_unit_vector(M.CRAB_LEFT)
    assert M.CRAB_LEFT.steer_deg == 90.0 and M.CRAB_LEFT.raw_sign == +1
    assert approx_vec(v, 0.0, 1.0), f"모델이 실측 ②를 재현 못함: {v}"


def test_ccw_interpretation_is_refuted_by_measurement_2():
    """+counts = CCW 해석이면 실측 ②와 반대(오른쪽)가 나와야 한다 — 반증 근거의 회귀 고정."""
    th = math.radians(M.CRAB_LEFT.steer_deg)
    ccw_pointing = (math.cos(th), +math.sin(th))          # CCW 가정
    s = -M.CRAB_LEFT.raw_sign
    ccw_motion = (s * ccw_pointing[0], s * ccw_pointing[1])
    assert ccw_motion[1] < 0, "CCW 가정이 왼쪽을 내면 반증 논리가 성립하지 않는다"


# ── ② 8방위가 의도한 방향을 내는가 ──────────────────────────────────────────
@pytest.mark.parametrize("key,ex,ey", [
    ("forward",    1.0,  0.0),
    ("backward",  -1.0,  0.0),
    ("crab_left",  0.0,  1.0),
    ("crab_right", 0.0, -1.0),
    ("crab_fl",     SQ,   SQ),   # ↖ 좌전
    ("crab_fr",     SQ,  -SQ),   # ↗ 우전
    ("crab_rl",    -SQ,   SQ),   # ↙ 좌후
    ("crab_rr",    -SQ,  -SQ),   # ↘ 우후
])
def test_eight_directions_point_where_labelled(key, ex, ey):
    v = M.motion_unit_vector(M.BY_KEY[key])
    assert approx_vec(v, ex, ey, tol=1e-9), f"{key}: 기대 ({ex:.3f},{ey:.3f}) 실제 ({v[0]:.3f},{v[1]:.3f})"


def test_all_direction_vectors_are_unit_length():
    for key in ("forward", "backward", "crab_left", "crab_right",
                "crab_fl", "crab_fr", "crab_rl", "crab_rr"):
        v = M.motion_unit_vector(M.BY_KEY[key])
        assert math.hypot(*v) == pytest.approx(1.0)


def test_stop_modes_have_zero_motion():
    for key in ("stop", "steer_only", "home"):
        assert M.motion_unit_vector(M.BY_KEY[key]) == (0.0, 0.0)
        assert M.BY_KEY[key].raw_sign == 0


# ── ③ verified 라벨이 근거 등급과 일치하는가 (추측 금지의 코드 표현) ────────
@pytest.mark.parametrize("key", ["forward", "backward", "crab_left", "crab_right"])
def test_cardinal_modes_are_verified(key):
    """4방위는 직접 실측(또는 raw 부호 반전)이므로 verified=True."""
    assert M.BY_KEY[key].verified is True


@pytest.mark.parametrize("key", ["crab_fl", "crab_fr", "crab_rl", "crab_rr"])
def test_diagonal_modes_are_marked_unverified(key):
    """대각 45° 는 도출일 뿐 직접 관측이 없다 — verified=False 여야 UI 에 ⚠ 가 뜬다."""
    m = M.BY_KEY[key]
    assert m.verified is False, f"{key} 를 검증됨으로 표시하면 안 된다(직접 실측 없음)"
    assert "도출" in m.basis
    assert abs(m.steer_deg) == 45.0


def test_every_mode_cites_its_basis():
    for m in M.ALL_MODES:
        assert m.basis and len(m.basis) > 5, f"{m.key} 에 근거 인용이 없다"
        assert m.arrow, f"{m.key} 에 방향 기호가 없다"


# ── ④ 조향각이 램프 하드 리밋 안에 있는가 ───────────────────────────────────
def test_all_mode_steer_targets_within_hard_limit():
    from amr_test_gui.ramp import STEER_LIMIT_DEG
    for m in M.ALL_MODES:
        assert abs(m.steer_deg) <= STEER_LIMIT_DEG, f"{m.key} 목표각이 하드 리밋 초과"


# ── ⑤ 방향 패드 배치가 화면 방향과 맞는가 ───────────────────────────────────
def test_pad_layout_matches_screen_directions():
    """3×3 패드: 위=전방(+x), 아래=후방, 왼쪽=좌(+y), 오른쪽=우."""
    assert len(M.PAD_LAYOUT) == 9
    for (r, c), key in M.PAD_LAYOUT.items():
        vx, vy = M.motion_unit_vector(M.BY_KEY[key])
        if key == "stop":
            assert (r, c) == (1, 1)
            continue
        expect_row = 0 if vx > 1e-9 else (2 if vx < -1e-9 else 1)
        expect_col = 0 if vy > 1e-9 else (2 if vy < -1e-9 else 1)
        assert (r, c) == (expect_row, expect_col), \
            f"{key} 가 패드 ({r},{c}) 에 있으나 이동은 ({vx:+.2f},{vy:+.2f})"
