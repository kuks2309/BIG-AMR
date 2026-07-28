# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""soak_stats 순수 함수 테스트 (하드웨어 불필요)."""

from soak_stats import (
    parse_capture_line,
    parse_display_line,
    rss_growth_mb,
    summarize_capture,
    summarize_display,
)

CAPTURE_LINE = (
    "[usb_cam_publisher_node-1] [INFO] [1785144791.235607004] "
    "[usb_cam_publisher_cam0]: [cam0] capture FPS: 29.70 (grab_failures=0)"
)
DISPLAY_LINE = (
    "[vision_guard-1] [INFO] [1785144791.235607004] [vision_guard]: display "
    "/cam0/image_raw=23.4fps/702f /cam1/image_raw=22.0fps/660f"
)


def test_parse_capture_line():
    parsed = parse_capture_line(CAPTURE_LINE)
    assert parsed == {
        "stamp": 1785144791.235607004,
        "camera": "cam0",
        "fps": 29.70,
        "grab_failures": 0,
    }


def test_parse_capture_line_ignores_other_lines():
    assert parse_capture_line("[INFO] subscribed to '/cam0/image_raw' (raw)") is None


def test_parse_capture_line_reads_grab_failures():
    line = CAPTURE_LINE.replace("grab_failures=0", "grab_failures=7")
    assert parse_capture_line(line)["grab_failures"] == 7


def test_parse_display_line():
    # 숫자는 구간 증분(frames_delta)이지 누적이 아니다.
    parsed = parse_display_line(DISPLAY_LINE)
    assert parsed["cameras"]["cam0"] == {"fps": 23.4, "frames_delta": 702}
    assert parsed["cameras"]["cam1"] == {"fps": 22.0, "frames_delta": 660}


def test_parse_display_line_skips_hidden_entries():
    line = DISPLAY_LINE + " /cam5/image_raw=hidden"
    parsed = parse_display_line(line)
    assert set(parsed["cameras"]) == {"cam0", "cam1"}


def test_parse_display_line_ignores_other_lines():
    assert parse_display_line(CAPTURE_LINE) is None


def test_summarize_capture_counts_degradation():
    samples = [
        {"stamp": 1.0, "camera": "cam0", "fps": 29.7, "grab_failures": 0},
        {"stamp": 2.0, "camera": "cam0", "fps": 18.0, "grab_failures": 0},
        {"stamp": 3.0, "camera": "cam0", "fps": 29.7, "grab_failures": 3},
    ]
    summary = summarize_capture(samples)["cam0"]
    assert summary["samples"] == 3
    assert summary["min_fps"] == 18.0
    assert summary["degraded_samples"] == 1
    assert summary["grab_failures"] == 3


def test_summarize_capture_empty():
    assert summarize_capture([]) == {}


def test_summarize_display_counts_stalls():
    samples = [
        {"stamp": 1.0, "cameras": {"cam0": {"fps": 24.0, "frames_delta": 1440}}},
        # 이 구간 렌더 0장 = 정지
        {"stamp": 2.0, "cameras": {"cam0": {"fps": 0.0, "frames_delta": 0}}},
        {"stamp": 3.0, "cameras": {"cam0": {"fps": 24.0, "frames_delta": 1400}}},
    ]
    summary = summarize_display(samples)["cam0"]
    assert summary["stall_intervals"] == 1
    assert summary["total_frames"] == 2840
    assert summary["min_frames_delta"] == 0
    assert summary["min_fps"] == 0.0


def test_summarize_display_equal_deltas_are_not_stalls():
    """증분이 연속으로 같아도 정지가 아니다(누적 오해 시 오판하던 회귀 방지)."""
    samples = [
        {"stamp": 1.0, "cameras": {"cam0": {"fps": 24.0, "frames_delta": 1435}}},
        {"stamp": 2.0, "cameras": {"cam0": {"fps": 24.0, "frames_delta": 1435}}},
    ]
    assert summarize_display(samples)["cam0"]["stall_intervals"] == 0


def test_rss_growth_mb():
    assert rss_growth_mb([100.0, 120.0, 110.0]) == {
        "first_mb": 100.0,
        "last_mb": 110.0,
        "max_mb": 120.0,
        "growth_mb": 10.0,
    }


def test_rss_growth_mb_empty():
    assert rss_growth_mb([])["growth_mb"] == 0.0
