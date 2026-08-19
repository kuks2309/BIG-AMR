"""The four-step cancellation dance — telling a machine we are not coming.

Source: `AGV与主机设备对接流程及协议.xlsx`, sheet 主机与AGV交互变量表, analysed in
the project handbook (held outside this repository):

    AGV-side cancellation is a four-step dance: AGV sets
    `AGV_Task_Processing = 9` -> host deletes the task -> host sets
    `MC_Task_Delete = 1` -> AGV moves off 9 -> host clears
    `MC_Task_Delete = 0`. The machine then raises an alarm; an operator resets
    it and re-dispatches.

WHY THIS EXISTS AT ALL
======================
Because a machine's call is acknowledged long before the work is finished.
`AGV_Task_Recive = 1` makes the machine STOP ASKING — that is its whole
purpose — so from the moment we answer, the machine is silent and waiting. If
CSM then gives up, and says nothing, the machine waits for ever for a robot
that is never coming. Nobody notices: our job retired, the machine's request
succeeded, and the material simply stands there.

So the acknowledgement is a promise, and this is the only way to give it back.

THE STEPS ARE A CONVERSATION, NOT A SEQUENCE
============================================
Each side waits for the other, and the ONE rule that carries the safety is that
we may only clear `AGV_Task_Processing = 9` after seeing `MC_Task_Delete = 1`.
Never on a timer. Clearing 9 because time passed would take the cancellation
back without the machine ever having seen it, which restores exactly the silent
loss this closes — and does it while looking like a completed handshake.

Which is the same principle as the docking watchdog in `handshake.py`: silence
never means "clear". Here silence means "the machine has not heard us yet, so
keep saying it".

WHAT COMES AFTER
================
The alarm is the point of the last step. The work does not come back to CSM —
it goes to a person, who resets the machine and lets it dispatch again. That is
the correct owner: CSM has already tried and failed a bounded number of times
(specification A7), and something at the station needs a human eye.
"""

from enum import Enum


class CancelState(Enum):
    """Where the four steps have got to."""

    #: Step 1 done. `AGV_Task_Processing = 9` is asserted and we are waiting
    #: for the machine to delete the task.
    RAISED = "raised"

    #: Steps 2-3 seen, step 4 done: the machine set `MC_Task_Delete = 1`, so
    #: we cleared 9. Waiting for it to clear the flag in turn.
    DELETING = "deleting"

    #: All four done. The machine has alarmed and an operator owns it now.
    COMPLETE = "complete"

    #: The machine has not answered in time. NOT a terminal state — a late
    #: reply is still a reply, and this recovers if one arrives.
    STALLED = "stalled"

    #: This link cannot report `MC_Task_Delete`, so the dance cannot be run.
    #: We asserted 9 and genuinely cannot tell whether it landed. Said out
    #: loud rather than assumed, for the same reason as
    #: `ConfirmState.UNVERIFIABLE`.
    UNVERIFIABLE = "unverifiable"


#: The task-cancelled code, `AGV_Task_Processing = 9`. Named because the bare
#: 9 appears in three files and a wrong one of them would be silent.
TASK_CANCELLED = 9


class TaskCancellation:
    """One cancellation in flight, driven by observations of `MC_Task_Delete`.

    Written as a state machine fed from outside — `observe(now, flag)` — rather
    than as something that reads a client itself, so that a test can drive all
    four steps deterministically and so the poll timestamp is the caller's.
    """

    def __init__(self, station, job_id, call_id, started_at, reply_timeout_s):
        """
        :param reply_timeout_s: how long to wait for the machine at each step.
            Required, with no default, because we do not have this number: the
            protocol does not state one. A default would be an invented figure
            that later gets believed. See `EquipmentAdapter.CANCEL_REPLY_TIMEOUT_S`
            for the placeholder actually in use and why it is not measured.
        """
        if reply_timeout_s is None or reply_timeout_s <= 0:
            raise ValueError("reply_timeout_s must be positive; there is no "
                             "safe default for how long a machine may take")
        self.station = station
        self.job_id = job_id
        self.call_id = call_id
        self.started_at = float(started_at)
        self.reply_timeout_s = float(reply_timeout_s)

        self.state = CancelState.RAISED
        #: When the step currently being waited on began.
        self._waiting_since = float(started_at)
        #: When this first ran out of patience, if it ever did. Kept even after
        #: a recovery, because "answered late" is worth seeing.
        self.stalled_at = None
        #: When `MC_Task_Delete = 1` was first seen — the moment the machine
        #: DEFINITELY knows. Held as its own fact rather than read off the
        #: state, because a stall during the second half would otherwise make
        #: `handed_back` go back to False and report a stranded machine that
        #: has in fact already been told.
        self.acknowledged_at = None

    # -- what the machine can see from us --------------------------------

    @property
    def agv_task_processing(self):
        """The code we are asserting, or None once step 4 has cleared it.

        Still 9 while STALLED. Holding it is the whole fail-safe: if the
        machine has not acknowledged, it has not been told.
        """
        return None if self.handed_back else TASK_CANCELLED

    # -- what the caller wants to know ------------------------------------

    @property
    def handed_back(self):
        """Has the machine DEFINITELY been told?

        True from the moment `MC_Task_Delete = 1` is seen. This is the fact
        that matters: a stall before this point means the material is stranded
        and nobody knows, a stall after it means only that the handshake did
        not finish tidily.
        """
        return self.acknowledged_at is not None

    @property
    def done(self):
        return self.state is CancelState.COMPLETE

    @property
    def stranded(self):
        """Stalled, and the machine still does not know. The bad case."""
        return self.state is CancelState.STALLED and not self.handed_back

    # -- the dance ---------------------------------------------------------

    def observe(self, now, mc_task_delete):
        """Feed one poll of `MC_Task_Delete`. Returns the new state.

        `mc_task_delete` of None means the link cannot report the signal —
        which is different from reporting False, and must not be rounded to it.
        """
        if self.state in (CancelState.COMPLETE, CancelState.UNVERIFIABLE):
            return self.state

        if mc_task_delete is None:
            self.state = CancelState.UNVERIFIABLE
            return self.state

        waiting_for_delete = not self.handed_back

        if waiting_for_delete:
            if mc_task_delete:
                # Step 3 seen. Step 4 is ours, and it is only allowed here.
                self.acknowledged_at = now
                self.state = CancelState.DELETING
                self._waiting_since = now
                return self.state
        else:
            if not mc_task_delete:
                self.state = CancelState.COMPLETE
                return self.state

        if now - self._waiting_since >= self.reply_timeout_s:
            if self.stalled_at is None:
                self.stalled_at = now
            self.state = CancelState.STALLED
        return self.state

    def __repr__(self):
        return (f"<TaskCancellation {self.station} {self.job_id} "
                f"{self.state.value}>")
