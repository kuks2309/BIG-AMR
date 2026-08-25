"""Handing the yield to the robot that actually has room.

THE DEADLOCK THIS BREAKS, measured live on 2026-08-24 with five robots.

amr1 and amr2 met head-on on the north aisle, 2.25 m apart:

    amr1  (-11.7, +3.1)  ->GRV3_LD   [passer: waiting for the yielder to stand aside]
    amr2  ( -9.6, +3.9)  ->GRV1_ULD  [robot ahead on the road]

Under RULE 1 the lower number gives way, so amr1 is the yielder. Every lay-by open to
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
    # Rule 4 reads these: a robot going in to dock outranks everyone.
    r._docking = False
    r._active_job = None
    r._waypoints = [(0.0, 0.0), (1.0, 0.0)]      # more than one hop: not final
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

def test_the_lower_number_decides_first():
    acs, amr1, amr2 = the_encounter()

    assert acs.who_yields(amr1, amr2) is amr1, "RULE 1: the lower number gives way"


def test_a_yielder_with_nowhere_to_go_hands_over():
    acs, amr1, amr2 = the_encounter()
    acs.who_yields(amr1, amr2)

    assert acs.cannot_yield(amr1) is amr2
    assert acs.yielding(amr2), "the one with room is now the yielder"
    assert not acs.yielding(amr1)


def test_the_new_yielder_starts_from_a_clean_slate():
    """A stale standoff or all-clear from the old role would be read as truth."""
    acs, amr1, amr2 = the_encounter()
    acs.who_yields(amr1, amr2)          # RULE 1: amr1 is the yielder
    amr2._stood_aside = True            # stale state on the robot about to take over
    amr2._standoff = (99.0, 99.0)

    acs.cannot_yield(amr1)              # amr1 has nowhere to go; amr2 takes the duty

    assert amr2._standoff is None
    assert amr2._stood_aside is False


def test_the_hand_over_happens_once_and_does_not_oscillate():
    """If neither has room, flipping for ever is worse than waiting it out."""
    acs, amr1, amr2 = the_encounter()
    acs.who_yields(amr1, amr2)
    acs.cannot_yield(amr1)

    assert acs.cannot_yield(amr2) is None, "no one left to hand to"
    assert acs.yielding(amr2), "the decision stands; YIELD_LIMIT ends it"


def test_a_robot_that_is_not_the_yielder_cannot_hand_over():
    acs, amr1, amr2 = the_encounter()
    acs.who_yields(amr1, amr2)

    assert acs.cannot_yield(amr2) is None
    assert acs.yielding(amr1), "unchanged — amr2 was never the yielder"


def test_the_budget_dies_with_the_encounter():
    """One hand-over PER ENCOUNTER. The next meeting starts with its own."""
    acs, amr1, amr2 = the_encounter()
    acs.who_yields(amr1, amr2)
    acs.cannot_yield(amr2)
    acs.encounter_over(amr1)

    acs.who_yields(amr1, amr2)
    assert acs.cannot_yield(amr1) is amr2, "a fresh encounter, a fresh allowance"


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


# ------------------------------------- rule 2 must not wait for a parked robot

def test_a_parked_robot_does_not_hold_the_encounter_open():
    """The five-robot jam of 2026-08-24.

    amr3 sat in leg C's first bay with no job. `_travel_dir` is None for a robot
    with no goal, and `_head_on_with` answers an unknown direction with True —
    the safe reading when OPENING an encounter, the wrong one when closing it.
    So amr4 and amr5 both held for a robot that was never going to move:

        [amr4] amr5 is past, but amr3 is following it — holding
        [amr5] amr4 is past, but amr3 is following it — holding

    Neither left the parking row.
    """
    from csm import plant

    mover = robot("amr4", 20.0, -3.65, (0.0, -3.65))      # driving west
    parked = robot("amr3", *plant.parking_for("amr3"), goal=None)
    parked._goal = None
    acs = fleet(mover, parked)

    assert parked._on_a_spur(), "it is in its bay"
    assert mover._oncoming_ahead() is None, \
        "a parked robot with no goal is not oncoming traffic"


# ------------------------------------ RULE 4: going in to dock beats everything

def docker(name, station_bound=True):
    r = robot(name, 0.0, 0.0, (1.0, 0.0))
    r._active_job = "JOB" if station_bound else None
    r._waypoints = [(1.0, 0.0)] if station_bound else [(1.0, 0.0), (2.0, 0.0)]
    return r


def test_a_robot_going_to_dock_never_gives_way():
    """The 2026-08-25 incident, in one call.

    amr3 was waiting for SLT_LD3 to grant entry. Six seconds later the deadlock
    breaker ruled it deadlocked with amr5, Rule 1 made it the yielder because
    3 < 5, and it abandoned its approach. It lost the delivery and then cycled
    through the 45 s timeout twenty-one times.
    """
    amr3, amr5 = docker("amr3"), docker("amr5", station_bound=False)
    acs = fleet(amr3, amr5)

    assert amr3.going_to_dock() and not amr5.going_to_dock()
    assert acs.who_yields(amr3, amr5) is amr5, \
        "the robot heading in to dock has priority, whatever its number"


def test_rule_4_beats_rule_1_in_both_directions():
    """It is about docking, not about which number happens to be docking."""
    amr5, amr3 = docker("amr5"), docker("amr3", station_bound=False)
    acs = fleet(amr5, amr3)

    assert acs.who_yields(amr3, amr5) is amr3, \
        "the higher number docks; the lower one stops for it"


def test_number_order_still_decides_when_neither_is_docking():
    amr3, amr5 = docker("amr3", station_bound=False), docker("amr5", station_bound=False)
    acs = fleet(amr3, amr5)

    assert acs.who_yields(amr3, amr5) is amr3, "RULE 1 applies as before"


def test_number_order_decides_when_both_are_docking():
    """Two robots bound for different stations cannot both be waved through."""
    amr3, amr5 = docker("amr3"), docker("amr5")
    acs = fleet(amr3, amr5)

    assert amr3.going_to_dock() and amr5.going_to_dock()
    assert acs.who_yields(amr3, amr5) is amr3, "falls back to the lower number"


def test_docking_covers_the_whole_approach_not_just_the_refusal():
    """Waiting for entry, the last hop, and the manoeuvre are all 'going in'."""
    r = docker("amr3")
    assert r.going_to_dock(), "on the final leg with a job"

    r._docking = True
    r._waypoints = [(1.0, 0.0), (2.0, 0.0)]
    assert r.going_to_dock(), "and while actually docking"

    r._docking = False
    r._active_job = None
    assert not r.going_to_dock(), "but not once the job is done"
