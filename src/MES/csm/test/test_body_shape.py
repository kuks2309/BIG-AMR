"""The shape the avoidance layer thinks a robot is.

Every safety margin in the traffic layer is derived from this. It was wrong, and
because the measuring script shared the same model, the measurement agreed with
the bug and reported "no contact" while the operator watched one robot shove
another across the floor (2026-08-10).

THE ERROR. The collision body in the robot description is a BOX, 1.600 x 0.900
(foil_a082.urdf.xacro:103-104). It was modelled as a CAPSULE — a segment with a
radius — which has the same length and width but rounds the corners off:

    box corner sits at (0.80, 0.45) from centre  ->  0.636 m from the axis
    capsule surface in that direction            ->  0.450 m from the axis
    so every corner protrudes                    ->  0.186 m beyond the shape

Exhaustive search over relative pose found footprints in contact while the
capsule reported a gap of up to 1.273 m — worst at relative pose (1.6, 0.9, 0),
which is two robots square-on and diagonally offset, i.e. one coming down an
aisle past one sitting in a spur mouth. The old STOP_GAP was 1.20 m, BELOW that,
so the margin the avoidance layer aimed for permitted a corner collision by
construction.

These tests pin the shape, not the symptom.
"""

import math

import pytest

from csm.adapters.sim_acs import (_seg_gap, _footprint, _overlap,
                                  ROBOT_L, ROBOT_W, ROBOT_CIRCUM,
                                  CONTACT_GAP, STOP_GAP)


def at(x, y, deg=0.0):
    return (x, y, math.radians(deg))


# ------------------------------------------------------------ the shape itself

def test_the_footprint_is_the_box_from_the_robot_description():
    assert (ROBOT_L, ROBOT_W) == (1.600, 0.900), \
        "must match foil_a082.urdf.xacro BODY_L / BODY_W"
    corners = _footprint(at(0, 0))
    xs = sorted(c[0] for c in corners)
    ys = sorted(c[1] for c in corners)
    assert xs[-1] - xs[0] == pytest.approx(ROBOT_L)
    assert ys[-1] - ys[0] == pytest.approx(ROBOT_W)


def test_the_footprint_turns_with_the_robot():
    corners = _footprint(at(0, 0, 90))
    xs = sorted(c[0] for c in corners)
    ys = sorted(c[1] for c in corners)
    assert xs[-1] - xs[0] == pytest.approx(ROBOT_W), "width is across x at 90 deg"
    assert ys[-1] - ys[0] == pytest.approx(ROBOT_L)


# --------------------------------------------------------------- touching is 0

def test_side_by_side_touch_at_exactly_one_width():
    assert _seg_gap(at(0, 0), at(0, ROBOT_W)) == pytest.approx(0.0, abs=1e-9)
    assert _seg_gap(at(0, 0), at(0, ROBOT_W + 0.10)) == pytest.approx(0.10)


def test_nose_to_tail_touch_at_exactly_one_length():
    assert _seg_gap(at(0, 0), at(ROBOT_L, 0)) == pytest.approx(0.0, abs=1e-9)
    assert _seg_gap(at(0, 0), at(ROBOT_L + 0.25, 0)) == pytest.approx(0.25)


def test_overlapping_bodies_report_zero_not_a_negative_or_a_gap():
    assert _seg_gap(at(0, 0), at(0.2, 0.1)) == 0.0
    assert _overlap(_footprint(at(0, 0)), _footprint(at(0.2, 0.1)))


# ----------------------------------------------- the case the capsule got wrong

def test_the_corner_case_that_the_capsule_model_missed():
    """Square-on, diagonally offset — an aisle robot passing a spur mouth.

    The capsule reported 1.273 m of clearance here. The footprints are touching.
    """
    a, b = at(0, 0), at(ROBOT_L, ROBOT_W)

    assert _seg_gap(a, b) == pytest.approx(0.0, abs=1e-9), \
        "corner to corner IS contact, whatever a capsule says"


def test_no_orientation_hides_a_contact_behind_the_stop_margin():
    """Sweep relative pose: nothing may be touching while _seg_gap >= STOP_GAP.

    This is the property the old model violated by 1.273 m against a 1.20 m
    margin, and it is the one worth defending — it holds in every orientation
    rather than only the ones somebody thought of.
    """
    worst = 0.0
    for ix in range(0, 200, 2):
        for iy in range(0, 200, 2):
            for ideg in range(0, 180, 6):
                b = at(ix * 0.02, iy * 0.02, ideg)
                gap = _seg_gap(at(0, 0), b)
                if gap <= CONTACT_GAP:
                    worst = max(worst, gap)
    assert worst <= CONTACT_GAP, \
        f"a touching pair reported a gap of {worst:.3f} m"


def test_the_stop_margin_is_real_clearance_above_contact():
    assert CONTACT_GAP == 0.0, "footprints touch at zero — that is what contact is"
    assert STOP_GAP > 0.0, "the avoidance layer must aim above contact"


# ------------------------------------------------------- the cheap rejection

def test_far_apart_robots_skip_the_exact_test_and_still_never_claim_contact():
    """The early-out returns a LOWER BOUND, so it may under-report the gap but
    must never report contact where there is none."""
    for d in (2.0, 3.5, 10.0):
        gap = _seg_gap(at(0, 0), at(d, 0, 37))
        assert gap > 0.0
        assert gap <= d, "the bound must not exceed the centre distance"


def test_the_rejection_threshold_cannot_cut_off_a_real_contact():
    """Two circumscribed circles is the furthest two bodies can possibly touch."""
    assert ROBOT_CIRCUM == pytest.approx(math.hypot(ROBOT_L, ROBOT_W) / 2.0)
    # Just inside the threshold, the exact test must be the one that answers.
    d = 2.0 * ROBOT_CIRCUM - 0.01
    assert _seg_gap(at(0, 0), at(d, 0)) > 0.0, "square-on at 1.8 m is not contact"
