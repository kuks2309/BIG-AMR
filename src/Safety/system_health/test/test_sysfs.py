"""sysfs/procfs reader 검증.

순수 계산(CPU 차분·키 충돌 회피)은 값을 지정해 검증하고, 실제 노드를 읽는 함수는 이 장비에서
실제로 읽히는지 + **노드가 없어도 죽지 않는지**를 확인한다.
"""
import pytest

from system_health import sysfs


# ── 순수 계산 ────────────────────────────────────────────────────────────────


def test_parse_cpu_line_counts_iowait_as_idle():
    # user nice system idle iowait irq softirq steal
    times = sysfs._parse_cpu_line(["10", "0", "5", "80", "5", "0", "0", "0"])
    assert times is not None
    assert times.idle == 85  # idle 80 + iowait 5
    assert times.total == 100


def test_parse_cpu_line_rejects_short_and_nonnumeric():
    assert sysfs._parse_cpu_line(["1", "2"]) is None
    assert sysfs._parse_cpu_line(["1", "2", "3", "x", "5"]) is None


def test_usage_pct_half_busy():
    prev = sysfs.CpuTimes(idle=50, total=100)
    cur = sysfs.CpuTimes(idle=100, total=200)
    assert sysfs._usage_pct(prev, cur) == pytest.approx(50.0)


def test_usage_pct_zero_interval_is_zero_not_crash():
    same = sysfs.CpuTimes(idle=50, total=100)
    assert sysfs._usage_pct(same, same) == 0.0


def test_usage_pct_is_clamped_to_0_100():
    # 카운터가 되감기거나(재부팅) 튀어도 범위를 벗어난 값을 내지 않아야 한다.
    prev = sysfs.CpuTimes(idle=0, total=0)
    cur = sysfs.CpuTimes(idle=-100, total=100)
    assert 0.0 <= sysfs._usage_pct(prev, cur) <= 100.0


def test_cpu_usage_pct_tolerates_core_count_change():
    prev = sysfs.CpuSnapshot(
        total=sysfs.CpuTimes(50, 100),
        per_core=(sysfs.CpuTimes(50, 100), sysfs.CpuTimes(50, 100)),
    )
    cur = sysfs.CpuSnapshot(
        total=sysfs.CpuTimes(100, 200),
        per_core=(sysfs.CpuTimes(100, 200),),  # 코어 1개가 빠졌다(hotplug)
    )
    usage = sysfs.cpu_usage_pct(prev, cur)
    assert len(usage.per_core_pct) == 1
    assert usage.total_pct == pytest.approx(50.0)


def test_unique_key_avoids_collision():
    seen = {"cpu-thermal": 1.0}
    first = sysfs._unique_key("cpu-thermal", seen)
    assert first == "cpu-thermal#1"
    seen[first] = 2.0
    assert sysfs._unique_key("cpu-thermal", seen) == "cpu-thermal#2"


def test_read_helpers_return_none_for_missing_path(tmp_path):
    missing = tmp_path / "does-not-exist"
    assert sysfs._read_text(missing) is None
    assert sysfs._read_int(missing) is None


def test_read_int_returns_none_for_nonnumeric(tmp_path):
    path = tmp_path / "value"
    path.write_text("not-a-number\n")
    assert sysfs._read_int(path) is None


# ── 실제 노드 ────────────────────────────────────────────────────────────────


def test_read_temperatures_are_plausible():
    temps = sysfs.read_temperatures_c()
    assert isinstance(temps, dict)
    for zone, value in temps.items():
        assert isinstance(zone, str) and zone
        assert -50.0 < value < 150.0, f"{zone}={value}"


def test_read_cooling_states_are_non_negative():
    for name, state in sysfs.read_cooling_states().items():
        assert isinstance(name, str) and name
        assert state >= 0


def test_read_cpu_times_has_total_and_cores():
    snapshot = sysfs.read_cpu_times()
    assert snapshot is not None
    assert snapshot.total.total > 0
    assert len(snapshot.per_core) >= 1


def test_read_cpu_freqs_are_positive_when_present():
    for khz in sysfs.read_cpu_freqs_khz():
        assert khz > 0


def test_read_memory_is_self_consistent():
    memory = sysfs.read_memory()
    assert memory is not None
    assert memory.total_mb > 0
    assert 0 <= memory.available_mb <= memory.total_mb
    assert memory.used_mb == pytest.approx(memory.total_mb - memory.available_mb)
    assert memory.swap_used_mb <= memory.swap_total_mb


def test_read_disk_root_is_positive():
    info = sysfs.read_disk("/")
    assert info.total_gb > 0
    assert 0 <= info.free_gb <= info.total_gb
    assert 0 <= info.used_pct <= 100


