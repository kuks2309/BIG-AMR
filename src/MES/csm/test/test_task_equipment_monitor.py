"""Tests for EquipmentMonitorTask.

Rewritten 2026-08-04 for the corrected direction. The old tests asserted
"a station reports FINISHED, therefore a job exists", which is backwards: the
equipment CALLS, and a machine having material is a separate fact that decides
whether a call can be *served*, not whether one was made.

step() is driven directly, no supervisor and no timers — production drives it
from the run loop, tests drive it by hand.
"""

import asyncio
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters.base import StationStatus, TaskType             # noqa: E402
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment  # noqa: E402
from csm.runtime.job_store import JobStore                        # noqa: E402
from csm.runtime.tasks import EquipmentMonitorTask                # noqa: E402

#: Who feeds whom. The call says who WANTS material; this says where it is.
FEEDS = {"1A01": "ASRS", "1T01": "1A01", "1L01": "1T01"}


def build():
    clock = ManualClock()
    equipment = MockEquipment(["ASRS", "1A01", "1T01", "1L01"], clock)
    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True)
    monitor = EquipmentMonitorTask(store, source_for=lambda s: FEEDS.get(s, "ASRS"))
    return clock, equipment, store, monitor


def step(task):
    asyncio.run(task.step())


def supply(equipment, *station_ids):
    """Give these places something available to hand over."""
    for sid in station_ids:
        equipment.force_status(sid, StationStatus.FINISHED)


class Spy:
    def __init__(self):
        self.woken = 0

    def notify(self):
        self.woken += 1


# ------------------------------------------------------- the direction itself

def test_a_call_creates_a_job_toward_the_caller():
    """The caller is the DESTINATION. It is asking for material to come TO it."""
    _, equipment, store, monitor = build()
    supply(equipment, "ASRS")
    equipment.raise_call("1A01", TaskType.LOAD)

    step(monitor)

    assert monitor.created == 1
    job = store.active[0].job
    assert job.to_station == "1A01", "the machine that called must be the destination"
    assert job.from_station == "ASRS", "material comes from whatever feeds it"
    assert job.task_type is TaskType.LOAD


def test_material_alone_creates_nothing():
    """The old behaviour, now explicitly forbidden.

    A station full of material is not a request. Somebody has to ask.
    """
    _, equipment, store, monitor = build()
    supply(equipment, "ASRS", "1A01", "1T01", "1L01")

    for _ in range(10):
        step(monitor)

    assert monitor.created == 0
    assert store.active == []


def test_a_pda_call_is_the_same_as_a_machine_call():
    """A person with a handheld and a button on the machine are equivalent."""
    _, equipment, store, monitor = build()
    supply(equipment, "ASRS")
    equipment.raise_call("1A01", TaskType.LOAD, source="PDA")

    step(monitor)

    assert monitor.created == 1


def test_the_task_type_reaches_the_job():
    _, equipment, store, monitor = build()
    supply(equipment, "1A01")
    equipment.raise_call("1T01", TaskType.SWAP)

    step(monitor)

    assert store.active[0].job.task_type is TaskType.SWAP


# ------------------------------------------------- acknowledgement and latching

def test_a_call_is_acknowledged_only_once_it_becomes_a_job():
    """Acknowledging says 'heard'. Saying it before acting would let the machine
    stop asking for something that never happened."""
    _, equipment, store, monitor = build()
    supply(equipment, "ASRS")
    equipment.raise_call("1A01", TaskType.LOAD)

    assert equipment.acknowledged == []
    step(monitor)
    assert [s for _, s in equipment.acknowledged] == ["1A01"]
    assert equipment.poll_calls() == [], "acknowledged calls must stop being reported"


def test_one_call_produces_one_job_however_often_it_is_polled():
    _, equipment, store, monitor = build()
    supply(equipment, "ASRS")
    equipment.raise_call("1A01", TaskType.LOAD)

    for _ in range(10):
        step(monitor)

    assert monitor.created == 1


def test_an_unservable_call_is_kept_not_acknowledged():
    """The failure this layer must not have.

    A call we cannot serve yet stays outstanding. Acknowledging it would tell
    the machine it had been heard and then drop the request — a silently lost
    job, with nothing anywhere reporting a problem.
    """
    _, equipment, store, monitor = build()
    equipment.raise_call("1T01", TaskType.LOAD)      # source 1A01 has nothing

    for _ in range(5):
        step(monitor)

    assert monitor.created == 0
    # ONE CALL DEFERRED FIVE TIMES IS ONE DEFERRED CALL, NOT FIVE.
    #
    # This assertion used to read `== 5`, which encoded the defect rather than
    # the requirement: `poll_calls()` re-returns the latched call every pass, so
    # the counter was really counting polls. At 1 Hz that made it a rate, and
    # the dashboard compared it against a job count — see ADR 2026-08-20.
    assert monitor.deferred == 1
    assert monitor.deferred_now == 1, "still outstanding, so still deferred now"
    assert equipment.acknowledged == [], "acknowledged a call it did not serve"
    assert len(equipment.poll_calls()) == 1, "the call must still be outstanding"

    # Once the source can supply, the same call is served.
    supply(equipment, "1A01")
    step(monitor)
    assert monitor.created == 1


def test_a_processing_machine_cannot_supply():
    """BUSY holds material but cannot give it. A machine handed a raw roll has
    nothing to hand on until it has finished working."""
    clock, equipment, store, monitor = build()
    equipment.start_processing("1A01", seconds=5.0)
    equipment.raise_call("1T01", TaskType.LOAD)

    step(monitor)
    assert monitor.created == 0, "collected from a machine that was still working"

    clock.advance(6.0)
    step(monitor)
    assert monitor.created == 1


# --------------------------------------------------------------- bookkeeping

def test_several_machines_calling_at_once_all_get_jobs():
    _, equipment, store, monitor = build()
    supply(equipment, "ASRS", "1A01")
    equipment.raise_call("1A01", TaskType.LOAD)
    equipment.raise_call("1T01", TaskType.LOAD)

    step(monitor)

    assert monitor.created == 2
    assert {r.job.to_station for r in store.active} == {"1A01", "1T01"}


def test_a_station_with_a_job_in_flight_does_not_get_a_second():
    _, equipment, store, monitor = build()
    supply(equipment, "ASRS")
    equipment.raise_call("1A01", TaskType.LOAD)
    step(monitor)

    equipment.raise_call("1A01", TaskType.LOAD)      # calls again while working
    step(monitor)

    assert monitor.created == 1


# ------------------------------------------------------------------- waking

def test_listeners_are_woken_when_a_job_is_created():
    _, equipment, _, monitor = build()
    spy = Spy()
    monitor.wakes.append(spy)
    supply(equipment, "ASRS")
    equipment.raise_call("1A01", TaskType.LOAD)

    step(monitor)

    assert spy.woken == 1


def test_listeners_are_not_woken_when_nobody_called():
    """A quiet factory must not wake the rest of the system once a second."""
    _, equipment, _, monitor = build()
    spy = Spy()
    monitor.wakes.append(spy)
    supply(equipment, "ASRS", "1A01")

    for _ in range(5):
        step(monitor)

    assert spy.woken == 0


def test_the_monitor_does_not_import_its_listeners():
    """Wiring is injected. A monitor that knew what a dispatcher was would be
    the first crack in the separation the supervisor exists to enforce."""
    import csm.runtime.tasks.equipment_monitor as mod

    source = pathlib.Path(mod.__file__).read_text()
    assert "Dispatcher" not in source
    assert "JobTracker" not in source
