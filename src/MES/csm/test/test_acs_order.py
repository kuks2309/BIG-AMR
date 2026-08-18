"""The ACS order model — ADR 2026-08-18-acs-order-task-interface.

These tests pin the shape of what we send the real ACS. They are deliberately
written against the VENDOR'S spelling: if someone renames a field to our taste,
these fail, because a renamed field cannot be checked against the live server.
"""

from csm.adapters.base import (AcsOrder, AcsTask, SimpleResponse, TaskKind,
                               TransportResult, build_order,
                               classify_error_code)
from csm.job import Carried, Job


def _job(job_id="job_0001", frm="ASRS", to="GRV1_LD", carries=Carried.ROLL,
         priority=0):
    return Job(job_id=job_id, from_station=frm, to_station=to,
               carries=carries, priority=priority)


# -- the task sequences the specification names, rev01 section 5 -------------

def test_roll_delivery_is_move_load_move_unload():
    order = build_order(_job())
    assert [t.kind for t in order.tasks] == [
        TaskKind.MOVE, TaskKind.LOAD, TaskKind.MOVE, TaskKind.UNLOAD]
    # Targets alternate source, source, destination, destination.
    assert [t.target for t in order.tasks] == [
        "ASRS", "ASRS", "GRV1_LD", "GRV1_LD"]


def test_deliver_and_collect_at_one_port_is_a_single_visit():
    """MOVE -> UNLOAD -> WAIT -> LOAD, and WAIT is STAGE.

    This is the case that justifies an order being a list. Two trips to the
    same port would be two orders; the machine's handshake expects one visit.
    """
    order = build_order(_job(frm="GRV1_LD", to="GRV1_LD"))
    assert [t.kind for t in order.tasks] == [
        TaskKind.MOVE, TaskKind.UNLOAD, TaskKind.STAGE, TaskKind.LOAD]
    assert {t.target for t in order.tasks} == {"GRV1_LD"}


def test_wait_is_stage_not_a_kind_of_its_own():
    """The specification says WAIT; the schema enum has no WAIT member."""
    assert not hasattr(TaskKind, "WAIT")
    assert TaskKind.STAGE.value == "STAGE"


# -- order identity and carried fields ---------------------------------------

def test_order_id_is_the_job_id_so_the_two_are_traceable():
    order = build_order(_job(job_id="job_0042"))
    assert order.id == "job_0042"


def test_priority_is_carried_through():
    assert build_order(_job(priority=7)).priority == 7


def test_bobbin_jobs_are_distinguishable_from_roll_jobs():
    """The six bobbin returns must not look like roll jobs to the ACS."""
    assert build_order(_job(carries=Carried.BOBBIN)).comment == "bobbin"
    assert build_order(_job(carries=Carried.ROLL)).comment == "roll"


# -- the vendor's spelling ----------------------------------------------------

def test_task_kind_matches_the_schema_enum_exactly():
    """schema.graphql L1081. Do not add, remove or rename members."""
    assert {k.name for k in TaskKind} == {
        "NONE", "LOAD", "UNLOAD", "STAGE", "SCAN", "TURN", "PORT_CUSTOM",
        "CHARGE", "MAINT", "MOVE", "NODE_CUSTOM"}


def test_order_carries_the_create_order_input_fields():
    """schema.graphql L2174 — id, tasks and the seven optional fields."""
    order = AcsOrder(id="x")
    for f in ("id", "tasks", "vehicleId", "priority", "hotLot", "custom",
              "requester", "requesterDetail", "comment"):
        assert hasattr(order, f), f


def test_task_carries_the_task_input_fields():
    """schema.graphql `input TaskInput`, including carrierCustom.

    carrierCustom is the field our own schema-analysis.md omits; coding from
    that summary rather than the schema would have dropped it.
    """
    task = AcsTask(kind=TaskKind.MOVE)
    for f in ("kind", "target", "vehicleSlot", "amount", "carrierId",
              "carrierModel", "carrierCustom", "independent", "enterReverse",
              "chargeTo", "expectedDuration", "noBlockingTime", "waitTimeout",
              "turnAngle", "custom"):
        assert hasattr(task, f), f


# -- the one thing the vendor still owes us ----------------------------------

def test_zero_is_the_only_code_we_claim_to_know():
    assert classify_error_code(0) is TransportResult.ACCEPTED
    assert SimpleResponse(0).ok


def test_unknown_codes_are_retryable_not_fatal():
    """Conservative direction, and the reason is in classify_error_code.

    Retrying a job that should have been rejected wastes robot time and shows
    up in the logs. Failing a job that would have run loses a material movement
    silently. Until the vendor supplies the table we take the loud failure.
    """
    for code in (1, 2, 42, 9999):
        assert classify_error_code(code) is TransportResult.BUSY
    assert not SimpleResponse(1).ok


def test_no_one_else_interprets_error_codes():
    """The guess must stay in one function so the real table is a one-line fix.

    If this fails someone has started reading errorCode elsewhere; point them
    at classify_error_code instead.
    """
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent / "csm"
    offenders = []
    for path in root.rglob("*.py"):
        if path.name == "base.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "errorCode" in text and "classify_error_code" not in text:
            offenders.append(path.name)
    assert not offenders, f"errorCode read outside base.py: {offenders}"
