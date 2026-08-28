"""Which material ships next, and from which rack.

CCS manual §1.2.1.1 and §1.2.1.2. Not policy we invented - decisions already
made and already running in CATL's plant, each with a reason on the floor.

§3.2's line selection (shortfall percentage) is NOT here: it is
`runtime.capacity.LineCapacity.shortfall` and the dispatcher already ranks by
it. FIFO by unload time is `records.ready_materials`. This is the part neither
covers - ordering ACROSS racks, and the window in which a main machine beats
an older buffer.
"""

from dataclasses import dataclass

import pytest

from csm.selection import (LONG_DWELL_SECONDS, RackTier, main_machine_wins,
                           order_racks, promote_by_dwell, rack_rank)

HOUR = 3600.0


@dataclass
class Candidate:
    name: str
    tier: RackTier
    unload_time: float = 0.0
    dwell_seconds: float = 0.0


# ------------------------------------------------- §1.2.1.2, the four tiers

def test_the_winding_buffer_appears_at_BOTH_ends():
    """The whole shape of the rule. Material that has sat in the winding
    buffer too long is the most urgent thing in the plant - closest to being
    needed, and waiting longest. Material that has just arrived there is the
    least urgent, because it is already where it is going."""
    stale = rack_rank(RackTier.WINDING_BUFFER, dwell_seconds=3 * HOUR)
    fresh = rack_rank(RackTier.WINDING_BUFFER, dwell_seconds=1 * HOUR)

    assert stale == 0, "stale winding buffer must ship first of all"
    assert fresh == 3, "fresh winding buffer must ship last of all"
    assert stale < rack_rank(RackTier.MAIN_MACHINE) < \
           rack_rank(RackTier.DIECUT_BUFFER) < fresh


def test_the_threshold_is_two_hours():
    assert LONG_DWELL_SECONDS == 2 * HOUR


def test_an_unknown_tier_sorts_last_not_first():
    """Unranked, not most urgent. Guessing high would let a misconfigured rack
    outrank every real one - the same reasoning LineCapacity.shortfall gives
    for scoring 0.0."""
    assert rack_rank(None, dwell_seconds=99 * HOUR) == 4


def test_the_full_order():
    cands = [
        Candidate("fresh-wind", RackTier.WINDING_BUFFER, 1.0, 0.5 * HOUR),
        Candidate("diecut", RackTier.DIECUT_BUFFER, 2.0),
        Candidate("machine", RackTier.MAIN_MACHINE, 3.0),
        Candidate("stale-wind", RackTier.WINDING_BUFFER, 4.0, 5 * HOUR),
    ]

    assert [c.name for c in order_racks(cands)] == [
        "stale-wind", "machine", "diecut", "fresh-wind"]


def test_ties_inside_a_tier_fall_back_to_age():
    """The order has to be total and reproducible: two racks of the same tier
    must not swap between polls, or the plan changes without the plant doing."""
    cands = [Candidate("late", RackTier.MAIN_MACHINE, 9.0),
             Candidate("early", RackTier.MAIN_MACHINE, 1.0)]

    assert [c.name for c in order_racks(cands)] == ["early", "late"]


# ------------------------------- §1.2.1.1 rule 3, the main-machine window

def test_the_manuals_own_worked_example():
    """§1.2.1.1: the oldest is on buffer rack 1801 at 2024/10/14 11:12:13 with
    X = 2 h, so it searches 11:12:13-13:12:13 for main-machine material; rack
    1501 has some, so 1501 ships."""
    t = 0.0                                   # 11:12:13
    cands = [Candidate("1801", RackTier.DIECUT_BUFFER, t),
             Candidate("1501", RackTier.MAIN_MACHINE, t + 1 * HOUR)]

    assert main_machine_wins(cands, window_seconds=2 * HOUR).name == "1501"


def test_a_main_machine_outside_the_window_does_not_win():
    """Two hours of FIFO is a cheap price for not stopping a machine. Two days
    is not."""
    t = 0.0
    cands = [Candidate("buffer", RackTier.DIECUT_BUFFER, t),
             Candidate("machine", RackTier.MAIN_MACHINE, t + 5 * HOUR)]

    assert main_machine_wins(cands, window_seconds=2 * HOUR).name == "buffer"


def test_when_the_oldest_is_already_a_main_machine_nothing_changes():
    cands = [Candidate("machine", RackTier.MAIN_MACHINE, 0.0),
             Candidate("other", RackTier.MAIN_MACHINE, 1 * HOUR)]

    assert main_machine_wins(cands, window_seconds=2 * HOUR).name == "machine"


def test_the_earliest_main_machine_inside_the_window_wins():
    t = 0.0
    cands = [Candidate("buffer", RackTier.DIECUT_BUFFER, t),
             Candidate("later", RackTier.MAIN_MACHINE, t + 1.5 * HOUR),
             Candidate("sooner", RackTier.MAIN_MACHINE, t + 0.5 * HOUR)]

    assert main_machine_wins(cands, window_seconds=2 * HOUR).name == "sooner"


def test_no_window_configured_leaves_plain_fifo():
    """What an operator who has not set 主机优先出库时间间隔 should get."""
    cands = [Candidate("buffer", RackTier.DIECUT_BUFFER, 0.0),
             Candidate("machine", RackTier.MAIN_MACHINE, 1 * HOUR)]

    assert main_machine_wins(cands, window_seconds=0).name == "buffer"
    assert main_machine_wins(cands, window_seconds=None).name == "buffer"


def test_nothing_to_choose_from():
    assert main_machine_wins([], window_seconds=HOUR) is None


# ------------------------------------- §1.3, dwell promotion on the press side

def test_main_machine_before_buffer():
    cands = [Candidate("buffer", RackTier.DIECUT_BUFFER, 0.0, 0.0),
             Candidate("machine", RackTier.MAIN_MACHINE, 5.0, 0.0)]

    assert [c.name for c in promote_by_dwell(cands, dwell_seconds=HOUR)] == [
        "machine", "buffer"]


def test_buffer_material_past_its_dwell_is_promoted():
    """Promotion stops it being starved behind every main-machine rack for
    ever. It does NOT make it more urgent than an older main-machine rack."""
    cands = [Candidate("old-machine", RackTier.MAIN_MACHINE, 0.0),
             Candidate("stale-buffer", RackTier.DIECUT_BUFFER, 5.0, 9 * HOUR),
             Candidate("new-machine", RackTier.MAIN_MACHINE, 9.0)]

    order = [c.name for c in promote_by_dwell(cands, dwell_seconds=HOUR)]

    assert order == ["old-machine", "stale-buffer", "new-machine"]


def test_no_dwell_configured_promotes_nothing():
    cands = [Candidate("stale-buffer", RackTier.DIECUT_BUFFER, 0.0, 99 * HOUR),
             Candidate("machine", RackTier.MAIN_MACHINE, 5.0)]

    assert [c.name for c in promote_by_dwell(cands, dwell_seconds=None)] == [
        "machine", "stale-buffer"]


# ------------------------------------ and what is deliberately NOT here

def test_line_selection_lives_where_it_already_lived():
    """§3.2's shortfall percentage was implemented before this module and the
    dispatcher already ranks by it. Duplicating it here would give the plant
    two answers to one question."""
    from csm.runtime.capacity import LineCapacity

    assert hasattr(LineCapacity, "shortfall")
