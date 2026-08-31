"""A robot with no job obeys the same rules as one with a job.

THE PRINCIPLE (user, 2026-08-31): "whatever AMR it is, it should obey all the
rules we have."

It did not. `_go_home` drove to a point without ever setting `_goal`, and half
the rule set is written against that field:

    `_travel_dir`     -> None, so `_could_still_reach` is False, so RULE 2
                         never held a robot driving home
    `_note_turning`   -> returns early, so a homing robot never claimed a turn
    the 3 m rule      -> guarded by `_goal is not None`

and `_final_leg` read `_waypoints`, which is empty while homing, so it
answered True for the whole trip and pinned the heading the entire way. The
robot therefore crabbed home — backwards across the plant if its bay was
behind it — and arrived pointing anywhere.

Measured 2026-08-31: 1C4 sat at yaw 123 deg on the inner lane, 56 deg across
the road, `_turning` False, with 1C1 queued behind it on the 3 m rule.
"""

import math

import pytest

from csm import plant
from csm.adapters.sim_acs import ROADS, SimRobot


def homing(name, x, y, yaw=0.0, waypoints=None):
    """A robot on its way to park: no job, no route, only a home list."""
    r = object.__new__(SimRobot)
    r.name = name
    r.pose = (x, y, yaw)
    r.vel = (0.0, 0.0)
    r.fleet = None
    r._active_job = None
    r._leg = r._from = r._to = None
    r._goal = None
    r._waypoints = []
    r._homing = True
    r._home_waypoints = list(waypoints or [(0.0, plant.AISLE_S_Y), (30.0, -1.5)])
    r._pausing_in = r._pausing_out = False
    r._turning = False
    r._pause_goal = None
    r._crossing_lane = None
    r._exit_goal = None
    r._exit_station = None
    r._left_station = None
    r._halt_reason = None
    # The steering constants are __init__ arguments, and this robot is built
    # without __init__ on purpose. Their defaults, from `SimRobot.__init__`.
    r.turn_gain, r.max_turn, r.crab_window = 1.6, 0.9, 0.5
    return r


def test_the_final_leg_is_about_the_route_the_robot_is_actually_on():
    """`_waypoints` is empty while homing, so the old test said True for the
    whole trip — and `_note_turning` reads it."""
    far = homing("amr3", -20.0, plant.AISLE_S_Y,
                 waypoints=[(0.0, plant.AISLE_S_Y), (30.0, -1.5)])
    near = homing("amr3", 28.0, -1.5, waypoints=[(30.0, -1.5)])

    assert far._final_leg is False, "two hops to go is not the final leg"
    assert near._final_leg is True


def test_a_homing_robot_claims_its_turn():
    """RULE 4. It never did, because `_final_leg` was always True."""
    r = homing("amr3", -20.0, plant.AISLE_S_Y, yaw=math.pi / 2,
               waypoints=[(0.0, plant.AISLE_S_Y), (30.0, -1.5)])
    r._goal = r._home_waypoints[0]          # what `_go_home` now sets

    r._note_turning()

    assert r._turning is True, "90 deg off its path and not claiming a turn"


def test_a_homing_robot_can_be_held_by_a_robot_leaving_a_dock():
    """RULE 2. `_could_still_reach` needs a travel direction, and a travel
    direction needs a goal."""
    r = homing("amr3", -20.0, plant.AISLE_S_Y,
               waypoints=[(0.0, plant.AISLE_S_Y)])

    assert r._could_still_reach((0.0, plant.AISLE_S_Y)) is False, \
        "with no goal there is no direction, and rule 2 cannot see it"

    r._goal = r._home_waypoints[0]          # what `_go_home` now sets

    assert r._could_still_reach((0.0, plant.AISLE_S_Y)) is True


def test_go_home_sets_the_goal():
    """Wired in, not merely possible."""
    import inspect

    from csm.adapters import sim_acs

    src = inspect.getsource(sim_acs.SimRobot._go_home)

    assert "self._goal = goal" in src, \
        "_go_home must set _goal or half the rules skip this robot"


def test_the_homing_drive_steers():
    """It commanded linear.x and linear.y and no rotation at all, so a robot
    whose bay was behind it drove backwards the whole way."""
    import inspect

    from csm.adapters import sim_acs

    src = inspect.getsource(sim_acs.SimRobot._drive_toward)

    assert "angular.z" in src, "the homing path must steer like the job leg"
    assert "_in_a_bay()" in src and "_on_a_spur()" in src, \
        "and it must keep the job leg's exemptions — turning sweeps 0.918 m"
