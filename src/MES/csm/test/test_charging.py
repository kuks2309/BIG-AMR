"""Charging — the CSM decides, the ACS drives.

The ACS team said so directly in the 2026-08-14 meeting: "CSM will give the
command to ACS to charge" (verified, transcript line 1357). Choosing WHO goes
and WHEN is a scheduling decision, and scheduling is this layer's job.
"""

import asyncio

import pytest

from csm import plant
from csm.adapters.base import SimpleResponse, TaskKind
from csm.adapters.mock import ManualClock, MockAcs, MockEquipment
from csm.runtime.job_store import JobStore
from csm.runtime.tasks.charging import (CHARGE_TO, CRITICAL_BATTERY,
                                        LOW_BATTERY, ChargingTask)
from csm.sim_node import _start_levels


class ReportingAcs(MockAcs):
    """An ACS that reports charge and records the orders it is given."""

    def __init__(self, clock, fleet):
        super().__init__(clock)
        self._fleet = fleet
        self.orders = []
        self.refuse = False

    def fleet_status(self):
        return self._fleet

    def create_order(self, order):
        self.orders.append(order)
        if self.refuse:
            return SimpleResponse(1, "robot is working")
        return SimpleResponse(0, "charging")


def build(fleet):
    clock = ManualClock()
    acs = ReportingAcs(clock, fleet)
    store = JobStore(MockEquipment(["ASRS"], clock), acs, clock,
                     logger=lambda m: None, dispatch_gated=True)
    return clock, acs, ChargingTask(store)


def robot(name="amr1", battery=100.0, busy=False, responsive=True,
          charging_to=None):
    return {"name": name, "battery": battery, "busy": busy,
            "responsive": responsive, "charging_to": charging_to}


def step(task):
    asyncio.run(task.step())


# -- the chargers themselves, from the deck's own numbers --------------------

def test_the_fleet_has_the_number_of_chargers_the_deck_states():
    """Deck slide 30: "Charger 5EA" for the Big AGV fleet on each polarity."""
    assert sum(len(v) for v in plant.CHARGERS.values()) == 5


def test_there_is_roughly_one_charger_per_two_robots():
    for leg, count in plant.FLEET.items():
        assert len(plant.CHARGERS[leg]) == (count + 1) // plant.CHARGER_EVERY


def test_a_charger_is_a_parking_slot_with_power():
    """Not separate geometry — which is how the real plant works."""
    for leg, chargers in plant.CHARGERS.items():
        for c in chargers:
            assert c in plant.PARKING_SLOTS[leg]


def test_a_robot_charges_on_its_own_leg():
    """Crossing the plant to another leg's charger crosses every lane it
    is bound to stay out of."""
    for name in ("amr1", "amr2", "amr3"):
        leg = plant.ROBOT_SEGMENT[name]
        assert plant.charger_for(name) in plant.CHARGERS[leg]


# -- when a robot is sent -----------------------------------------------------

def test_a_full_robot_is_left_alone():
    _, acs, task = build([robot(battery=100.0)])
    step(task)
    assert acs.orders == []


def test_a_low_idle_robot_is_sent_to_charge():
    _, acs, task = build([robot(battery=LOW_BATTERY - 1, busy=False)])
    step(task)
    assert len(acs.orders) == 1
    order = acs.orders[0]
    assert [t.kind for t in order.tasks] == [TaskKind.MOVE, TaskKind.CHARGE]
    assert order.tasks[1].chargeTo == int(CHARGE_TO)


def test_a_working_robot_finishes_its_job_first():
    """A charging robot is a robot not working, and there is one per leg."""
    _, acs, task = build([robot(battery=LOW_BATTERY - 1, busy=True)])
    step(task)
    assert acs.orders == []


def test_a_critically_low_robot_goes_even_if_it_is_working():
    """A robot that stops mid-aisle blocks the aisle for everyone."""
    _, acs, task = build([robot(battery=CRITICAL_BATTERY - 1, busy=True)])
    step(task)
    assert len(acs.orders) == 1
    assert acs.orders[0].priority > 1, "it should outrank material movement"


def test_a_robot_already_charging_is_not_sent_again():
    _, acs, task = build([robot(battery=20.0, charging_to=90.0)])
    step(task)
    assert acs.orders == []


def test_a_robot_is_asked_for_once_not_every_cycle():
    """A slow trip to the charger must not read as "still low, ask again"."""
    _, acs, task = build([robot(battery=LOW_BATTERY - 1)])
    for _ in range(5):
        step(task)
    assert len(acs.orders) == 1


def test_an_unresponsive_robot_is_not_sent():
    """It cannot drive to a charger either — the order would be unexecutable."""
    _, acs, task = build([robot(battery=5.0, responsive=False)])
    step(task)
    assert acs.orders == []


def test_a_refused_order_does_not_count_as_sent():
    _, acs, task = build([robot(battery=LOW_BATTERY - 1)])
    acs.refuse = True
    step(task)
    assert task.charge_orders == 0


# -- an ACS that cannot report charge ----------------------------------------

