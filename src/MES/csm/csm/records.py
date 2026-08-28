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
from datetime import datetime, timedelta
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
    #: WE gave it back. Distinct from WITHDRAWN, which is the machine changing
    #: its mind: this is CSM having acknowledged a call, failed to serve it,
    #: and handed it back through the four-step cancellation. The two look the
    #: same in a count of unserved calls and mean opposite things about who
    #: failed.
    CANCELLED = "cancelled"


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
    #: When CSM gave the call back, having acknowledged it and failed to serve
    #: it. Kept beside `acknowledged_at` because the pair is the whole story:
    #: we promised at one time and withdrew the promise at another.
    cancelled_at: float = None
    job_id: str = None
    status: CallStatus = CallStatus.RAISED


class RackMode(Enum):
    """What CCS may do with a rack. CCS manual §2.2, the monitor screen icons.

    THE RACK IS A STATEFUL OBJECT, not a bucket with a capacity. Every
    selection rule in the manual asks about the rack before it asks about the
    material on it: §1.3 wants "at least three auto-mode non-abnormal racks in
    the loading area, at least one of them empty", and §1.2.1.1 rule 3 wants a
    buffer rack "with no abnormality". Neither question can be asked of a
    number.

    Only AUTO is fully in the automatic flow. The others each mean a different
    kind of "not now", and they are not interchangeable — a locked rack is
    working and deliberately held back, an abnormal one is broken, and an
    unavailable one is not there at all.
    """

    #: In the automatic flow. Everything else is an exclusion.
    AUTO = "auto"
    #: Operator handling only. A person may still put material here; CCS will
    #: not move it.
    MANUAL = "manual"
    #: Grey icon — "locked in CCS, no automatic transport" (§2.2).
    LOCKED = "locked"
    #: A fault. See `holds_material`: an abnormal rack counts as holding
    #: material even when it is empty.
    ABNORMAL = "abnormal"
    #: Yellow or red frame — "rack unavailable, CCS ignores it entirely".
    UNAVAILABLE = "unavailable"


class SlotStatus(Enum):
    """What one slot is doing. CCS manual §2.2, the rack tile.

    Separate from RackMode because they answer different questions: the mode is
    about the RACK's availability to CCS, the status is about the MATERIAL on
    one position. A perfectly healthy auto rack can hold a slot whose outbound
    failed.
    """

    EMPTY = "empty"
    #: Orange-red arrow — awaiting inbound. "If it persists, the material can
    #: never ship", so it is worth being able to name.
    AWAITING_INBOUND = "awaiting_inbound"
    #: 待出库 — stocked, inventory normal. The ordinary resting state.
    STOCKED = "stocked"
    #: 已出库 — posted to a winding line, waiting for an AGV task. Committed to
    #: a destination but not yet moving.
    POSTED_OUT = "posted_out"
    #: Yellow arrow — a task is executing on this slot.
    IN_TASK = "in_task"
    #: Red down arrow.
    INBOUND_FAILED = "inbound_failed"
    #: Red up arrow — "double-click for the reason".
    OUTBOUND_FAILED = "outbound_failed"


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

    #: What is on the slot, recorded ON THE RACK rather than only on the
    #: material. CCS manual §4.6.6: completing a task writes the material type,
    #: attribute, bobbin type and roll number INTO THE TARGET RACK. The task is
    #: the carrier of identity and delivery is what transfers it — so the rack
    #: has to have somewhere to put it.
    #:
    #: §1.3 then reads it back: a machine may not be fed if a rack in its
    #: loading area "already holds the required attribute", and a rack holding
    #: material must have "both type and attribute recorded". A rack that
    #: cannot answer those is excluded, which is why missing is None and not a
    #: default.
    material_type: str = None
    material_attribute: object = None     # MaterialAttribute, 1-4
    bobbin_type: int = None               # 360 / 430 / 500 / 580

    status: SlotStatus = SlotStatus.EMPTY

    @property
    def occupied(self):
        return self.material_ref is not None and self.retrieved_at is None

    @property
    def described(self):
        """Does this slot know what is on it? §1.3 asks before feeding.

        Empty is not the same as undescribed: an empty slot has nothing to
        describe, and a slot holding material with no recorded type or
        attribute is the case the manual excludes.
        """
        if not self.occupied:
            return True
        return self.material_type is not None and self.material_attribute is not None


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


