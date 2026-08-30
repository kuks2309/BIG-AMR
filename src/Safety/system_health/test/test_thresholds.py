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


def test_swap_activity_is_flagged_not_usage():
    """스왑 판정은 **활동량** 기준이다.

    2026-07-28 시험 운전에서 사용량 기준이 표본 97 % 를 WARN 으로 만들었다 — 리눅스는 압박이
    끝나도 스왑 페이지를 되돌리지 않으므로 사용량은 몇 시간씩 높게 남는다. 지금 스왑을 쓰고
    있는지가 위험 신호다.
    """
    idle = {"memory": {"available_mb": 8000.0, "swap_used_mb": 4096.0},
            "swap_rate_pages_s": {"in": 0.0, "out": 0.0}}
    assert evaluate(idle, Thresholds()) == (), "누적 사용량만으로 경보를 냈다 — 경보 피로의 원인"

    active = {"memory": {"available_mb": 8000.0, "swap_used_mb": 10.0},
              "swap_rate_pages_s": {"in": 40.0, "out": 40.0}}
    findings = evaluate(active, Thresholds())
    assert [f.key for f in findings] == ["swap_rate"]
    assert findings[0].level is Level.WARN
    assert findings[0].value == pytest.approx(80.0)   # in + out 합산


def test_swap_rate_error_level():
    rec = {"swap_rate_pages_s": {"in": 300.0, "out": 300.0}}
    assert evaluate(rec, Thresholds())[0].level is Level.ERROR


def test_missing_swap_rate_is_not_judged():
    # 첫 표본에는 차분이 없다 — 판정하지 않아야 한다.
    assert evaluate({"memory": {"available_mb": 8000.0, "swap_used_mb": 4096.0}},
                    Thresholds()) == ()


# ── GPU ──────────────────────────────────────────────────────────────────────


def test_gpu_is_not_judged_by_default():
    """높은 GPU 사용률은 이 장비의 목적이지 결함이 아니다 — 기본 임계는 비활성이다."""
    assert Thresholds().gpu_warn_pct is None
    assert evaluate({"gpu": {"load_pct": 100.0}}, Thresholds()) == ()


def test_gpu_is_judged_when_thresholds_given():
    th = Thresholds.from_mapping({"gpu_warn_pct": 80.0, "gpu_error_pct": 95.0})
    findings = evaluate({"gpu": {"load_pct": 97.0}}, th)
    assert [f.key for f in findings] == ["gpu"]
    assert findings[0].level is Level.ERROR


def test_gpu_missing_node_is_not_judged():
    th = Thresholds.from_mapping({"gpu_warn_pct": 80.0, "gpu_error_pct": 95.0})
    assert evaluate({"gpu": {"load_pct": None}}, th) == ()


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


def test_retired_key_error_names_the_replacement():
    """상주 서비스가 업그레이드 후 이유 없이 죽어 보이면 안 된다 — 무엇으로 바뀌었는지 알린다."""
    with pytest.raises(KeyError) as e:
        Thresholds.from_mapping({"swap_used_warn_mb": 256.0})
    msg = str(e.value)
    assert "폐기된" in msg
    assert "swap_rate_warn_pages_s" in msg


def test_retired_keys_are_not_silently_migrated():
    # 사용량(MB)과 활동량(pages/s)은 단위도 뜻도 다르다 — 옮겨 담으면 잘못된 임계가 된다.
    with pytest.raises(KeyError):
        Thresholds.from_mapping({"swap_used_error_mb": 2048.0})


def test_unknown_key_error_lists_valid_names():
    with pytest.raises(KeyError) as e:
        Thresholds.from_mapping({"temp_warm_c": 60.0})
    assert "사용 가능" in str(e.value)


def test_retired_keys_are_not_current_fields():
    from dataclasses import fields as _fields
    from system_health.thresholds import RETIRED_KEYS
    current = {f.name for f in _fields(Thresholds)}
    assert not (set(RETIRED_KEYS) & current), "폐기 목록에 현행 필드가 섞여 있다"


# ── 입력 전류 ────────────────────────────────────────────────────────────────


