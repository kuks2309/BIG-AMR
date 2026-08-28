"""RULE 2, THE OTHER HALF: pausing before crossing a lane INTO a dock or bay.

The rule as the user stated it on 2026-08-26 has two words in it that turned
out to matter: "LEAVING a dock, a robot pauses before the road." Only leaving.
Every dock and every parking bay in this plant sits outside BOTH lanes, so
every arrival crosses a live lane too, and nothing covered that.

Measured 2026-08-26 15:36:24, with both robots obeying both rules:

    amr2 (-20.69,-4.50) eastbound on the south OUTER lane, dead straight 4 m
    amr3 (-19.09,-4.85) crossing that lane on the SLT_LD3 spur, going IN
    CONTACT, gap -0.007 m

These tests drive the geometry and the hold directly. No poses on a wire, no
ROS: the rule is arithmetic over positions, and it should be reproducible in
milliseconds rather than by waiting for two robots to meet at a spur mouth.
"""

import math

import pytest

from csm import plant
from csm.adapters.sim_acs import (HOLD_RADIUS, ROAD_EDGE, ROBOT_STOP_SIDE,
                                  SimRobot)


class FakePub:
    def __init__(self):
        self.sent = []

    def publish(self, msg):
        self.sent.append(msg)


class FakeFleet:
    def __init__(self, robots):
        self.robots = robots


def robot(name, x, y, yaw=0.0):
    """A SimRobot with only the fields RULE 2 reads.

    Built without __init__ deliberately: the real one needs a live ROS node,
    publishers and subscriptions, none of which participate in this rule.
    """
    r = object.__new__(SimRobot)
    r.name = name
    r.pose = (x, y, yaw)
    r.vel = (0.0, 0.0)
    r.fleet = None
    r.pub_cmd = FakePub()
    r._halt_reason = None
    r._stall_ref = r._stall_since = None
    r._exit_goal = None
    r._active_job = None
    r._goal = None
    r._waypoints = []
    r._leg = r._from = r._to = None
    r._homing = False
    r._home_waypoints = []
    r._pausing_out = False
    r._pausing_in = False
    r._turning = False
    r._crossing_lane = None
    r._pause_goal = None
    return r


def heading_for(name, station, x, y, goal=None):
    """A robot with a job, driving at `goal` on its way in to `station`."""
    r = robot(name, x, y)
    r._active_job = object()
    r._leg = "deliver"
    r._to = station
    r._goal = goal if goal is not None else plant.JOINS_OUTER[station]
    r._waypoints = [r._goal, plant.DOCKS[station]]
    return r


def together(*robots):
    fleet = FakeFleet(list(robots))
    for r in robots:
        r.fleet = fleet
    return fleet


# ------------------------------------------------ the premise: 27 of 27, 10 of 10

@pytest.mark.parametrize("station", sorted(plant.DOCKS))
def test_every_dock_sits_beyond_a_live_lane(station):
    """This is why the rule needs a second half at all."""
    assert plant.outer_lane_beyond(plant.DOCKS[station]) is not None


@pytest.mark.parametrize("segment", sorted(plant.PARKING_SLOTS))
def test_every_parking_bay_sits_beyond_a_live_lane(segment):
    for slot in plant.PARKING_SLOTS[segment]:
        assert plant.outer_lane_beyond(slot) is not None


def test_a_point_on_the_road_is_beyond_nothing():
    """The lane itself is not a dead end, so there is nothing to cross to it."""
    assert plant.outer_lane_beyond((0.0, plant.AISLE_N_IN)) is None


def test_the_leg_c_bays_cross_the_EAST_lane_not_the_south_one():
    """They run 11 m south of the south aisle, so two lanes are "beyond".

    Nearest has to win: bay C6 is 2.15 m past the east lane and 11.25 m past
    the south one, and its spur crosses the east one.
    """
    bay = plant.PARKING_SLOTS["C"][-1]
    axis, value, _ = plant.outer_lane_beyond(bay)

    assert (axis, round(value, 2)) == ("x", round(plant.AISLE_E_OUT, 2))


# --------------------------------------------------------- when the rule engages

def test_a_robot_on_the_inner_lane_turning_in_is_crossing():
    jx, jy = plant.JOINS_OUTER["ASRS"]
    r = heading_for("amr1", "ASRS", jx, plant.AISLE_N_IN)

    found = r._crossing()

    assert found is not None
    _, gap = found
    assert gap == pytest.approx(plant.LANE_GAP, abs=1e-9)


