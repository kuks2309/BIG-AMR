# -*- coding: utf-8 -*-
"""Which material ships next, and from which rack.

CCS manual §1.2.1.1 and §1.2.1.2 — the ordering rules CATL's own dispatcher
uses. These are not policy we invented; they are decisions already made and
already running in a plant, and each one has a reason on the floor.

WHAT IS ALREADY ELSEWHERE. §3.2's line selection — shortfall percentage
`(max - current) / max` — is `runtime.capacity.LineCapacity.shortfall`, and the
dispatcher ranks by it. FIFO by unload time is `records.ready_materials`. This
module is the part neither of those covers: ordering ACROSS RACKS, and the
window in which a main machine beats an older buffer.

THE MODULE DOES NOT KNOW OUR PLANT. It is given a tier per rack and a dwell per
candidate; which of our racks is a "winding buffer" is the caller's business.
Keeping the mapping out means the rule can be read against the manual without
also reading plant.py.
"""

from enum import Enum


class RackTier(Enum):
    """Where a rack sits in the flow. CCS manual §1.2.1.2."""

    #: The consuming end's buffer — material already posted toward winding.
    WINDING_BUFFER = "winding_buffer"
    #: A machine's own rack. Full ones block the machine.
    MAIN_MACHINE = "main_machine"
    #: The producing end's buffer.
    DIECUT_BUFFER = "diecut_buffer"


#: §1.2.1.2's threshold: material that has sat in the winding buffer longer
#: than this is the most urgent thing in the plant.
LONG_DWELL_SECONDS = 2 * 60 * 60.0


def rack_rank(tier, dwell_seconds=0.0, long_dwell=LONG_DWELL_SECONDS):
    """Lower ships first. CCS manual §1.2.1.2, four tiers:

        winding buffer dwelling > 2 h
          -> main machine
          -> diecut buffer
          -> winding buffer dwelling < 2 h

    THE WINDING BUFFER APPEARS AT BOTH ENDS, and that is the whole shape of the
    rule. Material that has sat there too long is the most urgent thing in the
    plant — it is closest to being needed and has been waiting longest.
    Material that has just arrived there is the least urgent, because it is
    already where it is going. Nothing in our own design had this shape.

    `dwell_seconds` defaults to 0 because only the winding buffer reads it —
    a main machine rack and a diecut buffer rank the same however long their
    material has sat, so requiring the caller to supply it would be asking for
    a number that changes nothing.

    An unknown tier sorts last rather than first: unranked, not most urgent.
    Guessing high would let a misconfigured rack outrank every real one — the
    same reasoning `LineCapacity.shortfall` gives for scoring 0.0.
    """
    if tier is RackTier.WINDING_BUFFER:
        return 0 if (dwell_seconds or 0.0) > long_dwell else 3
    if tier is RackTier.MAIN_MACHINE:
        return 1
    if tier is RackTier.DIECUT_BUFFER:
        return 2
    return 4


def order_racks(candidates, long_dwell=LONG_DWELL_SECONDS):
    """Sort candidates into shipping order.

    Each candidate is anything with `.tier` and `.dwell_seconds`; ties fall
    back to `.unload_time` so the order is total and reproducible. Stable
    within a tier, which matters: two racks of the same tier and the same age
    must not swap between polls, or the plan changes without the plant doing.
    """
    return sorted(
        candidates,
        key=lambda c: (rack_rank(c.tier, c.dwell_seconds, long_dwell),
                       c.unload_time))


def main_machine_wins(candidates, window_seconds):
    """§1.2.1.1 rule 3. FIFO, unless a main machine is close behind.

    The rule: ship the earliest-unloaded material. BUT if the oldest is on a
    BUFFER rack, look forward over `[oldest.unload_time, oldest.unload_time +
    X]` for material on a MAIN MACHINE rack, and ship that instead.

    The manual's own worked example: the oldest is on buffer rack 1801 at
    2024/10/14 11:12:13 with X = 2 h, so it searches 11:12:13-13:12:13 for
    main-machine material; rack 1501 has some, so 1501 ships.

    THE REASON IS NOT IN THE MANUAL BUT IS OBVIOUS ON THE FLOOR: a machine rack
    that stays full blocks the machine. A buffer rack that stays full blocks
    nothing. Two hours of FIFO is a cheap price for not stopping a machine.

    Returns the chosen candidate, or None if there are none. A window of 0 or
    None disables the rule and leaves plain FIFO, which is what an operator who
    has not configured 主机优先出库时间间隔 should get.
    """
    if not candidates:
        return None
    oldest = min(candidates, key=lambda c: c.unload_time)
    if not window_seconds or oldest.tier is RackTier.MAIN_MACHINE:
        return oldest
    limit = oldest.unload_time + window_seconds
    inside = [c for c in candidates
              if c.tier is RackTier.MAIN_MACHINE
              and oldest.unload_time <= c.unload_time <= limit]
    if not inside:
        return oldest
    return min(inside, key=lambda c: c.unload_time)


def promote_by_dwell(candidates, dwell_seconds):
    """§1.3, the cold-press side: main machine racks before buffer racks, but
    buffer material past 冷压缓存区物料优先时长 is promoted.

    Promotion means "treat it as a main machine rack for ordering purposes" —
    it does not make it more urgent than a genuinely older main-machine rack,
    it stops it being starved behind every one of them for ever.
    """
    def rank(c):
        promoted = (c.tier is RackTier.DIECUT_BUFFER and dwell_seconds
                    and (c.dwell_seconds or 0.0) > dwell_seconds)
        tier = RackTier.MAIN_MACHINE if promoted else c.tier
        return (rack_rank(tier, c.dwell_seconds), c.unload_time)

    return sorted(candidates, key=rank)
