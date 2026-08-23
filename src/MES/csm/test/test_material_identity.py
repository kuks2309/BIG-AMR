"""Material gets an identity when a job collects it.

Measured on a running fleet, 2026-08-20: 19 jobs created, 11 bobbin returns,
and **0 jobs carrying a material_ref**. `register_material` was reachable only
from the divert path, and divert never fired — so B1 to B4 answered nothing.

See `docs/adr/2026-08-20-material-identity-at-collection.md`.
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters.base import StationStatus, TaskType               # noqa: E402
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment    # noqa: E402
from csm.job import Carried                                          # noqa: E402
from csm.records import InMemoryRecords                              # noqa: E402
from csm.runtime.job_store import JobStore                           # noqa: E402
from csm.runtime.tasks import (DispatcherTask,                       # noqa: E402
                               EquipmentMonitorTask)

FEEDS = {"1A01": "ASRS", "1T01": "1A01", "1L01": "1T01"}
RETURNS = {"1A01": "ASRS", "1T01": "1A01"}
STATIONS = ["ASRS", "1A01", "1T01", "1L01"]


def build(with_returns=False):
    clock = ManualClock()
    equipment = MockEquipment(STATIONS, clock)
    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True, records=InMemoryRecords())
    monitor = EquipmentMonitorTask(
        store, source_for=lambda s: FEEDS.get(s, "ASRS"))
    if with_returns:
        monitor.return_for = lambda s: RETURNS.get(s)
    return clock, equipment, store, monitor


def step(task):
    asyncio.run(task.step())


def supply(equipment, *station_ids):
    for sid in station_ids:
        equipment.force_status(sid, StationStatus.FINISHED)


def jobs_of(store):
    return [r.job for r in store.active] + list(store.finished)


# -- the gap this closes ----------------------------------------------------

def test_a_job_names_what_it_is_carrying():
    _, equipment, store, monitor = build()
    supply(equipment, "ASRS")
    equipment.raise_call("1A01", TaskType.LOAD)
    step(monitor)

    (job,) = jobs_of(store)
    assert job.material_ref is not None, "the job must name what it carries"
    material = store.records.material(job.material_ref)
    assert material is not None
    assert material.kind == "roll"
    assert material.location == "ASRS", "it is still where it was collected"


def test_the_lot_id_is_the_customers_format():
    """`yyyymmddhhmmssfff` — B3, and their format exactly."""
    _, equipment, store, monitor = build()
    supply(equipment, "ASRS")
    equipment.raise_call("1A01", TaskType.LOAD)
    step(monitor)

    (job,) = jobs_of(store)
    lot = store.records.material(job.material_ref).lot_id
    assert len(lot) == 17 and lot.isdigit(), lot


# -- the reuse rule, which is the whole design ------------------------------

def test_a_second_job_from_the_same_place_reuses_the_same_material():
    """MINTING PER JOB WOULD DESTROY TRACEABILITY.

    A roll making three hops would become three unrelated records, and "where
    has this roll been" could not be answered at all.
    """
    _, equipment, store, monitor = build()
    supply(equipment, "ASRS")

    equipment.raise_call("1A01", TaskType.LOAD)
    step(monitor)
    first = jobs_of(store)[0].material_ref

    # Same source, a different destination, a fresh call.
    supply(equipment, "ASRS")
    equipment.raise_call("1T01", TaskType.LOAD)
    step(monitor)

    refs = {j.material_ref for j in jobs_of(store)}
    assert refs == {first}, "one roll at one place is one material"
    assert len(store.records.materials()) == 1


def test_material_at_a_different_place_is_a_different_material():
    _, equipment, store, monitor = build()
    supply(equipment, "ASRS", "1A01")

    equipment.raise_call("1A01", TaskType.LOAD)     # from ASRS
    step(monitor)
    equipment.raise_call("1T01", TaskType.LOAD)     # from 1A01
    step(monitor)

    refs = {j.material_ref for j in jobs_of(store)}
    assert len(refs) == 2, "two sources holding material are two materials"


def test_one_roll_across_two_hops_is_one_history():
    """B2 and B4 — the question that reuse exists to keep answerable."""
    clock, equipment, store, monitor = build()
    supply(equipment, "ASRS")
    equipment.raise_call("1A01", TaskType.LOAD)
    step(monitor)

    (record,) = store.active
    ref = record.job.material_ref

    # The store is dispatch-gated, so a job waits for its turn. Run the real
    # dispatcher rather than granting the permit by hand — the point is the
    # material's history through the ACTUAL path, not a shortcut to DONE.
    dispatcher = DispatcherTask(store)
    for _ in range(60):
        if record.fsm.current.name in ("DONE", "FAILED"):
            break
        step(dispatcher)
        clock.advance(1)
        store.step_all()

    assert record.fsm.current.name == "DONE", record.fsm.current.name
    assert store.records.locate(ref) == "1A01", "it arrived where it was sent"
    history = store.records.history_of(ref)
    assert history, "a delivered material must have a movement recorded"
    assert history[-1].to_location == "1A01"


# -- bobbins ----------------------------------------------------------------

def test_a_bobbin_return_registers_a_bobbin_not_a_roll():
    _, equipment, store, monitor = build(with_returns=True)
    equipment.raise_call("1A01", TaskType.UNLOAD)
    step(monitor)

    (job,) = jobs_of(store)
    assert job.carries is Carried.BOBBIN
    assert store.records.material(job.material_ref).kind == "bobbin"


# -- the thing that must not become a new failure mode ----------------------

def test_records_never_stop_a_job_being_created():
    """D5. The monitor already decides whether a source can supply.

    A second, quieter gate here would be a way to lose work for a bookkeeping
    reason, which is precisely the failure this layer exists to avoid.
    """
    _, equipment, store, monitor = build()
    supply(equipment, "ASRS")
    equipment.raise_call("1A01", TaskType.LOAD)
    step(monitor)

    assert monitor.created == 1
    assert len(jobs_of(store)) == 1


def test_claiming_counts_a_blind_resting_decision():
    """`unrested_decisions` read 0 because we never chose, not because we knew.

    Customer open decision #6 is how big this is, and it only becomes visible
    once something actually claims material.
    """
    _, equipment, store, monitor = build()
    # Both destinations fed from the store, so both claims hit the SAME place.
    monitor.source_for = lambda s: "ASRS"
    monitor.sources_for = lambda s: ["ASRS"]
    supply(equipment, "ASRS")

    # The FIRST claim mints, so nothing is examined and nothing is decided.
    equipment.raise_call("1A01", TaskType.LOAD)
    step(monitor)
    assert store.records.unrested_decisions == 0, "minting decides nothing"

    # The SECOND finds that material and has to judge whether it may be used.
    supply(equipment, "ASRS")
    equipment.raise_call("1T01", TaskType.LOAD)
    step(monitor)

    assert store.records.unrested_decisions > 0, (
        "claiming material with no known resting time is a blind decision "
        "and must be counted as one")


# -- what a live run found that these tests had not ------------------------
#
# Both of these passed the unit tests above and failed on a running fleet,
# where one LOT id ended up on three jobs at once. `ready_materials` answers
# "what is here", which is not the same question as "what is here that I can
# carry".

def test_a_bobbin_job_does_not_claim_a_roll():
    """An empty core must not travel upstream wearing a roll's identity.

    Observed live: a roll was delivered to GRV1_LD, and the bobbin-return job
    raised at GRV1_LD immediately claimed it.
    """
    _, equipment, store, monitor = build(with_returns=True)
    supply(equipment, "ASRS")

    equipment.raise_call("1A01", TaskType.LOAD)      # a roll, ASRS -> 1A01
    step(monitor)
    roll_ref = jobs_of(store)[0].material_ref
    # Put the roll where the bobbin call will be raised.
    store.records.move_material(roll_ref, "1T01", at=1.0)

    equipment.raise_call("1T01", TaskType.UNLOAD)    # a bobbin leaving 1T01
    step(monitor)

    bobbin_job = [j for j in jobs_of(store) if j.carries is Carried.BOBBIN][0]
    assert bobbin_job.material_ref != roll_ref, "a bobbin job took the roll"
    assert store.records.material(bobbin_job.material_ref).kind == "bobbin"


def test_two_jobs_from_one_place_do_not_carry_the_same_material():
    """Only one robot can pick a thing up.

    Observed live: job_0001 and job_0002 both collected from ASRS and both
    named the same LOT id.
    """
    _, equipment, store, monitor = build()
    monitor.source_for = lambda s: "ASRS"
    monitor.sources_for = lambda s: ["ASRS"]
    supply(equipment, "ASRS")

    equipment.raise_call("1A01", TaskType.LOAD)
    step(monitor)
    supply(equipment, "ASRS")
    equipment.raise_call("1T01", TaskType.LOAD)
    step(monitor)

    refs = [j.material_ref for j in jobs_of(store)]
    assert len(refs) == 2
    assert refs[0] != refs[1], "two jobs claimed the same material"


def test_a_material_freed_by_a_finished_job_can_be_claimed_again():
    """Exclusion is 'in flight', not 'forever'.

    A material whose job has retired is available again — otherwise every hop
    would mint a new identity and traceability would break the other way.
    """
    _, equipment, store, monitor = build()
    monitor.source_for = lambda s: "ASRS"
    monitor.sources_for = lambda s: ["ASRS"]
    supply(equipment, "ASRS")

    equipment.raise_call("1A01", TaskType.LOAD)
    step(monitor)
    first = jobs_of(store)[0].material_ref

    # Retire the job without moving the material — it is still at ASRS.
    store.active.clear()

    supply(equipment, "ASRS")
    equipment.raise_call("1T01", TaskType.LOAD)
    step(monitor)

    latest = [r.job for r in store.active][0]
    assert latest.material_ref == first, (
        "nothing is carrying it any more, so it is claimable again")
