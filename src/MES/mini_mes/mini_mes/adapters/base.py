"""Adapter interfaces - the boundary between the Mini MES and the outside world.

Everything the Mini MES talks to sits behind one of these. The main cycle and the
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

    Deliberately small. These are the only distinctions the Mini MES needs to
    decide whether transport work exists. A richer protocol should be collapsed
    into these by the adapter, not leaked upward.
    """

    IDLE = "idle"            # nothing loaded, nothing to collect
    BUSY = "busy"            # processing, do not disturb
    FINISHED = "finished"    # done — material is waiting for collection
    FAULT = "fault"          # broken; needs a human
    UNKNOWN = "unknown"      # unreachable or not answering


class EquipmentAdapter(ABC):
    """Production machines / process stations.

    Confirmed 2026-07-28 (Dr. Youngbo Shim): "Equipment" means production
    machines, not doors, lifts or conveyors.
    """

    @abstractmethod
    def get_station_status(self, station_id) -> StationStatus:
        """Current status of one station. Must not block for long — this is
        called from the main cycle."""

    @abstractmethod
    def send_station_command(self, station_id, command) -> bool:
        """Tell a station to do something. Returns True if accepted.

        ⚠ Whether the Mini MES is permitted to command equipment at all is not
        yet formally decided — Dr. Shim answered "I think b" on 2026-07-28,
        i.e. probably yes, not confirmed. If it stays permitted, the Mini MES can
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

        Needed by the timeout path: when the Mini MES gives up on a job it must
        also tell the ACS, or a robot keeps driving toward a job nobody is
        waiting for any more.
        """
