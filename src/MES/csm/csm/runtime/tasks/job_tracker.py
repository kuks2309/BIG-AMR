"""JobTrackerTask — owns the lifecycle of every job.

The second box on the whiteboard. It advances each active job by exactly one
transition per tick and retires the ones that reach DONE or FAILED. All the
actual decisions live in the job FSM's guards; this task only supplies the tick.

**Why it polls and does not simply wait to be notified.** RUNNING has to ask the
ACS "has the robot arrived yet?", and nothing is going to wake us to say so —
the AcsAdapter interface is a poll (`get_job_result`), because the real ACS
interface is still undecided and may well be request/response only. A purely
reactive tracker would sit still while a robot completed its journey.

It also wakes on notify(), so a newly created job starts moving immediately
instead of waiting up to a full period.

The rate is the one MainCycle used. This layer thinks in jobs, which last
minutes; a few hertz is ample and the cost is one adapter call per running job.
"""

from ..fsm_task import FsmTask

#: 4 Hz — jobs last minutes, so this is already far finer than it needs to be.
DEFAULT_RATE_HZ = 4.0


class JobTrackerTask(FsmTask):

    name = "job_tracker"
    period = 1.0 / DEFAULT_RATE_HZ

    def __init__(self, store, wakes=None, name=None, period=None):
        """
        :param store: the shared JobStore
        :param wakes: FsmTasks to notify when a job retires. A retirement means
            the fleet just got some capacity back, which is the one event a
            Dispatcher most wants to hear about.
        """
        super().__init__(name=name, period=period)
        self.store = store
        self.wakes = list(wakes or [])

        #: Terminal jobs seen, split by outcome. The pair is worth more than the
        #: total: a system completing jobs and a system failing them both look
        #: busy from the outside.
        self.completed = 0
        self.failed = 0

    async def step(self):
        retired = self.store.step_all()
        for record in retired:
            if record.fsm.current.name == "DONE":
                self.completed += 1
            else:
                self.failed += 1

        # Only on a retirement, and once per tick rather than once per job. A
        # retirement is the event that changes what a dispatcher can do; the
        # rest of the time it would be woken four times a second to look at a
        # queue nothing had touched. Its own period covers the slower case of a
        # job that bounced back to IDLE and is waiting out its backoff.
        if retired:
            for task in self.wakes:
                task.notify()
