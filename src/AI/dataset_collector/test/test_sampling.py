"""sampling 모듈 단위 테스트 — ROS·카메라 무접촉."""
import numpy as np
import pytest

from dataset_collector.sampling import (SampleVerdict, camera_name_from_topic,
                                        disk_free_gb, frame_filename,
                                        judge_frame, mean_abs_diff)

GRAY_SHAPE = (4, 4)


def gray(value):
    return np.full(GRAY_SHAPE, value, dtype=np.uint8)


# ── disk_free_gb ────────────────────────────────────────────────────────────
def test_disk_free_gb_is_positive_for_root():
    assert disk_free_gb("/") > 0.0


def test_disk_free_gb_raises_on_missing_path():
    with pytest.raises(OSError):
        disk_free_gb("/nonexistent-path-for-test")


# ── mean_abs_diff ───────────────────────────────────────────────────────────
def test_first_frame_has_infinite_diff():
    assert mean_abs_diff(None, gray(10)) == float("inf")


def test_shape_change_counts_as_new_scene():
    prev = np.zeros((4, 4), dtype=np.uint8)
    cur = np.zeros((8, 8), dtype=np.uint8)
    assert mean_abs_diff(prev, cur) == float("inf")


def test_identical_frames_have_zero_diff():
    assert mean_abs_diff(gray(77), gray(77)) == 0.0


def test_known_difference_is_exact():
    assert mean_abs_diff(gray(10), gray(14)) == pytest.approx(4.0)


def test_uint8_subtraction_does_not_wrap_around():
    """0 - 255 를 uint8 로 빼면 1 이 되어 '거의 동일'로 오판한다 — int16 승격 확인."""
    assert mean_abs_diff(gray(0), gray(255)) == pytest.approx(255.0)


# ── judge_frame ─────────────────────────────────────────────────────────────
def test_disk_floor_blocks_even_a_novel_frame():
    v = judge_frame(free_gb=1.0, min_free_gb=5.0, prev_gray=None,
                    cur_gray=gray(10), min_mean_abs_diff=3.0)
    assert v == SampleVerdict(False, "disk_low")


def test_disk_floor_is_inclusive():
    """여유 == 하한이면 이미 위험 — 저장하지 않는다."""
    v = judge_frame(free_gb=5.0, min_free_gb=5.0, prev_gray=None,
                    cur_gray=gray(10), min_mean_abs_diff=3.0)
    assert v.keep is False


def test_duplicate_frame_is_skipped():
    v = judge_frame(free_gb=100.0, min_free_gb=5.0, prev_gray=gray(50),
                    cur_gray=gray(51), min_mean_abs_diff=3.0)
    assert v == SampleVerdict(False, "duplicate")


def test_novel_frame_is_kept():
    v = judge_frame(free_gb=100.0, min_free_gb=5.0, prev_gray=gray(50),
                    cur_gray=gray(60), min_mean_abs_diff=3.0)
    assert v == SampleVerdict(True, "ok")


def test_first_frame_is_kept_when_disk_is_fine():
    v = judge_frame(free_gb=100.0, min_free_gb=5.0, prev_gray=None,
                    cur_gray=gray(0), min_mean_abs_diff=3.0)
    assert v.keep is True


def test_threshold_is_exclusive_lower_bound():
    """차이가 임계와 같으면 신규로 본다(< 임계만 중복)."""
    v = judge_frame(free_gb=100.0, min_free_gb=5.0, prev_gray=gray(10),
                    cur_gray=gray(13), min_mean_abs_diff=3.0)
    assert v.keep is True


# ── frame_filename ──────────────────────────────────────────────────────────
def test_frame_filename_is_zero_padded_and_sortable():
    assert frame_filename("cam0", 7, 123) == "cam0_000007_123.jpg"


def test_frame_filenames_sort_by_index():
    names = [frame_filename("cam1", i, 0) for i in (2, 10, 1)]
    assert sorted(names) == [frame_filename("cam1", i, 0) for i in (1, 2, 10)]


# ── camera_name_from_topic ──────────────────────────────────────────────────
@pytest.mark.parametrize("topic,expected", [
    ("/cam0/image_raw", "cam0"),
    ("/cam5/image_raw", "cam5"),
    ("cam3/image_raw", "cam3"),
    ("/ns/cam2/image_raw", "cam2"),
])
def test_camera_name_from_conventional_topic(topic, expected):
    assert camera_name_from_topic(topic) == expected


@pytest.mark.parametrize("topic", ["/image_raw", "image_raw", "/", ""])
def test_camera_name_never_empty(topic):
    assert camera_name_from_topic(topic) != ""
