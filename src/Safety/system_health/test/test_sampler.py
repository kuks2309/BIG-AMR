"""샘플러 검증 — record 스키마, CPU 차분 규칙, `--once` 경로, 정지 신호 처리."""
import json
import time

import pytest

from system_health import sampler, sysfs
from system_health.thresholds import Thresholds


@pytest.fixture(autouse=True)
def _isolate_stop_flag():
    """전역 정지 플래그는 프로세스 전역이라 테스트 간 누수를 막아야 한다."""
    sampler.reset_stop_flag()
    yield
    sampler.reset_stop_flag()


# ── record 스키마 ────────────────────────────────────────────────────────────


def test_first_sample_omits_cpu_percent(collect_sample):
    # 누적값 차분이라 첫 표본에서는 낼 수 없다. 0 으로 채우면 "한가함"으로 오독된다.
    record, snapshot = collect_sample(None)
    assert "cpu_total_pct" not in record
    assert snapshot is not None


def test_second_sample_reports_cpu_percent_in_range(collect_sample):
    _, first = collect_sample(None)
    record, _ = collect_sample(first)
    assert 0.0 <= record["cpu_total_pct"] <= 100.0
    assert all(0.0 <= p <= 100.0 for p in record["cpu_core_pct"])


def test_record_has_core_fields_and_is_json_serializable(collect_sample):
    record, _ = collect_sample(None)
    for key in ("iso_time", "epoch_s", "temperatures_c", "disks", "fan", "cooling_states"):
        assert key in record, key
    json.dumps(record, ensure_ascii=False)  # 예외가 없어야 한다


def test_injected_time_is_used(collect_sample):
    record, _ = collect_sample(None, now=0.0)
    assert record["epoch_s"] == 0.0
    assert record["iso_time"].startswith("19")  # epoch 0 = 1970


def test_disk_read_error_is_recorded_not_raised(collect_sample):
    record, _ = collect_sample(None, disk_paths=["/nonexistent-path-for-sampler-test"])
    assert record["disks"][0]["error"]


def test_proc_scan_adds_liveness_and_top_rss(collect_sample):
    record, _ = collect_sample(None, proc_scan=True)
    assert record["process_count"] > 0
    assert len(record["top_rss"]) <= 3
    assert isinstance(record["fan_daemon_alive"], bool)


def test_proc_scan_disabled_omits_those_fields(collect_sample):
    record, _ = collect_sample(None, proc_scan=False)
    assert "fan_daemon_alive" not in record
    assert "top_rss" not in record


def test_fan_field_always_present_even_without_rpm_node(collect_sample):
    # 본 하드웨어는 rpm 노드가 없다(ADR 2026-07-28 §Decision 5). 스키마에서 사라지면 안 된다.
    record, _ = collect_sample(None)
    assert set(record["fan"]) == {"pwm", "rpm"}


def test_fan_daemon_name_is_honoured(collect_sample):
    record, _ = collect_sample(None, proc_scan=True, fan_daemon_name="definitely-not-running-xyz")
    assert record["fan_daemon_alive"] is False


# ── 정지 신호 ────────────────────────────────────────────────────────────────


def test_signal_handler_sets_stop_flag():
    assert sampler.is_stop_requested() is False
    sampler._on_stop_signal(15, None)
    assert sampler.is_stop_requested() is True


def test_sleep_until_returns_immediately_when_stop_requested():
    sampler._on_stop_signal(15, None)
    started = time.monotonic()
    sampler._sleep_until(time.time() + 30.0)
    assert time.monotonic() - started < 1.0


def test_sleep_until_returns_at_deadline():
    started = time.monotonic()
    sampler._sleep_until(time.time() + 0.3)
    elapsed = time.monotonic() - started
    assert 0.2 <= elapsed < 2.0


# ── 임계값 파일 ──────────────────────────────────────────────────────────────


def test_threshold_overrides_are_loaded(tmp_path):
    path = tmp_path / "th.json"
    path.write_text(json.dumps({"temp_warn_c": 60.0}), encoding="utf-8")
    overrides = sampler._load_threshold_overrides(str(path))
    assert Thresholds.from_mapping(overrides).temp_warn_c == 60.0


def test_missing_threshold_file_aborts(tmp_path):
    with pytest.raises(SystemExit):
        sampler._load_threshold_overrides(str(tmp_path / "nope.json"))


def test_non_object_threshold_file_aborts(tmp_path):
    path = tmp_path / "th.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(SystemExit):
        sampler._load_threshold_overrides(str(path))


def test_no_threshold_file_means_defaults():
    assert sampler._load_threshold_overrides(None) == {}


# ── 임계값 저장(사용자 설정 고정) ────────────────────────────────────────────