def test_a_robot_driving_ALONG_the_inner_lane_is_not_crossing():
    """The whole lane is `LANE_GAP` short of the outer one. What separates
    crossing from driving past is where the next waypoint is, not where the
    robot is."""
    jx, _ = plant.JOINS_OUTER["ASRS"]
    r = heading_for("amr1", "ASRS", jx - 3.0, plant.AISLE_N_IN,
                    goal=(jx, plant.AISLE_N_IN))

    assert r._crossing() is None


def test_a_robot_already_on_the_outer_lane_is_not_crossing():
    """It turns off the lane it is on. There is no live lane in the way."""
    jx, jy = plant.JOINS_OUTER["ASRS"]
    r = heading_for("amr1", "ASRS", jx, jy)

    assert r._crossing() is None


def test_a_robot_past_the_lane_has_stopped_crossing():
    """Past it AND aimed onward. Aimed back AT the lane it would be coming
    out, which is the same rule read the other way — see the "new job" tests
    at the foot of this file."""
    jx, jy = plant.JOINS_OUTER["ASRS"]
    r = heading_for("amr1", "ASRS", jx, jy + ROAD_EDGE + 0.01,
                    goal=plant.DOCKS["ASRS"])

    assert r._crossing() is None


def test_a_robot_further_along_the_same_lane_is_not_crossing():
    """Beside the spur, not lined up on it."""
    jx, jy = plant.JOINS_OUTER["ASRS"]
    r = heading_for("amr1", "ASRS", jx + ROBOT_STOP_SIDE + 0.5,
                    plant.AISLE_N_IN)

    assert r._crossing() is None


def test_backing_out_is_the_other_half_and_not_this_one():
    """`_drive_to_exit` owns the way out. Two rules on one robot would fight."""
    jx, jy = plant.JOINS_OUTER["ASRS"]
    r = heading_for("amr1", "ASRS", jx, plant.AISLE_N_IN)
    r._exit_goal = (jx, jy)

    assert r._crossing() is None


def test_a_robot_going_home_to_its_bay_is_crossing_too():
    """A parking spur crosses the same lane a dock spur does."""
    bay = plant.PARKING_SLOTS["A"][0]
    axis, value, outward = plant.outer_lane_beyond(bay)
    join = (value, bay[1])
    r = robot("amr1", plant.AISLE_W_IN, bay[1])
    r._homing = True
    r._home_waypoints = [join, bay]

    assert r._crossing() is not None


# ------------------------------------------------------------ pause, hold, cross

def pause_point(station):
    """Where the rule says to stop: ROAD_EDGE short of the outer lane."""
    jx, jy = plant.JOINS_OUTER[station]
    _, _, outward = plant.outer_lane_beyond(plant.DOCKS[station])
    return jx, jy - outward * ROAD_EDGE


def just_short(station, back=0.20):
    """A shade further out than the pause point, where the decision is made.

    AT the pause point the robot is committed — `gap <= ROAD_EDGE` — and stops
    asking, because past there it is in the lane and there is nowhere to stop.
    """
    jx, jy = plant.JOINS_OUTER[station]
    _, _, outward = plant.outer_lane_beyond(plant.DOCKS[station])
    return jx, jy - outward * (ROAD_EDGE + back)


def test_it_stops_when_the_lane_it_must_cross_is_occupied():
    station = "SLT_LD3"
    px, py = pause_point(station)
    jx, jy = plant.JOINS_OUTER[station]
    goer = heading_for("amr3", station, px, py + 0.20)   # a shade short of it
    onlane = robot("amr2", jx + 0.4, jy)                 # in the spur mouth
    together(goer, onlane)

    assert goer._pause_before_crossing() is True
    assert goer._pausing_in is True
    assert "amr2" in goer._halt_reason


def test_it_crosses_when_the_lane_is_clear():
    station = "SLT_LD3"
    px, py = pause_point(station)
    goer = heading_for("amr3", station, px, py + 0.20)
    away = robot("amr2", px + 8.0, plant.AISLE_S_OUT)
    together(goer, away)

    assert goer._pause_before_crossing() is False
    assert goer._pausing_in is True         # still holding while it crosses


