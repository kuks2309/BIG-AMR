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

from .base import (AcsAdapter, DockingAxis, EquipmentAdapter,
                   MachineNumber, MaterialPresence, StationStatus,
                   TaskProcessing, TaskType, TransportCall,
                   TransportResult)
from .handshake import DockingHandshake


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
            # The source handed its material over, so it now has nothing —
            # UNLESS it is a warehouse. A store is always supplied; that is what
            # makes it a store, and it is why `mark_store` exists.
            #
            # Without the exemption the store emptied on the FIRST completed job
            # and was never restocked, so no ASRS-sourced job could be created
            # again. Measured in Gazebo 2026-08-07 with one robot: 18 calls
            # raised, 4 jobs created. GRV1_LD and GRV2_LD were served only
            # because both jobs existed before the first one finished; GRV3_LD
            # and GRV4_LD called repeatedly and were never served, and amr1 sat
            # at its parking bay with nothing it could legally do.
            #
            # The `delivered` branch below already had this exemption. The
            # asymmetry between the two was the whole bug.
            self._busy_until.pop(station_id, None)
            self._status[station_id] = (
                StationStatus.FINISHED if station_id in self._store_ids
                else StationStatus.IDLE)
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

    def can_accept(self, station_id):
        """A warehouse always has room for a returned bobbin.

        Unless the equipment has said otherwise — `buffer_full` is checked
        first, because "a store always has room" is our assumption and code 4
        is the customer's measurement.
        """
        if self.buffer_full(station_id):
            return False
        if station_id in self._store_ids:
            return True
        return super().can_accept(station_id)

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


