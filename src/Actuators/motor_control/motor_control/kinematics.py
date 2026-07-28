"""차체 Twist ↔ 휠 모듈 세트 변환 (순수 수학 — ROS·CAN 무의존).

모듈 세트 추상화(사용자 설계 지시 2026-07-09): 모듈 지령 = {구동속도 v[m/s], 조향각 θ[rad]|None}.
θ=None 모듈(조향축 없음)로 differential-drive 타입까지 동일 인터페이스로 커버한다.

역기구학 수식 근거: chassis_kin::inverse_multisteer 이식
  (ADR docs/adr/2026-07-09-kinviz-multisteer-to-drive-gui.md — 오라클 libOdoCalculator.so 대조 완전 일치)
  ⚠ 근거 상태(2026-07-27 감사): 위 "대조 완전 일치" 주장의 근거를 본 저장소에서 확인할 수 없다 —
    인용된 ADR 파일 부재(`find . -name "*kinviz*"` 0건, docs/adr/ 에는
    2026-07-09-motor-control-ros2-package.md 만 존재), 오라클 바이너리도 부재
    (`find . -name "*OdoCalculator*"` 0건). 저장소 내 언급은 모두 같은 끊긴 링크다
    (docs/adr/2026-07-09-motor-control-ros2-package.md:10, Tools/Kinematics/README.md:76,
     Tools/Kinematics/chassis_kinematics.py:10, driver_node.py:6).
    ⚠ 인용 좌표 정정 (2026-07-28 재대조) — 위 세 줄은 이력 보존용 원문이며, 괄호 안 좌표 2건과
      "docs/adr/ 에는 … 만 존재" 서술이 틀렸다(결론 자체는 유지된다 — 파일 부재는 재확인됨).
      · docs/adr/2026-07-09-motor-control-ros2-package.md **:10** → 실제 그 줄은 §배경의
        「`:84` "중간 조향각(0~90° 외) 지령 가능성 …"」이다. kinviz ADR 을 인용하는 줄은 **:28**
        「연속 역기구학 `kin_inverse` — [ADR 2026-07-09-kinviz-multisteer-to-drive-gui](…)
        (오라클 `libOdoCalculator.so` 대조 완전 일치 → Python 이식, 수학 selftest 5케이스 ✓)」이고,
        같은 문서 **:30** 은 이미 「`ls docs/adr/` 에 `2026-07-09-kinviz-multisteer-to-drive-gui.md`
        **없음**」이라고 부재를 기록해 둔다.
      · Tools/Kinematics/README.md **:76** → 실제 그 줄은 휠 기하(Roll_A084) 감사 주석이다.
        kinviz ADR 인용은 **:90** 「- ADR: `docs/adr/2026-07-09-kinviz-multisteer-to-drive-gui.md` …」.
      · Tools/Kinematics/chassis_kinematics.py **:10** ✓ 정확(「ADR: docs/adr/2026-07-09-kinviz-…md」),
        driver_node.py **:6** ✓ 정확(「⚠ 미검증 부호 가정 2건(… ADR 2026-07-09-kinviz-… §가정」).
      · 「docs/adr/ 에는 2026-07-09-motor-control-ros2-package.md 만 존재」는 사실이 아니다 —
        `ls docs/adr/` 결과 10개 파일이 있고(2026-07-20/24/26 ×4/27 ×3 포함), 그중 kinviz ADR 만 없다.
      · 누락된 in-tree 언급 1건 추가: src/Actuators/motor_control/README.md(§구조 — 역기구학 항목)도
        같은 ADR 을 인용하며 「**그 파일은 `docs/adr/` 에 존재하지 않는다**(2026-07-27 `ls` 확인 —
        근거 ADR 미이관)」이라 적는다. (그 README 는 동시 편집 중이라 줄번호 대신 문구로 인용한다.)
    docs/claude_guideline/reverse_engineering/principle.md §6 에 따라 이 검증 주장은 in-tree
    재확인 전까지 "확정"으로 취급하지 않는다. 해소 방법: 원 ADR 을 docs/adr/ 로 반입하거나,
    반입 불가면 오라클 출력 대조표를 test/test_kinematics.py 에 회귀 벡터로 고정.
  θᵢ = atan2(vy+ω·xᵢ, vx−ω·yᵢ), vᵢ = hypot(같은 성분), 비율 유지 포화, ±140° 초과 시 등가해 접기.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# 조향 한계 ±140°. 원 서술은 "(live_models.hpp:86 실측 config)" 였다.
# ⚠ 미판정 모순(2026-07-27 감사) — 값(2.443)은 실측 없이 바꾸지 않는다. 양쪽 근거:
#   · Seer 원본 config 상 기구 한계 ±140° (live_models.hpp:86). 단 그 원문은 본 저장소에 없고
#     (`find . -name "live_models*"` 0건), 이식 원본 Tools/Kinematics/chassis_kinematics.py:37 은
#     같은 상수를 "(live_models.hpp:86)" 로만 적어 '실측' 라벨이 없다 — 사본에서 라벨이 강해졌다.
#     ⚠ 인용 좌표 정정 (2026-07-28 재대조): 위 ":37" 은 틀렸다(그 줄은 KIN_NODE_XY 전/후 귀속
#       반증 주석이다). 실제 위치는 **chassis_kinematics.py:56** —
#       `STEER_LIMIT_RAD = 2.443         # 조향 한계 ±140° (live_models.hpp:86)`.
#       인용 내용('실측' 라벨 없이 live_models.hpp:86 만 적음)은 :56 에서 그대로 확인된다.
#   · 반대 기록: Tools/amr_test_gui/gui.py:36 `STEER_LIMIT_DEG = 90.0` "기구 한계는 ±140°이나 실측 검증된
#     (⚠ 2026-07-28: 원 인용 amr_test_gui/amr_test_gui/ramp.py:17-19 은 구 GUI 폐기로 삭제 — docs/adr/2026-07-28-old-gui-removal.md)
#     범위가 ±90°(홈↔90° = 5,160,960 counts)"; docs/claude-mistake/2026-07-27-002...md:17-18
#     node4 가 137°(정상 ±90° 범위 밖)로 밀려 물리적으로 갇힘(직결 호밍 복구 필요);
#     ⚠ 인용 좌표 정정 (2026-07-28 재대조) — 바로 위 두 좌표가 모두 틀렸다(인용 문구 자체는 실재).
#       · ramp.py **:17-19** → 그 줄은 pc_crab_steer 미존재 정정문이다. 실제 위치는 **:27-28**
#         「# 기구 한계는 ±140°(kinematics.STEER_LIMIT_RAD=2.443)이나, 실측 검증된 범위가 ±90°
#          # (홈↔90° = 5,160,960 counts, 양 부호 정상 확인)이므로 테스트 GUI 는 ±90° 로 좁힌다.」
#       · docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md **:17-18** →
#         그 줄은 「## 무엇을 했는가」 제목과 첫 문장이다. 인용 문구는 같은 절 **:19-20**
#         「그 결과 node4가 **물리적으로 137°(정상 ±90° 범위 밖)로 밀려 갇혔고**, 사용자가 CAN 직결
#          원점 호밍으로 복구해야 했다.」 (절 앵커: §무엇을 했는가)
#     ⚠ 정정 (2026-07-27, 실기 검증) — 바로 위 "node4 가 137°(정상 ±90° 범위 밖)" 는 이력 보존용
#       원문이며, **단위·기준계 혼동일 가능성이 높다**(미판정). 조향축에는 리밋 스위치가 실재하고
#       (전 노드 0x6098 = 1, Home 1 = 음의 리밋 트리거 [Handbook V7.0 §4.6 page 116 표]),
#       그 음 리밋을 원점으로 한 raw 좌표에서 **직진(θ=0)이 node3 +137.45° / node4 +137.05°**
#       (= 7,882,020 / 7,859,062 counts @57,344 counts/°)다.
#       근거: Log/homing_capture_220350.jsonl — 호밍 완료 후 0x607A 가 node3 7,882,020
#       @t=49.1402~179.993(6,072 회) / node4 7,859,062(6,319 회) 로 고정, EasyDRIVE
#       steerOffset 138.000 / 137.250 과 대응. ⇒ raw 137° 는 '범위 이탈'이 아니라 **홈(직진)**
#       일 수 있다. 조향각 θ(직진 기준)와 raw counts 각도를 구분해 재확인할 것.
#     ⚠ 비대칭 주의: 직진이 음 리밋 기준 +137° 부근이므로 음(−)측 여유는 약 137° 뿐이다.
#       STEER_LIMIT_RAD = 2.443(±140°)은 음측에서 리밋을 약 2.5° 초과한다(양측 대칭 가정 불가).
#     ※ 위 "직결 호밍 복구 필요" 서술도 함께 재해석할 것 — 콜드부팅 137° 조향 스윙 자체는
#       이상거동이 아니라 호밍 완료 후 원점(음 리밋)에서 조향 0° 로 복귀하는 설계된 이동이다.
#       ⚠ 과잉단정 정정 (2026-07-28) — 위 ※ 는 이력 보존용 원문이다. 「브링업 호밍 스윙은 설계된
#         이동」이라는 일반 명제는 in-tree 근거가 있으나(design-inputs.md §7 둘째 행 ⟦2026-07-27 해소⟧,
#         docs/adr/2026-07-09-motor-control-ros2-package.md:13-18), **mistake-002 의 node4 손상 사건을
#         그 스윙으로 대체 해석하는 것은 근거가 없다.** 같은 mistake 문서 §무엇을 했는가(:18-20)는
#         원인을 「부호/target을 실측·정본과 대조하지 않은 조향 지령(홈에서 큰 절대위치 점프)」으로
#         귀속하며, 브링업 호밍을 원인으로 적지 않는다. 두 사건의 동일성은 **미판정**이므로
#         "직결 호밍 복구 필요" 서술을 이 근거로 무효화하지 말 것.
#         (Handbook 인용 검증: `[Handbook V7.0 §4.6 page 116 표]` 는 ✓ 실재 대조됨 —
#          References/Tongyi-Motor-Controller/manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.txt
#          §4.6 Homing Operation, 페이지 푸터 115~116 사이 「Home 1: The home point is the negative
#          limit triggering signal」. 단 같은 원문 러닝 헤더는 "Handbook **V5.6**" 으로 파일명 V7.0 과
#          판본 표기가 다르다 — 판본 확정은 본 정정 범위 밖이며 어느 쪽으로도 단정하지 않는다.)
#     docs/ros2_driver/2026-07-09-design-inputs.md:45 "Seer 는 홈/90° 2상태만 사용 —
#     중간 조향각 연속 스워브는 미관측(⚠ §7)".
#     ⚠ 인용 좌표 정정 (2026-07-28 재대조): 위 ":45" 는 틀렸다(그 줄은 「## 1. 버스·노드」 제목이다).
#       인용 문구는 **§4 검증된 운동학 모델의 마지막 불릿(현재 :88)** 에 있다 —
#       「- Seer 는 홈/90° **2상태만** 사용 — 중간 조향각 연속 스워브는 미관측(⚠ §7)」.
#       ※ 이 문서는 스스로 :24-43 에서 「줄번호 이동 주의 … 인용은 가급적 줄번호 대신 **절 번호 +
#         원문 문구**로 할 것」이라고 경고하므로, 이후 인용은 절 앵커(§4)를 우선한다.
#   → 이 상수는 twist_to_modules 의 접기 임계이므로(아래 :45 부근), 90°~140° 구간의 조향각이
#     그대로 0x607A 지령이 된다(driver_node → backend, 램프·클램프 없음). 그 구간은 **미검증**.
#     ⚠ 인용 좌표 정정 (2026-07-28 재대조): 위 "(아래 :45 부근)" 은 본 파일의 옛 줄번호이며 현재는
#       틀렸다(감사 주석이 append 되며 밀렸다). 안정 앵커로 대체 —
#       **`DualSteerKinematics.twist_to_modules` 의 `if abs(th) > self.steer_limit_rad:` 분기**.
#       "램프·클램프 없음" 은 재대조로 확인된다(두 파일 모두 동시 편집 중이라 앵커로 인용한다):
#       · driver_node.py `_on_cmd_vel()` 은 `vx = max(-g["vmax"], min(g["vmax"], msg.linear.x))` 식으로
#         vx/vy/wz 만 vmax·wmax 로 클램프하고 **조향각 클램프는 없다**.
#       · backend.py `set_command()` 은
#         `mod.steer_home + self.steer_sign * cmd.steer_rad * self.counts_per_rad` 를 그대로
#         0x607A 목표로 쓴다(클램프되는 것은 구동 속도 `vel_limit_units` 뿐).
#   판정에 필요한 측정: 잭업 상태에서 홈→95°→…→140° 단계 램프로 각 단계 0x6064 추종·
#                      기계 스토퍼 접촉 여부 확인.
STEER_LIMIT_RAD = 2.443


@dataclass(frozen=True)
class ModuleCommand:
    """휠 모듈 1개 지령 세트. steer_rad=None ⇒ 고정 조향(DD 타입)."""

    drive_node: int
    velocity_mps: float
    steer_rad: float | None = None


class DualSteerKinematics:
    """듀얼 스티어(스워브) — Tongyi AMR: 전/후 모듈 각각 구동+조향."""

    def __init__(self, node_xy: dict[int, tuple[float, float]], vmax: float,
                 steer_limit_rad: float = STEER_LIMIT_RAD):
        self.node_xy = dict(node_xy)  # 구동노드 → 차체좌표 (x, y) m
        self.vmax = float(vmax)
        self.steer_limit_rad = float(steer_limit_rad)

    def twist_to_modules(self, vx: float, vy: float, wz: float) -> list[ModuleCommand]:
        """차체 (vx, vy[m/s], ω[rad/s]) → 모듈 지령 세트 (inverse_multisteer 이식)."""
        raw = {}
        vpeak = 0.0
        for n, (xi, yi) in self.node_xy.items():
            ax = vx - wz * yi
            ay = vy + wz * xi
            th = math.atan2(ay, ax)
            v = math.hypot(ax, ay)
            if abs(th) > self.steer_limit_rad:  # 접기 후 |θ'|=π−|θ|<40° — 항상 한계 내
                th -= math.copysign(math.pi, th)
                v = -v
            raw[n] = [th, v]
            vpeak = max(vpeak, abs(v))
        if vpeak > self.vmax > 0:  # 비율 유지 포화
            f = self.vmax / vpeak
            for n in raw:
                raw[n][1] *= f
        return [ModuleCommand(n, v, th) for n, (th, v) in sorted(raw.items())]

    def modules_to_twist(self, measured: dict[int, tuple[float, float]]) -> tuple[float, float, float]:
        """정기구학(오도메트리): {구동노드: (v_i[m/s], θ_i[rad])} → (vx, vy, ω) 최소제곱해.

        모듈별 속도벡터 (v·cosθ, v·sinθ) = (vx−ω·yᵢ, vy+ω·xᵢ) 를 3미지수 LSQ 로 푼다.
        입력이 변위(Δs)면 반환도 변위 스케일 — 호출측 dt 일관 유지.
        """
        # 정규방정식 AᵀA·[vx,vy,ω]ᵀ = Aᵀb 를 닫힌형으로 구성
        s_n = 0.0
        s_y = s_x = 0.0
        s_xx_yy = 0.0
        b1 = b2 = b3 = 0.0
        for n, (v, th) in measured.items():
            xi, yi = self.node_xy[n]
            mx = v * math.cos(th)
            my = v * math.sin(th)
            s_n += 1.0
            s_y += yi
            s_x += xi
            s_xx_yy += xi * xi + yi * yi
            b1 += mx
            b2 += my
            b3 += -yi * mx + xi * my
        # AᵀA = [[N, 0, −Σy], [0, N, Σx], [−Σy, Σx, Σ(x²+y²)]]
        a11, a13 = s_n, -s_y
        a22, a23 = s_n, s_x
        a33 = s_xx_yy
        det = a11 * (a22 * a33 - a23 * a23) - a13 * (a13 * a22)
        if abs(det) < 1e-12:
            return (0.0, 0.0, 0.0)
        vx = ((a22 * a33 - a23 * a23) * b1 + (a13 * a23) * b2 + (-a13 * a22) * b3) / det
        vy = ((a13 * a23) * b1 + (a11 * a33 - a13 * a13) * b2 + (-a11 * a23) * b3) / det
        wz = ((-a13 * a22) * b1 + (-a11 * a23) * b2 + (a11 * a22) * b3) / det
        return (vx, vy, wz)


class DiffDriveKinematics:
    """차동 구동(DD) — 조향축 없음(steer_rad=None). 동일 ModuleCommand 인터페이스."""

    def __init__(self, left_node: int, right_node: int, track_width: float, vmax: float):
        self.left_node = left_node
        self.right_node = right_node
        self.track_width = float(track_width)
        self.vmax = float(vmax)

    def twist_to_modules(self, vx: float, _vy: float, wz: float) -> list[ModuleCommand]:
        """(vx, ω) → 좌/우 바퀴 속도. vy 는 비홀로노믹이라 무시."""
        vl = vx - wz * self.track_width / 2.0
        vr = vx + wz * self.track_width / 2.0
        vpeak = max(abs(vl), abs(vr))
        if vpeak > self.vmax > 0:
            f = self.vmax / vpeak
            vl, vr = vl * f, vr * f
        return [ModuleCommand(self.left_node, vl, None), ModuleCommand(self.right_node, vr, None)]

    def modules_to_twist(self, measured: dict[int, tuple[float, float]]) -> tuple[float, float, float]:
        """{노드: (v_i, _)} → (vx, 0, ω)."""
        vl = measured[self.left_node][0]
        vr = measured[self.right_node][0]
        return ((vl + vr) / 2.0, 0.0, (vr - vl) / self.track_width)
