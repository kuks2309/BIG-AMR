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

        self.created = 0
        #: Calls heard but not turned into jobs, because the source had nothing
        #: to give. Worth counting separately: a rising number here is a supply
        #: problem upstream, not a fault in this layer.
        self.deferred = 0

    async def step(self):
        for call in self.store.equipment.poll_calls():
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

            self.store.create(source, call.station_id,
                              task_type=call.task_type)
            self.created += 1

            # Heard. The machine stops calling now, and only now.
            self.store.equipment.acknowledge_call(call)
            self.store.logger(
                f"[{call.station_id}] call heard via {call.source} "
                f"({call.task_type.name.lower()}) — source {source}")

            for task in self.wakes:
                task.notify()

    def _can_supply(self, station_id):
        """Can this place actually hand something over right now?

        BUSY is the one worth stating: a machine that is processing HOLDS
        material but cannot give it. Treating held and available as the same
        thing sends a robot to collect something that does not exist yet.
        """
        return (self.store.equipment.get_station_status(station_id)
                is StationStatus.FINISHED)
