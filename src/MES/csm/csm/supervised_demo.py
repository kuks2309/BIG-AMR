"""supervised_demo — the three FSMs under the real Supervisor, on real timers.

    ros2 run csm supervised_demo
    python3 -m csm.supervised_demo --seconds 30 --robots 1

`demo` runs the same factory through `MainCycle`: one thread, one tick, an
injected clock, everything in order. It stays as the reference — it is what
makes the job FSM's behaviour easy to reason about and easy to test.

This runs the system the way the whiteboard draws it: a supervisor holding a
list of independent state machines, each waking on its own period or when
another notifies it, on wall-clock asyncio timers. Watching both is the point.
The tick counts printed at the end are the visible difference — the three
machines run at genuinely different rates, which a single loop cannot do.

The fake factory is itself an FsmTask, so it needs no special handling: it is
registered like anything else and stops like anything else.
"""

import argparse
import asyncio
import time

from .adapters.base import StationStatus, TaskType, TransportResult
from .adapters.mock import MockEquipment
from .runtime import FsmTask, build_mes

STATIONS = ["ASRS", "1A01", "1T01", "1L01"]

#: Who feeds whom. A call says who WANTS material, never where it comes from.
FEEDS = {"1A01": "ASRS", "1T01": "1A01", "1L01": "1T01"}


class FakeFleet:
    """An ACS with a fixed number of robots, on wall-clock time.

    MockAcs accepts everything; this refuses once its robots are busy, which is
    what makes the dispatcher's queueing visible.
    """

    def __init__(self, robots=1, travel_seconds=3.0):
        self.capacity = robots
        self.travel = travel_seconds
        self._arrive_at = {}
        self.busy_answers = 0
        self.submissions = 0

    def submit_job(self, job):
        self.submissions += 1
        if len(self._arrive_at) >= self.capacity:
            self.busy_answers += 1
            return TransportResult.BUSY
        self._arrive_at[job.job_id] = time.monotonic() + self.travel
        return TransportResult.ACCEPTED

    def get_job_result(self, job_id):
        arrive_at = self._arrive_at.get(job_id)
        if arrive_at is None:
            return TransportResult.UNKNOWN
        if time.monotonic() >= arrive_at:
            del self._arrive_at[job_id]
            return TransportResult.ARRIVED
        return TransportResult.IN_PROGRESS

    def cancel_job(self, job_id):
        self._arrive_at.pop(job_id, None)
        return True


class FactoryTask(FsmTask):
    """The machines finishing batches. An FsmTask like everything else."""

    name = "factory"

    def __init__(self, equipment, period):
        super().__init__(period=period)
        self.equipment = equipment
        self.producers = list(FEEDS)
        self._next = 0
        self.batches = 0

    async def step(self):
        """A machine asks for material — the way work actually starts.

        The supply chain is kept stocked so the calls can be served; this demo
        is about the queueing, not about the line filling up.
        """
        station = self.producers[self._next % len(self.producers)]
        self._next += 1
        for sid in STATIONS:
            self.equipment.force_status(sid, StationStatus.FINISHED)
        self.equipment.raise_call(station, TaskType.LOAD, source="PDA")
        self.batches += 1
        print(f"  ── {station} called for material (PDA)")


class StopAfter(FsmTask):
    """Ends the run. A deadline is a periodic condition, so it is a task too."""

    name = "deadline"

    def __init__(self, supervisor, seconds):
        super().__init__(period=0.2)
        self.supervisor = supervisor
        self.deadline = None
        self.seconds = seconds

    async def on_start(self):
        self.deadline = time.monotonic() + self.seconds

    async def step(self):
        if time.monotonic() >= self.deadline:
            self.supervisor.request_stop()


async def run(seconds, robots, batch_seconds, travel):
    equipment = MockEquipment(STATIONS, time.monotonic)
    fleet = FakeFleet(robots=robots, travel_seconds=travel)

    app = build_mes(equipment, fleet,
                    source_for=lambda sid: FEEDS.get(sid, "ASRS"),
                    clock=time.monotonic,
                    logger=lambda m: print(f"  {m}"))

    app.supervisor.register(FactoryTask(equipment, period=batch_seconds))
    app.supervisor.register(StopAfter(app.supervisor, seconds))

    print("=" * 70)
    print(f"CSM under the Supervisor — {robots} robot(s), "
          f"a batch every {batch_seconds:.0f}s, {seconds:.0f}s run")
    print("=" * 70)

    health = await app.supervisor.run(install_signal_handlers=False)

    print("\n" + "=" * 70)
    print("per-FSM ticks — the three MES machines run at different rates,")
    print("which is the thing a single loop cannot do")
    for name, h in health.items():
        errors = f"  {h['errors']} errors" if h["errors"] else ""
        print(f"  {name:<20} {h['ticks']:>6} ticks{errors}")

    jobs = app.health()
    print(f"\njobs created {jobs['created']}   granted {jobs['granted']}   "
          f"completed {jobs['completed']}   failed {jobs['failed']}   "
          f"still active {jobs['jobs_active']}")
    print(f"ACS  submissions {fleet.submissions}   answered BUSY "
          f"{fleet.busy_answers}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="CSM under the real Supervisor")
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--robots", type=int, default=1,
                        help="fleet size — 1 makes the queueing obvious")
    parser.add_argument("--batch-seconds", type=float, default=2.0,
                        help="how often a machine finishes a batch")
    parser.add_argument("--travel", type=float, default=3.0,
                        help="how long a transport takes")
    args = parser.parse_args()

    try:
        asyncio.run(run(args.seconds, args.robots, args.batch_seconds,
                        args.travel))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
