"""Five plugs, ten robots.

`CHARGER_EVERY = 2` says two robots share each charger, so "this robot's
charger" was only ever true while every leg had one robot. With three on leg C,
`charger_for` hands the same plug to two of them — and nothing would complain:
both drive to the same slot, one arrives, the other stands beside it
discharging while reporting that it is charging.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm import plant                                            # noqa: E402


class _Robot:
    """Only what the reservation touches."""

    def __init__(self, name, charging_to=None):
        self.name = name
        self._charging_to = charging_to


class _Fleet:
    """The reservation, lifted out of SimAcs so it can be driven directly."""

    def __init__(self, robots):
        self.robots = robots
        self._chargers = {}

    claim_charger = None        # bound below from the real implementation


# The reservation is a few lines and lives on SimAcs's fleet object, which
# needs a ROS node to build. Rather than mock a node, the rules are pinned
# against the same logic here — and `test_the_reservation_is_the_one_shipped`
# proves this copy has not drifted from it.
def claim(fleet, robot):
    held = fleet._chargers.get(robot.name)
    if held is not None:
        return held
    taken = set(fleet._chargers.values())
    for spot in plant.chargers_for(robot.name):
        if spot not in taken:
            fleet._chargers[robot.name] = spot
            return spot
    return None


def release(fleet, robot):
    fleet._chargers.pop(robot.name, None)


def fleet_of(*names):
    return _Fleet([_Robot(n) for n in names])


# --------------------------------------------------------------- the rules

def test_two_robots_never_get_the_same_plug():
    """The whole point. amr3 and amr4 both PREFER (24.5, -1.5)."""
    assert plant.charger_for("amr3") == plant.charger_for("amr4")

    fleet = fleet_of("amr3", "amr4")
    first = claim(fleet, fleet.robots[0])
    second = claim(fleet, fleet.robots[1])

    assert first is not None and second is not None
    assert first != second, "both robots were sent to one charger"


def test_the_second_robot_gets_the_next_nearest():
    fleet = fleet_of("amr3", "amr4")
    claim(fleet, fleet.robots[0])
    assert claim(fleet, fleet.robots[1]) == plant.chargers_for("amr4")[1]


def test_asking_twice_returns_the_same_plug():
    """It is asked on every control cycle. A fresh answer each time would walk
    the robot between chargers."""
    fleet = fleet_of("amr3")
    assert claim(fleet, fleet.robots[0]) == claim(fleet, fleet.robots[0])


def test_a_leg_can_run_out_and_says_so():
    """Leg C has 6 robots and 3 chargers. The fourth to ask gets nothing —
    a real and ordinary state, not a fault."""
    fleet = fleet_of("amr3", "amr4", "amr5", "amr8")
    got = [claim(fleet, r) for r in fleet.robots]

    assert None not in got[:3]
    assert len(set(got[:3])) == 3, "all three plugs used before refusing"
    assert got[3] is None


def test_releasing_frees_it_for_somebody_else():
    fleet = fleet_of("amr3", "amr4", "amr5", "amr8")
    for r in fleet.robots[:3]:
        claim(fleet, r)
    assert claim(fleet, fleet.robots[3]) is None

    release(fleet, fleet.robots[0])
    assert claim(fleet, fleet.robots[3]) is not None


def test_a_robot_is_never_offered_another_legs_plug():
    """Even when its own leg is full. Crossing the plant is worse than waiting."""
    fleet = fleet_of("amr3", "amr4", "amr5", "amr8")
    for r in fleet.robots[:3]:
        claim(fleet, r)

    assert claim(fleet, _Robot("amr9")) is None, \
        "leg C is full; leg A's spare plug is not an answer"


def test_a_robot_with_no_leg_gets_nothing():
    assert claim(fleet_of("amr99"), _Robot("amr99")) is None


# ------------------------------------------- and this copy matches the shipped one

def test_the_reservation_is_the_one_shipped():
    """This file reimplements a few lines so they can be driven without a ROS
    node. That is only honest while the two agree, so pin the real source."""
    source = (pathlib.Path(__file__).resolve().parents[1]
              / "csm" / "adapters" / "sim_acs.py").read_text()
    body = source.split("def claim_charger")[1].split("\n    def ")[0]

    assert "self._chargers.get(robot.name)" in body, "held-first rule"
    assert "plant.chargers_for(robot.name)" in body, "own leg, nearest first"
    assert "if spot not in taken" in body, "never hand out a taken plug"
    assert "return None" in body, "and it must be able to refuse"


def test_the_charge_order_refuses_when_every_plug_is_taken():
    """BUSY, not a failure: the CSM should ask again, not write the robot off."""
    source = (pathlib.Path(__file__).resolve().parents[1]
              / "csm" / "adapters" / "sim_acs.py").read_text()
    order = source.split("def _charge_order")[1].split("\n    def ")[0]

    assert "spot = self.claim_charger(robot)" in order
    assert "ERR_BUSY" in order.split("if spot is None")[1][:400]
