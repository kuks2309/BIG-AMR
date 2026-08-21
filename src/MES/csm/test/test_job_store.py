"""Tests for JobStore — the bookkeeping both drivers share.

These exist separately from test_job_lifecycle.py because that file tests the
job FSM *through* MainCycle. Once two drivers exist, the rules below have to
hold no matter which one is on top, so they are pinned here directly against the
store.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters.base import StationStatus                  # noqa: E402
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment  # noqa: E402
from csm.runtime.job_store import JobStore                   # noqa: E402


def build(gated=False, timeout=600.0, travel=8.0):
    clock = ManualClock()
    equipment = MockEquipment(["station_3", "station_9"], clock)
    acs = MockAcs(clock, travel_seconds=travel)
    store = JobStore(equipment, acs, clock, logger=lambda m: None,
                     job_timeout_s=timeout, dispatch_gated=gated)
    return clock, equipment, acs, store


# ------------------------------------------------------------ the record shape

def test_job_record_unpacks_positionally_and_by_name():
    """Existing code unpacks `job, ctx, fsm = record`. That must keep working."""
    _, _, _, store = build()
    record = store.create("station_3", "station_9")

    job, ctx, fsm = record
    assert record.job is job
    assert record.ctx is ctx
    assert record.fsm is fsm
    assert record[0] is job


def test_job_ids_are_sequential_and_unique():
    _, _, _, store = build()
    ids = [store.create("station_3", "station_9").job.job_id for _ in range(3)]
    # THE ID IS THE DECK'S NAME PLUS A COUNTER (2026-08-21), not a bare
    # sequence. What this test cares about is that ids are unique and that the
    # counter advances, not the prefix — so it asserts the shape, not a literal.
    assert len(set(ids)) == 3, ids
    assert [i.rsplit("_", 1)[1] for i in ids] == ["0001", "0002", "0003"]
    assert all(i.startswith("JB_CELL_") for i in ids), ids


# ------------------------------------------------------------ the station latch

def test_a_finished_station_is_reported_once_then_suppressed():
    _, equipment, _, store = build()
    equipment.force_status("station_3", StationStatus.FINISHED)

    assert store.find_finished_stations() == ["station_3"]
    assert store.claim_station("station_3") is True
    assert store.find_finished_stations() == []


def test_claiming_a_station_twice_is_refused():
    _, _, _, store = build()
    assert store.claim_station("station_3") is True
    assert store.claim_station("station_3") is False


def test_a_station_is_freed_when_its_job_retires_successfully():
    clock, equipment, _, store = build(travel=1.0)
    equipment.force_status("station_3", StationStatus.FINISHED)
    store.claim_station("station_3")
    record = store.create("station_3", "station_9")

    store.step_all()            # t1 -> ASSIGNED (submits)
    store.step_all()            # t2 -> RUNNING
    clock.advance(2.0)
    retired = store.step_all()  # t3 -> DONE

    assert retired and retired[0].job is record.job
    assert record.job.state_name == "DONE"
    assert "station_3" not in store.station_busy
    assert store.active == []


def test_a_station_is_freed_even_when_its_job_fails():
    """A failed job must not block its source station for ever."""
    clock, equipment, acs, store = build(timeout=10.0)
    equipment.force_status("station_3", StationStatus.FINISHED)
    store.claim_station("station_3")
    record = store.create("station_3", "station_9")

    store.step_all()
    store.step_all()
    acs.never_arrives(record.job.job_id)
    clock.advance(11.0)
    store.step_all()            # t5 timeout -> FAILED

    assert record.job.state_name == "FAILED"
    assert "station_3" not in store.station_busy


def test_the_latch_survives_a_station_that_reproduces_immediately():
    """The regression that stalled the line.

    An observation-based latch clears only on a poll that catches the station
    non-finished. Here the station is FINISHED again before the next poll, so
    such a latch would stay stuck and never produce a second job.
    """
    clock, equipment, _, store = build(travel=1.0)

    equipment.force_status("station_3", StationStatus.FINISHED)
    for sid in store.find_finished_stations():
        store.claim_station(sid)
        store.create(sid, "station_9")

    store.step_all(); store.step_all()
    clock.advance(2.0)
    store.step_all()                       # DONE, station freed

    # The station finishes another batch straight away — no intervening poll
    # ever sees it idle.
    equipment.force_status("station_3", StationStatus.FINISHED)
    assert store.find_finished_stations() == ["station_3"], \
        "the station was latched out and would never produce again"


# ------------------------------------------------------------------- gating

def test_an_ungated_store_lets_a_job_dispatch_itself():
    _, _, _, store = build(gated=False)
    assert store.create("station_3", "station_9").ctx.dispatch_permit is True


def test_a_gated_store_withholds_permission():
    _, _, _, store = build(gated=True)
    assert store.create("station_3", "station_9").ctx.dispatch_permit is False


# ------------------------------------------------------------------ queries

def test_jobs_in_filters_by_state():
    _, _, _, store = build()
    a = store.create("station_3", "station_9")
    store.create("station_3", "station_9")

    assert len(store.jobs_in("IDLE")) == 2
    a.fsm.step(a.ctx)                       # a moves to ASSIGNED
    assert [r.job for r in store.jobs_in("ASSIGNED")] == [a.job]
    assert len(store.jobs_in("IDLE")) == 1
    assert len(store.jobs_in("IDLE", "ASSIGNED")) == 2
