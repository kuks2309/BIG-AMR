"""EquipmentMonitorTask — "is the material actually ready at source?"

The first box on the whiteboard. It polls the production machines and turns
finished batches into transport jobs. It decides nothing about robots, routes or
timing; it only notices that work exists.

Polling rather than waiting on an event, deliberately. The equipment protocol is
unknown when this was written, and a poll is the one interaction every
industrial protocol supports — Modbus has no notion of a subscription at all.

⚠ **The specification arrived on 2026-08-04 and polling is not sufficient.** A
machine requests a robot by *changing* a value: the request is the transition
itself, and the machine clears the signal once it believes it was heard. A
sampler misses any change that reverts between two samples, while the machine
believes the call succeeded — a silently dropped job, which is the worst failure
mode this layer has.

**Correction, 2026-08-04.** An earlier version of this note said subscriptions
were the fix. They are not. Asked directly in the system review, the answer was
that the equipment interface is *not* event-driven at all — both sides call each
other by raising bits, and CSM is expected to scan continuously at a fixed
interval. So polling is the specified design, not a shortcut.

What remains wrong is the **interval**, and it is now the entire safety margin:
a request is a transition, and the machine clears it once it believes it was
heard. 1 Hz here is an unjustified default. The number that decides it is the
equipment's minimum signal hold time, which nobody has yet — until we do, treat
this task as correct against the mock and unproven against the real protocol.
See debt-033.

One second is not a considered number so much as an obviously-safe one: a
station takes minutes to finish a batch, so a second of latency is invisible,
and one request per station per second is nothing to a PLC.
"""

from ..fsm_task import FsmTask


class EquipmentMonitorTask(FsmTask):

    name = "equipment_monitor"
    period = 1.0

    def __init__(self, store, route, wakes=None, name=None, period=None):
        """
        :param store: the shared JobStore
        :param route: callable(station_id) -> destination station_id. A real
            line is a process route, not everything piling into one place: a
            part finishes at one machine and moves to the next operation.
        :param wakes: FsmTasks to notify when a job is created. Wired by the
            application, not known here — this task must not learn who its
            listeners are.
        """
        super().__init__(name=name, period=period)
        self.store = store
        self.route = route
        self.wakes = list(wakes or [])

        #: Jobs this task has created. Cheap health signal: a monitor with zero
        #: created jobs and a factory that is producing means something is wrong
        #: between them.
        self.created = 0

    async def step(self):
        for station_id in self.store.find_finished_stations():
            self.store.claim_station(station_id)
            destination = self.route(station_id)
            self.store.create(station_id, destination)
            self.created += 1

            # Wake the others now rather than letting them find it on their own
            # next poll. Both would get there eventually; this removes up to a
            # full poll period of dead time per job, and it is what makes the
            # whiteboard's arrows between the boxes real.
            for task in self.wakes:
                task.notify()
