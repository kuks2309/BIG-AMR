"""Where a robot stands to let another past.

`_sidestep_target` is a pure function of two poses, and it produced the only
robot-to-robot CONTACT ever measured in this project — 0.90 m body gap between
amr2 and amr3 on 2026-08-10, against a 1.20 m avoidance target. It had no tests
at all, which is why a geometry bug survived in a function that could have been
checked in milliseconds.

Two defects, both fixed here:

  * the aisle was chosen by PROXIMITY IN Y, tested first. Where two aisles meet
    both tests pass, so a robot on the west cross aisle was treated as being on
    the south aisle and sent along the aisle it was driving on instead of off it.
  * the standoff never considered where the robot being yielded to was, so it
    could sit on the far side of it — a head-on approach dressed up as a lay-by.

These build a bare SimRobot with `object.__new__`: the real constructor needs a
live ROS node, publishers and subscriptions, none of which this arithmetic
touches. Requiring them is what kept this function untested.
"""

import math

import pytest

from csm import plant
from csm.adapters.sim_acs import (SimRobot, SIDESTEP, PATH_CLEARANCE,
                                  _point_seg)


def robot(pose, goal=None):
    """A robot that knows only where it is and where it is heading."""
    r = object.__new__(SimRobot)
    r.pose = pose
    r._goal = goal
    r.fleet = None
    return r


def heading(frm, to):
    """A goal far enough along a direction to fix the travel vector."""
    return (frm[0] + to[0] * 10.0, frm[1] + to[1] * 10.0)


# ------------------------------------------------- the aisle is the one we drive

def test_east_west_travel_steps_sideways_in_y():
    pose = (-8.0, plant.AISLE_S_Y, 0.0)
    r = robot(pose, heading(pose, (1.0, 0.0)))          # driving east

    gx, gy = r._sidestep_target()

    assert gx == pytest.approx(pose[0]), "must not move along the aisle"
    assert gy == pytest.approx(plant.AISLE_S_Y + SIDESTEP), "off the aisle, toward the hall centre"


def test_north_south_travel_steps_sideways_in_x():
    pose = (plant.AISLE_W_X, -6.0, 0.0)
    r = robot(pose, heading(pose, (0.0, 1.0)))          # driving north

    gx, gy = r._sidestep_target()

    assert gy == pytest.approx(pose[1]), "must not move along the cross aisle"
    assert gx == pytest.approx(plant.AISLE_W_X + SIDESTEP), "off the cross aisle, toward the centre"


def test_the_corner_that_caused_the_contact():
    """The measured case: on the west cross aisle, 1.07 m from the south aisle.

    Old behaviour returned (x, -1.0) — 3 m north, straight up the cross aisle
    the robot was driving on. Logged eight times as
    `[amr3] stepping aside to (-19.4,-1.0)` while amr2 sat at y = -2.70 in that
    exact path.
    """
    pose = (-19.36, -4.07, 0.0)
    r = robot(pose, heading(pose, (0.0, 1.0)))          # driving north, up the cross aisle

    gx, gy = r._sidestep_target()

    assert gy == pytest.approx(pose[1]), \
        "stepped ALONG the cross aisle — this is the bug that caused contact"
    assert gx > pose[0], "must move off the cross aisle, away from the wall"
    assert abs(gy - (-1.0)) > 1.0, "must not be the old (x, -1.0) answer"


def test_proximity_no_longer_beats_direction_of_travel():
    """Being near an east-west aisle line does not make it the aisle we are on."""
    pose = (plant.AISLE_W_X + 0.4, plant.AISLE_S_Y - 1.0, 0.0)
    r = robot(pose, heading(pose, (0.0, -1.0)))         # driving south

    gx, gy = r._sidestep_target()

    assert gy == pytest.approx(pose[1]), "direction of travel decides the axis"
    assert gx != pytest.approx(pose[0])


# ------------------------------------------------------- never aim at the partner

def test_a_standoff_is_not_chosen_through_the_robot_being_passed():
    pose = (plant.AISLE_W_X, -4.0, 0.0)
    r = robot(pose, heading(pose, (0.0, 1.0)))
    # Partner sitting exactly on the default standoff side.
    blocked = (plant.AISLE_W_X + SIDESTEP, -4.0, 0.0)
    other = robot(blocked)

    goal = r._sidestep_target(other)

    assert _point_seg(other.pose[:2], pose[:2], goal) >= PATH_CLEARANCE, \
        "the chosen path passes within the distance layer 1 refuses to close"


def test_the_clear_side_is_kept_when_the_partner_is_elsewhere():
    pose = (plant.AISLE_W_X, -4.0, 0.0)
    r = robot(pose, heading(pose, (0.0, 1.0)))
    far = robot((5.0, 5.0, 0.0))

    goal = r._sidestep_target(far)

    assert goal == pytest.approx((plant.AISLE_W_X + SIDESTEP, -4.0)), \
        "a partner nowhere near must not change the preferred side"


def test_a_partner_without_a_pose_is_not_a_crash():
    pose = (-8.0, plant.AISLE_N_Y, 0.0)
    r = robot(pose, heading(pose, (1.0, 0.0)))
    ghost = robot(None)

    goal = r._sidestep_target(ghost)

    assert goal == pytest.approx((pose[0], plant.AISLE_N_Y - SIDESTEP))


def test_both_sides_fouled_picks_the_further_one_rather_than_driving_at_it():
    pose = (plant.AISLE_W_X, -4.0, 0.0)
    r = robot(pose, heading(pose, (0.0, 1.0)))
    # Partner right on top of us: every candidate path is too close.
    other = robot((plant.AISLE_W_X, -4.2, 0.0))

    goal = r._sidestep_target(other)

    d_chosen = math.hypot(goal[0] - other.pose[0], goal[1] - other.pose[1])
    mirrored = (plant.AISLE_W_X - SIDESTEP, -4.0)
    preferred = (plant.AISLE_W_X + SIDESTEP, -4.0)
    d_other = min(math.hypot(c[0] - other.pose[0], c[1] - other.pose[1])
                  for c in (mirrored, preferred))
    assert d_chosen >= d_other, "must move away from the partner, not toward it"


# ------------------------------------------------------------------- fallback

def test_no_heading_falls_back_to_the_nearer_aisle_comparing_both_axes():
    """An idle robot has no goal, so there is no direction to use.

    The old fallback tested y first and returned on the first match, which is
    the same first-match bug. Both axes must be compared.
    """
    pose = (plant.AISLE_E_X, -9.0, 0.0)      # far from any east-west aisle line
    r = robot(pose, None)

    gx, gy = r._sidestep_target()

    assert gy == pytest.approx(pose[1]), "nearest line here is the east cross aisle"
    assert gx == pytest.approx(plant.AISLE_E_X - SIDESTEP)
