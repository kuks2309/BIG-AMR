"""Tests for JobTrackerTask — the lifecycle owner."""

import asyncio
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters.mock import ManualClock, MockAcs, MockEquipment  # noqa: E402
from csm.runtime.job_store import JobStore                   # noqa: E402
from csm.runtime.tasks import JobTrackerTask                 # noqa: E402


def build(travel=2.0, timeout=600.0):
    clock = ManualClock()
    equipment = MockEquipment(["station_3", "station_9"], clock)
    acs = MockAcs(clock, travel_seconds=travel)
    store = JobStore(equipment, acs, clock, logger=lambda m: None,
                     job_timeout_s=timeout)
    return clock, equipment, acs, store, JobTrackerTask(store)


def step(task):
    asyncio.run(task.step())


class Spy:
    def __init__(self):
        self.woken = 0

    def notify(self):
        self.woken += 1


# ------------------------------------------------------------- the lifecycle

def test_a_job_is_carried_to_done():
    clock, _, _, store, tracker = build(travel=2.0)
    record = store.create("station_3", "station_9")

    step(tracker)
    assert record.job.state_name == "ASSIGNED"
    step(tracker)
    assert record.job.state_name == "RUNNING"

    clock.advance(3.0)
    step(tracker)

    assert record.job.state_name == "DONE"
    assert tracker.completed == 1
    assert tracker.failed == 0
    assert store.active == []


def test_one_transition_per_tick():
    """The tracker supplies the tick; the machine still moves one step."""
    _, _, _, store, tracker = build()
    record = store.create("station_3", "station_9")

    step(tracker)
    assert record.fsm.current.name == "ASSIGNED"     # not RUNNING


def test_completed_and_failed_are_counted_apart():
    """A system completing jobs and one failing them both look busy.

    The two jobs are run one after the other rather than together. They share
    one timeout, and t5 is checked before t3 — so advancing the clock far enough
    to time the second one out would also time out the first, however healthy
    it was. That ordering is deliberate (job_fsm.py: a job that both completed
    and timed out is recorded as the failure it was); it just means this test
    cannot overlap them.
    """
    clock, _, acs, store, tracker = build(travel=1.0, timeout=10.0)

    good = store.create("station_3", "station_9")
    step(tracker); step(tracker)          # -> RUNNING
    clock.advance(2.0)
    step(tracker)                         # arrives well inside the timeout
    assert good.job.state_name == "DONE"

    bad = store.create("station_3", "station_9")
    step(tracker); step(tracker)          # -> RUNNING
    acs.never_arrives(bad.job.job_id)
    clock.advance(11.0)
    step(tracker)                         # t5

    assert bad.job.state_name == "FAILED"
    assert "timeout" in bad.job.failure_reason
    assert (tracker.completed, tracker.failed) == (1, 1)


def test_many_jobs_advance_on_the_same_tick():
    clock, _, _, store, tracker = build(travel=1.0)
    records = [store.create("station_3", "station_9") for _ in range(4)]

    step(tracker)
    assert all(r.job.state_name == "ASSIGNED" for r in records)
    step(tracker)
    clock.advance(2.0)
    step(tracker)

    assert tracker.completed == 4


# ------------------------------------------------------------------- waking

def test_listeners_are_woken_on_retirement():
    """A retirement means capacity came back — the one event a dispatcher
    most wants to hear about."""
    clock, _, _, store, tracker = build(travel=1.0)
    spy = Spy()
    tracker.wakes.append(spy)
    store.create("station_3", "station_9")

    step(tracker); step(tracker)
    assert spy.woken == 0, "woken before anything retired"

    clock.advance(2.0)
    step(tracker)
    assert spy.woken == 1


def test_listeners_are_not_woken_every_tick():
    """Waking the dispatcher 4 Hz to re-read an untouched queue would make its
    own period meaningless."""
    _, _, _, store, tracker = build(travel=1000.0)
    spy = Spy()
    tracker.wakes.append(spy)
    store.create("station_3", "station_9")

    for _ in range(10):
        step(tracker)

    assert spy.woken == 0


def test_an_empty_store_ticks_harmlessly():
    _, _, _, _, tracker = build()
    for _ in range(3):
        step(tracker)
    assert (tracker.completed, tracker.failed) == (0, 0)


# --------------------------------------------------------------- testability

def test_step_needs_no_supervisor():
    """The rule from fsm_task.py: production drives step() from the run loop,
    tests drive it by hand. Nothing above may be required."""
    _, _, _, store, tracker = build()
    store.create("station_3", "station_9")

    asyncio.run(tracker.step())

    assert tracker.ticks == 0        # ticks belong to the run loop, not step
