"""PDA — the handheld terminal, and the six things a worker does with it.

The fourth responsibility on the customer's CSM scope slide, and the only one
where a PERSON is the caller. Machines ask for robots automatically; this is
how a human gets into the loop when the automatic path cannot help — material
somewhere unexpected, a machine in manual mode, something gone wrong.

    생산 정보 등록          register material, by scanning it
    자재 위치 조회          where is this roll?
    작업 완료 확인          confirm a job finished
    비정상 상황 보고        report a problem
    AGV 수동 호출 및 취소   call a robot by hand, and cancel
    AGV 상태 확인          what are the robots doing?

THIS IS NOT A SCREEN. The handbook records that "CSM has no UI in the
specification and needs one", and that it is unscoped. So what is here is the
LOGIC a screen would call — which is CSM's, and can be tested without one. The
screens in the customer's own app (`RCS작업助手`, deck pages 81-84) are somebody
else's work.

⚠ POSITION CODES ARE NOT TRANSLATED YET. The real screen sends a 시작 위치 코드
and a 도착 위치 코드 — numbers in ranges 001-100, 101-199, 200-299 and 300-399.
We have never been given the mapping from those to the stations we know by
name, so `call_transport` accepts either and says plainly when a code cannot be
resolved. Inventing a mapping would put a fiction between a worker's button
press and a robot's destination.
"""

from dataclasses import dataclass

from .adapters.base import TaskType
from .material import MaterialAttribute


@dataclass
class Inbound:
    """The answer to "take this material inbound".

    TWO ORDINARY REFUSALS, TOLD APART. A worker who is turned away needs to
    know which of two different things to go and do: find another rack, or go
    and read the label. Returning None for both would collapse them into one
    unhelpful answer.

    The module's existing argument still holds — a full rack is an ordinary
    answer, not a fault — this is that argument with a second such answer.
    """

    ok: bool
    slot: object = None
    reason: str = ""


# `Abnormal` now lives in `records.py` with every other stored record — moved
# 2026-08-21 when reports stopped being memory-only. Import it from there;
# a second definition here would be a second truth about the same row.


