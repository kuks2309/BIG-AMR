"""centerline 단위 테스트 — 합성 마스크로 피팅·오차 계산 검증."""

import math

import numpy as np
import pytest

from line_vision.centerline import CenterLine, fit_centerline, line_error


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
