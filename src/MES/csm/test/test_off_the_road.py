"""When a robot may answer a give-way by standing still.

THE CONTACT THIS PREVENTS, measured live on 2026-08-24 with four robots.

    amr4 gives way to amr3
    [amr4] already clear — you may pass

amr4 never moved. It was 2.96 m from the CTR2_ULD marker, which is 0.04 m
inside BAY_RADIUS = 3.0 m, so `_in_a_bay` was true and `_off_the_road` took
that as clearance. But that bay circle reaches y = -4.0, one metre from the
south aisle, and amr4 sat at y = -4.04:

    amr4 north edge  y = -3.59
    amr3 south edge  y = -3.55        <- overlapping

amr3 took the all-clear, drove the aisle, and the bodies touched. Measured at
0.00 m by Tools/contact_meter/, which shares no code with the traffic layer.
Nothing in the run log recorded it — contact writes no log line, which is why
the run was reported as clean.

The old test asked what KIND of place the robot was in. The question that
decides whether another robot can get past is how far its BODY is from the
lane, and that is what is asked now.
"""

import math

import pytest

from csm import plant
from csm.adapters import roads
from csm.adapters.sim_acs import ROADS, ROBOT_L, ROBOT_W, SimRobot


def at(x, y, yaw=0.0):
    r = object.__new__(SimRobot)
    r.pose = (x, y, yaw)
    return r


def nearest_through_lane(x, y):
    """Distance to the closest lane a passing robot could be using."""
    return min(roads._clearance((x, y), ROADS.nodes[a], ROADS.nodes[b])
               for a, b in ROADS.lanes
               if not (a.startswith(("dock_", "park_"))
                       or b.startswith(("dock_", "park_"))))


# ------------------------------------------------------------- the requirement

def test_the_passing_gap_is_the_passer_plus_the_margin():
    """Not a tuned number — it is what the OTHER robot and the margin occupy.

    This robot's own half-extent is deliberately not in here. It is not a
    constant; see the orientation tests below.
    """
    assert SimRobot.PASSING_GAP == pytest.approx(ROBOT_W / 2 + 0.30)


# ------------------------------------------------------------- the incident

def test_the_2026_08_24_position_is_not_clear():
    amr4 = at(-2.73, -4.04)

    assert not amr4._off_the_road(), \
        "1.04 m off the south aisle is not room for another robot to pass"


def test_that_position_really_was_inside_a_bay():
    """So the test above is about the RULE, not about the position drifting.

    If BAY_RADIUS or the coater row moves and this stops holding, the old rule
    no longer fires there and this file should be re-read rather than trusted.
    """
    x, y = -2.73, -4.04
    inside = [n for n, (mx, my, _) in plant.MARKERS.items()
              if math.hypot(mx - x, my - y) < plant.BAY_RADIUS]

    assert inside == ["CTR2_ULD"], "the old rule called this 'in a bay'"
    assert nearest_through_lane(x, y) < ROBOT_W + 0.30


def test_a_robot_on_the_aisle_is_never_clear():
    assert not at(-2.73, plant.AISLE_S_Y)._off_the_road()


# --------------------------------------------- what must still count as clear

def test_a_docked_robot_is_clear():
    """A dock spur is a dead end. Nothing passes along it."""
    for station in ("CTR2_ULD", "GRV1_LD", "SLT_LD1"):
        x, y = plant.DOCKS[station]
        assert at(x, y)._off_the_road(), f"{station} dock should be clear"


@pytest.mark.parametrize("name", ["amr1", "amr2", "amr3", "amr4", "amr5"])
def test_every_parking_slot_is_clear(name):
    """A robot that has gone home must not be dragged out to perform a lay-by.

    Every slot, not the first: leg C's later slots sit at y = -3.65 and -5.80,
    which are close to the SOUTH AISLE LINE but nowhere near the south aisle
    itself, because that aisle ends at the east cross aisle and the bays are
    beyond it. Measuring against the lane SEGMENTS rather than the infinite
    line is what keeps these clear.
    """
    x, y = plant.parking_for(name)

    assert at(x, y)._off_the_road()


def test_the_infinite_line_would_have_failed_a_parking_slot():
    """States why the segment distance is load-bearing, not incidental."""
    x, y = plant.parking_for("amr4")

    assert abs(y - plant.AISLE_S_Y) < ROBOT_W + 0.30, \
        "close to the south aisle LINE"
    assert nearest_through_lane(x, y) >= ROBOT_W + 0.30, \
        "but far from every actual lane"


# ------------------------------------------ how much room a robot takes up
# ------------------------------------------ depends on which way it points

def test_a_turned_robot_needs_more_room_than_a_parallel_one():
    """The 2026-08-24 near miss, and then the contact.

    amr2 was driving to a lay-by at (-14.7,+1.0) and part way there, at
    (-13.63,+1.75) turned 27 degrees, announced "already clear — you may pass".
    Its centre was 1.25 m from the north aisle. A flat rule of half-width plus
    passing gap wants 1.20 m, so it passed by 0.05 m.

    Turned 27 degrees it reaches 0.76 m across the lane, not 0.45 m, so what it
    really needed was 1.51 m. amr1 came down the aisle: 0.160 m, then contact.
    """
    turned = at(-13.63, 1.75, 0.47)
    parallel = at(-13.63, 1.75, 0.0)

    assert not turned._off_the_road(), "27 degrees reaches into the lane"
    assert parallel._off_the_road(), "the same spot is fine lying flat"


def test_the_reach_is_measured_across_the_lane_not_across_y():
    """So it is right for the north-south cross aisles too."""
    lane = ("aisle_nw", "aisle_sw")           # the west cross aisle, x = -22.0
    r = at(plant.AISLE_W_X + 1.3, 0.0, 0.0)   # long axis pointing ACROSS it
    _distance, needed = r._lane_clearance(*r.pose, *lane)

    assert needed == pytest.approx(ROBOT_L / 2 + SimRobot.PASSING_GAP), \
        "end-on to a north-south lane, the LENGTH is what reaches into it"
    assert not r._off_the_road()


def test_square_on_is_the_worst_case_and_is_bounded():
    """Whatever the heading, the requirement never exceeds this."""
    worst = ROBOT_L / 2 + SimRobot.PASSING_GAP
    r = at(-13.0, plant.AISLE_N_Y - worst - 0.01, math.pi / 2)

    assert r._off_the_road(), "just past the worst case is clear at any heading"
