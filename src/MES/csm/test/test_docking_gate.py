"""A robot may not enter a machine until the machine says so — and keeps saying so.

`request_entry` is the FLEET's interlock: one robot per bay, arbitrated between
robots. This is a different question — MC_Enter_Permitted, the MACHINE saying
whether it is safe to come in at all.

It is not a flag. Condition 7: entry is permitted only once the signal has been
received CONTINUOUSLY for longer than the comm-alarm time. These tests fail if
anyone flattens that back into a boolean check.
"""

import pytest

from csm.adapters.mock import ManualClock, OpcUaEquipment
from csm.adapters.sim_acs import SimAcs, SimRobot


class FakeLogger:
    def __init__(self):
        self.lines = []

    def info(self, m):
        self.lines.append(m)

    def warn(self, m):
        self.lines.append(m)


class FakeNode:
    def __init__(self):
        self._logger = FakeLogger()

    def get_logger(self):
        return self._logger


def robot_at(equipment, now=0.0):
    """A SimRobot with only what the entry gate touches.

    Built without __init__ for the reason test_traffic.py gives: the real one
    needs a live ROS node, publishers and subscriptions, and none of that takes
    part in this rule.
    """
    acs = object.__new__(SimAcs)
    acs.node = FakeNode()
    acs.equipment = equipment
    acs.robots = []

    r = object.__new__(SimRobot)
    r.node = acs.node
    r.fleet = acs
    r.name = "amr1"
    r._docking = False
    r._noted_permission = False
    r._stopped = []
    r._stop = lambda why="unspecified": r._stopped.append(why)
    r._reset_stall = lambda: None
    r._tag = lambda: "[amr1] "
    return r


def build(comm_alarm=2.0):
    clock = ManualClock()
    equipment = OpcUaEquipment(["GRV1_LD"], clock, comm_alarm_seconds=comm_alarm)
    return clock, equipment, robot_at(equipment)


# -- the duration rule -------------------------------------------------------

def test_entry_is_refused_until_permission_has_been_held_long_enough():
    clock, equipment, r = build(comm_alarm=2.0)
    equipment.set_enter_permitted("GRV1_LD", True)

    assert not r._machine_permits("GRV1_LD"), "granted, but not yet for long enough"
    clock.advance(1.0)
    assert not r._machine_permits("GRV1_LD")
    clock.advance(1.0)
    assert r._machine_permits("GRV1_LD")


def test_a_robot_refused_entry_is_stopped():
    clock, equipment, r = build()
    equipment.set_enter_permitted("GRV1_LD", False)
    assert not r._machine_permits("GRV1_LD")
    assert r._stopped == ["machine has not granted entry"]


def test_permission_withdrawn_mid_approach_stops_the_robot():
    """The case a boolean check cannot express."""
    clock, equipment, r = build(comm_alarm=2.0)
    equipment.set_enter_permitted("GRV1_LD", True)
    for _ in range(3):
        r._machine_permits("GRV1_LD")
        clock.advance(1.0)
    assert r._machine_permits("GRV1_LD")

    equipment.set_enter_permitted("GRV1_LD", False)
    assert not r._machine_permits("GRV1_LD")

    equipment.set_enter_permitted("GRV1_LD", True)
    assert not r._machine_permits("GRV1_LD"), \
        "the clock restarts — banked time does not survive the gap"


def test_a_lost_heartbeat_refuses_entry():
    """Condition 6: communication not normal, the AGV stops."""
    clock, equipment, r = build(comm_alarm=2.0)
    equipment.set_enter_permitted("GRV1_LD", True)
    for _ in range(3):
        r._machine_permits("GRV1_LD")
        clock.advance(1.0)
    assert r._machine_permits("GRV1_LD")

    equipment.stop_heartbeat("GRV1_LD")
    clock.advance(3.0)
    assert not r._machine_permits("GRV1_LD")


# -- the machine is told we are inside ---------------------------------------

def test_the_machine_is_told_while_we_are_docking():
    """AGV_Entering rule 2: the machine may not move once it is set."""
    clock, equipment, r = build(comm_alarm=2.0)
    equipment.set_enter_permitted("GRV1_LD", True)
    r._docking = True

    r._machine_permits("GRV1_LD")
    assert not equipment.handshake("GRV1_LD").may_machine_move


def test_the_bay_is_not_released_the_moment_we_stop_asserting():
    """Rule 3: only PROLONGED silence means the robot has left."""
    clock, equipment, r = build(comm_alarm=2.0)
    equipment.set_enter_permitted("GRV1_LD", True)
    r._docking = True
    r._machine_permits("GRV1_LD")

    r._docking = False                      # stopped saying we are inside
    clock.advance(0.5)
    r._machine_permits("GRV1_LD")
    assert not equipment.handshake("GRV1_LD").may_machine_move, \
        "a gap in the signal must not read as departure"

    clock.advance(3.0)
    r._machine_permits("GRV1_LD")
    assert equipment.handshake("GRV1_LD").may_machine_move


# -- no equipment layer is not the same as a refusal -------------------------

def test_a_robot_with_no_equipment_layer_is_not_blocked():
    """"Cannot ask" must not mean "refused", or a line with no equipment stops."""
    r = robot_at(equipment=None)
    assert r._machine_permits("GRV1_LD")
    assert r._stopped == []


def test_an_adapter_without_a_handshake_is_not_blocked():
    from csm.adapters.mock import MockEquipment
    clock = ManualClock()
    r = robot_at(MockEquipment(["GRV1_LD"], clock))
    assert r._machine_permits("GRV1_LD")


# -- the wait is announced once, not every cycle -----------------------------

def test_waiting_is_logged_once_per_outage():
    clock, equipment, r = build()
    equipment.set_enter_permitted("GRV1_LD", False)
    for _ in range(10):
        r._machine_permits("GRV1_LD")
    waits = [l for l in r.node._logger.lines if "permit entry" in l]
    assert len(waits) == 1, waits
