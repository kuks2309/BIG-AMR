"""Mock adapters - a fake factory, so the CSM can be built and tested today.

These stand in for the two things that are not available:

  * the equipment protocol (spec received 2026-08-04; no adapter written yet)
  * the ACS interface, which is undecided

Both are driven by an injected clock rather than wall time, so tests can advance
time instantly and deterministically. That is what makes the timeout path
testable — a ten-minute timeout should not take ten minutes to verify.

MockEquipment cycles stations through a believable rhythm:

    IDLE --(load)--> BUSY --(process_seconds)--> FINISHED --(collected)--> IDLE

MockAcs accepts jobs and reports ARRIVED after a fixed travel time. Both can be
told to fail on demand, because the failure paths are the ones worth testing.
"""

import itertools

from .base import (AcsAdapter, EquipmentAdapter, StationStatus, TaskType,
                   TransportCall, TransportResult)


class MockEquipment(EquipmentAdapter):

    def __init__(self, station_ids, clock, process_seconds=5.0):
        """
        :param station_ids:     e.g. ["1A01", "1T01"]
        :param clock:           callable() -> float, seconds
        :param process_seconds: how long BUSY lasts before FINISHED
        """
        self._clock = clock
        self._process_seconds = process_seconds
        self._status = {sid: StationStatus.IDLE for sid in station_ids}
        self._busy_until = {}
        self.commands = []          # recorded for assertions in tests

        #: Calls raised and not yet acknowledged. Held here rather than
        #: reported as a level, because a call is a transition and the machine
        #: clears it once it believes it was heard — see TransportCall.
        self._calls = []
        self.acknowledged = []      # recorded for assertions in tests

        #: Stations that are warehouses rather than machines. A store always
        #: has something to give and never needs to process.
        self._store_ids = set()

        #: load port -> unload port, for machines whose output appears
        #: somewhere other than where the material went in. Empty means every
        #: station keeps its own output, which is how a single-port machine
        #: behaves and what every existing test assumes.
        self._outlet = {}

    # -- EquipmentAdapter ------------------------------------------------

    def get_station_status(self, station_id):
        if station_id not in self._status:
            return StationStatus.UNKNOWN
        self._settle()
        return self._status[station_id]

    def _settle(self):
        """Apply every elapsed processing time, not just the one being asked about.

        Lazily settling only the queried station is not enough once a machine's
        output appears at a DIFFERENT port from its input. Nobody ever asks
        about a load port: the monitor asks whether a job's SOURCE has material,
        and the source of a coater job is the gravure's UNLOAD port. So the
        gravure's load port would sit BUSY for ever, its timer never examined,
        and the material would arrive and stop dead.
        """
        now = self._clock()
        for sid, until in list(self._busy_until.items()):
            if now < until:
                continue
            self._busy_until.pop(sid, None)
            outlet = self._outlet.get(sid)
            if outlet is None:
                self._status[sid] = StationStatus.FINISHED
                continue
            # THE MACHINE'S INTERNAL HAND-OVER. Material went in at the load
            # port, the machine ran, and the output now sits at the unload
            # port — which is a different station with its own docking bay.
            # The load port is free again to take the next roll.
            self._status[sid] = StationStatus.IDLE
            self._status[outlet] = StationStatus.FINISHED

    def send_station_command(self, station_id, command):
        if station_id not in self._status:
            return False
        self.commands.append((self._clock(), station_id, command))

        if command == "start":
            self._status[station_id] = StationStatus.BUSY
            self._busy_until[station_id] = self._clock() + self._process_seconds
            return True
        if command == "collected":
            # The source handed its material over, so it now has nothing.
            self._status[station_id] = StationStatus.IDLE
            self._busy_until.pop(station_id, None)
            return True

        if command == "delivered":
            # Material ARRIVED here — which means the machine now has work to
            # do, not something to give away. It goes BUSY and only becomes
            # collectable once processing finishes.
            #
            # This is what makes a line FILL rather than being fully stocked
            # from the first tick: the store feeds machine 1, machine 1 works,
            # and only then can machine 2 be fed. A store is the exception —
            # it is a warehouse, so it is always ready.
            if self._store_ids and station_id in self._store_ids:
                self._status[station_id] = StationStatus.FINISHED
            else:
                self.start_processing(station_id)
            return True
        return False

    def list_stations(self):
        return list(self._status)

    # -- the call interface ----------------------------------------------

    def poll_calls(self):
        """Outstanding calls. Latched until acknowledged, deliberately."""
        return list(self._calls)

    def acknowledge_call(self, call):
        self.acknowledged.append((self._clock(), call.station_id))
        self._calls = [c for c in self._calls if c is not call]

    # -- test helpers ----------------------------------------------------

    def force_status(self, station_id, status):
        """Put a station into any state directly, including FAULT."""
        self._status[station_id] = status
        self._busy_until.pop(station_id, None)

    def link_ports(self, load_id, unload_id):
        """Declare that this machine's output appears at a different port.

        Real machines are listed as "Unwinder / Rewinder" pairs: a roll goes in
        one side and comes out the other. Without this the two ports are
        unrelated stations, material delivered to the load port is never
        collectable from the unload port, and every downstream job is unservable
        for ever — the line cannot fill past its first stage.
        """
        self._outlet[load_id] = unload_id

    def mark_store(self, *station_ids):
        """Declare these to be warehouses: always supplied, never processing."""
        self._store_ids.update(station_ids)
        for sid in station_ids:
            self._status[sid] = StationStatus.FINISHED

    def raise_call(self, station_id, task_type=TaskType.LOAD, source="machine"):
        """A machine asks for a robot — the way work actually starts.

        `source` is "machine" or "PDA"; the protocol treats them identically
        and both are ultimately a person pressing something.
        """
        call = TransportCall(station_id, task_type, self._clock(), source)
        self._calls.append(call)
        return call

    def start_processing(self, station_id, seconds=None):
        """The machine begins work on what it was given.

        BUSY means it HOLDS material that is not available. Only when the time
        elapses does it become FINISHED and collectable. A machine handed a raw
        roll has nothing to give until this completes.
        """
        self._status[station_id] = StationStatus.BUSY
        self._busy_until[station_id] = self._clock() + (
            self._process_seconds if seconds is None else seconds)


