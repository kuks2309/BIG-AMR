"""A robot that cannot move must not be given work.

On 2026-08-18 amr3's spawn_entity hung. Its controllers and wheel bridge never
started, so it sat immobile in its bay — but it had a valid pose from Gazebo
ground truth, which exists as soon as a model is spawned. The dispatcher saw a
free robot with a pose, gave it a job, and amr2 manoeuvred into it.

The launch timing that triggered that has been widened, but timing only makes
the race rarer. These tests cover the part that makes the state observable.
"""

import pytest

from csm.adapters.sim_acs import SimRobot


def robot(joints_stamp, now=100.0, battery=100.0):
    """A SimRobot with only what `can_move` reads.

    Built without __init__ for the same reason test_traffic.py does it: the
    real one needs a live ROS node, publishers and subscriptions, none of which
    take part in this rule.
    """
    r = object.__new__(SimRobot)
    r._joints_stamp = joints_stamp
    r._now = lambda: now
    # `can_move` reads the battery too — a robot with no charge cannot drive
    # anywhere, whatever its controllers are doing.
    r.battery = battery
    return r


def test_a_robot_that_never_reported_joint_states_cannot_move():
    """The exact amr3 case: spawned, has a pose, controllers never started."""
    assert not robot(None).can_move


def test_a_robot_reporting_joint_states_can_move():
    assert robot(99.5).can_move


def test_a_control_chain_that_has_gone_quiet_counts_as_dead():
    """Covers the chain dying, not just failing to start.

    joint_state_broadcaster publishes continuously while controllers are up, so
    a gap this long means it is no longer running.
    """
    assert not robot(100.0 - SimRobot.CONTROLLERS_TIMEOUT_S).can_move


def test_just_inside_the_timeout_is_still_alive():
    assert robot(100.0 - SimRobot.CONTROLLERS_TIMEOUT_S + 0.01).can_move


def test_pose_is_not_evidence_that_a_robot_can_move():
    """The whole point. A pose exists before controllers do.

    If this ever fails because someone made `can_move` fall back to pose, the
    2026-08-18 collision is back.
    """
    stalled = robot(None)
    stalled.pose = (23.5, -1.5, 0.0)      # a perfectly good ground-truth pose
    assert not stalled.can_move


# -- and a flat robot cannot move either -------------------------------------

def test_a_flat_battery_means_it_cannot_move():
    """Controllers reporting perfectly and no charge is still immobile."""
    assert not robot(99.5, battery=0.0).can_move


def test_a_charged_robot_with_live_controllers_can_move():
    assert robot(99.5, battery=55.0).can_move