def test_input_current_not_judged_by_default():
    """부하가 오르면 전류도 오르는 게 정상 — 기준선 없이 임계를 지어내지 않는다."""
    assert Thresholds().input_current_warn_ma is None
    rec = {"power": {"VDD_IN": {"mv": 11600, "ma": 9999, "mw": 115000}}}
    assert evaluate(rec, Thresholds()) == ()


def test_input_current_judged_when_enabled():
    th = Thresholds.from_mapping({"input_current_warn_ma": 2000.0,
                                  "input_current_error_ma": 3000.0})
    rec = {"power": {"VDD_IN": {"mv": 11600, "ma": 3200, "mw": 37120}}}
    findings = evaluate(rec, th)
    assert [f.key for f in findings] == ["input_current"]
    assert findings[0].level is Level.ERROR


def test_input_current_uses_configured_rail():
    th = Thresholds.from_mapping({"input_rail_name": "VDD_SOC",
                                  "input_current_warn_ma": 100.0,
                                  "input_current_error_ma": 200.0})
    rec = {"power": {"VDD_IN": {"ma": 5000}, "VDD_SOC": {"mv": 11600, "ma": 150, "mw": 1740}}}
    findings = evaluate(rec, th)
    assert findings[0].value == pytest.approx(150.0)
    assert findings[0].level is Level.WARN


def test_missing_rail_is_not_judged():
    th = Thresholds.from_mapping({"input_current_warn_ma": 100.0,
                                  "input_current_error_ma": 200.0})
    assert evaluate({"power": {}}, th) == ()


# ── 설정 값 검증 (로드 시점 거부) ────────────────────────────────────────────


@pytest.mark.parametrize("override, needle", [
    ({"temp_warn_c": "hot"}, "숫자"),
    ({"temp_warn_c": "75"}, "숫자"),          # JSON 에서 따옴표는 실수의 신호다
    ({"temp_warn_c": True}, "숫자"),          # bool 은 int 하위형이라 그냥 두면 1.0 이 된다
    ({"gpu_warn_pct": "80"}, "숫자"),
    ({"fan_daemon_name": 3}, "문자열"),
    ({"expected_processes": "ros2"}, "문자열 배열"),   # 문자열 하나는 배열이 아니다
    ({"expected_processes": ["ok", 7]}, "문자열"),
    ({"temp_warn_c": None}, "null"),
])
def test_from_mapping_rejects_wrong_value_type(override, needle):
    """타입 오류를 통과시키면 첫 판정에서 TypeError 로 죽는다 — 로드 시점에 거부해야 한다."""
    with pytest.raises(ValueError, match=needle):
        Thresholds.from_mapping(override)


def test_optional_threshold_accepts_null():
    """비활성(None)은 정상 입력이다 — 판정을 끄는 방법이 null 이기 때문이다."""
    assert Thresholds.from_mapping({"gpu_warn_pct": None}).gpu_warn_pct is None


@pytest.mark.parametrize("override", [
    {"temp_warn_c": 90.0, "temp_error_c": 85.0},              # 클수록 나쁨: warn <= error
    {"cpu_warn_pct": 99.0, "cpu_error_pct": 90.0},
    {"disk_free_warn_gb": 5.0, "disk_free_error_gb": 10.0},   # 작을수록 나쁨: warn >= error
    {"mem_available_warn_mb": 500.0, "mem_available_error_mb": 2000.0},
])
def test_from_mapping_rejects_inverted_order(override):
    """순서가 뒤집히면 WARN 대역이 사라진다 — 사용자는 그 사실을 모른 채 운영하게 된다."""
    with pytest.raises(ValueError, match="순서"):
        Thresholds.from_mapping(override)


def test_inverted_order_is_rejected_on_direct_construction():
    """설정 파일 경로뿐 아니라 직접 생성도 같은 규칙을 받는다."""
    with pytest.raises(ValueError, match="순서"):
        Thresholds(temp_warn_c=90.0, temp_error_c=85.0)


def test_ints_are_accepted_and_normalised():
    """JSON 은 75 를 int 로 준다 — 거부 대상이 아니라 float 로 맞출 대상이다."""
    th = Thresholds.from_mapping({"temp_warn_c": 70})
    assert th.temp_warn_c == pytest.approx(70.0)
    assert isinstance(th.temp_warn_c, float)