def test_the_hold_outlasts_the_pause():
    """A hold that ended the moment the robot moved would release the lane
    into the one instant the robot is standing in it."""
    station = "SLT_LD3"
    px, py = pause_point(station)
    jx, jy = plant.JOINS_OUTER[station]
    goer = heading_for("amr3", station, px, py)
    together(goer)

    goer._pause_before_crossing()                   # engages, lane clear
    assert goer._pausing_in is True

    # Reaching the junction pops it, so the goal becomes the dock beyond.
    goer.pose = (jx, jy, 0.0)                       # now dead in the lane
    goer._goal = plant.DOCKS[station]
    goer._waypoints = [goer._goal]
    goer._pause_before_crossing()

    assert goer._pausing_in is True


def test_a_robot_arriving_along_the_outer_lane_holds_nobody():
    """It turns off the lane it is already on and crosses nothing. Holding the
    neighbourhood for that would cost every dock arrival in the plant."""
    station = "SLT_LD3"
    jx, jy = plant.JOINS_OUTER[station]
    r = heading_for("amr3", station, jx, jy)
    together(r)

    assert r._pause_before_crossing() is False
    assert r._pausing_in is False


def test_a_robot_near_a_crossing_robot_stands_still():
    station = "SLT_LD3"
    px, py = pause_point(station)
    goer = heading_for("amr3", station, px, py)
    goer._pausing_in = True
    goer._pause_goal = plant.JOINS_OUTER[station]
    passer = robot("amr2", px - 4.0, plant.AISLE_S_OUT)
    passer._goal = (px + 4.0, plant.AISLE_S_OUT)   # eastbound, still short of it
    together(goer, passer)

    assert math.hypot(passer.pose[0] - px, passer.pose[1] - py) < HOLD_RADIUS
    assert passer._held_for_a_leaver() is True


def test_a_robot_further_off_than_the_hold_radius_carries_on():
    station = "SLT_LD3"
    px, py = pause_point(station)
    goer = heading_for("amr3", station, px, py)
    goer._pausing_in = True
    goer._pause_goal = plant.JOINS_OUTER[station]
    passer = robot("amr2", px - (HOLD_RADIUS + 1.0), plant.AISLE_S_OUT)
    passer._goal = (px + 4.0, plant.AISLE_S_OUT)
    together(goer, passer)

    assert passer._held_for_a_leaver() is False


def test_the_robot_standing_IN_the_way_is_not_held():
    """Otherwise the pause is the deadlock it exists to prevent: the pauser
    waits for its path to clear, and the only robot that could clear it has
    just been told to stand still."""
    station = "SLT_LD3"
    px, py = pause_point(station)
    jx, jy = plant.JOINS_OUTER[station]
    goer = heading_for("amr3", station, px, py)
    goer._pausing_in = True
    goer._pause_goal = (jx, jy)
    inthway = robot("amr2", jx, jy)
    together(goer, inthway)

    assert goer._blocks_path(inthway, px, py, (jx, jy)) is True
    assert inthway._held_for_a_leaver() is False


def test_two_crossing_robots_do_not_wait_on_each_other_for_ever():
    """Lower number goes, the other gives it room."""
    a = heading_for("amr1", "SLT_LD3", *pause_point("SLT_LD3"))
    b = heading_for("amr2", "SLT_LD1", *pause_point("SLT_LD1"))
    for r in (a, b):
        r._pausing_in = True
        r._pause_goal = plant.JOINS_OUTER[r._to]
    together(a, b)
    if math.hypot(a.pose[0] - b.pose[0], a.pose[1] - b.pose[1]) > HOLD_RADIUS:
        pytest.skip("those two spurs are further apart than the hold radius")

    assert a._held_for_a_leaver() is False
    assert b._held_for_a_leaver() is True


# ------------------------------------------------------------- the regression

def test_the_2026_08_26_contact_position_is_inside_the_lane():
    """amr3 was at (-19.09,-4.85) — 0.35 m PAST the line it should have
    stopped 1.55 m short of, with amr2 coming along that line."""
    _, _, outward = plant.outer_lane_beyond(plant.DOCKS["SLT_LD3"])
    _, value = plant.LANE_LINE[("outer", "south")]
    gap = (value - (-4.85)) * outward

    assert gap < 0.0, "amr3 was over the line, not short of it"
    assert gap < ROAD_EDGE, "and nowhere near the standoff the rule now keeps"


def test_the_turn_is_pinned_while_crossing():
    """Rotating reaches the half-diagonal, 0.918 m against 0.450 m held flat,
    which eats the air ROAD_EDGE leaves. The final leg crabs in anyway, so the
    turn is waste as well as hazard."""
    import inspect

    src = inspect.getsource(SimRobot.drive)
    pin = src.index("cmd.angular.z = 0.0")
    guard = src.rindex("self._pausing_in", 0, pin)

    assert src.index("_on_a_spur()", 0, pin) < guard < pin


