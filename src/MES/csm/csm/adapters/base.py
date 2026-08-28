"""Adapter interfaces - the boundary between the CSM and the outside world.

Everything the CSM talks to sits behind one of these. The main cycle and the
job FSM depend on the interface only, never on a protocol.

That is not decoration, and it has now been proven rather than argued. From
2026-07-28 to 2026-08-04 the equipment protocol was **unknown** — the
specification had been requested and not received. Had protocol details been
allowed to reach the FSM, the whole job layer would have sat waiting on a third
party. Behind this interface it was written, tested and run against a mock
instead.

The specification arrived on 2026-08-04: OPC-UA for the machine tools, Siemens S7
over a PLC data block for the pack line. Two implementations, this one interface,
and not a line of the state machines changes.

⚠ One thing the specification changes about this interface. A machine requests a
robot by *changing* a value — the request is the transition, and the machine
clears the signal once it believes it was heard. `get_station_status` is a poll,
so a change that reverts between two samples is missed while the machine believes
the call succeeded. A push path is needed here; OPC-UA subscriptions are the
intended mechanism. Do not paper over it by polling faster.

The same reasoning applies to the ACS. Its interface is undecided — it may end up
being generated JSON path files, a new API, or Seer's own TCP API. The FSM should
not care, and behind this interface it does not.

Precedent in this repository: `Tools/Kinematics/can_transport.py` puts a
`CanTransport` ABC in front of socketcan / pcan / mock so the drive logic never
learns which CAN hardware is underneath. This is the same move, one layer up.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from .cancellation import CancelState, TaskCancellation, TASK_CANCELLED


class StationStatus(Enum):
    """What a production machine reports about itself.

    Deliberately small. These are the only distinctions the CSM needs, and
    a richer protocol is collapsed into them by the adapter rather than leaked
    upward.

    ⚠ These describe what a machine HAS. They do not say whether it wants
    anything — that is a separate question with a separate answer, and
    conflating the two is the mistake corrected on 2026-08-04. See
    `TransportCall` below.
    """

    IDLE = "idle"            # nothing loaded, nothing to collect
    BUSY = "busy"            # processing — holds material, but not available
    FINISHED = "finished"    # done — material is available for collection
    FAULT = "fault"          # broken; needs a human
    UNKNOWN = "unknown"      # unreachable or not answering


class TaskType(Enum):
    """What a machine is asking for, as the equipment issues it."""

    LOAD = 1     # bring material to me
    UNLOAD = 2   # take material away from me
    SWAP = 3     # take what I have, then bring me the next one


class TransportCall:
    """A machine asking for a robot.

    **This is the correction of 2026-08-04, and it is the direction of the whole
    system.**

    The earlier model was that the CSM watched machines and pushed work at
    them: a station reported FINISHED, so we invented a job to move its output
    onward. That is backwards. The equipment CALLS — very often because a human
    pressed a button on the machine or scanned a handheld terminal beside it —
    and only then does anything happen.

        operator or machine  ──call──▶  CSM  ──▶  release from the source

    Two consequences that are easy to miss:

    **The caller is the DESTINATION, not the source.** A machine calling for a
    LOAD is asking for material to be brought *to* it. Where that material comes
    from is our problem to work out, not something the call carries.

    **The call is a transition, and the machine clears it once it believes it
    was heard.** So an adapter must report an outstanding call until the FSM has
    acted on it — see `EquipmentAdapter.poll_calls`.
    """

    __slots__ = ("station_id", "task_type", "raised_at", "source")

    def __init__(self, station_id, task_type, raised_at=0.0, source="equipment"):
        self.station_id = station_id
        self.task_type = task_type
        #: Where the call came from — the machine itself, or a person with a
        #: handheld terminal. The protocol treats them identically; we record it
        #: because "a human is waiting" is worth seeing in a log.
        self.source = source
        self.raised_at = raised_at

    def __repr__(self):
        return (f"<TransportCall {self.station_id} "
                f"{self.task_type.name} via {self.source}>")


class EquipmentAdapter(ABC):
    """Production machines / process stations.

    Confirmed 2026-07-28 (Dr. Youngbo Shim): "Equipment" means production
    machines, not doors, lifts or conveyors.
    """

    @abstractmethod
    def poll_calls(self):
        """Outstanding transport calls. Returns a list of `TransportCall`.

        **The primary input to the whole system.** Machines ask; we answer.

        Polling is the specified interaction, not a shortcut — the interface is
        not event-driven, both sides raise bits, and the CSM is expected to scan
        continuously at a fixed interval.

        ⚠ An implementation must hold a call until `acknowledge_call` is
        received. A call is raised as a transition and the machine clears it
        once it believes it was heard, so an adapter that reports the raw level
        can drop a request between two scans while the machine believes it
        succeeded. Latch it here, where the protocol detail belongs, rather than
        exposing the race to the FSM. See debt-033.
        """

    @abstractmethod
    def acknowledge_call(self, call) -> None:
        """Tell the equipment its call was heard, so it stops asking."""

    @abstractmethod
    def get_station_status(self, station_id) -> StationStatus:
        """What this station currently HAS. Must not block for long.

        Note this is no longer how work is discovered — `poll_calls` is. This
        answers the different question of whether a source can actually give
        anything, which is what stops a robot being sent to collect from a
        machine that is empty or still processing.
        """

    @abstractmethod
    def send_station_command(self, station_id, command) -> bool:
        """Tell a station to do something. Returns True if accepted.

        ⚠ Whether the CSM is permitted to command equipment at all is not
        yet formally decided — Dr. Shim answered "I think b" on 2026-07-28,
        i.e. probably yes, not confirmed. If it stays permitted, the CSM can
        start and stop production machinery, which is a materially wider safety
        scope than read-only monitoring. Keep every call site behind this method
        so the capability can be revoked in one place.
        """

    #: How long to wait for a command to show up in the machine's own state
    #: before calling it lost. Not a measured number — it stands in until the
    #: equipment vendor gives one, the same gap as `debt-033`.
    COMMAND_TIMEOUT_S = 5.0

    def always_supplied(self, station_id) -> bool:
        """Is this a WAREHOUSE rather than a machine?

        A store that hands material over still has material — that is what
        makes it a store. So its state does not change when it is collected
        from, and a read-back can never confirm the collection. See
        `send_and_confirm`.
        """
        return False

    def presence(self, station_id):
        """What is physically on this station, or None if it cannot say.

        None is a real answer and must not be read as "nothing". An adapter
        that cannot report presence cannot confirm a command either, which is
        what `ConfirmState.UNVERIFIABLE` exists to say out loud.
        """
        return None

    def send_and_confirm(self, station_id, command, now, timeout=None):
        """Send a command and return the CONFIRMATION, not a boolean.

        The boolean from `send_station_command` is kept — some adapters can
        refuse outright, and that is worth knowing immediately — but it is not
        treated as evidence of effect. The returned object is resolved later by
        `resolve_confirmations`, once the machine has had time to act.
        """
        accepted = self.send_station_command(station_id, command)
        pending = CommandConfirmation(
            station_id=station_id,
            command=command,
            expect=EXPECTED_AFTER.get(command, frozenset()),
            sent_at=now,
            timeout=self.COMMAND_TIMEOUT_S if timeout is None else timeout,
        )
        if not accepted:
            # It said no. That IS evidence, and the only kind this protocol
            # ever gives directly.
            pending.state = ConfirmState.LOST
        elif not pending.expect:
            # A command with nothing to read back. Say so rather than assume.
            pending.state = ConfirmState.UNVERIFIABLE
        elif command == "collected" and self.always_supplied(station_id):
            # A WAREHOUSE DOES NOT EMPTY. Collecting from a store leaves it
            # looking exactly as it did, so presence cannot confirm or deny it.
            #
            # Found by this mechanism in a Gazebo run: the ASRS was convicted
            # of ignoring every 'collected' notification, twice per run, purely
            # because a store never stops being full. The command was fine; the
            # expectation was wrong for this kind of station.
            pending.state = ConfirmState.UNVERIFIABLE
        self._pending_commands.append(pending)
        return pending

    @property
    def _pending_commands(self):
        if not hasattr(self, "_pending_command_list"):
            self._pending_command_list = []
        return self._pending_command_list

    def resolve_confirmations(self, now):
        """Read back every outstanding command. Returns the ones that were LOST.

        Called every tick by whoever owns the poll loop. Lost commands are
        returned rather than logged here, so the caller decides what a lost
        notification means for the job it belonged to.
        """
        lost = []
        still_pending = []
        for pending in self._pending_commands:
            state = pending.poll(self.presence(pending.station_id), now)
            if state is ConfirmState.PENDING:
                still_pending.append(pending)
            elif state is ConfirmState.LOST:
                lost.append(pending)
        self._pending_command_list = still_pending
        return lost

    def task_processing(self, station_id):
        """The last `AGV_Task_Processing` code reported at this station.

        None when the adapter does not carry one — most do not yet, and a
        missing code must never be read as a code of zero.
        """
        return None

    # -- giving a call back: the four-step cancellation ------------------

    #: How long to wait for the machine at each step of the cancellation.
    #:
    #: NOT A MEASURED NUMBER. The protocol says the host deletes the task and
    #: answers; it does not say how quickly. This stands in until the equipment
    #: vendor gives one, the same gap as `COMMAND_TIMEOUT_S` and `debt-033`.
    #: Running out of it never clears our side of the handshake — see
    #: `cancellation.py` — so getting it wrong costs a false alarm, not a lost
    #: cancellation.
    CANCEL_REPLY_TIMEOUT_S = 10.0

    def task_delete_requested(self, station_id):
        """`MC_Task_Delete` at this station, or None if it cannot be read.

        None is the honest answer for a link that does not carry the signal,
        and it is NOT False. False says the machine has not deleted the task;
        None says we cannot tell, which is what makes the whole four-step
        handshake unverifiable rather than merely unfinished.
        """
        return None

    def cancel_task(self, station_id, job_id, now, call_id=None):
        """Step 1: tell the machine we are not coming. Returns the handshake.

        THE ACKNOWLEDGEMENT WAS A PROMISE. `AGV_Task_Recive = 1` makes the
        machine stop asking, so from the moment CSM answers a call the machine
        is silent and waiting. Abandoning the job without this leaves it
        waiting for ever, and every component involved believes it finished its
        own part correctly.

        The returned object is resolved later by `resolve_cancellations`, the
        same shape as `send_and_confirm`, because the remaining three steps are
        the machine's and ours in turn and none of them can happen now.
        """
        pending = TaskCancellation(
            station=station_id, job_id=job_id, call_id=call_id,
            started_at=now, reply_timeout_s=self.CANCEL_REPLY_TIMEOUT_S,
        )
        # Assert `AGV_Task_Processing = 9` where the adapter can carry it.
        # Adapters that cannot say so are caught by the None check below, not
        # by this being absent.
        self.write_task_processing(station_id, TASK_CANCELLED)
        if self.task_delete_requested(station_id) is None:
            pending.state = CancelState.UNVERIFIABLE
        self._pending_cancellations.append(pending)
        return pending

    def write_task_processing(self, station_id, code):
        """Put `AGV_Task_Processing` on the wire. `code` of None clears it.

        Separate from `set_task_processing`, which is how a TEST states what a
        robot reported. This is CSM writing the signal itself, and it is the
        only reason step 4 ever reaches the machine: the handshake object
        deciding it may drop the 9 changes nothing until somebody writes it.
        Left as a no-op on adapters with nowhere to put it.
        """
        setter = getattr(self, "set_task_processing", None)
        clearer = getattr(self, "clear_task_processing", None)
        if code is None:
            if clearer is not None:
                clearer(station_id)
        elif setter is not None:
            setter(station_id, code)

    @property
    def _pending_cancellations(self):
        if not hasattr(self, "_cancellation_list"):
            self._cancellation_list = []
        return self._cancellation_list

    def resolve_cancellations(self, now):
        """Advance every cancellation in flight. Returns (finished, stranded).

        `finished` are the ones that completed all four steps — the machine has
        alarmed and a person owns the work now. `stranded` are the ones where
        the machine has still not acknowledged: those keep asserting 9 and are
        returned EVERY tick, because a station whose material nobody is coming
        for should not stop being reported after one line of log.
        """
        finished, stranded, still_pending = [], [], []
        for pending in self._pending_cancellations:
            state = pending.observe(now, self.task_delete_requested(pending.station))
            # STEP 4 IS A WRITE, not a decision. `agv_task_processing` goes to
            # None the moment `MC_Task_Delete = 1` is seen, and until that None
            # is written the machine still sees a 9 and waits for ever.
            self.write_task_processing(pending.station,
                                       pending.agv_task_processing)
            if state is CancelState.COMPLETE:
                finished.append(pending)
            elif state is CancelState.UNVERIFIABLE:
                finished.append(pending)
            else:
                if pending.stranded:
                    stranded.append(pending)
                still_pending.append(pending)
        self._cancellation_list = still_pending
        return finished, stranded

    def can_accept(self, station_id) -> bool:
        """Is this station free to RECEIVE something right now?

        Default: only an idle one. Not abstract, because it is derivable from
        `get_station_status` and every existing implementation already answers
        it correctly by that rule.

        A WAREHOUSE is the exception and must override this. A store is never
        idle — it permanently holds material to give — but it can always take a
        return. Judging it by status alone refuses it as a destination, which
        is what silently swallowed every leg-A bobbin return: the route to the
        ASRS existed, the ASRS simply never looked free.
        """
        if self.buffer_full(station_id):
            return False
        return self.get_station_status(station_id) is StationStatus.IDLE

    def buffer_full(self, station_id) -> bool:
        """Has the equipment ITSELF said this port has no empty slot?

        THE CUSTOMER'S OWN SIGNAL, AND IT WINS OVER OUR INFERENCE. Code 4 is
        reported by the AGV that just tried to place material there. Station
        status is our reading of whether a port looks free; this is the
        equipment saying it is not. When the two disagree, the one that was
        actually present is right.

        A separate method because every path that asks "can this take
        material?" has to honour it — including a warehouse, which otherwise
        answers yes on the grounds that a store always has room.
        """
        code = self.task_processing(station_id)
        return (code is not None
                and TaskProcessing(code) is TaskProcessing.BUFFER_FULL)

    @abstractmethod
    def list_stations(self):
        """All station ids this adapter knows about."""


# ---------------------------------------------------------------------------
# THE EQUIPMENT MODEL — OPC-UA, from `AGV与主机设备对接流程及协议.xlsx`
# (sheet 主机与AGV交互变量表; analysed in the project handbook, outside this
# repository). Variable names below are the CUSTOMER'S, for the same reason the
# ACS field names are the vendor's: a renamed signal cannot be checked against
# the real machine.
#
# Every signal exists twice — `_UW` (unwind) and `_RW` (rewind).
# ---------------------------------------------------------------------------


class Polarity(Enum):
    """First digit of `MC_Num`. Note the numbering is NOT alphabetical."""

    ANODE = 1
    CATHODE = 2


class EquipmentType(Enum):
    """Second character of `MC_Num`."""

    GRAVURE = "A"
    COATING = "T"
    COLD_PRESS = "L"


class DockingAxis(Enum):
    """`MC_Axis_Num` — WHICH of a machine's four docking axes is meant.

    A machine is not one port. It has an unwind side and a rewind side, each
    with an A and a B axis, and the whole variable block is duplicated `_UW` /
    `_RW` to match. The deck's coater drawing shows the pair directly:
    Unwinder takes a bobbin and gives back a roll, Rewinder takes a roll and
    gives back a bobbin.
    """

    UNWIND_A = 1
    UNWIND_B = 2
    REWIND_A = 3
    REWIND_B = 4

    @property
    def is_unwind(self):
        return self in (DockingAxis.UNWIND_A, DockingAxis.UNWIND_B)

    @property
    def suffix(self):
        """The variable-name suffix for this axis's half of the block."""
        return "_UW" if self.is_unwind else "_RW"


