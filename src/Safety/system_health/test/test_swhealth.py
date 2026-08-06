"""Phase 3a — SW(Software) 이상유무 워치독 검증.

핵심 불변식은 **"선언하지 않으면 판정하지 않는다"** 이다. 감시기가 무엇이 정상인지 스스로
정하면, 실재하지 않는 것을 감시하거나 정상 운영을 이상으로 보고하게 된다
(ADR 2026-08-01 §Decision 2 — 조사 시점에 이 장비의 ROS 노드는 0개, CAN 인터페이스도 0개였다).

두 번째 불변식은 **"누계가 아니라 증가율로 판정한다"** — Phase 1 에서 스왑 사용량 기준이
표본 97 % 를 WARN 으로 만든 실패를 CAN 에러에서 반복하지 않기 위해서다.
"""
from __future__ import annotations

import pytest

from system_health import sampler, sysfs
from system_health.thresholds import Level, Thresholds, evaluate


# ── 선언이 없으면 판정하지 않는다 ────────────────────────────────────────────


def test_no_declaration_means_no_process_watch(collect_sample):
    record, _ = collect_sample(proc_scan=True, expected_processes=())
    assert "process_watch" not in record


def test_default_thresholds_declare_nothing():
    assert Thresholds().expected_processes == ()


def test_empty_watch_yields_no_findings():
    assert evaluate({"process_watch": {"expected": [], "missing": [], "restarted": []}},
                    Thresholds()) == ()


# ── 프로세스 생존 ────────────────────────────────────────────────────────────


def test_declared_and_present_process_is_silent(collect_sample):
    # 자기 자신(python3)은 반드시 살아 있다.
    record, _ = collect_sample(proc_scan=True, expected_processes=["python3"])
    assert record["process_watch"]["missing"] == []
    assert evaluate(record, Thresholds()) == () or all(
        not f.key.startswith("process_missing") for f in evaluate(record, Thresholds()))


def test_missing_process_is_error(collect_sample):
    record, _ = collect_sample(proc_scan=True, expected_processes=["절대없는프로세스이름"])
    assert record["process_watch"]["missing"] == ["절대없는프로세스이름"]
    findings = evaluate(record, Thresholds())
    miss = [f for f in findings if f.key.startswith("process_missing")]
    assert len(miss) == 1 and miss[0].level is Level.ERROR


def test_watch_records_pids_for_audit(collect_sample):
    record, _ = collect_sample(proc_scan=True, expected_processes=["python3"])
    assert record["process_watch"]["pids"]["python3"], "PID 목록이 비었다 — 재시작 판정 불가"


# ── 재시작(crash-loop) 감지 ──────────────────────────────────────────────────


def test_pid_change_is_reported_as_restart(collect_sample):
    """생존 검사만으로는 죽었다 살아난 것을 못 잡는다 — PID 변화가 유일한 단서다."""
    prev = sampler.SampleState(stamp=0.0, cpu=None, swap=None, pids={"python3": (999999,)})
    record, _ = collect_sample(prev, proc_scan=True, expected_processes=["python3"], now=5.0)
    assert record["process_watch"]["restarted"] == ["python3"]
    findings = evaluate(record, Thresholds())
    r = [f for f in findings if f.key.startswith("process_restarted")]
    assert len(r) == 1 and r[0].level is Level.WARN


def test_same_pid_is_not_a_restart(collect_sample):
    first, state = collect_sample(proc_scan=True, expected_processes=["python3"])
    second, _ = collect_sample(state, proc_scan=True, expected_processes=["python3"])
    assert second["process_watch"]["restarted"] == []


def test_first_sample_has_no_restart_claim(collect_sample):
    # 이전 PID 를 모르는 상태에서 재시작을 주장하면 기동 직후마다 오탐이 된다.
    record, _ = collect_sample(proc_scan=True, expected_processes=["python3"])
    assert record["process_watch"]["restarted"] == []


# ── CAN ──────────────────────────────────────────────────────────────────────


def test_can_absent_means_no_field(collect_sample):
    """CAN 을 쓰지 않는 운영도 정상 — 부재를 이상으로 보고하지 않는다."""
    record, _ = collect_sample(proc_scan=True)
    if not sysfs.read_can_interfaces():
        assert "can" not in record


