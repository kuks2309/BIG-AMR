"""상수 드리프트 차단 — constants.py 의 인용값을 정본 파일에서 **재도출**해 대조한다.

정본이 바뀌었는데 인용본이 안 바뀌면 여기서 깨진다(자기보고가 아니라 재도출이므로 속일 수 없다).
"""
import os
import re
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..")))
REPO = os.path.normpath(os.path.join(_HERE, "..", "..", ".."))

from amr_test_gui import constants as C  # noqa: E402

DRIVER_NODE = os.path.join(REPO, "src/Actuators/motor_control/motor_control/driver_node.py")
CONFIG_YAML = os.path.join(REPO, "src/Actuators/motor_control/config/tongyi_amr.yaml")
DOCKING = os.path.join(REPO, "Tool/docking_field_kit/docking_drive.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _assign(text, name):
    """`NAME = <숫자 리터럴>` 의 우변을 float 로 돌려준다 (eval 미사용 — ⟦CI:banned-pattern⟧)."""
    m = re.search(rf"^{name}\s*=\s*([0-9][0-9eE.+\-]*)", text, re.M)
    assert m, f"정본에서 {name} 을 숫자 리터럴로 찾지 못했습니다"
    return float(m.group(1))


@pytest.mark.parametrize("name,ours", [
    ("M_S_PER_UNIT", C.M_S_PER_UNIT),
    ("COUNTS_PER_M", C.COUNTS_PER_M),
    ("WHEEL_RADIUS", C.WHEEL_RADIUS),
])
def test_driver_node_constants_match(name, ours):
    assert _assign(_read(DRIVER_NODE), name) == pytest.approx(ours, rel=1e-12)


def test_counts_per_rad_matches_driver_node():
    """driver_node 는 `57344.0 * 180.0 / math.pi` 로 정의한다 — 값이 동일해야 한다."""
    txt = _read(DRIVER_NODE)
    m = re.search(r"^COUNTS_PER_RAD\s*=\s*([0-9.]+)\s*\*\s*180\.0\s*/\s*math\.pi", txt, re.M)
    assert m, "driver_node.py 의 COUNTS_PER_RAD 정의 형태가 바뀌었습니다"
    assert float(m.group(1)) == pytest.approx(C.COUNTS_PER_DEG)


def test_steer_home_counts_match_config():
    txt = _read(CONFIG_YAML)
    m = re.search(r"steer_home_counts:\s*\[([0-9]+),\s*([0-9]+)\]", txt)
    assert m, "tongyi_amr.yaml 에서 steer_home_counts 를 찾지 못했습니다"
    assert C.STEER_HOME_COUNTS[3] == int(m.group(1))
    assert C.STEER_HOME_COUNTS[4] == int(m.group(2))


def test_node_mapping_matches_config():
    txt = _read(CONFIG_YAML)
    drive = re.search(r"module_drive_nodes:\s*\[([0-9]+),\s*([0-9]+)\]", txt)
    steer = re.search(r"module_steer_nodes:\s*\[([0-9]+),\s*([0-9]+)\]", txt)
    assert tuple(int(g) for g in drive.groups()) == C.DRIVE_NODES
    assert tuple(int(g) for g in steer.groups()) == C.STEER_NODES


@pytest.mark.parametrize("name,ours", [
    ("VEL_PER_MMPS", C.VEL_PER_MMPS),
    ("COUNTS_PER_DEG", C.COUNTS_PER_DEG),
])
def test_docking_kit_constants_match(name, ours):
    assert _assign(_read(DOCKING), name) == pytest.approx(ours)


def test_vel_max_matches_docking_kit():
    assert _assign(_read(DOCKING), "VEL_MAX") == C.VEL_MAX_UNITS


def test_vel_max_is_consistent_with_vmax_mps():
    """VEL_MAX_UNITS(4889) 와 VMAX_MPS(0.2) 가 M_S_PER_UNIT 로 서로 정합해야 한다."""
    assert C.VEL_MAX_UNITS * C.M_S_PER_UNIT == pytest.approx(C.VMAX_MPS, rel=1e-3)


def test_unit_conversions_round_trip():
    for mmps in (10.0, 50.0, 199.0):
        u = C.mmps_to_units(mmps)
        assert C.units_to_mps(u) == pytest.approx(mmps / 1000.0, rel=2e-3)


def test_mmps_to_units_saturates_at_vel_max():
    assert C.mmps_to_units(10_000.0) == C.VEL_MAX_UNITS
    assert C.mmps_to_units(-10_000.0) == -C.VEL_MAX_UNITS


def test_counts_to_deg_zero_at_home():
    for n, home in C.STEER_HOME_COUNTS.items():
        assert C.counts_to_deg(n, home) == 0.0
        assert C.counts_to_deg(n, home + int(90 * C.COUNTS_PER_DEG)) == pytest.approx(90.0)
