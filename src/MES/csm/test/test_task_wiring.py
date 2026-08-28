"""The manual's task record, wired to the vehicles that produce it.

`transport_task.py` had every rule and no callers - the model existed and
nothing constructed one. These tests are about the CALLERS: that a transport
passes through 中控已下发 / 开始执行 / 已装载 / 已送达 as the vehicle actually
moves, that a cancel is refused once loaded, and that a silent task is
announced.
"""

import pytest

from csm.adapters.base import TransportResult
from csm.transport_task import Ageing, PostTaskState, TaskState


class FakeLogger:
    def __init__(self):
        self.lines = []
    def info(self, m):
        self.lines.append(("info", m))
    def warn(self, m):
        self.lines.append(("warn", m))


class FakeClock:
    def __init__(self):
        self.t = 1000.0
    def now(self):
        return self
    @property
    def nanoseconds(self):
        return self.t * 1e9


class FakeNode:
    def __init__(self):
        self._log, self._clock = FakeLogger(), FakeClock()
    def get_logger(self):
        return self._log
    def get_clock(self):
        return self._clock


class FakeRobot:
    def __init__(self, name):
        self.name = name
        self._active_job = None
        self._loaded = False
        self._finished = []
    def _finish(self, job_id, result):
        self._finished.append((job_id, result))


def fleet(*names):
    """A SimAcs with only the task bookkeeping. The real one spawns SimRobots,
    which need a live ROS node and none of which participates in these rules."""
    from csm.adapters.sim_acs import SimAcs

    acs = object.__new__(SimAcs)
    acs.node = FakeNode()
    acs.robots = [FakeRobot(n) for n in names]
    acs._results = {}
    acs._tasks = {}
    acs._aged = {}
    return acs


def running(acs, job_id="job_0001", robot="amr1"):
    """A task in EXECUTING with a vehicle, as _dispatch leaves it."""
    from csm.transport_task import TransportTask

    now = acs._now()
    t = TransportTask(task_id=job_id, from_rack="1501", to_rack="1801",
                      dispatched_at=now, last_report_at=now)
    acs._tasks[job_id] = t
    t.assign(robot, now)
    r = next(r for r in acs.robots if r.name == robot)
    r._active_job = job_id
    return t


# --------------------------------------------- the states follow the vehicle

def test_a_task_is_created_dispatched_then_assigned():
    """§4.6.6 ① and ②. The vehicle number appears at EXECUTING and not before,
    which is why the task is built before `accept` rather than after."""
    import inspect

    from csm.adapters.sim_acs import SimAcs

    src = inspect.getsource(SimAcs._dispatch)
    at_task = src.index("TransportTask(")
    at_accept = src.index("robot.accept(job)")
    at_assign = src.index("task.assign(")

    assert at_task < at_accept < at_assign, \
        "DISPATCHED must be a real state, not one passed through too fast to see"


def test_loading_moves_the_task_to_LOADED():
    acs = fleet("amr1")
    t = running(acs)
    assert t.state is TaskState.EXECUTING

    acs.robots[0]._loaded = True
    acs._follow_tasks()

    assert t.state is TaskState.LOADED


def test_an_arrived_job_moves_the_task_to_ARRIVED():
    acs = fleet("amr1")
    t = running(acs)
    acs.robots[0]._loaded = True
    acs._follow_tasks()

    acs._results["job_0001"] = TransportResult.ARRIVED
    acs._follow_tasks()

    assert t.state is TaskState.ARRIVED
    assert t.in_flight is False


def test_a_state_is_only_ever_advanced():
    """A robot that has put its load down and picked up another is a NEW task
    with a new id. The old one arrived, and no report can un-arrive it."""
    acs = fleet("amr1")
    t = running(acs)
    acs._results["job_0001"] = TransportResult.ARRIVED
    acs._follow_tasks()
    assert t.state is TaskState.ARRIVED

    acs.robots[0]._loaded = True
    acs._follow_tasks()

    assert t.state is TaskState.ARRIVED


# ------------------------------------ §5.12, cancellation is state-dependent

