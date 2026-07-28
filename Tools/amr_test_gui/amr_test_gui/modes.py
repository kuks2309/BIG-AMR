"""주행 모드 = (조향각, 구동 raw 부호) 인용·도출 테이블.

⚠ 이 파일이 방향 의미의 유일한 소유자다. backend 는 `drive_sign=+1`·`steer_sign=+1` 항등 변환으로
   구성되므로(ADR 2026-07-27-amr-test-gui §3), 여기 적힌 부호가 그대로 CAN 에 나간다.

## 확정 실측 2건 (직접 관측 — 이 둘만이 1차 근거다)

| # | 조향 counts 각 | 구동 raw | 관측된 이동 | 출처 |
| - | --- | --- | --- | --- |
| ① | 0°(홈)  | 음수 | 전진 (+x) | docking_drive.py:93 `{1:-s,2:-s} # 전진=음(실측)` · tongyi_amr.yaml:14 `drive_sign:-1` |
| ② | +90°    | 양수(+2445) | 왼쪽 (+y) | 2026-07-27 실측, IMU ay 출발+1.0/정지−1.6 |

## 도출 모델 (①② 를 동시에 만족하는 유일한 해석)

바퀴 지향 = `(cos θ, −sin θ)` — 즉 **조향 +counts = CW(−θ)**.
이동 방향 = `−sign(raw) × 바퀴 지향`.

  - ① θ=0, raw 음수 → −(−1)·(1, 0) = (+1, 0) = 전진 ✓
  - ② θ=+90, raw 양수 → −(+1)·(0, −1) = (0, +1) = 왼쪽 ✓

**+counts = CCW 해석은 ② 에 의해 반증된다** (그 경우 θ=+90 의 지향이 (0,+1) 이 되어
raw 양수의 이동이 (0,−1) = 오른쪽이 되고, 실측과 반대가 된다).

## verified 의 의미

- `verified=True` — 그 (조향각, raw 부호) 조합 자체가 **직접 관측**됐거나, 관측된 조합에서
  구동 raw 부호만 반전한 것(속도지령 부호 반전 = 회전방향 반전).
- `verified=False` — 위 **도출 모델**을 거쳐 나온 조합. 모델은 ①②와 정합하나 그 각도에서
  직접 관측된 적은 없다. UI 에 ⚠ 로 노출되며, 저속 1회 육안 확인으로 승격해야 한다.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriveMode:
    key: str
    label: str            # UI 버튼 라벨
    arrow: str            # 방향 패드 기호
    steer_deg: float      # 양 조향축 공통 목표각(홈 기준 counts 각)
    raw_sign: int         # 구동 raw 부호 (0 = 정지)
    basis: str            # 근거 — UI 툴팁·로그에 그대로 표시
    verified: bool        # 직접 실측(또는 raw 부호 반전)인가


STOP = DriveMode(
    key="stop", label="정지", arrow="■", steer_deg=0.0, raw_sign=0,
    basis="속도 0 — 부호 무관", verified=True)

# ── 4방위: 직접 실측 계열 ───────────────────────────────────────────────────
FORWARD = DriveMode(
    key="forward", label="전진", arrow="↑", steer_deg=0.0, raw_sign=-1,
    basis="직접 실측 ① — 조향 홈 + raw 음수 = 전진", verified=True)

BACKWARD = DriveMode(
    key="backward", label="후진", arrow="↓", steer_deg=0.0, raw_sign=+1,
    basis="실측 ① 의 raw 부호 반전", verified=True)

CRAB_LEFT = DriveMode(
    key="crab_left", label="좌 크랩", arrow="←", steer_deg=+90.0, raw_sign=+1,
    basis="직접 실측 ② — 조향 +90° + raw 양수 = 왼쪽(+y), IMU ay 실증", verified=True)

CRAB_RIGHT = DriveMode(
    key="crab_right", label="우 크랩", arrow="→", steer_deg=+90.0, raw_sign=-1,
    basis="실측 ② 의 raw 부호 반전", verified=True)

# ── 대각 45° 크랩: 도출 계열 (직접 관측 없음) ───────────────────────────────
CRAB_FL = DriveMode(
    key="crab_fl", label="좌전 45°", arrow="↖", steer_deg=-45.0, raw_sign=-1,
    basis="도출 — 모델 −sign(raw)·(cosθ,−sinθ) 로 (+x,+y) 를 얻는 해", verified=False)

CRAB_FR = DriveMode(
    key="crab_fr", label="우전 45°", arrow="↗", steer_deg=+45.0, raw_sign=-1,
    basis="도출 — 모델로 (+x,−y) 를 얻는 해", verified=False)

CRAB_RL = DriveMode(
    key="crab_rl", label="좌후 45°", arrow="↙", steer_deg=+45.0, raw_sign=+1,
    basis="도출 — 모델로 (−x,+y) 를 얻는 해", verified=False)

CRAB_RR = DriveMode(
    key="crab_rr", label="우후 45°", arrow="↘", steer_deg=-45.0, raw_sign=+1,
    basis="도출 — 모델로 (−x,−y) 를 얻는 해", verified=False)

# ── 비주행 ──────────────────────────────────────────────────────────────────
STEER_ONLY = DriveMode(
    key="steer_only", label="조향만", arrow="↻", steer_deg=0.0, raw_sign=0,
    basis="구동 0 — 조향 단독 시험(슬라이더 각도 사용)", verified=True)

# ⚠ 2026-07-27 정정 — 원 basis 는 ~~"STEER_HOME counts 복귀 — tongyi_amr.yaml:20 실측(전원 사이클 불변)"~~
#   이었으나 인용처와 정면으로 어긋난다:
#     - tongyi_amr.yaml:20 은 값이 있는 줄이 아니라 그 반대 취지의 경고 줄이다
#       ("⚠ 미해소 모순 (2026-07-27 관측, debt-007) — 아래 값을 쓰기 전에 반드시 읽을 것.")
#     - 실제 값은 같은 파일 :32 이고 "⚠ debt-007 판정 전까지 무비판 신뢰 금지" 가 붙어 있다.
#   이 문자열은 내부 주석이 아니라 운전자에게 그대로 노출되므로(ui_main.py:230-232 툴팁,
#   ui_main.py:586 "근거:" 라벨, controller.py:165 로그) 미판정 표시로 정정한다.
#   verified 플래그·steer_deg 값은 손대지 않는다(동작 변경 없음).
#   판정에 필요한 측정: 전원 재인가 직후 조향 0x6064 를 판다 read + Seer 1040 동시 채취(yaml:26-28).
HOME = DriveMode(
    key="home", label="HOME", arrow="⌂", steer_deg=0.0, raw_sign=0,
    basis="STEER_HOME counts 복귀 — tongyi_amr.yaml:32 값. "
          "⚠ 전원 사이클 거동은 미판정 모순(debt-007, yaml:20-31) — "
          "런타임 capture_home() 캡처값 우선", verified=True)


ALL_MODES = (STOP, FORWARD, BACKWARD, CRAB_LEFT, CRAB_RIGHT,
             CRAB_FL, CRAB_FR, CRAB_RL, CRAB_RR, STEER_ONLY, HOME)
BY_KEY = {m.key: m for m in ALL_MODES}

# 방향 패드 3×3 배치 (row, col) → 모드 key. 중앙은 정지.
PAD_LAYOUT = {
    (0, 0): "crab_fl", (0, 1): "forward",  (0, 2): "crab_fr",
    (1, 0): "crab_left", (1, 1): "stop",   (1, 2): "crab_right",
    (2, 0): "crab_rl", (2, 1): "backward", (2, 2): "crab_rr",
}


def motion_unit_vector(mode: DriveMode) -> tuple[float, float]:
    """모드의 예상 이동 방향 단위벡터 (x 전방, y 좌) — 위 도출 모델 그대로.

    ⚠ 이는 **모델 예측**이지 실측이 아니다. 4방위는 실측과 일치함이 확인됐고,
    대각 4개는 예측만 있다(`verified=False`). 시각화의 예상 화살표에만 쓴다.
    """
    import math
    if mode.raw_sign == 0:
        return (0.0, 0.0)
    th = math.radians(mode.steer_deg)
    px, py = math.cos(th), -math.sin(th)      # 바퀴 지향 (+counts = CW)
    s = -mode.raw_sign
    return (s * px, s * py)