class OpcUaEquipment(MockEquipment):
    """A machine that speaks the customer's protocol — and misbehaves on demand.

    `MockEquipment` is a believable factory. This is a HOSTILE one, and that is
    the point: the equipment interface has no acknowledgement, its requests are
    edge-triggered, and its entry permission is a duration rather than a flag.
    Every one of those is a way for a correct-looking CSM to lose work
    silently, and none of them can be provoked by a mock that only behaves.

    So this one can:

      * report the three PRESENCE booleans independently, including the
        combination that means nothing (a real machine mid-transition can);
      * raise a request and CLEAR IT AGAIN after a set time, which is what
        makes a poll interval a safety margin rather than a preference;
      * accept a command, return success, and DO NOTHING — because the real
        protocol is shared memory and `send_station_command() -> bool` cannot
        tell the difference;
      * withdraw entry permission part way through a dock;
      * stop its heartbeat;
      * report any of the nine task-processing codes.

    Stations are identified by `MC_Num` (`1A01`), not by our invented names.
    """

    def __init__(self, station_ids, clock, process_seconds=5.0,
                 comm_alarm_seconds=2.0):
        super().__init__(station_ids, clock, process_seconds)
        self.comm_alarm_seconds = comm_alarm_seconds

        #: our name -> MC_Num. This IS the specification's `station_map`
        #: record; the customer's identity for a port, beside ours.
        self._mc_num = {}

        #: station -> (Rolling_Full, Roll_Null, Roll_IN). Three independent
        #: booleans, never a single status, so INCONSISTENT is reachable.
        self._presence = {sid: (False, True, False) for sid in station_ids}

        #: station -> TaskProcessing the AGV last reported there.
        self._processing = {}

        #: station -> when a held request clears itself. The machine stops
        #: asking once it believes it was heard, so a request that appears and
        #: clears between two polls is LOST while the machine thinks it landed.
        self._call_expiry = {}

        #: Stations whose next command will be accepted and ignored.
        self._swallow = set()

        #: station -> DockingHandshake, the mutual watchdog for its door.
        self._handshake = {}
        self._enter_permitted = {sid: False for sid in station_ids}
        self._heartbeat_on = {sid: True for sid in station_ids}

    # -- identity: MC_Num, not our invented names ------------------------

    def set_machine_number(self, station_id, mc_num):
        """Bind our name for a port to the customer's."""
        self._mc_num[station_id] = MachineNumber.parse(mc_num)

    def machine_number(self, station_id):
        return self._mc_num.get(station_id)

    def station_map(self):
        """The specification's station_map record: our name, their port id."""
        return {name: str(mc) for name, mc in self._mc_num.items()}

    # -- presence: three booleans, not a status --------------------------

    def set_presence(self, station_id, rolling_full=False, roll_null=False,
                     roll_in=False):
        """Set MC_Rolling_Full / MC_Roll_Null / MC_Roll_IN independently.

        Independently on purpose. A machine part way through an exchange can
        assert a combination that means nothing, and a CSM that rounds it to
        the nearest sensible state hides a fault.
        """
        self._presence[station_id] = (bool(rolling_full), bool(roll_null),
                                      bool(roll_in))

    def presence(self, station_id):
        return MaterialPresence.from_signals(
            *self._presence.get(station_id, (False, False, False)))

    # -- the nine status codes -------------------------------------------

    def set_task_processing(self, station_id, code):
        self._processing[station_id] = TaskProcessing(code)

    def task_processing(self, station_id):
        return self._processing.get(station_id)

    # -- edge-triggered requests, and losing them ------------------------

    def raise_call_for(self, station_id, seconds, task_type=TaskType.LOAD,
                       source="machine"):
        """Ask for a robot, then STOP ASKING after `seconds`.

        ⚠ NOT THE NORMAL PROTOCOL. Corrected 2026-08-18: the machine clears its
        request when it sees `AGV_Task_Recive = 1` — our acknowledgement — and
        NOT on a timer. A slow poll therefore costs latency, not the request.

        This models the cases where a request goes away for some OTHER reason:
        an operator cancelling at the panel, or the machine alarming out. Those
        are real and worth being able to provoke, but they are not what an
        ordinary unanswered call does, and a test using this should say which
        it means.
        """
        self.raise_call(station_id, task_type, source)
        self._call_expiry[station_id] = self._clock() + seconds

    def poll_calls(self):
        """Outstanding requests — minus any the machine has given up on."""
        now = self._clock()
        expired = [sid for sid, t in self._call_expiry.items() if now >= t]
        for sid in expired:
            del self._call_expiry[sid]
            self._calls = [c for c in self._calls if c.station_id != sid]
        return super().poll_calls()

    # -- no acknowledgement: a command may simply not happen -------------

    def swallow_next_command(self, station_id):
        """The next command to this station is accepted and ignored.

        Not a fault injection so much as an honest one. There is no
        acknowledgement in this protocol — it is shared memory, not a
        transaction — so `send_station_command() -> bool` returning True is a
        statement about the SEND, never about the effect. A CSM that trusts it
        is trusting something the wire cannot tell it. See debt-034.
        """
        self._swallow.add(station_id)

    def send_station_command(self, station_id, command):
        if station_id in self._swallow:
            self._swallow.discard(station_id)
            self.commands.append((station_id, command, "swallowed"))
            return True                 # the lie the real protocol also tells
        return super().send_station_command(station_id, command)

    # -- the door: entry permission and the mutual watchdog --------------

    def handshake(self, station_id):
        if station_id not in self._handshake:
            self._handshake[station_id] = DockingHandshake(
                comm_alarm_seconds=self.comm_alarm_seconds)
        return self._handshake[station_id]

    def set_enter_permitted(self, station_id, permitted):
        """MC_Enter_Permitted. Withdrawing it mid-dock is the case that matters."""
        self._enter_permitted[station_id] = bool(permitted)

    def stop_heartbeat(self, station_id):
        self._heartbeat_on[station_id] = False

    def start_heartbeat(self, station_id):
        self._heartbeat_on[station_id] = True

    def observe(self, station_id, agv_entering=False):
        """One poll of this station's door. Returns its DockingHandshake.

        The caller reads `may_enter` and `may_machine_move` from it. Both are
        duration rules, so this has to be called every cycle — asking once
        cannot answer either of them.
        """
        hs = self.handshake(station_id)
        hs.observe(self._clock(),
                   enter_permitted=self._enter_permitted.get(station_id, False),
                   agv_entering=agv_entering,
                   machine_heartbeat=self._heartbeat_on.get(station_id, True))
        return hs


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
