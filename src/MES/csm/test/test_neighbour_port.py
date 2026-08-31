"""RULE 7: check the ports either side before entering a docking point.

THE RULE (user, 2026-08-31):

    before any AMR going for docking they should check is there any AMR coming
    out from docking from adjacent LD or ULD. if anyone is coming out from
    docking then wait for it to finish. if not then start docking.

    ... SLT has 4 docking points, so if any AMR tries to enter docking point 2
    he has to check both 1 and 3. The waiting robot waits in the road, they
    should not enter anywhere. It will wait forever — it will just get the
    signal that docking is finished or not; until finished it will wait.

WHAT IT REPLACES. Nothing. The six existing rules all measure something — a
corridor, a clearance, whether a robot has left the lane — and the failure on
2026-08-31 happened with every one of them satisfied:

    amr4 (-20.71,-4.65) backing out of SLT_LD2, on the outer lane
    amr9 (-19.19,-3.61) crossing that lane to dock at SLT_LD3
    frozen 1.84 m apart, amr4 on the 3 m rule and amr9 on layer 1

This rule asks a station question instead, and the fleet already knows the
answer: `_exit_station` names the bay a robot is reversing out of, and it is
cleared when the bay is handed back.
"""

import pytest

from csm import plant
from csm.adapters.sim_acs import SimRobot


class FakeFleet:
    def __init__(self, robots):
        self.robots = robots


def robot(name, exiting=None, left=None, at=None):
    """Only the fields RULE 7 reads.

    `exiting` = still reversing out.  `left` = out of the bay but perhaps not
    yet away from it, which is the state that matters.  `at` is the pose, and
    it is needed only to answer "have you driven away yet".
    """
    r = object.__new__(SimRobot)
    r.name = name
    r.pose = (at[0], at[1], 0.0) if at else (0.0, 0.0, 0.0)
    r.fleet = None
    r._exit_station = exiting
    r._left_station = left if left is not None else exiting
    return r


def together(*robots):
    fleet = FakeFleet(list(robots))
    for r in robots:
        r.fleet = fleet
    return fleet


# ------------------------------------------------------------- who is adjacent

def test_the_slitter_middle_ports_check_both_sides():
    """The user's own example: entering 2, check 1 and 3."""
    assert plant.neighbour_ports("SLT_LD2") == ["SLT_LD1", "SLT_LD3"]
    assert plant.neighbour_ports("SLT_LD3") == ["SLT_LD2", "SLT_LD4"]


def test_a_port_at_the_end_of_the_row_has_one_neighbour():
    assert plant.neighbour_ports("SLT_LD1") == ["SLT_LD2"]
    assert plant.neighbour_ports("SLT_LD4") == ["SLT_LD3"]


def test_an_LD_and_its_ULD_are_neighbours():
    """They are 2.4 m apart on the same machine — the same spacing as two
    slitter ports, so the same hazard."""
    assert plant.neighbour_ports("CTR2_LD") == ["CTR2_ULD"]
    assert plant.neighbour_ports("GRV1_ULD") == ["GRV1_LD"]


def test_a_port_that_stands_alone_has_no_neighbours():
    assert plant.neighbour_ports("ASRS") == []


def test_every_port_knows_its_row():
    """No port may be missing from the table — one that is would silently
    never wait for anybody."""
    for name, station in plant.STATIONS.items():
        if station["kind"] == "MACHINE":
            continue
        assert name in plant.MACHINE_PORTS, name


# ----------------------------------------------------------------- the waiting

def test_the_2026_08_31_deadlock_is_refused():
    """The recorded incident, at the exact second amr9 asked.

    The bay was handed back at 947.6 — `SLT_LD2: amr4 clear — bay free` — and
    amr9 reached its junction and asked at 955.9, eight seconds later. amr4 was
    then at (-21.4,-4.5): out of the bay, on the road, and 2.1 m from the dock
    it had left. Not away.
    """
    amr4 = robot("amr4", left="SLT_LD2", at=(-21.4, -4.5))
    amr4._exit_station = None                  # bay already handed back
    amr9 = robot("amr9")
    together(amr9, amr4)

    assert amr9._neighbour_leaving("SLT_LD3") is amr4


def test_out_of_the_bay_is_NOT_finished():
    """The first version of this rule ended the wait here, and the deadlock
    happened anyway. Kept so it cannot quietly come back."""
    amr4 = robot("amr4", left="SLT_LD2", at=plant.DOCKS["SLT_LD2"])
    amr4._exit_station = None
    amr9 = robot("amr9")
    together(amr9, amr4)

    assert amr9._neighbour_leaving("SLT_LD3") is amr4