#: THE CUSTOMER'S LOT ID FORMAT: yyyymmddhhmmssfff, to the millisecond.
#:
#: Theirs, not ours — the CSM scope slide states it exactly. It is a TIMESTAMP
#: used as an identifier, which has one consequence worth knowing: there is no
#: room in it for a counter, so two materials registered in the same
#: millisecond would collide. `InMemoryRecords` steps the timestamp forward
#: rather than allowing that; see `_next_lot_id`.
LOT_ID_FORMAT = "%Y%m%d%H%M%S"


def lot_id_for(moment):
    """Format one datetime as a LOT id."""
    return f"{moment.strftime(LOT_ID_FORMAT)}{moment.microsecond // 1000:03d}"


@dataclass
class Material:
    """A roll or a bobbin, as far as CSM needs to know it.

    THE IDENTIFIER AND ALMOST NOTHING ELSE. Width, weight, grade and coating
    spec belong to the customer's systems; section 7 is explicit that keeping a
    second copy is how mismatches arise. What is here is what CSM decides with:
    where the thing is, when it may be used, and how it got there.
    """

    material_ref: str
    lot_id: str
    kind: str = "roll"                 # roll | bobbin
    created_at: float = 0.0
    location: str = None

    #: When resting finishes and this may be fed into a machine. None means WE
    #: DO NOT KNOW — not "ready now". Which of those it turns out to be is
    #: customer open decision #6, "who owns curing elapsed time".
    ready_at: float = None

    #: WHEN THE CURING CLOCK STARTED, and how long it has to run. Recorded as
    #: a start plus a duration rather than a deadline, because [HB] §3 requires
    #: the ELAPSED time to survive a power cut and requires that material moved
    #: to another rack MUST NOT CURE TWICE. A deadline cannot express either:
    #: it has no memory of when it began, so a second placement recomputes it
    #: and the material rests twice.
    #:
    #: `ready_at` is kept beside these and stays the authority when it is set
    #: directly — somebody telling us a deadline outright is a different and
    #: equally valid input, and it is the one the PDA path already uses.
    cure_started_at: float = None
    cure_seconds: float = None

    #: When it expires, for FEFO. None means unknown, and unknown is not
    #: "never expires".
    expires_at: float = None

    #: A PERSON decided this expired material may be used after all. CCS
    #: manual §4.6.11: expired material "will not be posted automatically and
    #: needs a manual unlock". Held as who and when rather than a bare flag,
    #: because the manual makes it a decision somebody took and a decision
    #: with nobody's name on it is one nobody can be asked about.
    unlocked_by: str = None
    unlocked_at: float = None

    # -- what the routing rules read (see `csm/material.py`) ----------------
    #
    # NOT master data, which is why they are here despite the docstring above.
    # Width, weight and grade belong to the customer's systems and copying them
    # invites mismatch. These three are different: CATL's own dispatcher READS
    # them on every decision, and two independent sources agree on their values
    # — manual §4.6.5 and the rack PLC table `Rack_To_PCS[7]`/`[8]`.
    #
    # All default to None, and None means WE WERE NOT TOLD. `attribute_matches`
    # refuses on unknown rather than passing, because feeding a machine the
    # wrong face costs more than a deferred call.

    #: `material.MaterialAttribute` — bright/dark face x rotation.
    attribute: object = None

    #: 360 / 430 / 500 / 580. An INT in their table, so an unlisted value is
    #: possible; `material.pallet_capacity` derives the capacity from it and
    #: capacity is deliberately NOT stored beside it.
    drum_type: int = None

    #: Their model code — 302, 228, 125. Carried and never interpreted: we have
    #: no table for it, so reading meaning into it would be invention.
    material_type: int = None

    #: `material.MaterialState` — empty / NG / OK.
    state: object = None


