"""실측 확정 상수 — 전량 정본 인용. 본 파일에 새 값을 창작하지 않는다.

정본 위치(드리프트 시 test/test_constants.py 가 재도출로 차단한다):
  - `M_S_PER_UNIT`, `COUNTS_PER_RAD`, `COUNTS_PER_M`, `WHEEL_RADIUS`
      → src/Actuators/motor_control/motor_control/driver_node.py §실측 확정 상수
        (driver_node 는 rclpy 를 import 하므로 비-ROS 툴에서 직접 import 불가 → 값을 인용하고 테스트로 대조)
  - `STEER_HOME_COUNTS`, `DRIVE_NODES`, `STEER_NODES`, `VMAX_MPS`
      → src/Actuators/motor_control/config/tongyi_amr.yaml (기동 캡처 실측, 전원 사이클 불변)
  - `VEL_PER_MMPS`, `VEL_MAX`
      → Tool/docking_field_kit/docking_drive.py (필드 실측 확정)
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
STEER_HOME_COUNTS = {3: 7871815, 4: 7840086}   # 0x6064 절대 counts, 전원 사이클 불변
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