# ------------------------------------------ the 2026-08-26 17:04 deadlock

def test_a_robot_a_body_length_along_the_lane_is_in_the_way():
    """The measured jam. amr3 crossing the CTR2_ULD spur, amr4 standing on the
    outer lane 1.81 m along it:

        1.6/2 + 1.6/2 + 0.30 = 1.90 m needed between centres
        1.90 > 1.81 > 1.20   the old corridor called it clear

    amr3 committed on that answer and layer 1 stopped it BETWEEN the two lanes,
    where a 1.80 m gap has no room for a 0.90 m robot to stand aside. amr3
    waited for amr4, amr4 was held by amr3, amr5 queued behind amr4, and the
    three of them never moved again.
    """
    from csm.adapters.sim_acs import ROBOT_STOP_SIDE

    station = "CTR2_ULD"
    px, py = pause_point(station)
    jx, jy = plant.JOINS_OUTER[station]
    goer = heading_for("amr3", station, *just_short(station))
    onlane = robot("amr4", jx - 1.81, jy)
    together(goer, onlane)

    assert 1.81 > ROBOT_STOP_SIDE, "the old corridor saw nothing there"
    assert goer._blocks_path(onlane, *goer.pose[:2], (jx, jy)) is False

    assert goer._pause_before_crossing() is True
    assert "amr4" in goer._halt_reason


def test_the_robot_it_is_waiting_for_is_told_to_carry_on():
    """The other half of the same number. It was held where it stood, which is
    what turned a wait into a deadlock."""
    station = "CTR2_ULD"
    px, py = pause_point(station)
    jx, jy = plant.JOINS_OUTER[station]
    goer = heading_for("amr3", station, px, py)
    onlane = robot("amr4", jx - 1.81, jy)
    together(goer, onlane)
    goer._pause_before_crossing()

    assert goer._pausing_in is True
    assert onlane._held_for_a_leaver() is False


def test_a_robot_two_body_lengths_off_is_clear_and_is_held():
    """The rule still lets a crossing happen, and still stops the traffic."""
    station = "CTR2_ULD"
    px, py = pause_point(station)
    jx, jy = plant.JOINS_OUTER[station]
    goer = heading_for("amr3", station, *just_short(station))
    onlane = robot("amr4", jx - 3.2, jy)
    onlane._goal = (jx + 4.0, jy)                  # eastbound, still short of it
    together(goer, onlane)

    assert goer._pause_before_crossing() is False
    assert onlane._held_for_a_leaver() is True


def test_the_clear_test_covers_the_whole_crossing():
    """`ROBOT_STOP_AHEAD` is 2.40 m and the crossing is 1.55 + 1.20 = 2.75 m,
    so the last 0.35 m of every crossing went unexamined."""
    from csm.adapters.sim_acs import CROSS_CLEAR, ROBOT_STOP_AHEAD

    assert ROAD_EDGE + CROSS_CLEAR > ROBOT_STOP_AHEAD

    station = "CTR2_ULD"
    px, py = pause_point(station)
    jx, jy = plant.JOINS_OUTER[station]
    _, _, outward = plant.outer_lane_beyond(plant.DOCKS[station])
    far = robot("amr4", jx, jy + outward * (CROSS_CLEAR - 0.4))  # just past it
    goer = heading_for("amr3", station, *just_short(station))
    together(goer, far)

    assert goer._pause_before_crossing() is True


# ------------------------------------------------ and the way OUT holds too

def test_the_hold_on_the_way_out_lasts_until_the_robot_is_out():
    """It used to be cleared the moment `distance` fell inside ROAD_EDGE —
    the moment the robot starts entering the lane. Every robot it had told to
    stand still started moving again exactly then."""
    import inspect

    from csm.adapters.sim_acs import SimRobot

    src = inspect.getsource(SimRobot._drive_to_exit)

    assert "self._pausing_out = False" not in src, \
        "the exit leg lets go of the hold before it has left the spur"
    assert "self._pausing_out = True" in src

    released = inspect.getsource(SimRobot._release_exit)
    assert "self._pausing_out = False" in released, \
        "arriving outside is where the hold ends"


# ------------------------------- the third way onto a spur, found 2026-08-26

