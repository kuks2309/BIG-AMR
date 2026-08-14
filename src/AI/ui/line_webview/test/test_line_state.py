"""line_state 단위 테스트 — 시계를 주입해 나이·수신율을 결정적으로 검증한다."""

import math

from line_webview.line_state import LineState, centerline_points


class FakeClock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


class TestLineState:

    def test_no_sample_reports_not_received(self):
        assert LineState(FakeClock()).snapshot() == {"received": False}

    def test_snapshot_carries_fields(self):
        st = LineState(FakeClock())
        st.put(True, -0.25, 0.1, 0.93, "cam_f")
        snap = st.snapshot()
        assert snap["received"] is True
        assert snap["detected"] is True
        assert snap["offset"] == -0.25
        assert snap["camera"] == "cam_f"
        assert snap["confidence"] == 0.93

    def test_age_grows_with_clock(self):
        clock = FakeClock()
        st = LineState(clock)
        st.put(True, 0.0, 0.0, 0.9, "cam_f")
        clock.advance(0.35)
        assert abs(st.snapshot()["age_ms"] - 350.0) < 1e-6

    def test_undetected_sample_is_kept(self):
        # 소실을 화면에서 봐야 하므로 미검출도 보관한다
        st = LineState(FakeClock())
        st.put(False, 0.0, 0.0, 0.0, "cam_r")
        assert st.snapshot()["detected"] is False

    def test_hz_needs_two_samples(self):
        clock = FakeClock()
        st = LineState(clock)
        st.put(True, 0.0, 0.0, 0.9, "cam_f")
        assert st.snapshot()["hz"] == 0.0
        clock.advance(0.05)
        st.put(True, 0.0, 0.0, 0.9, "cam_f")
        assert abs(st.snapshot()["hz"] - 20.0) < 0.05

    def test_hz_window_is_bounded(self):
        clock = FakeClock()
        st = LineState(clock)
        for _ in range(200):
            clock.advance(0.04)
            st.put(True, 0.0, 0.0, 0.9, "cam_f")
        assert abs(st.snapshot()["hz"] - 25.0) < 0.5


class TestCenterlinePoints:

    def test_centered_vertical_line(self):
        g = centerline_points(0.0, 0.0, 0.8)
        assert abs(g["cx"] - 0.5) < 1e-9
        assert abs(g["cy"] - 0.8) < 1e-9
        assert abs(g["x1"] - 0.5) < 1e-9  # 수직이라 위아래 x 가 같다
        assert abs(g["x2"] - 0.5) < 1e-9

    def test_offset_moves_control_point_right(self):
        assert centerline_points(0.5, 0.0, 0.8)["cx"] == 0.75

    def test_offset_moves_control_point_left(self):
        assert centerline_points(-0.5, 0.0, 0.8)["cx"] == 0.25

    def test_positive_angle_leans_right_at_top(self):
        # angle(+) = 위쪽이 오른쪽으로 기움 → 화면 위(y=0)의 x 가 제어점보다 크다
        g = centerline_points(0.0, 0.3, 0.8)
        assert g["x1"] > g["cx"]
        assert g["x2"] < g["cx"]

    def test_slope_magnitude_follows_tangent(self):
        # 정사각 화면(aspect=1)이면 정규화 기울기 = tan(angle) 그대로.
        # 좌표는 JSON 크기를 줄이려 소수 4자리로 반올림하므로 허용오차도 그 정밀도로 둔다.
        g = centerline_points(0.0, 0.4, 0.5, aspect=1.0)
        assert abs((g["x1"] - g["cx"]) - math.tan(0.4) * 0.5) < 1e-4

    def test_aspect_flattens_slope(self):
        # 16:9 화면에서는 픽셀 기울기가 정규화 좌표에서 1/aspect 로 눕는다.
        # 이 보정을 빠뜨리면 선이 1.78배 가팔라져 제어점에서만 맞는다(2026-08-14 실측).
        wide = centerline_points(0.0, 0.4, 0.5, aspect=16.0 / 9.0)
        square = centerline_points(0.0, 0.4, 0.5, aspect=1.0)
        assert abs((wide["x1"] - 0.5) * (16.0 / 9.0) - (square["x1"] - 0.5)) < 1e-3

    def test_zero_aspect_falls_back_to_one(self):
        # 잘못된 설정으로 0 이 들어와도 0 나눗셈으로 죽지 않는다.
        g = centerline_points(0.0, 0.4, 0.5, aspect=0.0)
        assert abs((g["x1"] - g["cx"]) - math.tan(0.4) * 0.5) < 1e-4

    def test_control_row_is_clamped(self):
        assert centerline_points(0.0, 0.0, 5.0)["cy"] == 1.0
        assert centerline_points(0.0, 0.0, -3.0)["cy"] == 0.0
