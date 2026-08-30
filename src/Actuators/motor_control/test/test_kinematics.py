"""kinematics.py 단위 검증 — GUI kin_selftest 5케이스 이식 + DD + 정기구학 왕복."""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from motor_control.kinematics import (  # noqa: E402
    DiffDriveKinematics,
    DualSteerKinematics,
    ModuleCommand,
)

NODE_XY = {1: (-0.5961, -0.0014), 2: (+0.6039, -0.0014)}
VMAX = 0.2


def _kin():
    return DualSteerKinematics(NODE_XY, VMAX)


def _by_node(cmds):
    return {c.drive_node: c for c in cmds}


def test_forward():
    t = _by_node(_kin().twist_to_modules(0.1, 0, 0))
    assert all(abs(c.steer_rad) < 0.02 and abs(c.velocity_mps - 0.1) < 1e-3 for c in t.values())


def test_backward_folds_to_negative_velocity():
    t = _by_node(_kin().twist_to_modules(-0.1, 0, 0))
    assert all(abs(c.steer_rad) < 0.02 and abs(c.velocity_mps + 0.1) < 1e-3 for c in t.values())


def test_crab_left():
    t = _by_node(_kin().twist_to_modules(0, 0.1, 0))
    assert all(abs(c.steer_rad - math.pi / 2) < 0.02 and abs(c.velocity_mps - 0.1) < 1e-3
               for c in t.values())


def test_spin_ccw():
    t = _by_node(_kin().twist_to_modules(0, 0, 0.2))
    front, rear = t[2], t[1]  # x>0 = node2(가정), x<0 = node1
    assert abs(front.steer_rad - math.pi / 2) < 0.02 and front.velocity_mps > 0
    assert abs(rear.steer_rad + math.pi / 2) < 0.02 and rear.velocity_mps > 0


def test_saturation_keeps_ratio():
    t = _by_node(_kin().twist_to_modules(1.0, 0, 0))
    assert all(abs(abs(c.velocity_mps) - VMAX) < 1e-6 for c in t.values())


def test_roundtrip_twist():
    kin = _kin()
    for vx, vy, wz in [(0.1, 0, 0), (0, 0.08, 0), (0, 0, 0.15), (0.05, 0.03, 0.1)]:
        meas = {c.drive_node: (c.velocity_mps, c.steer_rad)
                for c in kin.twist_to_modules(vx, vy, wz)}
        rx, ry, rw = kin.modules_to_twist(meas)
        assert abs(rx - vx) < 1e-6 and abs(ry - vy) < 1e-6 and abs(rw - wz) < 1e-6


def test_diff_drive_covers_dd_type():
    dd = DiffDriveKinematics(1, 2, track_width=1.2, vmax=0.5)
    t = _by_node(dd.twist_to_modules(0.1, 0.5, 0.1))  # vy 무시
    assert t[1].steer_rad is None and t[2].steer_rad is None
    assert abs(t[1].velocity_mps - 0.04) < 1e-9 and abs(t[2].velocity_mps - 0.16) < 1e-9
    vx, vy, wz = dd.modules_to_twist({1: (0.04, 0.0), 2: (0.16, 0.0)})
    assert abs(vx - 0.1) < 1e-9 and vy == 0.0 and abs(wz - 0.1) < 1e-9


def test_diff_drive_saturation():
    dd = DiffDriveKinematics(1, 2, track_width=1.2, vmax=0.1)
    t = _by_node(dd.twist_to_modules(0.2, 0, 0))
    assert all(abs(c.velocity_mps - 0.1) < 1e-9 for c in t.values())


def test_module_command_is_one_set():
    c = ModuleCommand(1, 0.1, 0.5)
    assert (c.drive_node, c.velocity_mps, c.steer_rad) == (1, 0.1, 0.5)