class Pda:
    """What the handheld can ask the CSM to do."""

    def __init__(self, store, position_codes=None):
        """
        :param store: the JobStore — records, equipment and ACS hang off it.
        :param position_codes: {position code: our station name}. EMPTY by
            default and deliberately not guessed; see the module note.
        """
        self.store = store
        self.position_codes = dict(position_codes or {})

    # -- D1  생산 정보 등록 ------------------------------------------------

    def register_material(self, kind="roll", location=None, attribute=None,
                          drum_type=None, material_type=None):
        """Scan a new roll or bobbin into the system. Returns the `Material`.

        The LOT id is generated here, in the customer's format. A worker
        scanning material is usually the FIRST moment anything in our system
        knows the material exists.

        The three routing fields are optional HERE and required at inbound. On
        the real line scanning and describing are two moments: material is
        scanned when it appears, and supplemented once somebody has read the
        label. A scanner that already knows them may pass them straight in.
        """
        return self.store.records.register_material(
            kind=kind, at=self.store.clock(), location=location,
            attribute=attribute, drum_type=drum_type,
            material_type=material_type)

    def supplement(self, material_ref, attribute=None, drum_type=None,
                   material_type=None):
        """보록 — fill in what a worker read off the label. Returns the Material.

        §3.4's supplement, and the manual is explicit that all three must be
        **non-empty and non-zero**, "because a zero here is what produces the
        missing-info rack states".

        ZERO IS NOT A VALUE, IT IS THE MISSING STATE. `drum_type=0` would
        otherwise reach `pallet_capacity(0)` and come back as a dual pallet — a
        confident wrong answer derived from a field nobody filled in.

        Raises ValueError on a zero or an unknown material, because unlike a
        full rack these are not ordinary answers: they mean the screen sent
        something it should never send.
        """
        material = self.store.records.material(material_ref)
        if material is None:
            raise ValueError(f"no such material: {material_ref}")

        if attribute is not None:
            if not isinstance(attribute, MaterialAttribute):
                attribute = MaterialAttribute(attribute)
            material.attribute = attribute
        for name, value in (("drum_type", drum_type),
                            ("material_type", material_type)):
            if value is None:
                continue
            if value == 0:
                raise ValueError(f"{name} may not be zero — a zero here is the "
                                 f"missing-info state, not a value")
            setattr(material, name, value)

        self._save(material)
        return material

    def is_supplemented(self, material_ref):
        """Are all three routing fields present? The inbound condition."""
        material = self.store.records.material(material_ref)
        if material is None:
            return False
        return (material.attribute is not None
                and material.drum_type
                and material.material_type)

    def _save(self, material):
        """Persist an edited material, when the store is a durable one.

        `InMemoryRecords` hands out the live object, so mutating it is enough.
        A durable store needs telling. Reached through the store's own saver
        rather than SQL here, because a PDA does not know about databases.
        """
        saver = getattr(self.store.records, "_save_material", None)
        if saver is not None:
            saver(material)

    def bind_to_rack(self, material_ref, rack):
        """입고 — take supplemented material inbound onto a rack. -> `Inbound`.

        REFUSES MATERIAL NOBODY HAS DESCRIBED. The customer's rule (§3, §3.4),
        and the reason is their §5.1: a rack holding material whose information
        was never completed cannot be routed, and clearing those up is a
        standing daily task (§6 item 5).

        This gates the HUMAN inbound only. The WIP diversion parks through
        `records.park` directly, so a robot stranding a roll is unaffected —
        which is where the customer puts the gate too.
        """
        if not self.is_supplemented(material_ref):
            return Inbound(ok=False, reason="not supplemented — material type, "
                                            "attribute and bobbin type are "
                                            "required before inbound")
        now = self.store.clock()
        slot = self.store.records.park(rack, material_ref=material_ref,
                                       job_id=None, at=now)
        if slot is None:
            return Inbound(ok=False, reason=f"{rack} is full")
        self.store.records.move_material(material_ref, rack, at=now,
                                         note="bound by PDA")
        return Inbound(ok=True, slot=slot)

    # -- D2  자재 위치 조회 ------------------------------------------------

    def where_is(self, material_ref):
        """Where a material is, and how it got there.

        Returns None when we have never heard of it — which is a real answer.
        Material can exist on the floor without our knowing it; saying "not
        found" is honest, and inventing a location would be worse.
        """
        material = self.store.records.material(material_ref)
        if material is None:
            return None
        return {
            "material_ref": material.material_ref,
            "lot_id": material.lot_id,
            "kind": material.kind,
            "location": material.location,
            "history": self.store.records.history_of(material.material_ref),
        }

    # -- D3  작업 완료 확인 ------------------------------------------------

    def job_status(self, job_id):
        """Has this job finished, and how did it end?"""
        for record in self.store.active:
            if record.job.job_id == job_id:
                return {"job_id": job_id, "state": record.job.state_name,
                        "finished": False,
                        "failure_reason": record.job.failure_reason}
        for job in self.store.finished:
            if job.job_id == job_id:
                return {"job_id": job_id, "state": job.state_name,
                        "finished": True,
                        "failure_reason": job.failure_reason}
        return None

    # -- D4  비정상 상황 보고 ----------------------------------------------

    def report_abnormal(self, station, description, reported_by="PDA"):
        """File a problem. STORED, not just logged.

        Until 2026-08-21 these lived in a dict on this object and were written
        nowhere, so a report vanished when the process restarted. That defeats
        the reason for keeping them at all, stated at the top of this module:
        a report that is only logged is a report nobody can count, chase or
        close. They go to the records store now, like everything else that has
        to outlive a run.
        """
        report = self.store.records.add_abnormal(
            station=station, description=description,
            reported_by=reported_by, at=self.store.clock())
        self.store.logger(f"[{station}] ABNORMAL reported via "
                          f"{reported_by}: {description}")
        return report

    def open_reports(self):
        return self.store.records.open_reports()

    def acknowledge_report(self, report_id):
        return self.store.records.acknowledge_report(
            report_id, at=self.store.clock())

    # -- D5  AGV 수동 호출 및 취소 ------------------------------------------

    def resolve_position(self, code):
        """A position code from the handheld -> a station we know.

        Returns None when the code is not in the map, and the map is EMPTY
        until the customer gives it to us. A worker seeing "unknown position
        code" is a great deal better than a robot being sent somewhere we
        guessed.
        """
        if code in self.position_codes:
            return self.position_codes[code]
        # A name the plant already uses is accepted as itself, so the function
        # is usable today without the customer's table.
        if code in self.store.equipment.list_stations():
            return code
        return None

    def call_transport(self, from_code, to_code, equipment_no=None):
        """The 大AGV搬运 screen: move something from here to there.

        A POINT-TO-POINT JOB, which is a different shape from an equipment
        call. A machine asking for material says only who wants it, and CSM
        works out the source. Here the worker has named BOTH ends, so there is
        nothing for CSM to choose — and the decision record says so.

        Returns the job record, or a string naming what could not be resolved.
        """
        source = self.resolve_position(from_code)
        destination = self.resolve_position(to_code)
        if source is None:
            return f"unknown start position code: {from_code}"
        if destination is None:
            return f"unknown destination position code: {to_code}"
        if source == destination:
            return "start and destination are the same place"

        return self.store.create(
            source, destination,
            task_type=TaskType.LOAD,
            reason=f"manual call from the PDA"
                   f"{f' (equipment {equipment_no})' if equipment_no else ''}")

    def cancel_transport(self, job_id):
        """Withdraw a job a person raised. True if it was cancelled.

        Stops the CSM job and the ACS order behind it. If the job was
        answering a machine's call, the store then hands that call back through
        the four-step cancellation, which ends in an alarm an operator resets —
        marking the job unretryable is what starts it. A job the PDA raised
        itself answers no call, so nothing is handed back.
        """
        for record in self.store.active:
            if record.job.job_id == job_id:
                # `cancel_order` — ADR 2026-08-18. The response is deliberately
                # not read: against the real ACS this mutation only acknowledges
                # that the REQUEST was taken, and whether the order actually
                # stopped arrives later on the order itself. Returning True here
                # because the CSM job was withdrawn, which is what the person
                # pressing the button asked for and is true either way.
                self.store.acs.cancel_order(job_id)
                record.job.failure_reason = "cancelled from the PDA"
                # A person stopped this on purpose. Raising it again
                # would be arguing with them.
                record.job.retryable = False
                self.store.logger(f"[{job_id}] cancelled from the PDA")
                return True
        return False

    # -- D6  AGV 상태 확인 -------------------------------------------------

    def fleet_status(self):
        """What each robot is doing. Empty when the ACS cannot say.

        Read from the ACS, never kept here: robot position and battery are on
        section 7's "not retained" list, and a copy of them would be a second
        version of the truth.
        """
        acs = self.store.acs
        if not hasattr(acs, "fleet_status"):
            return []
        return acs.fleet_status()