@dataclass
class JobRecord:
    """One transport job, retained after it has finished.

    ⚠ NOT one of section 7's six records, and deliberately not a copy of the
    fleet controller's order history — section 7 puts that on the "not
    retained" list and it is theirs. Their record is about a VEHICLE CARRYING
    OUT AN ORDER. This one is about **why the work existed and whether it
    succeeded**: the call it answered, the material it moved, and the retry
    chain behind it. That is CSM's own knowledge and exists nowhere else.

    Added 2026-08-21. Before it, four tables carried a `job_id` and nothing
    could resolve one — a call, a decision and a movement all survived a
    restart while the job that connected them did not.

    `retry_of` is the field that earns its place. "Was this the third attempt?"
    was unanswerable after a restart, and it is exactly the question asked when
    a line under-performs.
    """

    job_id: str
    from_station: str = None
    to_station: str = None
    #: WHICH MACHINE of the four, at each end. The job id cannot say — the
    #: workshop deck's codes are per process, so GRV1_LD and GRV4_LD both read
    #: GRVPRTLD. These columns are where that is not lost.
    from_instance: int = None
    to_instance: int = None
    carries: str = None
    material_ref: str = None
    call_id: str = None
    #: The fleet controller's own reference. Equal to `job_id` today; kept
    #: separate because that is our choice, not their requirement.
    acs_order_id: str = None
    state: str = None
    priority: int = 0
    attempt: int = 1
    retry_of: str = None
    failure_reason: str = ""
    created_at: float = 0.0
    #: Set when the job reaches DONE or FAILED. None while it is still running,
    #: which is how an unfinished job is told from a finished one after a crash.
    finished_at: float = None


class LocationKind(Enum):
    """What sort of place a location is.

    `materials.location` was a free string that might name a machine port, a
    buffer rack or the store, and only the first had a table behind it. A
    reader joining materials to stations lost every roll in the ASRS without
    being told. This enum is what makes the three tellable apart.
    """

    PORT = "port"       # an LD or ULD station on a machine
    RACK = "rack"       # a WIP buffer shelf
    STORE = "store"     # the ASRS


@dataclass
class Location:
    """One place material can be. The dimension table the schema was missing.

    Added 2026-08-21. Deliberately thin: three columns, and no capacity or
    geometry. Where a location IS belongs to `plant.py`, which is the single
    source of truth for the plant; this table exists so that a location
    REFERENCE resolves, not to become a second plant model.
    """

    location: str
    kind: LocationKind
    #: Which leg works it — A, B or C. None for anything not on a leg.
    segment: str = None


@dataclass
class Abnormal:
    """A problem a person reported from the handheld.

    ⚠ NOT one of section 7's six records. It comes from the CSM scope slide
    (비정상 상황 보고), and it is kept because the PDA module's own note gives
    the reason: *a report that is only logged is a report nobody can count,
    chase or close.*

    Until 2026-08-21 it lived on the `Pda` object and was written nowhere, so
    a report did not survive a restart — which is the one thing a report has
    to do.
    """

    report_id: str
    station: str
    description: str
    reported_at: float
    reported_by: str = "PDA"
    acknowledged_at: float = None

    @property
    def open(self):
        return self.acknowledged_at is None