def test_write_thresholds_creates_editable_file(tmp_path):
    path = tmp_path / "cfg" / "thresholds.json"
    assert sampler.main(["--write-thresholds", str(path)]) == 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["temp_warn_c"] == Thresholds().temp_warn_c
    # 어느 값이 잠정치인지 파일만 보고 알 수 있어야 한다.
    assert "temp_warn_c" in payload["_provisional"]


def test_written_file_can_be_loaded_back(tmp_path):
    path = tmp_path / "thresholds.json"
    sampler.main(["--write-thresholds", str(path)])
    loaded = Thresholds.from_mapping(sampler._load_threshold_overrides(str(path)))
    assert loaded == Thresholds()


def test_user_edit_survives_round_trip(tmp_path):
    path = tmp_path / "thresholds.json"
    sampler.main(["--write-thresholds", str(path)])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["temp_warn_c"] = 62.0  # 사용자가 손으로 고친 상황
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    loaded = Thresholds.from_mapping(sampler._load_threshold_overrides(str(path)))
    assert loaded.temp_warn_c == 62.0


def test_write_thresholds_applies_input_overrides(tmp_path):
    src = tmp_path / "in.json"
    src.write_text(json.dumps({"temp_warn_c": 55.0}), encoding="utf-8")
    dst = tmp_path / "out.json"
    sampler.main(["--thresholds", str(src), "--write-thresholds", str(dst)])
    assert json.loads(dst.read_text(encoding="utf-8"))["temp_warn_c"] == 55.0


def test_write_thresholds_does_not_start_sampling(tmp_path, capsys):
    # 저장만 하고 끝나야 한다 — 표본을 stdout 으로 흘리면 안 된다.
    sampler.main(["--write-thresholds", str(tmp_path / "t.json")])
    assert capsys.readouterr().out == ""


def test_write_thresholds_failure_aborts(tmp_path):
    blocker = tmp_path / "blocked"
    blocker.write_text("i am a file")
    with pytest.raises(SystemExit):
        sampler.main(["--write-thresholds", str(blocker / "sub" / "t.json")])


# ── 진입점 ───────────────────────────────────────────────────────────────────


