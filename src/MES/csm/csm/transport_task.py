# -*- coding: utf-8 -*-
"""The AGV transport task, with the states the CCS manual actually defines.

CCS manual §2.3, §4.6.6, §5.8–5.12.

WHY THIS IS NOT THE JOB FSM. `job_fsm.py` is the MES-side lifecycle — IDLE,
ASSIGNED, RUNNING, DONE, FAILED — and it answers "did the work happen and did
it succeed". This answers a different question: **where is the vehicle in this
one transport, right now**. The manual keeps them apart and so do we, because
three of its rules cannot be stated without the finer states:

  * cancellation is legal in two states, REFUSED in a third and pointless in
    the fourth (§5.12)
  * a task counts as in flight if it has not arrived **or** it has arrived and
    a post-task is still pending (§4.6.6)
  * completion writes the carried identity into the TARGET rack (§4.6.6)

Collapsing all four into RUNNING loses each of them, and the first one loses it
in the expensive direction: cancelling a loaded task leaves the AGV standing in
the middle of the plant holding a pallet — 取消的话 AGV 停在半路.

NOTHING CALLS THIS YET. It is the model, with the rules and their sources, and
the wiring into `SimAcs` is deliberately a separate change so that a live run
can be trusted while it happens.
"""

from dataclasses import dataclass, field
from enum import Enum


class TaskState(Enum):
    """The four states, §4.6.6, in the order the manual lists them."""

    #: 中控已下发 — CCS gave the task to the AGV system; it was received, but
    #: no vehicle has been assigned.
    DISPATCHED = "中控已下发"
    #: 开始执行 — a vehicle is assigned. THE VEHICLE NUMBER APPEARS AT THIS
    #: STEP, which is why `vehicle` is None until here and not before.
    EXECUTING = "开始执行"
    #: 已装载 — the AGV reached the source rack and jacked the pallet.
    LOADED = "已装载"
    #: 已送达 — the AGV reached the target rack and placed the pallet.
    ARRIVED = "已送达"


class PostTaskState(Enum):
    """The parallel state every task carries, §4.6.6.

    Parallel, not sequential: a task has a transport state AND a post-task
    state at the same time, and "in flight" is a question about both.
    """

    NONE = "无后置"          # this task has no post-task
    PENDING = "待处理"       # needs one, not yet dispatched
    DISPATCHED = "已下发"    # needs one, dispatched
    CANCELLED = "已取消"     # needed one, no longer


class Ageing(Enum):
    """§2.3. White is normal; the manual gives two thresholds and one colour
    each, and applies both to the post-task status as well."""

    NORMAL = "normal"
    WARNING = "预警"         # 10 minutes with no status update
    ABNORMAL = "abnormal"    # 20 minutes — treated as timed out


class Escalation(Enum):
    """§5.3–5.12, repeated verbatim six times. IN THIS ORDER ONLY.

    Every level in the manual is prefixed 联系供应商 — contact the supplier
    first — and 切不可私自操作, never on your own authority. The enum exists so
    that a caller has to name which level it is using, rather than reaching for
    the most convenient one.
    """

    #: Report complete/cancel to the AGV system; it ends the task and reports
    #: back; only then does CCS unlock the racks. The real one.
    REPORT = "report"
    #: CCS reports to ITSELF — unlocks its racks, no interaction with the AGV
    #: system. Only when the supplier confirms the vehicle already finished.
    SIMULATE = "simulate"
    #: Clear the task. ONLY when the task number exists in CCS but has no
    #: record in the AGV system. Forbidden if it shows any real state.
    CLEAR = "clear"


#: §2.3. Ten minutes with no status update is a warning, twenty is abnormal.
WARNING_SECONDS = 10 * 60.0
ABNORMAL_SECONDS = 20 * 60.0


