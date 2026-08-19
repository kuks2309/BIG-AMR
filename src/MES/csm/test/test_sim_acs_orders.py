"""SimAcs speaks the ACS contract: orders carrying task lists.

ADR 2026-08-18-acs-order-task-interface. The point is that what the simulator
verifies has the SAME SHAPE as what runs at deployment — specification section
9 — so `submit_job` now goes through `create_order` rather than beside it.
"""

import pytest

from csm.adapters.base import (AcsOrder, AcsTask, TaskKind, TransportResult,
                               build_order, classify_error_code)
from csm.adapters.sim_acs import (ERR_BUSY, ERR_NO_TASKS,
                                  ERR_UNKNOWN_STATION, SIM_ERROR_CODES,
                                  SimAcs)
from csm.job import Carried, Job


class FakeLogger:
    def __init__(self):
        self.lines = []

    def info(self, m):
        self.lines.append(m)

    def warn(self, m):
        self.lines.append(m)


class FakeNode:
    def __init__(self):
        self._logger = FakeLogger()

    def get_logger(self):
        return self._logger


def acs(stations=("ASRS", "GRV1_LD")):
    """A SimAcs with no robots — enough to test the order surface.

    Built without __init__ for the reason test_traffic.py gives: the real one
    spawns SimRobots needing a live ROS node, and none of that takes part in
    reading a task list.
    """
    a = object.__new__(SimAcs)
    a.node = FakeNode()
    a.robots = []
    a._results = {}
    a._occupied = {}
    a.stations = {s: (0.0, 0.0) for s in stations}
    return a


def order(tasks, id="job_0001", priority=0):
    return AcsOrder(id=id, tasks=tasks, priority=priority)


# -- the task list is what says where to go ----------------------------------

def test_a_delivery_reads_its_two_ends_from_the_task_list():
    """LOAD target is the source, UNLOAD target is the destination."""
    a = acs()
    a.create_order(order([
        AcsTask(kind=TaskKind.MOVE, target="ASRS"),
        AcsTask(kind=TaskKind.LOAD, target="ASRS"),
        AcsTask(kind=TaskKind.MOVE, target="GRV1_LD"),
        AcsTask(kind=TaskKind.UNLOAD, target="GRV1_LD"),
    ]))
    # No robots, so it can only be BUSY — but it got far enough to accept the
    # stations, which is what proves the task list was read.
    assert a._results.get("job_0001") is None
    assert not any("unknown" in line for line in a.node._logger.lines)


def test_a_deliver_and_collect_visit_resolves_to_one_station_twice():
    """MOVE, UNLOAD, STAGE, LOAD — the case that makes an order a list.

    Both ends resolve to the same station, which is the point. Dispatch then
    refuses it for a DIFFERENT reason: a visit that starts and ends at one port
    is not a leg of the documented material flow, and the fleet is segmented by
    leg. That refusal is correct — the CSM raises no such job today — and the
    test asserts the reason, because "rejected" alone would also be what an
    unresolved task list produced.
    """
    a = acs(("GRV1_LD",))
    a.create_order(order([
        AcsTask(kind=TaskKind.MOVE, target="GRV1_LD"),
        AcsTask(kind=TaskKind.UNLOAD, target="GRV1_LD"),
        AcsTask(kind=TaskKind.STAGE, target="GRV1_LD"),
        AcsTask(kind=TaskKind.LOAD, target="GRV1_LD"),
    ]))
    said = " ".join(a.node._logger.lines)
    assert "not a leg" in said, said
    assert "unknown" not in said, "both ends DID resolve from the task list"


def test_an_unknown_station_is_rejected_not_retried():
    """The distinction that decides retry-for-ever versus fail."""
    a = acs()
    r = a.create_order(order([
        AcsTask(kind=TaskKind.LOAD, target="NOWHERE"),
        AcsTask(kind=TaskKind.UNLOAD, target="GRV1_LD"),
    ]))
    assert r.errorCode == ERR_UNKNOWN_STATION
    assert classify_error_code(r.errorCode, SIM_ERROR_CODES) \
        is TransportResult.REJECTED


# -- malformed orders are refused, not guessed at ----------------------------

def test_an_order_with_no_tasks_is_refused():
    assert acs().create_order(order([])).errorCode == ERR_NO_TASKS


def test_an_order_that_never_loads_or_unloads_is_refused():
    """A list of MOVEs says where to drive but not what the job IS."""
    r = acs().create_order(order([
        AcsTask(kind=TaskKind.MOVE, target="ASRS"),
        AcsTask(kind=TaskKind.MOVE, target="GRV1_LD"),
    ]))
    assert r.errorCode == ERR_NO_TASKS


# -- the old entry point now runs through the new one ------------------------

def test_submit_job_goes_through_the_order_path():
    """The four existing call sites exercise orders without being touched."""
    a = acs()
    seen = []
    a.create_order = lambda o: seen.append(o) or __import__(
        "csm.adapters.base", fromlist=["SimpleResponse"]).SimpleResponse(0)
    a.submit_job(Job(job_id="job_0007", from_station="ASRS",
                     to_station="GRV1_LD"))
    assert len(seen) == 1
    assert seen[0].id == "job_0007"
    assert [t.kind for t in seen[0].tasks] == [
        TaskKind.MOVE, TaskKind.LOAD, TaskKind.MOVE, TaskKind.UNLOAD]


def test_submit_job_still_reports_a_transport_result():
    """Its callers have not changed, so its return type must not either."""
    a = acs()
    out = a.submit_job(Job(job_id="job_0001", from_station="ASRS",
                           to_station="GRV1_LD"))
    assert isinstance(out, TransportResult)


def test_a_bobbin_job_survives_the_round_trip():
    a = acs(("CTR1_LD", "GRV1_ULD"))
    built = build_order(Job(job_id="job_0011", from_station="CTR1_LD",
                            to_station="GRV1_ULD", carries=Carried.BOBBIN))
    assert built.comment == "bobbin"
    assert a.create_order(built).errorCode == ERR_BUSY   # resolved, no robots


# -- the invented codes are quarantined --------------------------------------

def test_the_simulators_codes_are_ours_and_labelled_as_such():
    """The real server's table is still owed; these stand in for its shape."""
    assert set(SIM_ERROR_CODES) == {0, ERR_BUSY, ERR_UNKNOWN_STATION,
                                    ERR_NO_TASKS}
    assert SIM_ERROR_CODES[0] is TransportResult.ACCEPTED


def test_a_code_this_server_does_not_define_is_retryable():
    """Unknown means unknown — take the loud failure, not the silent one."""
    assert classify_error_code(4242, SIM_ERROR_CODES) is TransportResult.BUSY