def test_the_wait_ends_when_it_has_driven_away():
    """Five metres from the port it left. In the run that is roughly x = -17,
    a couple of metres east of the neighbouring spur."""
    amr4 = robot("amr4", left="SLT_LD2", at=(-17.0, -4.5))
    amr4._exit_station = None
    amr9 = robot("amr9")
    together(amr9, amr4)

    assert amr9._neighbour_leaving("SLT_LD3") is None


def test_the_clearance_covers_the_neighbouring_crossing():
    """The number is not a taste. A robot standing exactly on the next port's
    crossing is 3.19 m from the dock it came out of, so anything at or under
    that would release the wait with a body still across the path."""
    import math

    from csm.adapters.sim_acs import CLEAR_OF_PORT

    dock = plant.DOCKS["SLT_LD2"]
    crossing = plant.JOINS["SLT_LD3"]
    reach = math.hypot(crossing[0] - dock[0], crossing[1] - dock[1])

    assert CLEAR_OF_PORT > reach + plant.ROBOT_L / 2.0, \
        "a robot could still be sitting across the neighbour's crossing"


def test_a_robot_two_ports_away_does_not_hold_us():
    """Either side, not the whole machine. SLT_LD1 is 4.8 m from SLT_LD3 and
    cannot sweep the ground in front of it."""
    amr4 = robot("amr4", exiting="SLT_LD1")
    amr9 = robot("amr9")
    together(amr9, amr4)

    assert amr9._neighbour_leaving("SLT_LD3") is None


def test_a_robot_leaving_the_bay_we_want_is_not_this_rule():
    """That is the fleet interlock's job, and it answers with a different
    refusal. RULE 7 is only about the ports BESIDE ours."""
    amr4 = robot("amr4", exiting="SLT_LD3")
    amr9 = robot("amr9")
    together(amr9, amr4)

    assert amr9._neighbour_leaving("SLT_LD3") is None


def test_a_docked_robot_that_is_not_leaving_does_not_hold_us():
    """Sitting in the next bay is not the hazard. Reversing out of it is."""
    amr4 = robot("amr4", exiting=None)
    amr9 = robot("amr9")
    together(amr9, amr4)

    assert amr9._neighbour_leaving("SLT_LD2") is None


def test_no_fleet_and_no_station_are_answered_not_guessed():
    lone = robot("amr9")
    assert lone._neighbour_leaving("SLT_LD3") is None    # fleet is None
    together(lone)
    assert lone._neighbour_leaving(None) is None


# ------------------------------------------------- and it is actually wired in

def test_the_check_runs_before_the_crossing_commits():
    """WHERE it is asked is the whole rule.

    A robot commits to the crossing at ROAD_EDGE and does not stop after that,
    because stopping half way across is stopping in the road. So the question
    has to be asked on the near side of that line.

    It was first wired to the entry request instead, 2.2 m from the dock — and
    for SLT_LD3 the commit is at y = -2.95 while that request fires at
    y = -4.40, a metre and a half after the decision it was meant to inform.
    """
    import inspect
    from csm.adapters import sim_acs

    src = inspect.getsource(sim_acs.SimRobot._pause_before_crossing)
    rule7 = src.index("_neighbour_leaving(station)")
    commit = src.index("if gap <= ROAD_EDGE:")

    assert rule7 < commit, "RULE 7 must be asked before the robot commits"


def test_the_robot_waits_on_the_road():
    """`entry_request_range` is the distance at which the refusal happens, and
    it has to leave the robot on the lane rather than part way down a spur."""
    import inspect
    import re

    from csm.adapters import sim_acs

    src = inspect.getsource(sim_acs.SimRobot.__init__)
    found = re.search(r"entry_request_range = ([0-9.]+)", src)
    assert found, "entry_request_range is no longer set in __init__"
    request_range = float(found.group(1))

    dock_to_lane = abs(plant.DOCKS["SLT_LD3"][1] - plant.AISLE_S_OUT)

    # 2.20 against 2.10 — ten centimetres. Tight, and worth a test rather than
    # a comment: shorten the range or deepen a spur and the robot would stop
    # part way down its own spur, which is not "in the road".
    assert request_range > dock_to_lane, \
        "the refusal must arrive before the robot leaves the lane"


# ------------------------------------------- the deadlock the rule itself made

