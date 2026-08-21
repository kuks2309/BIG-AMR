"""Jobs, retained.

Until 2026-08-21 four tables carried a `job_id` and nothing could resolve one.
A call, a decision and a material movement all survived a restart while the job
that connected them did not.

The test that matters is `test_a_finished_job_survives_a_restart`. Everything
else here supports it.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.job import Carried, Job                                   # noqa: E402
from csm.records import InMemoryRecords                            # noqa: E402
from csm.records_sqlite import SqliteRecords                       # noqa: E402


def a_job(job_id="JB_CELL_LOWBIGA_ASRS_ASRS_GRVPRTLD_ROLL_0001", **kw):
    fields = dict(from_station="ASRS", to_station="GRV1_LD",
                  carries=Carried.ROLL, created_at=1.0)
    fields.update(kw)
    return Job(job_id=job_id, **fields)


def stores(tmp_path):
    """Both implementations, so neither can drift from the other."""
    return [InMemoryRecords(), SqliteRecords(str(tmp_path / "r.db"))]


# ------------------------------------------------------------ the basics


def test_a_saved_job_can_be_read_back(tmp_path):
    for records in stores(tmp_path):
        job = a_job()
        records.save_job(job, at=1.0)
        assert records.job(job.job_id).from_station == "ASRS"
        assert records.job(job.job_id).to_station == "GRV1_LD"


def test_saving_twice_updates_rather_than_duplicates(tmp_path):
    for records in stores(tmp_path):
        job = a_job()
        records.save_job(job, at=1.0)
        job.state_name = "RUNNING"
        records.save_job(job, at=2.0)
        assert len(records.jobs()) == 1
        assert records.job(job.job_id).state == "RUNNING"


def test_an_unfinished_job_has_no_finish_time(tmp_path):
    """How a job still in flight is told from one that ended."""
    for records in stores(tmp_path):
        records.save_job(a_job(), at=1.0)
        assert records.jobs()[0].finished_at is None


def test_finishing_stamps_the_time(tmp_path):
    for records in stores(tmp_path):
        job = a_job()
        records.save_job(job, at=1.0)
        job.state_name = "DONE"
        records.save_job(job, at=9.0, finished=True)
        assert records.job(job.job_id).finished_at == 9.0


def test_a_later_update_does_not_erase_the_finish_time(tmp_path):
    """A job that ended stays ended, whatever is written afterwards."""
    for records in stores(tmp_path):
        job = a_job()
        records.save_job(job, at=1.0)
        records.save_job(job, at=9.0, finished=True)
        records.save_job(job, at=11.0)          # some later, non-final write
        assert records.job(job.job_id).finished_at == 9.0


def test_jobs_come_back_newest_first(tmp_path):
    for records in stores(tmp_path):
        for n in (1, 2, 3):
            records.save_job(a_job(job_id=f"JB_X_{n:04d}"), at=float(n))
        assert [j.job_id for j in records.jobs()] == \
            ["JB_X_0003", "JB_X_0002", "JB_X_0001"]
        assert [j.job_id for j in records.jobs(limit=2)] == \
            ["JB_X_0003", "JB_X_0002"]


# ------------------------------------------------- what the id cannot say


def test_the_machine_number_is_kept_even_though_the_id_loses_it(tmp_path):
    """`GRV1_LD` and `GRV4_LD` both read `GRVPRTLD` in the id.

    The workshop deck's codes are per process, so the id cannot say which of
    the four gravures. These columns are where that is not lost.
    """
    for records in stores(tmp_path):
        job = a_job(to_station="GRV4_LD")
        job.to_instance = 4
        records.save_job(job, at=1.0)
        assert records.job(job.job_id).to_instance == 4


# ------------------------------------------------------- the retry chain


def test_the_retry_chain_is_answerable(tmp_path):
    """"Was this the third attempt?" — unanswerable before this table."""
    for records in stores(tmp_path):
        first = a_job(job_id="JB_X_0001")
        records.save_job(first, at=1.0)

        second = a_job(job_id="JB_X_0002")
        second.attempt, second.retry_of = 2, "JB_X_0001"
        records.save_job(second, at=2.0)

        assert records.job("JB_X_0002").attempt == 2
        assert records.job("JB_X_0002").retry_of == "JB_X_0001"
        assert records.job(records.job("JB_X_0002").retry_of) is not None


def test_a_failure_reason_is_kept(tmp_path):
    for records in stores(tmp_path):
        job = a_job()
        job.state_name, job.failure_reason = "FAILED", "ACS rejected the job"
        records.save_job(job, at=5.0, finished=True)
        assert records.job(job.job_id).failure_reason == "ACS rejected the job"


# ------------------------------------------------------- THE ACTUAL POINT


def test_a_finished_job_survives_a_restart(tmp_path):
    """Close the database, open it again, and the job is still there.

    This is the whole reason the table exists. Before it, a call could say it
    was answered by `job_0021` and nothing in the database could say what
    `job_0021` was.
    """
    path = str(tmp_path / "restart.db")

    first = SqliteRecords(path)
    job = a_job(material_ref="20260821120749985", call_id="call_0007")
    first.save_job(job, at=1.0)
    job.state_name = "DONE"
    first.save_job(job, at=42.0, finished=True)
    first.close()

    reopened = SqliteRecords(path)
    back = reopened.job(job.job_id)
    assert back is not None, "the job did not survive"
    assert back.state == "DONE"
    assert back.finished_at == 42.0
    assert back.material_ref == "20260821120749985"
    assert back.call_id == "call_0007"


def test_a_call_can_now_resolve_the_job_it_names(tmp_path):
    """The dangling reference from the database review, closed.

    A call records the job raised to serve it. Before this table that id
    pointed at nothing after a restart.
    """
    path = str(tmp_path / "resolve.db")

    first = SqliteRecords(path)
    call = first.add_call("GRV1_LD", None, "machine", raised_at=1.0)
    job = a_job(call_id=call.call_id)
    first.acknowledge_call(call.call_id, at=2.0, job_id=job.job_id)
    first.save_job(job, at=2.0)
    first.close()

    reopened = SqliteRecords(path)
    stored = [c for c in reopened._calls.values() if c.call_id == call.call_id][0]
    assert reopened.job(stored.job_id) is not None, \
        "a call still names a job the database cannot explain"
    assert reopened.job(stored.job_id).from_station == "ASRS"
