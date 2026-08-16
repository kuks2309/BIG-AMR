"""가상 라인 센서 기하 단위테스트 — 부호 규약이 제어와 어긋나면 여기서 잡힌다."""

import math

import pytest

from line_sim_sensor.line_geometry import (LineSegment, anchor_line, measure,
                                          normalize_angle)

STRAIGHT = LineSegment(x0=0.0, y0=0.0, heading=0.0, length=10.0)
LOOKAHEAD = 1.0
HALF_W = 0.6


class TestSignConvention:
    """offset(+) = 라인이 진행방향 기준 오른쪽. angle(+) = 먼 쪽이 오른쪽으로 기움."""

    def test_on_line_gives_zero_offset(self):
        m = measure(0.0, 0.0, 0.0, STRAIGHT, LOOKAHEAD, HALF_W)
        assert m.detected
        assert abs(m.offset) < 1e-9
        assert abs(m.angle) < 1e-9

    def test_robot_right_of_line_gives_positive_offset(self):
        # 라인은 y=0, 로봇은 y=-0.2 → +x 를 보면 라인은 왼쪽 → offset 음수
        m = measure(0.0, -0.2, 0.0, STRAIGHT, LOOKAHEAD, HALF_W)
        assert m.offset < 0.0

    def test_robot_left_of_line_gives_negative_offset(self):
        # 로봇이 y=+0.2 → 라인(y=0)은 오른쪽 → offset 양수
        m = measure(0.0, 0.2, 0.0, STRAIGHT, LOOKAHEAD, HALF_W)
        assert m.offset > 0.0

    def test_offset_is_normalized_by_half_width(self):
        m = measure(0.0, 0.3, 0.0, STRAIGHT, LOOKAHEAD, HALF_W)
        assert abs(m.offset - 0.5) < 1e-9  # 0.3 / 0.6

    def test_offset_saturates_at_unit(self):
        m = measure(0.0, 5.0, 0.0, STRAIGHT, LOOKAHEAD, HALF_W)
        assert m.offset == 1.0
        assert not m.detected  # 화각 밖

    def test_heading_left_of_line_gives_positive_angle(self):
        # 진행 heading 이 라인보다 CCW(왼쪽) → 라인은 화면에서 오른쪽으로 흘러간다
        m = measure(0.0, 0.0, 0.2, STRAIGHT, LOOKAHEAD, HALF_W)
        assert m.angle > 0.0

    def test_heading_right_of_line_gives_negative_angle(self):
        m = measure(0.0, 0.0, -0.2, STRAIGHT, LOOKAHEAD, HALF_W)
        assert m.angle < 0.0


class TestControlConsistency:
    """제어가 이 오차를 받아 라인 쪽으로 조향하는지 — 부호를 함께 검사한다."""

    def test_correcting_steer_reduces_offset(self):
        # 로봇이 라인 왼쪽(offset +)이면 제어는 오른쪽으로 꺾는다(전진 δ<0).
        # 오른쪽으로 꺾어 진행하면 y 가 줄어 라인에 가까워져야 한다.
        before = measure(0.0, 0.2, 0.0, STRAIGHT, LOOKAHEAD, HALF_W)
        after = measure(0.3, 0.1, -0.1, STRAIGHT, LOOKAHEAD, HALF_W)
        assert before.offset > 0.0
        assert after.offset < before.offset

    def test_reverse_flips_offset_sign_for_same_pose(self):
        # 같은 자세라도 진행방향이 뒤집히면 좌우가 뒤집힌다
        fwd = measure(1.0, 0.2, 0.0, STRAIGHT, LOOKAHEAD, HALF_W)
        rev = measure(1.0, 0.2, 0.0, STRAIGHT, LOOKAHEAD, HALF_W, reverse=True)
        assert fwd.offset > 0.0
        assert rev.offset < 0.0

    def test_line_pointing_backwards_is_aligned_to_travel(self):
        # 라인 heading 이 진행방향과 반대(π)여도 angle 이 ±π 로 튀지 않는다 —
        # 정렬하지 않으면 제어가 최대 조향을 요구한다
        flipped = LineSegment(x0=10.0, y0=0.0, heading=math.pi, length=10.0)
        m = measure(1.0, 0.0, 0.0, flipped, LOOKAHEAD, HALF_W)
        assert abs(m.angle) < 1e-9