@dataclass
class MaterialMove:
    """One movement of one material. Section 7's traceability, in a row.

    `job_history` records what a JOB did. This records what a MATERIAL did, and
    they are not the same question: "where has this roll been" cannot be
    answered by reading job records, because a roll outlives the jobs that
    carried it.
    """

    material_ref: str
    seq: int
    at: float
    from_location: str = None
    to_location: str = None
    job_id: str = None
    note: str = ""


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
    def cancel_call(self, call_id, at):
        """Give an acknowledged call back. Distinct from it being withdrawn."""

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
    def register_material(self, kind="roll", at=0.0, location=None,
                          attribute=None, drum_type=None, material_type=None,
                          state=None):
        """Give a new roll or bobbin a LOT id. Returns the `Material`.

        THE FOUR OPTIONAL FIELDS ARE THE PDA SUPPLEMENT (§3.4). On the real
        line a person scans a rack and enters material type, attribute and
        bobbin type before the roll may be taken inbound — the manual says
        outright that supplement requires them non-empty and non-zero, because
        a zero there is what produces the "missing info" rack states.

        They default to None because a caller that does not know is honest;
        `material.attribute_matches` then refuses rather than guessing.
        """

    @abstractmethod
    def move_material(self, material_ref, to_location, at, job_id=None,
                      note=""):
        """Record that a material moved. Returns the `MaterialMove`."""

    @abstractmethod
    def locate(self, material_ref):
        """Where is it now, or None if we have never been told."""

    @abstractmethod
    def history_of(self, material_ref):
        """Every movement of this material, oldest first."""

    @abstractmethod
    def define_location(self, location, kind, segment=None):
        """Declare a place material can be. Idempotent."""

    @abstractmethod
    def location_kind(self, location):
        """`LocationKind` for a place, or None if it was never declared."""

    @abstractmethod
    def locations(self):
        """Every declared location."""

    @abstractmethod
    def add_abnormal(self, station, description, reported_by="PDA", at=0.0):
        """Record a problem a person reported. Returns the `Abnormal`."""

    @abstractmethod
    def open_reports(self):
        """Reports nobody has acknowledged yet."""

    @abstractmethod
    def acknowledge_report(self, report_id, at):
        """Close a report. Returns it, or None if there is no such report."""

    @abstractmethod
    def reports(self, limit=None):
        """Every report, newest first."""

    @abstractmethod
    def save_job(self, job, at=None, finished=False):
        """Record a job, or update the one already recorded.

        An UPSERT keyed on `job_id`, called at creation and on every state
        change. Not called per tick: the job tracker steps every job four times
        a second and writing that often would be all I/O and no information.
        """

    @abstractmethod
    def job(self, job_id):
        """One job by id, or None."""

    @abstractmethod
    def jobs(self, limit=None):
        """Jobs, newest first."""

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

    def __init__(self, rack_sizes=None, wall_clock=None):
        """
        :param rack_sizes: {rack name: how many slots}. The specification's
            capacities are WIPGP 2, WIPCTR 13, WIPSLT 30 and WIPCAL 28 — real
            numbers, and the reason a rack is slot-counted rather than a flag.
        :param wall_clock: callable() -> datetime, for LOT ids. Separate from
            the simulation clock ON PURPOSE: the sim clock is a monotonic float
            that starts near zero, and a LOT id is a real calendar timestamp
            the customer will read. A test injects a fixed one.
        """
        self._materials = {}
        self._moves = []
        self._issued_lots = set()
        self._wall_clock = wall_clock or datetime.now
        self._calls = {}
        self._decisions = []
        self._racks = {}
        self._stations = {}
        #: location name -> Location. Declared, not discovered: a location
        #: exists because somebody said so, which is what makes an undeclared
        #: one detectable.
        self._locations = {}
        #: report_id -> Abnormal, insertion ordered.
        self._reports = {}
        self._report_seq = itertools.count(1)
        #: job_id -> JobRecord. Insertion-ordered, so `jobs()` reverses it
        #: rather than sorting on a timestamp that is only monotonic within
        #: one run.
        self._jobs = {}
        self._call_seq = itertools.count(1)
        #: How many times a material was accepted without knowing whether it
        #: had rested. See `is_ready`.
        self.unrested_decisions = 0
        #: Rack mode by name. Separate from `_racks` so that the slot list
        #: stays a plain list and every existing reader of it keeps working.
        self._rack_modes = {}
        for rack, size in (rack_sizes or {}).items():
            self.define_rack(rack, size)

    def define_rack(self, rack, slots, mode=RackMode.AUTO):
        self._racks[rack] = [RackSlot(rack=rack, slot=i)
                             for i in range(1, slots + 1)]
        self._rack_modes[rack] = mode

    # -- rack mode: what CCS may do with a rack (manual §2.2) -------------

    def rack_mode(self, rack):
        """A rack nobody has declared is AUTO. Racks arrive from configuration
        already in service; a mode has to be set to take one OUT of service."""
        return self._rack_modes.get(rack, RackMode.AUTO)

    def set_rack_mode(self, rack, mode):
        self._rack_modes[rack] = mode
        return mode

    def rack_usable(self, rack):
        """May the AUTOMATIC flow use this rack at all?

        Only AUTO. Note this is NOT what `park` asks — a person putting
        material on a locked or manual rack is exactly what those modes are
        for. This is the question the selection rules ask, and nothing else.
        """
        return self.rack_mode(rack) is RackMode.AUTO

    def holds_material(self, rack):
        """Does this rack count as holding material, for the line's quota?

        AN ABNORMAL RACK COUNTS AS HOLDING MATERIAL EVEN WHEN IT IS EMPTY.
        CCS manual §2.15: it counts as one task. Fail-safe — a broken rack
        reduces the line's quota rather than being ignored, which is the
        opposite of what an optimiser would do and is the right way round.
        """
        if self.rack_mode(rack) is RackMode.ABNORMAL:
            return True
        return any(s.occupied for s in self._racks.get(rack, []))

    def racks_fit_to_feed(self, racks):
        """The §1.3 loading-area test, over the racks of one machine.

        ALL of these, and the manual states them together because any one of
        them alone would let a machine be fed wrongly:

          * at least three auto-mode, non-abnormal racks in the area
          * at least one of them empty
          * every rack holding material has its type AND attribute recorded
          * no rack in the area has a task running
          * no rack already holds the required attribute  <- the caller checks
            this one, because only it knows what is required

        Returns True if the area itself is fit. The attribute question needs
        the machine's configuration and is asked by the caller.
        """
        usable = [r for r in racks if self.rack_usable(r)]
        if len(usable) < 3:
            return False
        slots = [s for r in usable for s in self._racks.get(r, [])]
        if not any(not s.occupied for s in slots):
            return False
        if not all(s.described for s in slots):
            return False
        if any(s.status is SlotStatus.IN_TASK for s in slots):
            return False
        return True

    def holds_attribute(self, racks, attribute):
        """Does any of these racks already hold that attribute? §1.3."""
        return any(s.occupied and s.material_attribute == attribute
                   for r in racks for s in self._racks.get(r, []))

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

    def cancel_call(self, call_id, at):
        """We acknowledged this call and could not serve it. Section 7's C9."""
        call = self._calls.get(call_id)
        if call is None:
            return None
        call.status = CallStatus.CANCELLED
        call.cancelled_at = at
        return call

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

    def park(self, rack, material_ref, job_id, at,
             material_type=None, material_attribute=None, bobbin_type=None):
        """Put material on the first free slot, and RECORD WHAT IT IS.

        The three describing arguments are optional because the PDA path and
        the equipment monitor both existed before the rack could hold them, and
        a slot that does not know what it holds is a real state the manual has
        a rule for (§1.3 excludes it from feeding). Unknown is therefore
        modelled, not defaulted.

        Deliberately NOT gated on `rack_usable`: a person may put material on a
        locked or manual rack, and that is what those modes are for. The
        automatic flow asks `rack_usable` before it gets here.
        """
        for slot in self._racks.get(rack, []):
            if not slot.occupied:
                slot.material_ref = material_ref
                slot.parked_by_job = job_id
                slot.parked_at = at
                slot.retrieved_at = None
                slot.material_type = material_type
                slot.material_attribute = material_attribute
                slot.bobbin_type = bobbin_type
                slot.status = SlotStatus.STOCKED
                return slot
        return None                      # full — the caller decides what that means

    def describe_slot(self, rack, slot_no, material_type=None,
                      material_attribute=None, bobbin_type=None):
        """Write the carried identity into the rack. CCS manual §4.6.6.

        This is what task COMPLETION does: "write the task's carried
        information — material type, material attribute, bobbin type and roll
        number — into the TARGET rack". Separate from `park` because the two
        happen at different moments in the real system: the pallet is placed,
        and the task then reports complete.
        """
        for s in self._racks.get(rack, []):
            if s.slot == slot_no:
                if material_type is not None:
                    s.material_type = material_type
                if material_attribute is not None:
                    s.material_attribute = material_attribute
                if bobbin_type is not None:
                    s.bobbin_type = bobbin_type
                return s
        return None

    def set_slot_status(self, rack, slot_no, status):
        for s in self._racks.get(rack, []):
            if s.slot == slot_no:
                s.status = status
                return s
        return None

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
        # The slot is empty again, and an empty slot describes nothing. Leaving
        # the old type and attribute behind would make `holds_attribute` answer
        # about material that has gone.
        oldest.material_type = None
        oldest.material_attribute = None
        oldest.bobbin_type = None
        oldest.status = SlotStatus.EMPTY
        return oldest

    def slots(self, rack):
        return list(self._racks.get(rack, []))

    def free_slots(self, rack):
        return [s for s in self._racks.get(rack, []) if not s.occupied]

    def is_full(self, rack):
        return rack in self._racks and not self.free_slots(rack)

    # -- materials, LOT ids and where things are -------------------------

    def _next_lot_id(self):
        """A LOT id nobody else has.

        The customer's format is a millisecond timestamp with no counter in it,
        so two registrations inside one millisecond would produce the same id.
        Rather than allow a duplicate — a LOT id is how their systems will
        refer to this material — the timestamp is stepped forward until it is
        free. The id stays the right shape and stays unique; the cost is that
        it can be up to a few milliseconds later than the true moment.
        """
        moment = self._wall_clock()
        candidate = lot_id_for(moment)
        while candidate in self._issued_lots:
            moment = moment + timedelta(milliseconds=1)
            candidate = lot_id_for(moment)
        self._issued_lots.add(candidate)
        return candidate

    def register_material(self, kind="roll", at=0.0, location=None,
                          attribute=None, drum_type=None, material_type=None,
                          state=None):
        lot = self._next_lot_id()
        material = Material(material_ref=lot, lot_id=lot, kind=kind,
                            created_at=at, location=location,
                            attribute=attribute, drum_type=drum_type,
                            material_type=material_type, state=state)
        self._materials[lot] = material
        if location is not None:
            self._record_move(lot, None, location, at, note="registered")
        return material

    def material(self, material_ref):
        return self._materials.get(material_ref)

    def materials(self):
        """Every material we hold, in registration order.

        The daily check needs to sweep them — §6 items 5-8 are all "find the
        ones that look wrong" — and asking by reference cannot answer a
        question whose whole point is that you do not know which one."""
        return list(self._materials.values())

    def _record_move(self, material_ref, frm, to, at, job_id=None, note=""):
        move = MaterialMove(
            material_ref=material_ref,
            seq=len(self.history_of(material_ref)) + 1,
            at=at, from_location=frm, to_location=to,
            job_id=job_id, note=note)
        self._moves.append(move)
        return move

    def move_material(self, material_ref, to_location, at, job_id=None,
                      note=""):
        material = self._materials.get(material_ref)
        if material is None:
            return None
        move = self._record_move(material_ref, material.location, to_location,
                                 at, job_id, note)
        material.location = to_location
        return move

    def locate(self, material_ref):
        material = self._materials.get(material_ref)
        return material.location if material else None

    def history_of(self, material_ref):
        return [m for m in self._moves if m.material_ref == material_ref]

    def materials_at(self, location):
        return [m for m in self._materials.values() if m.location == location]

    # -- resting, and being honest about not knowing ---------------------

    def set_ready_at(self, material_ref, when):
        """Record when this material finishes resting, if we are told."""
        material = self._materials.get(material_ref)
        if material is not None:
            material.ready_at = when
        return material

    def begin_curing(self, material_ref, at, seconds):
        """Start the curing clock. IDEMPOTENT, and that is the whole point.

        [HB] §3: "If the destination rack is full, the item is routed elsewhere
        and cures there — and MUST NOT CURE TWICE." So the second call does not
        restart the clock; it returns the material with the original start
        intact. Getting this wrong costs six hours per affected roll, silently,
        and only shows up as a line that is mysteriously slow.

        A duration of 0 or None starts nothing: those mean "this process does
        not cure" and "we were not told", and neither is a reason to hold
        material. `curing.CuringPolicy` is where that distinction lives.
        """
        material = self._materials.get(material_ref)
        if material is None or not seconds:
            return material
        if material.cure_started_at is not None:
            return material               # already curing — do not restart it
        material.cure_started_at = at
        material.cure_seconds = seconds
        return material

    def cure_remaining(self, material_ref, now):
        """Seconds still to rest. 0 when done, None when not curing at all."""
        material = self._materials.get(material_ref)
        if material is None or material.cure_started_at is None:
            return None
        done_at = material.cure_started_at + (material.cure_seconds or 0.0)
        return max(0.0, done_at - now)

    def is_ready(self, material_ref, now):
        """May this be fed into a machine yet?

        ⚠ UNKNOWN COUNTS AS READY, and that is a decision, not an oversight.

        The specification selects "the oldest matching material that has
        finished resting" (A2) while section 7 says resting state is not
        retained — so unless somebody tells us, we cannot apply the rule. The
        two available answers are both wrong in different ways: refusing
        material we know nothing about stops the line, and accepting it may
        feed a machine something that has not cured.

        Accepting is chosen because the line stopping is the louder failure and
        because nothing today tells us otherwise — and `unrested_decisions`
        counts how often we did it blind, so the size of the exposure is
        visible rather than assumed. Customer open decision #6 settles it.
        """
        material = self._materials.get(material_ref)
        if material is None:
            return False
        # A RUNNING CLOCK IS THE BEST ANSWER WE HAVE, so it is asked first.
        # This is knowledge, not a guess, and it must not be overridden by a
        # `ready_at` somebody set earlier from a weaker source.
        if material.cure_started_at is not None:
            return self.cure_remaining(material_ref, now) <= 0.0
        if material.ready_at is None:
            self.unrested_decisions += 1
            return True
        return now >= material.ready_at

    def is_expired(self, material_ref, now):
        """Past its own expiry, and nobody has unlocked it. §4.6.11.

        Unknown expiry is NOT expired. The same reasoning as `is_ready`'s
        unknown-counts-as-ready: refusing material nobody has given us a
        lifetime for would stop a line on our own assumption. Where `is_ready`
        counts its blind decisions, this one has nothing to count — there is
        no exposure in declining to expire something.
        """
        material = self._materials.get(material_ref)
        if material is None or material.expires_at is None:
            return False
        if material.unlocked_by is not None:
            return False
        return now >= material.expires_at

    def unlock_expired(self, material_ref, by, at):
        """A person allows expired material to be used. §4.6.11.

        Takes who and when because the manual makes this a human decision, and
        a decision with nobody's name on it is one nobody can be asked about.
        """
        material = self._materials.get(material_ref)
        if material is None:
            return None
        material.unlocked_by = by
        material.unlocked_at = at
        return material

    def ready_materials(self, location, now):
        """What is at this place and may be used, oldest first — FIFO.

        Two gates, and they are opposite ends of the same axis: `is_ready` is
        a MINIMUM age (curing, §4.6.12) and `is_expired` a MAXIMUM (§4.6.11).
        Material must have rested long enough and not sat too long.
        """
        here = [m for m in self.materials_at(location)
                if self.is_ready(m.material_ref, now)
                and not self.is_expired(m.material_ref, now)]
        return sorted(here, key=lambda m: m.created_at)

    def expiring_first(self, location, now):
        """FEFO: earliest expiry first, then oldest.

        ⚠ Materials with no expiry sort LAST, not first. We are not told
        expiries by anything today, so in practice this degrades to FIFO — and
        it should, rather than inventing an order out of missing data.
        """
        here = [m for m in self.materials_at(location)
                if self.is_ready(m.material_ref, now)
                and not self.is_expired(m.material_ref, now)]
        return sorted(here, key=lambda m: (m.expires_at is None,
                                           m.expires_at or 0.0,
                                           m.created_at))

    # -- locations --------------------------------------------------------

    def define_location(self, location, kind, segment=None):
        entry = Location(location=location,
                         kind=kind if isinstance(kind, LocationKind)
                         else LocationKind(kind),
                         segment=segment)
        self._locations[location] = entry
        return entry

    def location_kind(self, location):
        entry = self._locations.get(location)
        return entry.kind if entry else None

    def locations(self):
        return list(self._locations.values())

    # -- abnormal reports --------------------------------------------------

    def add_abnormal(self, station, description, reported_by="PDA", at=0.0):
        report = Abnormal(
            report_id=f"abn_{next(self._report_seq):04d}",
            station=station,
            description=description,
            reported_at=at,
            reported_by=reported_by,
        )
        self._reports[report.report_id] = report
        return report

    def open_reports(self):
        return [r for r in self._reports.values() if r.open]

    def acknowledge_report(self, report_id, at):
        report = self._reports.get(report_id)
        if report is not None:
            report.acknowledged_at = at
        return report

    def reports(self, limit=None):
        out = list(reversed(self._reports.values()))
        return out[:limit] if limit else out

    # -- jobs -------------------------------------------------------------

    def save_job(self, job, at=None, finished=False):
        """Upsert. `finished` stamps `finished_at`; it is not inferred here.

        Inferring it from the state name would put knowledge of which states
        are terminal in two places — the FSM already owns that, and the caller
        knows.
        """
        record = JobRecord(
            job_id=job.job_id,
            from_station=job.from_station,
            to_station=job.to_station,
            from_instance=getattr(job, "from_instance", None),
            to_instance=getattr(job, "to_instance", None),
            carries=getattr(getattr(job, "carries", None), "value", None),
            material_ref=getattr(job, "material_ref", None),
            call_id=getattr(job, "call_id", None),
            acs_order_id=getattr(job, "acs_order_id", None) or job.job_id,
            state=getattr(job, "state_name", None),
            priority=getattr(job, "priority", 0) or 0,
            attempt=getattr(job, "attempt", 1) or 1,
            retry_of=getattr(job, "retry_of", None),
            failure_reason=getattr(job, "failure_reason", "") or "",
            created_at=getattr(job, "created_at", 0.0) or 0.0,
        )
        # Keep a finish time already recorded: a later update must not erase
        # when the job ended.
        previous = self._jobs.get(job.job_id)
        if finished:
            record.finished_at = at
        elif previous is not None:
            record.finished_at = previous.finished_at
        self._jobs[job.job_id] = record
        return record

    def job(self, job_id):
        return self._jobs.get(job_id)

    def jobs(self, limit=None):
        out = list(reversed(self._jobs.values()))
        return out[:limit] if limit else out

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
