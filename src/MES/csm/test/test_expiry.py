"""Expiry (超期) — material too old to use, and the warning before it.

CCS manual §4.6.11, configured per polarity:

    阴极预警时间：即阴极物料超期时长-1
    阴极超期时间：即阴极物料超期时长

and the consequence: expired material will not be posted automatically and
needs a MANUAL UNLOCK.

The mirror of curing. `curing.py` is a MINIMUM age, this is a MAXIMUM. They
fail in opposite directions - curing missing means feeding uncured material,
expiry missing means feeding stale material - which is why they are separate
modules and why `ready_materials` asks both.
"""

import pytest

from csm.expiry import DEFAULT_WARNING_BEFORE, ExpiryPolicy, ExpiryState
from csm.records import InMemoryRecords

HOUR = 3600.0
DAY = 24 * HOUR


# --------------------------------------------------------------- the policy

def test_a_polarity_with_no_lifetime_does_not_expire():
    """Refusing material nobody has given us a lifetime for would stop a line
    on our own assumption."""
    p = ExpiryPolicy()

    assert p.lifetime("cathode") is None
    assert p.expires("cathode") is False
    assert p.state("cathode", age_seconds=99 * DAY) is ExpiryState.NORMAL


def test_each_polarity_has_its_own_pair():
    """§4.6.11 configures 阴极 and 阳极 separately."""
    p = ExpiryPolicy({"cathode": 3 * DAY, "anode": 5 * DAY})

    assert p.lifetime("cathode") == 3 * DAY
    assert p.lifetime("anode") == 5 * DAY


def test_the_warning_comes_before_expiry():
    p = ExpiryPolicy({"cathode": 3 * DAY})

    assert p.warning_at("cathode") == 3 * DAY - DEFAULT_WARNING_BEFORE
    assert p.state("cathode", 3 * DAY - DEFAULT_WARNING_BEFORE - 1) is ExpiryState.NORMAL
    assert p.state("cathode", 3 * DAY - DEFAULT_WARNING_BEFORE) is ExpiryState.WARNING
    assert p.state("cathode", 3 * DAY) is ExpiryState.EXPIRED


def test_a_warning_window_longer_than_the_lifetime_is_clamped():
    """Material that arrives already warning is not a warning, it is noise."""
    p = ExpiryPolicy({"cathode": 10.0}, warning_before=99 * DAY)

    assert p.warning_at("cathode") == 0.0
    assert p.state("cathode", age_seconds=0.0) is ExpiryState.WARNING


def test_the_warning_offset_is_ours_and_is_marked_as_such():
    """The manual says 预警时间 = 超期时长 - 1 and gives NO UNIT. We take an
    hour, configurable, and it is on the list to ask CATL - the alternative is
    to pick silently."""
    assert DEFAULT_WARNING_BEFORE == HOUR

    p = ExpiryPolicy({"cathode": 3 * DAY}, warning_before=DAY)

    assert p.warning_at("cathode") == 2 * DAY


# ------------------------------------------------------- the store's gate

def with_material(expires_at=None):
    r = InMemoryRecords()
    m = r.register_material(kind="roll", at=0.0, location="WIP")
    m.expires_at = expires_at
    r.ref = m.material_ref
    return r


def test_material_with_no_expiry_is_never_expired():
    """Unknown is not expired - the same reasoning is_ready gives for unknown
    counting as ready."""
    r = with_material(expires_at=None)

    assert r.is_expired(r.ref, now=99 * DAY) is False


def test_material_past_its_expiry_is_expired():
    r = with_material(expires_at=100.0)

    assert r.is_expired(r.ref, now=99.0) is False
    assert r.is_expired(r.ref, now=100.0) is True


def test_expired_material_is_not_offered_to_a_machine():
    """§4.6.11: it will not be posted automatically. This is where that bites."""
    r = with_material(expires_at=100.0)

    assert [m.material_ref for m in r.ready_materials("WIP", now=99.0)] == [r.ref]
    assert r.ready_materials("WIP", now=101.0) == []


def test_fefo_honours_expiry_too():
    """Ordering by expiry while still offering expired material would put the
    worst thing first."""
    r = with_material(expires_at=100.0)

    assert r.expiring_first("WIP", now=101.0) == []


# ------------------------------------------------- the manual unlock

def test_a_person_can_unlock_expired_material():
    r = with_material(expires_at=100.0)
    assert r.is_expired(r.ref, now=200.0) is True

    r.unlock_expired(r.ref, by="line-lead", at=150.0)

    assert r.is_expired(r.ref, now=200.0) is False
    assert r.ready_materials("WIP", now=200.0) != []


def test_the_unlock_records_who_and_when():
    """The manual makes this a human decision, and a decision with nobody's
    name on it is one nobody can be asked about."""
    r = with_material(expires_at=100.0)

    r.unlock_expired(r.ref, by="line-lead", at=150.0)
    m = r.material(r.ref)

    assert m.unlocked_by == "line-lead"
    assert m.unlocked_at == 150.0


def test_expiry_is_not_a_deletion():
    """Expired material still exists, is still where it was, and still appears
    in inventory. Only the automatic flow declines it."""
    r = with_material(expires_at=100.0)

    assert r.material(r.ref) is not None
    assert [m.material_ref for m in r.materials_at("WIP")] == [r.ref]


def test_the_unlock_survives_a_restart(tmp_path):
    """A decision that did not survive would be taken again every restart -
    and the material would expire again in front of the person who unlocked
    it."""
    from csm.records_sqlite import SqliteRecords

    path = str(tmp_path / "expiry.db")
    first = SqliteRecords(path)
    m = first.register_material(kind="roll", at=0.0, location="WIP")
    m.expires_at = 100.0
    first._save_material(m)
    first.unlock_expired(m.material_ref, by="line-lead", at=150.0)

    again = SqliteRecords(path)

    assert again.is_expired(m.material_ref, now=200.0) is False
    assert again.material(m.material_ref).unlocked_by == "line-lead"


# ------------------------------------------- curing and expiry together

def test_material_must_have_rested_AND_not_gone_stale():
    """Opposite ends of one axis. Both gates, or neither is meaningful."""
    from csm.curing import SIX_HOURS

    r = InMemoryRecords()
    m = r.register_material(kind="roll", at=0.0, location="WIP")
    m.expires_at = 10 * HOUR
    r.begin_curing(m.material_ref, at=0.0, seconds=SIX_HOURS)

    assert r.ready_materials("WIP", now=1 * HOUR) == [], "not rested yet"
    assert r.ready_materials("WIP", now=7 * HOUR) != [], "rested, not stale"
    assert r.ready_materials("WIP", now=11 * HOUR) == [], "gone stale"
