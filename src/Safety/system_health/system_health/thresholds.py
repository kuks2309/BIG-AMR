"""임계값과 판정 — 우리 기준. 커널·`nvfancontrol` 설정은 참조하지 않는다.

**왜 자체 기준인가** (ADR 2026-07-28 §Decision 4, 사용자 지시):
커널 trip 값은 운영 경보에 쓸 수 없다. 이 하드웨어의 `cpu-thermal` 은 99 °C 에서야 주파수를
깎기 시작하고 104.5 °C 에서 셧다운한다(2026-07-28 실측) — 99 °C 경보는 이미 성능이 무너진
뒤이고 셧다운이 5.5 °C 앞이라 너무 늦다. 70 °C trip 은 표면온도 경보일 뿐 실리콘 여유와 무관하다.

**⚠ 잠정치 (provisional)**: 온도·CPU 기본값은 램프 시험 전 잠정치이며 `PROVISIONAL_KEYS` 에
열거되어 있다. 지어낸 값을 확정처럼 쓰지 않기 위해 코드에 명시적으로 표시한다.

- **온도** 임계: 부하 램프 시험으로 확정한다
  (ADR 2026-07-28 §Consequences 후속 과제 1 — 온도·`pwm1` 동시 기록 → 온도 임계 확정).
- **CPU** 임계: 확정 절차가 아직 없다. 위 후속 과제는 온도만 대상으로 한다.

판정 결과는 `Finding` 목록이다. 판정 대상은 `sampler.collect()` 가 만든 record dict 이며,
**항목이 없으면 그 항목은 판정하지 않는다**(하드웨어마다 읽히는 노드가 다르므로 부재는 정상).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from enum import IntEnum
from typing import Any, Mapping

#: `_` 로 시작하는 키는 주석으로 보고 무시한다. JSON 에는 주석 문법이 없으므로, 설정 파일에
#: 설명을 남길 수 있게 하려면 이 관례가 필요하다. 오타 검출(§from_mapping)은 그대로 유지된다.
COMMENT_KEY_PREFIX = "_"


class Level(IntEnum):
    """심각도. 정수 크기로 비교 가능해야 하므로 IntEnum 이다."""

    OK = 0
    WARN = 1
    ERROR = 2


@dataclass(frozen=True)
class Finding:
    """단일 판정 결과.

    Attributes:
        key: 안정 키(로그 집계용). 표현이 바뀌어도 이 값은 유지한다.
        level: 심각도.
        value: 판정에 쓰인 실측값. 값이 없는 판정(데몬 부재 등)은 None.
        message: 사람이 읽을 설명.
    """

    key: str
    level: Level
    value: float | None
    message: str


@dataclass(frozen=True)
class Thresholds:
    """경보 임계값. 전부 CLI/JSON 으로 덮어쓸 수 있다.

    디스크 하한이 `dataset_collector` 의 `MIN_FREE_GB_DEFAULT = 5.0` **보다 높다**. 두 방어가
    순서대로 걸려야 하기 때문이다 — 감시기가 먼저 경고하고, 그래도 차면 수집기가 저장을 멈춘다.
    """

    temp_warn_c: float = 75.0  # ⚠ 잠정 — 램프 시험으로 확정 필요
    temp_error_c: float = 85.0  # ⚠ 잠정 — 램프 시험으로 확정 필요
    cpu_warn_pct: float = 85.0  # ⚠ 잠정 — 순간값 기준(지속시간 미반영)
    cpu_error_pct: float = 95.0  # ⚠ 잠정 — 순간값 기준(지속시간 미반영)
    mem_available_warn_mb: float = 2000.0
    mem_available_error_mb: float = 1000.0
    # 스왑은 **활동량**(페이지/초)으로 판정한다. 사용량 기준은 폐기했다 — 2026-07-28 시험
    # 운전에서 표본 97 % 가 WARN 이 됐다: 리눅스는 압박이 끝나도 스왑에 나간 페이지를 되돌리지
    # 않아 사용량이 몇 시간씩 높게 남는다. 지금 스왑을 읽고 쓰고 있는지가 실시간성 위험이다.
    # in+out 합산 기준. 4 KiB 페이지에서 64 pages/s ≈ 0.25 MB/s.
    swap_rate_warn_pages_s: float = 64.0
    swap_rate_error_pages_s: float = 512.0
    disk_free_warn_gb: float = 10.0
    disk_free_error_gb: float = 6.0
    # GPU 사용률은 **기본적으로 판정하지 않는다**(None). 높은 GPU 사용률은 이 장비를 쓰는
    # 목적이지 결함이 아니다 — 임계를 켜면 정상 추론 부하가 곧 경보가 되어 경보 피로만 만든다.
    # 필요하면 설정 파일에서 값을 넣어 활성화한다.
    gpu_warn_pct: float | None = None
    gpu_error_pct: float | None = None
    # 입력 전류도 **기본 비활성**이다. 부하가 오르면 전류도 오르는 게 정상이므로, 기준선을
    # 모르는 상태에서 임계를 지어내면 GPU 와 같은 경보 피로가 된다. 시험 운전으로 이 장비의
    # 정상 대역을 확인한 뒤 값을 넣어 켠다(2026-07-29 관측 시작: VDD_IN 약 1.6 A / 18 W).
    input_rail_name: str = "VDD_IN"
    input_current_warn_ma: float | None = None
    input_current_error_ma: float | None = None
    # ── Phase 3a: SW(Software) 이상유무 ──────────────────────────────────────
    # 살아 있어야 하는 프로세스 이름들(`/proc` comm — **15자에서 잘린다**).
    # **비어 있으면 판정하지 않는다.** 감시기가 "무엇이 정상인지" 를 스스로 정하지 않는다:
    # 운영 시나리오마다 띄우는 launch 가 다르고, 목록을 지어내면 실재하지 않는 것을 감시하게
    # 된다(ADR 2026-08-01 §Decision 2 — 조사 시점에 ROS 노드가 0개였다.
    # 근거: docs/adr/2026-08-01-system-health-phase3-sw-watchdog.md:53).
    expected_processes: tuple[str, ...] = ()
    # CAN 에러 **증가율**(건/초) 임계. 누계가 아니다 — 누계 기준은 한 번 오르면 계속 경보한다.
    # 기본 비활성: 이 장비에 socketcan 인터페이스가 아직 없어 정상 대역을 모른다.
    can_error_rate_warn_s: float | None = None
    can_error_rate_error_s: float | None = None
    # 팬을 실제로 돌리는 userspace 데몬. 이것이 죽으면 팬이 마지막 PWM 값에 얼어붙고,
    # 커널은 99 °C 까지 개입하지 않으므로 그 구간이 통째로 무방비가 된다.
    fan_daemon_name: str = "nvfancontrol"

    def __post_init__(self) -> None:
        """JSON 에서 온 list 를 tuple 로 맞추고, WARN/ERROR 대소 순서를 검증한다.

        설정 파일은 배열을 list 로 주는데 필드는 tuple 이라, 그대로 두면
        `from_mapping(x.to_mapping()) == x` 왕복 비교가 타입 때문에 깨진다.

        순서 검증을 여기 두는 이유: 순서가 뒤집힌 임계값은 **WARN 대역을 통째로 없앤다**.
        예를 들어 `temp_warn_c=90 / temp_error_c=85` 면 87 °C 가 WARN 을 건너뛰고 바로 ERROR 가
        된다. 사용자는 90 °C 부터 경고를 받는다고 믿는데 실제로는 85 °C 부터 최고 등급이 뜬다.

        Raises:
            ValueError: WARN/ERROR 순서가 방향과 어긋날 때.
        """
        if not isinstance(self.expected_processes, tuple):
            object.__setattr__(self, "expected_processes", tuple(self.expected_processes))
        for warn_key, error_key, higher_is_worse in THRESHOLD_PAIRS:
            warn, error = getattr(self, warn_key), getattr(self, error_key)
            if warn is None or error is None:
                continue  # 한쪽이라도 비활성이면 판정 자체를 하지 않는다.
            if higher_is_worse and warn > error:
                raise ValueError(
                    f"임계값 순서 오류: 값이 클수록 나쁜 항목이므로 "
                    f"{warn_key}({warn}) <= {error_key}({error}) 여야 한다")
            if not higher_is_worse and warn < error:
                raise ValueError(
                    f"임계값 순서 오류: 값이 작을수록 나쁜 항목이므로 "
                    f"{warn_key}({warn}) >= {error_key}({error}) 여야 한다")

    @classmethod
    def from_mapping(cls, overrides: Mapping[str, Any]) -> "Thresholds":
        """기본값 위에 `overrides` 를 얹어 만든다.

        `_` 로 시작하는 키는 주석으로 보고 무시한다(`COMMENT_KEY_PREFIX`) — 그래야
        `to_mapping()` 이 써 넣은 설명 필드를 그대로 되읽을 수 있다(왕복 가능).

        Args:
            overrides: 필드명 → 값. 빈 매핑이면 전부 기본값.
        Returns:
            새 `Thresholds`.
        Raises:
            KeyError: 알 수 없는 필드명이 있을 때. **오타를 조용히 무시하면 사용자가 임계값을
                바꿨다고 믿는데 실제로는 안 바뀐 상태가 되므로** 거부한다.
            ValueError: 값의 타입이 필드와 맞지 않거나(`"75"` 같은 문자열 수치) WARN/ERROR
                순서가 뒤집혔을 때. **로드 시점에 거부한다** — 통과시키면 첫 판정에서
                `TypeError` 로 죽고, 유닛의 `Restart=always` 와 만나 5초 주기 재시작 루프가
                되어 기록이 하나도 남지 않는다.
        """
        applied = {
            k: v for k, v in overrides.items() if not k.startswith(COMMENT_KEY_PREFIX)
        }
        known = {f.name for f in fields(cls)}
        unknown = set(applied) - known
        retired = sorted(unknown & set(RETIRED_KEYS))
        if retired:
            # 의미가 바뀐 항목은 자동 변환하지 않는다 — 사용량(MB)과 활동량(pages/s)은 단위도
            # 뜻도 달라서 옮겨 담으면 사용자가 의도하지 않은 임계가 된다. 대신 무엇으로
            # 바뀌었는지 알려서 사람이 고치게 한다.
            detail = "; ".join(f"{k} → {RETIRED_KEYS[k]}" for k in retired)
            raise KeyError(f"폐기된 임계값 항목: {retired} — 설정 파일을 고치십시오. {detail}")
        if unknown:
            raise KeyError(
                f"알 수 없는 임계값 항목: {sorted(unknown)} "
                f"(사용 가능: {sorted(known)})")
        annotations = {f.name: f.type for f in fields(cls)}
        return cls(**{k: _coerce(k, str(annotations[k]), v) for k, v in applied.items()})

    def to_mapping(self) -> dict[str, Any]:
        """현재 값을 JSON 직렬화 가능한 dict 로. `from_mapping` 의 역함수.

        Returns:
            필드명 → 값. 주석 키는 포함하지 않는다(호출자가 붙인다).
        """
        return asdict(self)


#: (WARN 키, ERROR 키, 값이 클수록 나쁜가). `_grade` 의 `higher_is_worse` 와 같은 방향이며
#: `__post_init__` 의 순서 검증과 `evaluate` 의 판정이 같은 근원을 보게 하려고 표로 둔다.
THRESHOLD_PAIRS: tuple[tuple[str, str, bool], ...] = (
    ("temp_warn_c", "temp_error_c", True),
    ("cpu_warn_pct", "cpu_error_pct", True),
    ("mem_available_warn_mb", "mem_available_error_mb", False),
    ("swap_rate_warn_pages_s", "swap_rate_error_pages_s", True),
    ("disk_free_warn_gb", "disk_free_error_gb", False),
    ("gpu_warn_pct", "gpu_error_pct", True),
    ("input_current_warn_ma", "input_current_error_ma", True),
    ("can_error_rate_warn_s", "can_error_rate_error_s", True),
)


def _coerce(key: str, annotation: str, value: Any) -> Any:
    """설정 파일에서 온 값 하나를 필드 타입에 맞춰 변환하거나 거부한다.

    `from __future__ import annotations` 때문에 `fields()` 가 주는 타입은 **문자열**이다
    (`"float | None"`). 실제 타입 객체를 얻으려면 `typing.get_type_hints` 가 필요한데, 그
    한 줄을 위해 런타임 의존을 늘리는 대신 문자열을 그대로 판별한다 — 본 dataclass 의 필드
    타입은 `float`·`float | None`·`str`·`tuple[str, ...]` 넷뿐이다.

    Args:
        key: 필드명(오류 메시지용).
        annotation: 필드 타입 주석 문자열.
        value: 설정 파일에서 온 값.
    Returns:
        필드 타입에 맞는 값.
    Raises:
        ValueError: 타입이 맞지 않을 때. 문자열 수치(`"75"`)를 조용히 숫자로 바꾸지 않는다 —
            설정 파일이 JSON 이라 숫자를 숫자로 쓸 수 있고, 따옴표는 실수의 신호다.
    """
    optional = "None" in annotation
    if value is None:
        if optional:
            return None
        raise ValueError(f"임계값 '{key}' 는 null 을 받지 않는다")
    if annotation.startswith("float") or annotation.startswith("int"):
        # bool 은 int 의 하위형이라 그냥 두면 True 가 1.0 으로 통과한다.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"임계값 '{key}' 는 숫자여야 한다 — 받은 값 {value!r} ({type(value).__name__})")
        return float(value)
    if annotation.startswith("str"):
        if not isinstance(value, str):
            raise ValueError(
                f"임계값 '{key}' 는 문자열이어야 한다 — 받은 값 {value!r} "
                f"({type(value).__name__})")
        return value
    if annotation.startswith("tuple"):
        if isinstance(value, str) or not isinstance(value, (list, tuple)):
            raise ValueError(
                f"임계값 '{key}' 는 문자열 배열이어야 한다 — 받은 값 {value!r} "
                f"({type(value).__name__})")
        bad = [v for v in value if not isinstance(v, str)]
        if bad:
            raise ValueError(f"임계값 '{key}' 의 원소는 전부 문자열이어야 한다 — {bad!r}")
        return tuple(value)
    return value


#: 램프 시험 전까지 근거가 실측이 아닌 항목. 보고서·문서에서 `잠정` 으로 표기한다.
PROVISIONAL_KEYS: frozenset[str] = frozenset(
    {"temp_warn_c", "temp_error_c", "cpu_warn_pct", "cpu_error_pct"}
)

#: 폐기된 설정 키 → 대체 항목 안내. **자동 변환하지 않는다** — 의미·단위가 바뀐 항목을 옮겨
#: 담으면 사용자가 의도하지 않은 임계가 된다. 기동을 거부하고 무엇으로 바뀌었는지 알린다.
#: (이 안내가 없으면 상주 서비스가 업그레이드 후 이유 없이 죽어 보인다 — 2026-07-28 실제 발생.)
RETIRED_KEYS: dict[str, str] = {
    "swap_used_warn_mb": "swap_rate_warn_pages_s (사용량 MB → 활동량 pages/s)",
    "swap_used_error_mb": "swap_rate_error_pages_s (사용량 MB → 활동량 pages/s)",
}


def _grade(
    value: float,
    warn_at: float,
    error_at: float,
    *,
    higher_is_worse: bool,
) -> Level:
    """값 하나를 WARN/ERROR 임계와 비교해 등급을 매긴다.

    Args:
        value: 실측값.
        warn_at: WARN 경계(포함).
        error_at: ERROR 경계(포함).
        higher_is_worse: True 면 값이 클수록 나쁨(온도·사용률), False 면 작을수록 나쁨(여유공간).
    Returns:
        `Level`.
    """
    if higher_is_worse:
        if value >= error_at:
            return Level.ERROR
        if value >= warn_at:
            return Level.WARN
    else:
        if value <= error_at:
            return Level.ERROR
        if value <= warn_at:
            return Level.WARN
    return Level.OK


def _hottest(temps: Mapping[str, float]) -> tuple[str, float] | None:
    """가장 뜨거운 존과 그 온도. 비어 있으면 None."""
    if not temps:
        return None
    zone = max(temps, key=lambda k: temps[k])
    return zone, temps[zone]


def evaluate(record: Mapping[str, Any], th: Thresholds) -> tuple[Finding, ...]:
    """샘플 record 를 임계값과 대조해 WARN/ERROR 만 돌려준다.

    OK 는 결과에 넣지 않는다 — 로그가 정상 항목으로 뒤덮이면 이상을 못 찾는다.

    Args:
        record: `sampler.collect()` 가 만든 dict. 없는 항목은 판정을 건너뛴다.
        th: 임계값.
    Returns:
        심각도 내림차순 `Finding` 튜플. 이상 없으면 빈 튜플.
    """
    findings: list[Finding] = []

    hottest = _hottest(record.get("temperatures_c") or {})
    if hottest is not None:
        zone, temp = hottest
        level = _grade(temp, th.temp_warn_c, th.temp_error_c, higher_is_worse=True)
        if level is not Level.OK:
            findings.append(
                Finding(
                    key="temperature",
                    level=level,
                    value=temp,
                    message=f"최고 온도 {temp:.1f}°C ({zone}) — 임계 WARN {th.temp_warn_c}"
                    f"/ERROR {th.temp_error_c}°C (잠정치)",
                )
            )

    cpu_pct = record.get("cpu_total_pct")
    if cpu_pct is not None:
        level = _grade(cpu_pct, th.cpu_warn_pct, th.cpu_error_pct, higher_is_worse=True)
        if level is not Level.OK:
            findings.append(
                Finding(
                    key="cpu",
                    level=level,
                    value=cpu_pct,
                    message=f"CPU 사용률 {cpu_pct:.1f}% — 임계 WARN {th.cpu_warn_pct}"
                    f"/ERROR {th.cpu_error_pct}% (잠정치·순간값)",
                )
            )

    memory = record.get("memory") or {}
    available_mb = memory.get("available_mb")
    if available_mb is not None:
        level = _grade(
            available_mb,
            th.mem_available_warn_mb,
            th.mem_available_error_mb,
            higher_is_worse=False,
        )
        if level is not Level.OK:
            findings.append(
                Finding(
                    key="memory_available",
                    level=level,
                    value=available_mb,
                    message=f"가용 메모리 {available_mb:.0f}MB — 임계 WARN "
                    f"{th.mem_available_warn_mb}/ERROR {th.mem_available_error_mb}MB",
                )
            )

    swap_rate = record.get("swap_rate_pages_s")
    if swap_rate is not None:
        total_rate = (swap_rate.get("in") or 0.0) + (swap_rate.get("out") or 0.0)
        level = _grade(
            total_rate,
            th.swap_rate_warn_pages_s,
            th.swap_rate_error_pages_s,
            higher_is_worse=True,
        )
        if level is not Level.OK:
            used = memory.get("swap_used_mb")
            used_note = f", 누적 사용 {used:.0f}MB" if used is not None else ""
            findings.append(
                Finding(
                    key="swap_rate",
                    level=level,
                    value=total_rate,
                    message=f"스왑 활동 {total_rate:.0f} pages/s "
                    f"(in {swap_rate.get('in', 0):.0f} / out "
                    f"{swap_rate.get('out', 0):.0f}{used_note}) — "
                    f"지금 스왑을 쓰고 있다 = 실시간성 저하 (임계 WARN "
                    f"{th.swap_rate_warn_pages_s}/ERROR {th.swap_rate_error_pages_s} pages/s)",
                )
            )

    gpu_pct = (record.get("gpu") or {}).get("load_pct")
    if gpu_pct is not None and th.gpu_warn_pct is not None and th.gpu_error_pct is not None:
        level = _grade(gpu_pct, th.gpu_warn_pct, th.gpu_error_pct, higher_is_worse=True)
        if level is not Level.OK:
            findings.append(
                Finding(
                    key="gpu",
                    level=level,
                    value=gpu_pct,
                    message=f"GPU 사용률 {gpu_pct:.1f}% — 임계 WARN {th.gpu_warn_pct}"
                    f"/ERROR {th.gpu_error_pct}%",
                )
            )

    for disk in record.get("disks") or []:
        free_gb = disk.get("free_gb")
        if free_gb is None:
            continue
        level = _grade(
            free_gb,
            th.disk_free_warn_gb,
            th.disk_free_error_gb,
            higher_is_worse=False,
        )
        if level is not Level.OK:
            findings.append(
                Finding(
                    key=f"disk_free:{disk.get('path', '?')}",
                    level=level,
                    value=free_gb,
                    message=f"디스크 여유 {free_gb:.1f}GB ({disk.get('path', '?')}) — 임계 "
                    f"WARN {th.disk_free_warn_gb}/ERROR {th.disk_free_error_gb}GB",
                )
            )

    rail = (record.get("power") or {}).get(th.input_rail_name)
    if (rail is not None and th.input_current_warn_ma is not None
            and th.input_current_error_ma is not None):
        current = rail.get("ma")
        if current is not None:
            level = _grade(current, th.input_current_warn_ma, th.input_current_error_ma,
                           higher_is_worse=True)
            if level is not Level.OK:
                findings.append(
                    Finding(
                        key="input_current",
                        level=level,
                        value=float(current),
                        message=f"{th.input_rail_name} 전류 {current} mA "
                        f"({rail.get('mw', 0)/1000:.1f} W) — 임계 WARN "
                        f"{th.input_current_warn_ma}/ERROR {th.input_current_error_ma} mA",
                    )
                )

    fan_daemon_alive = record.get("fan_daemon_alive")
    if fan_daemon_alive is False:
        findings.append(
            Finding(
                key="fan_daemon",
                level=Level.ERROR,
                value=None,
                message=f"팬 제어 데몬 '{th.fan_daemon_name}' 미동작 — 팬이 마지막 PWM 값에 "
                "고정된다. 온도 상승의 원인이 될 수 있다",
            )
        )

    watch = record.get("process_watch") or {}
    for name in watch.get("missing", []):
        findings.append(
            Finding(
                key=f"process_missing:{name}",
                level=Level.ERROR,
                value=None,
                message=f"프로세스 '{name}' 가 없다 — 죽었거나 기동하지 않았다",
            )
        )
    for name in watch.get("restarted", []):
        findings.append(
            Finding(
                key=f"process_restarted:{name}",
                level=Level.WARN,
                value=None,
                message=f"프로세스 '{name}' 의 PID 가 바뀌었다 — 죽었다 살아났다. "
                "생존 검사만으로는 보이지 않는 crash-loop 일 수 있다",
            )
        )

    for iface in record.get("can") or []:
        if iface.get("up") is False:
            findings.append(
                Finding(
                    key=f"can_down:{iface.get('name', '?')}",
                    level=Level.ERROR,
                    value=None,
                    message=f"CAN 인터페이스 '{iface.get('name', '?')}' 가 down 이다",
                )
            )
        can_rate = iface.get("error_rate_s")
        if (can_rate is not None and th.can_error_rate_warn_s is not None
                and th.can_error_rate_error_s is not None):
            level = _grade(can_rate, th.can_error_rate_warn_s, th.can_error_rate_error_s,
                           higher_is_worse=True)
            if level is not Level.OK:
                findings.append(
                    Finding(
                        key=f"can_errors:{iface.get('name', '?')}",
                        level=level,
                        value=can_rate,
                        message=f"CAN '{iface.get('name', '?')}' 에러 {can_rate:.1f} 건/초 "
                        f"(누계 {iface.get('errors_total', 0)}) — 임계 WARN "
                        f"{th.can_error_rate_warn_s}/ERROR {th.can_error_rate_error_s} 건/초",
                    )
                )

    if record.get("log_write_failed"):
        findings.append(
            Finding(
                key="log_write",
                level=Level.ERROR,
                value=None,
                message="감시 로그 기록 실패 — 이 상태에서는 사고 시 증거가 남지 않는다",
            )
        )

    findings.sort(key=lambda f: f.level, reverse=True)
    return tuple(findings)


def worst_level(findings: tuple[Finding, ...]) -> Level:
    """가장 심각한 등급. 비어 있으면 OK."""
    return max((f.level for f in findings), default=Level.OK)
