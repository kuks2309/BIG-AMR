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
        self._stood_aside = False


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
    acs._occupied = {}
    acs._results = {}
    acs._last_log = 0.0
    return acs


def hold(acs, node, robot):
    """Give a robot a junction, the way _junction_control does."""
    assert acs.claim_junction(node, robot)
    robot._junction = node


# ------------------------------------------------------- the regression

def test_the_yielder_releases_the_junction_it_was_holding():
    """The fix. Standing aside must free the red light too, not just the road."""
    acs = fleet("amr1", "amr2")
    amr1, amr2 = acs.robots
    hold(acs, "join_GRV1_ULD", amr2)

    chosen = acs.who_yields(amr1, amr2)

    assert chosen is amr2, "name order decides; amr2 yields to amr1"
    assert acs.junction_holder("join_GRV1_ULD") is None, \
        "a robot standing aside must not keep the junction it was holding"
    assert amr2._junction is None, "and its own record must agree with the fleet's"


def test_the_passer_can_take_the_junction_the_yielder_gave_up():
    """Releasing is only useful if the other robot can then actually move."""
    acs = fleet("amr1", "amr2")
    amr1, amr2 = acs.robots
    hold(acs, "join_GRV1_ULD", amr2)

    acs.who_yields(amr1, amr2)

    assert acs.claim_junction("join_GRV1_ULD", amr1), \
        "the passer was blocked by the yielder's reservation, and must not be"


def test_the_mutual_hold_that_failed_three_jobs():
    """The exact deadlock from the 2026-08-10 run, at GRV1.

        join_GRV1_ULD: held by amr2
        join_GRV1_LD:  held by amr1
        [amr2] holding at join_GRV1_LD — amr1 has it
        amr2 gives way to amr1 -> stepping aside -> clear — you may pass
        [amr1] holding at join_GRV1_ULD — amr2 has it
        ... 45 s ... gave way for 45s and nobody passed — giving up

    Each robot sat on the junction the other needed. Giving way is the rule
    that exists to break exactly this, and it could not.
    """
    acs = fleet("amr1", "amr2")
    amr1, amr2 = acs.robots
    hold(acs, "join_GRV1_ULD", amr2)
    hold(acs, "join_GRV1_LD", amr1)

    # amr2 reaches for what amr1 holds and is refused. Being refused is now
    # itself the cure: it lets go of join_GRV1_ULD on the way out, so the cycle
    # never forms. This is the root fix doing the work, before any give-way
    # decision is taken at all.
    assert not acs.claim_junction("join_GRV1_LD", amr2)
    assert acs.junction_holder("join_GRV1_ULD") is None, \
        "a refused robot must not still be sitting on the other one's junction"

    # Giving way still happens when the meeting is head-on, and must also leave
    # the yielder holding nothing. Belt and braces: this is the narrower rule.
    acs.who_yields(amr1, amr2)

    # Either way, the passer gets through.
    assert acs.claim_junction("join_GRV1_ULD", amr1), \
        "the circular wait was not broken — both robots would sit at v=0.00 " \
        "until the job timeout killed one"


def test_the_passer_keeps_its_own_junction():
    """Only the yielder gives up its claim. The passer is about to drive."""
    acs = fleet("amr1", "amr2")
    amr1, amr2 = acs.robots
    hold(acs, "join_GRV1_LD", amr1)
    hold(acs, "join_GRV1_ULD", amr2)

    acs.who_yields(amr1, amr2)

    assert acs.junction_holder("join_GRV1_LD") is amr1
    assert amr1._junction == "join_GRV1_LD", \
        "the robot being let through must not be stripped of its own red light"


def test_a_yielder_holding_nothing_is_not_a_special_case():
    acs = fleet("amr1", "amr2")
    amr1, amr2 = acs.robots

    chosen = acs.who_yields(amr1, amr2)

    assert chosen is amr2
    assert acs.junction_holder("join_GRV1_ULD") is None


# ------------------------------- traffic applies to the robot, not to the job

def test_right_of_way_is_checked_before_asking_what_job_the_robot_has():
    """A robot is a robot. Carrying a roll, reversing out of a bay, driving home
    or parked — it is a body in an aisle and it blocks the others the same.

    The give-way rules used to live INSIDE the "driving to a goal" branch of
    drive(), which made obeying them a property of HAVING WORK. Every other
    state returned before reaching them and was silently exempt. All three were
    measured on 2026-08-10 in one session:

        idle      "amr3 gives way to amr2"  and no "stepping aside" ever
        exit leg  "amr3 gives way to amr2" -> "could not clear SLT_LD1 in 8s"
        homing    kept a junction 36 m from where it had parked

    This asserts the ORDER, because that is the property that makes the fix
    hold for states nobody has written yet.
    """
    import inspect
    from csm.adapters.sim_acs import SimRobot

    src = inspect.getsource(SimRobot.drive)
    gate = src.index("_handle_give_way")
    for later, what in ((src.index("_exit_goal is not None"), "exit leg"),
                        (src.index("_go_home()"), "homing"),
                        (src.index("if self._docking"), "docking")):
        assert gate < later, (
            f"the {what} branch is dispatched before right of way is checked, "
            f"so a robot in that state is exempt from the traffic rules")


