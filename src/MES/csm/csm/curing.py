# -*- coding: utf-8 -*-
"""Curing (숙성) — how long material must rest before the next process.

WHY THIS EXISTS AS ITS OWN THING. The handbook calls curing "the requirement
nobody told us about" and is blunt about the state of it:

    CSM must track elapsed curing time per item and release only what is ready.
    ...
    This is a stateful obligation lasting hours, surviving restarts. Nothing in
    the current code model supports it.

Four details from [HB] §3 that each change the design, and are easy to miss:

  * **6 hours in some places, 10 hours in others.** So the duration is per
    process, not one constant.
  * **The elapsed time must survive a power cut.** So the clock is a recorded
    start, not a timer object.
  * **If the destination rack is full, the item is routed elsewhere and cures
    there — and MUST NOT CURE TWICE.** So starting the clock is idempotent.
    This is the one that a naive "set ready_at when you park it" gets wrong,
    and it gets it wrong in the expensive direction: material that has already
    rested six hours is made to rest six more.
  * **Some processes have no curing at all, so it must be switchable per
    process.** So "no curing here" has to be expressible, and has to be
    different from "we were not told".

And one from the CCS manual (§4.6.12), which is the only place we have seen a
shipped default:

    静置为非标准功能，静置时间一般设置为 0
    resting is a non-standard feature and the resting time is normally 0.

So the shipped behaviour is no curing. Our default matches that, and anything
else is configuration somebody has to state.

THREE ANSWERS, NOT TWO. `None` means we were never told, `0` means this process
does not cure, and a positive number is a duration. Collapsing the first two is
how a plant ends up feeding uncured material while the log says everything is
fine — `records.unrested_decisions` counts exactly that case today.
"""


class CuringPolicy:
    """How long each process makes material rest.

    Keyed by whatever the caller uses to name a process or a material type —
    this module does not care which, because the customer has not told us which
    it is. [HB] §3 says "per process"; CCS manual §4.6.12 configures it per
    material type. Until that is settled, the key is a string and the caller
    owns its meaning.
    """

    #: The shipped default, from CCS manual §4.6.12. Not a guess.
    SHIPPED_DEFAULT = 0.0

    def __init__(self, by_key=None, default=None):
        """:param by_key: {name: seconds}. 0 means "this one does not cure".
        :param default: seconds for anything not listed. **None means we were
            not told**, which is not the same as zero and is reported as such.
        """
        self._by_key = dict(by_key or {})
        self._default = default

    def seconds_for(self, key):
        """Seconds of rest required, 0 for none, or None if we were not told."""
        if key in self._by_key:
            return self._by_key[key]
        return self._default

    def requires_curing(self, key):
        """True only when we KNOW a positive duration is required.

        Unknown answers False here on purpose: this question is asked to decide
        whether to start a clock, and starting one on a guess would hold
        material for a duration nobody specified. Whether unknown material may
        be FED is a different question and belongs to `records.is_ready`, which
        has its own documented answer and counts how often it is used.
        """
        seconds = self.seconds_for(key)
        return seconds is not None and seconds > 0

    def known(self, key):
        return self.seconds_for(key) is not None

    def with_key(self, key, seconds):
        """A copy with one more rule. Policies are configuration; treating them
        as immutable keeps one from being edited underneath a running line."""
        merged = dict(self._by_key)
        merged[key] = seconds
        return CuringPolicy(merged, self._default)

    def __repr__(self):
        return (f"CuringPolicy({self._by_key!r}, default={self._default!r})")


#: The two durations the customer has actually named, in seconds.
#:
#: [HB] §3: "6 hours in some places, 10 hours in others". The Small AGV job
#: description puts numbers to it — 6 h at the cathode winding WIP, 10 h at the
#: anode. Written here so that a reader meets the source, not a magic number.
SIX_HOURS = 6 * 60 * 60.0
TEN_HOURS = 10 * 60 * 60.0