class MachineNumber:
    """`MC_Num`, e.g. `1A01` — string[5]. THE station's real identity.

    This replaces the invented names (`station_3`, `station_out`) that the CSM
    grew while the protocol was unknown. It is also exactly the `station_map`
    record the specification's section 7 asks for: our name on one side, the
    customer's port id on the other.

        1     A     01
        |     |     +-- sequence number
        |     +-------- equipment type: A gravure, T coating, L cold press
        +-------------- polarity:       1 anode,   2 cathode
    """

    __slots__ = ("polarity", "equipment", "sequence")

    def __init__(self, polarity, equipment, sequence):
        self.polarity = Polarity(polarity)
        self.equipment = EquipmentType(equipment)
        self.sequence = int(sequence)

    @classmethod
    def parse(cls, text):
        """Read a `MC_Num` off the wire.

        Rejects anything that is not the documented shape rather than guessing.
        A misread machine number sends a robot to the wrong machine, so this is
        the wrong place to be lenient.
        """
        text = str(text).strip()
        if len(text) != 4 or not text[0].isdigit() or not text[2:].isdigit():
            raise ValueError(f"MC_Num must look like 1A01, got {text!r}")
        return cls(int(text[0]), text[1], int(text[2:]))

    def __str__(self):
        return f"{self.polarity.value}{self.equipment.value}{self.sequence:02d}"

    def __eq__(self, other):
        return isinstance(other, MachineNumber) and str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        return f"MachineNumber({self})"