@dataclass
class TransportTask:
    """One transport, from one rack to another.

    The carried identity is on the task rather than looked up elsewhere because
    §4.6.6 makes the task the CARRIER: completion writes the material type,
    attribute, bobbin type and roll number into the target rack. If the task
    does not hold them, delivery has nothing to transfer.
    """

    task_id: str
    from_rack: str = None
    to_rack: str = None
    state: TaskState = TaskState.DISPATCHED
    post_task: PostTaskState = PostTaskState.NONE
    #: None until EXECUTING. The manual is explicit that the vehicle number
    #: appears at that step and not before.
    vehicle: str = None
    dispatched_at: float = 0.0
    #: When the AGV system last said anything. Ageing is measured from here,
    #: NOT from dispatch — a task reporting every minute for an hour is
    #: healthy, and one silent for twenty minutes is not, however new it is.
    last_report_at: float = 0.0
    cancelled: bool = False

    material_ref: str = None
    material_type: object = None
    material_attribute: object = None
    bobbin_type: int = None

    history: list = field(default_factory=list)

    # -- the transitions -------------------------------------------------

    def _to(self, state, at):
        self.state = state
        self.last_report_at = at
        self.history.append((at, state))
        return self

    def assign(self, vehicle, at):
        """§4.6.6 ②. The vehicle number appears here."""
        self.vehicle = vehicle
        return self._to(TaskState.EXECUTING, at)

    def loaded(self, at):
        """§4.6.6 ③ — reached the source rack and jacked the pallet."""
        return self._to(TaskState.LOADED, at)

    def arrived(self, at):
        """§4.6.6 ④ — reached the target rack and placed the pallet."""
        return self._to(TaskState.ARRIVED, at)

    def report(self, at):
        """The AGV system said something without changing state. Enough to
        keep the task out of the ageing thresholds, which is the point."""
        self.last_report_at = at
        return self

    # -- cancellation, which is the rule that needs the states -----------

    def may_cancel(self):
        """§5.12. Legal before the vehicle reaches the source, and not after.

        LOADED is the one that matters: 取消的话 AGV 停在半路 — the AGV would
        stop in the middle of the route holding a pallet. ARRIVED returns False
        as well, but for the opposite reason: there is nothing left to cancel.
        """
        return self.state in (TaskState.DISPATCHED, TaskState.EXECUTING)

    def cancel(self, at):
        """Returns True if the cancel was accepted. Refusal is not an error —
        it is the rule doing its job, and the caller has to hear it."""
        if not self.may_cancel():
            return False
        self.cancelled = True
        self.last_report_at = at
        self.history.append((at, "cancelled"))
        return True

    # -- what "in flight" means ------------------------------------------

    @property
    def in_flight(self):
        """§4.6.6. NOT ARRIVED, or arrived with a post-task still pending.

        Every screen in the manual that lists running work uses this
        definition, and it is why the post-task state cannot be an
        afterthought: a task that has delivered its pallet and still owes a
        return leg is occupying a vehicle, and a count that ignores it will
        over-commit the line.
        """
        if self.cancelled:
            return False
        if self.state is not TaskState.ARRIVED:
            return True
        return self.post_task in (PostTaskState.PENDING,
                                  PostTaskState.DISPATCHED)

    @property
    def complete(self):
        return not self.in_flight and not self.cancelled

    # -- ageing ------------------------------------------------------------

    def ageing(self, now):
        """§2.3. Applies to the post-task status too, hence `last_report_at`
        being touched by post-task changes as well as transport ones."""
        silent = now - self.last_report_at
        if silent >= ABNORMAL_SECONDS:
            return Ageing.ABNORMAL
        if silent >= WARNING_SECONDS:
            return Ageing.WARNING
        return Ageing.NORMAL

    # -- the post-task -----------------------------------------------------

    def needs_post_task(self, at):
        self.post_task = PostTaskState.PENDING
        self.last_report_at = at
        return self

    def post_task_dispatched(self, at):
        self.post_task = PostTaskState.DISPATCHED
        self.last_report_at = at
        return self

    def post_task_cancelled(self, at):
        """§4.6.6 ④: it was needed and is no longer. Distinct from NONE, which
        means it was never needed — the two look the same from outside and
        answer different questions when something has gone wrong."""
        self.post_task = PostTaskState.CANCELLED
        self.last_report_at = at
        return self

    # -- what completion hands to the target rack -------------------------

    def carried_identity(self):
        """§4.6.6: what completion writes INTO THE TARGET RACK.

        Returned rather than written here, because the task does not own the
        rack. `records.describe_slot` takes exactly this.
        """
        return {"material_type": self.material_type,
                "material_attribute": self.material_attribute,
                "bobbin_type": self.bobbin_type}
