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
    acs._yield_refused = {}
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


# -- 3. three robots, and the encounters that superimposed -------------------

def test_a_robot_already_in_an_encounter_is_not_given_a_second():
    """The south-west cycle of 2026-08-24.

    `_giving_way` is keyed by pair, so three robots meeting at once opened three
    encounters in one second — amr5 yielding to amr4, amr5 to amr3, amr4 to
    amr3. amr5 was then the yielder twice over with one `_standoff` to satisfy
    both, and amr4 was a passer and a yielder at the same time. All three
    stopped and the fleet delivered nothing for six minutes.
    """
    acs = fleet("amr3", "amr4", "amr5")
    amr3, amr4, amr5 = acs.robots

    assert acs.who_yields(amr5, amr4) is amr5
    assert acs.who_yields(amr5, amr3) is None, "amr5 is already engaged"
    assert acs.who_yields(amr4, amr3) is None, "so is amr4"

    assert acs.partner_of(amr3) is None, "amr3 queues instead"
    assert acs.partner_of(amr5) is amr4


def test_the_queue_moves_up_when_the_encounter_ends():
    """Serialised, not refused for ever."""
    acs = fleet("amr3", "amr4", "amr5")
    amr3, amr4, amr5 = acs.robots
    acs.who_yields(amr5, amr4)
    assert acs.who_yields(amr5, amr3) is None

    acs.encounter_over(amr5)

    assert acs.who_yields(amr5, amr3) is amr5, "now it may open"


def test_partner_of_is_unambiguous_once_encounters_are_serialised():
    """It returns the first matching key, which only means anything with one."""
    acs = fleet("amr3", "amr4", "amr5")
    amr3, amr4, amr5 = acs.robots
    acs.who_yields(amr5, amr4)
    acs.who_yields(amr5, amr3)

    assert acs.partner_of(amr5) is amr4
    assert acs.partner_of(amr4) is amr5


# -- 4. the breaker may now act on a stalled encounter -----------------------

def test_a_stalled_encounter_is_dropped_when_a_third_robot_boxes_us_in():
    """Being in an encounter was treated as proof someone was working on it."""
    acs = fleet("amr3", "amr4", "amr5")
    amr3, amr4, amr5 = acs.robots
    acs.who_yields(amr5, amr4)          # amr5 and amr4 engaged, both stationary

    amr5._note_blocked_by(amr3)         # a third robot in the way
    advance(amr5, SimRobot.DEADLOCK_AFTER_S + 0.1)
    amr5._note_blocked_by(amr3)

    assert acs.partner_of(amr5) is None, "the stalled encounter was let go"


def test_an_encounter_making_progress_is_left_alone():
    """A partner still driving to its lay-by must not be stranded there."""
    acs = fleet("amr3", "amr4", "amr5")
    amr3, amr4, amr5 = acs.robots
    acs.who_yields(amr5, amr4)
    amr4.vel = (0.5, 0.0)               # the partner is moving

    amr5._note_blocked_by(amr3)
    advance(amr5, SimRobot.DEADLOCK_AFTER_S + 0.1)
    amr5._note_blocked_by(amr3)

    assert acs.partner_of(amr5) is amr4, "still engaged"


def test_our_own_partner_blocking_us_is_the_handshake_not_a_deadlock():
    acs = fleet("amr4", "amr5")
    amr4, amr5 = acs.robots
    acs.who_yields(amr5, amr4)

    amr5._note_blocked_by(amr4)
    advance(amr5, SimRobot.DEADLOCK_AFTER_S + 1.0)
    amr5._note_blocked_by(amr4)

    assert acs.partner_of(amr5) is amr4, "the give-way branch owns this"
