"""The mutual watchdog.

`MC_Enter_Permitted` condition 7 and `AGV_Entering` rule 3. These are DURATION
rules, not boolean ones, and the tests are written to fail if anyone ever
simplifies them back into a boolean check.
"""

import pytest

from csm.adapters.handshake import (BayOccupancy, ContinuousSignal,
                                    DockingHandshake, Heartbeat)


# -- there is no safe default for the comm-alarm time ------------------------

@pytest.mark.parametrize("cls", [ContinuousSignal, BayOccupancy, Heartbeat])
@pytest.mark.parametrize("bad", [None, 0, -1])
def test_the_timeout_must_be_supplied(cls, bad):
    """We do not have this number. A default would be an invented margin."""
    with pytest.raises(ValueError):
        cls(bad)


# -- condition 7: permission must be held CONTINUOUSLY -----------------------

def test_permission_is_withheld_until_held_long_enough():
    sig = ContinuousSignal(3.0)
    assert not sig.update(True, 0.0)
    assert not sig.update(True, 2.9)
    assert sig.update(True, 3.0)


def test_a_momentary_interruption_restarts_the_clock():
    """The reason this is not a boolean check.

    A signal that flickers 1-0-1 between polls passes any boolean test while
    violating condition 7. Here the accumulated time is DISCARDED, not paused.
    """
    sig = ContinuousSignal(3.0)
    sig.update(True, 0.0)
    sig.update(True, 2.9)       # nearly there
    sig.update(False, 2.95)     # one blink
    assert not sig.update(True, 3.0)
    # The new run begins at the first True AFTER the blink, t=3.0 — not at the
    # blink itself. So satisfaction is at 6.0, and 5.95 is still short.
    assert not sig.update(True, 5.0)     # 2.0 s into the new run
    assert not sig.update(True, 5.95)    # 2.95 s — still short
    assert sig.update(True, 6.0)         # 3.0 s of unbroken permission


def test_never_asserted_is_never_satisfied():
    sig = ContinuousSignal(1.0)
    for t in range(10):
        assert not sig.update(False, float(t))


# -- rule 3: the machine may only assume the robot left after SILENCE --------

def test_a_bay_never_entered_is_not_occupied():
    bay = BayOccupancy(3.0)
    bay.update(False, 0.0)
    assert not bay.occupied
    assert bay.may_machine_move


def test_entry_makes_the_bay_occupied():
    bay = BayOccupancy(3.0)
    bay.update(True, 0.0)
    assert bay.occupied
    assert not bay.may_machine_move


def test_losing_the_signal_does_not_release_the_bay():
    """The failure that would let a machine move onto a docked robot.

    Silence is not "the robot left". It is "assume the robot is still inside".
    """
    bay = BayOccupancy(3.0)
    bay.update(True, 0.0)
    bay.update(False, 0.1)      # signal lost immediately
    assert bay.occupied, "a dropped signal must not read as departure"
    assert not bay.may_machine_move
    bay.update(False, 2.9)
    assert bay.occupied


def test_only_prolonged_silence_releases_the_bay():
    bay = BayOccupancy(3.0)
    bay.update(True, 0.0)
    bay.update(False, 3.0)
    assert not bay.occupied
    assert bay.may_machine_move


def test_a_flickering_presence_keeps_the_bay_held():
    """Opposite of the permission rule, and deliberately so.

    Here an intermittent signal must keep the bay HELD — each sighting renews
    it. The two rules fail safe in opposite directions.
    """
    bay = BayOccupancy(3.0)
    t = 0.0
    bay.update(True, t)
    for _ in range(10):
        t += 2.0
        bay.update(False, t)
        t += 0.1
        bay.update(True, t)     # one sighting renews the hold
        assert bay.occupied


# -- heartbeat: absence is not health ----------------------------------------

def test_a_heartbeat_never_seen_is_not_alive():
    hb = Heartbeat(2.0)
    assert not hb.update(0.0)


def test_heartbeat_dies_after_its_timeout():
    hb = Heartbeat(2.0)
    hb.pulse(0.0)
    assert hb.update(1.9)
    assert not hb.update(2.0)


# -- the two rules together --------------------------------------------------

def test_entry_needs_both_permission_and_a_live_link():
    hs = DockingHandshake(comm_alarm_seconds=2.0)
    for t in (0.0, 1.0, 2.0):
        hs.observe(t, enter_permitted=True, agv_entering=False,
                   machine_heartbeat=True)
    assert hs.may_enter


def test_a_lost_heartbeat_withdraws_permission_immediately():
    """Condition 6: if communication is not normal, the AGV stops.

    And the permission clock restarts — regaining comms does not restore the
    time already banked, because during the outage nothing was verified.
    """
    hs = DockingHandshake(comm_alarm_seconds=2.0)
    for t in (0.0, 1.0, 2.0):
        hs.observe(t, True, False, machine_heartbeat=True)
    assert hs.may_enter

    hs.observe(4.5, True, False, machine_heartbeat=False)   # link lost
    assert not hs.may_enter

    hs.observe(5.0, True, False, machine_heartbeat=True)    # link back
    assert not hs.may_enter, "banked time must not survive the outage"
    hs.observe(7.0, True, False, machine_heartbeat=True)
    assert hs.may_enter


def test_the_pair_is_pessimistic_in_opposite_directions():
    """One object, so a caller cannot check one rule and forget the other.

    After a robot enters and everything goes quiet: it may NOT enter (no
    permission is being heard) and the machine may NOT move (the robot is
    assumed still inside). Both unsafe actions are refused at once.
    """
    hs = DockingHandshake(comm_alarm_seconds=2.0)
    hs.observe(0.0, True, True, machine_heartbeat=True)
    hs.observe(0.5, False, False, machine_heartbeat=False)  # everything stops
    assert not hs.may_enter
    assert not hs.may_machine_move
