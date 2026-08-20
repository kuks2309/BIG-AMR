"""DispatcherTask — "takes the oldest job, asks for transport".

The third box on the whiteboard, and the one that has no equivalent in
`MainCycle` at all. There, every IDLE job decided for itself when to submit, so
with one robot and ten queued jobs the ACS got ten submissions on the same tick
and answered BUSY nine times. That worked — the queue drained correctly — but
the MES was shouting at a fleet controller which had already said no.

This task answers the one question a single job cannot: **whose turn is it?**
That is fleet-wide information, and no job can see the queue it is standing in.

The rule is deliberately small:

    among the IDLE jobs whose own backoff has elapsed,
    grant a permit to the best one,
    and only when nobody already holds an unspent permit.

"Best" is highest priority, then oldest. Age breaks the tie so a low-priority
job cannot be starved indefinitely by a steady trickle of higher-priority work —
it eventually becomes the oldest of its priority band, and every band above it
drains first only because it is genuinely more urgent.

**One outstanding permit at a time** is what makes this a queue rather than a
crowd. It also means the dispatcher does not need to know how many robots the
fleet has: it offers one job, and if the ACS says BUSY the job comes back and
nothing else was wasted. Discovering fleet capacity would mean an interface the
ACS may not have — the interface is still undecided (ARCHITECTURE.md §10).

The period matters more than it looks. A job bounced back by t_busy needs a
fresh permit once its backoff expires, and nothing notifies anyone when a
backoff expires — time simply passes. Without a period this task would wait for
the next retirement, and a queue with nothing retiring would stall completely.
"""

from ..fsm_task import FsmTask


class DispatcherTask(FsmTask):

    name = "dispatcher"
    #: Also wakes on notify() — a new job or a retirement. This period exists
    #: for the case nothing can notify: a backoff quietly running out.
    period = 0.5

    def __init__(self, store, wakes=None, name=None, period=None):
        """
        :param store: the shared JobStore
        :param wakes: FsmTasks to notify after granting — the tracker, so the
            job moves on the next tick rather than at its own leisure.
        """
        super().__init__(name=name, period=period)
        self.store = store
        self.wakes = list(wakes or [])

        #: Permits issued. With the ACS's own submitted-job count this gives the
        #: grant-to-submission ratio; anything other than 1:1 means permits are
        #: being spent on jobs that then cannot move.
        self.granted = 0

        #: LineCapacity, or None. When set, the leg's shortfall breaks ties
        #: between jobs of equal priority — CCS manual §3.2. None leaves the
        #: sort byte-for-byte as it was, so every existing caller is unchanged.
        self.capacity = None
        #: callable(station_id) -> leg name. Needed only when `capacity` is set.
        self.leg_of = None

    def _shortfall_by_leg(self):
        """§3.2 — `(max - current) / max` per leg, higher is more starved.

        A FRACTION, NOT A COUNT. An absolute shortfall would always favour the
        leg with the biggest ceiling: leg C's ceiling is 34 and leg A's is 6, so
        leg C would win every tie while leg A starved. The percentage lets a
        small line compete fairly with a big one, which is the whole reason the
        manual specifies it this way.
        """
        if self.capacity is None or self.leg_of is None:
            return {}
        counts = {}
        for record in self.store.active:
            leg = self.leg_of(record.job.to_station)
            if leg is not None:
                counts[leg] = counts.get(leg, 0) + 1
        return {leg: self.capacity.shortfall(leg, counts.get(leg, 0))
                for leg in self.capacity.legs}

    def _candidates(self):
        """IDLE jobs that could actually move if granted.

        Filtering on backoff here rather than granting blindly is the point of
        sharing `backoff_elapsed` with t1's guard: a permit handed to a job
        still inside its backoff is a wasted turn, and with one outstanding
        permit at a time a wasted turn stalls the whole queue until the next
        period.
        """
        return [r for r in self.store.jobs_in("IDLE") if r.ctx.backoff_elapsed()]

    async def step(self):
        idle = self.store.jobs_in("IDLE")

        # Somebody already has the floor. Wait for them to use it — they will on
        # the tracker's next tick, which is faster than this task's period.
        if any(r.ctx.dispatch_permit for r in idle):
            return

        candidates = self._candidates()
        if not candidates:
            return

        # Highest priority first, then the most starved leg, then oldest.
        #
        # PRIORITY STAYS ABOVE SHORTFALL. The 2026-08-14 ACS meeting put the
        # ordering of competing jobs squarely on CSM, and priority is the field
        # that expresses it. The manual's shortfall rule decides WHICH LINE to
        # post to, not whether an urgent job waits behind a routine one — so it
        # belongs below priority, as a tie-break.
        #
        # created_at rather than state_since: a job bounced back by a busy
        # fleet keeps its place in the queue instead of going to the back of it
        # every time it is refused.
        #
        # With no LineCapacity injected every shortfall is 0.0 and this sort is
        # byte-for-byte the one it replaced.
        shortfall = self._shortfall_by_leg()

        def rank(record):
            leg = self.leg_of(record.job.to_station) if self.leg_of else None
            return (-record.job.priority,
                    -shortfall.get(leg, 0.0),
                    record.job.created_at)

        candidates.sort(key=rank)
        chosen = candidates[0]

        chosen.ctx.dispatch_permit = True
        self.granted += 1
        chosen.ctx.log(f"dispatcher: your turn ({len(idle)} waiting)")

        for task in self.wakes:
            task.notify()