class TestSegmentExtent:

    def test_before_start_is_not_detected(self):
        m = measure(-5.0, 0.0, 0.0, STRAIGHT, LOOKAHEAD, HALF_W)
        assert not m.detected

    def test_past_end_is_not_detected(self):
        # 라인 끝(10 m) 을 지나면 미검출 → 제어의 coast·abort 경로가 시험된다
        m = measure(10.5, 0.0, 0.0, STRAIGHT, LOOKAHEAD, HALF_W)
        assert not m.detected

    def test_inside_segment_is_detected(self):
        m = measure(5.0, 0.0, 0.0, STRAIGHT, LOOKAHEAD, HALF_W)
        assert m.detected
        assert abs(m.along - 6.0) < 1e-9  # 5.0 + lookahead 1.0

    def test_lookahead_moves_measurement_point(self):
        near = measure(0.0, 0.0, 0.0, STRAIGHT, 0.5, HALF_W)
        far = measure(0.0, 0.0, 0.0, STRAIGHT, 2.0, HALF_W)
        assert abs(near.along - 0.5) < 1e-9
        assert abs(far.along - 2.0) < 1e-9


class TestGuards:

    def test_zero_half_width_returns_undetected(self):
        assert not measure(0.0, 0.0, 0.0, STRAIGHT, LOOKAHEAD, 0.0).detected

    def test_normalize_angle_folds_to_pi(self):
        assert abs(normalize_angle(3 * math.pi) - math.pi) < 1e-9
        assert abs(normalize_angle(-3 * math.pi) + math.pi) < 1e-9 or \
               abs(normalize_angle(-3 * math.pi) - math.pi) < 1e-9


class TestAnchorLine:
    """라인을 로봇 시작 자세 기준으로 놓는다 — 플랜트 초기 자세가 원점이 아니어도 성립해야 한다."""

    def test_origin_start_places_line_at_offsets(self):
        line = anchor_line(0.0, 0.0, 0.0, offset_x=0.0, offset_y=0.10,
                           heading_deg=0.0, length=10.0)
        assert abs(line.x0) < 1e-9
        assert abs(line.y0 - 0.10) < 1e-9
        assert abs(line.heading) < 1e-9

    def test_offset_is_relative_to_start_heading(self):
        # 로봇이 +90° 를 보고 있으면 "좌측 0.1 m" 는 맵에서 −x 방향이다
        line = anchor_line(0.0, 0.0, math.pi / 2, offset_x=0.0, offset_y=0.10,
                           heading_deg=0.0, length=10.0)
        assert abs(line.x0 + 0.10) < 1e-9
        assert abs(line.y0) < 1e-9
        assert abs(line.heading - math.pi / 2) < 1e-9

    def test_translated_start_carries_line_along(self):
        # 플랜트 시나리오 초기 자세(4.952, −2.327)에서도 라인이 옆 10 cm 에 놓인다
        line = anchor_line(4.952, -2.327, 0.0, offset_x=0.0, offset_y=0.10,
                           heading_deg=0.0, length=10.0)
        assert abs(line.x0 - 4.952) < 1e-9
        assert abs(line.y0 - (-2.227)) < 1e-9

    def test_anchored_line_is_detected_from_start_pose(self):
        # 앵커링의 목적 — 플랜트 시나리오 초기 자세에서 바로 검출돼야 한다.
        # 라인을 좌측 0.10 m 에 놓았으므로 진행방향 기준 라인은 왼쪽 → offset 음수이고,
        # 크기는 0.10/0.6 이다.
        sx, sy, syaw = 4.952, -2.327, 0.0
        line = anchor_line(sx, sy, syaw, 0.0, 0.10, 0.0, 10.0)
        m = measure(sx, sy, syaw, line, LOOKAHEAD, HALF_W)
        assert m.detected
        assert m.offset < 0.0
        assert abs(m.offset - (-0.10 / HALF_W)) < 1e-9

    def test_forward_offset_moves_line_start_ahead(self):
        line = anchor_line(0.0, 0.0, 0.0, offset_x=2.0, offset_y=0.0,
                           heading_deg=0.0, length=5.0)
        assert abs(line.x0 - 2.0) < 1e-9

    def test_heading_deg_is_relative_to_start_yaw(self):
        line = anchor_line(0.0, 0.0, 0.5, offset_x=0.0, offset_y=0.0,
                           heading_deg=30.0, length=5.0)
        assert abs(line.heading - (0.5 + math.radians(30.0))) < 1e-9


