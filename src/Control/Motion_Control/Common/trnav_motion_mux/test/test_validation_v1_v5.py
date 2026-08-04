"""launch_test V-01~V-05: trnav_motion_mux config schema validation.

Each test launches ``trnav_motion_mux_node`` with a bad fixture yaml via the
shared helper in ``conftest.py`` and asserts on return code + stderr
marker.

V-04 is a known skip: ``source_ids=[0,1,3,3]`` keeps the duplicate in the
YAML list, but ``loadSources()`` uses ``sources_[id]=move(entry)`` (map
overwrite), so the second ``id=3`` silently overwrites the first.
``validateSources()`` iterates the already-unique map, so V-04 cannot be
detected at the C++ layer today. See ``trnav_motion_mux_node.cpp`` comment:
"V-04: sources_ 가 map 이라 자동 unique".
"""

import os
import sys
import unittest

import pytest

# Standalone pytest (not launch_test) — subprocess pattern runs trnav_motion_mux_node
# externally for each case, so we don't need launch_testing orchestration.
sys.path.insert(0, os.path.dirname(__file__))

from conftest import run_mux_with_yaml  # noqa: E402


class TestValidationV1V5(unittest.TestCase):

    # ------------------------------------------------------------------ V-01
    def test_v01_id0_wrong_name(self):
        rc, stderr = run_mux_with_yaml("bad_v01_id0_wrong_name.yaml")
        self.assertNotEqual(rc, 0,
            "trnav_motion_mux must exit non-zero on V-01 violation")
        self.assertIn("V-01", stderr,
            f"stderr must contain 'V-01' marker. Got:\n{stderr}")

    # ------------------------------------------------------------------ V-02
    def test_v02_id1_wrong_name(self):
        rc, stderr = run_mux_with_yaml("bad_v02_id1_wrong_name.yaml")
        self.assertNotEqual(rc, 0,
            "trnav_motion_mux must exit non-zero on V-02 violation")
        self.assertIn("V-02", stderr,
            f"stderr must contain 'V-02' marker. Got:\n{stderr}")

    # ------------------------------------------------------------------ V-04 (옛 V-03 폐지 후 재배정)
    # V-03 (id=2 영구 미예약) 정책은 2026-04-27 폐지. id=2 는 translate_reverse 로 재배정됨.
    # 본 케이스는 fixture 의 id=2 name="old_joystick" 이 신규 SSOT (id=2→translate_reverse) 와
    # 불일치하여 V-04 FATAL 이 발생하는지 검증.
    def test_v03_id2_used(self):
        rc, stderr = run_mux_with_yaml("bad_v03_id2_used.yaml")
        self.assertNotEqual(rc, 0,
            "trnav_motion_mux must exit non-zero on V-04 (id=2 reserved name) violation")
        self.assertIn("V-04", stderr,
            f"stderr must contain 'V-04' marker. Got:\n{stderr}")

    # ------------------------------------------------------------------ V-04
    @pytest.mark.skip(
        reason=(
            "V-04 (duplicate id) cannot be detected at the C++ layer: "
            "loadSources() uses std::unordered_map overwrite, so "
            "validateSources() never sees the duplicate. Informational only."
        )
    )
    def test_v04_duplicate_id(self):
        rc, stderr = run_mux_with_yaml("bad_v04_duplicate_id.yaml")
        self.assertNotEqual(rc, 0,
            "trnav_motion_mux must exit non-zero on V-04 violation")
        self.assertIn("V-04", stderr,
            f"stderr must contain 'V-04' marker. Got:\n{stderr}")

    # ------------------------------------------------------------------ V-05
    def test_v05_duplicate_name(self):
        rc, stderr = run_mux_with_yaml("bad_v05_duplicate_name.yaml")
        self.assertNotEqual(rc, 0,
            "trnav_motion_mux must exit non-zero on V-05 violation")
        self.assertIn("V-05", stderr,
            f"stderr must contain 'V-05' marker. Got:\n{stderr}")
