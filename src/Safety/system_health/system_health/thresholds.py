"""임계값과 판정 — 우리 기준. 커널·`nvfancontrol` 설정은 참조하지 않는다.

**왜 자체 기준인가** (ADR 2026-07-28 §Decision 4, 사용자 지시):
커널 trip 값은 운영 경보에 쓸 수 없다. 이 하드웨어의 `cpu-thermal` 은 99 °C 에서야 주파수를
깎기 시작하고 104.5 °C 에서 셧다운한다(2026-07-28 실측) — 99 °C 경보는 이미 성능이 무너진
뒤이고 셧다운이 5.5 °C 앞이라 너무 늦다. 70 °C trip 은 표면온도 경보일 뿐 실리콘 여유와 무관하다.

**⚠ 잠정치 (provisional)**: 온도·CPU 기본값은 램프 시험 전 잠정치다. `PROVISIONAL_KEYS` 에
열거되어 있으며, 부하 램프 시험(ADR §Consequences 후속과제 1)으로 확정해야 한다. 지어낸 값을
확정처럼 쓰지 않기 위해 코드에 명시적으로 표시한다.

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
    swap_used_warn_mb: float = 256.0
    swap_used_error_mb: float = 2048.0
    disk_free_warn_gb: float = 10.0
    disk_free_error_gb: float = 6.0
    # 팬을 실제로 돌리는 userspace 데몬. 이것이 죽으면 팬이 마지막 PWM 값에 얼어붙고,
    # 커널은 99 °C 까지 개입하지 않으므로 그 구간이 통째로 무방비가 된다.
    fan_daemon_name: str = "nvfancontrol"

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
        """
        applied = {
            k: v for k, v in overrides.items() if not k.startswith(COMMENT_KEY_PREFIX)
        }
        known = {f.name for f in fields(cls)}
        unknown = set(applied) - known
        if unknown:
            raise KeyError(f"알 수 없는 임계값 항목: {sorted(unknown)}")
        return cls(**applied)

    def to_mapping(self) -> dict[str, Any]:
        """현재 값을 JSON 직렬화 가능한 dict 로. `from_mapping` 의 역함수.

        Returns:
            필드명 → 값. 주석 키는 포함하지 않는다(호출자가 붙인다).
        """
        return asdict(self)


#: 램프 시험 전까지 근거가 실측이 아닌 항목. 보고서·문서에서 `잠정` 으로 표기한다.
PROVISIONAL_KEYS: frozenset[str] = frozenset(
    {"temp_warn_c", "temp_error_c", "cpu_warn_pct", "cpu_error_pct"}
)


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

    swap_used_mb = memory.get("swap_used_mb")
    if swap_used_mb is not None:
        level = _grade(
            swap_used_mb,
            th.swap_used_warn_mb,
            th.swap_used_error_mb,
            higher_is_worse=True,
        )
        if level is not Level.OK:
            findings.append(
                Finding(
                    key="swap_used",
                    level=level,
                    value=swap_used_mb,
                    message=f"스왑 사용 {swap_used_mb:.0f}MB — 스왑 진입은 실시간성 저하의 "
                    f"조기 신호 (임계 WARN {th.swap_used_warn_mb}"
                    f"/ERROR {th.swap_used_error_mb}MB)",
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
