"""The records survive a restart.

`InMemoryRecords` is correct and loses everything when the process stops.
`SqliteRecords` is the same working set written through to a file, so the
interesting tests are not "does park() work" — the base class already proves
that — but "is what comes back the same as what went in".
"""

import inspect
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime                                      # noqa: E402

from csm.adapters.base import TaskType                             # noqa: E402
from csm.records import (CallStatus, Decision, InMemoryRecords,     # noqa: E402
                         Records)
from csm.records_sqlite import SqliteRecords                       # noqa: E402


RACKS = {"WIP_CTR": 3, "WIP_SLT": 2}


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "csm.db")


def reopen(path):
    """What a restart does."""
    return SqliteRecords(path, rack_sizes=RACKS)


def store(path):
    return SqliteRecords(path, rack_sizes=RACKS)


# ------------------------------------------------------- it is the same store

def test_it_is_a_records_implementation():
    assert issubclass(SqliteRecords, Records)


def test_an_in_memory_database_needs_no_file():
    """What most tests want: every SQL statement exercised, nothing left."""
    assert SqliteRecords(":memory:").locate("nothing") is None


# ------------------------------------------------------- surviving a restart

def test_a_call_survives(db):
    first = store(db)
    call = first.add_call("GRV1_LD", TaskType.LOAD, "machine", 12.0)
    first.acknowledge_call(call.call_id, at=13.0, job_id="job_0001")
    first.close()

    back = reopen(db).call(call.call_id)
    assert back.station == "GRV1_LD"
    assert back.acknowledged_at == 13.0
    assert back.job_id == "job_0001"
    assert back.status is CallStatus.ACKNOWLEDGED


def test_the_task_type_comes_back_as_the_enum_not_a_string(db):
    """Stored by NAME, so a renumbered enum cannot silently reinterpret old
    rows — but it must still come back as the same type it went in as."""
    first = store(db)
    call = first.add_call("GRV1_LD", TaskType.UNLOAD, "machine", 1.0)
    first.close()

    assert reopen(db).call(call.call_id).task_type is TaskType.UNLOAD


def test_a_cancelled_call_survives_as_cancelled(db):
    """C9's record. WITHDRAWN and CANCELLED mean opposite things about who
    failed, so the distinction has to outlive the process."""
    first = store(db)
    call = first.add_call("GRV1_LD", TaskType.LOAD, "machine", 1.0)
    first.acknowledge_call(call.call_id, at=2.0, job_id="job_0001")
    first.cancel_call(call.call_id, at=9.0)
    first.close()

    back = reopen(db).call(call.call_id)
    assert back.status is CallStatus.CANCELLED
    assert back.cancelled_at == 9.0


def test_decisions_survive_in_order(db):
    """The only record that exists purely to be read by a person — and the one
    that answers "why that machine" long after the logs have rotated."""
    first = store(db)
    for i in range(3):
        first.add_decision(Decision(job_id="job_0001", decided_at=float(i),
                                    reason=f"reason {i}"))
    first.close()

    reasons = [d.reason for d in reopen(db).decisions_for("job_0001")]
    assert reasons == ["reason 0", "reason 1", "reason 2"]


def test_a_parked_material_is_still_parked_after_a_restart(db):
    """The one that matters most on the floor. A rack slot the database
    forgot is a physical bobbin nobody can find."""
    first = store(db)
    material = first.register_material(kind="bobbin", at=1.0)
    first.park("WIP_CTR", material.material_ref, "job_0001", at=2.0)
    first.close()

    back = reopen(db)
    occupied = [s for s in back.slots("WIP_CTR") if s.occupied]
    assert len(occupied) == 1
    assert occupied[0].material_ref == material.material_ref
    assert occupied[0].parked_by_job == "job_0001"


def test_a_retrieved_slot_comes_back_free(db):
    first = store(db)
    material = first.register_material(at=1.0)
    first.park("WIP_CTR", material.material_ref, "job_0001", at=2.0)
    first.retrieve("WIP_CTR", at=3.0)
    first.close()

    assert reopen(db).free_slots("WIP_CTR") == reopen(db).slots("WIP_CTR")


def test_where_a_material_is_survives(db):
    first = store(db)
    material = first.register_material(at=1.0, location="ASRS")
    first.move_material(material.material_ref, "GRV1_LD", at=2.0,
                        job_id="job_0001")
    first.close()

    assert reopen(db).locate(material.material_ref) == "GRV1_LD"