def test_leaving_the_dock_on_a_NEW_JOB_is_a_crossing_too():
    """Neither half of rule 2 covered it, and it is the commonest way out.

    The back-out leg ends at the OUTER junction and releases the bay. The robot
    then takes a job whose first waypoint is its own INNER junction, and drives
    from the dock straight across both lanes. `_pausing_out` belongs to the
    exit leg, which is over; `_pausing_in` wanted a goal BEYOND the lane, and
    the inner junction is on the hall side. So the crossing held nobody.

    Measured 2026-08-26: amr5 0.84 m up the CTR1_ULD spur bound for SLT_LD1,
    amr2 stopped on the outer lane 0.33 m from that spur line, both frozen on
    layer 1, neither able to start.
    """
    r = robot("amr5", -10.48, -5.76, -3.09)
    r._active_job = object()
    r._leg, r._to = "deliver", "SLT_LD1"
    r._goal = plant.JOINS_INNER["CTR1_ULD"]
    r._waypoints = [r._goal]

    found = r._crossing()

    assert found is not None, "leaving the dock on a job crosses the lane"
    assert found[1] == pytest.approx(1.26, abs=0.01)


def test_the_robot_in_the_spur_mouth_is_what_it_waits_for():
    """amr2's own position from that jam, 0.33 m off the spur line."""
    goer = robot("amr5", -10.56, -6.25, -3.09)      # a shade short of it
    goer._active_job = object()
    goer._leg, goer._to = "deliver", "SLT_LD1"
    goer._goal = plant.JOINS_INNER["CTR1_ULD"]
    goer._waypoints = [goer._goal]
    onlane = robot("amr2", -10.89, plant.AISLE_S_OUT)
    together(goer, onlane)

    assert goer._pause_before_crossing() is True
    assert "amr2" in goer._halt_reason
    assert onlane._held_for_a_leaver() is False, \
        "the robot it is waiting for must clear the mouth, not freeze in it"


def test_the_hold_covers_the_whole_way_out_across_both_lanes():
    """From short of the outer lane until the body is clear on the far side."""
    r = robot("amr5", -10.56, -7.75, -3.09)
    r._active_job = object()
    r._leg, r._to = "deliver", "SLT_LD1"
    r._goal = plant.JOINS_INNER["CTR1_ULD"]
    r._waypoints = [r._goal]
    together(r)

    held = []
    for y in (-7.75, -7.20, -6.05, -5.50, -4.50, -3.60, -2.90, -2.70):
        r.pose = (-10.56, y, -3.09)
        r._pause_before_crossing()
        held.append(r._pausing_in)

    assert held == [False, True, True, True, True, True, False, False], held


# --------------------------- "near it" means able to get there, 2026-08-27

def approaching(name, x, y, goal):
    r = robot(name, x, y)
    r._goal = goal
    r._waypoints = [goal]
    r._active_job = object()
    r._leg, r._to = "deliver", "GRV3_LD"
    return r


def leaver(station):
    """A robot backing out of `station`, holding the road."""
    jx, jy = plant.JOINS_OUTER[station]
    _, _, outward = plant.outer_lane_beyond(plant.DOCKS[station])
    r = robot("amr2", jx, jy + outward * 0.92)
    r._pausing_out = True
    r._pause_goal = (jx, jy)
    return r


def test_a_robot_that_has_already_passed_the_spur_is_not_held():
    """It cannot drive into a crossing it has left behind.

    Measured 2026-08-27: amr2 backing out of GRV1_ULD, spur at x = -10.56.
    amr1 was on the inner lane at (-8.25,+2.70) — 2.31 m EAST of that spur,
    driving east — and was told to stand still.
    """
    out = leaver("GRV1_ULD")
    past = approaching("amr1", -8.25, plant.AISLE_N_IN, (-6.24, plant.AISLE_N_IN))
    together(out, past)

    assert math.hypot(past.pose[0] - out.pose[0],
                      past.pose[1] - out.pose[1]) < HOLD_RADIUS
    assert past._held_for_a_leaver() is False


def test_a_robot_still_short_of_the_spur_is_held():
    """The other side of the same test — the rule still has to work."""
    out = leaver("GRV1_ULD")
    coming = approaching("amr1", -13.5, plant.AISLE_N_IN,
                         (-6.24, plant.AISLE_N_IN))
    together(out, coming)

    assert coming._held_for_a_leaver() is True


def test_a_robot_off_the_road_is_not_held():
    """amr6 was docked at GRV2_LD, 4.85 m away and in a bay. Held for nothing."""
    out = leaver("GRV1_ULD")
    docked = approaching("amr6", *plant.DOCKS["GRV2_LD"], plant.DOCKS["GRV2_LD"])
    docked.pose = (plant.DOCKS["GRV2_LD"][0], 7.71, 0.0)
    together(out, docked)

    assert docked._held_for_a_leaver() is False


