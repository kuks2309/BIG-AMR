"""조향 단계 램프 — 전범위 급점프를 구조적으로 불가능하게 만드는 순수 상태기계.

⚠ **근거 등급 구분 (2026-07-28 추가)** — 이 절차는 **사용자가 지정한 시험 절차**이지
  이 시스템의 네이티브 지령 방식이 **아니다**. 실기 캡처가 반증한다:
  `Log/homing_capture_220350.jsonl` 에서 조향 지령 `0x607A` 는 노드당 6,464 프레임 중
  **서로 다른 값이 2 개뿐**이고, 실제 이동이 일어난 호밍 구간에는 write 가 **0 프레임**이다.
  Seer 는 최종 절대 목표를 반복 송신하고 이동 프로파일은 드라이브가 수행한다
  (`docs/verified_facts/2026-07-27.md` §A-8 결론 6).
  ⇒ 본 모듈을 "시스템이 요구하는 안전 인터록"으로 인용하지 말 것. 시험 절차의 구현일 뿐이다.
  경위: `docs/claude-mistake/2026-07-28-003`.

존재 이유(사고 회귀 방지):
  2026-07-27 세션에서 node4 를 전범위 급점프 지령해 137° 범위 밖으로 밀어 물리 갇힘 →
  직결 호밍 복구가 필요했다(docs/claude-mistake/2026-07-27-002). 본 모듈은 그 사고 유형을
  ① ±90° 하드 클램프 ② ≤step_deg 단계 전진 ③ 단계별 실측 추종 확인 ④ 미추종 시 FAULT 래치
  네 겹으로 막는다. Qt·CAN·시간원 무의존(now 를 주입받음) → 실차 없이 단위 테스트 가능.

램프 절차 근거: 사용자 지시 sess:56a709a5 "저각/단계 램프(±30→±60→±90) → 각 단계 실측 추종확인
→ 이탈 시 즉시 home", ~~실측 선례 Tools/docking_field_kit 계열 pc_crab_steer.py(단계 램프 +
추종 실패 시 home·중단)~~.

⚠ 2026-07-27 정정 — 위 취소선 인용은 **확인 불가**(원문은 이력 보존 위해 남긴다):
  `find . -name "pc_crab_steer*"` 가 저장소 전체에서 0건이고, Tools/docking_field_kit/ 및 폴백
  개발킷 ~/Project/CAN-Relay/docking_field_kit/ 목록에도 그런 파일이 없다(2026-07-27 확인).
  저장소 내 유일한 다른 언급인 docs/adr/2026-07-27-amr-test-gui.md:20 도 같은 미존재 파일을 가리킨다.
  → '단계 램프 + 추종 실패 시 home·중단' 이 실측 선례로 존재했는지 확인할 수 없다.
  본 절차의 1차 근거는 실재가 확인된 다음 둘이다:
    - docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md:47-49 §재발 방지 ①~④
    - 사용자 지시 sess:56a709a5 (위)
"""
from __future__ import annotations

from dataclasses import dataclass

# 조향 하드 리밋 — 이 값을 넘는 지령은 생성 자체가 불가능하다.
# 기구 한계는 ±140°(kinematics.STEER_LIMIT_RAD=2.443)이나, 실측 검증된 범위가 ±90°
# (홈↔90° = 5,160,960 counts, 양 부호 정상 확인)이므로 테스트 GUI 는 ±90° 로 좁힌다.
STEER_LIMIT_DEG = 90.0

# 상태
IDLE = "IDLE"          # 목표=지령=현재, 정착 대기 중 아님
RAMPING = "RAMPING"    # 단계 전진 중 — 구동 금지
SETTLED = "SETTLED"    # 목표 도달 + 실측 추종 확인 — 구동 허용
FAULT = "FAULT"        # 추종 실패 래치 — 홈 강제, 구동 금지, reset() 전까지 유지


@dataclass(frozen=True)
class RampOutput:
    """1 tick 결과. commanded_deg 를 그대로 조향 지령으로 쓰고, drive_allowed 로 구동을 게이트한다."""

    commanded_deg: float
    drive_allowed: bool
    state: str
    detail: str = ""


