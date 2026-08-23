"""The §2.15 per-line task ceiling, and honest deferral counting.

Two defects found by running the simulator on 2026-08-20, fixed together
because the second makes the first measurable. See ADR
`docs/adr/2026-08-20-line-task-ceiling-and-deferral-counting.md`.

1. `calls_deferred` counted POLLS, not calls. `poll_calls()` returns the
   latched outstanding calls every pass, so one unservable call incremented the
   counter once per second for as long as it stayed unserved — 759 in six
   minutes. The dashboard then compared that against a cumulative job count and
   warned on every run of any length.

2. Nothing bounded work in flight against a leg. Jobs created outran jobs
   finished for the whole run and the open-call list grew monotonically.
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters.base import StationStatus, TaskType              # noqa: E402
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment   # noqa: E402
from csm.runtime.capacity import LineCapacity                       # noqa: E402
from csm.runtime.job_store import JobStore                          # noqa: E402
from csm.runtime.tasks import (DispatcherTask,                      # noqa: E402
                               EquipmentMonitorTask)

#: Two legs with deliberately different ceilings, so the shortfall test is
#: about the FRACTION and not about the raw count.
SEGMENTS = [
    {"name": "A", "to": ["A_LD1", "A_LD2"], "buffer": ["WIP_A"]},
    {"name": "B", "to": ["B_LD1", "B_LD2"], "buffer": ["WIP_B"]},
]
RACK_SLOTS = {"WIP_A": 1, "WIP_B": 10}
FEEDS = {"A_LD1": "SRC", "A_LD2": "SRC", "B_LD1": "SRC", "B_LD2": "SRC"}
STATIONS = ["SRC", "A_LD1", "A_LD2", "B_LD1", "B_LD2"]


def leg_of(station_id):
    for seg in SEGMENTS:
        if station_id in seg["to"]:
            return seg["name"]
    return None


def capacity(redundancy=0):
    return LineCapacity(SEGMENTS, RACK_SLOTS.get, redundancy=redundancy)


def build(redundancy=0, with_ceiling=True):
    clock = ManualClock()
    equipment = MockEquipment(STATIONS, clock)
    store = JobStore(equipment, MockAcs(clock), clock, logger=lambda m: None,
                     dispatch_gated=True)
    monitor = EquipmentMonitorTask(store,
                                   source_for=lambda s: FEEDS.get(s, "SRC"))
    if with_ceiling:
        monitor.capacity = capacity(redundancy)
        monitor.leg_of = leg_of
    return clock, equipment, store, monitor


def step(task):
    asyncio.run(task.step())


def supply(equipment, *station_ids):
    for sid in station_ids:
        equipment.force_status(sid, StationStatus.FINISHED)


# --------------------------------------------------------------- the formula

def test_ceiling_is_ports_plus_rack_slots_plus_redundancy():
    """CCS manual §2.15, exactly as written."""
    cap = capacity()
    assert cap.ceiling("A") == 2 + 1          # 2 ports, 1 rack slot
    assert cap.ceiling("B") == 2 + 10


def test_redundancy_shifts_the_ceiling_and_may_be_negative():
    """The manual is explicit that a negative keeps a line deliberately short."""
    assert capacity(redundancy=3).ceiling("A") == 6
    assert capacity(redundancy=-2).ceiling("A") == 1


def test_a_ceiling_never_falls_below_one():
    """A leg that may hold no work at all is deadlocked, not throttled."""
    assert capacity(redundancy=-99).ceiling("A") == 1


def test_an_unknown_leg_has_no_ceiling_rather_than_a_zero_one():
    """Refusing to throttle what we cannot measure.

    A ceiling of zero for a leg we simply failed to configure would stop that
    line permanently, and look exactly like the ceiling working.
    """
    cap = capacity()
    assert cap.ceiling("Z") is None
    assert cap.has_room("Z", 10_000) is True


def test_shortfall_is_a_fraction_so_a_small_leg_competes_with_a_big_one():
    """§3.2 — the reason the manual specifies a percentage.

    Leg A holds 1 of 3; leg B holds 4 of 12. Both are a third full, so neither
    outranks the other — an absolute count would have handed it to B every time.
    """
    cap = capacity()
    assert cap.shortfall("A", 1) == cap.shortfall("B", 4)
    # And the more starved leg does win.
    assert cap.shortfall("A", 0) > cap.shortfall("A", 2)


def test_shortfall_of_an_unknown_leg_is_zero_not_one():
    """Unranked, not most urgent — a misconfigured leg must not win every tie."""
    assert capacity().shortfall("Z", 0) == 0.0


# ------------------------------------------------------- deferral is per call

def test_one_call_deferred_many_times_counts_once():
    """The defect this ADR exists for.

    The counter is cumulative over CALLS. Ten polls of one unserved call is one
    deferred call, not ten.
    """
    _, equipment, _, monitor = build()
    equipment.raise_call("A_LD1", TaskType.LOAD)     # SRC has nothing

    for _ in range(10):
        step(monitor)

    assert monitor.deferred == 1
    assert monitor.deferred_now == 1


def test_the_gauge_clears_when_the_call_is_served():
    """`deferred_now` is a gauge — it must come back down."""
    _, equipment, _, monitor = build()
    equipment.raise_call("A_LD1", TaskType.LOAD)
    step(monitor)
    assert monitor.deferred_now == 1

    supply(equipment, "SRC")
    step(monitor)

    assert monitor.created == 1
    assert monitor.deferred_now == 0, "served, so nothing is waiting now"
    assert monitor.deferred == 1, "but it did wait once, and that is history"


def test_a_second_distinct_call_counts_again():
    """Counting once per call must not collapse different calls into one."""
    _, equipment, _, monitor = build()
    equipment.raise_call("A_LD1", TaskType.LOAD)
    step(monitor)
    equipment.raise_call("A_LD2", TaskType.LOAD)
    step(monitor)

    assert monitor.deferred == 2
    assert monitor.deferred_now == 2


# ----------------------------------------------------------- the ceiling bites

def test_a_leg_at_its_ceiling_stops_taking_work():
    """§2.15 — stop posting to a full line."""
    _, equipment, store, monitor = build(redundancy=-2)   # leg A ceiling = 1
    supply(equipment, "SRC")

    equipment.raise_call("A_LD1", TaskType.LOAD)
    step(monitor)
    assert monitor.created == 1, "the first job fits under the ceiling"

    equipment.raise_call("A_LD2", TaskType.LOAD)
    step(monitor)

    assert monitor.created == 1, "the second is refused — the leg is full"
    assert monitor.at_ceiling == 1


def test_a_call_refused_at_the_ceiling_is_never_acknowledged():
    """The property this whole layer exists to preserve.

    Acknowledging tells the machine it was heard. Doing that and then not
    moving anything is a silently lost job with nothing reporting a problem.
    """
    _, equipment, _, monitor = build(redundancy=-2)
    supply(equipment, "SRC")
    equipment.raise_call("A_LD1", TaskType.LOAD)
    step(monitor)
    equipment.raise_call("A_LD2", TaskType.LOAD)
    for _ in range(5):
        step(monitor)

    outstanding = [c.station_id for c in equipment.poll_calls()]
    assert "A_LD2" in outstanding, "the refused call must still be outstanding"
    assert "A_LD2" not in [s for _, s in equipment.acknowledged]
    assert monitor.at_ceiling == 1, "counted once, not once per poll"


def test_a_full_leg_does_not_block_a_different_one():
    """The ceiling is per line. B must keep running while A is full."""
    _, equipment, _, monitor = build(redundancy=-2)      # A ceiling 1, B 10
    supply(equipment, "SRC")

    equipment.raise_call("A_LD1", TaskType.LOAD)
    step(monitor)
    equipment.raise_call("A_LD2", TaskType.LOAD)
    equipment.raise_call("B_LD1", TaskType.LOAD)
    step(monitor)

    assert monitor.created == 2, "B was served even though A was full"


def test_without_a_capacity_there_is_no_ceiling_at_all():
    """The opt-in guarantee: every existing caller behaves exactly as before."""
    _, equipment, _, monitor = build(with_ceiling=False)
    supply(equipment, "SRC")

    for station in ("A_LD1", "A_LD2", "B_LD1", "B_LD2"):
        equipment.raise_call(station, TaskType.LOAD)
    step(monitor)

    assert monitor.created == 4
    assert monitor.at_ceiling == 0


# -------------------------------------------------------- dispatcher ordering

def test_the_dispatcher_prefers_the_more_starved_leg():
    """§3.2, as a tie-break below priority."""
    clock, equipment, store, monitor = build()
    dispatcher = DispatcherTask(store)
    dispatcher.capacity = capacity()
    dispatcher.leg_of = leg_of

    # Ceilings are A=3 and B=12, so the comparison is proportional, not
    # absolute. Load B to 8 of 12 (shortfall 0.33) against A at 1 of 3
    # (shortfall 0.67), and A is the more starved leg.
    #
    # Every B job is created FIRST, so age alone would pick one of them —
    # shortfall is what must override that.
    for _ in range(8):
        store.create("SRC", "B_LD1")
        clock.advance(1)
    store.create("SRC", "A_LD1")

    step(dispatcher)

    granted = [r for r in store.jobs_in("IDLE") if r.ctx.dispatch_permit]
    assert len(granted) == 1
    assert granted[0].job.to_station == "A_LD1", (
        "the emptier leg should get the turn even though its job is younger")


def test_the_real_plant_wires_through_without_blowing_up():
    """The integration this file's own fixtures cannot catch.

    Every test above supplies its own `leg_of` returning a string, so all of
    them passed while the real system was broken: `plant.segment_of_station`
    returns the segment DICT, not its name, and a dict is unhashable. The
    monitor threw `TypeError: unhashable type: 'dict'` out of every step.

    Nothing crashed — the Supervisor caught it, logged it and kept the other
    FSMs running — so the only symptom was three robots sitting still. A unit
    test with a hand-written fixture can never find that. This one uses the
    real plant, the real rack sizes and the real leg lookup.
    """
    from csm import plant as real_plant
    from csm.sim_node import _leg_of, _rack_sizes

    cap = LineCapacity(real_plant.SEGMENTS, _rack_sizes().get)

    # THE TRAP ITSELF, pinned so nobody "simplifies" _leg_of away again.
    # segment_of_station answers with the whole segment, which is the right
    # answer to a different question.
    raw = real_plant.segment_of_station("GRV1_LD")
    assert isinstance(raw, dict), (
        "segment_of_station returns the segment; _leg_of exists to unwrap it")

    # Every leg must key by something hashable, or the counts dict explodes.
    for station in real_plant.FEEDS:
        leg = _leg_of(station)
        assert leg is None or isinstance(leg, str), (
            f"{station} -> {leg!r}: leg keys must be hashable names")
        {leg: 1}                       # the operation that actually failed

    # And the documented capacities produce the ceilings the ADR records.
    assert cap.ceiling("A") == 6
    assert cap.ceiling("B") == 17
    assert cap.ceiling("C") == 34


def test_build_mes_actually_wires_what_it_is_given():
    """Built, tested, and never switched on is the failure mode here.

    Both `divert_for` and the §2.15 capacity shipped opt-in — correctly, so no
    existing caller silently acquired new behaviour. Neither was then opted
    into by `sim_node`, so both were dead in the running system while their
    unit tests passed. `diverted_to_rack` was 0 across four measured runs on
    2026-08-20, with all 45 rack slots empty, and that read as "the condition
    never arose" rather than "the feature is off".

    This asserts the wiring itself, which no test did before.
    """
    from csm.runtime.mes_app import build_mes

    clock = ManualClock()
    equipment = MockEquipment(STATIONS, clock)
    cap = capacity()
    app = build_mes(equipment, MockAcs(clock),
                    source_for=lambda s: FEEDS.get(s, "SRC"),
                    clock=clock, logger=lambda m: None,
                    install_supervisor=False,
                    capacity=cap, leg_of=leg_of,
                    divert_for=SEGMENTS)

    assert app.monitor.divert_for is SEGMENTS, "divert scan not switched on"
    assert app.monitor.capacity is cap, "monitor has no ceiling"
    assert app.monitor.leg_of is leg_of
    # Both tasks or neither — a dispatcher without the ceiling would disagree
    # with the monitor about how loaded a leg is.
    assert app.dispatcher.capacity is cap, "dispatcher has no ceiling"
    assert app.dispatcher.leg_of is leg_of


def test_build_mes_leaves_everything_off_by_default():
    """The opt-in guarantee, asserted rather than assumed."""
    from csm.runtime.mes_app import build_mes

    clock = ManualClock()
    app = build_mes(MockEquipment(STATIONS, clock), MockAcs(clock),
                    source_for=lambda s: FEEDS.get(s, "SRC"),
                    clock=clock, logger=lambda m: None,
                    install_supervisor=False)

    assert app.monitor.divert_for is None
    assert app.monitor.capacity is None
    assert app.dispatcher.capacity is None


def test_priority_still_outranks_shortfall():
    """Ordering competing jobs is CSM's, and priority is how it is expressed."""
    clock, equipment, store, monitor = build()
    dispatcher = DispatcherTask(store)
    dispatcher.capacity = capacity()
    dispatcher.leg_of = leg_of

    store.create("SRC", "B_LD1")            # loads leg B
    clock.advance(1)
    store.create("SRC", "A_LD1")            # starved leg, routine priority
    clock.advance(1)
    store.create("SRC", "B_LD2", priority=5)  # busy leg, but urgent

    step(dispatcher)

    granted = [r for r in store.jobs_in("IDLE") if r.ctx.dispatch_permit]
    assert granted[0].job.to_station == "B_LD2", (
        "an urgent job must not wait behind a routine one on an emptier leg")