def test_the_whole_history_of_a_material_survives(db):
    """Traceability is the point of keeping it. A history with a hole in it
    answers "where has this roll been" wrongly rather than incompletely."""
    first = store(db)
    material = first.register_material(at=1.0, location="ASRS")
    for i, place in enumerate(["GRV1_LD", "GRV1_ULD", "WIP_CTR"], start=2):
        first.move_material(material.material_ref, place, at=float(i))
    first.close()

    history = reopen(db).history_of(material.material_ref)
    assert [m.to_location for m in history] == \
        ["ASRS", "GRV1_LD", "GRV1_ULD", "WIP_CTR"]
    assert [m.seq for m in history] == [1, 2, 3, 4]


def test_the_station_map_survives(db):
    """Learned from the machines over OPC-UA, not configured. Losing it means
    relearning it, and until then our name and theirs are not connected."""
    first = store(db)
    first.map_station("GRV1_LD", "2A01")
    first.close()

    assert reopen(db).customer_id("GRV1_LD") == "2A01"


def test_resting_time_survives(db):
    first = store(db)
    material = first.register_material(at=1.0)
    first.set_ready_at(material.material_ref, when=500.0)
    first.close()

    back = reopen(db)
    assert not back.is_ready(material.material_ref, now=100.0)
    assert back.is_ready(material.material_ref, now=600.0)


# --------------------------------------------------------- identity is not reused

def test_call_ids_carry_on_where_they_stopped(db):
    """Restarting at call_0001 would overwrite a served call with a new one and
    lose both — and the two would be indistinguishable afterwards."""
    first = store(db)
    first.add_call("GRV1_LD", TaskType.LOAD, "machine", 1.0)
    first.add_call("GRV2_LD", TaskType.LOAD, "machine", 2.0)
    first.close()

    assert reopen(db).add_call("SLT_LD1", TaskType.LOAD, "machine",
                               3.0).call_id == "call_0003"


def test_lot_ids_issued_before_a_restart_are_not_handed_out_again(db):
    """A LOT id is how the customer's systems refer to the material. Two
    materials sharing one is worse than either being unnamed."""
    fixed = datetime(2026, 8, 19, 10, 0, 0, 500000)
    first = SqliteRecords(db, rack_sizes=RACKS, wall_clock=lambda: fixed)
    before = first.register_material(at=1.0).lot_id
    first.close()

    second = SqliteRecords(db, rack_sizes=RACKS, wall_clock=lambda: fixed)
    assert second.register_material(at=2.0).lot_id != before


# ------------------------------------------------- the trap this design sets

def _mutators(cls):
    """Public methods that CHANGE something, by the base class's own naming."""
    changing = ("add_", "set_", "map_", "register_", "move_", "park",
                "retrieve", "acknowledge_", "cancel_", "define_")
    return {name for name, fn in inspect.getmembers(cls, inspect.isfunction)
            if not name.startswith("_") and name.startswith(changing)}


def test_every_mutating_method_is_written_through():
    """THE TRAP. Subclassing means a new mutator on `InMemoryRecords` works
    perfectly and persists nothing — and the loss only appears after a restart,
    by which time the cause is hours away. A human reviewer will not catch it.
    This will.
    """
    missing = sorted(name for name in _mutators(InMemoryRecords)
                     if name not in vars(SqliteRecords))
    assert not missing, (
        f"{missing} change the records but are not overridden in "
        f"SqliteRecords, so their effect is lost on restart")


def test_the_check_above_can_actually_fail():
    """A guard that cannot fail is decoration. This proves it has teeth."""
    assert "park" in _mutators(InMemoryRecords)
    assert _mutators(InMemoryRecords), "the naming rule found nothing at all"


# ---------------------------------------------- and it behaves like the other one

def test_it_answers_the_same_as_the_in_memory_store():
    """Same operations, same answers. The port only means something if the two
    implementations are actually substitutable."""
    fixed = datetime(2026, 8, 19, 10, 0, 0, 0)
    pair = [InMemoryRecords(rack_sizes=RACKS, wall_clock=lambda: fixed),
            SqliteRecords(":memory:", rack_sizes=RACKS,
                          wall_clock=lambda: fixed)]
    answers = []
    for records in pair:
        call = records.add_call("GRV1_LD", TaskType.LOAD, "machine", 1.0)
        records.acknowledge_call(call.call_id, at=2.0, job_id="job_0001")
        material = records.register_material(at=1.0, location="ASRS")
        records.move_material(material.material_ref, "GRV1_LD", at=3.0)
        records.park("WIP_CTR", material.material_ref, "job_0001", at=4.0)
        records.map_station("GRV1_LD", "2A01")
        answers.append((
            call.call_id,
            records.call(call.call_id).status,
            material.lot_id,
            records.locate(material.material_ref),
            [m.to_location for m in records.history_of(material.material_ref)],
            [s.material_ref for s in records.slots("WIP_CTR")],
            records.customer_id("GRV1_LD"),
            records.is_full("WIP_SLT"),
        ))
    assert answers[0] == answers[1]
