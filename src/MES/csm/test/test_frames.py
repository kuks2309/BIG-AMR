"""World-frame error must be rotated into the body frame before commanding.

Twist.linear is a BODY velocity. The exit leg fed it a world-frame direction,
which coincides with the body frame at yaw 0 and is exactly REVERSED at yaw 180.
That is why it looked intermittent: the same code drove a robot correctly out of
one bay and into a wall out of the next.

Measured before the fix — amr2, exit goal to the south-east, yaw -178.5:
    t+319  (-16.4, +3.0)  driving away from its wait spot
    t+344  (-21.8, +12.5) stopped only by the corner
"""

import math

import pytest

from csm.adapters.sim_acs import _to_body


def test_at_yaw_zero_the_frames_coincide():
    """Why the bug hid: at yaw 0 the wrong code gave the right answer."""
    assert _to_body(1.0, 0.0, 0.0) == pytest.approx((1.0, 0.0))
    assert _to_body(0.0, 1.0, 0.0) == pytest.approx((0.0, 1.0))


def test_at_yaw_180_the_command_is_reversed():
    """The failure: driving north-west when the goal is south-east."""
    bx, by = _to_body(1.0, 0.0, math.pi)
    assert bx == pytest.approx(-1.0)
    assert by == pytest.approx(0.0, abs=1e-9)


def test_facing_the_goal_always_means_drive_forward():
    """Whatever the heading, a goal dead ahead must command +x and nothing else."""
    for deg in range(0, 360, 15):
        yaw = math.radians(deg)
        ex, ey = math.cos(yaw), math.sin(yaw)          # goal straight ahead
        bx, by = _to_body(ex, ey, yaw)
        assert bx == pytest.approx(1.0), f"yaw {deg}"
        assert by == pytest.approx(0.0, abs=1e-9), f"yaw {deg}"


def test_the_rotation_preserves_distance():
    for deg in range(0, 360, 30):
        bx, by = _to_body(3.0, -4.0, math.radians(deg))
        assert math.hypot(bx, by) == pytest.approx(5.0)


def test_a_goal_to_the_left_commands_positive_y():
    bx, by = _to_body(0.0, 1.0, 0.0)        # due north, robot facing east
    assert by == pytest.approx(1.0)
    bx, by = _to_body(-1.0, 0.0, math.pi / 2)   # robot facing north, goal west
    assert by == pytest.approx(1.0), "west is to the left of a north-facing robot"


# --------------------------------------------------- squaring up to a machine

from csm import plant                                          # noqa: E402
from csm.adapters.sim_acs import _parallel_heading, _wrap       # noqa: E402


def test_parallel_to_a_north_row_machine_is_along_the_aisle():
    """North-row markers look south, so parallel is due east or due west."""
    marker_yaw = plant.MARKERS["ASRS"][2]
    for current, expect in ((0.0, 0.0), (math.pi, math.pi)):
        got = _parallel_heading(marker_yaw, current)
        assert abs(_wrap(got - expect)) == pytest.approx(0.0, abs=1e-9)


def test_it_takes_the_nearer_of_the_two_parallel_headings():
    """Both dock equally well — never turn 180 deg for a symmetric result."""
    marker_yaw = plant.MARKERS["ASRS"][2]
    got = _parallel_heading(marker_yaw, math.radians(170))
    assert abs(_wrap(got - math.pi)) < math.radians(1), "should pick 180, not 0"
    got = _parallel_heading(marker_yaw, math.radians(10))
    assert abs(_wrap(got)) < math.radians(1), "should pick 0, not 180"


def test_the_turn_needed_is_never_more_than_ninety_degrees():
    """'It should rotate only 90 degrees' — never further, from any heading."""
    for name in ("ASRS", "GRV2_ULD", "CTR1_LD", "SLT_LD3"):
        marker_yaw = plant.MARKERS[name][2]
        for deg in range(-180, 181, 5):
            cur = math.radians(deg)
            turn = abs(_wrap(_parallel_heading(marker_yaw, cur) - cur))
            assert turn <= math.pi / 2 + 1e-9, f"{name} at {deg} deg: {turn}"


@pytest.mark.parametrize("tilt_deg,reach", [(0, 0.450), (5, 0.518), (11.4, 0.599)])
def test_tilt_costs_reach_and_eats_the_docking_gap(tilt_deg, reach):
    """Why parallel matters: a tilted robot touches before its centre arrives.

    Square on it presents its half-width into a 0.229 m gap. Measured at 11.4
    deg the corner reached the machine face while the centre still read 0.60 m.
    """
    t = math.radians(tilt_deg)
    got = 0.45 * math.cos(t) + 0.8 * math.sin(t)
    assert got == pytest.approx(reach, abs=0.002)
    gap = plant.DOCK_TARGET - plant.ROBOT_HALF_WIDTH
    if tilt_deg > 10:
        assert got - 0.45 > gap * 0.5, "a 11 deg tilt spends most of the gap"
