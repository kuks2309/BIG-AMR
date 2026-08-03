#!/usr/bin/env python3
"""안전 게이트 — 순수 함수만. 하드웨어·ROS·판다 무의존.

이 파일이 존재하는 이유는 하나다. **2026-07-27 에 검증 안 된 조향 지령으로
node4 가 물리 손상됐다**(`docs/claude-mistake/2026-07-27-002`). 그때 재발방지로
만든 강제 코드는 구 GUI 폐기와 함께 삭제됐고, 남은 강제는 `gui.py` 의 클램프
두 줄뿐이었다. 여기서는 그 강제를 **지령을 만드는 단일 지점**에 되돌려 놓고
전량 회귀 시험으로 고정한다.

모든 함수는 하드웨어 없이 시험 가능하다 — 그것이 이 파일의 설계 목적이다.
"""
from __future__ import annotations

import math
from typing import Optional

# ── 하드웨어 상수 ─────────────────────────────────────────────────────────
COUNTS_PER_DEG = 57344.0
#   근거: `docs/ros2_driver/2026-07-09-design-inputs.md` — 16384×4×315/360.
#   실측 홈↔90° Δ = +5,160,960 counts = 정확히 90.00°.

STEER_LIMIT_DEG = 90.0
#   크랩은 조향 90° + 바퀴 역회전으로도 같은 운동이 나오므로, ±90° 로 묶어
#   **이중해를 없앤다**(합의). 기구 한계(±140°)와는 다른 목적이다.

VEL_PER_MMPS = 24.447
VEL_MAX_UNITS = 4889            # ≈0.2 m/s. 실측이 아니라 config 환산 + 계승된 안전 상한

STATUSWORD_HOMED_BIT = 1 << 15  # 0=호밍 진행 중 · 1=완료

# ── 조향 홈: **코드에 값을 두지 않는다** ──────────────────────────────────
#   2026-08-02 결정(사용자 지시) — 홈은 기체마다 다르고 잘못되면 전체 코드가 오판한다.
#   따라서 **캘리브레이션 config 만이 정본**이고, 코드는 기본값을 갖지 않는다.
#   값이 없으면 조용히 대체하지 않고 `UnsafeCommand` 로 거부한다(fail-safe).
#
#   왜 상수를 없앴나: 구값 `{3:7871815, 4:7840086}` 이 저장소 31개 파일에 퍼져 있었고,
#   실측값보다 15배 널리 노출돼 새 세션이 grep 하면 틀린 값을 먼저 만났다.
#   코드 기본값이 존재하는 한 config 미로드가 조용한 오판으로 이어진다.
#
#   정본 위치: `config/machine/<기체>.yaml` 의 `steer_home_counts`
DEFAULT_STEER_HOME: dict = {}


class UnsafeCommand(ValueError):
    """안전 게이트가 지령을 거부했다. 조용히 무시하지 않고 예외로 알린다."""


def finite(*values: float) -> bool:
    """NaN·inf 가 하나라도 있으면 False.

    이 검사가 필요한 이유: `max(-v, min(v, x))` 이디엄은 NaN 을 클램프하지 못하고
    **첫 인자를 그대로 반환**한다. 즉 NaN 한 개가 최대속도 지령이 된다.
        >>> max(-0.2, min(0.2, float("nan")))
        0.2
    """
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)


def clamp(value: float, limit: float) -> float:
    """±limit 대칭 클램프. **비유한 입력은 거부한다**(조용히 통과시키지 않는다)."""
    if not finite(value, limit):
        raise UnsafeCommand(f"비유한 값은 클램프할 수 없다: {value!r}")
    return max(-limit, min(limit, value))


def steer_deg_to_counts(node: int, deg: float,
                        steer_home: Optional[dict] = None,
                        limit_deg: float = STEER_LIMIT_DEG,
                        counts_per_deg: float = COUNTS_PER_DEG) -> tuple[float, int]:
    """조향 각도 → 절대위치 counts. 반환 `(적용된 각도, counts)`.

    **범위를 벗어난 각도는 잘라서 보낸다** — 이 클램프가 0x607A 를 만드는
    단일 지점에 있는 것이 핵심이다. 상위 계층(기구학·모션 스택)에만 두면
    다른 상위가 붙었을 때 보호가 사라진다.
    """
    home = DEFAULT_STEER_HOME if steer_home is None else steer_home
    if not home:
        raise UnsafeCommand(
            "조향 홈이 설정되지 않았다 — 코드에 기본값을 두지 않으므로 "
            "캘리브레이션 config(`config/machine/<기체>.yaml` 의 `steer_home_counts`)가 "
            "반드시 실려야 한다. 값 없이 조향 지령을 만들지 않는다")
    if node not in home:
        raise UnsafeCommand(f"조향 홈이 정의되지 않은 노드: {node}")
    applied = clamp(float(deg), float(limit_deg))
    return applied, int(round(home[node] + applied * float(counts_per_deg)))


