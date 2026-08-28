"""Curing (숙성) — the requirement nobody told us about.

[HB] §3 is blunt about where we were: "CSM must track elapsed curing time per
item and release only what is ready... This is a stateful obligation lasting
hours, surviving restarts. Nothing in the current code model supports it."

Four details from that section drive every test below:

  * 6 hours in some places, 10 in others - so it is per process, not a constant
  * the elapsed time must survive a power cut  - so it is a recorded start
  * material routed elsewhere MUST NOT CURE TWICE - so starting is idempotent
  * some processes have no curing - so "none" and "not told" are different

And CCS manual §4.6.12, the only shipped default we have seen:
静置为非标准功能，静置时间一般设置为 0 - resting is non-standard, normally 0.
"""

import pytest

from csm.curing import SIX_HOURS, TEN_HOURS, CuringPolicy
from csm.records import InMemoryRecords


def store_with(at=0.0):
    """A store holding one roll. `register_material` mints the LOT id itself,
    so the ref comes back rather than going in."""
    r = InMemoryRecords()
    r.ref = r.register_material(kind="roll", at=at).material_ref
    return r


# ------------------------------------------------------- the three answers

def test_a_process_that_does_not_cure_is_not_the_same_as_one_we_were_not_told():
    """Collapsing these is how a plant feeds uncured material while the log
    says everything is fine."""
    p = CuringPolicy({"winding": SIX_HOURS, "slitting": 0.0})

    assert p.seconds_for("slitting") == 0.0        # this one does not cure
    assert p.seconds_for("coating") is None        # we were never told
    assert p.known("slitting") is True
    assert p.known("coating") is False


def test_only_a_known_positive_duration_starts_a_clock():
    """Unknown must not start one - holding material for a duration nobody
    specified is worse than the question it was trying to answer."""
    p = CuringPolicy({"winding": SIX_HOURS, "slitting": 0.0})

    assert p.requires_curing("winding") is True
    assert p.requires_curing("slitting") is False
    assert p.requires_curing("coating") is False


def test_the_shipped_default_is_no_curing():
    """CCS manual §4.6.12. Our default has to match what the real system does,
    not what we imagine it should do."""
    assert CuringPolicy.SHIPPED_DEFAULT == 0.0


def test_the_two_durations_the_customer_actually_named():
    assert SIX_HOURS == 6 * 3600
    assert TEN_HOURS == 10 * 3600


# ------------------------------------------------------------- the clock

def test_material_is_not_ready_until_it_has_rested():
    r = store_with()
    r.begin_curing(r.ref, at=1000.0, seconds=SIX_HOURS)

    assert r.is_ready(r.ref, now=1000.0) is False
    assert r.is_ready(r.ref, now=1000.0 + SIX_HOURS - 1) is False
    assert r.is_ready(r.ref, now=1000.0 + SIX_HOURS) is True


def test_how_long_is_left():
    r = store_with()
    r.begin_curing(r.ref, at=0.0, seconds=SIX_HOURS)

    assert r.cure_remaining(r.ref, now=0.0) == SIX_HOURS
    assert r.cure_remaining(r.ref, now=3600.0) == SIX_HOURS - 3600
    assert r.cure_remaining(r.ref, now=SIX_HOURS + 99) == 0.0


def test_material_that_is_not_curing_has_no_remainder():
    """None, not zero. Zero would read as "finished curing", which it has not
    done, because it never started."""
    r = store_with()

    assert r.cure_remaining(r.ref, now=0.0) is None


# ---------------------------------------------- and it must not cure twice

def test_moving_material_to_another_rack_does_not_restart_the_clock():
    """[HB] §3: "If the destination rack is full, the item is routed elsewhere
    and cures there - and must not cure twice."

    Getting this wrong costs six hours per affected roll, silently, and shows
    up only as a line that is mysteriously slow.
    """
    r = store_with()
    r.begin_curing(r.ref, at=0.0, seconds=SIX_HOURS)

    # five hours later it is moved, and the destination starts curing again
    r.begin_curing(r.ref, at=5 * 3600.0, seconds=SIX_HOURS)

    assert r._materials[r.ref].cure_started_at == 0.0
    assert r.is_ready(r.ref, now=SIX_HOURS) is True, \
        "the clock restarted - the roll is being made to rest twice"


def test_a_zero_duration_starts_nothing():
    r = store_with()
    r.begin_curing(r.ref, at=0.0, seconds=0.0)

    assert r._materials[r.ref].cure_started_at is None
    assert r.is_ready(r.ref, now=0.0) is True


def test_an_unknown_duration_starts_nothing():
    r = store_with()
    r.begin_curing(r.ref, at=0.0, seconds=None)

    assert r._materials[r.ref].cure_started_at is None


# ------------------------------------------- how it meets what was there

def test_a_running_clock_beats_a_ready_at_set_from_a_weaker_source():
    """Knowledge beats a guess. `ready_at` may have been set by anything;
    a clock we started ourselves is the thing we actually know."""
    r = store_with()
    r.set_ready_at(r.ref, when=0.0)                # "ready now"
    r.begin_curing(r.ref, at=0.0, seconds=SIX_HOURS)

    assert r.is_ready(r.ref, now=3600.0) is False


def test_material_with_no_clock_still_follows_the_old_documented_rule():
    """Unknown counts as READY and is counted. That decision predates this
    file and is unchanged - curing adds a better answer where it has one, and
    changes nothing where it does not."""
    r = store_with()

    assert r.is_ready(r.ref, now=0.0) is True
    assert r.unrested_decisions == 1


def test_curing_material_is_kept_out_of_the_feed_list():
    """`ready_materials` is what selection reads, so this is where curing
    actually bites."""
    r = InMemoryRecords()
    old = r.register_material(kind="roll", at=0.0).material_ref
    new = r.register_material(kind="roll", at=10.0).material_ref
    r.move_material(old, to_location="WIP", at=0.0)
    r.move_material(new, to_location="WIP", at=10.0)
    r.begin_curing(old, at=0.0, seconds=SIX_HOURS)

    refs = [m.material_ref for m in r.ready_materials("WIP", now=3600.0)]

    assert refs == [new], "uncured material was offered to a machine"


# --------------------------------------------------- surviving a power cut

def test_the_elapsed_time_survives_a_restart(tmp_path):
    """[HB] §3 requires exactly this, and it is the only reason the clock is a
    recorded start rather than a timer object."""
    from csm.records_sqlite import SqliteRecords

    path = str(tmp_path / "curing.db")
    first = SqliteRecords(path)
    ref = first.register_material(kind="roll", at=0.0).material_ref
    first.begin_curing(ref, at=0.0, seconds=SIX_HOURS)

    again = SqliteRecords(path)

    assert again.cure_remaining(ref, now=3600.0) == SIX_HOURS - 3600
    assert again.is_ready(ref, now=3600.0) is False
    assert again.is_ready(ref, now=SIX_HOURS) is True


def test_a_restart_does_not_restart_the_clock(tmp_path):
    """The two failure modes together: if a restart reset the start, every
    power cut would cost six hours of every roll in the plant."""
    from csm.records_sqlite import SqliteRecords

    path = str(tmp_path / "curing.db")
    first = SqliteRecords(path)
    ref = first.register_material(kind="roll", at=0.0).material_ref
    first.begin_curing(ref, at=0.0, seconds=SIX_HOURS)

    again = SqliteRecords(path)
    again.begin_curing(ref, at=5 * 3600.0, seconds=SIX_HOURS)

    assert again.is_ready(ref, now=SIX_HOURS) is True
