"""EquipmentMonitorTask — "who is asking for a robot?"

The first box on the whiteboard, and the one whose direction was wrong until
2026-08-04.

**The correction.** This task used to watch machines and invent work: a station
reported FINISHED, so a job was created to move its output onward. That is
backwards. The equipment CALLS — usually because a person pressed a button on
the machine or scanned a handheld terminal beside it — and only then does
anything happen.

    operator or machine  ──call──▶  CSM  ──▶  release from the source

The caller is the **destination**. A machine asking for a LOAD wants material
brought *to* it; working out where that material comes from is our job, not
something the call carries.

**Polling is the specified interaction**, not a shortcut. The interface is not
event-driven — both sides raise bits and the CSM scans at a fixed interval.
Which makes the interval the entire safety margin, because a call is a
transition and the machine clears it once it believes it was heard. The adapter
latches calls until acknowledged so the race does not reach this task; the
period below is still an unjustified default until somebody asks the equipment
vendor for its minimum signal hold time. See debt-033.
"""

from ...adapters.base import StationStatus, TaskType
from ...job import Carried
from ..fsm_task import FsmTask

#: 1 Hz. Not a measured number — see the note above and debt-033.
DEFAULT_PERIOD_S = 1.0


class EquipmentMonitorTask(FsmTask):

    name = "equipment_monitor"
    period = DEFAULT_PERIOD_S

    def __init__(self, store, source_for, wakes=None, name=None, period=None):
        """
        :param store: the shared JobStore
        :param source_for: callable(station_id) -> station_id that feeds it.
            The call says who wants material, never where it comes from, so
            somebody has to answer that. It is the process route, and it lives
            outside this task because a route is configuration, not logic.
        :param wakes: FsmTasks to notify when a job is created.
        """
        super().__init__(name=name, period=period)
        self.store = store
        self.source_for = source_for

        #: Ranked alternatives for a destination. Defaults to "whatever
        #: source_for said", so a caller that supplied only the single-source
        #: callable keeps its existing behaviour exactly.
        self.sources_for = getattr(source_for, "candidates",
                                   lambda sid: [source_for(sid)])
        self.wakes = list(wakes or [])

        #: Segments to run the diversion scan over. None disables it, which is
        #: the default so that every existing caller behaves exactly as before.
        self.divert_for = None

        #: callable(station_id) -> where that station's EMPTY BOBBIN goes, or
        #: None if it does not hand one back. Injected for the same reason
        #: `source_for` is: the return route is the process route, which is
        #: configuration, not logic. `plant.bobbin_return_for` is the real
        #: implementation. None disables bobbin returns entirely, so every
        #: existing caller behaves exactly as before.
        self.return_for = None

        #: Bobbin returns raised, counted apart from material jobs because a
        #: line that moves rolls and never returns bobbins runs out of empty
        #: cores, and the two numbers diverging is how you see it.
        self.returned = 0

        #: Commands that were accepted and then never showed up in the
        #: machine's own state. Counted because on this protocol that is the
        #: ONLY way a lost command is visible — nothing errors. See debt-034.
        self.commands_lost = 0

        self.created = 0
        #: Jobs created with no caller, to clear stranded material.
        self.diverted = 0
        #: Calls heard but not turned into jobs, because the source had nothing
        #: to give. Worth counting separately: a rising number here is a supply
        #: problem upstream, not a fault in this layer.
        self.deferred = 0

    async def step(self):
        for call in self.store.equipment.poll_calls():
            # AN UNLOAD CALL INVERTS THE QUESTION THIS TASK NORMALLY ASKS.
            #
            # A LOAD call means "bring me material", so the caller is the
            # destination and the work is finding a source. An UNLOAD call
            # means "take this away" — the machine is holding an empty bobbin
            # after its roll was consumed. The caller is the SOURCE, and the
            # destination is not chosen at all: it is fixed by the process
            # route (specification jobs 3, 7 and 11, assumption A5).
            #
            # Handled before the material path rather than inside it, because
            # every step below — ranking sources, checking they can supply —
            # asks a question that does not apply here.
            if call.task_type is TaskType.UNLOAD and self.return_for is not None:
                if self._return_bobbin(call):
                    for task in self.wakes:
                        task.notify()
                continue

            # TRY EVERY CANDIDATE, NOT JUST THE PAIRED ONE.
            #
            # `source_for` names one station. When that one is empty the call
            # used to be deferred, even if a sibling upstream was holding
            # finished material — so a coater could sit idle while three
            # gravures had output waiting. `sources_for` ranks the alternatives
            # (rack first, then the pair, then siblings) and the first that can
            # actually supply wins.
            source = None
            for cand in self.sources_for(call.station_id):
                if self._can_supply(cand):
                    source = cand
                    break

            # Nothing anywhere can serve this call yet. Leave it outstanding —
            # do NOT acknowledge it — so it is picked up again once material
            # exists. Acknowledging here would tell the machine it had been
            # heard and then drop the request, which is the silent failure this
            # layer must not have.
            if source is None:
                self.deferred += 1
                continue

            # One job per station at a time. The station latch is the store's,
            # and it is what stops a machine that keeps calling from spawning a
            # second robot for work already under way.
            if not self.store.claim_station(call.station_id):
                continue

            # RECORD THE CALL BEFORE SERVING IT. Section 7 keeps calls and
            # jobs apart because they are not the same thing and do not always
            # both exist: a call nothing can serve yet has no job, and the WIP
            # diversion is a job with no call.
            recorded = self.store.records.add_call(
                station=call.station_id,
                task_type=call.task_type,
                source=call.source,
                raised_at=self.store.clock(),
            )
            job = self.store.create(source, call.station_id,
                                    task_type=call.task_type,
                                    call_id=recorded.call_id,
                                    reason=f"nearest source that could supply "
                                           f"{call.station_id}")
            self.created += 1

            # Heard. The machine stops calling now, and only now.
            self.store.records.acknowledge_call(
                recorded.call_id, at=self.store.clock(),
                job_id=job.job.job_id)
            self.store.equipment.acknowledge_call(call)
            self.store.logger(
                f"[{call.station_id}] call heard via {call.source} "
                f"({call.task_type.name.lower()}) — source {source}")

            for task in self.wakes:
                task.notify()

        self._divert_stranded()
        self._resolve_commands()
        self._sync_station_map()

    def _sync_station_map(self):
        """Learn the customer's id for each port, as the machines report it.

        Done every tick rather than once at startup, because `MC_Num` arrives
        over a subscription like everything else: at startup we have not been
        told it yet, and a station that comes back after a restart reports it
        again. Writing only on change keeps that cheap.

        Adapters that cannot report one are skipped rather than recorded as
        None — an absent mapping and a mapping to nothing are different, and
        only the first is normal.
        """
        equipment = self.store.equipment
        if not hasattr(equipment, "station_map"):
            return
        for our_name, customer_id in equipment.station_map().items():
            if customer_id and self.store.records.customer_id(our_name) != customer_id:
                self.store.records.map_station(our_name, customer_id)

    def _resolve_commands(self):
        """Read back every command we sent and have not yet seen take effect.

        This is the other half of `send_and_confirm`. The equipment link has no
        acknowledgement, so a command that was accepted and ignored looks
        exactly like one that worked — until the machine's own state fails to
        change. Nothing else in the system will ever notice it.

        Owned here because this task already holds the poll loop; the reading
        has to happen every tick, and a one-shot caller cannot do it.
        """
        equipment = self.store.equipment
        if not hasattr(equipment, "resolve_confirmations"):
            return
        for lost in equipment.resolve_confirmations(self.store.clock()):
            self.commands_lost += 1
            self.store.logger(
                f"[{lost.station_id}] '{lost.command}' was accepted and never "
                f"took effect — the machine may still be blocked")

    def _return_bobbin(self, call):
        """Send this station's empty bobbin back up the process route.

        Returns True if a job was created. A False here leaves the call
        OUTSTANDING and unacknowledged on purpose: telling the machine it was
        heard and then not moving the bobbin is the silent failure this layer
        exists to avoid, and the machine will keep asking until it is served.
        """
        destination = self.return_for(call.station_id)
        if destination is None:
            # Not a station that hands bobbins back — the ASRS and the racks do
            # not. A call here means our route table and the machine disagree,
            # which is worth seeing rather than swallowing.
            self.deferred += 1
            self.store.logger(
                f"[{call.station_id}] unload call, but no bobbin return route")
            return False

        if not self._can_accept(destination):
            self.deferred += 1
            return False

        if not self.store.claim_station(call.station_id):
            return False

        recorded = self.store.records.add_call(
            station=call.station_id,
            task_type=call.task_type,
            source=call.source,
            raised_at=self.store.clock(),
        )
        job = self.store.create(call.station_id, destination,
                                task_type=call.task_type,
                                carries=Carried.BOBBIN,
                                call_id=recorded.call_id,
                                reason="bobbin returns one process upstream")
        self.created += 1
        self.returned += 1
        self.store.records.acknowledge_call(
            recorded.call_id, at=self.store.clock(), job_id=job.job.job_id)
        self.store.equipment.acknowledge_call(call)
        self.store.logger(
            f"[{call.station_id}] bobbin return via {call.source} "
            f"-> {destination}")
        return True

    # ------------------------------------------------------------ diversion

    def _divert_stranded(self):
        """Park material whose destinations are all full onto the WIP rack.

        THE ONE JOB TYPE CSM ORIGINATES ITSELF. Every other job answers a call:
        a machine asks and we serve it. This one has no caller — a source is
        holding finished material, every destination that could take it is
        occupied, and if nobody moves it the upstream machine blocks.

        The specification names CSM as the decider ("장비들이 판단하는게 아니라
        CSM에서 판단을 해서") and gives the rule: find a free rack port and use
        the first one.

        Deliberately conservative. It only fires when EVERY destination is
        unavailable, so it never competes with a real delivery, and it is the
        last thing each tick so calls always win.
        """
        if self.divert_for is None:
            return
        for seg in self.divert_for:
            for source in seg["from"]:
                if not self._can_supply(source):
                    continue
                if self.store.station_claimed(source):
                    continue
                # Somewhere real to put it? Then this is not stranded.
                if any(self._can_accept(d) for d in seg["to"]):
                    continue
                port = next((b for b in seg["buffer"]
                             if self._can_accept(b)
                             and not self.store.station_claimed(b)), None)
                if port is None:
                    continue                      # rack full too — nothing to do
                if not self.store.claim_station(port):
                    continue
                # THE ONE JOB WITH NO CALLER, so no call_id — which is
                # exactly what makes it identifiable later.
                job = self.store.create(
                    source, port,
                    reason=f"every destination of segment {seg['name']} was "
                           f"full")
                self.store.records.park(port, material_ref=job.job.job_id,
                                        job_id=job.job.job_id,
                                        at=self.store.clock())
                self.diverted += 1
                self.store.logger(
                    f"[{source}] all destinations full — diverted to {port}")
                for task in self.wakes:
                    task.notify()

    def _can_accept(self, station_id):
        """Is this station free to receive something right now?

        Asked of the adapter rather than derived from status here, because a
        warehouse answers it differently — see `EquipmentAdapter.can_accept`.
        """
        return self.store.equipment.can_accept(station_id)

    def _can_supply(self, station_id):
        """Can this place actually hand something over right now?

        BUSY is the one worth stating: a machine that is processing HOLDS
        material but cannot give it. Treating held and available as the same
        thing sends a robot to collect something that does not exist yet.
        """
        return (self.store.equipment.get_station_status(station_id)
                is StationStatus.FINISHED)
