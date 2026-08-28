"""The durable half of section 7's records — SQLite behind the same port.

WHY SQLITE, GIVEN THE ENGINE IS STILL UNANSWERED
================================================
`records.py` lists four customer answers missing before an engine can be
chosen, and they are still missing. This does not pretend to settle them. It
settles a smaller question — whether CSM survives a restart — with the choice
that costs least if the answers arrive differently:

  * one file, no server, and nobody has agreed to provide a server;
  * the schema is six small tables of plain SQL, so if the answer to "one CSM
    instance or six" turns out to be six, the same statements move to
    PostgreSQL rather than being rewritten;
  * MongoDB was ruled out in the 2026-08-14 meeting, so the document shape was
    never available anyway.

If the customer names a different engine, what is thrown away is this file. The
`Records` port and everything above it are untouched — which is the whole point
of there being a port.

WHY THIS SUBCLASSES RATHER THAN REIMPLEMENTS
============================================
A second implementation would mean a second copy of the rules that are NOT
obvious: FIFO falling out of `parked_at` ordering, unknown-resting counting as
ready and being counted while it does, LOT ids stepping forward to stay unique,
materials with no expiry sorting LAST under FEFO. Every one of those is a
decision with a reason recorded beside it, and expressing them again in SQL
creates two versions that can disagree — silently, because both would look
right in isolation.

So the working set stays in memory, where it is already correct and already
tested, and every MUTATION is written through to the database as it happens.
On startup the tables are read back. What SQLite provides here is durability,
which is the thing actually missing; it is not being asked to provide query
semantics.

The cost is honest and worth stating: the whole record set lives in memory, so
this does not scale past what one process can hold. For six records that are
deliberately small — the specification keeps identifiers and reads the rest —
that is a shift's worth of rows, not a warehouse.

⚠ EVERY MUTATING METHOD MUST BE OVERRIDDEN HERE. A new one added to
`InMemoryRecords` and not mirrored would work perfectly and persist nothing,
and the loss would only appear after a restart. `test_records_sqlite.py` walks
the base class and fails if one is missed, because a human reviewer will not.
"""

import sqlite3

from .adapters.base import TaskType
from .material import MaterialAttribute, MaterialState
from .records import (Abnormal, Call, CallStatus, Decision, InMemoryRecords,
                      RackMode, SlotStatus,
                      JobRecord, Location, LocationKind, Material,
                      MaterialMove, RackSlot, StationMap)

def _attribute_from(text):
    """A material attribute read back from the database.

    Stored by NAME rather than by value, because the name is what a human
    reading the file needs and the value is an integer that means nothing on
    its own. Unknown names come back as the raw text rather than raising: a
    store that refuses to open because of one unrecognised row is worse than
    one that hands back what it found.
    """
    from .material import MaterialAttribute
    try:
        return MaterialAttribute[text]
    except KeyError:
        return text


