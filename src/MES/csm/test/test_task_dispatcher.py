"""Tests for DispatcherTask — whose turn is it?

The behaviour worth protecting is that this is a *queue*, not a crowd: one
outstanding permit at a time, granted on priority then age, and never to a job
that could not act on it.
"""

import asyncio
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters.base import AcsAdapter, TransportResult                # noqa: E402
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment  # noqa: E402
from csm.runtime.job_store import JobStore                   # noqa: E402
from csm.runtime.tasks import DispatcherTask, JobTrackerTask  # noqa: E402


def build(travel=2.0):
    clock = ManualClock()
    equipment = MockEquipment(["station_3", "station_9"], clock)
    store = JobStore(equipment, MockAcs(clock, travel_seconds=travel), clock,
                     logger=lambda m: None, dispatch_gated=True)
    return clock, store, DispatcherTask(store), JobTrackerTask(store)


def step(task):
    asyncio.run(task.step())


def permitted(store):
    return [r.job.job_id for r in store.active if r.ctx.dispatch_permit]


class Spy:
    def __init__(self):
        self.woken = 0

    def notify(self):
        self.woken += 1


# ------------------------------------------------------------ one at a time

def test_only_one_permit_is_outstanding():
    """This is what makes it a queue rather than a crowd."""
    _, store, dispatcher, _ = build()
    for _ in range(5):
        store.create("station_3", "station_9")

    step(dispatcher)
    assert len(permitted(store)) == 1

    for _ in range(5):
        step(dispatcher)
    assert len(permitted(store)) == 1
    assert dispatcher.granted == 1


def test_the_next_job_is_granted_once_the_first_moves_on():
    _, store, dispatcher, tracker = build()
    a = store.create("station_3", "station_9")
    b = store.create("station_3", "station_9")

    step(dispatcher)
    assert permitted(store) == [a.job.job_id]

    step(tracker)                    # a leaves IDLE and spends its permit
    step(dispatcher)
    assert permitted(store) == [b.job.job_id]
    assert dispatcher.granted == 2


def test_an_empty_queue_grants_nothing():
    _, _, dispatcher, _ = build()
    for _ in range(3):
        step(dispatcher)
    assert dispatcher.granted == 0


# ------------------------------------------------------------------ ordering

def test_priority_wins():
    _, store, dispatcher, _ = build()
    store.create("station_3", "station_9", priority=0)
    urgent = store.create("station_3", "station_9", priority=5)
    store.create("station_3", "station_9", priority=1)

    step(dispatcher)

    assert permitted(store) == [urgent.job.job_id]


def test_age_breaks_a_priority_tie():
    """Otherwise a low-priority job could be starved indefinitely."""
    clock, store, dispatcher, _ = build()
    first = store.create("station_3", "station_9")
    clock.advance(5.0)
    store.create("station_3", "station_9")

    step(dispatcher)

    assert permitted(store) == [first.job.job_id]


def test_a_bounced_job_keeps_its_place_in_the_queue():
    """created_at, not state_since. A job refused by a busy fleet must not go
    to the back of the queue every time it is refused."""
    clock, store, dispatcher, tracker = build()

    class AlwaysBusy(AcsAdapter):
        def submit_job(self, job):
            return TransportResult.BUSY

        def get_job_result(self, job_id):
            return TransportResult.UNKNOWN

        def cancel_job(self, job_id):
            return True

    store.acs = AlwaysBusy()
    old = store.create("station_3", "station_9")
    clock.advance(1.0)
    store.create("station_3", "station_9")

    step(dispatcher)                        # old granted
    step(tracker)                           # -> ASSIGNED, told BUSY
    step(tracker)                           # t_busy -> back to IDLE
    assert old.fsm.current.name == "IDLE"

    clock.advance(old.ctx.retry_backoff_s + 0.1)
    step(dispatcher)
    assert permitted(store) == [old.job.job_id], \
        "the bounced job was sent to the back of the queue"


# ------------------------------------------------------- no wasted turns

def test_a_job_still_inside_its_backoff_is_not_granted():
    """With one permit outstanding at a time, a permit given to a job that
    cannot move stalls the whole queue until the next period."""
    clock, store, dispatcher, tracker = build()

    class AlwaysBusy(AcsAdapter):
        def submit_job(self, job):
            return TransportResult.BUSY

        def get_job_result(self, job_id):
            return TransportResult.UNKNOWN

        def cancel_job(self, job_id):
            return True

    store.acs = AlwaysBusy()
    only = store.create("station_3", "station_9")

    step(dispatcher); step(tracker); step(tracker)
    assert only.fsm.current.name == "IDLE"
    granted_so_far = dispatcher.granted

    step(dispatcher)                        # no time has passed
    assert dispatcher.granted == granted_so_far, "granted inside the backoff"

    clock.advance(only.ctx.retry_backoff_s + 0.1)
    step(dispatcher)
    assert dispatcher.granted == granted_so_far + 1


def test_the_dispatcher_agrees_with_t1_about_readiness():
    """Both must use ctx.backoff_elapsed(). If they disagree, permits are spent
    on jobs the guard then refuses to act on — quietly, with nothing logged."""
    _, store, dispatcher, tracker = build()
    record = store.create("station_3", "station_9")

    step(dispatcher)
    assert record.ctx.dispatch_permit is True

    step(tracker)
    assert record.fsm.current.name == "ASSIGNED", \
        "granted a permit the guard would not honour"


# ------------------------------------------------------------------- waking

def test_the_tracker_is_woken_after_a_grant():
    """So the job moves on the next tick rather than at its own leisure."""
    _, store, dispatcher, _ = build()
    spy = Spy()
    dispatcher.wakes.append(spy)
    store.create("station_3", "station_9")

    step(dispatcher)
    assert spy.woken == 1

    step(dispatcher)                        # permit still outstanding
    assert spy.woken == 1
