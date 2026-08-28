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

from .. import naming, plant
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

#: How many times work may be raised before CSM gives up on it.
#:
#: Specification assumption A7: unknown failures are "retried a bounded number
#: of times, then failed". Bounded is the important word — a job that cannot
#: succeed must eventually stop consuming a robot, and an unbounded retry turns
#: one broken station into a fleet that never does anything else.
MAX_ATTEMPTS = 3


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
        #: Work raised again after a failure. Worth counting apart from jobs
        #: created: a rising number here is a line that is struggling, not a
        #: line that is busy.
        self.retried = 0
        #: Calls given back to the machine after CSM ran out of attempts.
        #: Every one of these ends in an alarm and a person, so this number is
        #: the count of times the line needed a human.
        self.abandoned = 0
        self._job_seq = 0

    # ---------------------------------------------------------------- jobs

    def create(self, from_station, to_station, priority=0, task_type=None,
               carries=Carried.ROLL, call_id=None, reason="",
               material_ref=None, attempt=1, retry_of=None,
               requester=None):
        self._job_seq += 1
        now = self.clock()
        # THE ID IS THE WORKSHOP DECK'S NAME PLUS A COUNTER, so it explains
        # itself wherever it appears — our records, the fleet controller's own
        # logs, an error message — with no lookup. Built here, once, because
        # the id must be fixed at creation and never change afterwards: it is
        # what every later ACS operation names the order by.
        #
        # The requester is the station that RAISED THE CALL, which is not
        # always the source. A machine calling for material names itself while
        # the material comes from somewhere else.
        segment = plant.segment_of_station(from_station) \
            or plant.segment_of_station(to_station)
        leg = segment["name"] if isinstance(segment, dict) else segment
        _sketch = Job(job_id="", from_station=from_station,
                      to_station=to_station, carries=carries)
        job = Job(
            job_id=naming.job_id(_sketch, leg, self._job_seq,
                                 requester=requester),
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
            material_ref=material_ref,
            attempt=attempt,
            retry_of=retry_of,
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

        # PERSIST IT NOW, not when it finishes. A job written only at the end
        # is a job that never existed if the process dies mid-flight, which is
        # exactly the case the record is for.
        self.records.save_job(job, at=now)

        record = JobRecord(job, ctx, build_job_fsm(on_change=self._on_change))
        self.active.append(record)
        self.logger(f"[{job.job_id}] created: {from_station} -> {to_station}"
                    f" ({carries.value})")
        return record

    def _raise_again(self, failed):
        """Re-raise the work a failed job was carrying, within the ceiling.

        THE WORK OUTLIVES THE JOB. A transport that failed does not mean the
        material stopped needing to move — but nothing raised it again, so it
        was simply lost: the ACS order cancelled, the job retired, and the
        machine's call already acknowledged, so the equipment had stopped
        asking and no one was coming. Nothing reported it, because from every
        component's point of view its own part had finished.

        Not every failure comes back. An invalid job and one a person cancelled
        are answers, not accidents, and repeating them argues with the answer.
        The ceiling is specification A7's "bounded number of times".
        """
        if not failed.retryable:
            self.logger(f"[{failed.job_id}] not retried: "
                        f"{failed.failure_reason or 'terminal failure'}")
            self._hand_back(failed)
            return None
        if failed.attempt >= MAX_ATTEMPTS:
            # Loud, because this is where work is genuinely abandoned and
            # somebody has to know the material is still standing there.
            self.logger(f"[{failed.job_id}] GIVING UP after "
                        f"{failed.attempt} attempts: "
                        f"{failed.from_station} -> {failed.to_station} "
                        f"({failed.failure_reason})")
            self._hand_back(failed)
            return None

        replacement = self.create(
            failed.from_station, failed.to_station,
            priority=failed.priority,
            task_type=getattr(failed, "task_type", None),
            carries=failed.carries,
            call_id=failed.call_id,
            material_ref=failed.material_ref,
            attempt=failed.attempt + 1,
            retry_of=failed.job_id,
            reason=f"attempt {failed.attempt + 1} of {MAX_ATTEMPTS} after "
                   f"{failed.job_id} failed: {failed.failure_reason}",
        )
        self.retried += 1
        self.logger(f"[{replacement.job.job_id}] raised again for "
                    f"{failed.job_id} (attempt {failed.attempt + 1})")
        return replacement

    def _hand_back(self, failed):
        """Tell the machine we are not coming. Specification C9.

        THE ACKNOWLEDGEMENT WAS A PROMISE. A machine stops calling the moment
        it sees `AGV_Task_Recive = 1`, so every call CSM answers leaves a
        machine silent and waiting. Retiring the job without this leaves it
        waiting for ever — and the failure is invisible, because the call
        succeeded, the job finished, and only the material knows.

        Run when the work is ABANDONED, not when it is retried. A retry is
        still us coming; there is nothing to tell the machine and telling it
        anyway would alarm a station over a job that is about to be served.

        Deliberately NOT part of the job FSM. The job is already retired; this
        is a conversation between CSM and the machine about the CALL, and it
        outlives the job that answered it.
        """
        if failed.call_id is None:
            # CSM's own work — the WIP diversion answers no call, so there is
            # nobody waiting to be told.
            return None
        call = self.records.call(failed.call_id)
        if call is None:
            self.logger(f"[{failed.job_id}] abandoned, but call "
                        f"{failed.call_id} is not on record — the machine "
                        f"cannot be told")
            return None

        now = self.clock()
        self.records.cancel_call(failed.call_id, at=now)
        cancel = self.equipment.cancel_task(
            call.station, failed.job_id, now, call_id=failed.call_id)
        self.abandoned += 1
        self.logger(f"[{failed.job_id}] handing {failed.call_id} back to "
                    f"{call.station} — AGV_Task_Processing = 9")
        return cancel

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

        # AND WHERE THE MATERIAL NOW IS. Done here rather than in the Done
        # state because this is the one place that sees every transition and
        # also holds the records; the FSM's context deliberately does not.
        #
        # Only on success. A failed job did not move anything, and recording a
        # movement that did not happen is worse than recording none — the whole
        # point of the history is that it can be trusted.
        if job.material_ref and transition.target.name == "DONE":
            self.records.move_material(job.material_ref, job.to_station,
                                       at=ctx.now(), job_id=job.job_id,
                                       note=f"{job.carries.value} delivered")
            self._hand_identity_to(job, ctx.now())

        # AND THE JOB ITSELF. On transitions only — the tracker steps every job
        # four times a second, and writing that often would be all I/O and no
        # information. `finished` is passed rather than inferred: which states
        # are terminal is the FSM's knowledge, and it should not be restated in
        # the records layer where it could drift.
        self.records.save_job(
            job, at=ctx.now(),
            finished=transition.target.name in ("DONE", "FAILED"))

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

    # ------------------------------------------------- where the material IS

    def _hand_identity_to(self, job, now):
        """CCS manual §4.6.6 — completion writes what was carried INTO THE
        TARGET RACK.

        "the task's carried information — material type, material attribute,
        bobbin type and roll number — into the TARGET rack". The task is the
        carrier of identity and delivery is what transfers it, which is why
        this belongs on the DONE transition and nowhere else.

        Only where the destination IS a rack. A machine port is not modelled
        this way and deliberately so: the ACS team described their own system
        the same way — carrier identity vanishes at an equipment station and
        persists at the buffer.
        """
        if not self.records.slots(job.to_station):
            return                          # not a rack; nothing to write to
        known = self.records.material(job.material_ref)
        if known is None:
            return
        slot = self.records.park(
            job.to_station, material_ref=job.material_ref,
            job_id=job.job_id, at=now,
            material_type=known.material_type,
            material_attribute=known.attribute,
            bobbin_type=known.drum_type)
        if slot is None:
            # The rack filled between choosing it and arriving. Worth saying —
            # the pallet is physically there and the record cannot show which
            # slot, which is exactly the kind of silent divergence §5 is full of.
            self.logger(f"[{job.job_id}] delivered to {job.to_station} but "
                        f"every slot is taken — identity not recorded")


    def _carrier_of(self, job_id):
        """The robot that has this job on its deck right now, or None.

        Asked of the ACS rather than remembered here, because which robot has
        which job is the ACS's knowledge and it can reassign one. `loaded` is
        the vehicle layer's own observation — the dwell at the source finished,
        so the thing is physically on the deck.
        """
        acs = getattr(self, "acs", None)
        if acs is None or not hasattr(acs, "fleet_status"):
            return None
        try:
            rows = acs.fleet_status() or []
        except Exception:
            return None
        for row in rows:
            if row.get("job_id") == job_id and row.get("loaded"):
                return row.get("name")
        return None

    def _follow_the_material(self, job):
        """Put the material where it actually is: ON THE ROBOT, in transit.

        THE RECORD USED TO BE FALSE FOR THE WHOLE JOURNEY. `move_material` was
        called once, on DONE, so a roll sat in the records at its source while
        a robot drove it across the plant, and then teleported. "Where is roll
        X" had no true answer for minutes at a time, and the movement history
        recorded a jump that never happened.

        Called every tick and guarded on the location actually changing, so it
        writes one move when the robot picks the material up and nothing
        afterwards. The DONE handler still writes the arrival — this adds the
        middle, it does not replace the end.
        """
        if not job.material_ref:
            return
        carrier = self._carrier_of(job.job_id)
        if carrier is None:
            return
        known = self.records.material(job.material_ref)
        if known is None or known.location == carrier:
            return
        self.records.move_material(job.material_ref, carrier, at=self.clock(),
                                   job_id=job.job_id,
                                   note=f"{job.carries.value} loaded")

    # ---------------------------------------------------------------- steps

    def step_all(self):
        """Advance every active job by one tick. Returns the records retired."""
        still_active, retired = [], []
        for record in self.active:
            self._follow_the_material(record.job)
            record.fsm.step(record.ctx)
            if record.fsm.current.name in TERMINAL:
                retired.append(record)
            else:
                still_active.append(record)

        replacements = []
        for record in retired:
            self.finished.append(record.job)
            if record.fsm.current.name == "FAILED":
                replacements.append(record.job)
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

        # RAISE THE WORK AGAIN — after `self.active` has been rebuilt, because
        # `create` appends to it and doing this inside the loop above would
        # have the new jobs wiped by the reassignment.
        for job in replacements:
            self._raise_again(job)
        return retired

    # --------------------------------------------------------------- queries

    def jobs_in(self, *state_names):
        """Active records currently sitting in any of the named states."""
        return [r for r in self.active if r.fsm.current.name in state_names]

    def __repr__(self):
        return (f"<JobStore active={len(self.active)} "
                f"finished={len(self.finished)}>")