def test_the_give_way_rules_exist_in_exactly_one_place():
    """Copying them per-state is the wrong shape — the next state added misses
    them again. They were duplicated once and it is what let three states drift.
    """
    import inspect
    from csm.adapters.sim_acs import SimRobot

    whole = inspect.getsource(SimRobot)
    # Match the emitting statements, not prose: docstrings quote these log lines
    # when citing the measurements, and that is not duplicated logic.
    assert whole.count("self.fleet.who_yields(self, threat)") == 1, \
        "the give-way decision is written in more than one place"
    assert whole.count('f"{self._tag()}stepping aside to "') == 1, \
        "the stand-aside manoeuvre is written in more than one place"
    assert whole.count("partner._stood_aside") == 1, \
        "the passer's wait is written in more than one place"


def test_a_robot_already_off_the_road_answers_by_standing_still():
    """A robot in a bay or on its parking spur has nothing to step aside from.

    Without this it would either be dragged out of a dock to perform a lay-by it
    does not need, or — as measured — leave the passer waiting on a
    `_stood_aside` flag that a parked robot never sets.
    """
    import inspect
    from csm.adapters.sim_acs import SimRobot

    assert hasattr(SimRobot, "_off_the_road")
    gate = inspect.getsource(SimRobot._handle_give_way)
    assert "_off_the_road()" in gate, \
        "the handshake must let an already-clear robot answer without moving"
    assert "already clear" in gate


# --------------------------------------------- behaviour that must not change

def test_the_decision_is_remembered_and_does_not_flip():
    """It used to be recomputed from live positions and flipped as they moved:
    both gave way, both rejoined, both met again, and they touched inside that
    loop. Name order is total, so the answer cannot depend on who asks."""
    acs = fleet("amr1", "amr2")
    amr1, amr2 = acs.robots

    first = acs.who_yields(amr1, amr2)
    assert acs.who_yields(amr2, amr1) is first
    assert acs.who_yields(amr1, amr2) is first


def test_the_encounter_can_be_ended_and_started_again():
    """After rejoining, a robot claims junctions normally — and a fresh
    encounter with the same partner must release again, not stay memoised."""
    acs = fleet("amr1", "amr2")
    amr1, amr2 = acs.robots
    hold(acs, "join_GRV1_ULD", amr2)
    acs.who_yields(amr1, amr2)
    acs.encounter_over(amr2)
    assert not acs.yielding(amr2)

    # amr2 rejoins the road and takes a junction again.
    hold(acs, "join_CTR1_LD", amr2)
    acs.who_yields(amr1, amr2)

    assert acs.junction_holder("join_CTR1_LD") is None, \
        "a second encounter must release just like the first"


# --------------------------------------------- hold-and-wait (the root defect)

def test_a_blocked_robot_does_not_keep_its_own_junction():
    """The root defect. Failing to claim used to leave the old claim in place.

    `claim_junction` promised "no robot ever waits on a junction while holding
    one", but enforced it only on the SUCCESS path. A robot that failed to
    claim returned False still holding what it had — hold-and-wait, which is
    one of the four conditions a deadlock needs.
    """
    acs = fleet("amr1", "amr2")
    amr1, amr2 = acs.robots
    hold(acs, "join_GRV1_ULD", amr2)
    hold(acs, "join_GRV2_LD", amr1)

    assert not acs.claim_junction("join_GRV2_LD", amr2), "amr1 has it"

    assert acs.junction_holder("join_GRV1_ULD") is None, \
        "a robot that must wait has to let go of what it holds"
    assert amr2._junction is None


def test_the_eastbound_deadlock_that_giving_way_could_not_break():
    """Two robots travelling the SAME direction, each on the other's junction.

    Measured 2026-08-10 with three robots. Giving way does not help here: it
    only triggers head-on, and these two were both eastbound, so nothing broke
    the cycle and both sat at v=0.00 until the 600 s job timeout killed one.
    Eight jobs died this way in ninety minutes.
    """
    acs = fleet("amr1", "amr2")
    amr1, amr2 = acs.robots
    hold(acs, "join_GRV1_ULD", amr2)
    hold(acs, "join_GRV2_LD", amr1)

    # Each reaches for what the other holds. Whoever asks first lets go.
    acs.claim_junction("join_GRV2_LD", amr2)
    assert acs.claim_junction("join_GRV1_ULD", amr1), \
        "amr1 must be able to proceed once amr2 stops hoarding"


def test_releasing_on_failure_does_not_hand_over_a_junction_in_use():
    """The robot that HOLDS a junction keeps it — only the waiter lets go."""
    acs = fleet("amr1", "amr2")
    amr1, amr2 = acs.robots
    hold(acs, "join_GRV1_ULD", amr1)
    hold(acs, "join_GRV2_LD", amr2)

    acs.claim_junction("join_GRV1_ULD", amr2)       # amr2 is refused

    assert acs.junction_holder("join_GRV1_ULD") is amr1, \
        "the holder must not be evicted by someone else's failed claim"
    assert amr1._junction == "join_GRV1_ULD"


def test_reclaiming_the_junction_you_already_hold_is_not_a_release():
    """A robot re-asserting its own claim must not drop it."""
    acs = fleet("amr1", "amr2")
    amr1, _ = acs.robots
    hold(acs, "join_GRV1_ULD", amr1)

    assert acs.claim_junction("join_GRV1_ULD", amr1)

    assert acs.junction_holder("join_GRV1_ULD") is amr1
    assert amr1._junction == "join_GRV1_ULD"


def test_only_one_robot_yields_in_an_encounter():
    acs = fleet("amr1", "amr2")
    amr1, amr2 = acs.robots

    acs.who_yields(amr1, amr2)

    assert acs.yielding(amr2)
    assert not acs.yielding(amr1), "both yielding means nobody passes"