def test_once_to_stdout_emits_one_json_line(capsys):
    assert sampler.main(["--once"]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1
    record = json.loads(out[0])
    assert record["level"] in {"OK", "WARN", "ERROR"}
    assert "cpu_total_pct" in record  # --once 는 기준선을 먼저 잡으므로 사용률이 나온다


def test_resident_first_sample_omits_cpu_percent(tmp_path):
    """상주 모드 첫 표본에 CPU% 가 없어야 한다 — 있으면 구간 0초의 쓰레기 값이다.

    2026-07-28 성능시험에서 이 결함이 실측됐다: 유휴 상태인데 첫 표본이 total=100%,
    코어별 [100,0,100,100,0,0,0,0] 를 보고해 오탐 ERROR 를 냈다.
    """
    out_dir = tmp_path / "health"
    # SIGTERM 대신 플래그를 직접 세워 1주기만 돌린다.
    args = sampler._parse_args(["--interval", "0.1", "--out-dir", str(out_dir)])
    sampler._on_stop_signal(15, None)   # 첫 표본을 쓴 뒤 루프가 끝나도록
    sampler.reset_stop_flag()

    import threading

    def stop_soon():
        sampler._on_stop_signal(15, None)

    threading.Timer(0.05, stop_soon).start()
    sampler.run(args)
    lines = [
        l for f in out_dir.glob("health-*.jsonl") for l in f.read_text(encoding="utf-8").splitlines()
    ]
    assert lines, "표본이 하나도 기록되지 않았다"
    first = json.loads(lines[0])
    assert "cpu_total_pct" not in first, f"첫 표본에 구간 0초 CPU% 가 실렸다: {first.get('cpu_total_pct')}"
    # 판정 전체(level)를 OK 로 못박으면 **호스트의 실제 상태**에 의존한다 — 시험 장비가 정말로
    # 메모리·스왑 압박을 받고 있으면 정상 경보가 뜨고 테스트가 깨진다(2026-07-28 실제로 깨졌다).
    # 이 테스트가 고정할 대상은 "구간 0초 CPU% 로 인한 cpu 경보가 없다" 뿐이다.
    cpu_findings = [f for f in first.get("findings", []) if f["key"] == "cpu"]
    assert not cpu_findings, f"첫 표본이 CPU 경보를 냈다 — 오탐이다: {cpu_findings}"


def test_once_still_reports_cpu_percent():
    """`--once` 는 표본이 하나뿐이라 기준선을 기다려서라도 CPU% 를 내야 한다."""
    args = sampler._parse_args(["--once"])
    assert args.once is True
    # 실제 값은 test_once_to_stdout_emits_one_json_line 이 확인한다.


def test_once_to_out_dir_writes_a_file(tmp_path):
    out_dir = tmp_path / "health"
    assert sampler.main(["--once", "--out-dir", str(out_dir)]) == 0
    files = sorted(out_dir.glob("health-*.jsonl"))
    assert len(files) == 1
    record = json.loads(files[0].read_text(encoding="utf-8").strip())
    assert record["log_write_failed"] is False


def test_once_respects_disk_argument(tmp_path, capsys):
    sampler.main(["--once", "--disk", "/", "--disk", str(tmp_path)])
    record = json.loads(capsys.readouterr().out.strip().splitlines()[0])
    assert [d["path"] for d in record["disks"]] == ["/", str(tmp_path)]


def test_findings_are_reported_on_stderr(tmp_path, capsys):
    # 임계값을 비현실적으로 낮춰 강제로 경보를 만든다.
    th = tmp_path / "th.json"
    th.write_text(json.dumps({"temp_warn_c": -100.0, "temp_error_c": -50.0}), encoding="utf-8")
    sampler.main(["--once", "--thresholds", str(th)])
    captured = capsys.readouterr()
    assert "ERROR" in captured.err
    assert json.loads(captured.out.strip().splitlines()[0])["level"] == "ERROR"


def test_stop_before_loop_yields_nonzero_exit():
    # 아무것도 기록하지 못하고 끝났다면 성공으로 보고하면 안 된다.
    sampler._on_stop_signal(15, None)
    assert sampler.main(["--once"]) == 1


def test_parse_args_defaults():
    args = sampler._parse_args([])
    assert args.interval == sampler.DEFAULT_INTERVAL_S
    assert args.out_dir is None
    assert args.disk_paths is None
    assert args.once is False


def test_sample_state_is_returned_for_next_call(collect_sample):
    _, state = collect_sample(None)
    assert isinstance(state, sampler.SampleState)
    assert isinstance(state.cpu, sysfs.CpuSnapshot)
    assert state.stamp > 0


# ── GPU · 스왑 활동량 ────────────────────────────────────────────────────────


def test_gpu_field_is_always_present(collect_sample):
    """Jetson 을 쓰는 이유가 GPU 다 — 노드가 없는 하드웨어에서도 스키마에서 사라지면 안 된다."""
    record, _ = collect_sample(None)
    assert set(record["gpu"]) == {"load_pct", "freq_hz", "max_freq_hz"}


def test_gpu_load_is_percent_not_per_mille(collect_sample):
    record, _ = collect_sample(None)
    load = record["gpu"]["load_pct"]
    if load is not None:
        assert 0.0 <= load <= 100.0, f"천분율이 그대로 실렸다: {load}"


def test_swap_rate_absent_on_first_sample(collect_sample):
    record, _ = collect_sample(None)
    assert "swap_rate_pages_s" not in record


def test_swap_rate_present_on_second_sample(collect_sample):
    _, first = collect_sample(None)
    record, _ = collect_sample(first)
    assert set(record["swap_rate_pages_s"]) == {"in", "out"}
    assert record["swap_rate_pages_s"]["in"] >= 0
    assert record["swap_rate_pages_s"]["out"] >= 0


# ── CLI 인자 범위 검증 ───────────────────────────────────────────────────────


@pytest.mark.parametrize("argv", [
    ["--interval", "0"],
    ["--interval", "-1"],
    ["--max-total-mb", "0"],
    ["--max-age-days", "0"],
    ["--top-rss", "-1"],
    ["--proc-scan-every", "-1"],
])
def test_out_of_range_args_are_rejected(argv):
    """0·음수 주기는 루프를 최대 속도로 돌려 감시기가 감시 대상의 부하가 된다."""
    with pytest.raises(SystemExit) as exc:
        sampler._parse_args(argv)
    assert exc.value.code == 2  # argparse 표준 사용법 오류


def test_valid_args_pass():
    args = sampler._parse_args(["--interval", "0.5", "--top-rss", "0"])
    assert args.interval == pytest.approx(0.5)
    assert args.top_rss == 0


# ── 설정 오류는 기동 시점에 끝낸다 ───────────────────────────────────────────


@pytest.mark.parametrize("payload", [
    {"temp_warn_c": "hot"},                          # 타입 오류
    {"temp_warn_c": 90.0, "temp_error_c": 85.0},     # 순서 오류
    {"temp_warm_c": 60.0},                           # 오타(미지 키)
])
def test_bad_threshold_file_exits_at_startup(tmp_path, payload):
    """통과시키면 첫 판정에서 죽고, Restart=always 와 만나 재시작 루프가 된다.

    그 상태는 '떠 있는데 기록이 0' 이라 감시기를 넣은 의미가 사라진다.
    """
    path = tmp_path / "thresholds.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        sampler.main(["--thresholds", str(path), "--once"])
    assert "임계값 설정을 받아들일 수 없다" in str(exc.value)
