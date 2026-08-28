"""The junction reservation and the give-way handshake, where they meet.

These two rules were each correct alone and wrong together, and nothing tested
the seam. `claim_junction` states the invariant the whole scheme rests on:

    "A robot always releases the junction it holds before claiming another, so
     no robot ever waits on a junction while holding one — which is what makes
     a circular wait impossible."

That was true only along the path through `_junction_control`. A robot that was
told to give way returned from `drive()` before ever reaching it, so it stood
aside — off the road, stationary, announcing "clear — you may pass" — while
still holding its red light. The robot it was yielding TO then waited on that
light, and the yielder waited for it to pass. Neither could move.

Measured 2026-08-10 in a two-robot Gazebo run: three jobs failed in twenty
minutes and every one of them was this. The give-up log line is followed within
50 ms by the passer taking the junction, which is what proves the reservation
was the only thing in the way — both robots had already stopped, and the
yielder was off the lane. It was never a question of space.

The tests below drive the fleet logic directly. It is pure bookkeeping — no
poses, no ROS — so the deadlock is reproducible in milliseconds rather than by
waiting for two robots to meet at the wrong junction.
"""

import pytest

from csm.adapters.sim_acs import SimAcs


class FakeLogger:
    def __init__(self):
        self.lines = []

    def info(self, message):
        self.lines.append(message)

    def warn(self, message):
        self.lines.append(message)


class FakeNode:
    def __init__(self):
        self._logger = FakeLogger()

    def get_logger(self):
        return self._logger


class FakeRobot:
    """Only what the fleet's traffic rules touch: a name and a held junction."""

    def __init__(self, name):
        self.name = name
        self._junction = None
        # Rule 4 reads these: going in to dock outranks everyone.
        self._docking = False
        self._active_job = None
        self._waypoints = [(0.0, 0.0), (1.0, 0.0)]
        self._stood_aside = False

    def going_to_dock(self):
        """RULE 4. Mirrors SimRobot's, which the fleet calls on every robot."""
        return self._docking or (self._active_job is not None
                                 and len(self._waypoints) <= 1)


def fleet(*names):
    """A SimAcs with its traffic bookkeeping and nothing else.

    Built without __init__ deliberately: the real one spawns SimRobots, which
    need a live ROS node, publishers and subscriptions. None of that
    participates in the rules under test, and requiring it would mean this
    seam could only ever be tested in a running simulation — which is exactly
    how it stayed untested until it failed three jobs.
    """
    acs = object.__new__(SimAcs)
    acs.node = FakeNode()
    acs.robots = [FakeRobot(n) for n in names]
    acs._junctions = {}
    acs._giving_way = {}
    acs._yield_refused = {}
    acs._occupied = {}
    acs._results = {}
    acs._last_log = 0.0
    return acs


def hold(acs, node, robot):
    """Give a robot a junction, the way _junction_control does."""
    assert acs.claim_junction(node, robot)
    robot._junction = node


# ------------------------------------------------------- the regression

def test_layer_1_is_checked_before_the_job_dispatch():
    """_threat() knows STOP_GAP, and it was wired to two places only: the homing
    path, and the question "who yields?". It never stopped anything on a normal
    job leg. Head-on meetings were covered because they route into the give-way
    handshake; a robot CROSSING our path or catching us from behind produced no
    stop at all, leaving only _repulsion(), which is bounded so that it steers
    without ever halting.

    Measured 2026-08-10 with every other fix in place: amr1 and amr2 overlapped
    for 225 samples — about 7.5 s — in a run reporting 82 deliveries and zero
    failures. Job success is not a safety signal.
    """
    import inspect
    from csm.adapters.sim_acs import SimRobot

    src = inspect.getsource(SimRobot.drive)
    guard = src.index("self._threat()")
    for later, what in ((src.index("_exit_goal is not None"), "exit leg"),
                        (src.index("_go_home()"), "homing"),
                        (src.index("if self._docking"), "docking")):
        assert guard < later, (
            f"the {what} branch is dispatched before layer 1 is checked, so a "
            f"robot in that state can publish a velocity unguarded")


def test_layer_1_is_not_copied_into_the_individual_paths():
    """One check, in the gate. A second copy is what let the paths drift apart
    in the first place."""
    import inspect
    from csm.adapters.sim_acs import SimRobot

    assert inspect.getsource(SimRobot.drive).count("self._threat()") == 1
    assert "self._threat()" not in inspect.getsource(SimRobot._go_home), \
        "the homing path re-checks layer 1; the gate already did"


def test_excluding_a_robot_only_removes_that_one():
    """The exclusion must be surgical, not a way to switch layer 1 off."""
    import math
    from csm.adapters.sim_acs import SimRobot, STOP_GAP

    def bot(x, y):
        r = object.__new__(SimRobot)
        r.pose, r.vel = (x, y, 0.0), (0.0, 0.0)
        return r

    me, near, far = bot(0.0, 0.0), bot(1.0, 0.0), bot(40.0, 0.0)
    fleet_obj = type("F", (), {"robots": [me, near, far]})()
    me.fleet = fleet_obj

    assert me._threat() is near, "a robot 1.0 m nose-to-nose must be a threat"
    assert me._threat(exclude=near) is None, "only that one is excluded"
    assert me._threat(exclude=far) is near, "excluding a distant robot changes nothing"


# --------------------------------------------- behaviour that must not change


# The three junction-reservation tests that stood here are gone with the rule
# they tested. Junctions are no longer a resource anybody claims: a robot
# leaving a dock pauses at the road edge and holds the robots near it instead
# (RULE 2), and layer 1 below is the only other thing that stops anyone.
