# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""내구(soak) 테스트 로그 파싱·요약 — 순수 함수 (하드웨어·I/O 무관).

`soak_monitor.py` 가 수집하는 원시 로그를 해석하는 부분만 분리해 하드웨어 없이
단위 테스트한다(coding SOP §4 TDD-lite, `bench_stats.py` 와 같은 구성).
"""

import re

# usb_cam_publisher 캡처 로그:
# [usb_cam_publisher_node-1] [INFO] [1785144791.235] [usb_cam_publisher_cam0]:
#     [cam0] capture FPS: 29.70 (grab_failures=0)
_CAPTURE_RE = re.compile(
    r"\[(?P<stamp>\d+\.\d+)\].*?\[(?P<cam>cam\d+)\] capture FPS: "
    r"(?P<fps>[\d.]+) \(grab_failures=(?P<failures>\d+)\)"
)

# vision_guard 표시 로그:
# [INFO] [1785144791.235] [vision_guard]: display /cam0/image_raw=23.4fps/702f ...
# 뒤의 숫자는 **보고 구간(기본 60초) 동안 렌더된 프레임 수(증분)** 이며 누적이 아니다
# (main_window._report_display_stats 가 delta 를 찍는다). 누적으로 오해하면 정지 판정이
# 뒤집힌다 — 2026-07-28 오판 사례.
_DISPLAY_RE = re.compile(r"\[(?P<stamp>\d+\.\d+)\].*?\bdisplay (?P<body>/cam.+)$")
_DISPLAY_ITEM_RE = re.compile(
    r"/(?P<cam>cam\d+)/image_raw=(?P<fps>[\d.]+)fps/(?P<frames>\d+)f"
)


def parse_capture_line(line):
    """퍼블리셔 캡처 FPS 로그 한 줄 → dict, 해당 없으면 None."""
    match = _CAPTURE_RE.search(line)
    if not match:
        return None
    return {
        "stamp": float(match.group("stamp")),
        "camera": match.group("cam"),
        "fps": float(match.group("fps")),
        "grab_failures": int(match.group("failures")),
    }


def parse_display_line(line):
    """뷰어 표시 FPS 로그 한 줄 → dict, 해당 없으면 None.

    ``cameras`` 는 {카메라: {"fps": float, "frames_delta": int}} 이며,
    ``frames_delta`` 는 **직전 보고 이후 렌더된 프레임 수**(누적 아님). 숨겨진(hidden)
    카메라 항목은 값이 없으므로 제외한다.
    """
    match = _DISPLAY_RE.search(line)
    if not match:
        return None
    cameras = {
        item.group("cam"): {
            "fps": float(item.group("fps")),
            "frames_delta": int(item.group("frames")),
        }
        for item in _DISPLAY_ITEM_RE.finditer(match.group("body"))
    }
    if not cameras:
        return None
    return {"stamp": float(match.group("stamp")), "cameras": cameras}


def summarize_capture(samples):
    """캡처 샘플 목록 → 카메라별 요약 {min/mean/max fps, 저하 횟수, grab_failures}.

    :param samples: ``parse_capture_line`` 결과 리스트.
    :returns: {카메라: dict}. 입력이 비면 빈 dict.
    """
    by_camera = {}
    for sample in samples:
        by_camera.setdefault(sample["camera"], []).append(sample)

    summary = {}
    for camera, rows in by_camera.items():
        values = [r["fps"] for r in rows]
        summary[camera] = {
            "samples": len(values),
            "min_fps": min(values),
            "mean_fps": sum(values) / len(values),
            "max_fps": max(values),
            # 25fps 미만 = 30fps 목표 대비 유의미한 저하로 간주(운용 판정선).
            "degraded_samples": sum(1 for v in values if v < 25.0),
            "grab_failures": max(r["grab_failures"] for r in rows),
        }
    return summary


def summarize_display(samples):
    """표시 샘플 목록 → 카메라별 요약 {min/mean fps, 정지 구간 수, 총 렌더 프레임}.

    정지(stall) = 해당 보고 구간의 ``frames_delta`` 가 0 인 경우(그 60초 동안 한 장도
    그리지 못함). 값이 증분이므로 연속 값 비교가 아니라 0 여부로 판정한다 — 증분을
    누적으로 오해해 "연속 두 값이 같으면 정지"로 세면 오판한다(2026-07-28 사례).
    """
    by_camera = {}
    for sample in samples:
        for camera, values in sample["cameras"].items():
            by_camera.setdefault(camera, []).append(values)

    summary = {}
    for camera, rows in by_camera.items():
        fps_values = [r["fps"] for r in rows]
        deltas = [r["frames_delta"] for r in rows]
        summary[camera] = {
            "samples": len(rows),
            "min_fps": min(fps_values),
            "mean_fps": sum(fps_values) / len(fps_values),
            "min_frames_delta": min(deltas),
            "stall_intervals": sum(1 for d in deltas if d == 0),
            "total_frames": sum(deltas),
        }
    return summary


def rss_growth_mb(rss_samples):
    """RSS(MB) 시계열 → {first, last, max, growth}. 누수 판정을 위한 최소 통계."""
    if not rss_samples:
        return {"first_mb": 0.0, "last_mb": 0.0, "max_mb": 0.0, "growth_mb": 0.0}
    return {
        "first_mb": rss_samples[0],
        "last_mb": rss_samples[-1],
        "max_mb": max(rss_samples),
        "growth_mb": rss_samples[-1] - rss_samples[0],
    }