class MaterialPresence(Enum):
    """What is physically on the machine, from three booleans.

    The protocol does not report a status; it reports presence, with
    `MC_Rolling_Full`, `MC_Roll_Null` and `MC_Roll_IN`. Those three replace the
    five-value `StationStatus` this file invented while the protocol was
    unknown:

        Rolling_Full  Roll_Null  Roll_IN   meaning
              1            0         0     a full roll is on the machine
              0            1         0     nothing on the machine
              0            0         1     an empty bobbin is on the machine

    EMPTY_BOBBIN is the one that matters and the one we could not express: it is
    what makes the specification's six bobbin-return jobs observable at all.
    """

    FULL_ROLL = "full_roll"
    NOTHING = "nothing"
    EMPTY_BOBBIN = "empty_bobbin"
    #: The three booleans disagreed. Real machines can report this during a
    #: transition, and it must not be silently rounded to one of the others.
    INCONSISTENT = "inconsistent"

    @classmethod
    def from_signals(cls, rolling_full, roll_null, roll_in):
        flags = (bool(rolling_full), bool(roll_null), bool(roll_in))
        if flags == (True, False, False):
            return cls.FULL_ROLL
        if flags == (False, True, False):
            return cls.NOTHING
        if flags == (False, False, True):
            return cls.EMPTY_BOBBIN
        return cls.INCONSISTENT


