"""EquipmentMonitorTask — "is the material actually ready at source?"

The first box on the whiteboard. It polls the production machines and turns
finished batches into transport jobs. It decides nothing about robots, routes or
timing; it only notices that work exists.

Polling rather than waiting on an event, deliberately. The equipment protocol is
still unknown (blocked on CATL), and a poll is the one interaction every
industrial protocol supports — Modbus has no notion of a subscription at all. If
the real protocol turns out to push, the adapter can absorb that and this task
keeps its shape.

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