class MockAcs(AcsAdapter):

    def __init__(self, clock, travel_seconds=8.0, accept=True):
        """
        :param clock:          callable() -> float, seconds
        :param travel_seconds: time from submission to ARRIVED
        :param accept:         False makes every submission REJECTED
        """
        self._clock = clock
        self._travel_seconds = travel_seconds
        self.accept = accept
        self.fail_next = False       # flip to exercise the failure branch
        self._arrive_at = {}
        self._failed = set()
        self._cancelled = set()
        self.submitted = []          # recorded for assertions in tests

    # -- AcsAdapter ------------------------------------------------------

    def submit_job(self, job):
        if not self.accept:
            return TransportResult.REJECTED
        self.submitted.append(job.job_id)
        if self.fail_next:
            self._failed.add(job.job_id)
            self.fail_next = False
        else:
            self._arrive_at[job.job_id] = self._clock() + self._travel_seconds
        return TransportResult.ACCEPTED

    def get_job_result(self, job_id):
        if job_id in self._cancelled:
            return TransportResult.FAILED
        if job_id in self._failed:
            return TransportResult.FAILED
        arrive_at = self._arrive_at.get(job_id)
        if arrive_at is None:
            return TransportResult.UNKNOWN
        if self._clock() >= arrive_at:
            return TransportResult.ARRIVED
        return TransportResult.IN_PROGRESS

    def cancel_job(self, job_id):
        self._cancelled.add(job_id)
        self._arrive_at.pop(job_id, None)
        return True

    # -- test helpers ----------------------------------------------------

    def never_arrives(self, job_id):
        """Make a job hang forever — the case the timeout transition exists for."""
        self._arrive_at[job_id] = float("inf")


class ManualClock:
    """A clock the test drives by hand.

    Real time in a test means a ten-minute timeout takes ten minutes to verify.
    With this, it takes no time at all and the result is identical on every run.
    """

    def __init__(self, start=0.0):
        self.now = float(start)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += float(seconds)
        return self.now


_counter = itertools.count(1)


def next_job_id():
    return f"job_{next(_counter):04d}"
