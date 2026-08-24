"""Handing the yield to the robot that actually has room.

THE DEADLOCK THIS BREAKS, measured live on 2026-08-24 with five robots.

amr1 and amr2 met head-on on the north aisle, 2.25 m apart:

    amr1  (-11.7, +3.1)  ->GRV3_LD   [passer: waiting for the yielder to stand aside]
    amr2  ( -9.6, +3.9)  ->GRV1_ULD  [robot ahead on the road]

`who_yields` picks by name order, so amr2 was the yielder. Every lay-by open to
amr2 lay west, on the far side of amr1, so amr2 could not move — and a passer
waits for the explicit all-clear, so amr1 would not. Forty-five seconds later
YIELD_LIMIT ended it the only way it can, by failing a job. It cost two:
amr2's BOBBIN_0003 and amr1's ROLL_0006.

amr1 had room the whole time. It was simply not the one being asked.

Name order is deliberate and stays — a rule recomputed from live positions
flipped every tick and the two robots touched inside the loop (see
`who_yields`). What it cannot know is whether the robot it names has anywhere
to go. So the decision is still made once, and may be handed over ONCE, by the
robot that has tried and found nothing.
"""

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters.sim_acs import SimAcs, SimRobot        # noqa: E402


class FakeLogger:
    def info(self, message): pass
    def warn(self, message): pass


class FakeNode:
    def get_logger(self): return FakeLogger()


def robot(name, x, y, goal):
    r = object.__new__(SimRobot)
    r.name = name
    r.node = FakeNode()
    r.pose = (x, y, 0.0)
    r.vel = (0.0, 0.0)
    r._goal = goal
    r._standoff = None
    r._stood_aside = False
    r._yield_since = None
    r._junction = None
    r.fleet = None
    return r


def fleet(*robots):
    acs = object.__new__(SimAcs)
    acs.node = FakeNode()
    acs.robots = list(robots)
    acs._junctions = {}
    acs._giving_way = {}
    acs._yield_refused = {}
    acs._occupied = {}
    acs._results = {}
    acs._last_log = 0.0
    for r in robots:
        r.fleet = acs
    return acs


def the_encounter():
    """The two robots exactly where they stuck on 2026-08-24."""
    amr1 = robot("amr1", -11.7, 3.1, (-11.7, 13.1))
    amr2 = robot("amr2", -9.6, 3.9, (-9.6, 13.9))
    return fleet(amr1, amr2), amr1, amr2


# --------------------------------------------------------------- the hand-over

def test_name_order_still_decides_first():
    acs, amr1, amr2 = the_encounter()

    assert acs.who_yields(amr1, amr2) is amr2, "later name yields"


def test_a_yielder_with_nowhere_to_go_hands_over():
    acs, amr1, amr2 = the_encounter()
    acs.who_yields(amr1, amr2)

    assert acs.cannot_yield(amr2) is amr1
    assert acs.yielding(amr1), "the one with room is now the yielder"
    assert not acs.yielding(amr2)


def test_the_new_yielder_starts_from_a_clean_slate():
    """A stale standoff or all-clear from the old role would be read as truth."""
    acs, amr1, amr2 = the_encounter()
    acs.who_yields(amr1, amr2)
    amr1._stood_aside = True
    amr1._standoff = (99.0, 99.0)

    acs.cannot_yield(amr2)

    assert amr1._standoff is None
    assert amr1._stood_aside is False


def test_the_hand_over_happens_once_and_does_not_oscillate():
    """If neither has room, flipping for ever is worse than waiting it out."""
    acs, amr1, amr2 = the_encounter()
    acs.who_yields(amr1, amr2)
    acs.cannot_yield(amr2)

    assert acs.cannot_yield(amr1) is None, "no one left to hand to"
    assert acs.yielding(amr1), "the decision stands; YIELD_LIMIT ends it"


def test_a_robot_that_is_not_the_yielder_cannot_hand_over():
    acs, amr1, amr2 = the_encounter()
    acs.who_yields(amr1, amr2)

    assert acs.cannot_yield(amr1) is None
    assert acs.yielding(amr2), "unchanged — amr1 was never the yielder"


def test_the_budget_dies_with_the_encounter():
    """One hand-over PER ENCOUNTER. The next meeting starts with its own."""
    acs, amr1, amr2 = the_encounter()
    acs.who_yields(amr1, amr2)
    acs.cannot_yield(amr2)
    acs.encounter_over(amr1)

    acs.who_yields(amr1, amr2)
    assert acs.cannot_yield(amr2) is amr1, "a fresh encounter, a fresh allowance"


# ------------------------------------------------- why it could not move at all

def test_the_incident_geometry_left_amr2_no_lay_by_on_its_own_axis():
    """The x-offset candidates all lay through amr1 — that is what stuck.

    Kept as a statement of the geometry, so that if the aisle constants move
    this test says the incident no longer reproduces rather than passing on.
    """
    from csm import plant
    from csm.adapters.sim_acs import SIDESTEP, PATH_CLEARANCE, _point_seg

    _, amr1, amr2 = the_encounter()
    x, y, _ = amr2.pose
    ns = [(plant.AISLE_W_X + SIDESTEP, y), (plant.AISLE_W_X - SIDESTEP, y)]

    for goal in ns:
        assert _point_seg(amr1.pose[:2], (x, y), goal) < PATH_CLEARANCE, \
            "every north-south candidate passed through amr1"
        assert math.hypot(goal[0] - x, goal[1] - y) > 10.0, \
            "and each was a journey, not a step aside"
