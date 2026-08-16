"""centerline 단위 테스트 — 합성 마스크로 피팅·오차 계산 검증."""

import math

import numpy as np
import pytest

from line_vision.centerline import (CenterLine, fit_centerline, fit_centerline_roi,
                                   line_x_at_row, select_line_in_roi,
                                   line_error)


def _vertical_band_mask(h=100, w=100, x_center=50, half_width=3):
    mask = np.zeros((h, w), np.uint8)
    mask[:, x_center - half_width:x_center + half_width + 1] = 255
    return mask


class TestFitCenterline:

    def test_empty_mask_invalid(self):
        assert fit_centerline(np.zeros((10, 10), np.uint8)).valid is False

    def test_none_and_wrong_dtype_invalid(self):
        assert fit_centerline(None).valid is False
        assert fit_centerline(np.zeros((10, 10), np.float32)).valid is False

    def test_vertical_band_fits_vertical_line(self):
        line = fit_centerline(_vertical_band_mask(x_center=40))
        assert line.valid
        # 수직 밴드 → 방향벡터가 y축에 정렬, 통과점 x=40
        assert abs(line.vx) < 0.01
        assert abs(abs(line.vy) - 1.0) < 0.01
        assert abs(line.x0 - 40.0) < 0.5

    def test_diagonal_line_45deg(self):
        mask = np.zeros((100, 100), np.uint8)
        for i in range(100):
            mask[i, max(0, i - 2):min(100, i + 3)] = 255
        line = fit_centerline(mask)
        assert line.valid
        # 대각선 → |vx| == |vy| (45도)
        assert abs(abs(line.vx) - abs(line.vy)) < 0.02

    def test_horizontal_band_uses_column_scan(self):
        mask = _vertical_band_mask().T.copy()  # 수평 밴드
        line = fit_centerline(mask)
        assert line.valid
        assert abs(line.vy) < 0.01  # 수평 방향

    def test_single_pixel_invalid(self):
        mask = np.zeros((10, 10), np.uint8)
        mask[5, 5] = 255
        assert fit_centerline(mask).valid is False

    def test_wide_frame_endpoints_span_mask_extent(self):
        # 16:9 프레임(Big-AMR 1280x720 로스터)에서도 끝점이 마스크 세로 범위를 덮는다
        mask = _vertical_band_mask(h=720, w=1280, x_center=640)
        line = fit_centerline(mask)
        assert line.valid
        ys = sorted([line.p1[1], line.p2[1]])
        assert ys[0] < 1.0 and ys[1] > 718.0


class TestLineError:

    def test_center_vertical_line_zero_error(self):
        line = fit_centerline(_vertical_band_mask(x_center=50))
        offset, angle = line_error(line, 100, 100, 0.8)
        assert abs(offset) < 0.02
        assert abs(angle) < 0.02

    def test_right_side_line_positive_offset(self):
        line = fit_centerline(_vertical_band_mask(x_center=75))
        offset, _ = line_error(line, 100, 100, 0.8)
        assert 0.4 < offset < 0.6  # (75-50)/50 = 0.5

    def test_left_side_line_negative_offset(self):
        line = fit_centerline(_vertical_band_mask(x_center=25))
        offset, _ = line_error(line, 100, 100, 0.8)
        assert -0.6 < offset < -0.4

    def test_tilt_right_positive_angle(self):
        # 위로 갈수록 오른쪽(x 증가)으로 기우는 45도 라인
        mask = np.zeros((100, 100), np.uint8)
        for y in range(100):
            x = 99 - y  # y=99(아래)에서 x=0, y=0(위)에서 x=99
            mask[y, max(0, x - 2):min(100, x + 3)] = 255
        line = fit_centerline(mask)
        _, angle = line_error(line, 100, 100, 0.8)
        assert abs(angle - math.pi / 4) < 0.05

    def test_offset_clipped_to_unit_range(self):
        # 통과점이 화면 밖을 가리키는 극단 케이스 — 클리핑 확인
        line = CenterLine(valid=True, vx=0.0, vy=1.0, x0=250.0, y0=50.0)
        offset, _ = line_error(line, 100, 100, 0.8)
        assert offset == 1.0

    def test_wide_frame_offset_uses_half_width(self):
        # 1280 폭에서 x=960 → (960-640)/640 = 0.5. 4:3 학습본과 정규화 규칙이 같은지 확인
        line = CenterLine(valid=True, vx=0.0, vy=1.0, x0=960.0, y0=360.0)
        offset, _ = line_error(line, 1280, 720, 0.8)
        assert abs(offset - 0.5) < 0.01


class TestCameraForDirection:
    """방향 → 카메라 선택. 노드 모듈은 ROS 인터페이스가 필요하므로 없으면 건너뛴다."""

    @staticmethod
    def _fn():
        node = pytest.importorskip("line_vision.line_seg_node")
        return node.camera_for_direction

    def test_forward_picks_front_camera(self):
        assert self._fn()("forward", "cam_f", "cam_r") == "cam_f"

    def test_reverse_picks_rear_camera(self):
        assert self._fn()("reverse", "cam_f", "cam_r") == "cam_r"

    def test_case_and_whitespace_tolerated(self):
        assert self._fn()(" Reverse ", "cam_f", "cam_r") == "cam_r"

    def test_unknown_direction_falls_back_to_forward(self):
        # 오타 하나로 카메라를 잃는 것보다 전방을 보는 편이 안전하다
        assert self._fn()("sideways", "cam_f", "cam_r") == "cam_f"


