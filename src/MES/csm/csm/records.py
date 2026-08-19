"""What CSM retains — the six records of the specification, section 7.

DELIBERATELY SMALL. The specification is explicit about why: "For anything the
customer's systems own we keep the identifier and read the rest — two copies of
one fact is how rack/inventory mismatches arise."

So these hold OUR decisions and OUR bookkeeping. They do not hold inventory,
roll master data, robot position, battery, routes or ACS order history; those
belong to systems that already own them, and copying them here would create a
second version of the truth that can drift.

WHY THIS IS AN INTERFACE AND NOT A DATABASE
===========================================

Four customer answers are missing before an engine can be chosen:

  * who owns curing elapsed time, the server or the rack PLC — the project
    handbook's own note says this "blocks persistence design";
  * one CSM instance or six, which decides whether a process-local store is
    possible at all;
  * the implementation language, which waits on the ACS server's OS;
  * the engine itself. No new server is being provided — an existing one is
    reused — and MongoDB was ruled out in the 2026-08-14 meeting. The CCS
    review still lists the engine as unknown.

Picking one today would be inventing four customer answers at once. So the
shape is settled here and the storage is not: `Records` is the port,
`InMemoryRecords` is the implementation the simulator and the tests use, and a
durable one arrives later behind the same interface. That is the same move
`EquipmentAdapter` and `AcsAdapter` already make.

⚠ NOTHING HERE SURVIVES A RESTART YET. The handbook lists that as a known gap
and it remains one.
"""

import itertools
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


def instance_of(station_id):
    """Which of the four machines this port belongs to, or None.

    Specification assumption A3: job names stay generic and the RECORD carries
    the instance. "Two coaters requesting material therefore produce two
    distinguishable jobs" — the job name alone cannot tell them apart.

    Derived from the first run of digits rather than a position, because the
    plant's own names do not agree on where the number goes:

        GRV1_LD     the family, then the instance, then the port
        SLT_LD1     the port, then the instance
        WIP_CTR_2   the family, then the instance
        ASRS        no instance at all — there is one store

    A positional rule would be right for one of those and quietly wrong for the
    others.
    """
    if not station_id:
        return None
    found = re.search(r"\d+", station_id)
    return int(found.group()) if found else None


class CallStatus(Enum):
    """Where a transport request has got to."""

    RAISED = "raised"
    #: We told the machine we heard it. It stops asking at this point, so the
    #: transition is worth recording rather than inferring from a job existing.
    ACKNOWLEDGED = "acknowledged"
    SERVED = "served"
    #: Went away before we could serve it — an operator cancelling at the
    #: panel, or the machine alarming out.
    WITHDRAWN = "withdrawn"


@dataclass
class Call:
    """A request for transport. Section 7's `call` record.

    Kept separate from the job it produced because the two are not the same
    thing and do not always both exist: a call that nothing can serve yet has
    no job, and a job CSM originates itself — the WIP diversion — has no call.
    """

    call_id: str
    station: str
    instance: int
    task_type: object                 # TaskType; not imported, to stay leaf
    source: str                       # "equipment" or "PDA"
    raised_at: float
    acknowledged_at: float = None
    job_id: str = None
    status: CallStatus = CallStatus.RAISED


@dataclass
class RackSlot:
    """One position on a WIP rack. Section 7's `rack_slot` record.

    THE RACK IS WHERE IDENTITY LIVES. The ACS team described their own model in
    the 2026-08-14 meeting: carrier identity vanishes at an equipment station
    but persists at the buffer — "내려놓으면 좀 사라지고 있거든요… 버퍼 같은
    경우도 내려놓으면 저희 시스템에 가만히 있어요". So a machine port is not
    modelled this way and a rack slot is.

    `material_ref` is an identifier, not a copy of the material's data. Which
    is the whole retention rule in one field.
    """

    rack: str
    slot: int
    material_ref: str = None
    parked_by_job: str = None
    parked_at: float = None
    retrieved_at: float = None

    @property
    def occupied(self):
        return self.material_ref is not None and self.retrieved_at is None


@dataclass
class Decision:
    """Why CSM chose what it chose. Section 7's `decision` record.

    The only record that exists purely to be read by a person. When a job goes
    to the wrong machine the question is always "why that one", and without
    this the answer has to be reconstructed from logs that have since rotated.
    """

    job_id: str
    decided_at: float
    chosen_source: str = None
    chosen_dest: str = None
    priority_given: int = 0
    reason: str = ""


@dataclass
class StationMap:
    """Our name for a port beside the customer's. Section 7's `station_map`.

    The customer's identity is `MC_Num` — `1A01`, being polarity, equipment
    type and sequence. Ours is `GRV1_LD`. Both are needed: theirs is what goes
    on the wire, ours is what the plant model and every road is written in.
    """

    our_name: str
    instance: int
    customer_port_id: str = None


