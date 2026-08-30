# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""Pure, I/O-free statistics helpers for the USB camera benchmark.

Kept separate from device capture so they can be unit tested without hardware
(coding SOP §4 TDD-lite).
"""

import numpy as np


def fps_from(frame_count, elapsed_sec):
    """Frames per second over an interval; 0.0 when elapsed is non-positive."""
    if elapsed_sec <= 0.0:
        return 0.0
    return float(frame_count) / elapsed_sec


def interval_stats_ms(frame_timestamps):
    """Summarise inter-frame intervals from a list of capture timestamps (sec).

    :param frame_timestamps: monotonic capture times, one per grabbed frame.
    :returns: dict with mean/p50/p95/max/std/jitter interval in milliseconds.
        All zero when fewer than two timestamps are given.
    """
    keys = ("mean_ms", "p50_ms", "p95_ms", "max_ms", "std_ms", "jitter_ms")
    if frame_timestamps is None or len(frame_timestamps) < 2:
        return {k: 0.0 for k in keys}
    intervals = np.diff(np.asarray(frame_timestamps, dtype=np.float64)) * 1000.0
    return {
        "mean_ms": float(np.mean(intervals)),
        "p50_ms": float(np.percentile(intervals, 50)),
        "p95_ms": float(np.percentile(intervals, 95)),
        "max_ms": float(np.max(intervals)),
        "std_ms": float(np.std(intervals)),
        # Jitter = mean absolute deviation from the mean interval.
        "jitter_ms": float(np.mean(np.abs(intervals - np.mean(intervals)))),
    }


def fps_deficit_pct(actual_fps, target_fps):
    """Percent shortfall of actual vs target FPS (0 if meeting/exceeding target)."""
    if target_fps <= 0.0:
        return 0.0
    deficit = (target_fps - actual_fps) / target_fps * 100.0
    return max(0.0, deficit)
