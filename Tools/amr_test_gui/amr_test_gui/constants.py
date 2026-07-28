"""실측 인용 상수 + GUI 로컬 정책값 **혼재** 파일.

⚠ 2026-07-27 정정(원문 보존): 원래 헤더는 ~~"실측 확정 상수 — 전량 정본 인용.
   본 파일에 새 값을 창작하지 않는다."~~ 였으나 본문과 어긋난다.
   반례: :43-44 `BODY_LENGTH`/`BODY_WIDTH` 는 "외형 근사치(시각화용, 실측 아님)" 이고,
         :50-55 §GUI 로컬 정책(DEFAULT_SPEED_MMPS·RAMP_STEP_DEG·RAMP_STEP_TIMEOUT_S·CMD_HZ)
         은 인용 없이 이 파일에서 새로 정한 값이다.
   → 헤더만 보고 이 파일 전체를 검증 면제로 취급하지 말 것. **절별 라벨을 반드시 확인**한다:
     §driver_node/§tongyi_amr.yaml/§docking_drive 인용분만 정본 대조 대상이고,
     §차체 기하 근사치·§GUI 로컬 정책은 실측이 아니다.

정본 위치(드리프트 시 test/test_constants.py 가 재도출로 차단한다):
  - `M_S_PER_UNIT`, `COUNTS_PER_RAD`, `COUNTS_PER_M`, `WHEEL_RADIUS`
      → src/Actuators/motor_control/motor_control/driver_node.py §실측 확정 상수
        (driver_node 는 rclpy 를 import 하므로 비-ROS 툴에서 직접 import 불가 → 값을 인용하고 테스트로 대조)
  - `STEER_HOME_COUNTS`, `DRIVE_NODES`, `STEER_NODES`, `VMAX_MPS`
      → src/Actuators/motor_control/config/tongyi_amr.yaml:32
        ⚠ 전원 사이클 거동 **미판정** — 같은 파일 :20-31 이 debt-007 미해소 모순으로 등록,
          :32 "debt-007 판정 전까지 무비판 신뢰 금지". 무비판 신뢰 금지.
        ※ 원문 괄호 ~~"(기동 캡처 실측, 전원 사이클 불변)"~~ 은 인용처가 실제로 하는 말이 아니다
          (yaml:29 "미판정 상태이므로 어느 쪽으로도 값을 고치지 않는다",
           yaml:30 "allow_homing_motion 게이트를 끄지 말 것 — 그 게이트가 이 불일치를 잡아내는 방어선").
          그 문구의 실제 출처는 src/Actuators/motor_control/motor_control/backend.py:36 이며,
          그것 역시 원출처 docs/ros2_driver/2026-07-09-design-inputs.md:81 의 조건
          (부팅 시 0x6064≈0 이 정상 + 매 기동 137.3° 브링업 스윙 필요)을 떼어낸 축약이다.
  - `VEL_PER_MMPS`, `VEL_MAX`
      → Tools/docking_field_kit/docking_drive.py (필드 실측 확정)
"""
from __future__ import annotations

import math

# ── driver_node.py 인용 ─────────────────────────────────────────────────────
M_S_PER_UNIT = 4.0906e-5                       # 1 unit(0.1 rpm) → m/s
COUNTS_PER_DEG = 57344.0                       # 조향 counts/° (protocol 실측)
COUNTS_PER_RAD = COUNTS_PER_DEG * 180.0 / math.pi
COUNTS_PER_M = 2670177.0                       # 구동 위치 counts/m
WHEEL_RADIUS = 0.125