class TestCurvedLine:
    """곡률 ≠ 0 인 원호. 직선판과 **같은 부호 규약**을 지켜야 제어가 그대로 동작한다."""

    def test_zero_curvature_matches_straight(self):
        # 곡률 0 은 직선판과 완전히 같아야 한다(무회귀 보장)
        arc0 = LineSegment(0.0, 0.0, 0.0, 10.0, curvature=0.0)
        a = measure(0.0, 0.2, 0.0, arc0, LOOKAHEAD, HALF_W)
        b = measure(0.0, 0.2, 0.0, STRAIGHT, LOOKAHEAD, HALF_W)
        assert a.detected == b.detected
        assert abs(a.offset - b.offset) < 1e-12
        assert abs(a.angle - b.angle) < 1e-12

    def test_on_arc_gives_zero_offset(self):
        # 반경 5 m 좌선회 원호의 시점에 서서 접선 방향을 보면 오차 0
        arc = LineSegment(0.0, 0.0, 0.0, 20.0, curvature=1.0 / 5.0)
        m = measure(-LOOKAHEAD, 0.0, 0.0, arc, LOOKAHEAD, HALF_W)
        assert m.detected
        assert abs(m.offset) < 1e-6

    def test_left_turn_line_appears_left_ahead(self):
        # 좌선회 원호를 직진으로 바라보면 전방주시점에서 라인은 **왼쪽**에 있다 → offset 음수
        arc = LineSegment(0.0, 0.0, 0.0, 20.0, curvature=1.0 / 5.0)
        m = measure(0.0, 0.0, 0.0, arc, LOOKAHEAD, HALF_W)
        assert m.offset < 0.0

    def test_right_turn_line_appears_right_ahead(self):
        arc = LineSegment(0.0, 0.0, 0.0, 20.0, curvature=-1.0 / 5.0)
        m = measure(0.0, 0.0, 0.0, arc, LOOKAHEAD, HALF_W)
        assert m.offset > 0.0

    def test_tighter_curve_gives_larger_offset(self):
        loose = measure(0.0, 0.0, 0.0, LineSegment(0.0, 0.0, 0.0, 20.0, 1.0 / 10.0),
                        LOOKAHEAD, HALF_W)
        tight = measure(0.0, 0.0, 0.0, LineSegment(0.0, 0.0, 0.0, 20.0, 1.0 / 3.0),
                        LOOKAHEAD, HALF_W)
        assert abs(tight.offset) > abs(loose.offset)

    def test_arc_angle_matches_tangent_rotation(self):
        # 호를 s 만큼 진행하면 접선은 κ·s 만큼 회전한다 → 그 지점에서 angle ≈ -κ·s
        arc = LineSegment(0.0, 0.0, 0.0, 20.0, curvature=1.0 / 5.0)
        m = measure(-LOOKAHEAD, 0.0, 0.0, arc, LOOKAHEAD, HALF_W)
        assert abs(m.angle) < 1e-6           # 시점에서는 접선과 정렬
        assert abs(m.along) < 1e-6

    def test_arc_along_is_arc_length(self):
        arc = LineSegment(0.0, 0.0, 0.0, 20.0, curvature=1.0 / 5.0)
        m = measure(-LOOKAHEAD, 0.0, 0.0, arc, LOOKAHEAD, HALF_W)
        assert abs(m.along) < 1e-6
        # 시점에서 호를 따라 조금 간 지점의 진행량은 호 길이다
        s = 2.0
        th = s / 5.0
        px, py = 5.0 * math.sin(th), 5.0 * (1.0 - math.cos(th))
        m2 = measure(px, py, th, arc, 0.0, HALF_W)
        assert abs(m2.along - s) < 1e-6

    def test_past_arc_end_is_not_detected(self):
        arc = LineSegment(0.0, 0.0, 0.0, 2.0, curvature=1.0 / 5.0)
        th = 3.0 / 5.0
        px, py = 5.0 * math.sin(th), 5.0 * (1.0 - math.cos(th))
        assert not measure(px, py, th, arc, 0.0, HALF_W).detected

    def test_anchor_carries_curvature(self):
        line = anchor_line(1.0, 2.0, 0.0, 0.0, 0.0, 0.0, 10.0, curvature=0.25)
        assert abs(line.curvature - 0.25) < 1e-12