# ── 기준행 ROI 씨앗·추적 (fit_centerline_roi) ──
# 실기에서 바닥 라인이 격자로 여러 개일 때 엉뚱한 선을 잡는 것을 막는 경로다.


def _blank(h=200, w=400):
    return np.zeros((h, w), dtype=np.uint8)


def _vline(mask, x, thickness=6, y0=0, y1=None):
    h = mask.shape[0]
    y1 = h if y1 is None else y1
    mask[y0:y1, x - thickness // 2:x + thickness // 2 + 1] = 255
    return mask


def test_roi_picks_line_nearest_center_not_the_widest():
    """격자: 화면 중앙 근처 선을 고른다 — 굵기·개수에 휘둘리지 않는다."""
    m = _blank()
    _vline(m, 210, thickness=6)     # 중앙(200) 근처
    _vline(m, 380, thickness=20)    # 화면 끝, 훨씬 굵다
    line = fit_centerline_roi(m, 0.8)
    assert line.valid
    offset, _ = line_error(line, 400, 200, 0.8)
    assert abs(offset - (210 - 200) / 200.0) < 0.05


def test_roi_returns_invalid_when_no_line_at_control_row():
    """기준행 띠에 전경이 없으면 외삽하지 않고 미검출로 낸다."""
    m = _blank()
    _vline(m, 210, y0=0, y1=60)     # 화면 위쪽에만 있고 기준행(y=159)엔 없다
    line = fit_centerline_roi(m, 0.8)
    assert not line.valid


def test_roi_follows_prefer_x_over_center():
    """직전 프레임 위치(prefer_x)를 주면 중앙보다 그쪽을 잇는다 — 프레임 간 연관."""
    m = _blank()
    _vline(m, 210)
    _vline(m, 360)
    near_center = fit_centerline_roi(m, 0.8)
    tracked = fit_centerline_roi(m, 0.8, prefer_x=360.0)
    o_center, _ = line_error(near_center, 400, 200, 0.8)
    o_track, _ = line_error(tracked, 400, 200, 0.8)
    assert o_center < o_track
    assert abs(o_track - (360 - 200) / 200.0) < 0.05


def test_roi_ignores_crossing_horizontal_line():
    """가로선이 교차해도 세로선을 계속 따라간다 — 구간 폭이 튀는 줄은 건너뛴다."""
    m = _blank()
    _vline(m, 200)
    m[100:106, :] = 255            # 가로로 화면을 가로지르는 선
    line = fit_centerline_roi(m, 0.8)
    assert line.valid
    offset, angle = line_error(line, 400, 200, 0.8)
    assert abs(offset) < 0.05
    assert abs(angle) < math.radians(5)


def test_roi_matches_plain_fit_on_single_clean_line():
    """라인이 하나뿐이면 기존 방식과 같은 답을 낸다 — 무회귀."""
    m = _blank()
    _vline(m, 240)
    a, _ = line_error(fit_centerline(m), 400, 200, 0.8)
    b, _ = line_error(fit_centerline_roi(m, 0.8), 400, 200, 0.8)
    assert abs(a - b) < 0.02


# ── 직선-ROI 판정 (select_line_in_roi) ──
# 픽셀이 기준행에 있느냐가 아니라 **피팅된 직선이 ROI 를 지나느냐**로 고른다.


def _line_through(x_top, x_bottom, h=200):
    """(x_top, 0) ~ (x_bottom, h-1) 을 지나는 CenterLine."""
    dx, dy = float(x_bottom - x_top), float(h - 1)
    n = math.hypot(dx, dy)
    return CenterLine(valid=True, vx=dx / n, vy=dy / n, x0=float(x_top), y0=0.0)


def test_roi_line_rejects_candidate_crossing_outside_roi():
    """화면 끝을 지나는 직선은 ROI 밖이라 후보에서 빠진다."""
    inside = _line_through(210, 210)
    outside = _line_through(390, 390)
    picked = select_line_in_roi([outside, inside], 400, 200, 0.8, roi_half_width_ratio=0.6)
    assert picked is inside


def test_roi_line_accepts_when_pixels_absent_at_control_row():
    """직선 판정이므로 기준행에 픽셀이 없어도(끊긴 구간) 후보로 남는다."""
    line = _line_through(200, 200)
    assert select_line_in_roi([line], 400, 200, 0.8) is line


def test_roi_line_prefers_previous_position():
    """둘 다 ROI 안이면 직전 위치(prefer_x)에 가까운 것을 고른다."""
    a = _line_through(180, 180)
    b = _line_through(260, 260)
    assert select_line_in_roi([a, b], 400, 200, 0.8, prefer_x=255.0) is b
    assert select_line_in_roi([a, b], 400, 200, 0.8, prefer_x=175.0) is a


def test_roi_line_returns_none_when_all_outside():
    """ROI 를 지나는 후보가 없으면 None — 미검출로 보고해야 한다."""
    assert select_line_in_roi([_line_through(395, 395)], 400, 200, 0.8,
                              roi_half_width_ratio=0.3) is None


def test_line_x_at_row_matches_geometry():
    line = _line_through(100, 300)          # 아래로 갈수록 오른쪽
    assert abs(line_x_at_row(line, 0.0) - 100) < 1e-6
    assert abs(line_x_at_row(line, 199.0) - 300) < 1e-6
