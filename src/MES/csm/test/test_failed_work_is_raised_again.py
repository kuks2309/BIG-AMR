"""A failed job used to lose the work silently.

The ACS order was cancelled, the job retired FAILED, and the machine's call had
already been acknowledged — so the equipment had stopped asking and nobody was
coming. Nothing reported it, because from each component's own point of view its
part had finished correctly.

THE WORK OUTLIVES THE JOB. A transport that failed does not mean the material
stopped needing to move.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters.base import StationStatus                        # noqa: E402
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment  # noqa: E402
from csm.job import Carried                                        # noqa: E402
from csm.runtime.job_store import MAX_ATTEMPTS, JobStore           # noqa: E402


def build(timeout=600.0):
    clock = ManualClock()
    equipment = MockEquipment(["station_3", "station_9"], clock)
    acs = MockAcs(clock, travel_seconds=8.0)
    store = JobStore(equipment, acs, clock, logger=lambda m: None,
                     job_timeout_s=timeout)
    return clock, equipment, acs, store


def failed_job(store, reason="ACS reported failure", retryable=True, **kw):
    """A job in the state `_raise_again` is handed one: retired, FAILED."""
    job = store.create("station_3", "station_9", **kw).job
    job.failure_reason = reason
    job.retryable = retryable
    return job


# ------------------------------------------------------------ the work returns

def test_failed_work_is_raised_again():
    _, _, _, store = build()
    again = store._raise_again(failed_job(store))

    assert again is not None
    assert again.job.from_station == "station_3"
    assert again.job.to_station == "station_9"


def test_the_replacement_carries_the_same_work():
    """Same material, same object, same caller — it IS the same work."""
    _, _, _, store = build()
    job = failed_job(store, carries=Carried.BOBBIN, priority=5)
    job.call_id = "call_0007"
    job.material_ref = "20260818120000000"

    again = store._raise_again(job).job
    assert again.carries is Carried.BOBBIN
    assert again.priority == 5
    assert again.call_id == "call_0007"
    assert again.material_ref == "20260818120000000"


def test_the_chain_of_attempts_is_followable():
    """Without `retry_of`, six job ids for one bobbin look like six bobbins."""
    _, _, _, store = build()
    first = failed_job(store)
    second = store._raise_again(first).job

    assert second.attempt == 2
    assert second.retry_of == first.job_id


def test_the_replacement_is_a_new_job_not_the_old_one_revived():
    _, _, _, store = build()
    first = failed_job(store)
    second = store._raise_again(first).job

    assert second.job_id != first.job_id
    assert first.state_name == "FAILED" or first.failure_reason


def test_the_retry_records_why():
    _, _, _, store = build()
    job = failed_job(store, reason="timeout after 600s in RUNNING")
    again = store._raise_again(job).job

    reasons = " ".join(d.reason for d in
                       store.records.decisions_for(again.job_id))
    assert "attempt 2" in reasons
    assert "timeout" in reasons


def test_retries_are_counted_apart_from_jobs_created():
    """A rising retry count is a line struggling, not a line busy."""
    _, _, _, store = build()
    assert store.retried == 0
    store._raise_again(failed_job(store))
    assert store.retried == 1


# --------------------------------------------------------------- but not for ever

def test_it_gives_up_at_the_ceiling():
    """Unbounded retry turns one broken station into a fleet doing nothing else."""
    _, _, _, store = build()
    assert store._raise_again(failed_job(store, attempt=MAX_ATTEMPTS)) is None


def test_giving_up_says_so_loudly():
    """This is where work is genuinely abandoned. Somebody has to know."""
    logged = []
    _, _, _, store = build()
    store.logger = logged.append
    store._raise_again(failed_job(store, attempt=MAX_ATTEMPTS))

    assert any("GIVING UP" in m for m in logged), logged


def test_the_ceiling_holds_across_a_real_chain():
    _, _, _, store = build()
    job = failed_job(store)

    for expected in range(2, MAX_ATTEMPTS + 1):
        record = store._raise_again(job)
        assert record is not None, f"attempt {expected} should still be tried"
        assert record.job.attempt == expected
        job = record.job
        job.failure_reason = "ACS reported failure"
        job.retryable = True

    assert store._raise_again(job) is None
    assert store.retried == MAX_ATTEMPTS - 1


# ------------------------------------------ some failures are answers, not accidents

def test_an_invalid_job_is_not_raised_again():
    """REJECTED means the job is wrong. Repeating it argues with the answer."""
    _, _, _, store = build()
    job = failed_job(store, reason="ACS rejected the job", retryable=False)
    assert store._raise_again(job) is None


def test_a_job_a_person_cancelled_is_not_raised_again():
    """Otherwise cancelling from the PDA does nothing and looks broken."""
    _, _, _, store = build()
    job = failed_job(store, reason="cancelled from the PDA", retryable=False)
    assert store._raise_again(job) is None


def test_not_retrying_is_explained_too():
    logged = []
    _, _, _, store = build()
    store.logger = logged.append
    store._raise_again(failed_job(store, retryable=False))

    assert any("not retried" in m for m in logged), logged


# ----------------------------------------------------- through the real lifecycle

def test_a_job_that_times_out_comes_back_by_itself():
    """Not by calling the helper — by letting a job genuinely fail."""
    clock, equipment, acs, store = build(timeout=10.0)
    equipment.force_status("station_3", StationStatus.FINISHED)
    record = store.create("station_3", "station_9")

    store.step_all()
    store.step_all()
    acs.never_arrives(record.job.job_id)
    clock.advance(11.0)
    store.step_all()

    assert record.job.state_name == "FAILED"
    assert len(store.active) == 1, "the work should have been raised again"
    assert store.active[0].job.retry_of == record.job.job_id
    assert store.active[0].job.attempt == 2


def test_the_replacement_is_not_wiped_by_the_retire_sweep():
    """`create` appends to `self.active`, which `step_all` then reassigns.

    Raising the work again from inside the retire loop would have the new job
    thrown away silently — the exact hole this whole file exists to close.
    """
    clock, equipment, acs, store = build(timeout=10.0)
    equipment.force_status("station_3", StationStatus.FINISHED)
    record = store.create("station_3", "station_9")

    store.step_all()
    store.step_all()
    acs.never_arrives(record.job.job_id)
    clock.advance(11.0)
    retired = store.step_all()

    assert [r.job for r in retired] == [record.job]
    assert store.active, "the replacement must survive the sweep"


def test_a_successful_job_is_not_raised_again():
    clock, equipment, acs, store = build()
    equipment.force_status("station_3", StationStatus.FINISHED)
    store.create("station_3", "station_9")

    for _ in range(12):
        clock.advance(5.0)
        store.step_all()

    assert store.finished and store.finished[0].state_name == "DONE"
    assert store.active == [], "a job that worked must not be repeated"
    assert store.retried == 0
