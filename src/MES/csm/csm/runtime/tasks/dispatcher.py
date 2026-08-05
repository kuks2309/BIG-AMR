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

        # Highest priority first, then oldest. created_at rather than
        # state_since: a job bounced back by a busy fleet keeps its place in the
        # queue instead of going to the back of it every time it is refused.
        candidates.sort(key=lambda r: (-r.job.priority, r.job.created_at))
        chosen = candidates[0]

        chosen.ctx.dispatch_permit = True
        self.granted += 1
        chosen.ctx.log(f"dispatcher: your turn ({len(idle)} waiting)")

        for task in self.wakes:
            task.notify()