# ── tongyi_amr.yaml 인용 ────────────────────────────────────────────────────
DRIVE_NODES = (1, 2)                           # 1=FrontWalk, 2=RearWalk (PV=3, 0x60FF)
STEER_NODES = (3, 4)                           # 3=FrontSteer, 4=RearSteer (PP=1, 0x607A+0x6040=0x3F)
# ⚠ 2026-07-27 정정(원 주석 ~~"0x6064 절대 counts, 전원 사이클 불변"~~ 은 오독을 부른다):
#   "전원 사이클 불변"은 **절대 목표 상수**(0x607A 로 지령할 값)에 대한 진술이며
#   (docs/ros2_driver/2026-07-09-design-inputs.md:56,81), 전원 인가 직후 0x6064 **판독값**이
#   이 값이라는 뜻이 **아니다**. 같은 정본 :56 은 "부팅 직후 전 노드 0x6064 ≈ 0 (홈값 아님, 정상)",
#   :81 은 "매 기동 시 브링업 스윙 필요" 라고 적는다.
#   현재 src/Actuators/motor_control/config/tongyi_amr.yaml:20-32 에 **미판정 모순(debt-007)** 으로
#   등록돼 있다(:32 "무비판 신뢰 금지"). 무비판 신뢰 금지 — 런타임은 controller.capture_home()
#   실측 캡처를 우선한다. 이 오독은 2026-07-27-002 사고(137° 스윙)와 같은 경로다
#   (docs/claude-mistake/2026-07-27-002_node4-unverified-command-damage.md).
#   판정에 필요한 측정: 전원 재인가 직후 조향 0x6064 를 판다 read 와 Seer 1040 으로 동시 채취해
#   어긋남이 (a) read 오염인지 (b) 호밍 후 드라이브 기준 재설정인지 구분(yaml:26-28).
STEER_HOME_COUNTS = {3: 7871815, 4: 7840086}   # 0x6064 절대 counts (값 불변 — 위 경고 참조)
VMAX_MPS = 0.2                                 # 안전 상한(기구 최대 1.23 m/s)
STEER_SETTLE_TOL_DEG = 3.0
HOMING_TOL_DEG = 5.0

# ── 차체 기하 (top-view 시각화 전용 — 제어에는 쓰이지 않음) ─────────────────
# 근거: References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md §1
#       (EasyDRIVE canID config 실측 노드 매핑)
#   | 1 FrontWalk  전 구동 x=+0.604 | 2 RealWalk  후 구동 x=−0.596 |
#   | 3 FrontSteer 전 조향 x=+0.604 | 4 RearSteer 후 조향 x=−0.596 |
# ⚠ config/tongyi_amr.yaml 의 module_x=[-0.5961, 0.6039] 은 이것과 전/후가 뒤집혀 있다
#   (docs/code_review/motor_control-can-consistency/2026-07-26.md §3 🔴HIGH, 미해결).
#   본 GUI 는 twist 변환을 쓰지 않아 제어에 영향이 없으므로, **그림에는 실측 정본**을 쓴다.
WHEEL_X = {1: +0.604, 2: -0.596, 3: +0.604, 4: -0.596}   # m, 차체 전방 +x
WHEEL_Y = -0.0014                                        # m, 센터라인 (좌 +y)
WHEELBASE = 1.200                                        # m = 0.604 + 0.596
DRIVE_TO_STEER = {1: 3, 2: 4}                            # 구동노드 → 같은 모듈의 조향노드
BODY_LENGTH = 1.60                                       # m — 외형 근사치(시각화용, 실측 아님)
BODY_WIDTH = 0.90                                        # m — 외형 근사치(시각화용, 실측 아님)

# ── docking_drive.py 인용 ───────────────────────────────────────────────────
VEL_PER_MMPS = 24.447                          # 0.1rpm units per (mm/s)
VEL_MAX_UNITS = 4889                           # ≈0.2 m/s 안전 상한

# ── GUI 로컬 정책(실측 아님 — 안전 여유값) ──────────────────────────────────
DEFAULT_SPEED_MMPS = 50.0                      # 저속 기본
MAX_SPEED_MMPS = VEL_MAX_UNITS / VEL_PER_MMPS  # ≈200 mm/s — VEL_MAX 에서 재도출
RAMP_STEP_DEG = 30.0                           # ±30 → ±60 → ±90 단계 램프
RAMP_STEP_TIMEOUT_S = 4.0
CMD_HZ = 20.0                                  # GUI → backend 지령 주기(backend 워치독 0.2 s 대비 4배 여유)


def mmps_to_units(mmps: float) -> int:
    """mm/s → 구동 raw units(0.1 rpm). VEL_MAX_UNITS 로 포화."""
    u = int(round(mmps * VEL_PER_MMPS))
    return max(-VEL_MAX_UNITS, min(VEL_MAX_UNITS, u))


def units_to_mps(units: float) -> float:
    """구동 raw units → m/s (backend ModuleCommand.velocity_mps 용)."""
    return units * M_S_PER_UNIT


def counts_to_deg(node: int, counts: int) -> float:
    """조향 노드의 0x6064 절대 counts → 홈 기준 각도(°)."""
    return (counts - STEER_HOME_COUNTS[node]) / COUNTS_PER_DEG