class SteerRamp:
    """조향 스칼라 1개(양 조향축 동일각)를 단계 램프로 안전하게 옮긴다.

    호출측 계약:
      - `set_target(deg)` 로 목표를 바꾸고, 주기적으로 `tick(measured_deg, now)` 를 호출한다.
      - 반환 `commanded_deg` 만 조향 지령으로 송신한다(목표를 직접 송신하면 안 된다 — 램프 우회).
      - `drive_allowed=False` 인 동안 구동 속도는 0 이어야 한다.
    """

    def __init__(self, *, step_deg: float = 30.0, settle_tol_deg: float = 3.0,
                 step_timeout_s: float = 4.0, limit_deg: float = STEER_LIMIT_DEG,
                 start_deg: float = 0.0):
        if step_deg <= 0:
            raise ValueError("step_deg 는 양수여야 한다")
        if settle_tol_deg <= 0:
            raise ValueError("settle_tol_deg 는 양수여야 한다")
        self.step_deg = float(step_deg)
        self.settle_tol_deg = float(settle_tol_deg)
        self.step_timeout_s = float(step_timeout_s)
        self.limit_deg = abs(float(limit_deg))
        self._cmd = self._clamp(start_deg)
        self._target = self._cmd
        self._state = IDLE
        self._detail = ""
        self._deadline: float | None = None   # None ⇒ 기한 감시 없음(정착 상태)
        self._last_now: float | None = None   # freeze() 의 기한 시계 정지에 사용

    # ── 공개 API ────────────────────────────────────────────────────────────
    def _clamp(self, deg: float) -> float:
        """하드 클램프 — 램프를 우회하는 어떤 경로로도 ±limit 를 넘길 수 없다."""
        return max(-self.limit_deg, min(self.limit_deg, float(deg)))

    def set_target(self, deg: float) -> float:
        """목표각 설정(클램프됨). FAULT 중에는 무시된다 — reset() 이 선행되어야 한다."""
        if self._state == FAULT:
            return self._target
        self._target = self._clamp(deg)
        return self._target

    def reset(self):
        """FAULT 래치 해제 — 운전자 명시 확인용. 목표를 현재 지령으로 되돌려 잔류목표 급발진을 막는다."""
        self._state = IDLE
        self._detail = ""
        self._deadline = None
        self._last_now = None
        self._target = self._cmd

    def freeze(self, now: float) -> RampOutput:
        """액추에이터가 지령을 따를 수 없는 구간(E-STOP 등)에서 램프를 동결한다.

        E-stop 중 backend 는 조향 신규 setpoint 송신을 억제하므로(정지 중 물리 스윙 방지) 실측이
        지령을 따라올 수 없다. 그 동안 기한 시계를 그대로 두면 **정상적인 E-STOP 조작이 항상
        추종 실패 FAULT 를 남긴다** — 진짜 고장 신호가 희석되므로 시계를 멈춘다.
        """
        if self._state == FAULT:
            self._cmd = 0.0
            self._last_now = now
            return RampOutput(0.0, False, FAULT, self._detail)
        if self._deadline is not None and self._last_now is not None:
            self._deadline += max(0.0, now - self._last_now)   # 기한 시계 정지
        self._last_now = now
        return RampOutput(self._cmd, False, self._state, "동결 — 램프 정지(E-STOP)")

    def tick(self, measured_deg: float | None, now: float) -> RampOutput:
        """1 주기 진행. measured_deg=None ⇒ 피드백 미수신(기한 초과 시 FAULT)."""
        self._last_now = now
        if self._state == FAULT:
            # 홈 강제 — 지령을 0 으로 눌러 둔다(사고 시 즉시 home 규칙).
            self._cmd = 0.0
            return RampOutput(0.0, False, FAULT, self._detail)

        if measured_deg is None:
            # 정착 상태에서 피드백이 끊기면 기한이 None 이라 감시 창이 안 열린다 →
            # 여기서 기한을 세워 '피드백 소실'도 반드시 FAULT 로 수렴시킨다.
            if self._deadline is None:
                self._deadline = now + self.step_timeout_s
            elif now > self._deadline:
                return self._fault(f"조향 피드백 미수신({self.step_timeout_s:.0f}s) — 지령 {self._cmd:+.1f}°")
            self._state = RAMPING if self._state == IDLE else self._state
            self._detail = "피드백 대기"
            return RampOutput(self._cmd, False, self._state, self._detail)

        err = abs(measured_deg - self._cmd)
        if err > self.settle_tol_deg:
            # 아직 현 단계 미정착 — 기한 내면 대기, 초과면 추종 실패로 확정한다.
            if self._deadline is None:
                self._deadline = now + self.step_timeout_s
            elif now > self._deadline:
                return self._fault(
                    f"조향 추종 실패 — 실측 {measured_deg:+.1f}° vs 지령 {self._cmd:+.1f}° "
                    f"(허용 {self.settle_tol_deg:.1f}°, {self.step_timeout_s:.0f}s 초과)")
            self._state = RAMPING
            self._detail = f"정착 대기 {measured_deg:+.1f}° → {self._cmd:+.1f}°"
            return RampOutput(self._cmd, False, RAMPING, self._detail)

        # 현 단계 정착 확인됨.
        remain = self._target - self._cmd
        if abs(remain) <= 1e-9:
            self._state = SETTLED
            self._deadline = None
            self._detail = f"목표 {self._target:+.1f}° 도달"
            return RampOutput(self._cmd, True, SETTLED, self._detail)

        # 다음 단계로 전진 — 한 번에 step_deg 를 넘지 않는다.
        advance = self.step_deg if remain > 0 else -self.step_deg
        if abs(remain) < self.step_deg:
            advance = remain
        self._cmd = self._clamp(self._cmd + advance)
        self._deadline = now + self.step_timeout_s
        self._state = RAMPING
        self._detail = f"단계 전진 → {self._cmd:+.1f}° (목표 {self._target:+.1f}°)"
        return RampOutput(self._cmd, False, RAMPING, self._detail)

    # ── 조회 ────────────────────────────────────────────────────────────────
    @property
    def state(self) -> str:
        return self._state

    @property
    def commanded_deg(self) -> float:
        return self._cmd

    @property
    def target_deg(self) -> float:
        return self._target

    @property
    def detail(self) -> str:
        return self._detail

    # ── 내부 ────────────────────────────────────────────────────────────────
    def _fault(self, reason: str) -> RampOutput:
        self._state = FAULT
        self._detail = reason
        self._deadline = None
        self._cmd = 0.0        # 즉시 home
        self._target = 0.0
        return RampOutput(0.0, False, FAULT, reason)