def test_a_robot_leaving_its_own_dock_is_not_held_by_rule_7():
    """RULE 7 is about going IN. The same crossing check also fires for a robot
    driving OUT of its dock across both lanes, and holding that one for its
    neighbour is not this rule.

    Measured 2026-08-31 12:4x, ten minutes after the rule went in: amr4 at
    SLT_LD2 and amr8 at SLT_LD3, both wanting to drive out, each reading the
    other as "leaving a neighbouring port". Both stopped for good.
    """
    from test_crossing_in import heading_for, robot as bare, together as pair

    # amr4 sits AT SLT_LD2 and is going to CTR2_ULD -- it is leaving, not
    # entering, even though it is about to cross the same lane.
    amr4 = heading_for("amr4", "CTR2_ULD", *plant.DOCKS["SLT_LD2"])
    amr8 = bare("amr8", *plant.DOCKS["SLT_LD3"])
    amr8._left_station = "SLT_LD3"
    pair(amr4, amr8)

    assert amr4._target_station() == "CTR2_ULD"
    assert plant.port_at_join(plant.JOINS["SLT_LD2"]) == "SLT_LD2"
    # the neighbour IS leaving, and it still must not hold us
    assert amr4._neighbour_leaving("SLT_LD2") is amr8
    assert amr4._pause_before_crossing() is False or \
        "rule 7" not in (amr4._halt_reason or "")


def test_docking_ends_any_claim_to_be_leaving():
    """A robot that drove away, took another job and came back would arrive
    still carrying the flag — and a parked robot that looks like a leaving one
    holds its neighbours for ever."""
    amr4 = robot("amr4", left="SLT_LD2", at=plant.DOCKS["SLT_LD2"])
    amr4._exit_station = None
    amr9 = robot("amr9")
    together(amr9, amr4)
    assert amr9._neighbour_leaving("SLT_LD3") is amr4, "held before docking"

    amr4._arrived_at_dock()

    assert amr9._neighbour_leaving("SLT_LD3") is None


def test_two_robots_at_adjacent_docks_do_not_hold_each_other():
    """The measured deadlock, both directions at once."""
    from test_crossing_in import heading_for, together as pair

    amr4 = heading_for("amr4", "CTR2_ULD", *plant.DOCKS["SLT_LD2"])
    amr8 = heading_for("amr8", "CTR3_ULD", *plant.DOCKS["SLT_LD3"])
    amr4._left_station = "SLT_LD2"
    amr8._left_station = "SLT_LD3"
    pair(amr4, amr8)

    for r in (amr4, amr8):
        r._pause_before_crossing()
        assert "rule 7" not in (r._halt_reason or ""), \
            f"{r.name} is leaving its own dock, not entering one"


# --------------------------- a job can end without the robot ever getting there

def test_a_robot_that_never_arrived_does_not_claim_the_exit():
    """The 2026-08-31 phantom exit.

    amr8 sat in its parking bay at (+29.99, -10.5) for a whole run — x never
    moved a centimetre — and still took `_exit_station = SLT_LD3`, 49 m west,
    every time one of its jobs ended. The exit leg then set a pause goal at
    SLT_LD3's junction, which is a 49 m pause corridor reaching across the
    plant, and amr4 parked 33 m away fell inside it:

        pausing before the road — amr4 in the way

    Permanently, and it held amr9 and amr10 in the neighbouring bays too.
    """
    from csm.adapters.sim_acs import SimRobot
    from test_crossing_in import robot as bare

    park = plant.parking_for("amr8")
    far = bare("amr8", park[0], park[1])

    assert far._standing_in("SLT_LD3") is False, "49 m away is not in the bay"

    docked = bare("amr8", *plant.DOCKS["SLT_LD3"])
    assert docked._standing_in("SLT_LD3") is True

    # and the boundary is the one the constant names, not an accident
    edge = bare("amr8", plant.DOCKS["SLT_LD3"][0],
                plant.DOCKS["SLT_LD3"][1] + SimRobot.IN_THE_BAY - 0.1)
    assert edge._standing_in("SLT_LD3") is True
    out = bare("amr8", plant.DOCKS["SLT_LD3"][0],
               plant.DOCKS["SLT_LD3"][1] + SimRobot.IN_THE_BAY + 0.1)
    assert out._standing_in("SLT_LD3") is False


def test_the_exit_claim_asks_whether_the_robot_is_there():
    """Wired in, not merely defined."""
    import inspect

    from csm.adapters import sim_acs

    src = inspect.getsource(sim_acs.SimRobot._finish)

    assert "_standing_in(station)" in src, \
        "_finish must not claim an exit the robot never reached"


def test_an_unknown_station_is_not_a_bay():
    from test_crossing_in import robot as bare

    assert bare("amr8", 0.0, 0.0)._standing_in(None) is False
    assert bare("amr8", 0.0, 0.0)._standing_in("NOT_A_STATION") is False
