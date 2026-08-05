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
from enum import Enum


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

    @abstractmethod
    def list_stations(self):
        """All station ids this adapter knows about."""


class TransportResult(Enum):
    """Outcome of a transport job, as reported by the ACS."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"      # invalid job — will never succeed, fail it
    BUSY = "busy"              # no robot free right now — retry later
    IN_PROGRESS = "in_progress"
    ARRIVED = "arrived"
    FAILED = "failed"
    UNKNOWN = "unknown"


class AcsAdapter(ABC):
    """The fleet controller: picks a robot and a route, then drives it there."""

    @abstractmethod
    def submit_job(self, job) -> TransportResult:
        """Hand a transport job over. Returns ACCEPTED or REJECTED."""

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