class Records(ABC):
    """The port. Storage is deliberately not decided here — see the module note."""

    @abstractmethod
    def add_call(self, station, task_type, source, raised_at, instance=None):
        """Record a request. Returns the `Call`."""

    @abstractmethod
    def acknowledge_call(self, call_id, at, job_id=None):
        """Mark a call heard. The machine stops asking at this point."""

    @abstractmethod
    def open_calls(self):
        """Calls raised and not yet acknowledged."""

    @abstractmethod
    def add_decision(self, decision):
        """Record why a job went where it did."""

    @abstractmethod
    def decisions_for(self, job_id):
        """Every decision recorded against a job, oldest first."""

    @abstractmethod
    def park(self, rack, material_ref, job_id, at):
        """Take the first free slot on a rack. Returns it, or None if full."""

    @abstractmethod
    def retrieve(self, rack, at, material_ref=None):
        """Free a slot. Oldest first, which is FIFO by construction."""

    @abstractmethod
    def slots(self, rack):
        """Every slot on a rack, in order."""

    @abstractmethod
    def map_station(self, our_name, customer_port_id):
        """Bind our name for a port to the customer's."""

    @abstractmethod
    def customer_id(self, our_name):
        """Their id for this port, or None if we have not been told."""


class InMemoryRecords(Records):
    """The implementation the simulator and the tests run on.

    ⚠ Lost on restart. That is the known gap, not an oversight — see the
    module note on why the engine is not chosen yet.
    """

    def __init__(self, rack_sizes=None):
        """
        :param rack_sizes: {rack name: how many slots}. The specification's
            capacities are WIPGP 2, WIPCTR 13, WIPSLT 30 and WIPCAL 28 — real
            numbers, and the reason a rack is slot-counted rather than a flag.
        """
        self._calls = {}
        self._decisions = []
        self._racks = {}
        self._stations = {}
        self._call_seq = itertools.count(1)
        for rack, size in (rack_sizes or {}).items():
            self.define_rack(rack, size)

    def define_rack(self, rack, slots):
        self._racks[rack] = [RackSlot(rack=rack, slot=i)
                             for i in range(1, slots + 1)]

    # -- calls -----------------------------------------------------------

    def add_call(self, station, task_type, source, raised_at, instance=None):
        call = Call(
            call_id=f"call_{next(self._call_seq):04d}",
            station=station,
            instance=instance if instance is not None else instance_of(station),
            task_type=task_type,
            source=source,
            raised_at=raised_at,
        )
        self._calls[call.call_id] = call
        return call

    def acknowledge_call(self, call_id, at, job_id=None):
        call = self._calls.get(call_id)
        if call is None:
            return None
        call.acknowledged_at = at
        call.job_id = job_id
        call.status = CallStatus.ACKNOWLEDGED
        return call

    def open_calls(self):
        return [c for c in self._calls.values()
                if c.status is CallStatus.RAISED]

    def call(self, call_id):
        return self._calls.get(call_id)

    def calls_for(self, station):
        return [c for c in self._calls.values() if c.station == station]

    # -- decisions -------------------------------------------------------

    def add_decision(self, decision):
        self._decisions.append(decision)
        return decision

    def decisions_for(self, job_id):
        return [d for d in self._decisions if d.job_id == job_id]

    # -- rack slots ------------------------------------------------------

    def park(self, rack, material_ref, job_id, at):
        for slot in self._racks.get(rack, []):
            if not slot.occupied:
                slot.material_ref = material_ref
                slot.parked_by_job = job_id
                slot.parked_at = at
                slot.retrieved_at = None
                return slot
        return None                      # full — the caller decides what that means

    def retrieve(self, rack, at, material_ref=None):
        """Oldest parked first, so FIFO falls out of the ordering.

        FEFO is not this method's business — it needs an expiry we are not
        given and have not been told who owns.
        """
        candidates = [s for s in self._racks.get(rack, []) if s.occupied
                      and (material_ref is None or s.material_ref == material_ref)]
        if not candidates:
            return None
        oldest = min(candidates, key=lambda s: s.parked_at)
        oldest.retrieved_at = at
        return oldest

    def slots(self, rack):
        return list(self._racks.get(rack, []))

    def free_slots(self, rack):
        return [s for s in self._racks.get(rack, []) if not s.occupied]

    def is_full(self, rack):
        return rack in self._racks and not self.free_slots(rack)

    # -- station map -----------------------------------------------------

    def map_station(self, our_name, customer_port_id):
        entry = StationMap(our_name=our_name,
                           instance=instance_of(our_name),
                           customer_port_id=customer_port_id)
        self._stations[our_name] = entry
        return entry

    def customer_id(self, our_name):
        entry = self._stations.get(our_name)
        return entry.customer_port_id if entry else None

    def station_map(self):
        return dict(self._stations)
