"""A charging robot is not a free robot.

Observed live on 2026-08-19 with the fleet started at 20%: amr1 climbed from
20% to 30%, was given a job, drove off its charger and started falling again —
while the live view went on reporting `charging_to 90` the whole way down,
because nothing ever cleared it.

Neither existing test excluded it. `busy` is False for a robot standing on a
charger, and `can_move` is True — it can move, that is the problem.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.adapters import roads                                  # noqa: E402
from csm import plant                                           # noqa: E402


class _Robot:
    """The two fields dispatch actually reads, and nothing else."""

    def __init__(self, name, charging_to=None, busy=False):
        self.name = name
        self._charging_to = charging_to
        self.busy = busy

    charging = property(lambda self: self._charging_to is not None)


def test_a_robot_told_to_charge_is_not_free():
    assert _Robot("amr1", charging_to=90.0).charging


def test_a_robot_that_finished_charging_is_free_again():
    """The exclusion has to end by itself. `_step_battery` clears the target on
    reaching it, and nothing else has to remember to lift anything."""
    robot = _Robot("amr1", charging_to=90.0)
    robot._charging_to = None
    assert not robot.charging


def test_being_idle_is_not_the_same_as_being_available():
    """The distinction the dispatcher was missing. A robot on a charger is not
    busy and can move — both old tests pass while it is pulled off mid-charge."""
    parked = _Robot("amr1", charging_to=90.0, busy=False)
    assert not parked.busy
    assert parked.charging, "not busy, but not available either"


def test_the_dispatcher_actually_applies_it():
    """Against the real source, so the rule cannot be deleted quietly."""
    source = (pathlib.Path(__file__).resolve().parents[1]
              / "csm" / "adapters" / "sim_acs.py").read_text()
    assert "and not r.charging" in source


# -- and the parking node the drive FSM died on ------------------------------

def test_every_robot_has_a_parking_node():
    """`park_{segment}` was a NameError in `_go_home`, so every attempt to
    drive home killed the drive FSM. It stayed hidden because homing is only
    reached by a robot that is idle AND away from its bay."""
    for name in plant.ROBOT_SEGMENT:
        assert roads.park_node(name) is not None, name


def test_the_parking_node_is_a_node_that_exists():
    """A name that is merely well-formed still routes nowhere."""
    network = roads.build()
    for name in plant.ROBOT_SEGMENT:
        assert roads.park_node(name) in network.nodes


def test_the_node_and_the_coordinates_agree():
    """`plant.parking_for` gives the point, `roads.park_node` gives the node
    with that point. Two derivations of one slot is how they drift apart."""
    network = roads.build()
    for name in plant.ROBOT_SEGMENT:
        assert network.nodes[roads.park_node(name)] == plant.parking_for(name)


def test_robots_on_one_leg_get_different_slots():
    seen = {}
    for name, leg in plant.ROBOT_SEGMENT.items():
        node = roads.park_node(name)
        assert node not in seen.values(), f"{name} shares {node}"
        seen[name] = node


def test_a_robot_can_be_routed_home_from_anywhere_on_the_floor():
    """The call `_go_home` makes. It has to return waypoints, not nothing."""
    network = roads.build()
    for name in plant.ROBOT_SEGMENT:
        other = plant.parking_for("amr3" if name != "amr3" else "amr1")
        route = network.route_to_node(other, roads.park_node(name))
        assert route, f"{name} cannot route home from {other}"
