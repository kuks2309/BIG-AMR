"""Tests for EquipmentMonitorTask.

step() is driven directly, with no supervisor and no event loop beyond
asyncio.run. That is the testability rule from fsm_task.py: production drives
step() from the run loop, tests drive it by hand.
"""

import asyncio
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from mini_mes.adapters.base import StationStatus                  # noqa: E402
from mini_mes.adapters.mock import ManualClock, MockAcs, MockEquipment  # noqa: E402
from mini_mes.runtime.job_store import JobStore                   # noqa: E402
from mini_mes.runtime.tasks import EquipmentMonitorTask           # noqa: E402

ROUTE = {"station_3": "station_5", "station_5": "station_9"}


def build():
    clock = ManualClock()
    equipment = MockEquipment(["station_3", "station_5", "station_9"], clock)
    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True)
    monitor = EquipmentMonitorTask(
        store, route=lambda sid: ROUTE.get(sid, "station_9"))
    return clock, equipment, store, monitor


def step(task):
    asyncio.run(task.step())


class Spy:
    """Records notify() calls without being an FsmTask."""

    def __init__(self):
        self.woken = 0

    def notify(self):
        self.woken += 1


# --------------------------------------------------------------- job creation

def test_a_finished_station_becomes_a_job():
    _, equipment, store, monitor = build()
    equipment.force_status("station_3", StationStatus.FINISHED)

    step(monitor)

    assert monitor.created == 1
    assert len(store.active) == 1
    job = store.active[0].job
    assert job.from_station == "station_3"
    assert job.to_station == "station_5"      # the route, not a default sink


def test_an_idle_factory_creates_nothing():
    _, _, store, monitor = build()
    for _ in range(5):
        step(monitor)
    assert monitor.created == 0
    assert store.active == []


def test_a_station_left_finished_produces_only_one_job():
    """Polling repeatedly must not spawn a job per poll."""
    _, equipment, store, monitor = build()
    equipment.force_status("station_3", StationStatus.FINISHED)

    for _ in range(10):
        step(monitor)

    assert monitor.created == 1


def test_several_stations_finishing_at_once_all_get_jobs():
    _, equipment, store, monitor = build()
    equipment.force_status("station_3", StationStatus.FINISHED)
    equipment.force_status("station_5", StationStatus.FINISHED)

    step(monitor)

    assert monitor.created == 2
    assert {r.job.from_station for r in store.active} == {"station_3", "station_5"}


def test_the_route_decides_the_destination():
    """A real line is a process route, not everything piling into one place."""
    _, equipment, store, monitor = build()
    equipment.force_status("station_5", StationStatus.FINISHED)

    step(monitor)

    assert store.active[0].job.to_station == "station_9"


# ------------------------------------------------------------------- waking

def test_listeners_are_woken_when_a_job_is_created():
    _, equipment, _, monitor = build()
    spy = Spy()
    monitor.wakes.append(spy)

    equipment.force_status("station_3", StationStatus.FINISHED)
    step(monitor)

    assert spy.woken == 1


def test_listeners_are_not_woken_when_nothing_happened():
    """An idle factory must not wake the rest of the system once a second."""
    _, _, _, monitor = build()
    spy = Spy()
    monitor.wakes.append(spy)

    for _ in range(5):
        step(monitor)

    assert spy.woken == 0


def test_the_monitor_does_not_import_its_listeners():
    """Wiring is injected. A monitor that knew what a dispatcher was would be
    the first crack in the separation the supervisor exists to enforce."""
    import mini_mes.runtime.tasks.equipment_monitor as mod

    source = pathlib.Path(mod.__file__).read_text()
    assert "Dispatcher" not in source
    assert "JobTracker" not in source
