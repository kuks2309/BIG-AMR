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


@dataclass
class Abnormal:
    """A problem a person reported. Not in specification section 7.

    It comes from the scope slide (비정상 상황 보고) rather than the record list,
    and it is kept because a report that is only logged is a report nobody can
    count, chase or close.
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
        self._abnormal = {}
        self._report_seq = 0

    # -- D1  생산 정보 등록 ------------------------------------------------

    def register_material(self, kind="roll", location=None):
        """Scan a new roll or bobbin into the system. Returns the `Material`.

        The LOT id is generated here, in the customer's format. A worker
        scanning material is usually the FIRST moment anything in our system
        knows the material exists.
        """
        return self.store.records.register_material(
            kind=kind, at=self.store.clock(), location=location)

    def bind_to_rack(self, material_ref, rack):
        """Put scanned material into a rack slot — the binding screens.

        Returns the slot, or None if the rack is full. None rather than an
        exception because a full rack is an ordinary answer a worker needs to
        see, not a fault.
        """
        now = self.store.clock()
        slot = self.store.records.park(rack, material_ref=material_ref,
                                       job_id=None, at=now)
        if slot is not None:
            self.store.records.move_material(material_ref, rack, at=now,
                                             note="bound by PDA")
        return slot

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
        self._report_seq += 1
        report = Abnormal(
            report_id=f"abn_{self._report_seq:04d}",
            station=station,
            description=description,
            reported_at=self.store.clock(),
            reported_by=reported_by,
        )
        self._abnormal[report.report_id] = report
        self.store.logger(f"[{station}] ABNORMAL reported via "
                          f"{reported_by}: {description}")
        return report

    def open_reports(self):
        return [r for r in self._abnormal.values() if r.open]

    def acknowledge_report(self, report_id):
        report = self._abnormal.get(report_id)
        if report is not None:
            report.acknowledged_at = self.store.clock()
        return report

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
                self.store.acs.cancel_job(job_id)
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
