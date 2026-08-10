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
    채널별 라벨 유무 확인: ls /sys/class/hwmon/hwmon*/in*_label curr*_input
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


def test_cpu_usage_pct_joins_by_core_id_when_available():
    """중간 번호 코어가 빠지면 인덱스는 밀린다 — 번호로 짝지어야 같은 코어를 비교한다."""
    prev = sysfs.CpuSnapshot(
        total=sysfs.CpuTimes(50, 100),
        per_core=(sysfs.CpuTimes(90, 100), sysfs.CpuTimes(50, 100), sysfs.CpuTimes(10, 100)),
        core_ids=(0, 1, 2),
    )
    cur = sysfs.CpuSnapshot(          # 코어 1 이 offline 되어 행이 사라졌다
        total=sysfs.CpuTimes(100, 200),
        per_core=(sysfs.CpuTimes(180, 200), sysfs.CpuTimes(20, 200)),
        core_ids=(0, 2),
    )
    usage = sysfs.cpu_usage_pct(prev, cur)
    # 코어 0: idle 90→180(+90) / total 100→200(+100) ⇒ 10 % · 코어 2: idle +10 ⇒ 90 %
    assert usage.per_core_pct == pytest.approx((10.0, 90.0))


def test_cpu_usage_pct_falls_back_to_index_without_core_ids():
    """번호가 없는 스냅샷(옛 형식)은 종전대로 인덱스로 짝짓는다."""
    prev = sysfs.CpuSnapshot(total=sysfs.CpuTimes(50, 100),
                             per_core=(sysfs.CpuTimes(50, 100),))
    cur = sysfs.CpuSnapshot(total=sysfs.CpuTimes(100, 200),
                            per_core=(sysfs.CpuTimes(100, 200),))
    assert sysfs.cpu_usage_pct(prev, cur).per_core_pct == pytest.approx((50.0,))


def test_read_cpu_times_fills_core_ids():
    snapshot = sysfs.read_cpu_times()
    assert snapshot is not None
    assert len(snapshot.core_ids) == len(snapshot.per_core)
    assert list(snapshot.core_ids) == sorted(snapshot.core_ids)


# ── powercap(RAPL) 전력 ──────────────────────────────────────────────────────


def _fake_powercap(root, domains):
    """가짜 powercap 트리를 만든다. 실경로는 커널이 root 전용으로 잠가 두어 그대로 읽을 수 없다."""
    for i, (name, energy, max_range) in enumerate(domains):
        d = root / f"intel-rapl:{i}"
        d.mkdir(parents=True)
        (d / "name").write_text(name + "\n")
        (d / "energy_uj").write_text(str(energy) + "\n")
        if max_range is not None:
            (d / "max_energy_range_uj").write_text(str(max_range) + "\n")
    return root


def test_read_energy_counters_parses_domains(tmp_path):
    root = _fake_powercap(tmp_path, [("package-0", 1000, 262143328850), ("dram", 500, None)])
    counters = sysfs.read_energy_counters(root)
    assert [c.name for c in counters] == ["package-0", "dram"]
    assert counters[0].energy_uj == 1000
    assert counters[0].max_range_uj == 262143328850
    assert counters[1].max_range_uj is None


def test_read_energy_counters_empty_when_unreadable(tmp_path):
    """권한이 없거나 트리가 없으면 조용히 빈 튜플 — 감시기가 항목 하나 때문에 죽지 않는다."""
    assert sysfs.read_energy_counters(tmp_path / "없음") == ()
    assert sysfs.read_energy_counters(_fake_powercap(tmp_path, [])) == ()


def test_power_watts_is_energy_delta_over_time():
    prev = (sysfs.EnergyCounter("package-0", 1_000_000, 262143328850),)
    cur = (sysfs.EnergyCounter("package-0", 21_000_000, 262143328850),)
    # 20 J / 5 s = 4 W
    assert sysfs.power_watts(prev, cur, 5.0)["package-0"] == pytest.approx(4.0)


def test_power_watts_corrects_wraparound():
    """카운터는 max_range 에서 되감긴다 — 보정하지 않으면 그 주기에 음수 전력이 나온다."""
    mx = 262143328850
    prev = (sysfs.EnergyCounter("package-0", mx - 1_000_000, mx),)
    cur = (sysfs.EnergyCounter("package-0", 19_000_000, mx),)   # 되감김 직후
    # (mx - (mx-1e6) + 19e6) = 20 J → 5초에 4 W
    assert sysfs.power_watts(prev, cur, 5.0)["package-0"] == pytest.approx(4.0)


def test_power_watts_drops_domain_when_wrap_uncorrectable():
    """max_range 를 모르면 음수를 보고하는 대신 그 주기를 버린다."""
    prev = (sysfs.EnergyCounter("core", 100, None),)
    cur = (sysfs.EnergyCounter("core", 50, None),)
    assert sysfs.power_watts(prev, cur, 5.0) == {}


def test_power_watts_ignores_unmatched_domain_and_bad_elapsed():
    prev = (sysfs.EnergyCounter("core", 0, 10),)
    cur = (sysfs.EnergyCounter("dram", 100, 10),)
    assert sysfs.power_watts(prev, cur, 5.0) == {}          # 짝이 없는 도메인
    assert sysfs.power_watts(prev, prev, 0.0) == {}          # 경과 0