def test_read_disk_raises_on_missing_path():
    # 다른 reader 와 달리 예외를 전파한다 — 경로는 사용자가 지정하므로 오타를 숨기면 안 된다.
    with pytest.raises(OSError):
        sysfs.read_disk("/nonexistent-path-for-system-health-test")


def test_read_fan_returns_info_even_without_nodes():
    fan = sysfs.read_fan()
    assert isinstance(fan, sysfs.FanInfo)
    assert fan.pwm is None or fan.pwm >= 0


def test_scan_processes_finds_self():
    scan = sysfs.scan_processes(top_n=3)
    assert scan.count > 0
    assert len(scan.top_rss) <= 3
    assert all(p.rss_mb >= 0 for p in scan.top_rss)
    # RSS 내림차순 정렬 보장
    rss_values = [p.rss_mb for p in scan.top_rss]
    assert rss_values == sorted(rss_values, reverse=True)


def test_scan_processes_top_n_zero_is_empty():
    assert sysfs.scan_processes(top_n=0).top_rss == ()


def test_load_average_and_uptime():
    load = sysfs.read_load_average()
    assert load is not None and len(load) == 3
    uptime = sysfs.read_uptime_s()
    assert uptime is not None and uptime > 0


# ── GPU (Jetson 필수 항목) ───────────────────────────────────────────────────


def test_read_gpu_returns_info():
    gpu = sysfs.read_gpu()
    assert isinstance(gpu, sysfs.GpuInfo)


def test_gpu_load_is_scaled_to_percent():
    """sysfs 는 천분율(0~1000)을 낸다 — ÷10 을 빼먹으면 100 을 넘는 값이 실린다.

    2026-07-28 실측 확정: 이 노드가 401~704 인 동안 tegrastats GR3D 는 22~54 % 였다.
    """
    gpu = sysfs.read_gpu()
    if gpu.load_pct is not None:
        assert 0.0 <= gpu.load_pct <= 100.0


def test_gpu_freq_does_not_exceed_max():
    gpu = sysfs.read_gpu()
    if gpu.freq_hz is not None and gpu.max_freq_hz is not None:
        assert gpu.freq_hz <= gpu.max_freq_hz


# ── 스왑 활동량 ──────────────────────────────────────────────────────────────


def test_read_swap_counters_are_monotonic():
    a = sysfs.read_swap_counters()
    assert a is not None
    b = sysfs.read_swap_counters()
    assert b.pswpin >= a.pswpin and b.pswpout >= a.pswpout


def test_swap_rate_divides_by_elapsed():
    prev = sysfs.SwapCounters(pswpin=100, pswpout=200)
    cur = sysfs.SwapCounters(pswpin=150, pswpout=400)
    rin, rout = sysfs.swap_rate_pages_s(prev, cur, 5.0)
    assert rin == pytest.approx(10.0)
    assert rout == pytest.approx(40.0)


def test_swap_rate_zero_elapsed_is_zero():
    c = sysfs.SwapCounters(pswpin=1, pswpout=1)
    assert sysfs.swap_rate_pages_s(c, c, 0.0) == (0.0, 0.0)


def test_swap_rate_never_negative_on_counter_reset():
    # 재부팅 등으로 카운터가 되감기면 음수 속도를 보고하지 않아야 한다.
    prev = sysfs.SwapCounters(pswpin=1000, pswpout=1000)
    cur = sysfs.SwapCounters(pswpin=5, pswpout=5)
    assert sysfs.swap_rate_pages_s(prev, cur, 5.0) == (0.0, 0.0)


# ── 전원 레일 (전류 모니터링) ────────────────────────────────────────────────


def test_power_rails_have_labels_only():
    """라벨 없는 채널은 레일이 아니다.

    이 드라이버는 라벨 없는 `curr4_input`·`in4~in6_input`(shunt 전압)도 노출한다.
    그것까지 실으면 화면에 존재하지 않는 레일이 뜬다(2026-07-29 실제로 rail4 가 떴다).
    """
    for rail in sysfs.read_power_rails():
        assert rail.name and not rail.name.startswith("rail")


def test_power_rails_are_plausible():
    for rail in sysfs.read_power_rails():
        assert 0 <= rail.voltage_mv < 60000, f"{rail.name} {rail.voltage_mv}mV"
        assert 0 <= rail.current_ma < 100000, f"{rail.name} {rail.current_ma}mA"


def test_power_mw_is_voltage_times_current():
    rail = sysfs.PowerRail(name="X", voltage_mv=12000, current_ma=1500)
    assert rail.power_mw == pytest.approx(18000.0)   # 12 V × 1.5 A = 18 W


def test_power_rails_returns_tuple_even_without_sensor():
    assert isinstance(sysfs.read_power_rails(), tuple)