def test_an_acs_that_reports_no_battery_is_left_alone():
    """No battery figure is not a battery figure of zero."""
    _, acs, task = build([{"name": "amr1", "busy": False, "responsive": True}])
    step(task)
    assert acs.orders == []


def test_an_acs_with_no_fleet_report_does_nothing():
    clock = ManualClock()
    store = JobStore(MockEquipment(["ASRS"], clock), MockAcs(clock), clock,
                     logger=lambda m: None, dispatch_gated=True)
    step(ChargingTask(store))          # must not raise


def test_a_leg_with_no_charger_is_reported_once():
    logged = []
    clock = ManualClock()
    # A name with no leg, and therefore no charger. Not `amr9` — that became a
    # real robot when the fleet table grew to the deck's ten.
    acs = ReportingAcs(clock, [robot(name="amr99", battery=5.0)])
    store = JobStore(MockEquipment(["ASRS"], clock), acs, clock,
                     logger=logged.append, dispatch_gated=True)
    task = ChargingTask(store)
    for _ in range(4):
        step(task)
    assert acs.orders == []
    assert sum("no charger" in m for m in logged) == 1


# -- the deadlock this had, and no longer has --------------------------------

def test_a_critical_order_is_marked_to_preempt():
    """"Finish the job first" cannot apply when the charge will not last.

    The simulator produced the deadlock: a robot told to charge after its
    current job went flat mid-job, so the job never ended and the charge never
    started — three robots dead holding jobs they could not finish. A critical
    order carries a priority the ACS uses to take the job off the robot.
    """
    _, acs, task = build([robot(battery=CRITICAL_BATTERY - 1, busy=True)])
    step(task)
    assert acs.orders[0].priority >= 100


def test_a_merely_low_order_does_not_preempt():
    """A robot with charge to spare finishes what it is carrying."""
    _, acs, task = build([robot(battery=LOW_BATTERY - 1, busy=False)])
    step(task)
    assert acs.orders[0].priority < 100


# ------------------------------------------------ the thresholds are parameters

def task_for(fleet, **thresholds):
    clock = ManualClock()
    acs = ReportingAcs(clock, fleet)
    store = JobStore(MockEquipment(["ASRS"], clock), acs, clock,
                     logger=lambda m: None, dispatch_gated=True)
    return acs, ChargingTask(store, **thresholds)


def test_the_thresholds_can_be_set_per_run():
    """None of the three is a measured number. Their own comments say they are
    parameters, and this is what makes that true."""
    _, task = task_for([], low_battery=80.0, charge_to=95.0,
                       critical_battery=50.0)
    assert (task.low_battery, task.charge_to, task.critical_battery) == \
        (80.0, 95.0, 50.0)


def test_unset_thresholds_keep_the_documented_defaults():
    _, task = task_for([])
    assert task.low_battery == LOW_BATTERY
    assert task.charge_to == CHARGE_TO
    assert task.critical_battery == CRITICAL_BATTERY


def test_a_lower_threshold_actually_changes_who_is_sent():
    """Not just stored — used."""
    _, quiet = task_for([robot(battery=75.0)])
    step(quiet)
    assert quiet.charge_orders == 0, "75% is not low by the default rule"

    _, eager = task_for([robot(battery=75.0)], low_battery=80.0, charge_to=95.0)
    step(eager)
    assert eager.charge_orders == 1


def test_the_charge_target_reaches_the_order():
    acs, task = task_for([robot(battery=10.0)], charge_to=55.0)
    step(task)

    charge = [t for t in acs.orders[0].tasks if t.kind is TaskKind.CHARGE]
    assert charge[0].chargeTo == 55


def test_charging_to_at_or_below_the_trigger_is_refused():
    """The robot would leave the charger still low and turn straight back."""
    with pytest.raises(ValueError):
        task_for([], low_battery=30.0, charge_to=30.0)
    with pytest.raises(ValueError):
        task_for([], low_battery=30.0, charge_to=20.0)


def test_critical_above_low_is_refused():
    """Every low robot would be critical, and a critical robot PREEMPTS the job
    it is holding — the whole fleet would drop its work at once."""
    with pytest.raises(ValueError):
        task_for([], low_battery=30.0, critical_battery=40.0)


# ---------------------------------------------------- starting a run part-charged

def test_one_number_starts_the_whole_fleet_there():
    assert _start_levels("20") == 20.0


def test_robots_can_be_started_at_different_levels():
    """A fleet that all starts at the same level all crosses the low mark at
    the same moment, which is not the case worth watching."""
    assert _start_levels("amr1=35,amr2=36,amr3=40") == \
        {"amr1": 35.0, "amr2": 36.0, "amr3": 40.0}


def test_spacing_does_not_matter():
    assert _start_levels(" amr1 = 35 , amr2=36 ") == {"amr1": 35.0, "amr2": 36.0}


def test_naming_only_some_robots_leaves_the_rest_alone():
    assert "amr3" not in _start_levels("amr1=35")


def test_nothing_given_means_leave_them_full():
    assert _start_levels("") is None
    assert _start_levels(None) is None