def test_can_down_is_error():
    rec = {"can": [{"name": "can0", "up": False, "errors_total": 0}]}
    findings = evaluate(rec, Thresholds())
    assert [f.key for f in findings] == ["can_down:can0"]
    assert findings[0].level is Level.ERROR


def test_can_errors_not_judged_without_thresholds():
    rec = {"can": [{"name": "can0", "up": True, "error_rate_s": 9999.0, "errors_total": 5}]}
    assert Thresholds().can_error_rate_warn_s is None
    assert evaluate(rec, Thresholds()) == ()


def test_can_error_rate_judged_when_enabled():
    th = Thresholds.from_mapping({"can_error_rate_warn_s": 1.0,
                                  "can_error_rate_error_s": 10.0})
    rec = {"can": [{"name": "can0", "up": True, "error_rate_s": 12.0, "errors_total": 500}]}
    findings = evaluate(rec, th)
    assert [f.key for f in findings] == ["can_errors:can0"]
    assert findings[0].level is Level.ERROR


def test_can_judged_by_rate_not_cumulative():
    """누계가 커도 증가가 멈췄으면 경보하지 않는다 — 스왑에서 겪은 경보 피로의 재발 방지."""
    th = Thresholds.from_mapping({"can_error_rate_warn_s": 1.0,
                                  "can_error_rate_error_s": 10.0})
    rec = {"can": [{"name": "can0", "up": True, "error_rate_s": 0.0, "errors_total": 1_000_000}]}
    assert evaluate(rec, th) == ()


def test_can_error_rate_arithmetic():
    a = sysfs.CanInterface("can0", True, 0, 0, 10, 0, 0, 0)      # total_errors=10
    b = sysfs.CanInterface("can0", True, 0, 0, 40, 0, 10, 0)     # total_errors=50
    assert sysfs.can_error_rate(a, b, 4.0) == pytest.approx(10.0)


def test_can_error_rate_never_negative_on_counter_reset():
    a = sysfs.CanInterface("can0", True, 0, 0, 1000, 0, 0, 0)
    b = sysfs.CanInterface("can0", True, 0, 0, 5, 0, 0, 0)
    assert sysfs.can_error_rate(a, b, 5.0) == 0.0


def test_can_error_rate_zero_elapsed():
    a = sysfs.CanInterface("can0", True, 0, 0, 1, 0, 0, 0)
    assert sysfs.can_error_rate(a, a, 0.0) == 0.0


def test_can_total_errors_sums_all_four_counters():
    c = sysfs.CanInterface("can0", True, 0, 0, 1, 2, 4, 8)
    assert c.total_errors == 15


def test_read_can_interfaces_returns_tuple():
    assert isinstance(sysfs.read_can_interfaces(), tuple)


# ── DDS 세그먼트 ─────────────────────────────────────────────────────────────


def test_dds_segments_recorded_but_not_judged(collect_sample):
    """정상 개수를 모르므로 기록만 한다 — 지어낸 임계로 경보하지 않는다."""
    record, _ = collect_sample(proc_scan=True)
    assert isinstance(record["dds_segments"], int)
    assert record["dds_segments"] >= 0
    assert evaluate({"dds_segments": 0}, Thresholds()) == ()


def test_count_dds_segments_is_non_negative():
    assert sysfs.count_dds_segments() >= 0


# ── 설정 왕복 ────────────────────────────────────────────────────────────────


def test_expected_processes_round_trips_from_json_list():
    """설정 파일은 배열을 list 로 준다 — tuple 필드와 타입이 어긋나면 왕복이 깨진다."""
    th = Thresholds.from_mapping({"expected_processes": ["a", "b"]})
    assert th.expected_processes == ("a", "b")
    assert Thresholds.from_mapping(th.to_mapping()) == th


def test_process_scan_exposes_pids_by_name():
    scan = sysfs.scan_processes(top_n=1)
    assert scan.pids_by_name
    # names 와 pids_by_name 의 키가 같아야 한다(둘이 어긋나면 감시 대상이 조용히 빠진다).
    assert set(scan.names) == set(scan.pids_by_name)
