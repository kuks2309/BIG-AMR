"""Mock adapters - a fake factory, so the Mini MES can be built and tested today.

These stand in for the two things that are not available:

  * the equipment protocol, which is blocked on CATL
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

from .base import (AcsAdapter, EquipmentAdapter, StationStatus,
                   TransportResult)


class MockEquipment(EquipmentAdapter):

    def __init__(self, station_ids, clock, process_seconds=5.0):
        """
        :param station_ids:     e.g. ["station_3", "station_9"]
        :param clock:           callable() -> float, seconds
        :param process_seconds: how long BUSY lasts before FINISHED
        """
        self._clock = clock
        self._process_seconds = process_seconds
        self._status = {sid: StationStatus.IDLE for sid in station_ids}
        self._busy_until = {}
        self.commands = []          # recorded for assertions in tests

    # -- EquipmentAdapter ------------------------------------------------

    def get_station_status(self, station_id):
        if station_id not in self._status:
            return StationStatus.UNKNOWN

        # A BUSY station becomes FINISHED once its processing time elapses.
        until = self._busy_until.get(station_id)
        if until is not None and self._clock() >= until:
            self._status[station_id] = StationStatus.FINISHED
            self._busy_until.pop(station_id, None)

        return self._status[station_id]

    def send_station_command(self, station_id, command):
        if station_id not in self._status:
            return False
        self.commands.append((self._clock(), station_id, command))

        if command == "start":
            self._status[station_id] = StationStatus.BUSY
            self._busy_until[station_id] = self._clock() + self._process_seconds
            return True
        if command == "collected":
            self._status[station_id] = StationStatus.IDLE
            return True
        return False

    def list_stations(self):
        return list(self._status)

    # -- test helpers ----------------------------------------------------

    def force_status(self, station_id, status):
        """Put a station into any state directly, including FAULT."""
        self._status[station_id] = status
        self._busy_until.pop(station_id, None)


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
