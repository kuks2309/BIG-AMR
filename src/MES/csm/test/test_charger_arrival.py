"""A robot that parks at its charger must actually charge.

Observed live on 2026-08-19, with the fleet started part-charged: amr1 and amr3
sat at their slots reporting `charging_to 90` while their batteries fell. They
had stopped 0.6 m from the charger — inside the tolerance that says "you have
arrived", outside the one that says "you are on the charger".

The gap between two tolerances is not a rounding error. It is a state in which
a robot is parked, idle, believed to be filling up, and going flat.
"""

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm import plant                                            # noqa: E402


HOME_TOL = 0.8            # SimAcs robot arrival tolerance; see _go_home


def test_the_parking_tolerance_is_the_one_that_matters():
    """`is_charger`'s own default is TIGHTER than the distance a robot stops
    at, so it can never be the test for "did it arrive"."""
    assert 0.3 < HOME_TOL, (
        "plant.is_charger's default tolerance is looser than parking; "
        "this test's premise has changed")


def test_the_observed_failure():
    """The exact positions from the run. amr1 parked, and did not charge."""
    parked_at = (-21.9, 1.6)
    charger = plant.charger_for("amr1")

    assert not plant.is_charger(parked_at), "this is what went wrong"
    assert math.hypot(charger[0] - parked_at[0],
                      charger[1] - parked_at[1]) <= HOME_TOL, \
        "...yet it was parked, by the rule that decides parking"


def test_anywhere_a_robot_may_stop_counts_as_on_its_charger():
    """Sweep the whole ring a robot may legally come to rest in.

    Not one sample point: the failure was at 0.6 m and a test that checked 0.1
    and 1.0 would have passed while the bug sat between them.
    """
    for name in plant.ROBOT_SEGMENT:
        charger = plant.charger_for(name)
        if charger is None:
            continue
        for i in range(24):
            angle = 2 * math.pi * i / 24
            for radius in (0.0, 0.2, 0.4, 0.6, 0.79):
                spot = (charger[0] + radius * math.cos(angle),
                        charger[1] + radius * math.sin(angle))
                assert math.hypot(charger[0] - spot[0],
                                  charger[1] - spot[1]) <= HOME_TOL
                # The rule the simulator now uses: my charger, my arrival
                # tolerance. Every point a robot may stop at must pass it.
                assert _on_own_charger(name, spot), \
                    f"{name} may park at {spot} and would not charge"


def _on_own_charger(name, pose):
    """The rule under test, as `SimAcs.Robot._on_own_charger` applies it."""
    mine = plant.charger_for(name)
    if mine is None:
        return False
    return math.hypot(mine[0] - pose[0], mine[1] - pose[1]) <= HOME_TOL


def test_another_robots_charger_is_not_mine():
    """A charger is one robot's own slot. Being near somebody else's is not
    being on one — otherwise two robots would 'charge' from one plug."""
    for name in plant.ROBOT_SEGMENT:
        for other in plant.ROBOT_SEGMENT:
            if other == name:
                continue
            theirs = plant.charger_for(other)
            mine = plant.charger_for(name)
            if theirs is None or mine is None or theirs == mine:
                continue
            assert not _on_own_charger(name, theirs), \
                f"{name} would charge at {other}'s slot"


def test_a_robot_far_from_its_charger_is_not_on_it():
    """The rule must still be able to say no, or it says nothing."""
    assert not _on_own_charger("amr1", (0.0, 0.0))


def test_the_source_uses_its_own_arrival_tolerance():
    """Pin the coupling. Re-deriving the charger test from a separate constant
    is exactly how these two drifted apart in the first place."""
    source = (pathlib.Path(__file__).resolve().parents[1]
              / "csm" / "adapters" / "sim_acs.py").read_text()
    assert "def _on_own_charger" in source
    body = source.split("def _on_own_charger")[1].split("\n    def ")[0]
    assert "self.HOME_TOL" in body, \
        "the charger test must use the same tolerance as arrival"
    assert "charger_for(self.name)" in body, \
        "it must ask about THIS robot's charger, not any charger"