SCHEMA = """
CREATE TABLE IF NOT EXISTS racks (
    rack        TEXT PRIMARY KEY,
    slot_count  INTEGER NOT NULL,
    mode        TEXT
);
CREATE TABLE IF NOT EXISTS calls (
    call_id         TEXT PRIMARY KEY,
    station         TEXT NOT NULL,
    instance        INTEGER,
    task_type       TEXT,
    source          TEXT,
    raised_at       REAL,
    acknowledged_at REAL,
    cancelled_at    REAL,
    job_id          TEXT,
    status          TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    seq            INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id         TEXT NOT NULL,
    decided_at     REAL,
    chosen_source  TEXT,
    chosen_dest    TEXT,
    priority_given INTEGER,
    reason         TEXT
);
CREATE TABLE IF NOT EXISTS rack_slots (
    rack               TEXT NOT NULL,
    slot               INTEGER NOT NULL,
    material_ref       TEXT,
    parked_by_job      TEXT,
    parked_at          REAL,
    retrieved_at       REAL,
    material_type      TEXT,
    material_attribute TEXT,
    bobbin_type        INTEGER,
    status             TEXT,
    PRIMARY KEY (rack, slot)
);
CREATE TABLE IF NOT EXISTS materials (
    material_ref TEXT PRIMARY KEY,
    lot_id       TEXT NOT NULL,
    kind         TEXT,
    created_at   REAL,
    location     TEXT,
    ready_at     REAL,
    expires_at   REAL,
    attribute     TEXT,
    drum_type     INTEGER,
    material_type INTEGER,
    state         TEXT,
    cure_started_at REAL,
    cure_seconds    REAL
);
CREATE TABLE IF NOT EXISTS material_moves (
    material_ref  TEXT NOT NULL,
    seq           INTEGER NOT NULL,
    at            REAL,
    from_location TEXT,
    to_location   TEXT,
    job_id        TEXT,
    note          TEXT,
    PRIMARY KEY (material_ref, seq)
);
CREATE TABLE IF NOT EXISTS stations (
    our_name         TEXT PRIMARY KEY,
    instance         INTEGER,
    customer_port_id TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
    job_id         TEXT PRIMARY KEY,
    from_station   TEXT,
    to_station     TEXT,
    from_instance  INTEGER,
    to_instance    INTEGER,
    carries        TEXT,
    material_ref   TEXT,
    call_id        TEXT,
    acs_order_id   TEXT,
    state          TEXT,
    priority       INTEGER,
    attempt        INTEGER,
    retry_of       TEXT,
    failure_reason TEXT,
    created_at     REAL,
    finished_at    REAL
);
CREATE TABLE IF NOT EXISTS locations (
    location TEXT PRIMARY KEY,
    kind     TEXT NOT NULL,
    segment  TEXT
);
CREATE TABLE IF NOT EXISTS abnormal_reports (
    report_id       TEXT PRIMARY KEY,
    station         TEXT,
    description     TEXT NOT NULL,
    reported_by     TEXT,
    reported_at     REAL,
    acknowledged_at REAL
);
CREATE INDEX IF NOT EXISTS ix_reports_open ON abnormal_reports (acknowledged_at);
CREATE INDEX IF NOT EXISTS ix_jobs_state    ON jobs (state);
CREATE INDEX IF NOT EXISTS ix_jobs_retry    ON jobs (retry_of);
CREATE INDEX IF NOT EXISTS ix_decisions_job ON decisions (job_id);
CREATE INDEX IF NOT EXISTS ix_moves_ref     ON material_moves (material_ref);
CREATE INDEX IF NOT EXISTS ix_calls_station ON calls (station);
"""


def _task_type(name):
    """The stored name back as a `TaskType`, or the raw string if unknown.

    `records.py` does not import `TaskType` — it stays leaf on purpose — so the
    enum is resolved HERE, where a storage module is already allowed to know
    about the protocol. Storing the name rather than the number means a
    renumbered enum does not silently reinterpret old rows.

    An unrecognised name is returned as the string rather than raising: a row
    written by a newer version must not stop this one from starting, and a
    value that reads back oddly is easier to diagnose than a store that will
    not open.
    """
    if name is None:
        return None
    try:
        return TaskType[name]
    except KeyError:
        return name


#: Columns added after the first release, per table. `CREATE TABLE IF NOT
#: EXISTS` does nothing to a table that already exists, so a database written
#: by an earlier version keeps its old shape and every new field is silently
#: dropped on save and comes back None on load — the exact quiet data loss this
#: store exists to prevent.
#:
#: Additive only. SQLite can ADD COLUMN cheaply and cannot drop or retype one,
#: so anything beyond an addition is a real migration and does not belong here.
LATE_COLUMNS = {
    "materials": (
        ("attribute", "TEXT"),          # MaterialAttribute, by NAME
        ("drum_type", "INTEGER"),
        ("material_type", "INTEGER"),
        ("state", "TEXT"),              # MaterialState, by NAME
        # The curing clock. A start plus a duration rather than a deadline,
        # because [HB] §3 needs the ELAPSED time to survive a power cut — and
        # surviving is exactly what this table is for.
        ("cure_started_at", "REAL"),
        ("cure_seconds", "REAL"),
    ),
    "racks": (
        # RackMode, by value. An old database comes back with mode NULL, which
        # `_load` reads as "not set" and leaves at AUTO — the same answer a
        # rack that has never been touched gives, and the right one.
        ("mode", "TEXT"),
    ),
    "rack_slots": (
        # What the rack knows about what it holds — CCS manual §4.6.6's
        # identity transfer, and what §1.3 reads back before feeding.
        ("material_type", "TEXT"),
        ("material_attribute", "TEXT"),
        ("bobbin_type", "INTEGER"),
        ("status", "TEXT"),
    ),
}