def drive_mmps_to_units(mmps: float, sign: int = 1,
                        max_units: int = VEL_MAX_UNITS,
                        units_per_mmps: float = VEL_PER_MMPS) -> int:
    """구동 속도 mm/s → raw(0.1 r/min) + 상한 클램프."""
    if not finite(mmps):
        raise UnsafeCommand(f"비유한 속도: {mmps!r}")
    raw = int(round(sign * float(mmps) * float(units_per_mmps)))
    return max(-int(max_units), min(int(max_units), raw))


def home_search_allowed(position: Optional[int], rng) -> tuple[bool, str]:
    """호밍(method 35) 시작 전 현재 위치가 예상 범위 안인가.

    **이 검사가 미측정 전제를 검출하는 장치다.** method 35 는 "지정한 절대 카운트로 가서
    거기를 홈으로 삼는" 방식이라 절대 엔코더가 전원 사이클을 넘어 재현된다는 전제 위에 있다
    (debt-007 상환계획 ② — 아직 측정되지 않았다). 전제가 깨지면 현재 위치가 엉뚱한 값이 되고,
    그대로 이동하면 바퀴가 예상 밖으로 돈다. 여기서 걸어 **움직이기 전에** 멈춘다.

    반환 `(허용, 사유)`.
    """
    if position is None:
        return False, "현재 위치를 모른다 — 피드백을 먼저 확보해야 한다"
    lo, hi = int(rng[0]), int(rng[1])
    if not (lo <= int(position) <= hi):
        return False, (f"현재 위치 {position} 가 예상 범위 [{lo}, {hi}] 밖이다 — "
                       f"엔코더 기준이 달라졌을 수 있다(전원 재투입 재현성 미측정). "
                       f"캘리브레이션을 확인하기 전에는 호밍하지 않는다")
    return True, "범위 내"


def is_homed(statusword: Optional[int]) -> Optional[bool]:
    """0x6041 bit15 판정. 상태워드를 모르면 None(= 판단 보류)."""
    if statusword is None:
        return None
    return bool(statusword & STATUSWORD_HOMED_BIT)


def position_trustworthy(statusword: Optional[int]) -> bool:
    """이 축의 0x6064 를 믿어도 되는가.

    호밍 진행 중(bit15=0)에는 드라이브가 위치를 **정확히 0 으로 고정**해 보고한다
    (실측 3,080/3,080 샘플). 그것을 각도로 환산하면 ≈−137° 가 나와 상위로
    흘러가므로, 상태워드를 모르거나 호밍 중이면 위치를 쓰지 않는다.
    """
    return is_homed(statusword) is True


class HomingJudge:
    """호밍 완료 2상 판정기.

    **bit15 가 1 인 것만 보면 안 된다** — 이전에 호밍을 마친 축은 시작 전부터 1 이라
    곧바로 완료로 읽힌다. 먼저 두 축이 0(진행 중)이 되는 것을 확인하고, 그 다음
    1 로 돌아오는 것을 기다린다. 0 을 한 번도 못 보면 성공이라고 하지 않는다.
    """

    def __init__(self, nodes, start_window_s: float = 10.0,
                 timeout_s: float = 90.0):
        self.nodes = tuple(nodes)
        self.start_window_s = float(start_window_s)
        self.timeout_s = float(timeout_s)
        self.started: set[int] = set()

    def update(self, status: dict, elapsed_s: float) -> tuple[Optional[bool], str]:
        """반환 `(결과, 사유)`. 결과 None = 아직 진행 중."""
        for n in self.nodes:
            homed = is_homed(status.get(n))
            if homed is False:
                self.started.add(n)
        all_started = set(self.nodes) <= self.started
        if not all_started:
            if elapsed_s >= self.start_window_s:
                missing = sorted(set(self.nodes) - self.started)
                return False, (f"개시 신호(bit15=0)를 못 봤습니다 — 노드 {missing}. "
                               f"움직이지 않았는지 육안으로 확인하세요.")
            return None, "개시 대기"
        if all(is_homed(status.get(n)) is True for n in self.nodes):
            return True, f"{elapsed_s:.0f}초 소요"
        if elapsed_s >= self.timeout_s:
            return False, f"{self.timeout_s:.0f}초 안에 완료 신호가 오지 않았습니다."
        return None, "호밍 진행 중"


def settled(target_deg: float, measured: dict, nodes, tol_deg: float) -> bool:
    """조향 정착 판정 — **모든 축**이 허용치 안에 들어와야 한다.

    crab 은 앞뒤가 같은 각이어야 성립하므로 한 축만 확인하면 뒷바퀴가 어긋난 채
    구동에 들어간다. 실측이 없는 축은 정착으로 치지 않는다.
    """
    for n in nodes:
        cur = measured.get(n)
        if cur is None or not finite(cur):
            return False
        if abs(target_deg - cur) > tol_deg:
            return False
    return True
