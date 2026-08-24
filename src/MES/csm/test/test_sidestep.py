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
    # DERIVED FROM THE PLANT, not written down. The measured pose was
    # (-19.36, -4.07) when the west aisle was at x -20.0 — 0.64 m east of it
    # and 1.07 m south of the south aisle. The aisle moved on 2026-08-21 and a
    # hard-coded x quietly stopped being "on the cross aisle" at all, so the
    # test passed the wrong pose and failed for the wrong reason. What matters
    # here is the RELATIVE position, so that is what is written.
    pose = (plant.AISLE_W_X + 0.64, plant.AISLE_S_Y - 1.07, 0.0)
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


def test_every_candidate_fouled_reports_no_lay_by():
    """Nowhere to go must be said, not approximated.

    This used to return "the one furthest from the partner", on the reasoning
    that moving away beats driving at it. Where the partner is between us and
    that whole side — which is the only case that reaches here — the furthest
    candidate is the one deepest THROUGH it. The robot then stood still until
    YIELD_LIMIT failed its job. `None` lets the fleet hand the yield to the
    other robot instead; see test_cannot_yield.py.
    """
    pose = (plant.AISLE_W_X, -4.0, 0.0)
    r = robot(pose, heading(pose, (0.0, 1.0)))
    # Partner right on top of us: every candidate path is too close.
    other = robot((plant.AISLE_W_X, -4.2, 0.0))

    assert r._sidestep_target(other) is None


# ------------------------------------------- the aisle we are ON, not only the
# ------------------------------------------- direction we happen to be facing

def test_turning_off_an_aisle_still_steps_off_that_aisle():
    """The 2026-08-24 deadlock, in one call.

    amr2 stood on the north aisle at (-9.6, +3.9) and had turned north toward
    GRV1_ULD, so its goal vector read north-south. The candidates became
    x-offsets from AISLE_W_X and the nearest lay-by on offer was 10.4 m west —
    on the far side of amr1, the robot it was yielding to. Neither robot moved
    again until YIELD_LIMIT failed both their jobs.

    A lay-by must be somewhere the robot can actually reach, and here that is
    the perpendicular step off the aisle it is standing on.
    """
    pose = (-9.6, 3.9, 0.0)
    r = robot(pose, heading(pose, (0.0, 1.0)))       # turned north to its port
    partner = robot((-11.7, 3.1, 0.0))               # amr1, 2.25 m to the west

    goal = r._sidestep_target(partner)

    assert goal is not None, "there was a clear lay-by 1.1 m away"
    assert math.hypot(goal[0] - pose[0], goal[1] - pose[1]) < 3.0, \
        "a lay-by must be a step aside, not a journey"
    assert _point_seg(partner.pose[:2], pose[:2], goal) >= PATH_CLEARANCE, \
        "must never aim through the robot we are yielding to"
    assert not r._blocks_path(partner, pose[0], pose[1], goal), \
        "and must not pick a path the partner is standing in"


def test_the_preferred_axis_still_wins_when_it_is_usable():
    """Trying both axes must not disturb the ordinary case.

    The heading still chooses which pair to offer first. It only stops being
    the last word when every candidate in that pair is unreachable.
    """
    pose = (-8.0, plant.AISLE_S_Y, 0.0)
    r = robot(pose, heading(pose, (1.0, 0.0)))       # driving east
    far = robot((5.0, 12.0, 0.0))

    gx, gy = r._sidestep_target(far)

    assert gx == pytest.approx(pose[0])
    assert gy == pytest.approx(plant.AISLE_S_Y + SIDESTEP)


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


# ------------------------------------ a lay-by is unreachable whoever is in it

def test_a_third_robot_standing_in_the_lay_by_rules_it_out():
    """The 2026-08-24 three-robot jam.

    amr4, yielding to amr2, chose the north lay-by. amr2 did not block it —
    but amr3 did, and amr3 was there precisely BECAUSE of this encounter:
    `_yielder_ahead` holds a queuer back so the passer gets the gap, and where
    it holds is often the lay-by itself. amr4 stopped with "robot ahead on the
    road" for eighty seconds while amr2 waited as the passer.

    The south lay-by was clear of both and was never considered, because only
    the partner was asked about.
    """
    class Fleet:
        def __init__(self, robots):
            self.robots = robots

    yielder = robot((-13.44, -2.98, 0.0), heading((-13.44, -2.98), (-1.0, 0.0)))
    partner = robot((-15.33, -2.99, 0.0))
    third = robot((-14.22, -1.52, 0.0))          # queueing, sat in the north lay-by
    yielder.fleet = Fleet([yielder, partner, third])

    goal = yielder._sidestep_target(partner)

    assert goal is not None, "the south lay-by was free"
    assert goal[1] < -2.98, "must go SOUTH, away from the robot in the north one"
    assert not yielder._blocks_path(third, -13.44, -2.98, goal)
    assert not yielder._blocks_path(partner, -13.44, -2.98, goal)