def _add_missing_columns(db):
    """Bring an existing database up to the current schema. Idempotent."""
    for table, columns in LATE_COLUMNS.items():
        have = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
        for name, sql_type in columns:
            if name not in have:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")


def _enum_by_name(enum_class, name):
    """Stored name back to a member, or the raw value if we do not know it.

    Same contract and same reasoning as `_task_type`: a row written by a newer
    version must not stop this one from starting, and storing the NAME means
    renumbering our enum cannot silently reinterpret old rows. For the material
    attribute the numbers are the customer's and fixed, but the convention is
    worth more than the exception.
    """
    if name is None:
        return None
    try:
        return enum_class[name]
    except KeyError:
        return name


def _enum_name(value):
    """A member's name for storage; passes through anything else."""
    return value.name if hasattr(value, "name") else value


class SqliteRecords(InMemoryRecords):
    """Section 7's records, surviving a restart.

    :param path: the database file. `":memory:"` gives a private one, which is
        what most tests want — it exercises every SQL statement while leaving
        nothing behind.
    """

    def __init__(self, path, rack_sizes=None, wall_clock=None):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        _add_missing_columns(self.db)
        # WAL so a reader — the director's view — never blocks the CSM writing.
        # Refused on :memory: and on some network filesystems, and a refusal is
        # not a reason to fail to start.
        try:
            self.db.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass

        # The base constructor calls define_rack, which writes. So the
        # connection has to exist before this runs.
        super().__init__(rack_sizes=rack_sizes, wall_clock=wall_clock)
        self._load()

    # ------------------------------------------------------------- loading

    def _load(self):
        """Read the tables back into the working set.

        Racks declared in the FILE win over racks passed to the constructor: a
        rack that was resized in configuration must not silently drop the slot
        a material is still parked in. A genuine resize is a migration, and it
        should look like one.
        """
        for row in self.db.execute("SELECT * FROM racks"):
            existing = self._racks.get(row["rack"])
            if row["mode"]:
                self._rack_modes[row["rack"]] = RackMode(row["mode"])
            if existing is None or len(existing) != row["slot_count"]:
                self._racks[row["rack"]] = [
                    RackSlot(rack=row["rack"], slot=i)
                    for i in range(1, row["slot_count"] + 1)]

        for row in self.db.execute("SELECT * FROM rack_slots"):
            slots = self._racks.get(row["rack"])
            if slots is None or row["slot"] > len(slots):
                continue                 # a rack that no longer has this slot
            slot = slots[row["slot"] - 1]
            slot.material_ref = row["material_ref"]
            slot.parked_by_job = row["parked_by_job"]
            slot.parked_at = row["parked_at"]
            slot.retrieved_at = row["retrieved_at"]
            slot.material_type = row["material_type"]
            slot.bobbin_type = row["bobbin_type"]
            if row["material_attribute"] is not None:
                slot.material_attribute = _attribute_from(
                    row["material_attribute"])
            if row["status"]:
                slot.status = SlotStatus(row["status"])

        for row in self.db.execute("SELECT * FROM calls"):
            self._calls[row["call_id"]] = Call(
                call_id=row["call_id"], station=row["station"],
                instance=row["instance"],
                task_type=_task_type(row["task_type"]),
                source=row["source"], raised_at=row["raised_at"],
                acknowledged_at=row["acknowledged_at"],
                cancelled_at=row["cancelled_at"], job_id=row["job_id"],
                status=CallStatus(row["status"]))
        # Carry on numbering where the last run stopped. Reusing call_0001
        # would overwrite a served call with a new one and lose both.
        self._resume_call_numbering()

        for row in self.db.execute("SELECT * FROM decisions ORDER BY seq"):
            self._decisions.append(Decision(
                job_id=row["job_id"], decided_at=row["decided_at"],
                chosen_source=row["chosen_source"],
                chosen_dest=row["chosen_dest"],
                priority_given=row["priority_given"], reason=row["reason"]))

        for row in self.db.execute("SELECT * FROM materials"):
            self._materials[row["material_ref"]] = Material(
                material_ref=row["material_ref"], lot_id=row["lot_id"],
                kind=row["kind"], created_at=row["created_at"],
                location=row["location"], ready_at=row["ready_at"],
                cure_started_at=row["cure_started_at"],
                cure_seconds=row["cure_seconds"],
                expires_at=row["expires_at"],
                attribute=_enum_by_name(MaterialAttribute, row["attribute"]),
                drum_type=row["drum_type"],
                material_type=row["material_type"],
                state=_enum_by_name(MaterialState, row["state"]))
            # Every LOT id ever issued, so a restart inside the same
            # millisecond cannot hand out one that already exists.
            self._issued_lots.add(row["lot_id"])

        for row in self.db.execute(
                "SELECT * FROM material_moves ORDER BY material_ref, seq"):
            self._moves.append(MaterialMove(
                material_ref=row["material_ref"], seq=row["seq"],
                at=row["at"], from_location=row["from_location"],
                to_location=row["to_location"], job_id=row["job_id"],
                note=row["note"] or ""))

        # Jobs, oldest first so the dict keeps insertion order and `jobs()`
        # can simply reverse it. THIS IS THE WHOLE POINT OF THE TABLE: after a
        # restart the calls, decisions and movements can resolve the job id
        # they carry, instead of pointing at something nothing can explain.
        for row in self.db.execute(
                "SELECT * FROM jobs ORDER BY rowid"):
            self._jobs[row["job_id"]] = JobRecord(
                job_id=row["job_id"],
                from_station=row["from_station"],
                to_station=row["to_station"],
                from_instance=row["from_instance"],
                to_instance=row["to_instance"],
                carries=row["carries"],
                material_ref=row["material_ref"],
                call_id=row["call_id"],
                acs_order_id=row["acs_order_id"],
                state=row["state"],
                priority=row["priority"] or 0,
                attempt=row["attempt"] or 1,
                retry_of=row["retry_of"],
                failure_reason=row["failure_reason"] or "",
                created_at=row["created_at"] or 0.0,
                finished_at=row["finished_at"])

        for row in self.db.execute("SELECT * FROM locations"):
            self._locations[row["location"]] = Location(
                location=row["location"], kind=LocationKind(row["kind"]),
                segment=row["segment"])

        # Reports, oldest first so insertion order is preserved and the
        # sequence can be resumed past them.
        for row in self.db.execute(
                "SELECT * FROM abnormal_reports ORDER BY rowid"):
            self._reports[row["report_id"]] = Abnormal(
                report_id=row["report_id"], station=row["station"],
                description=row["description"], reported_by=row["reported_by"],
                reported_at=row["reported_at"],
                acknowledged_at=row["acknowledged_at"])
        self._resume_report_numbering()

        for row in self.db.execute("SELECT * FROM stations"):
            self._stations[row["our_name"]] = StationMap(
                our_name=row["our_name"], instance=row["instance"],
                customer_port_id=row["customer_port_id"])

    def _resume_call_numbering(self):
        """Continue the call_NNNN sequence past everything already stored."""
        import itertools

        highest = 0
        for call_id in self._calls:
            _, _, digits = call_id.partition("_")
            if digits.isdigit():
                highest = max(highest, int(digits))
        self._call_seq = itertools.count(highest + 1)

    def _resume_report_numbering(self):
        """Continue the abn_NNNN sequence past everything already stored.

        Same reason as calls: without it a restart reuses `abn_0001` and
        overwrites the report that already had that id.
        """
        import itertools

        highest = 0
        for report_id in self._reports:
            _, _, digits = report_id.partition("_")
            if digits.isdigit():
                highest = max(highest, int(digits))
        self._report_seq = itertools.count(highest + 1)

    # ------------------------------------------------------------- writing

    def _write(self, sql, params):
        self.db.execute(sql, params)
        # Committed per mutation rather than batched. A batch would be faster
        # and would lose exactly the records written since the last flush —
        # which, for a store whose whole purpose is surviving an unplanned
        # stop, is the wrong trade.
        self.db.commit()

    def define_rack(self, rack, slots, mode=RackMode.AUTO):
        result = super().define_rack(rack, slots, mode)
        # UPSERT THAT LEAVES THE MODE ALONE. The base constructor calls this
        # for every configured rack BEFORE `_load` reads the file back, so an
        # INSERT OR REPLACE here would write AUTO over a rack somebody had
        # marked abnormal, and `_load` would then read its own clobbered row.
        # A broken rack would come back in service after a restart, which is
        # the one thing a persistent store exists to prevent.
        #
        # Slot count still follows configuration — that is the existing rule
        # a few lines up in `_load`, and resizing a rack is deliberate.
        self._write("INSERT INTO racks (rack, slot_count, mode) "
                    "VALUES (?, ?, ?) ON CONFLICT(rack) DO UPDATE SET "
                    "slot_count = excluded.slot_count",
                    (rack, slots, mode.value))
        return result

    def set_rack_mode(self, rack, mode):
        """A rack taken out of service MUST stay out of service across a
        restart. An abnormal rack that came back as AUTO would be fed."""
        result = super().set_rack_mode(rack, mode)
        self._write("UPDATE racks SET mode = ? WHERE rack = ?",
                    (mode.value, rack))
        return result

    # -- calls ------------------------------------------------------------

    def _save_call(self, call):
        self._write(
            "INSERT OR REPLACE INTO calls (call_id, station, instance, "
            "task_type, source, raised_at, acknowledged_at, cancelled_at, "
            "job_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (call.call_id, call.station, call.instance,
             getattr(call.task_type, "name", call.task_type), call.source,
             call.raised_at, call.acknowledged_at, call.cancelled_at,
             call.job_id, call.status.value))
        return call

    def add_call(self, station, task_type, source, raised_at, instance=None):
        return self._save_call(super().add_call(
            station, task_type, source, raised_at, instance))

    def acknowledge_call(self, call_id, at, job_id=None):
        call = super().acknowledge_call(call_id, at, job_id)
        return self._save_call(call) if call else None

    def cancel_call(self, call_id, at):
        call = super().cancel_call(call_id, at)
        return self._save_call(call) if call else None

    # -- decisions --------------------------------------------------------

    def add_decision(self, decision):
        result = super().add_decision(decision)
        self._write(
            "INSERT INTO decisions (job_id, decided_at, chosen_source, "
            "chosen_dest, priority_given, reason) VALUES (?, ?, ?, ?, ?, ?)",
            (decision.job_id, decision.decided_at, decision.chosen_source,
             decision.chosen_dest, decision.priority_given, decision.reason))
        return result

    # -- rack slots -------------------------------------------------------

    def _save_slot(self, slot):
        attribute = getattr(slot.material_attribute, "name",
                            slot.material_attribute)
        self._write(
            "INSERT OR REPLACE INTO rack_slots (rack, slot, material_ref, "
            "parked_by_job, parked_at, retrieved_at, material_type, "
            "material_attribute, bobbin_type, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (slot.rack, slot.slot, slot.material_ref, slot.parked_by_job,
             slot.parked_at, slot.retrieved_at, slot.material_type,
             None if attribute is None else str(attribute), slot.bobbin_type,
             slot.status.value))
        return slot

    def park(self, rack, material_ref, job_id, at,
             material_type=None, material_attribute=None, bobbin_type=None):
        slot = super().park(rack, material_ref, job_id, at, material_type,
                            material_attribute, bobbin_type)
        return self._save_slot(slot) if slot else None

    def describe_slot(self, rack, slot_no, material_type=None,
                      material_attribute=None, bobbin_type=None):
        """§4.6.6's identity transfer has to survive a restart — it IS the
        record of what is on the rack."""
        slot = super().describe_slot(rack, slot_no, material_type,
                                     material_attribute, bobbin_type)
        return self._save_slot(slot) if slot else None

    def set_slot_status(self, rack, slot_no, status):
        slot = super().set_slot_status(rack, slot_no, status)
        return self._save_slot(slot) if slot else None

    def retrieve(self, rack, at, material_ref=None):
        slot = super().retrieve(rack, at, material_ref)
        return self._save_slot(slot) if slot else None

    # -- materials --------------------------------------------------------

    def _save_material(self, material):
        self._write(
            "INSERT OR REPLACE INTO materials (material_ref, lot_id, kind, "
            "created_at, location, ready_at, expires_at, attribute, "
            "drum_type, material_type, state, cure_started_at, "
            "cure_seconds) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (material.material_ref, material.lot_id, material.kind,
             material.created_at, material.location, material.ready_at,
             material.expires_at, _enum_name(material.attribute),
             material.drum_type, material.material_type,
             _enum_name(material.state), material.cure_started_at,
             material.cure_seconds))
        return material

    def _save_move(self, move):
        self._write(
            "INSERT OR REPLACE INTO material_moves (material_ref, seq, at, "
            "from_location, to_location, job_id, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (move.material_ref, move.seq, move.at, move.from_location,
             move.to_location, move.job_id, move.note))
        return move

    def register_material(self, kind="roll", at=0.0, location=None,
                          attribute=None, drum_type=None, material_type=None,
                          state=None):
        material = super().register_material(
            kind, at, location, attribute=attribute, drum_type=drum_type,
            material_type=material_type, state=state)
        self._save_material(material)
        # `register_material` records a move of its own when a location is
        # given, and that move is in the working set but not yet on disk.
        for move in self.history_of(material.material_ref):
            self._save_move(move)
        return material

    def move_material(self, material_ref, to_location, at, job_id=None,
                      note=""):
        move = super().move_material(material_ref, to_location, at, job_id,
                                     note)
        if move is None:
            return None
        self._save_move(move)
        # The material's own `location` changed too, and it is the field every
        # later question is answered from.
        self._save_material(self.material(material_ref))
        return move

    def begin_curing(self, material_ref, at, seconds):
        """The elapsed time MUST survive a power cut ([HB] §3), which is the
        only reason the clock is a recorded start rather than a timer."""
        material = super().begin_curing(material_ref, at, seconds)
        return self._save_material(material) if material else None

    def set_ready_at(self, material_ref, when):
        material = super().set_ready_at(material_ref, when)
        return self._save_material(material) if material else None

    # -- station map ------------------------------------------------------

    def define_location(self, location, kind, segment=None):
        entry = super().define_location(location, kind, segment)
        self._write(
            "INSERT OR REPLACE INTO locations (location, kind, segment) "
            "VALUES (?, ?, ?)",
            (entry.location, entry.kind.value, entry.segment))
        return entry

    def add_abnormal(self, station, description, reported_by="PDA", at=0.0):
        report = super().add_abnormal(station, description, reported_by, at)
        self._save_report(report)
        return report

    def acknowledge_report(self, report_id, at):
        report = super().acknowledge_report(report_id, at)
        if report is not None:
            self._save_report(report)
        return report

    def _save_report(self, report):
        self._write(
            "INSERT OR REPLACE INTO abnormal_reports (report_id, station, "
            "description, reported_by, reported_at, acknowledged_at) "
            "VALUES (?,?,?,?,?,?)",
            (report.report_id, report.station, report.description,
             report.reported_by, report.reported_at, report.acknowledged_at))

    def save_job(self, job, at=None, finished=False):
        record = super().save_job(job, at=at, finished=finished)
        self._write(
            "INSERT OR REPLACE INTO jobs (job_id, from_station, to_station, "
            "from_instance, to_instance, carries, material_ref, call_id, "
            "acs_order_id, state, priority, attempt, retry_of, "
            "failure_reason, created_at, finished_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (record.job_id, record.from_station, record.to_station,
             record.from_instance, record.to_instance, record.carries,
             record.material_ref, record.call_id, record.acs_order_id,
             record.state, record.priority, record.attempt, record.retry_of,
             record.failure_reason, record.created_at, record.finished_at))
        return record

    def map_station(self, our_name, customer_port_id):
        entry = super().map_station(our_name, customer_port_id)
        self._write(
            "INSERT OR REPLACE INTO stations (our_name, instance, "
            "customer_port_id) VALUES (?, ?, ?)",
            (entry.our_name, entry.instance, entry.customer_port_id))
        return entry

    # ------------------------------------------------------------- closing

    def close(self):
        self.db.close()

    def __repr__(self):
        return (f"<SqliteRecords calls={len(self._calls)} "
                f"materials={len(self._materials)} "
                f"decisions={len(self._decisions)}>")
