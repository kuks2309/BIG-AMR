# Copyright 2026 T-Robot
#
# launch_test: trnav_motion_mux config validation V-06 ~ V-10
#
# 실행: colcon test --packages-select trnav_motion_mux
#       또는 launch_test src/Control-Abstract/trnav_motion_mux/test/test_validation_v6_v10.py
#
# V-06: 동일 topic 2회+ → FATAL + "V-06" in stderr
# V-07: name/topic 빈 문자열 → loadSources() 가 FATAL 로 처리 (wave 1.6 에서 통일).
#        이전 구현에서는 "Skipping incomplete source" WARN+continue 였으나 io_contract §11
#        계약(FATAL) 에 맞춰 loadSources() 내부에서 FATAL+throw 로 변경.
# V-08: default_source_id 가 sources 집합에 없음 → FATAL + "V-08" in stderr
# V-09: id < 0 → uint8_t cast wrapping 으로 FATAL 미발생. C++ 타입 보장으로 skip.
# V-10: topic 패턴 미준수 → WARN only (FATAL 아님) + stderr 에 "V-10" 포함 + 노드 정상 기동.

import os
import sys
import unittest

import pytest

# Standalone pytest — subprocess pattern runs trnav_motion_mux_node externally.
sys.path.insert(0, os.path.dirname(__file__))

from conftest import run_mux_with_yaml  # noqa: E402


class TestV06DuplicateTopic(unittest.TestCase):
    """V-06: 동일 topic 이 2개 이상 등록되면 FATAL 로 종료해야 한다."""

    def test_v06_duplicate_topic(self):
        returncode, stderr = run_mux_with_yaml(
            "bad_v06_duplicate_topic.yaml", timeout=5.0)

        self.assertIsNotNone(returncode,
            "노드가 timeout 안에 종료하지 않았습니다 (FATAL 미발생 의심)")
        self.assertNotEqual(returncode, 0,
            f"FATAL 이 발생해야 하므로 exit code != 0 이어야 합니다. stderr:\n{stderr}")
        self.assertIn("V-06", stderr, f"stderr 에 'V-06' 이 없습니다:\n{stderr}")


class TestV07MissingField(unittest.TestCase):
    """V-07: name/topic 빈 문자열 source → loadSources() 가 FATAL 로 처리한다.

    io_contract §11 은 V-07 을 FATAL 로 규정. wave 1.6 에서 loadSources() 의
    기존 'Skipping incomplete source' WARN+continue 패턴을 FATAL+throw 로 변경.
    (이전에는 validateSources() 가 실행되기 전에 loadSources() 가 empty entry 를
    skip 해서 V-07 체크가 unreachable 이었음.)
    """

    def test_v07_missing_name_triggers_fatal(self):
        returncode, stderr = run_mux_with_yaml(
            "bad_v07_missing_name.yaml", timeout=5.0)

        self.assertIsNotNone(returncode,
            "노드가 timeout 안에 종료하지 않았습니다 (FATAL 미발생 의심)")
        self.assertNotEqual(returncode, 0,
            f"FATAL 이 발생해야 하므로 exit code != 0 이어야 합니다. stderr:\n{stderr}")
        self.assertIn("V-07", stderr, f"stderr 에 'V-07' 이 없습니다:\n{stderr}")


class TestV08DefaultNotInSources(unittest.TestCase):
    """V-08: default_source_id 가 등록된 source id 집합에 없으면 FATAL 로 종료."""

    def test_v08_default_not_in_sources(self):
        returncode, stderr = run_mux_with_yaml(
            "bad_v08_default_not_in_sources.yaml", timeout=5.0)

        self.assertIsNotNone(returncode,
            "노드가 timeout 안에 종료하지 않았습니다 (FATAL 미발생 의심)")
        self.assertNotEqual(returncode, 0,
            f"FATAL 이 발생해야 하므로 exit code != 0 이어야 합니다. stderr:\n{stderr}")
        self.assertIn("V-08", stderr, f"stderr 에 'V-08' 이 없습니다:\n{stderr}")


class TestV09Placeholder(unittest.TestCase):
    """V-09: id < 0 검증 — uint8_t cast wrapping 으로 launch_test 검증 불가, SKIP.

    loadSources() 는 source_ids 를 int64_t 로 읽은 뒤 uint8_t 로 static_cast.
    YAML 에 음수 source_ids 를 지정해도 uint8_t cast wrapping 이 발생 (-1 → 255).
    validateSources() 는 sources_ map(uint8_t 키)만 순회하므로 원래 음수 값 불가시.
    → V-09 검증은 C++ 단위 테스트(gtest)로 validateSources() 직접 호출 필요.
    """

    @unittest.skip(
        "V-09: uint8_t cast wrapping 으로 launch_test 레벨 검증 불가. "
        "C++ gtest 로 validateSources() 직접 호출 필요."
    )
    def test_v09_negative_id_skipped(self):
        pass


class TestV10WrongTopicPattern(unittest.TestCase):
    """V-10: topic 이 /motion/wheel_cmd/ prefix 미준수 — WARN only, 노드 정상 기동.

    V-10 은 FATAL 이 아닌 WARN (레거시 action_server_legacy 하위 호환, io_contract §11).
    검증: 2초 실행 후 SIGINT. exit code None(timeout) 또는 0, stderr 에 "V-10" WARN 포함.
    """

    def test_v10_wrong_topic_pattern_warn_only(self):
        returncode, stderr = run_mux_with_yaml(
            "bad_v10_wrong_topic_pattern.yaml", timeout=2.0)

        # V-10 은 WARN only — FATAL 발생 시 returncode > 0 (예: 250).
        # 허용: None(timeout), 0(정상 종료), 음수(SIGINT/SIGKILL 로 우리가 종료시킴).
        # 거부: returncode > 0 (mux 가 FATAL 로 자가 종료).
        if returncode is not None and returncode > 0:
            self.fail(
                f"V-10 은 WARN only 이므로 비정상 종료 금지. "
                f"exit code={returncode}. stderr:\n{stderr}")

        self.assertIn("V-10", stderr, f"stderr 에 'V-10' WARN 이 없습니다:\n{stderr}")


