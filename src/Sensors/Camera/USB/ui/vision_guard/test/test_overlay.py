# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""오버레이 좌표 변환·나이 판정 회귀 테스트 (Qt·ROS 무접촉).

좌표 변환이 틀리면 "사람 옆에 박스가 그려지는" 안전 오인식이 되고, 눈으로는 미묘해서
놓치기 쉽다. 레터박스 축이 타일 종횡비에 따라 뒤집힌다는 점이 특히 함정이다.
"""

from types import SimpleNamespace

import pytest

from vision_guard.overlay import (EXPIRED, FRESH, FRESH_MS, STALE, STALE_MS,
                                  build_view_boxes, classify_age,
                                  detector_status, map_box)

SRC = (1280, 720)


def det(x, y, w, h, name="person", conf=0.9):
    return SimpleNamespace(x=x, y=y, width=w, height=h, class_name=name, confidence=conf)


# ── classify_age ────────────────────────────────────────────────────────────
def test_fresh_below_threshold():
    assert classify_age(0.0) == FRESH
    assert classify_age(FRESH_MS - 0.1) == FRESH


def test_stale_between_thresholds():
    assert classify_age(FRESH_MS) == STALE
    assert classify_age(STALE_MS - 0.1) == STALE


def test_expired_at_and_above_threshold():
    assert classify_age(STALE_MS) == EXPIRED
    assert classify_age(10_000.0) == EXPIRED


def test_negative_age_treated_as_fresh():
    """`classify_age` 자체는 음수를 FRESH 로 본다 — 부호 처리는 호출자(`_age_ms`) 책임이다.

    `_age_ms` 가 절대값을 넘기므로 실제로는 음수가 들어오지 않는다
    (`test_stale_detection.py::test_age_ms_uses_absolute_difference` 가 그 계약을 고정).
    """
    assert classify_age(-50.0) == FRESH


# ── map_box: 배율 ───────────────────────────────────────────────────────────
def test_exact_fit_is_identity():
    assert map_box((10, 20, 100, 200), SRC, SRC, SRC) == (10, 20, 100, 200)


def test_uniform_downscale():
    """1280x720 -> 640x360 (배율 0.5), 레터박스 없음."""
    assert map_box((100, 200, 400, 300), SRC, (640, 360), (640, 360)) == (50, 100, 200, 150)


def test_scale_uses_actual_pixmap_not_computed_ratio():
    """`scaled()` 는 내림하므로 계산 배율과 실제 pixmap 이 어긋난다 — 실제 크기를 써야 한다.

    label 1272x668 에 16:9 를 넣으면 pixmap 은 1187x668 이지 1272 폭이 아니다.
    계산식(min(1272/1280, 668/720)=0.9278)을 쓰면 폭이 어긋난다.
    """
    mapped = map_box((0, 0, 1280, 720), SRC, (1187, 668), (1272, 668))
    assert mapped[2] == 1187        # 폭이 실제 pixmap 폭과 일치
    assert mapped[3] == 668


# ── map_box: 레터박스 ───────────────────────────────────────────────────────
def test_horizontal_letterbox_offsets_x():
    """넓은 타일 — 좌우에 여백. 오프셋 없이 그리면 박스가 왼쪽으로 밀린다."""
    mapped = map_box((0, 0, 1280, 720), SRC, (640, 360), (800, 360))
    assert mapped[0] == 80          # (800-640)/2
    assert mapped[1] == 0


def test_vertical_letterbox_offsets_y():
    """세로로 긴 타일 — 상하에 여백. 2x3 그리드에서 실제로 이 축이 된다."""
    mapped = map_box((0, 0, 1280, 720), SRC, (420, 236), (420, 315))
    assert mapped[0] == 0
    assert mapped[1] == 40          # round((315-236)/2)


def test_letterbox_axis_flips_between_layouts():
    """같은 영상이라도 타일 종횡비에 따라 여백 축이 뒤집힌다 — 한 축만 처리하면 틀린다."""
    wide = map_box((0, 0, 1280, 720), SRC, (640, 360), (900, 360))
    tall = map_box((0, 0, 1280, 720), SRC, (640, 360), (640, 500))
    assert wide[0] > 0 and wide[1] == 0
    assert tall[0] == 0 and tall[1] > 0


def test_box_stays_inside_pixmap_area():
    """우하단 경계 박스가 픽스맵 밖으로 나가면 안 된다."""
    x, y, w, h = map_box((1180, 620, 100, 100), SRC, (640, 360), (800, 400))
    off_x, off_y = (800 - 640) / 2, (400 - 360) / 2
    assert x + w <= off_x + 640 + 1      # 반올림 오차 1 px 허용
    assert y + h <= off_y + 360 + 1


# ── map_box: 방어 ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("src,pix", [((0, 720), (640, 360)), ((1280, 0), (640, 360)),
                                     ((1280, 720), (0, 360)), ((1280, 720), (640, 0))])
def test_zero_dimension_returns_none(src, pix):
    assert map_box((0, 0, 10, 10), src, pix, (640, 360)) is None


# ── build_view_boxes ────────────────────────────────────────────────────────
def test_expired_boxes_are_not_drawn():
    assert build_view_boxes([det(0, 0, 100, 100)], SRC, SRC, SRC, age_ms=STALE_MS + 1) == []


def test_freshness_is_propagated():
    fresh = build_view_boxes([det(0, 0, 100, 100)], SRC, SRC, SRC, age_ms=10)
    stale = build_view_boxes([det(0, 0, 100, 100)], SRC, SRC, SRC, age_ms=300)
    assert fresh[0].freshness == FRESH
    assert stale[0].freshness == STALE


def test_label_includes_class_and_confidence():
    boxes = build_view_boxes([det(0, 0, 100, 100, "person", 0.87)], SRC, SRC, SRC, age_ms=0)
    assert boxes[0].label == "person 0.87"


def test_degenerate_box_is_dropped():
    """축소로 폭이 0이 된 박스는 그리지 않는다."""
    assert build_view_boxes([det(0, 0, 1, 1)], SRC, (64, 36), (64, 36), age_ms=0) == []


def test_no_detections_yields_no_boxes():
    assert build_view_boxes([], SRC, SRC, SRC, age_ms=0) == []


# ── detector_status ─────────────────────────────────────────────────────────
def test_status_no_publisher():
    text, ok = detector_status(0, None, 0.21)
    assert ok is False and "탐지기 없음" in text


def test_status_waiting_first_message():
    text, ok = detector_status(1, None, 0.21)
    assert ok is False and "대기" in text


def test_status_healthy():
    text, ok = detector_status(1, 0.1, 0.21)
    assert ok is True and "감시 중" in text


def test_status_unresponsive_after_two_periods():
    text, ok = detector_status(1, 0.5, 0.21)
    assert ok is False and "응답 없음" in text


def test_status_partial_outage_when_some_camera_never_reported():
    """감시 대상 중 한 번도 결과를 못 받은 카메라가 있으면 부분 고장으로 드러나야 한다.

    회귀 방어: 종전에는 수신 시각이 **단일 스칼라**라 6대 합산을 보았고, 한 대가 죽어도
    나머지 5대가 타이머를 갱신해 "감시 중" 이 유지됐다.
    """
    text, ok = detector_status(1, float("inf"), 0.21)
    assert ok is False
    assert "무응답" in text
    assert "inf" not in text        # f-string 으로 inf 가 새어나오면 안 된다


def test_status_distinguishes_dead_from_empty():
    """'사람 없음'과 '탐지기 죽음'이 같은 화면이면 안 된다 — 문구가 달라야 한다."""
    dead, _ = detector_status(0, None, 0.21)
    alive, _ = detector_status(1, 0.05, 0.21)
    assert dead != alive
