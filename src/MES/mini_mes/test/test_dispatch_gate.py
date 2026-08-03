"""Tests for the dispatch permit — t1's second condition.

The permit answers "is it this job's turn", which is a fleet-wide question. The
backoff answers "has this job waited long enough", which is a per-job question.
They are independent, and these tests keep them that way: a permit must not
bypass a backoff, and a backoff must not substitute for a permit.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from mini_mes.adapters.base import TransportResult                 # noqa: E402
from mini_mes.adapters.mock import ManualClock, MockAcs, MockEquipment  # noqa: E402
from mini_mes.runtime.job_store import JobStore                    # noqa: E402


def build(gated):
    clock = ManualClock()
    store = JobStore(MockEquipment(["station_3", "station_9"], clock),
                     MockAcs(clock, travel_seconds=5.0), clock,
                     logger=lambda m: None, dispatch_gated=gated)
    return clock, store


# -------------------------------------------------------------- gated behaviour

def test_a_gated_job_stays_idle_until_granted():
    _, store = build(gated=True)
    record = store.create("station_3", "station_9")

    for _ in range(10):
        store.step_all()
    assert record.fsm.current.name == "IDLE"
    assert record.ctx.submit_attempts == 0, "submitted without a permit"

    record.ctx.dispatch_permit = True
    store.step_all()
    assert record.fsm.current.name == "ASSIGNED"
    assert record.ctx.submit_attempts == 1


def test_a_permit_is_spent_on_leaving_idle():
    """One permit authorises one attempt, not a standing right to retry."""
    _, store = build(gated=True)
    record = store.create("station_3", "station_9")

    record.ctx.dispatch_permit = True
    store.step_all()                        # t1 -> ASSIGNED
    assert record.ctx.dispatch_permit is False


def test_a_bounced_job_waits_for_a_fresh_permit():
    """t_busy returns the job to IDLE. It must not re-submit on its own."""
    clock, store = build(gated=True)

    class AlwaysBusy:
        calls = 0

        def submit_job(self, job):
            type(self).calls += 1
            return TransportResult.BUSY

        def get_job_result(self, job_id):
            return TransportResult.UNKNOWN

        def cancel_job(self, job_id):
            return True

    store.acs = AlwaysBusy()
    record = store.create("station_3", "station_9")

    record.ctx.dispatch_permit = True
    store.step_all()                        # t1 -> ASSIGNED, told BUSY
    store.step_all()                        # t_busy -> IDLE
    assert record.fsm.current.name == "IDLE"
    assert AlwaysBusy.calls == 1

    clock.advance(60.0)                     # long past any backoff
    for _ in range(10):
        store.step_all()
    assert record.fsm.current.name == "IDLE"
    assert AlwaysBusy.calls == 1, "re-submitted without being granted again"

    record.ctx.dispatch_permit = True       # the Dispatcher's turn again
    store.step_all()
    assert AlwaysBusy.calls == 2


def test_a_permit_does_not_bypass_the_backoff():
    """The two conditions are independent. A permit is not a licence to ignore
    the job's own retry spacing."""
    clock, store = build(gated=True)

    class AlwaysBusy:
        calls = 0

        def submit_job(self, job):
            type(self).calls += 1
            return TransportResult.BUSY

        def get_job_result(self, job_id):
            return TransportResult.UNKNOWN

        def cancel_job(self, job_id):
            return True

    store.acs = AlwaysBusy()
    record = store.create("station_3", "station_9")

    record.ctx.dispatch_permit = True
    store.step_all(); store.step_all()      # one attempt, back to IDLE
    assert AlwaysBusy.calls == 1

    record.ctx.dispatch_permit = True       # granted again, but no time passed
    store.step_all()
    assert record.fsm.current.name == "IDLE", "backoff was bypassed by a permit"
    assert AlwaysBusy.calls == 1

    clock.advance(store.create("x", "y").ctx.retry_backoff_s + 0.1)
    store.step_all()
    assert AlwaysBusy.calls == 2


# ------------------------------------------------------------ ungated is intact

def test_an_ungated_job_never_consults_the_permit():
    """The sequential driver must behave exactly as it did before the gate."""
    _, store = build(gated=False)
    record = store.create("station_3", "station_9")

    record.ctx.dispatch_permit = False      # would block a gated job outright
    store.step_all()
    assert record.fsm.current.name == "ASSIGNED"


def test_an_ungated_bounced_job_still_retries_by_itself():
    """Idle.on_exit must not strand a job where nothing grants permits."""
    clock, store = build(gated=False)

    class BusyThenFree:
        calls = 0

        def submit_job(self, job):
            type(self).calls += 1
            return (TransportResult.BUSY if type(self).calls <= 1
                    else TransportResult.ACCEPTED)

        def get_job_result(self, job_id):
            return TransportResult.ARRIVED

        def cancel_job(self, job_id):
            return True

    store.acs = BusyThenFree()
    record = store.create("station_3", "station_9")

    store.step_all(); store.step_all()      # attempt 1 -> BUSY -> back to IDLE
    assert record.fsm.current.name == "IDLE"

    clock.advance(record.ctx.retry_backoff_s + 0.1)
    store.step_all()
    assert record.fsm.current.name == "ASSIGNED", "stranded — no permit exists here"
    assert BusyThenFree.calls == 2