def test_cancel_is_allowed_before_the_vehicle_reaches_the_source():
    acs = fleet("amr1")
    running(acs)

    assert acs.cancel_job("job_0001") is True
    assert acs._results["job_0001"] is TransportResult.FAILED


def test_cancel_is_REFUSED_once_the_task_is_loaded():
    """取消的话 AGV 停在半路 — the AGV would stop in the middle of the route
    holding a pallet. The old cancel_job returned True unconditionally, so a
    cancel at any moment reported success and stranded a loaded robot."""
    acs = fleet("amr1")
    t = running(acs)
    acs.robots[0]._loaded = True
    acs._follow_tasks()
    assert t.state is TaskState.LOADED

    assert acs.cancel_job("job_0001") is False
    assert "job_0001" not in acs._results, "the job must not be failed"
    assert acs.robots[0]._finished == [], "the robot must not be stopped"


def test_the_refusal_says_why():
    acs = fleet("amr1")
    running(acs)
    acs.robots[0]._loaded = True
    acs._follow_tasks()
    acs.cancel_job("job_0001")

    said = " ".join(m for _lvl, m in acs.node._log.lines)
    assert "cancel refused" in said
    assert "loaded" in said and "mid-route" in said


def test_a_job_with_no_task_can_still_be_cancelled():
    """Charge orders and anything else that never became a transport. A
    missing task must not make a job uncancellable."""
    acs = fleet("amr1")
    acs.robots[0]._active_job = "job_9999"

    assert acs.cancel_job("job_9999") is True


# ---------------------------------------------------- §2.3, task ageing

def test_a_silent_task_is_announced_once_per_level():
    """The failure the whole troubleshooting section is about, and it is
    invisible in a log that only prints transitions — the point is that
    nothing is happening."""
    from csm.transport_task import ABNORMAL_SECONDS, WARNING_SECONDS

    acs = fleet("amr1")
    running(acs)

    # A second past the threshold, not exactly on it. A poll never lands on
    # the boundary, and the clock's nanosecond round-trip loses a microsecond
    # either way — asserting the exact edge would test the float, not the rule.
    # `test_transport_task` pins the boundary itself, with no clock involved.
    acs.node._clock.t += WARNING_SECONDS + 1
    acs._follow_tasks()
    acs._follow_tasks()                       # a second poll must not repeat
    warned = [m for lvl, m in acs.node._log.lines if "预警" in m]
    assert len(warned) == 1, warned

    acs.node._clock.t += (ABNORMAL_SECONDS - WARNING_SECONDS)  # past it again
    acs._follow_tasks()
    bad = [m for lvl, m in acs.node._log.lines if lvl == "warn"]
    assert len(bad) == 1 and "abnormal" in bad[0]


def test_a_finished_task_is_not_aged():
    """It is not silent, it is done."""
    from csm.transport_task import ABNORMAL_SECONDS

    acs = fleet("amr1")
    running(acs)
    acs._results["job_0001"] = TransportResult.ARRIVED
    acs._follow_tasks()

    acs.node._clock.t += ABNORMAL_SECONDS * 2
    acs._follow_tasks()

    assert [m for lvl, m in acs.node._log.lines if lvl == "warn"] == []


# ------------------------------------------------------ what the view gets

def test_task_status_carries_the_state_and_whether_a_cancel_would_work():
    acs = fleet("amr1")
    running(acs)
    acs.robots[0]._loaded = True
    acs._follow_tasks()

    row = acs.task_status()[0]

    assert row["state"] == TaskState.LOADED.value
    assert row["vehicle"] == "amr1"
    assert row["in_flight"] is True
    assert row["may_cancel"] is False
    assert row["post_task"] == PostTaskState.NONE.value
    assert row["ageing"] == Ageing.NORMAL.value


def test_ageing_is_computed_not_stored():
    """It is a function of the clock. A stored copy would be wrong the moment
    nobody looked at it."""
    from csm.transport_task import WARNING_SECONDS

    acs = fleet("amr1")
    running(acs)
    assert acs.task_status()[0]["ageing"] == Ageing.NORMAL.value

    acs.node._clock.t += WARNING_SECONDS + 1

    assert acs.task_status()[0]["ageing"] == Ageing.WARNING.value