class TaskProcessing(Enum):
    """`AGV_Task_Processing` — the nine codes the AGV reports to the machine.

    `TransportResult` collapses 2-7 into a single BUSY. These are the customer's
    own distinctions and two of them (6 and 7) are exactly the conditions this
    file previously had to infer.

    Code 4 is load-bearing: it is the customer's own trigger for diverting to a
    WIP rack, which is what the specification's jobs 4, 8 and 12 exist for.
    """

    SUCCESS = 1
    BUFFER_EMPTY = 2                # no material to take
    BUFFER_AWAITING_STORAGE = 3
    BUFFER_FULL = 4                 # no empty slot -> divert to WIP
    BUFFER_LACKS_MATERIAL = 5
    TRAFFIC_JAM = 6
    GOING_TO_CHARGE = 7
    AGV_FAULT = 8
    TASK_CANCELLED = 9


class ConfirmState(Enum):
    """How a sent command turned out — which is NOT what the send returned."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    #: The timeout passed and the expected state never appeared. The command
    #: was accepted and did nothing.
    LOST = "lost"
    #: We cannot tell. The adapter reports no presence, so there is nothing to
    #: read back. Deliberately NOT "confirmed" — an unverifiable command must
    #: not be recorded as a successful one.
    UNVERIFIABLE = "unverifiable"


#: What each command should leave behind, read back from the presence booleans.
#:
#: "collected" means the material is gone, which is either an empty machine or
#: one holding the empty core. "delivered" means a full roll is now there.
EXPECTED_AFTER = {
    "collected": frozenset({MaterialPresence.NOTHING,
                            MaterialPresence.EMPTY_BOBBIN}),
    "delivered": frozenset({MaterialPresence.FULL_ROLL}),
}


@dataclass
class CommandConfirmation:
    """A command that was sent, and has not yet been shown to have happened.

    THE SEND IS NOT THE EFFECT. The equipment link is shared memory, not a
    transaction: there is no acknowledgement, so `send_station_command()`
    returning True says a value was written and nothing whatever about whether
    the machine acted on it. A CSM that treats the return as proof has believed
    something the wire never told it — `debt-034`.

    The only evidence available is the machine's own state afterwards. So a
    command is held here until either the expected state appears, or the
    timeout passes and it is declared lost.
    """

    station_id: str
    command: str
    expect: frozenset
    sent_at: float
    timeout: float
    state: ConfirmState = ConfirmState.PENDING

    def poll(self, presence, now):
        """Read the machine back. `presence` is None if it cannot report one."""
        if self.state is not ConfirmState.PENDING:
            return self.state
        if presence is None:
            self.state = ConfirmState.UNVERIFIABLE
        elif presence in self.expect:
            self.state = ConfirmState.CONFIRMED
        elif now - self.sent_at >= self.timeout:
            self.state = ConfirmState.LOST
        return self.state


class TransportResult(Enum):
    """Outcome of a transport job, as reported by the ACS."""

    # ⚠ 2026-08-14: the real ACS returns a single integer error code on every
    # mutation, and job outcomes are free text rather than an enum. Nothing in
    # the GraphQL schema distinguishes "busy, retry" from
    # "rejected, give up". That distinction is the whole reason these two enum
    # members exist, and it now depends on an errorCode table we have asked for
    # and not received. Do not guess the mapping; a wrong guess either retries
    # forever or fails a job that would have run.
    ACCEPTED = "accepted"
    REJECTED = "rejected"      # invalid job — will never succeed, fail it
    BUSY = "busy"              # no robot free right now — retry later
    IN_PROGRESS = "in_progress"
    ARRIVED = "arrived"
    FAILED = "failed"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# THE REAL ACS INTERFACE — MAPPED 2026-08-14 FROM THE GRAPHQL SCHEMA
#
# The schema arrived after the 2026-08-14 ACS meeting. **The schema and the full
# field-by-field mapping are held outside this repository** — vendor material,
# and this repository is public:
#
#     References/local/acs/schema.graphql          the schema itself
#     References/local/acs/schema-analysis.md      the mapping onto this file
#
# NOTHING BELOW IS IMPLEMENTED YET. Conclusions only, so that the next person to
# touch this file knows what is coming and why.
#
# HOW OUR THREE METHODS MAP
#
#   submit_job      -> the create mutation
#   get_job_result  -> a subscription (preferred), or a query
#   cancel_job      -> TWO operations, cancel and abort, not one
#
# WHAT THE SCHEMA GIVES US THAT THIS INTERFACE CANNOT EXPRESS
#
# 1. AN ORDER IS AN ORDERED LIST OF TASKS, NOT A MOVE. This is the most important
#    finding, and it DISSOLVES the exchange gap (gazebo open question B0): a
#    deliver-and-collect visit is one order with two tasks, not a new primitive.
#    `TaskType.SWAP` above becomes a two-task order. `Job` carries one origin and
#    one destination today; it will need to carry a task list.
#
# 2. PRIORITY EXISTS AND IS OURS TO SET, with a separate hot-lot flag. We have no
#    priority concept at all.
#
# 3. CANCEL AND ABORT ARE SEPARATE OPERATIONS — and, contradicting what we took
#    from the meeting, **abort does NOT take a drop-off location**. The ACS
#    decides where the load goes. Do not build that parameter.
#
# 4. THE PUSH PATH EXISTS, AND SO DOES A BASIS FOR RECONCILE: change events carry
#    a monotonic sequence number and both the old and the new value, so gap
#    detection is free. That is the answer to the edge-trigger problem this file
#    raises above and that `debt-033` tracks — stop polling `get_job_result` at
#    4 Hz. ⚠ The field the reconnect path would depend on is UNDOCUMENTED; its
#    meaning is inferred from its name and must be confirmed against the live
#    server before anything depends on it.
#
# 5. WAITING IS A REPORTED VEHICLE STATE, with a per-task wait timeout and an
#    explicit release operation. A robot holding at a port is distinguishable
#    from one that is lost, so the job timeout can stop treating a legitimate
#    hold as a fault.
#
# 6. CHARGING IS COMMANDABLE BY US, with a target percentage. Does not prove the
#    ACS will not also charge on its own.
#
# 7. REVERSING INTO A STATION is a first-class per-task option (gazebo A4).
#
# WHAT THE SCHEMA DOES **NOT** SETTLE — AND IT IS THE ONE THAT MATTERS HERE
#
# Every mutation returns a single integer error code, and job outcomes are free
# text rather than an enum. So the BUSY-versus-REJECTED distinction that
# `TransportResult` depends on lives in an **error-code table that is not in the
# schema**. Until we have it, any retry policy is guesswork — see the note on
# TransportResult above and `job_fsm.py:70`.
#
# COST OF DOING THIS PROPERLY: `AcsAdapter` has two implementations (`mock.py`,
# `sim_acs.py`) and four call sites (`main_cycle.py`, `mes_app.py`,
# `runtime/tasks/job_tracker.py`, `seer_client.py`). Widening the interface is a
# deliberate change across eight files and wants an ADR, not a drive-by edit.
# ---------------------------------------------------------------------------


@dataclass
class ProcessingOutcome:
    """What the CSM should DO about an `AGV_Task_Processing` code."""

    result: "TransportResult"
    #: Code 4 only. The destination has no empty slot, so the material has to
    #: go somewhere — the WIP rack — rather than the job simply failing.
    divert_to_buffer: bool = False
    note: str = ""


def interpret_task_processing(code):
    """Turn one of the nine codes into a CSM decision. THE ONLY PLACE THAT MAY.

    Same rule as `classify_error_code`, and for the same reason: nine codes
    scattered across the codebase become nine independent guesses, and the two
    that matter most are easy to get backwards.

    `TransportResult` collapses codes 2-7 into a single BUSY. That is not wrong
    — all six are retryable — but it throws away WHY, and one of them is not
    merely retryable:

      4  buffer full, no empty slot   THE CUSTOMER'S OWN DIVERT TRIGGER. The
                                      specification has three jobs (4, 8, 12)
                                      that exist for exactly this condition,
                                      and until now the CSM inferred it from
                                      station status instead of being told.

    The two that end a job rather than delaying it:

      8  AGV fault during transport   the robot is out, not the job
      9  task cancelled

    ⚠ Codes 2, 3 and 5 are read as retryable because they describe a MATERIAL
    state that can change without anyone intervening. That is our reading of
    the customer's wording, not something they have confirmed.
    """
    code = TaskProcessing(code)
    if code is TaskProcessing.SUCCESS:
        return ProcessingOutcome(TransportResult.ARRIVED, note="success")
    if code is TaskProcessing.BUFFER_FULL:
        return ProcessingOutcome(TransportResult.BUSY, divert_to_buffer=True,
                                 note="destination full — park on the WIP rack")
    if code in (TaskProcessing.AGV_FAULT, TaskProcessing.TASK_CANCELLED):
        return ProcessingOutcome(TransportResult.FAILED, note=code.name.lower())
    return ProcessingOutcome(TransportResult.BUSY, note=code.name.lower())


# ---------------------------------------------------------------------------
# THE ORDER MODEL — ADR 2026-08-18-acs-order-task-interface
#
# Field names and enum members below are the VENDOR'S SPELLING, taken from
# `References/local/acs/schema.graphql` (outside this repository: vendor
# material, this repository is public). They are deliberately not renamed to
# our taste — a name that differs from the schema cannot be checked against the
# live server, and this is the interface the real ACS arrives behind.
# ---------------------------------------------------------------------------


class TaskKind(Enum):
    """One step of an order. The schema's enum, verbatim.

    The CSM specification (rev01 §5) names six tasks: MOVE, LOAD, UNLOAD, WAIT,
    SCAN, CHARGE. Five map onto identically-named members here; **WAIT is
    STAGE** — the specification's own "ACS kind" column says so. The remaining
    members exist in the schema and are carried so that an order read back from
    the server is representable, not because we issue them.
    """

    NONE = "NONE"
    LOAD = "LOAD"
    UNLOAD = "UNLOAD"
    STAGE = "STAGE"          # the specification's WAIT — hold at the port
    SCAN = "SCAN"
    TURN = "TURN"
    PORT_CUSTOM = "PORT_CUSTOM"
    CHARGE = "CHARGE"
    MAINT = "MAINT"
    MOVE = "MOVE"
    NODE_CUSTOM = "NODE_CUSTOM"


@dataclass
class AcsTask:
    """One entry of an order's task list — the schema's `TaskInput`.

    Every field is optional except `kind`, matching the schema. `target` is the
    port or node id; leaving it None is meaningful for kinds that do not need
    one (CHARGE picks its own charger unless told otherwise).
    """

    kind: TaskKind
    target: str = None
    vehicleSlot: int = None
    amount: int = None
    carrierId: str = None
    carrierModel: str = None
    carrierCustom: object = None
    independent: bool = None
    enterReverse: bool = None
    chargeTo: int = None
    expectedDuration: int = None
    noBlockingTime: int = None
    waitTimeout: int = None
    turnAngle: float = None
    custom: object = None


@dataclass
class AcsOrder:
    """What `createOrder` takes — the schema's `CreateOrderInput`.

    `id` is ours to choose and is how every later operation names this order, so
    it must be unique and stable. We use the job id, which makes an ACS order
    traceable back to the job that raised it without a second lookup — that is
    the `acs_order_id` field the specification's §7 job record asks for.
    """

    id: str
    tasks: list = field(default_factory=list)
    vehicleId: str = None
    priority: int = None
    hotLot: int = None
    custom: object = None
    requester: str = None
    requesterDetail: str = None
    comment: str = None


@dataclass
class SimpleResponse:
    """What every ACS mutation returns — `{errorCode: Int!, message: String}`.

    One integer for every failure mode there is. See `classify_error_code`.
    """

    errorCode: int
    message: str = ""

    @property
    def ok(self):
        return self.errorCode == 0


#: Error codes WE invented, because the vendor's table has not been supplied.
#:
#: Marked PROVISIONAL and kept in one place on purpose. When the real table
#: arrives, this dict and `classify_error_code` are the only things that change
#: — nothing else in the CSM is allowed to interpret an integer error code.
PROVISIONAL_ERROR_CODES = {
    0: TransportResult.ACCEPTED,
}


def classify_error_code(code, table=None):
    """Turn an ACS `errorCode` into a TransportResult. THE ONLY PLACE THAT MAY.

    :param table: the code table of the server being talked to. An adapter that
        KNOWS its own codes — the simulator invented its own, so it does —
        passes them here. Without one, only zero is understood.

    ⚠ THE VENDOR'S ERROR-CODE TABLE DOES NOT EXIST IN THE SCHEMA. Our own
    analysis calls it "the single most important thing still owed to us", and
    the CSM specification carries it as assumption A7. So the busy-versus-
    rejected distinction — the one that decides whether a job is retried for
    ever or failed while it would have run — is currently a guess.

    The guess is confined to this function so that receiving the table is a
    one-function change rather than a hunt across the codebase. Anywhere else
    that wants to know what a code means must call this.

    Until the table exists we treat every non-zero code as BUSY, i.e. retryable.
    That is the deliberately conservative direction: retrying a job that should
    have been rejected wastes robot time and is visible in the logs, whereas
    failing a job that would have run loses material movement silently. The job
    FSM's own retry ceiling stops the first from running away.
    """
    table = PROVISIONAL_ERROR_CODES if table is None else table
    if code in table:
        return table[code]
    return TransportResult.BUSY


def build_order(job, requester="CSM", rotate=False):
    """Turn a CSM job into an ACS order — an id and an ordered task list.

    The sequences are the specification's, rev01 §5:

        a roll delivery          MOVE -> LOAD -> MOVE -> UNLOAD
        deliver-and-collect      MOVE -> UNLOAD -> WAIT -> LOAD   (ONE visit)
        needing a 180 deg turn   MOVE -> LOAD -> TURN -> MOVE -> UNLOAD

    The second is the one that matters, and it is why an order has to be a list
    at all. `Carried`'s docstring states the plant's actual shape: **every hop
    here is an exchange, not a delivery** — a robot brings a full roll to a
    machine and takes the empty core away in the same visit. Expressed as two
    orders that is two trips to the same port; expressed as one order it is one
    visit, which is what the machine's docking handshake expects.

    WAIT is `TaskKind.STAGE`. The specification's own "ACS kind" column says so.

    The order id is the job id. That is deliberate: it makes an ACS order
    traceable back to the job that raised it with no second lookup, and it is
    what the §7 job record calls `acs_order_id`.
    """
    same_port = job.from_station == job.to_station
    if same_port:
        # One visit. Put down what we carry, hold while the machine works the
        # exchange, then pick up what it gives back. The hold is not padding —
        # the machine confirms placement and pickup separately (MC_Put_OK then
        # MC_Take_OK), so the robot must still be there between them.
        tasks = [
            AcsTask(kind=TaskKind.MOVE, target=job.from_station),
            AcsTask(kind=TaskKind.UNLOAD, target=job.from_station),
            AcsTask(kind=TaskKind.STAGE, target=job.from_station),
            AcsTask(kind=TaskKind.LOAD, target=job.from_station),
        ]
    else:
        tasks = [
            AcsTask(kind=TaskKind.MOVE, target=job.from_station),
            AcsTask(kind=TaskKind.LOAD, target=job.from_station),
            AcsTask(kind=TaskKind.MOVE, target=job.to_station),
            AcsTask(kind=TaskKind.UNLOAD, target=job.to_station),
        ]

        # ROTATION IS THE ESCAPE HATCH, AND IT IS A TASK (§1.3, §3.8).
        #
        # The face must match and nothing turns a bright face into a dark one.
        # The winding direction need not: a 180° turn of the pallet flips it,
        # and that turn is a first-class AGV task rather than something the
        # robot does implicitly. `material.needs_rotation` decides; this only
        # places it.
        #
        # AFTER LOAD, BEFORE THE MOVE. The pallet has to be on the deck to be
        # turned, and turning it at the destination would mean arriving with
        # the wrong presentation and blocking the port while it spins.
        if rotate:
            tasks.insert(2, AcsTask(kind=TaskKind.TURN,
                                    target=job.from_station))

    return AcsOrder(
        id=job.job_id,
        tasks=tasks,
        priority=job.priority,
        requester=requester,
        # What the job moves, carried through so the ACS and any later reader
        # can tell a roll job from a bobbin job without asking us. The order id
        # itself now says this too — see `naming.py` — but the id is one string
        # and this is a field, and a field is what a query can filter on.
        comment=job.carries.value,
    )


class AcsAdapter(ABC):
    """The fleet controller: picks a robot and a route, then drives it there."""

    def submit_job(self, job) -> TransportResult:
        """Hand a transport job over. Returns ACCEPTED, BUSY or REJECTED.

        THE DEFAULT THE COMMENT BLOCK ABOVE PROMISES, now actually here. Until
        2026-08-20 this was `@abstractmethod` with a docstring and no body while
        the block above stated that "`submit_job` has a default implementation
        here that builds an order and calls `create_order`, so an adapter only
        has to implement one of the two paths". An adapter written to that
        promise returned None from every submission, and None is not a
        TransportResult — every job would have read as an unrecognised answer.

        So an adapter implements EITHER path now, as intended: override this, or
        implement `create_order` and inherit this.

        `build_order` is the specification's job-to-task-list mapping (rev01
        §5), and it belongs here rather than in each adapter so that the
        deliver-and-collect single visit is expressed the same way everywhere.
        """
        response = self.create_order(
            build_order(job, rotate=getattr(job, "rotate", False)))
        return classify_error_code(response.errorCode)

    @abstractmethod
    def get_job_result(self, job_id) -> TransportResult:
        """Poll the outcome of a previously submitted job."""

    @abstractmethod
    def cancel_job(self, job_id) -> bool:
        """Ask for a job to be abandoned. Returns True if the ACS agreed.

        Needed by the timeout path: when the CSM gives up on a job it must
        also tell the ACS, or a robot keeps driving toward a job nobody is
        waiting for any more.
        """

    # -- the order interface -------------------------------------------------
    #
    # ADR 2026-08-18-acs-order-task-interface. These are what the real ACS
    # actually exposes; the three methods above are kept so that the existing
    # call sites and 193 tests keep working while call sites move over one at a
    # time. `submit_job` has a default implementation here that builds an order
    # and calls `create_order`, so an adapter only has to implement one of the
    # two paths.

    def create_order(self, order) -> SimpleResponse:
        """Submit an `AcsOrder` — an id and an ORDERED LIST OF TASKS.

        This is the schema's `createOrder`.

        ⚠ THERE IS NO FALLBACK HERE, and there cannot be one. This docstring
        used to claim it "falls back to the old single-move path, so existing
        adapters keep working unchanged" while the body raised — corrected
        2026-08-20. The claim was never implementable: `submit_job` takes a
        `Job`, this takes an `AcsOrder`, and an order cannot be turned back into
        the job that raised it. The fallback runs the other way round, and
        `submit_job` is where it lives.

        An adapter must therefore implement THIS or override `submit_job`.
        Implementing neither raises here rather than silently doing nothing.
        """
        raise NotImplementedError(
            f"{type(self).__name__} implements neither create_order nor "
            "submit_job; one of the two paths is required")

    def fleet_status(self):
        """What each robot is doing, for the PDA's AGV 상태 확인 screen.

        Read through, never retained: section 7 puts robot position and battery
        on the "not retained" list, and a copy here would be a second version
        of a fact the ACS already owns.

        Empty by default — an adapter that cannot say must not invent a fleet.
        """
        return []

    def order_state(self, order_id) -> TransportResult:
        """Where an order has got to.

        The real ACS offers a subscription carrying a monotonic sequence number
        and both old and new value, which is how gap detection stays free — see
        the schema notes above. Polling is the fallback, not the design.
        """
        return self.get_job_result(order_id)

    def cancel_order(self, order_id) -> SimpleResponse:
        """Withdraw an order. Distinct from abort — see `abort_order`."""
        ok = self.cancel_job(order_id)
        return SimpleResponse(0 if ok else 1)

    def abort_order(self, order_id) -> SimpleResponse:
        """Stop an order that is already running.

        ⚠ Takes NO drop-off location. The meeting notes said otherwise; the
        schema settles it — `AbortOrderInput` has id, requester, requesterDetail
        and comment, and nothing else. The ACS decides where the load goes. Do
        not add that parameter back.
        """
        raise NotImplementedError

    def pause_order(self, order_id) -> SimpleResponse:
        raise NotImplementedError

    def resume_order(self, order_id) -> SimpleResponse:
        raise NotImplementedError

    def make_order_fail(self, order_id) -> SimpleResponse:
        """Force an order to a failed terminal state."""
        raise NotImplementedError

    def make_order_success(self, order_id) -> SimpleResponse:
        """Force an order to a successful terminal state."""
        raise NotImplementedError
