"""detection 모듈 단위 테스트 — ROS·GPU·카메라 무접촉."""
import pytest

from yolo_detector.detection import (Box, build_boxes, clamp_box, keep_class,
                                     missing_class_names, next_camera_index,
                                     per_camera_hz, resolve_class_filter)

NAMES = {0: "person", 1: "bicycle", 2: "car"}
IMG_W, IMG_H = 1280, 720


# ── 라운드로빈 ──────────────────────────────────────────────────────────────
def test_round_robin_wraps():
    assert [next_camera_index(c, 3) for c in (-1, 0, 1, 2)] == [0, 1, 2, 0]


def test_round_robin_handles_zero_cameras():
    assert next_camera_index(0, 0) == 0


def test_per_camera_hz_divides_budget():
    assert per_camera_hz(30.0, 6) == pytest.approx(5.0)


def test_per_camera_hz_zero_cameras_is_zero():
    assert per_camera_hz(30.0, 0) == 0.0


# ── 클래스 필터 ─────────────────────────────────────────────────────────────
def test_empty_filter_passes_everything():
    assert keep_class(7, ()) is True


def test_filter_blocks_other_classes():
    assert keep_class(0, (0,)) is True
    assert keep_class(2, (0,)) is False


def test_resolve_names_to_indices():
    assert resolve_class_filter(NAMES, ["person", "car"]) == (0, 2)


def test_resolve_empty_means_all():
    assert resolve_class_filter(NAMES, []) == ()


def test_resolve_drops_unknown_names():
    """모델에 없는 이름은 제외된다 — 조용히 전체 허용으로 바뀌면 안 된다."""
    assert resolve_class_filter(NAMES, ["person", "pallet"]) == (0,)


def test_missing_names_are_reported():
    assert missing_class_names(NAMES, ["person", "pallet", "forklift"]) == ["pallet", "forklift"]


def test_missing_names_empty_when_all_present():
    assert missing_class_names(NAMES, ["person"]) == []


# ── 박스 정리 ───────────────────────────────────────────────────────────────
def test_clamp_keeps_inside_box_intact():
    assert clamp_box(10, 20, 110, 220, IMG_W, IMG_H) == (10, 20, 100, 200)


def test_clamp_cuts_negative_coordinates():
    """모델이 이미지 밖 좌표를 내면 소비자가 음수 인덱스로 자르다 터진다."""
    x, y, w, h = clamp_box(-50, -30, 100, 100, IMG_W, IMG_H)
    assert (x, y) == (0, 0)
    assert (w, h) == (100, 100)


def test_clamp_cuts_overflow_beyond_image():
    x, y, w, h = clamp_box(1200, 700, 1400, 900, IMG_W, IMG_H)
    assert x + w <= IMG_W
    assert y + h <= IMG_H


def test_clamp_normalizes_inverted_box():
    assert clamp_box(100, 100, 50, 50, IMG_W, IMG_H) == (50, 50, 50, 50)


def test_clamp_fully_outside_box_has_zero_area():
    _, _, w, h = clamp_box(2000, 2000, 2100, 2100, IMG_W, IMG_H)
    assert w == 0 and h == 0


# ── build_boxes ─────────────────────────────────────────────────────────────
def test_build_filters_by_class():
    rows = [(0, 0.9, 10, 10, 110, 210), (2, 0.8, 20, 20, 120, 220)]
    boxes = build_boxes(rows, NAMES, (0,), IMG_W, IMG_H)
    assert [b.class_name for b in boxes] == ["person"]


def test_build_sorts_by_confidence_descending():
    rows = [(0, 0.4, 10, 10, 110, 210), (0, 0.95, 20, 20, 120, 220), (0, 0.7, 30, 30, 130, 230)]
    boxes = build_boxes(rows, NAMES, (), IMG_W, IMG_H)
    assert [b.confidence for b in boxes] == [0.95, 0.7, 0.4]


def test_build_drops_degenerate_tiny_boxes():
    rows = [(0, 0.9, 10, 10, 12, 12)]          # 변 2 px
    assert build_boxes(rows, NAMES, (), IMG_W, IMG_H) == []


def test_build_drops_fully_offscreen_boxes():
    rows = [(0, 0.9, 5000, 5000, 5100, 5100)]
    assert build_boxes(rows, NAMES, (), IMG_W, IMG_H) == []


def test_build_handles_no_detections():
    assert build_boxes([], NAMES, (), IMG_W, IMG_H) == []


def test_build_uses_index_when_name_unknown():
    boxes = build_boxes([(77, 0.9, 10, 10, 110, 210)], NAMES, (), IMG_W, IMG_H)
    assert boxes[0].class_name == "77"


def test_build_returns_box_dataclass():
    boxes = build_boxes([(0, 0.9, 10, 20, 110, 220)], NAMES, (), IMG_W, IMG_H)
    assert boxes[0] == Box(class_id=0, class_name="person", confidence=0.9,
                           x=10, y=20, width=100, height=200)
