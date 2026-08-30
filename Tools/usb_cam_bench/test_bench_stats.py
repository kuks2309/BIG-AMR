# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""Unit tests for the pure benchmark stats helpers (coding SOP §4/§5)."""

import pytest

from bench_stats import fps_deficit_pct, fps_from, interval_stats_ms


def test_fps_from_normal():
    assert fps_from(150, 5.0) == 30.0


def test_fps_from_zero_elapsed():
    assert fps_from(100, 0.0) == 0.0
    assert fps_from(100, -1.0) == 0.0


def test_interval_stats_uniform_30fps():
    # 31 timestamps, exactly 1/30 s apart -> intervals ~33.33 ms, ~zero jitter.
    ts = [i / 30.0 for i in range(31)]
    stats = interval_stats_ms(ts)
    assert stats["mean_ms"] == pytest.approx(1000.0 / 30.0, abs=1e-6)
    assert stats["p95_ms"] == pytest.approx(1000.0 / 30.0, abs=1e-6)
    assert stats["jitter_ms"] == pytest.approx(0.0, abs=1e-9)


def test_interval_stats_too_few_samples():
    assert interval_stats_ms([]) == {
        "mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0,
        "max_ms": 0.0, "std_ms": 0.0, "jitter_ms": 0.0,
    }
    assert interval_stats_ms([1.23])["mean_ms"] == 0.0


def test_interval_stats_captures_a_stall():
    # Three fast frames then a 200 ms stall; max must reflect the stall.
    ts = [0.0, 0.033, 0.066, 0.266]
    stats = interval_stats_ms(ts)
    assert stats["max_ms"] == pytest.approx(200.0, abs=0.1)
    assert stats["jitter_ms"] > 0.0


def test_fps_deficit():
    assert fps_deficit_pct(15.0, 30.0) == pytest.approx(50.0)
    assert fps_deficit_pct(30.0, 30.0) == 0.0
    # Exceeding the target is not a deficit.
    assert fps_deficit_pct(32.0, 30.0) == 0.0
    assert fps_deficit_pct(15.0, 0.0) == 0.0
