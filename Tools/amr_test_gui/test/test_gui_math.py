"""`tongyi_can.py` 순수 환산 회귀 — 하드웨어·Qt 창 없이 돈다.

구 GUI 폐기(docs/adr/2026-07-28-old-gui-removal.md)로 테스트 84건이 함께 사라졌다.
본 파일은 debt-011 의 1차 상환으로, **실기에서 틀리면 로봇이 움직이는** 값들을 고정한다.

인용 정본
  · 조향 57,344 counts/° · 홈↔90° Δ = 5,160,960 counts (정확히 90.00°)
      docs/ros2_driver/2026-07-09-design-inputs.md §3 스케일 표
  · 구동 ±2445 = 0.10 m/s · VEL_MAX 4889
      Tools/docking_field_kit 실측 관례 (tongyi_can.py `VEL_PER_MMPS` 주석)
  · 조향 가동범위 ±90° = 실측 검증 범위 (기구 한계 ±140° 는 Roll_A084 config 값)
      docs/claude-mistake/2026-07-27-002 — 범위 밖 지령으로 node4 물리 갇힘
  · 조그 방향표의 1차 근거는 직접 실측 2건뿐 (tongyi_can.py `JOG` 주석)
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")   # import 만으로 창을 열지 않도록

from tongyi_can import (COUNTS_PER_DEG, JOG, STEER_HOME,   # noqa: E402
                        STEER_LIMIT_DEG, VEL_MAX_UNITS,
                        drive_units, steer_counts)

NODES = (3, 4)
DELTA_90 = 5_160_960          # 실측: 홈 ↔ 90° = 정확히 90.00°


# ── 조향 환산 ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("node", NODES)
def test_zero_deg_is_exactly_home(node):
    """0° 지령은 홈 counts 와 **정확히** 같아야 한다 — 여기서 어긋나면 전 각도가 어긋난다."""
    deg, counts = steer_counts(node, 0.0)
    assert deg == 0.0
    assert counts == STEER_HOME[node]


@pytest.mark.parametrize("node", NODES)
def test_ninety_deg_matches_measured_delta(node):
    """+90° 는 실측 Δ=5,160,960 counts 와 일치해야 한다(정본 스케일 재도출)."""
    _, counts = steer_counts(node, 90.0)
    assert counts - STEER_HOME[node] == DELTA_90
    assert DELTA_90 == 90 * COUNTS_PER_DEG          # 스케일 상수 자체도 함께 고정


@pytest.mark.parametrize("node", NODES)
@pytest.mark.parametrize("deg", [-90.0, -45.0, 0.0, 45.0, 90.0])
def test_sign_is_symmetric_about_home(node, deg):
    """±같은 각은 홈을 중심으로 대칭이어야 한다."""
    _, pos = steer_counts(node, deg)
    _, neg = steer_counts(node, -deg)
    assert (pos - STEER_HOME[node]) == -(neg - STEER_HOME[node])


@pytest.mark.parametrize("node", NODES)
@pytest.mark.parametrize("deg", [90.001, 137.0, 140.0, 1e6, float("inf")])
def test_beyond_range_is_clamped_not_sent(node, deg):
    """가동범위 밖은 **잘려서** 나가야 한다 — node4 137° 갇힘 사고(2026-07-27-002)의 재발 방지."""
    applied, counts = steer_counts(node, deg)
    assert applied == STEER_LIMIT_DEG
    assert counts == STEER_HOME[node] + DELTA_90
    applied_n, counts_n = steer_counts(node, -deg)
    assert applied_n == -STEER_LIMIT_DEG
    assert counts_n == STEER_HOME[node] - DELTA_90


@pytest.mark.parametrize("node", NODES)
def test_137_deg_never_reaches_the_bus(node):
    """사고 당시의 137° 가 그대로 counts 로 환산되는 일이 없어야 한다."""
    _, counts = steer_counts(node, 137.0)
    assert counts != STEER_HOME[node] + int(137.0 * COUNTS_PER_DEG)


# ── 구동 환산 ──────────────────────────────────────────────────────────────
def test_100mmps_matches_measured_unit():
    """실측 관례 ±2445 = 0.10 m/s 를 재도출한다."""
    assert drive_units(100.0, -1) == -2445
    assert drive_units(100.0, +1) == +2445


def test_zero_speed_is_zero_both_signs():
    assert drive_units(0.0, -1) == 0
    assert drive_units(0.0, +1) == 0


@pytest.mark.parametrize("mmps", [200.0, 500.0, 10_000.0])
def test_speed_is_clamped_to_max(mmps):
    """상한을 넘겨도 VEL_MAX 를 벗어나지 않는다."""
    assert drive_units(mmps, +1) == VEL_MAX_UNITS
    assert drive_units(mmps, -1) == -VEL_MAX_UNITS


# ── 조그 방향표 ────────────────────────────────────────────────────────────
def test_every_jog_angle_is_inside_range():
    """표에 가동범위 밖 각이 섞여 들어가지 못하게 한다."""
    for label, (deg, _, _) in JOG.items():
        assert abs(deg) <= STEER_LIMIT_DEG, label


def test_measured_entries_are_the_documented_two_pairs():
    """직접 실측 근거 2건(과 그 부호 반전)만 verified=True 여야 한다."""
    measured = {k for k, v in JOG.items() if v[2]}
    assert measured == {"전진", "후진", "좌 크랩", "우 크랩"}
    assert JOG["전진"][:2] == (0.0, -1)      # ① 조향 0° + raw 음수 → 전진
    assert JOG["좌 크랩"][:2] == (90.0, +1)  # ② 조향 +90° + raw 양수 → 좌 (IMU 실증)


@pytest.mark.parametrize("a,b", [("전진", "후진"), ("좌 크랩", "우 크랩"),
                                 ("좌전 45°", "우후 45°"), ("우전 45°", "좌후 45°")])
def test_opposite_pairs_invert_exactly_one_of_angle_or_sign(a, b):
    """반대 방향 쌍은 조향각·구동부호 중 정확히 하나만 뒤집혀야 한다."""
    da, sa, _ = JOG[a]
    db, sb, _ = JOG[b]
    flipped = (da == -db and da != 0.0, sa == -sb)
    assert sum(flipped) == 1, (a, b, JOG[a], JOG[b])
