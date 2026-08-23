"""LineCapacity — how much work one leg may have in flight at once.

CCS manual §2.15, recorded in `References/local/ccs-manual-notes.md` §5. This is
NOT a policy we invented. CATL's own central control system bounds the work
outstanding against a winding line, and stops posting to that line when the
bound is reached:

    max_tasks = (turntables assigned) + (buffer racks assigned) + redundancy

    stop posting when
        AGV tasks in flight
      + material at turntable entrances
      + material on the line's buffer racks
      + material posted to this line awaiting transport
     >= max_tasks

WHY A CEILING AT ALL. Without one, a machine that keeps calling produces an
unbounded queue. Measured on 2026-08-20 over six minutes: 14 jobs created, 5
finished, and an open-call list that grew for the whole run. Nothing was broken
— every job was progressing — but intake outran service and no part of the
system said so. A ceiling is what turns "we are behind" from an emergent
property of a growing list into a fact the line can act on.

WHY IT IS A PERCENTAGE THAT DECIDES WHO IS SERVED NEXT (§3.2):

    shortfall = (max_tasks - current_tasks) / max_tasks     -- highest wins

An absolute count would always favour the biggest line. A fraction lets a leg
with a ceiling of 6 compete fairly against one with a ceiling of 34.

WHAT WE DO NOT MODEL. The manual's second term — material at turntable
entrances — has no analogue here, because we have no turntables. We count
in-flight jobs and material parked on the leg's racks, and we say so rather than
approximating the missing term with something that looks similar. See
`debt-119`.

REDUNDANCY IS NOT A NUMBER ANYBODY HAS GIVEN US. It defaults to 0. The manual
describes it as the tuning knob between lines — positive means extra pallets may
wait upstream, negative means the line is deliberately kept short — and
explicitly allows negatives. It is recorded as `debt-118`, not guessed at.
"""


class LineCapacity:
    """The §2.15 ceiling for every leg, and the §3.2 shortfall that ranks them.

    :param segments: `plant.SEGMENTS` — each entry needs `name`, `to` (the
        leg's destination ports, our analogue of the manual's turntables) and
        `buffer` (the leg's WIP racks).
    :param rack_slots: callable(rack_name) -> int, the rack's slot count.
        Injected rather than imported so the ceiling can be built against a
        test plant as easily as the real one.
    :param redundancy: int, or dict of leg name -> int. May be negative;
        the manual says so. Defaults to 0 — see `debt-118`.
    """

    def __init__(self, segments, rack_slots, redundancy=0):
        self._ports = {}
        self._buffers = {}
        for seg in segments:
            self._ports[seg["name"]] = tuple(seg.get("to", ()))
            self._buffers[seg["name"]] = tuple(seg.get("buffer", ()))
        self._rack_slots = rack_slots
        if isinstance(redundancy, dict):
            self._redundancy = dict(redundancy)
        else:
            self._redundancy = {name: redundancy for name in self._ports}

    @property
    def legs(self):
        return tuple(self._ports)

    def ceiling(self, leg):
        """`max_tasks` for one leg. None if we do not know this leg.

        Returning None rather than a default matters: an unknown leg must not
        silently acquire a ceiling of zero, which would stop the line dead.
        """
        if leg not in self._ports:
            return None
        slots = sum(self._rack_slots(rack) or 0
                    for rack in self._buffers[leg])
        ceiling = len(self._ports[leg]) + slots + self._redundancy.get(leg, 0)
        # A ceiling below one would deadlock the leg permanently — a negative
        # redundancy large enough to do that is a configuration error, not an
        # instruction to stop working.
        return max(1, ceiling)

    def in_flight(self, leg, jobs, parked=0):
        """Work already committed to this leg.

        :param jobs: the active job records. Counted when the job's own
            segment is this leg.
        :param parked: material sitting on this leg's racks — the manual's
            third term. Supplied by the caller, which owns the records.
        """
        return sum(1 for j in jobs if j == leg) + parked

    def has_room(self, leg, in_flight):
        """May another job be posted to this leg?

        An unknown leg always has room. We refuse to throttle something we
        cannot measure — the alternative is a silent stall on a leg whose
        configuration we simply failed to load.
        """
        ceiling = self.ceiling(leg)
        if ceiling is None:
            return True
        return in_flight < ceiling

    def shortfall(self, leg, in_flight):
        """§3.2 — `(max - current) / max`, higher is more starved.

        An unknown leg scores 0.0 rather than 1.0: unranked, not most urgent.
        Guessing high would let a misconfigured leg outrank every real one.
        """
        ceiling = self.ceiling(leg)
        if not ceiling:
            return 0.0
        return max(0.0, (ceiling - in_flight) / ceiling)

    def snapshot(self, in_flight_by_leg):
        """Every leg's ceiling, load and shortfall — for the dashboard.

        :param in_flight_by_leg: dict of leg -> committed work.
        """
        out = {}
        for leg in self._ports:
            ceiling = self.ceiling(leg)
            current = in_flight_by_leg.get(leg, 0)
            out[leg] = {
                "ceiling": ceiling,
                "in_flight": current,
                "shortfall": self.shortfall(leg, current),
                "at_ceiling": not self.has_room(leg, current),
            }
        return out
