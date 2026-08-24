"""The red light behind a robot that is standing aside.

THE JAM THIS PREVENTS, observed live on 2026-08-21 with four robots.

amr3 and amr4 were travelling west together; amr2 was coming east. amr3 was
told to stand aside for amr2 and pulled off into its lay-by. amr4 did not stop
— it drove PAST amr3 and took the road directly in front of amr2. Now amr4 was
the one that had to yield, with amr3 parked beside it and amr2 in front of it,
and nowhere left to go.

Measured at the moment it stuck:

    amr2  (-5.32, -3.00)  facing east   giving way to amr4
    amr4  (-3.52, -3.02)  facing west   giving way to amr2
    amr3  (-3.56, -1.39)  parked in its lay-by, junction held

All three stopped. Nothing would have broken it except YIELD_LIMIT, forty-five
seconds later, which resolves it by FAILING A JOB.

WHY IT HAPPENED. `_threat` sees only closing geometry — it stops for anything
whose gap would close below STOP_GAP. A robot standing aside is stationary, so
the gap to it never closes, so it never stops anybody. That is correct for a
robot that has turned off to its dock, and wrong for one holding a gap open.

A robot leaves the lane for two reasons and they need opposite treatment:

    giving way   holding a gap for ONE named robot   -> nobody else may pass
    docking      gone to its own port                -> traffic carries on

From outside they look identical. The difference is why, and only the fleet
knows that.

These tests drive the geometry directly. No ROS, no poses being integrated —
the question is arithmetic over two positions and a heading, and it should be
answerable in milliseconds rather than by waiting for three robots to meet at
the wrong place.
"""

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters.sim_acs import (QUEUE_LOOKAHEAD, SimAcs,        # noqa: E402
                                  SimRobot, STOP_GAP)


class FakeLogger:
    def info(self, message): pass
    def warn(self, message): pass


class FakeNode:
    def get_logger(self): return FakeLogger()


def robot(name, x, y, heading, goal=None):
    """A SimRobot with only what the traffic rules read.

    Built without __init__ for the same reason `test_traffic.py` does it: the
    real one needs a live ROS node, publishers and subscriptions, none of which
    take part in the rule under test.

    ⚠ `_goal`, not the heading, is what direction of travel comes from — the
    platform crabs, so where it points and where it moves are different things.
    A test that set only the yaw would be testing nothing.
    """
    r = object.__new__(SimRobot)
    r.name = name
    r.node = FakeNode()
    r.pose = (x, y, heading)
    r.vel = (0.0, 0.0)
    r._goal = goal if goal is not None else (
        (x + 10.0, y) if abs(heading) < 1.0 else (x - 10.0, y))
    r._stood_aside = False
    r._junction = None
    r.fleet = None
    return r


def fleet(*robots):
    acs = object.__new__(SimAcs)
    acs.node = FakeNode()
    acs.robots = list(robots)
    acs._junctions = {}
    acs._giving_way = {}
    acs._occupied = {}
    acs._results = {}
    acs._last_log = 0.0
    for r in robots:
        r.fleet = acs
    return acs


WEST, EAST = math.pi, 0.0


def the_jam():
    """The three robots as they actually were, before amr4 went past.

    amr4 is placed BEHIND amr3 rather than level with it — the question is
    whether it is allowed to close that gap, which is the decision that went
    wrong live.
    """
    amr2 = robot("amr2", -5.32, -3.00, EAST)     # oncoming, will be passed
    amr3 = robot("amr3", -3.56, -1.39, WEST)     # standing aside, in its lay-by
    amr4 = robot("amr4", -1.00, -3.00, WEST)     # following amr3, still on road
    acs = fleet(amr2, amr3, amr4)
    acs.who_yields(amr3, amr2)                   # amr3 is the yielder
    assert acs.yielding(amr3), "amr3 should be the one standing aside"
    return acs, amr2, amr3, amr4


# ------------------------------------------------------------- the fix


def test_a_follower_stops_behind_a_robot_that_is_giving_way():
    """amr4 must not go past amr3. This is the whole bug."""
    _, _, amr3, amr4 = the_jam()
    assert amr4._yielder_ahead() is amr3


def test_the_passer_drives_through_the_gap():
    """amr2 is who the gap was made for. It must NOT be held."""
    _, amr2, _, _ = the_jam()
    assert amr2._yielder_ahead() is None, \
        "the robot being given way to was stopped by the gap made for it"


def test_a_robot_that_has_already_passed_is_not_held():
    """Once beyond the yielder there is nothing to queue behind."""
    _, _, amr3, amr4 = the_jam()
    # put amr4 west of amr3, i.e. past it in its direction of travel
    amr4.pose = (-6.00, -3.00, WEST)
    assert amr4._yielder_ahead() is None


def test_a_robot_far_back_carries_on_normally():
    """No stopping half an aisle away from something it cannot act on yet."""
    _, _, _, amr4 = the_jam()
    amr4.pose = (-3.56 + QUEUE_LOOKAHEAD + 5.0, -3.00, WEST)
    assert amr4._yielder_ahead() is None


def test_the_light_goes_out_when_the_encounter_ends():
    """amr3 rejoins, and amr4 is free again — no lingering block."""
    acs, _, amr3, amr4 = the_jam()
    assert amr4._yielder_ahead() is amr3
    acs.encounter_over(amr3)
    assert amr4._yielder_ahead() is None


# ------------------------------- the distinction that caused the bug


def test_a_robot_off_the_lane_for_ITS_OWN_reasons_does_not_block():
    """A robot at a dock is not giving way, so traffic passes it.

    This is the case `_threat`'s "a robot standing still is ignored" comment
    was written for, and it must keep working — otherwise nothing could ever
    drive past a docked robot.
    """
    amr2 = robot("amr2", -5.32, -3.00, EAST)
    docked = robot("amr3", -3.56, -1.39, WEST)   # same spot, but NOT yielding
    amr4 = robot("amr4", -1.00, -3.00, WEST)
    acs = fleet(amr2, docked, amr4)
    assert not acs.yielding(docked)
    assert amr4._yielder_ahead() is None, \
        "a docked robot must not stop the traffic behind it"


def test_the_queue_forms_at_the_same_gap_as_every_other_stop():
    """One number for "how close is too close", not two."""
    _, _, amr3, amr4 = the_jam()
    amr4.pose = (-3.56 + 0.9 + STOP_GAP / 2.0, -3.00, WEST)   # inside STOP_GAP
    assert amr4._yielder_ahead() is amr3


# ------------------------------------------------- the cascade behind it


def test_a_third_robot_queues_behind_the_second():
    """A queue forms without any code for queues.

    amr5 stops because amr4 has stopped, and amr4 stopped for amr3. Nothing
    counts the queue or orders it — each robot only ever looks at what is in
    front of it.
    """
    acs, _, amr3, amr4 = the_jam()
    amr5 = robot("amr5", 1.50, -3.00, WEST)
    acs.robots.append(amr5)
    amr5.fleet = acs
    # amr5 is behind amr4, which is behind amr3: the yielder is still what it
    # ultimately queues on, and it is inside the lookahead.
    assert amr4._yielder_ahead() is amr3
    assert amr5._yielder_ahead() is amr3


def test_a_robot_with_no_goal_is_not_held():
    """An idle robot has no direction of travel, so "ahead" is meaningless."""
    _, _, _, amr4 = the_jam()
    amr4._goal = None
    assert amr4._yielder_ahead() is None
