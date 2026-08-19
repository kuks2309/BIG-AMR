"""JobStore — the jobs, and the bookkeeping around them.

Extracted from `MainCycle` so that the sequential driver and the concurrent
supervisor drive **the same bookkeeping** rather than two copies of it. There is
one implementation of "what happens when a job is created / stepped / retired",
and two things that call it:

    MainCycle            one thread, one tick, everything in order  (tests, demo)
    runtime/tasks.py     three independent FSMs under the Supervisor (production)

Keeping this in one place is the point. The station-latch rule below was got
wrong once already; it must not be possible to fix it in one driver and leave
the other broken.
"""

from collections import namedtuple

from ..job import Job, JobContext, Carried
from ..records import Decision, InMemoryRecords, instance_of
from ..job_fsm import build_job_fsm

#: One job and everything needed to run it.
#:
#: A namedtuple rather than a plain class because callers already unpack it
#: positionally — `job, ctx, fsm = record` — and reading `record.fsm` is clearer
#: than `record[2]`. Both work.
JobRecord = namedtuple("JobRecord", "job ctx fsm")

#: States a job never leaves.
TERMINAL = ("DONE", "FAILED")


class JobStore:

    def __init__(self, equipment, acs, clock, logger=print,
                 job_timeout_s=600.0, dispatch_gated=False, records=None):
        """
        :param records: where specification section 7's records are kept. An
            in-memory one by default, because the storage engine cannot be
            chosen yet — see `records.py` for the four customer answers that
            block it. Anything implementing `Records` substitutes here.
        :param dispatch_gated: when True, a new job may **not** submit itself to
            the ACS — it waits for a DispatcherTask to grant permission. Used by
            the concurrent runtime, where a separate FSM decides submission
            order. When False (the sequential driver) every job self-dispatches,
            which is the behaviour the existing tests describe.
        """
        self.equipment = equipment
        self.acs = acs
        self.clock = clock
        self.logger = logger
        self.job_timeout_s = job_timeout_s
        self.dispatch_gated = dispatch_gated

        #: Section 7's records. Held on the store because it is what every
        #: task already has a handle on.
        self.records = records if records is not None else InMemoryRecords()

        self.active = []            # [JobRecord]
        self.finished = []          # [Job] that reached DONE or FAILED
        self.station_busy = set()   # stations with a job still in flight
        self._job_seq = 0

    # ---------------------------------------------------------------- jobs

    def create(self, from_station, to_station, priority=0, task_type=None,
               carries=Carried.ROLL, call_id=None, reason=""):
        self._job_seq += 1
        now = self.clock()
        job = Job(
            job_id=f"job_{self._job_seq:04d}",
            from_station=from_station,
            to_station=to_station,
            priority=priority,
            created_at=now,
            state_since=now,
            carries=carries,
            # Which of the four machines each end is. Derived here rather than
            # asked of the caller: every caller already passes station names,
            # and one place deriving it cannot disagree with another.
            from_instance=instance_of(from_station),
            to_instance=instance_of(to_station),
            #: None for the WIP diversion, which CSM originates itself and
            #: which therefore answers no call.
            call_id=call_id,
        )
        # What the equipment asked for: load, unload, or swap. Carried so the
        # adapter can issue the right operation without re-deriving it.
        job.task_type = task_type
        ctx = JobContext(job, self.equipment, self.acs, self.clock,
                         logger=self.logger, job_timeout_s=self.job_timeout_s)
        # A gated store hands submission timing to the Dispatcher FSM; an
        # ungated one lets each job ask for itself, as it always has.
        ctx.dispatch_gated = self.dispatch_gated
        ctx.dispatch_permit = not self.dispatch_gated

        # WHY this job went where it did. Recorded at creation because that
        # is when the choice is made and the reasons are still in hand; a log
        # line answers it only until the log rotates.
        self.records.add_decision(Decision(
            job_id=job.job_id,
            decided_at=now,
            chosen_source=from_station,
            chosen_dest=to_station,
            priority_given=priority,
            reason=reason or "",
        ))

        record = JobRecord(job, ctx, build_job_fsm(on_change=self._on_change))
        self.active.append(record)
        self.logger(f"[{job.job_id}] created: {from_station} -> {to_station}"
                    f" ({carries.value})")
        return record

    def _on_change(self, ctx, transition):
        """Mirror the FSM's state onto the job record.

        `state_since` is reset here, and that is what makes the timeout guard
        mean "too long in *this* state" rather than "too long since the job
        existed".
        """
        job = ctx.job
        job.state_name = transition.target.name
        job.state_since = ctx.now()
        job.history.append((ctx.now(), transition.name, transition.target.name))

    # ------------------------------------------------------------- stations

    def claim_station(self, station_id):
        """Mark a station as having a job in flight. False if already claimed."""
        if station_id in self.station_busy:
            return False
        self.station_busy.add(station_id)
        return True

    def station_claimed(self, station_id):
        """Is a job already in flight against this station? Read-only.

        `claim_station` both tests and takes, which is right for the caller that
        wants the claim. The diversion scan needs to look without taking, or it
        would claim a source it then decides not to use.
        """
        return station_id in self.station_busy

    def find_finished_stations(self):
        """Stations with material waiting and no job already covering them.

        Suppression is keyed on "this station has an unfinished job", **not** on
        "I have already seen this station finished".

        The difference is the bug that stalled the line. An observation-based
        latch only clears on a tick that happens to catch the station in a
        non-finished state, so a station producing its next batch before the
        next poll stays latched for ever — the line runs two or three jobs and
        then goes quiet while batches keep completing. Keying on the job's
        lifetime makes this independent of sampling timing.
        """
        from ..adapters.base import StationStatus

        ready = []
        for station_id in self.equipment.list_stations():
            if station_id in self.station_busy:
                continue
            if self.equipment.get_station_status(station_id) is StationStatus.FINISHED:
                ready.append(station_id)
        return ready

    # ---------------------------------------------------------------- steps

    def step_all(self):
        """Advance every active job by one tick. Returns the records retired."""
        still_active, retired = [], []
        for record in self.active:
            record.fsm.step(record.ctx)
            if record.fsm.current.name in TERMINAL:
                retired.append(record)
            else:
                still_active.append(record)

        for record in retired:
            self.finished.append(record.job)
            # Free BOTH ends, whether the job succeeded or failed.
            #
            # Which end was claimed changed on 2026-08-04: the old model claimed
            # the source (the station whose output we were moving), the new one
            # claims the CALLER, which is the destination. Discarding both is
            # correct under either, and a discard of something never claimed is
            # a no-op — so this cannot leak a latch again if the direction is
            # ever revisited.
            #
            # A leaked latch does not fail loudly. The station simply stops
            # being served, for ever, while everything else keeps working.
            self.station_busy.discard(record.job.from_station)
            self.station_busy.discard(record.job.to_station)
            self.logger(f"[{record.job.job_id}] retired in "
                        f"{record.fsm.current.name}")

        self.active = still_active
        return retired

    # --------------------------------------------------------------- queries

    def jobs_in(self, *state_names):
        """Active records currently sitting in any of the named states."""
        return [r for r in self.active if r.fsm.current.name in state_names]

    def __repr__(self):
        return (f"<JobStore active={len(self.active)} "
                f"finished={len(self.finished)}>")
