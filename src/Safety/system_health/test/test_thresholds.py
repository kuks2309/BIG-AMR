"""임계값 판정 검증 — 경계값 포함 여부와 "항목 없으면 판정 안 함" 규칙이 핵심이다."""
import pytest

from system_health.thresholds import (PROVISIONAL_KEYS, Finding, Level,
                                      Thresholds, _grade, evaluate,
                                      worst_level)


def test_grade_higher_is_worse_boundaries_are_inclusive():
    assert _grade(74.9, 75.0, 85.0, higher_is_worse=True) is Level.OK
    assert _grade(75.0, 75.0, 85.0, higher_is_worse=True) is Level.WARN
    assert _grade(85.0, 75.0, 85.0, higher_is_worse=True) is Level.ERROR


def test_grade_lower_is_worse_boundaries_are_inclusive():
    assert _grade(10.1, 10.0, 6.0, higher_is_worse=False) is Level.OK
    assert _grade(10.0, 10.0, 6.0, higher_is_worse=False) is Level.WARN
    assert _grade(6.0, 10.0, 6.0, higher_is_worse=False) is Level.ERROR


def test_empty_record_yields_no_findings():
    # 하드웨어마다 읽히는 노드가 다르다 — 항목 부재는 정상이지 이상이 아니다.
    assert evaluate({}, Thresholds()) == ()


def test_hottest_zone_drives_temperature_finding():
    record = {"temperatures_c": {"cpu-thermal": 60.0, "tj-thermal": 88.0}}
    findings = evaluate(record, Thresholds())
    assert len(findings) == 1
    assert findings[0].key == "temperature"
    assert findings[0].level is Level.ERROR
    assert findings[0].value == pytest.approx(88.0)
    assert "tj-thermal" in findings[0].message


def test_normal_temperature_yields_nothing():
    assert evaluate({"temperatures_c": {"cpu-thermal": 51.8}}, Thresholds()) == ()


def test_disk_finding_names_the_path():
    record = {"disks": [{"path": "/", "free_gb": 7.0}]}
    findings = evaluate(record, Thresholds())
    assert findings[0].key == "disk_free:/"
    assert findings[0].level is Level.WARN


def test_disk_warn_fires_before_dataset_collector_floor():
    # dataset_collector 의 하한은 5.0 GB 다. 감시기가 그보다 먼저 경고해야 순서가 맞다.
    th = Thresholds()
    assert th.disk_free_warn_gb > 5.0
    assert th.disk_free_error_gb > 5.0


def test_disk_entry_with_read_error_is_skipped_not_crash():
    assert evaluate({"disks": [{"path": "/x", "error": "boom"}]}, Thresholds()) == ()


def test_swap_usage_is_flagged():
    record = {"memory": {"available_mb": 8000.0, "swap_used_mb": 512.0}}
    findings = evaluate(record, Thresholds())
    assert [f.key for f in findings] == ["swap_used"]
    assert findings[0].level is Level.WARN


def test_dead_fan_daemon_is_error():
    findings = evaluate({"fan_daemon_alive": False}, Thresholds())
    assert findings[0].key == "fan_daemon"
    assert findings[0].level is Level.ERROR


def test_live_fan_daemon_is_silent():
    assert evaluate({"fan_daemon_alive": True}, Thresholds()) == ()


def test_log_write_failure_is_error():
    findings = evaluate({"log_write_failed": True}, Thresholds())
    assert findings[0].key == "log_write"
    assert findings[0].level is Level.ERROR


def test_findings_are_sorted_worst_first():
    record = {
        "temperatures_c": {"tj-thermal": 90.0},  # ERROR
        "memory": {"available_mb": 1500.0},  # WARN
    }
    findings = evaluate(record, Thresholds())
    assert [f.level for f in findings] == [Level.ERROR, Level.WARN]


def test_worst_level_of_empty_is_ok():
    assert worst_level(()) is Level.OK


def test_worst_level_picks_max():
    findings = (
        Finding("a", Level.WARN, 1.0, ""),
        Finding("b", Level.ERROR, 2.0, ""),
    )
    assert worst_level(findings) is Level.ERROR


def test_from_mapping_applies_override():
    th = Thresholds.from_mapping({"temp_warn_c": 60.0})
    assert th.temp_warn_c == 60.0
    assert th.temp_error_c == Thresholds().temp_error_c


def test_to_mapping_round_trips():
    original = Thresholds(temp_warn_c=61.0, disk_free_warn_gb=12.0)
    assert Thresholds.from_mapping(original.to_mapping()) == original


def test_comment_keys_are_ignored_on_load():
    # to_mapping 결과에 설명 필드를 붙여 저장하므로, 되읽을 때 깨지면 왕복이 불가능해진다.
    payload = dict(Thresholds().to_mapping())
    payload["_설명"] = "사람이 읽는 주석"
    payload["_provisional"] = ["temp_warn_c"]
    assert Thresholds.from_mapping(payload) == Thresholds()


def test_from_mapping_rejects_unknown_key():
    # 오타를 조용히 무시하면 사용자가 임계값을 바꿨다고 믿는데 실제로는 기본값인 상태가 된다.
    with pytest.raises(KeyError):
        Thresholds.from_mapping({"temp_warn": 60.0})


def test_provisional_keys_are_real_fields():
    defaults = Thresholds()
    for key in PROVISIONAL_KEYS:
        assert hasattr(defaults, key), key
