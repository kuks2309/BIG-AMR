"""Two ways two robots could stop each other for ever, and neither can now.

Layer 1 says STOP and, by design, "cannot say who goes" — deciding that is the
job of the rules above it. But those rules only covered a HEAD-ON meeting, so
two robots that met any other way had nothing above layer 1 to break the tie.

Both cases here were found in Gazebo, not by reasoning.
"""

import math

import pytest

from csm.adapters.sim_acs import SimAcs, SimRobot


class FakeLogger:
    def __init__(self):
        self.lines = []

    def info(self, m):
        self.lines.append(m)

    def warn(self, m):
        self.lines.append(m)


class FakeNode:
    def __init__(self):
        self._logger = FakeLogger()

    def get_logger(self):
        return self._logger


def fleet(*names):
    acs = object.__new__(SimAcs)
    acs.node = FakeNode()
    acs._junctions = {}
    acs._giving_way = {}
    acs._occupied = {}
    acs._results = {}
    acs._last_log = 0.0
    acs.robots = []
    for n in names:
        r = object.__new__(SimRobot)
        r.node = acs.node
        r.fleet = acs
        r.name = n
        r.pose = (0.0, 0.0, 0.0)
        r.vel = (0.0, 0.0)
        r._junction = None
        r._stood_aside = False
        r._standoff = None
        r._blocked_by = None
        r._blocked_since = 0.0
        r._clock = 0.0
        r._now = lambda rr=r: rr._clock
        r._stopped = []
        r._stop = lambda why="x", rr=r: rr._stopped.append(why)
        r._reset_stall = lambda: None
        r._tag = lambda rr=r: f"[{rr.name}] "
        acs.robots.append(r)
    return acs


def advance(robot, seconds):
    robot._clock += seconds


# -- 1. two robots crossing, neither head-on nor following -------------------

def test_a_brief_block_is_not_treated_as_a_deadlock():
    """A robot waiting a moment for another to pass is ordinary traffic."""
    acs = fleet("amr1", "amr2")
    a, b = acs.robots
    a._note_blocked_by(b)
    advance(a, 1.0)
    a._note_blocked_by(b)
    assert acs.partner_of(a) is None, "no encounter should have been opened"


def test_a_lasting_mutual_block_asks_who_yields():
    """The case that froze amr2 and amr3 for two minutes.

    One heading north to a gravure ULD, one heading south to a slitter LD.
    Converging, so not head-on; neither following the other. Layer 1 stopped
    both and nothing above it ever chose.
    """
    acs = fleet("amr1", "amr2")
    a, b = acs.robots
    a._note_blocked_by(b)
    advance(a, SimRobot.DEADLOCK_AFTER_S + 0.1)
    a._note_blocked_by(b)
    assert acs.partner_of(a) is not None, "a yielder should have been chosen"


def test_a_moving_blocker_is_left_alone():
    """If the other robot is still moving this is traffic and will clear."""
    acs = fleet("amr1", "amr2")
    a, b = acs.robots
    b.vel = (0.6, 0.0)
    a._note_blocked_by(b)
    advance(a, SimRobot.DEADLOCK_AFTER_S + 0.1)
    a._note_blocked_by(b)
    assert acs.partner_of(a) is None


def test_the_clock_restarts_when_the_blocker_changes():
    """Blocked by a different robot is a different situation, not a longer one."""
    acs = fleet("amr1", "amr2", "amr3")
    a, b, c = acs.robots
    a._note_blocked_by(b)
    advance(a, SimRobot.DEADLOCK_AFTER_S - 0.1)
    a._note_blocked_by(c)          # someone else now
    advance(a, 0.2)
    a._note_blocked_by(c)
    assert acs.partner_of(a) is None


def test_an_encounter_already_being_handled_is_not_reopened():
    acs = fleet("amr1", "amr2")
    a, b = acs.robots
    acs.who_yields(a, b)
    before = acs.partner_of(a)
    a._note_blocked_by(b)
    advance(a, SimRobot.DEADLOCK_AFTER_S + 1.0)
    a._note_blocked_by(b)
    assert acs.partner_of(a) is before


# -- 2. a passer waiting on a yielder that never reports ---------------------

def test_robots_far_apart_are_not_in_an_encounter():
    """amr1 sat waiting for a yielder THIRTEEN METRES away.

    The yielder has an escape from a stuck handshake — YIELD_LIMIT. The passer
    had none, and the "we are past each other" test only runs once the yielder
    reports clear. So a passer waiting on a yielder that never reports waited
    for ever, at any distance.
    """
    assert SimRobot.ENCOUNTER_RANGE < 13.0, \
        "13 m apart must count as out of range"


def test_the_range_is_generous_enough_not_to_end_a_real_encounter():
    """Ending one early is the failure the code above it warns about."""
    assert SimRobot.ENCOUNTER_RANGE >= 5.0
