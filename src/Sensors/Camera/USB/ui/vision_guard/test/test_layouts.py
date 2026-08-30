# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""Unit tests for the Qt-free layout logic (coding SOP §4/§5)."""

import pytest

from vision_guard.layouts import (
    cell_capacity,
    parse_layout,
    smallest_layout_for,
)


def test_parse_preset():
    assert parse_layout("2x3") == (2, 3)
    assert parse_layout("1x1") == (1, 1)


def test_parse_raw_spec():
    assert parse_layout("4x2") == (4, 2)


def test_parse_invalid_raises():
    with pytest.raises(ValueError):
        parse_layout("banana")
    with pytest.raises(ValueError):
        parse_layout("0x3")


def test_cell_capacity():
    assert cell_capacity("2x3") == 6
    assert cell_capacity("1x1") == 1


def test_smallest_layout_for():
    assert smallest_layout_for(1) == "1x1"
    assert smallest_layout_for(3) == "1x3"
    assert smallest_layout_for(6) == "2x3"


def test_smallest_layout_zero_defaults_1x1():
    assert smallest_layout_for(0) == "1x1"


def test_smallest_layout_overflow_returns_largest():
    # More cameras than any preset holds -> largest preset (3x3 = 9).
    assert smallest_layout_for(100) == "3x3"