def test_an_idle_robot_with_nowhere_to_go_is_not_held():
    """No goal, no direction, nothing to drive into."""
    out = leaver("GRV1_ULD")
    idle = robot("amr9", -13.5, plant.AISLE_N_IN)
    together(out, idle)

    assert idle._travel_dir() is None
    assert idle._held_for_a_leaver() is False


# ------------------------- the turn, and the hold that has to cover it

def turner(name, x, y, yaw, goal):
    """A robot on a lane whose goal is well off its nose — i.e. turning."""
    r = robot(name, x, y, yaw)
    r._goal = goal
    r._waypoints = [goal, (goal[0] + 5.0, goal[1])]
    r._active_job = object()
    r._leg, r._to = "deliver", "GRV3_LD"
    r.crab_window = 0.5
    return r


def test_a_robot_turning_at_a_junction_holds_the_road():
    """The hold used to end when the CROSSING ended, and the turn happens
    straight after — which is exactly when the robot stops presenting 0.450 m
    and starts sweeping 0.918 m.

    Measured 2026-08-27: amr6 on the inner lane and amr7 on the outer, both
    off the GRV2_ULD spur, both mid-turn, 1.93 m apart. Two turning robots
    need 0.918 + 0.918 + 0.30 = 2.14 m. Both stopped on layer 1 and neither
    recovered. Nothing had held either of them.
    """
    x = plant.DOCKS["GRV2_ULD"][0]
    t = turner("amr6", x, plant.AISLE_N_IN, -math.pi / 4, (x + 4.3, plant.AISLE_N_IN))
    together(t)

    t._note_turning()

    assert t._turning is True
    assert t._pausing is True
    assert t._pause_goal == t.pose[:2]


def test_two_robots_do_not_turn_beside_each_other():
    """1.80 m of lane gap against 2.14 m of swept width. The lower number
    turns and the other waits."""
    x = plant.DOCKS["GRV2_ULD"][0]
    six = turner("amr6", x, plant.AISLE_N_IN, -math.pi / 4, (x + 4.3, plant.AISLE_N_IN))
    seven = turner("amr7", x, plant.AISLE_N_OUT, -math.pi / 2, (x - 2.9, plant.AISLE_N_OUT))
    together(six, seven)
    for r in (six, seven):
        r._note_turning()

    swept = 2 * (math.hypot(plant.ROBOT_L, plant.ROBOT_W) / 2) + 0.30
    assert plant.LANE_GAP < swept, "the two lanes are not wide enough for two turns"

    assert six._held_for_a_leaver() is False       # lower number goes
    assert seven._held_for_a_leaver() is True      # and this one waits


def test_a_robot_already_square_is_not_turning():
    """No hold for driving straight on. Otherwise every robot holds the plant."""
    x = plant.DOCKS["GRV2_ULD"][0]
    r = turner("amr6", x, plant.AISLE_N_IN, 0.0, (x + 4.3, plant.AISLE_N_IN))
    together(r)

    r._note_turning()

    assert r._turning is False
    assert r._pausing is False


def test_no_turn_is_reported_where_the_heading_is_pinned():
    """On a spur, in a bay, on the final leg or mid-crossing the driver holds
    the heading, so there is no turn to hold the road for."""
    station = "GRV2_ULD"
    dock = plant.DOCKS[station]
    r = turner("amr6", dock[0], dock[1], math.pi / 2, plant.JOINS_INNER[station])
    together(r)

    assert r._on_a_spur() is True
    r._note_turning()

    assert r._turning is False


def test_the_turn_hold_reaches_only_as_far_as_the_sweep():
    """A turn takes 1.7 s and endangers what is beside it. Holding everything
    within HOLD_RADIUS for that would stop the plant at every corner."""
    from csm.adapters.sim_acs import SimRobot

    x = plant.DOCKS["GRV2_ULD"][0]
    six = turner("amr6", x, plant.AISLE_N_IN, -math.pi / 4,
                 (x + 4.3, plant.AISLE_N_IN))
    far = approaching("amr7", x - 4.0, plant.AISLE_N_IN, (x + 4.3, plant.AISLE_N_IN))
    together(six, far)
    six._note_turning()

    assert SimRobot.TURN_ROOM < HOLD_RADIUS
    assert 4.0 > SimRobot.TURN_ROOM
    assert far._held_for_a_leaver() is False
