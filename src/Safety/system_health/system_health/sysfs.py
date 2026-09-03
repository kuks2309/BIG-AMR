"""OS·하드웨어 자원 수치 읽기 — sysfs/procfs 직독. ROS·외부 패키지 의존 0.

**왜 sysfs 직독인가** (ADR 2026-07-28 §Decision 3·9):
  ① `tegrastats` 출력은 JetPack 버전마다 필드가 바뀌는 문자열이라 파서가 조용히 깨진다.
     sysfs 노드는 커널 ABI 라 훨씬 안정적이다. (§Decision 3)
  ② 감시기는 다른 것이 다 깨져도 떠야 하므로 의존 표면을 최소로 유지한다(`psutil` 미사용).
     (§Decision 9 — 의존성은 표준 라이브러리만)
  ③ `ros2 topic hz` 같은 서브프로세스 호출은 매번 새 DDS participant 를 만들어 전체 노드에
     discovery 트래픽을 유발한다 — 관측이 대상을 바꾸면 안 된다. (§Decision 3)

**모든 reader 는 노드 부재에 관대하다.** 하드웨어마다 있는 노드가 다르므로, 읽을 수 없는 항목은
예외를 던지는 대신 `None` 또는 빈 컬렉션을 돌려준다 — 감시기가 항목 하나 때문에 죽으면 안 된다.
단 `read_disk()` 만은 예외를 전파한다(경로를 사용자가 지정하므로 오타를 숨기면 안 된다).
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

# 커널이 온도를 milli-degree Celsius 로 노출한다.
_MILLI_C_PER_C = 1000.0
_KB_PER_MB = 1024.0
_BYTES_PER_GB = 1 << 30

_THERMAL_ZONE_ROOT = Path("/sys/devices/virtual/thermal")
_COOLING_DEVICE_ROOT = Path("/sys/class/thermal")
_CPUFREQ_ROOT = Path("/sys/devices/system/cpu")
# Tegra GPU(GR3D) 사용률. **천분율(0~1000)이다** — 2026-07-28 실측으로 확정:
# 이 노드가 401~704 를 내는 동안 `tegrastats` 의 GR3D_FREQ 는 22~54 % 였다. 값이 100 을
# 넘으므로 퍼센트가 아니고, ÷10 하면 tegrastats 와 같은 크기가 된다.
_GPU_LOAD_PATHS = (
    Path("/sys/devices/platform/gpu.0/load"),
    Path("/sys/devices/platform/17000000.gpu/load"),
)
_GPU_LOAD_PER_MILLE = 10.0
# 부하 노드는 순간값이다. 배치 추론처럼 수백 ms 주기로 0↔99% 를 오가는 버스트 부하는
# 긴 간격의 순간 표본 대부분이 유휴 순간에 떨어져 0% 로 보인다(에일리어싱). 그래서
# 1초 창에서 여러 번 읽어 평균한다 — sampler 주기는 고정 격자(기준선+n×interval)라
# 수집이 길어져도 표본 시각이 밀리지 않는다.
_GPU_LOAD_SAMPLES = 20
_GPU_LOAD_WINDOW_S = 1.0
_DEVFREQ_ROOT = Path("/sys/class/devfreq")
# 범용 PC 의 통합 GPU 주파수. Intel i915 는 `gt_cur_freq_mhz`·`gt_max_freq_mhz` 를 **MHz** 로 낸다
# (Tegra devfreq 는 Hz). 사용률(%) 노드는 주지 않으므로 그 플랫폼에서 `load_pct` 는 None 이다.
_DRM_ROOT = Path("/sys/class/drm")
_HZ_PER_MHZ = 1_000_000
# INA3221 전력 모니터. 본 장비는 3채널(VDD_IN·VDD_CPU_GPU_CV·VDD_SOC)이며 hwmon 이
# 전압을 mV, 전류를 mA 로 낸다(2026-07-28 실측: 11624 mV · 1576 mA = VDD_IN).
# 전력 노드(`power*_input`)는 이 커널에 없어 전압×전류로 계산한다.
_HWMON_ROOT = Path("/sys/class/hwmon")
_INA3221_NAME = "ina3221"
_MAX_RAIL_CHANNELS = 8
# powercap(RAPL) — x86 에서 INA3221 을 대신하는 전력 관측점. 값은 **누적 에너지(μJ)** 라
# 차분해야 W 가 된다. 커널이 기본적으로 root 전용으로 잠가 두므로 판독은 권한에 달렸다.
_POWERCAP_ROOT = Path("/sys/class/powercap")
_UJ_PER_J = 1_000_000
_NETDEV_ROOT = Path("/sys/class/net")
# `ARPHRD_CAN` — socketcan 인터페이스의 `type` 값. 이름을 `can*` 로 가정하지 않기 위해 쓴다
# (2026-08-01 이 장비 `/usr/include/linux/if_arp.h:56` 에서 확인).
_ARPHRD_CAN = 280
_SHM_ROOT = Path("/dev/shm")
# FastDDS 가 만드는 공유메모리 세그먼트 이름 조각. 다른 DDS 구현은 다른 이름을 쓴다.
_DDS_SHM_PATTERNS = ("fastrtps", "fastdds")
# 본 하드웨어(Jetson Orin NX)의 팬 hwmon 경로. 부재 시 팬 항목은 전부 None 이 된다.
_FAN_HWMON_ROOT = Path("/sys/devices/platform/pwm-fan/hwmon")
_PROC_ROOT = Path("/proc")

# `/proc/<pid>/stat` 에서 ") " 뒤를 기준으로 센 필드 인덱스(state=0).
_PROC_STAT_RSS_PAGES = 21

_PAGE_MB = os.sysconf("SC_PAGE_SIZE") / (1024 * 1024)


# ── 순수 헬퍼 ────────────────────────────────────────────────────────────────


def _read_text(path: Path) -> str | None:
    """파일 내용을 읽어 양끝 공백을 제거해 돌려준다. 읽을 수 없으면 None.

    TypeError 도 '읽을 수 없음'이다 — 전원 게이트(power-gate)된 존의 sysfs 노드는
    raw read 가 None 을 돌려줘 codecs 단계에서 TypeError 로 나타난다(CV 클러스터가
    꺼진 Orin 기체의 cv*-thermal 실측).
    """
    try:
        return path.read_text().strip()
    except (OSError, UnicodeDecodeError, TypeError):
        return None


def _read_int(path: Path) -> int | None:
    """파일을 정수로 읽는다. 없거나 정수가 아니면 None."""
    text = _read_text(path)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _unique_key(key: str, seen: dict[str, float] | dict[str, int]) -> str:
    """같은 `type` 을 가진 노드가 둘 이상일 때 키 충돌을 피한다 (`cpu-thermal#1`)."""
    if key not in seen:
        return key
    index = 1
    while f"{key}#{index}" in seen:
        index += 1
    return f"{key}#{index}"


# ── 온도 ─────────────────────────────────────────────────────────────────────


def read_temperatures_c() -> dict[str, float]:
    """모든 thermal zone 의 온도(°C). 존 `type` 이 키.

    Returns:
        {존 type: 섭씨 온도}. 하나도 못 읽으면 빈 dict.
    """
    temps: dict[str, float] = {}
    if not _THERMAL_ZONE_ROOT.is_dir():
        return temps
    for zone in sorted(_THERMAL_ZONE_ROOT.glob("thermal_zone*")):
        zone_type = _read_text(zone / "type")
        milli_c = _read_int(zone / "temp")
        if zone_type is None or milli_c is None:
            continue
        temps[_unique_key(zone_type, temps)] = milli_c / _MILLI_C_PER_C
    return temps


def read_cooling_states() -> dict[str, int]:
    """냉각장치별 현재 단계(`cur_state`). 0 이 아니면 **지금 실제로 개입 중**이라는 뜻이다.

    임계값 추정 없이 "커널이 이미 판단한 결과"를 그대로 읽는 지표라 신뢰도가 높다.

    Returns:
        {cooling device type: cur_state}. 하나도 못 읽으면 빈 dict.
    """
    states: dict[str, int] = {}
    if not _COOLING_DEVICE_ROOT.is_dir():
        return states
    for device in sorted(_COOLING_DEVICE_ROOT.glob("cooling_device*")):
        device_type = _read_text(device / "type")
        cur_state = _read_int(device / "cur_state")
        if device_type is None or cur_state is None:
            continue
        states[_unique_key(device_type, states)] = cur_state
    return states


# ── 팬 ───────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FanInfo:
    """팬 상태.

    Attributes:
        pwm: `pwm1` 값(0~255). 노드 부재 시 None.
        rpm: 실측 회전수. 값의 유무는 **플랫폼에 달렸다** — Jetson 의 `pwm-fan` hwmon 은 `rpm`
            노드를 주지 않아 None 이고(ADR 2026-07-28 §Decision 5), 범용 hwmon 을 가진 PC 는
            `fan1_input` 으로 RPM 을 준다. None 이면 `pwm` 과 온도 추세로만 간접 판단한다.
    """

    pwm: int | None
    rpm: int | None


def read_fan() -> FanInfo:
    """팬 PWM/RPM 을 읽는다. 팬을 **제어하지 않는다 — 읽기 전용**(ADR 2026-07-28 §Decision 5).

    경로를 두 갈래로 찾는다. Jetson 은 `pwm-fan` 플랫폼 hwmon 에 `pwm1` 만 두고, 범용 PC 는
    `/sys/class/hwmon` 아래에 `fan1_input`(RPM)·`pwm1` 을 둔다. 한 코드가 두 하드웨어에서 모두
    뜨도록 Tegra 경로를 먼저 보고, 없으면 범용 hwmon 을 훑는다.

    Returns:
        `FanInfo`. 어느 경로에도 노드가 없으면 두 필드 모두 None.
    """
    roots = []
    if _FAN_HWMON_ROOT.is_dir():
        roots.append((_FAN_HWMON_ROOT, "rpm"))
    if _HWMON_ROOT.is_dir():
        roots.append((_HWMON_ROOT, "fan1_input"))
    for root, rpm_node in roots:
        for hwmon in sorted(root.glob("hwmon*")):
            pwm = _read_int(hwmon / "pwm1")
            rpm = _read_int(hwmon / rpm_node)
            if pwm is not None or rpm is not None:
                return FanInfo(pwm=pwm, rpm=rpm)
    return FanInfo(pwm=None, rpm=None)


# ── CPU ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CpuTimes:
    """`/proc/stat` 한 줄에서 뽑은 누적 시간(jiffies)."""

    idle: int
    total: int


@dataclass(frozen=True)
class CpuSnapshot:
    """어느 한 시점의 CPU 누적 시간. 사용률은 두 스냅샷의 **차분**으로만 구한다.

    Attributes:
        total: `/proc/stat` 의 `cpu` 집계 행.
        per_core: `cpu<N>` 행들, 파일에 나온 순서.
        core_ids: `per_core` 와 같은 순서의 코어 번호. **차분을 인덱스가 아니라 번호로
            짝짓기 위해** 함께 담는다 — 코어가 offline 되어 행이 사라지면 인덱스는 밀리지만
            번호는 밀리지 않는다. 비어 있으면 인덱스로 짝짓는다(옛 스냅샷 하위 호환).
    """

    total: CpuTimes
    per_core: tuple[CpuTimes, ...]
    core_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class CpuUsage:
    """두 스냅샷 사이 구간의 CPU 사용률(%)."""

    total_pct: float
    per_core_pct: tuple[float, ...]


def _parse_cpu_line(fields: list[str]) -> CpuTimes | None:
    """`/proc/stat` 의 `cpu*` 한 줄(레이블 제외)을 `CpuTimes` 로.

    idle 은 `idle + iowait` 로 센다 — iowait 구간도 CPU 가 일을 하지 않은 시간이다.
    """
    try:
        values = [int(v) for v in fields]
    except ValueError:
        return None
    if len(values) < 5:
        return None
    idle = values[3] + values[4]  # idle + iowait
    # guest/guest_nice(9,10번째)는 user/nice 에 이미 포함되어 있어 이중 계산을 피해 제외한다.
    total = sum(values[:8])
    return CpuTimes(idle=idle, total=total)


def read_cpu_times() -> CpuSnapshot | None:
    """`/proc/stat` 에서 전체·코어별 누적 CPU 시간을 읽는다.

    Returns:
        `CpuSnapshot`. 읽을 수 없으면 None.
    """
    text = _read_text(_PROC_ROOT / "stat")
    if text is None:
        return None
    total: CpuTimes | None = None
    per_core: list[CpuTimes] = []
    core_ids: list[int] = []
    for line in text.splitlines():
        parts = line.split()
        if not parts or not parts[0].startswith("cpu"):
            continue
        times = _parse_cpu_line(parts[1:])
        if times is None:
            continue
        if parts[0] == "cpu":
            total = times
            continue
        suffix = parts[0][3:]
        if not suffix.isdigit():
            continue
        per_core.append(times)
        core_ids.append(int(suffix))
    if total is None:
        return None
    return CpuSnapshot(total=total, per_core=tuple(per_core), core_ids=tuple(core_ids))


def _usage_pct(prev: CpuTimes, cur: CpuTimes) -> float:
    """두 누적 시간 사이 구간의 사용률(%). 구간이 0 이하면 0.0."""
    delta_total = cur.total - prev.total
    if delta_total <= 0:
        return 0.0
    delta_idle = cur.idle - prev.idle
    return max(0.0, min(100.0, 100.0 * (delta_total - delta_idle) / delta_total))


def cpu_usage_pct(prev: CpuSnapshot, cur: CpuSnapshot) -> CpuUsage:
    """두 스냅샷 사이의 CPU 사용률.

    양쪽에 코어 번호가 있으면 **번호로 짝짓는다**. 인덱스로 짝지으면 중간 번호 코어가 빠졌을 때
    이후 인덱스가 밀려 서로 다른 물리 코어를 비교하게 된다. 번호가 없는 옛 스냅샷은 종전대로
    인덱스로 짝짓고, 코어 수가 다르면 겹치는 만큼만 본다 — 감시기가 죽는 것보다 낫다.

    Args:
        prev: 이전 스냅샷.
        cur: 현재 스냅샷.
    Returns:
        전체·코어별 사용률(%). 코어별 값은 현재 스냅샷의 코어 순서를 따른다.
    """
    total_pct = _usage_pct(prev.total, cur.total)
    if (len(prev.core_ids) == len(prev.per_core)
            and len(cur.core_ids) == len(cur.per_core) and cur.core_ids):
        before = dict(zip(prev.core_ids, prev.per_core))
        return CpuUsage(
            total_pct=total_pct,
            per_core_pct=tuple(
                _usage_pct(before[cid], times)
                for cid, times in zip(cur.core_ids, cur.per_core) if cid in before
            ),
        )
    core_count = min(len(prev.per_core), len(cur.per_core))
    return CpuUsage(
        total_pct=total_pct,
        per_core_pct=tuple(
            _usage_pct(prev.per_core[i], cur.per_core[i]) for i in range(core_count)
        ),
    )


def read_cpu_freqs_khz() -> tuple[int, ...]:
    """코어별 현재 주파수(kHz), 코어 번호 순.

    최대 주파수에 못 미치면 주파수 저감(throttle)이 **실제로 일어났다는 확증**이다.

    Returns:
        주파수 튜플. `cpufreq` 노드가 없으면 빈 튜플.
    """
    freqs: list[tuple[int, int]] = []
    if not _CPUFREQ_ROOT.is_dir():
        return ()
    for cpu_dir in _CPUFREQ_ROOT.glob("cpu[0-9]*"):
        suffix = cpu_dir.name[3:]
        if not suffix.isdigit():
            continue
        khz = _read_int(cpu_dir / "cpufreq" / "scaling_cur_freq")
        if khz is not None:
            freqs.append((int(suffix), khz))
    return tuple(khz for _, khz in sorted(freqs))


# ── 메모리 ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MemoryInfo:
    """메모리·스왑 사용량(MB).

    `used_mb` 는 `total - available` 이다 — `MemFree` 기준이 아니다. page cache 는 회수
    가능하므로 `MemFree` 로 세면 실제보다 훨씬 비관적으로 보인다.
    """

    total_mb: float
    available_mb: float
    used_mb: float
    swap_total_mb: float
    swap_used_mb: float


def read_memory() -> MemoryInfo | None:
    """`/proc/meminfo` 에서 메모리·스왑 사용량을 읽는다.

    Returns:
        `MemoryInfo`. 필수 항목을 못 읽으면 None.
    """
    text = _read_text(_PROC_ROOT / "meminfo")
    if text is None:
        return None
    values: dict[str, float] = {}
    for line in text.splitlines():
        key, _, rest = line.partition(":")
        parts = rest.split()
        if not parts:
            continue
        try:
            values[key] = int(parts[0]) / _KB_PER_MB
        except ValueError:
            continue
    try:
        total = values["MemTotal"]
        available = values["MemAvailable"]
        swap_total = values["SwapTotal"]
        swap_free = values["SwapFree"]
    except KeyError:
        return None
    return MemoryInfo(
        total_mb=total,
        available_mb=available,
        used_mb=total - available,
        swap_total_mb=swap_total,
        swap_used_mb=swap_total - swap_free,
    )


# ── 디스크 ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DiskInfo:
    """파일시스템 사용량(GB, 1 GB = 2**30 B)."""

    path: str
    total_gb: float
    free_gb: float
    used_pct: float


def read_disk(path: str) -> DiskInfo:
    """`path` 가 속한 파일시스템 사용량.

    가용 공간은 `f_bavail`(root 예약분 제외)로 센다 — `f_bfree` 는 비특권 프로세스가 실제로
    쓸 수 있는 양보다 낙관적이다. `dataset_collector` 의 `disk_free_gb()` 와 같은 기준이다.

    Args:
        path: 존재하는 파일 또는 디렉토리 경로.
    Returns:
        `DiskInfo`.
    Raises:
        OSError: 지정한 경로를 열 수 없거나 statvfs 실패 시. **경로는 사용자가 지정하므로
            오타를 숨기지 않는다** — 다른 reader 와 달리 예외를 전파한다.
    """
    st = os.statvfs(path)
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    return DiskInfo(
        path=path,
        total_gb=total / _BYTES_PER_GB,
        free_gb=free / _BYTES_PER_GB,
        used_pct=(100.0 * used / total) if total > 0 else 0.0,
    )


# ── 프로세스 ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProcessInfo:
    """단일 프로세스의 식별자와 상주 메모리."""

    pid: int
    name: str
    rss_mb: float


@dataclass(frozen=True)
class ProcessScan:
    """`/proc` 1회 순회 결과.

    Attributes:
        count: 살아 있는 프로세스 수.
        top_rss: RSS(Resident Set Size, 상주 메모리) 상위 프로세스. 누수 추적용.
        names: 실행 파일 이름 집합. 특정 데몬 생존 확인에 쓴다.
        pids_by_name: 이름 → PID 튜플. **재시작 감지용** — 이름이 계속 보여도 PID 가 바뀌었으면
            죽었다 살아난 것이다. 생존 검사만으로는 조용한 crash-loop 를 못 잡는다.

    ⚠ 이름은 `/proc/<pid>/stat` 의 `comm` 이라 **15자에서 잘린다**(커널 제약). 긴 실행파일명을
    감시하려면 선언도 잘린 이름으로 써야 한다.
    """

    count: int
    top_rss: tuple[ProcessInfo, ...]
    names: frozenset[str]
    pids_by_name: dict[str, tuple[int, ...]]


def _read_process(pid: int) -> ProcessInfo | None:
    """`/proc/<pid>/stat` 한 개를 읽는다. 사라졌으면 None(경쟁은 정상 상황이다)."""
    text = _read_text(_PROC_ROOT / str(pid) / "stat")
    if text is None:
        return None
    # comm 에는 공백·괄호가 들어갈 수 있어 마지막 ") " 를 기준으로 잘라야 안전하다.
    head, sep, tail = text.rpartition(") ")
    if not sep:
        return None
    name = head.partition("(")[2]
    fields = tail.split()
    if len(fields) <= _PROC_STAT_RSS_PAGES:
        return None
    try:
        rss_pages = int(fields[_PROC_STAT_RSS_PAGES])
    except ValueError:
        return None
    return ProcessInfo(pid=pid, name=name, rss_mb=rss_pages * _PAGE_MB)


def scan_processes(top_n: int = 5) -> ProcessScan:
    """`/proc` 를 한 번 순회해 프로세스 수·상위 RSS·이름 집합을 모은다.

    순회 중 프로세스가 사라지는 것은 정상이므로 조용히 건너뛴다.

    Args:
        top_n: RSS 상위 몇 개를 남길지. 0 이하면 빈 튜플.
    Returns:
        `ProcessScan`.
    """
    found: list[ProcessInfo] = []
    pids: dict[str, list[int]] = {}
    if not _PROC_ROOT.is_dir():
        return ProcessScan(count=0, top_rss=(), names=frozenset(), pids_by_name={})
    for entry in _PROC_ROOT.iterdir():
        if not entry.name.isdigit():
            continue
        info = _read_process(int(entry.name))
        if info is None:
            continue
        found.append(info)
        pids.setdefault(info.name, []).append(info.pid)
    found.sort(key=lambda p: p.rss_mb, reverse=True)
    return ProcessScan(
        count=len(found),
        top_rss=tuple(found[: max(0, top_n)]),
        names=frozenset(pids),
        pids_by_name={name: tuple(sorted(v)) for name, v in pids.items()},
    )


# ── 기타 ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GpuInfo:
    """GPU(GR3D) 상태.

    Jetson 은 GPU 가 **시스템 메모리를 공유**하므로 별도 GPU 메모리 항목이 없다 —
    `MemoryInfo` 가 곧 GPU 메모리 압박이기도 하다.

    Attributes:
        load_pct: 사용률(%) — 순간값이 아니라 1초 창 평균(`_GPU_LOAD_WINDOW_S`). 노드 부재 시 None.
        freq_hz: 현재 devfreq 주파수. 부재 시 None.
        max_freq_hz: devfreq 최대 주파수. `freq_hz` 가 이보다 낮으면 GPU 주파수 저감
            (throttle 또는 유휴 스케일다운)이 일어난 것이다. 본 장비는 `jetson-clocks` 가
            min=max 로 고정해 두었으므로(2026-07-28 실측 918 MHz) 저감이 곧 이상 신호다.
    """

    load_pct: float | None
    freq_hz: int | None
    max_freq_hz: int | None


def read_gpu() -> GpuInfo:
    """GPU 사용률·주파수. Jetson 에서 GPU 는 이 장비를 쓰는 이유이므로 필수 항목이다.

    Returns:
        `GpuInfo`. 노드가 없으면 필드가 None.
    """
    load_pct: float | None = None
    for path in _GPU_LOAD_PATHS:
        raw = _read_int(path)
        if raw is None:
            continue
        # 창 평균 — 첫 표본은 위에서 읽었고, 나머지를 창 안에 등간격으로 읽는다.
        total, count = raw, 1
        step = _GPU_LOAD_WINDOW_S / _GPU_LOAD_SAMPLES
        for _ in range(_GPU_LOAD_SAMPLES - 1):
            time.sleep(step)
            nxt = _read_int(path)
            if nxt is not None:
                total += nxt
                count += 1
        load_pct = max(0.0, min(100.0, total / count / _GPU_LOAD_PER_MILLE))
        break
    freq = max_freq = None
    if _DEVFREQ_ROOT.is_dir():
        for node in sorted(_DEVFREQ_ROOT.glob("*.gpu")):
            freq = _read_int(node / "cur_freq")
            max_freq = _read_int(node / "max_freq")
            if freq is not None:
                break
    if freq is None and _DRM_ROOT.is_dir():
        # `card*` glob 은 `card1-HDMI-A-1` 같은 커넥터도 잡는다 — 숫자로 끝나는 카드만 본다.
        for card in sorted(_DRM_ROOT.glob("card[0-9]*")):
            if not card.name[4:].isdigit():
                continue
            cur_mhz = _read_int(card / "gt_cur_freq_mhz")
            if cur_mhz is None:
                continue
            freq = cur_mhz * _HZ_PER_MHZ
            max_mhz = _read_int(card / "gt_max_freq_mhz")
            max_freq = None if max_mhz is None else max_mhz * _HZ_PER_MHZ
            break
    return GpuInfo(load_pct=load_pct, freq_hz=freq, max_freq_hz=max_freq)


@dataclass(frozen=True)
class PowerRail:
    """전원 레일 하나의 전압·전류·전력.

    Attributes:
        name: 레일 이름(`VDD_IN` 등). hwmon 의 `in<N>_label`.
        voltage_mv: 전압(mV).
        current_ma: 전류(mA).
        power_mw: 전력(mW) = 전압×전류. **커널이 전력 노드를 주지 않아 계산값**이다.
    """

    name: str
    voltage_mv: int
    current_ma: int

    @property
    def power_mw(self) -> float:
        """전력(mW). mV × mA = µW 이므로 1000 으로 나눈다."""
        return self.voltage_mv * self.current_ma / 1000.0


def read_power_rails() -> tuple[PowerRail, ...]:
    """INA3221 전원 레일별 전압·전류.

    전류는 소비 전력의 직접 지표다 — 부하가 아닌데 전류가 오르면 하드웨어 이상이고,
    입력 전류가 급변하면 전원계(배터리·컨버터) 문제를 시사한다.

    Returns:
        레일 튜플. 센서가 없으면 빈 튜플(다른 reader 와 같이 부재에 관대하다).
    """
    if not _HWMON_ROOT.is_dir():
        return ()
    rails: list[PowerRail] = []
    for hwmon in sorted(_HWMON_ROOT.glob("hwmon*")):
        if _read_text(hwmon / "name") != _INA3221_NAME:
            continue
        for ch in range(1, _MAX_RAIL_CHANNELS + 1):
            # **라벨이 있는 채널만 레일이다.** 이 드라이버는 라벨 없는 `curr4_input`·
            # `in4~in6_input` 도 노출하는데 그것은 shunt 전압 등 파생값이지 전원 레일이
            # 아니다(2026-07-29 실측: `in7_label` = "sum of shunt voltages").
            # 라벨 없는 채널까지 실으면 화면에 존재하지 않는 17.8 W 레일이 뜬다.
            # 채널별 라벨 유무 확인: ls /sys/class/hwmon/hwmon*/in*_label curr*_input
            label = _read_text(hwmon / f"in{ch}_label")
            if not label:
                continue
            current = _read_int(hwmon / f"curr{ch}_input")
            voltage = _read_int(hwmon / f"in{ch}_input")
            if current is None or voltage is None:
                continue
            rails.append(
                PowerRail(name=label, voltage_mv=voltage, current_ma=current)
            )
    return tuple(rails)


@dataclass(frozen=True)
class EnergyCounter:
    """powercap 도메인 하나의 **누적** 에너지.

    `energy_uj` 는 순간 전력이 아니라 계속 증가하는 카운터다 — 전력(W)은 두 표본의 차분을 경과
    시간으로 나눠야 나온다(`power_watts`). 누적값을 그대로 실으면 스왑 사용량과 같은 실패가 된다.

    Attributes:
        name: 도메인 이름(`package-0`·`core`·`uncore`·`dram`). powercap 의 `name` 파일.
        energy_uj: 누적 소비 에너지(마이크로줄).
        max_range_uj: 이 값에서 되감긴다. 되감김 보정에 쓰며, 읽지 못하면 None.
    """

    name: str
    energy_uj: int
    max_range_uj: int | None


def read_energy_counters(root: Path | None = None) -> tuple[EnergyCounter, ...]:
    """powercap(RAPL) 도메인별 누적 에너지.

    **판독에 권한이 필요하다.** 커널은 이 노드를 기본적으로 root 전용(0400)으로 둔다 — 전력
    파형에서 다른 프로세스의 비밀을 추측하는 부채널(PLATYPUS) 대응이다. 권한이 없으면 다른
    reader 와 같이 **조용히 빈 튜플**을 돌려준다. 코드가 권한을 바꾸려 시도하지 않는다.

    Args:
        root: powercap 루트. 시험이 가짜 트리를 넣기 위한 주입점이다 — 실경로는 권한이 닫혀
            있으면 판독 자체가 막히므로(확인: `ls -l /sys/class/powercap/intel-rapl:*/energy_uj`
            가 `-r-------- root root` 면 닫힌 상태), 파서 검증은 주입한 트리로 한다.
    Returns:
        도메인 튜플, 경로 이름 오름차순. 트리가 없거나 전부 못 읽으면 빈 튜플.
    """
    base = _POWERCAP_ROOT if root is None else root
    if not base.is_dir():
        return ()
    out: list[EnergyCounter] = []
    seen: dict[str, int] = {}
    for node in sorted(base.glob("intel-rapl:*")):
        name = _read_text(node / "name")
        energy = _read_int(node / "energy_uj")
        if name is None or energy is None:
            continue
        key = _unique_key(name, seen)
        seen[key] = energy
        out.append(EnergyCounter(name=key, energy_uj=energy,
                                 max_range_uj=_read_int(node / "max_energy_range_uj")))
    return tuple(out)


def power_watts(
    prev: Sequence[EnergyCounter], cur: Sequence[EnergyCounter], elapsed_s: float
) -> dict[str, float]:
    """두 표본 사이의 도메인별 평균 전력(W).

    카운터가 `max_range_uj` 에서 되감기므로 차분이 음수면 그 값을 더해 보정한다. 상시 감시는
    하루를 넘겨 돌기 때문에 되감김은 반드시 겪는다 — 보정하지 않으면 그 주기에 음수 전력이 나온다.
    `max_range_uj` 를 읽지 못한 도메인은 그 주기를 **버린다**(음수를 보고하지 않는다).

    Args:
        prev: 이전 표본.
        cur: 현재 표본.
        elapsed_s: 경과 시간(초). 0 이하면 빈 dict.
    Returns:
        {도메인: 와트}. 양쪽에 다 있는 도메인만.
    """
    if elapsed_s <= 0:
        return {}
    before = {c.name: c for c in prev}
    out: dict[str, float] = {}
    for counter in cur:
        earlier = before.get(counter.name)
        if earlier is None:
            continue
        delta_uj = counter.energy_uj - earlier.energy_uj
        if delta_uj < 0:
            if counter.max_range_uj is None:
                continue
            delta_uj += counter.max_range_uj
        out[counter.name] = delta_uj / elapsed_s / _UJ_PER_J
    return out


@dataclass(frozen=True)
class SwapCounters:
    """`/proc/vmstat` 의 누적 스왑 페이지 수. **활동량은 이 값의 차분으로만** 구한다.

    스왑 *사용량*(`MemoryInfo.swap_used_mb`)은 위험 신호로 쓸 수 없다 — 리눅스는 한 번
    스왑에 나간 페이지를 압박이 끝나도 적극적으로 되돌리지 않으므로 사용량이 몇 시간씩
    높게 남는다(2026-07-28 시험 운전에서 표본 97 % 가 그 이유로 WARN 이 됐다).
    지금 **스왑을 읽고 쓰고 있는지**가 실시간성 위험이다.
    """

    pswpin: int
    pswpout: int


def read_swap_counters() -> SwapCounters | None:
    """`/proc/vmstat` 에서 누적 스왑 in/out 페이지 수를 읽는다. 없으면 None."""
    text = _read_text(_PROC_ROOT / "vmstat")
    if text is None:
        return None
    vals: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] in ("pswpin", "pswpout"):
            try:
                vals[parts[0]] = int(parts[1])
            except ValueError:
                continue
    if "pswpin" not in vals or "pswpout" not in vals:
        return None
    return SwapCounters(pswpin=vals["pswpin"], pswpout=vals["pswpout"])


def swap_rate_pages_s(
    prev: SwapCounters, cur: SwapCounters, elapsed_s: float
) -> tuple[float, float]:
    """두 표본 사이의 스왑 in/out 속도(페이지/초).

    카운터가 되감기면(재부팅) 0 을 돌려준다 — 음수 속도를 보고하지 않는다.

    Args:
        prev: 이전 누적값.
        cur: 현재 누적값.
        elapsed_s: 경과 시간(초). 0 이하면 (0.0, 0.0).
    Returns:
        (in 속도, out 속도) 페이지/초.
    """
    if elapsed_s <= 0:
        return 0.0, 0.0
    din = max(0, cur.pswpin - prev.pswpin)
    dout = max(0, cur.pswpout - prev.pswpout)
    return din / elapsed_s, dout / elapsed_s


@dataclass(frozen=True)
class CanInterface:
    """socketcan 인터페이스 하나의 상태와 누적 카운터.

    **카운터는 누계다.** 판정은 반드시 두 표본의 차분(증가율)으로 한다 — 누계 기준으로 판정하면
    한 번 오른 값이 계속 남아 경보가 상시화된다(2026-07-31 스왑 사용량 기준에서 표본 97 % 가
    WARN 이 된 것과 같은 실패).

    Attributes:
        name: 인터페이스 이름(`can0` 등). **이름으로 판별하지 않고** `type == ARPHRD_CAN` 으로 찾는다.
        is_up: `operstate` 가 `up` 인지.
        rx_packets · tx_packets: 누적 프레임 수.
        rx_errors · tx_errors: 누적 에러 수.
        rx_dropped · tx_dropped: 누적 드랍 수.
    """

    name: str
    is_up: bool
    rx_packets: int
    tx_packets: int
    rx_errors: int
    tx_errors: int
    rx_dropped: int
    tx_dropped: int

    @property
    def total_errors(self) -> int:
        """rx+tx 에러·드랍 합계. 증가율 판정의 입력."""
        return self.rx_errors + self.tx_errors + self.rx_dropped + self.tx_dropped


def read_can_interfaces() -> tuple[CanInterface, ...]:
    """socketcan 인터페이스별 상태·누적 카운터.

    **인터페이스가 없으면 빈 튜플**을 돌려준다 — CAN 을 쓰지 않는 운영도 정상이므로
    부재 자체는 이상이 아니다(2026-08-01 이 장비 실측: socketcan 인터페이스 0개).

    Returns:
        `CanInterface` 튜플, 이름 오름차순.
    """
    if not _NETDEV_ROOT.is_dir():
        return ()
    out: list[CanInterface] = []
    for dev in sorted(_NETDEV_ROOT.iterdir()):
        if _read_int(dev / "type") != _ARPHRD_CAN:
            continue
        stats = dev / "statistics"

        def counter(field: str) -> int:
            return _read_int(stats / field) or 0

        out.append(
            CanInterface(
                name=dev.name,
                is_up=_read_text(dev / "operstate") == "up",
                rx_packets=counter("rx_packets"),
                tx_packets=counter("tx_packets"),
                rx_errors=counter("rx_errors"),
                tx_errors=counter("tx_errors"),
                rx_dropped=counter("rx_dropped"),
                tx_dropped=counter("tx_dropped"),
            )
        )
    return tuple(out)


def can_error_rate(prev: CanInterface, cur: CanInterface, elapsed_s: float) -> float:
    """두 표본 사이 에러+드랍 증가율(건/초).

    카운터가 되감기면(인터페이스 재기동) 0 을 돌려준다 — 음수 속도를 보고하지 않는다.

    Args:
        prev: 이전 표본.
        cur: 현재 표본.
        elapsed_s: 경과 시간(초). 0 이하면 0.0.
    Returns:
        증가율(건/초).
    """
    if elapsed_s <= 0:
        return 0.0
    return max(0, cur.total_errors - prev.total_errors) / elapsed_s


def count_dds_segments() -> int:
    """`/dev/shm` 의 DDS 공유메모리 세그먼트 수.

    **판정하지 않고 기록만 한다** — 정상 개수는 노드 수·QoS 에 따라 달라져 기준을 세울 수 없다.
    사후 분석에서 "그 시점에 DDS 가 살아 있었나"를 가리는 용도다.

    Returns:
        세그먼트 수. `/dev/shm` 을 읽을 수 없으면 0.
    """
    if not _SHM_ROOT.is_dir():
        return 0
    try:
        names = [p.name.lower() for p in _SHM_ROOT.iterdir()]
    except OSError:
        return 0
    return sum(1 for n in names if any(pat in n for pat in _DDS_SHM_PATTERNS))


def read_load_average() -> tuple[float, float, float] | None:
    """1·5·15분 부하 평균. 읽을 수 없으면 None."""
    try:
        return os.getloadavg()
    except OSError:
        return None


def read_uptime_s() -> float | None:
    """부팅 후 경과 시간(초). 재시작을 감지하는 데 쓴다. 읽을 수 없으면 None."""
    text = _read_text(_PROC_ROOT / "uptime")
    if text is None:
        return None
    parts = text.split()
    if not parts:
        return None
    try:
        return float(parts[0])
    except ValueError:
        return None
