"""build_mes — the one place the three FSMs are wired together.

    equipment ─┐
               ├─► JobStore ◄── all three tasks share this
    acs       ─┘

    EquipmentMonitorTask ──notify──► DispatcherTask ──notify──► JobTrackerTask
              ▲                                                      │
              └──────────────────── notify ──────────────────────────┘
                                (a retirement freed capacity)

Wiring lives here rather than in any task because no task should know what the
others are. Each takes a `wakes` list and calls `notify()` on whatever is in it;
only this function knows the shape of the graph. That is what keeps the
Supervisor's promise real — the system is extended by registering another
machine, not by editing the ones that already exist.

Usage:

    app = build_mes(equipment, acs, route=lambda s: ROUTE.get(s, "station_out"))
    asyncio.run(app.supervisor.run())

Or, when something else already owns the loop (a ROS 2 node, for instance), call
`app.tick_all()` from that loop instead and never start the supervisor at all.
Both drive the same three step() methods.
"""

import time

from .job_store import JobStore
from .supervisor import Supervisor
from .tasks import DispatcherTask, EquipmentMonitorTask, JobTrackerTask


class MesApp:
    """The assembled system: a store, three FSMs, and a supervisor over them."""

    def __init__(self, store, monitor, dispatcher, tracker, supervisor):
        self.store = store
        self.monitor = monitor
        self.dispatcher = dispatcher
        self.tracker = tracker
        self.supervisor = supervisor

    @property
    def tasks(self):
        return (self.monitor, self.dispatcher, self.tracker)

    async def tick_all(self):
        """Step all three once, in order, without the supervisor.

        For a host that already owns a loop — a ROS 2 node's timer, or a test.
        The order matters and is the same one MainCycle uses: notice new work,
        decide whose turn it is, then move the jobs. Any other order costs a
        full cycle of latency per job for no benefit.

        Errors are not swallowed here. Under the supervisor a crashing FSM is
        isolated and recorded; a caller driving the steps itself should see the
        exception rather than have it silently absorbed by a helper.
        """
        for task in self.tasks:
            await task.step()

    def health(self):
        return {
            "jobs_active": len(self.store.active),
            "jobs_finished": len(self.store.finished),
            "created": self.monitor.created,
            "granted": self.dispatcher.granted,
            "completed": self.tracker.completed,
            "failed": self.tracker.failed,
            "stations_busy": sorted(self.store.station_busy),
        }

    def __repr__(self):
        return f"<MesApp {self.health()}>"


def build_mes(equipment, acs, source_for, clock=time.monotonic, logger=print,
              job_timeout_s=600.0, poll_seconds=None, install_supervisor=True):
    """Assemble the Mini MES.

    :param equipment: EquipmentAdapter — mock, or the CATL one when it exists
    :param acs:       AcsAdapter — mock, SimAcs, or the real fleet controller
    :param source_for: callable(station_id) -> the station that FEEDS it.
        Note the direction. A machine calls for material to be brought TO it,
        so what we need to know is where that material comes from — not where
        this machine's output goes next.
    :param poll_seconds: optional {task_name: period} override. Only for hosts
        with a good reason — a simulation running faster than real time, say.
    :param install_supervisor: False builds the tasks without one, for a host
        that drives tick_all() from its own loop.

    The store is created **gated**: a job may not submit itself, because a
    DispatcherTask is present to decide the order. That is the difference from
    MainCycle, which is ungated and lets each job ask for itself.
    """
    store = JobStore(equipment, acs, clock, logger=logger,
                     job_timeout_s=job_timeout_s, dispatch_gated=True)

    periods = poll_seconds or {}
    monitor = EquipmentMonitorTask(store, source_for=source_for,
                                   period=periods.get("equipment_monitor"))
    dispatcher = DispatcherTask(store, period=periods.get("dispatcher"))
    tracker = JobTrackerTask(store, period=periods.get("job_tracker"))

    # The graph. Appended after construction because it has a cycle — the
    # tracker tells the dispatcher that capacity came back, and the dispatcher
    # tells the tracker to move the job it just granted.
    monitor.wakes.extend([dispatcher, tracker])
    dispatcher.wakes.append(tracker)
    tracker.wakes.append(dispatcher)

    supervisor = None
    if install_supervisor:
        supervisor = Supervisor(logger=logger)
        for task in (monitor, dispatcher, tracker):
            supervisor.register(task)

    return MesApp(store, monitor, dispatcher, tracker, supervisor)
