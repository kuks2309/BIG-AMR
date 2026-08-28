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
from ...material import attribute_matches, needs_rotation
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
        #: `material_profile.MaterialProfile`, or None to mint material with
        #: no description — which is what the code did before and is still a
        #: real state, being the one §1.3 excludes.
        self.profile = None
        #: `curing.CuringPolicy`, or None for a line that does not cure.
        #: Left None by default because CCS manual §4.6.12 says resting is a
        #: non-standard feature normally set to 0 — so no policy is the
        #: shipped behaviour, and a policy is something somebody configures.
        self.curing = None

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

        #: Calls handed back and fully acknowledged by the machine. Each one
        #: is a station now alarmed and waiting for a person, so this is not a
        #: number that should grow quietly.
        self.cancellations_done = 0

        self.created = 0
        #: Jobs created with no caller, to clear stranded material.
        self.diverted = 0
        #: DISTINCT calls heard but not turned into jobs — because the source
        #: had nothing to give, or the destination leg is at its ceiling.
        #:
        #: COUNTED ONCE PER CALL, NOT ONCE PER POLL. `poll_calls()` returns the
        #: latched outstanding calls, so the same call comes back every pass
        #: until it is acknowledged. Incrementing per pass made this a rate
        #: integrated over wall-clock — measured at ~1/s per unservable call,
        #: reaching 759 in six minutes — which `ui/health.py` then compared
        #: against a cumulative job count. See ADR 2026-08-20.
        self.deferred = 0
        #: Calls that cannot be served RIGHT NOW. A gauge, not a total: this is
        #: the number that says whether the line is behind at this instant.
        self.deferred_now = 0
        #: Keys of the calls deferred on the previous pass, so a call already
        #: counted is not counted again while it stays outstanding.
        self._deferred_keys = set()

        #: LineCapacity, or None. None disables the ceiling entirely, so every
        #: existing caller behaves exactly as before — the same opt-in shape as
        #: `divert_for` and `return_for` above.
        self.capacity = None
        #: callable(station_id) -> leg name, needed only when `capacity` is set.
        self.leg_of = None
        #: Calls deferred specifically because their leg was at its ceiling,
        #: counted apart from "nothing to supply". The two have opposite cures:
        #: one is a supply problem upstream, the other is this line being full.
        self.at_ceiling = 0

    def _claim_material(self, location, kind, at, wants=None):
        """The material being collected from `location` — found, or minted.

        CLAIM BEFORE MINTING. Registering unconditionally would hand a roll a
        new LOT id at every hop, so one roll making three hops would be three
        unrelated records and "where has this roll been" — the traceability
        B4 exists for — could not be answered at all.

        `ready_materials` is FIFO by `created_at`, which IS specification A2
        and manual §3.1's rule ("the oldest matching material that has finished
        resting"). It has existed since location management landed and the
        running system has never called it, because nothing ever claimed
        material. Same for `unrested_decisions`, which counts how often we
        accepted material whose resting state we do not know: it read 0 not
        because we never guessed, but because we never chose.

        TWO THINGS DISQUALIFY A CANDIDATE, and a live run on 2026-08-20 found
        both by handing one LOT id to three different jobs:

        * **The wrong KIND.** `ready_materials` answers "what is here", not
          "what is here that I can carry". A bobbin-return job at a gravure
          claimed the roll that had just been delivered to it, so an empty core
          travelled back upstream wearing the roll's identity.
        * **Already spoken for.** Two jobs collecting from the same place both
          claimed the same material, because nothing recorded that the first
          one had taken it. Only one robot can carry it.

        Returns `(material_ref, needs_turn)`. `needs_turn` is §1.3's escape
        hatch: the face matched and the winding did not, and a 180° turn of the
        pallet fixes it. It is decided HERE because this is the only moment
        both halves are known — what we have and what the destination wants.

        Returns None only when there is nothing and nothing may be minted —
        never a reason to refuse the job. See ADR 2026-08-20, D5.
        """
        records = self.store.records
        taken = {r.job.material_ref for r in self.store.active
                 if r.job.material_ref}
        available = [m for m in records.ready_materials(location, at)
                     if m.kind == kind and m.material_ref not in taken]

        # §1.3's MATCH, and the escape hatch that goes with it.
        #
        # The face must match; the winding need not, because a 180° turn of the
        # pallet fixes it and that turn is a task. So candidates are tried in
        # two passes: exact first, then rotatable. Preferring exact is not
        # fussiness — a turn is a real task with a real cost, and taking the
        # rotatable one while an exact one sits beside it buys nothing.
        #
        # With no requirement configured, `wants` is None and this falls
        # through to the first available candidate — which is what the code did
        # before and is still right for a station nobody has configured.
        if wants is not None:
            for m in available:
                if attribute_matches(m.attribute, wants):
                    if m.attribute is wants:
                        return m.material_ref, False
            for m in available:
                if needs_rotation(m.attribute, wants):
                    return m.material_ref, True

        for material in available:
            return material.material_ref, False
        # DESCRIBE IT AT BIRTH. A roll minted with a LOT id and nothing else
        # is a roll nobody can name, and CCS manual §1.3 refuses to feed a
        # machine from an area holding material whose type and attribute are
        # not recorded — so undescribed material makes that rule permanently
        # answer "no" rather than ever being exercised.
        #
        # `profile` is None by default, which mints exactly as before. The
        # simulator sets one; a real line gets it from machine configuration
        # (§4.6.5) or from the PDA supplement.
        described = self.profile.describe(location, kind) if self.profile else {}
        material = records.register_material(kind=kind, at=at,
                                             location=location, **described)
        # Newly minted material is described by the station's own profile, so
        # whether it needs turning is the same question asked of a fresh roll.
        return material.material_ref, needs_rotation(material.attribute, wants)

    def _call_key(self, call):
        """Identity of a call across polls.

        A station has at most one outstanding call per task type — the store's
        station latch guarantees it — so this pair is stable and unique for as
        long as the call is latched.
        """
        return (call.station_id, call.task_type)

    def _leg_in_flight(self):
        """Committed work per leg: active jobs plus material on its racks.

        The manual's second term — material at turntable entrances — has no
        analogue in our model and is deliberately not approximated. See
        `debt-119`.
        """
        counts = {}
        for record in self.store.active:
            leg = self.leg_of(record.job.to_station)
            if leg is not None:
                counts[leg] = counts.get(leg, 0) + 1
        return counts

    async def step(self):
        deferred_now = set()

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
                if self._return_bobbin(call, deferred_into=deferred_now):
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
                deferred_now.add(self._call_key(call))
                continue

            # THE LINE IS FULL. CCS manual §2.15: stop posting to a line whose
            # committed work has reached its ceiling. The call is left
            # outstanding and NOT acknowledged, exactly as an unservable one is
            # — the machine keeps asking, and the work resumes the moment the
            # leg drains. Acknowledging here would be the silent drop this
            # layer exists to prevent.
            if self.capacity is not None and self.leg_of is not None:
                leg = self.leg_of(call.station_id)
                if leg is not None:
                    committed = self._leg_in_flight().get(leg, 0)
                    if not self.capacity.has_room(leg, committed):
                        key = self._call_key(call)
                        if key not in self._deferred_keys:
                            self.at_ceiling += 1
                        deferred_now.add(key)
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
            # THE JOB NAMES WHAT IT IS CARRYING. Without this the material
            # moving through the plant has no identity, so B1-B4 answer
            # nothing and `move_material` on DONE never fires.
            # WHAT THE DESTINATION WANTS. §4.6.5 puts the required attribute
            # in machine configuration and §1.3 reads it back before feeding.
            # None where nothing is configured, which takes the first
            # available candidate exactly as before.
            wants = (self.profile.requires(call.station_id)
                     if self.profile else None)
            material_ref, turn = self._claim_material(
                source, "roll", self.store.clock(), wants=wants)
            job = self.store.create(source, call.station_id,
                                    task_type=call.task_type,
                                    call_id=recorded.call_id,
                                    material_ref=material_ref,
                                    rotate=turn,
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

        # COUNT THE NEWLY DEFERRED, NOT THE STILL-DEFERRED. A call that has
        # been outstanding for a minute is one deferred call, not sixty.
        self.deferred += len(deferred_now - self._deferred_keys)
        self._deferred_keys = deferred_now
        self.deferred_now = len(deferred_now)

        self._divert_stranded()
        self._resolve_commands()
        self._resolve_cancellations()
        self._sync_station_map()

    def _resolve_cancellations(self):
        """Advance the four-step cancellation for every call we gave back.

        Steps 2, 3 and 5 belong to the machine and arrive whenever it gets to
        them, so this has to run every tick — the handshake cannot be finished
        by the code that started it.

        A stranded cancellation is logged EVERY tick on purpose. It means we
        told a machine we were not coming and it has not heard us, so material
        is standing at a station that still expects a robot. That is not a
        thing to mention once.
        """
        equipment = self.store.equipment
        if not hasattr(equipment, "resolve_cancellations"):
            return
        finished, stranded = equipment.resolve_cancellations(self.store.clock())
        for cancel in finished:
            self.cancellations_done += 1
            self.store.logger(
                f"[{cancel.station}] cancellation complete for "
                f"{cancel.job_id} — the machine has the task back")
        for cancel in stranded:
            self.store.logger(
                f"[{cancel.station}] cancellation NOT acknowledged for "
                f"{cancel.job_id} — the machine still expects a robot")

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

    def _return_bobbin(self, call, deferred_into=None):
        """Send this station's empty bobbin back up the process route.

        Returns True if a job was created. A False here leaves the call
        OUTSTANDING and unacknowledged on purpose: telling the machine it was
        heard and then not moving the bobbin is the silent failure this layer
        exists to avoid, and the machine will keep asking until it is served.

        :param deferred_into: set to record this call's key in when it could
            not be served. Passed in rather than counted here so that a call
            outstanding across many polls is counted once — see `step`.

        A REFUSED STATION CLAIM IS NOT A DEFERRAL. It means a job for this
        station is already under way, which is the latch working, not the line
        falling behind.
        """
        destination = self.return_for(call.station_id)
        if destination is None:
            # Not a station that hands bobbins back — the ASRS and the racks do
            # not. A call here means our route table and the machine disagree,
            # which is worth seeing rather than swallowing.
            if deferred_into is not None:
                deferred_into.add(self._call_key(call))
            self.store.logger(
                f"[{call.station_id}] unload call, but no bobbin return route")
            return False

        if not self._can_accept(destination):
            if deferred_into is not None:
                deferred_into.add(self._call_key(call))
            return False

        if not self.store.claim_station(call.station_id):
            return False

        recorded = self.store.records.add_call(
            station=call.station_id,
            task_type=call.task_type,
            source=call.source,
            raised_at=self.store.clock(),
        )
        # An empty core is a tracked object in their model too — the return
        # flow is specified in pallets carrying DOUBLE empty bobbins (§1.2.2)
        # and `TrayStatus` tells them apart from material.
        # No `wants`: a bobbin is a bare core with no face, so there is
        # nothing for §1.3 to match and nothing a turn could fix.
        material_ref, _turn = self._claim_material(call.station_id, "bobbin",
                                                   self.store.clock())
        job = self.store.create(call.station_id, destination,
                                task_type=call.task_type,
                                carries=Carried.BOBBIN,
                                call_id=recorded.call_id,
                                material_ref=material_ref,
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
                # A RACK OUT OF SERVICE IS NOT SOMEWHERE TO PUT ANYTHING.
                # CCS manual §1.2.1.1 rule 3 requires the buffer rack to have
                # "no abnormality", and §2.2 has four separate ways a rack can
                # be unavailable to the automatic flow. `_can_accept` asks the
                # equipment whether the port is physically free; this asks
                # whether CCS is allowed to use it, which is a different
                # question and was not being asked at all.
                port = next((b for b in seg["buffer"]
                             if self._can_accept(b)
                             and self.store.records.rack_usable(b)
                             and not self.store.station_claimed(b)), None)
                if port is None:
                    continue                      # rack full too — nothing to do
                if not self.store.claim_station(port):
                    continue
                # THE ONE JOB WITH NO CALLER, so no call_id — which is
                # exactly what makes it identifiable later.
                # THE MATERIAL GETS AN IDENTITY HERE, because this is where
                # it stops being "whatever the machine had" and starts being a
                # thing sitting on a rack that somebody will later ask for by
                # name. The rack is also where the customer's own system keeps
                # carrier identity — it vanishes at an equipment station and
                # persists at the buffer.
                now = self.store.clock()
                # Through the same helper as every other path: a stranded roll
                # that was already known keeps its identity instead of
                # acquiring a second one.
                # No `wants`: a buffer rack holds material, it does not
                # require a particular attribute. The turn is decided when the
                # material later leaves for a machine.
                material_ref, _turn = self._claim_material(source, "roll", now)
                job = self.store.create(
                    source, port,
                    reason=f"every destination of segment {seg['name']} was "
                           f"full",
                    material_ref=material_ref)
                # WHAT THE RACK NOW HOLDS. CCS manual §4.6.6: completing a
                # task writes the carried material type, attribute and bobbin
                # type into the target rack. §1.3 then reads it back and
                # refuses to feed a machine from an area holding material it
                # cannot name — so a rack that does not record this is a rack
                # that quietly blocks its own machine.
                known = self.store.records.material(material_ref)
                self.store.records.park(
                    port, material_ref=material_ref,
                    job_id=job.job.job_id, at=now,
                    material_type=getattr(known, "material_type", None),
                    material_attribute=getattr(known, "attribute", None),
                    bobbin_type=getattr(known, "drum_type", None))

                # AND THE CURING CLOCK STARTS HERE, if this place cures.
                #
                # `begin_curing` is idempotent, which is the whole reason it
                # can be called from a divert: [HB] §3 says material routed
                # elsewhere "must not cure twice", and a roll that arrives here
                # having already rested somewhere else keeps its original
                # start. Calling it is therefore always safe; not calling it is
                # what loses the obligation.
                seconds = self.curing.seconds_for(port) if self.curing else None
                if seconds:
                    self.store.records.begin_curing(material_ref, now, seconds)
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
