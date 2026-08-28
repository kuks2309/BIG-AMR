# -*- coding: utf-8 -*-
"""Expiry (超期) — material too old to use, and the warning before it.

CCS manual §4.6.11. Configured per polarity, with two numbers each:

    阴极预警时间：即阴极物料超期时长-1
    阴极超期时间：即阴极物料超期时长

and the consequence, stated plainly: expired material **will not be posted
automatically** and needs a manual unlock.

THE MIRROR OF CURING. `curing.py` is a MINIMUM age — material may not be used
until it has rested. This is a MAXIMUM — material may not be used once it is
too old. They are separate modules because they fail in opposite directions and
a plant can run either, both, or neither: curing missing means feeding uncured
material, expiry missing means feeding stale material, and confusing the two
would be worse than having neither.

⚠ ONE THING THE MANUAL DOES NOT SAY. "预警时间 = 超期时长 - 1" gives no unit.
Minus one hour? One day? The surrounding parameters are durations without units
throughout §4.6.11. We take one hour and make it configurable, because the
alternative is to pick silently — and this is on the open-questions list for
CATL rather than settled by us.

EXPIRY IS NOT A DELETION. Expired material still exists, is still on its rack
and still appears in inventory. What changes is that the automatic flow will
not post it. A person unlocks it, and the manual is explicit that this is a
person's decision rather than a timeout — which is why `unlock` takes who did
it and when.
"""

from enum import Enum


class ExpiryState(Enum):
    """Where material stands against its own clock."""

    NORMAL = "normal"
    #: 预警 — inside the warning window, still usable. The whole point of a
    #: warning is that it is not yet a refusal: somebody can still act.
    WARNING = "预警"
    #: 超期 — will not be posted automatically. Not gone, not deleted.
    EXPIRED = "超期"


#: ⚠ INVENTED. "预警时间 = 超期时长 - 1" with no unit given (§4.6.11).
#: One hour, configurable, and on the list of things to ask CATL.
DEFAULT_WARNING_BEFORE = 60 * 60.0


class ExpiryPolicy:
    """How long material of each polarity may live.

    Keyed by polarity because §4.6.11 configures it that way — 阴极 and 阳极
    have their own pair of numbers. A polarity with no entry and no default
    does not expire, which is the right default for a plant that has not
    configured it: refusing material nobody has given us a lifetime for would
    stop a line on our own assumption.
    """

    def __init__(self, by_polarity=None, default=None,
                 warning_before=DEFAULT_WARNING_BEFORE):
        self._by_polarity = dict(by_polarity or {})
        self._default = default
        self._warning_before = warning_before

    def lifetime(self, polarity):
        """Seconds from the clock's start until 超期, or None for no expiry."""
        if polarity in self._by_polarity:
            return self._by_polarity[polarity]
        return self._default

    def warning_at(self, polarity):
        """Seconds until 预警, or None. Never negative and never after expiry —
        a warning window longer than the lifetime would mean material arrives
        already warning, which is not a warning, it is noise."""
        life = self.lifetime(polarity)
        if life is None:
            return None
        return max(0.0, life - self._warning_before)

    def state(self, polarity, age_seconds):
        life = self.lifetime(polarity)
        if life is None:
            return ExpiryState.NORMAL
        if age_seconds >= life:
            return ExpiryState.EXPIRED
        if age_seconds >= self.warning_at(polarity):
            return ExpiryState.WARNING
        return ExpiryState.NORMAL

    def expires(self, polarity):
        return self.lifetime(polarity) is not None