# ── 원호 진행량은 한 바퀴까지 단조 ──
# ±π 로 접으면 반 바퀴를 지나는 순간 along 이 음수로 뒤집혀 「라인 끝」으로 오판한다.


def test_arc_along_is_monotonic_past_half_circle():
    line = LineSegment(x0=0.0, y0=0.0, heading=0.0, length=20.0, curvature=0.5)  # R=2
    radius = 2.0
    prev = -1.0
    for deg in range(0, 360, 15):
        rad = math.radians(deg)
        # 원 위의 점 — 중심 (0, R), 시점 (0,0) 에서 좌선회로 rad 만큼 진행한 자리
        x = radius * math.sin(rad)
        y = radius * (1.0 - math.cos(rad))
        m = measure(x, y, rad, line, lookahead_m=1e-6, half_width_m=0.6)
        assert m.along >= prev - 1e-9, f"deg={deg} along={m.along} < prev={prev}"
        prev = m.along
    assert prev > math.pi * radius  # 반 바퀴를 넘겨도 계속 는다


def test_arc_beyond_half_circle_still_detected():
    # R=2 원호를 3/4 바퀴(9.42 m) 돈 자리 — 종전에는 along 이 음수라 미검출이었다
    line = LineSegment(x0=0.0, y0=0.0, heading=0.0, length=20.0, curvature=0.5)
    rad = math.radians(270.0)
    m = measure(2.0 * math.sin(rad), 2.0 * (1.0 - math.cos(rad)), rad, line,
                lookahead_m=1e-6, half_width_m=0.6)
    assert m.detected
    assert m.along == pytest.approx(2.0 * rad, abs=1e-6)


def test_arc_length_is_capped_at_one_lap():
    # length 가 원주보다 길어도 한 바퀴까지만 — 시점 바로 뒤(=거의 한 바퀴)는 구간 밖
    line = LineSegment(x0=0.0, y0=0.0, heading=0.0, length=100.0, curvature=0.5)
    circumference = 2.0 * math.pi * 2.0
    rad = math.radians(359.0)
    m = measure(2.0 * math.sin(rad), 2.0 * (1.0 - math.cos(rad)), rad, line,
                lookahead_m=1e-6, half_width_m=0.6)
    assert m.along <= circumference + 1e-9
    assert m.detected  # 닫힌 고리이므로 한 바퀴 안은 유효


def test_arc_shorter_than_circumference_rejects_behind_start():
    # length < 원주 이면 시점 뒤쪽은 종전대로 미검출이어야 한다 (무회귀)
    line = LineSegment(x0=0.0, y0=0.0, heading=0.0, length=4.0, curvature=0.5)
    rad = math.radians(-20.0)
    m = measure(2.0 * math.sin(rad), 2.0 * (1.0 - math.cos(rad)), rad, line,
                lookahead_m=1e-6, half_width_m=0.6)
    assert not m.detected
