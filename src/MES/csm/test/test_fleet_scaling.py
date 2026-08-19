"""Growing the fleet past three.

Everything below was written while `ROBOT_SEGMENT` held exactly three names,
and several things were true only because of that: one robot per leg, a
robot's charger being its own parking slot, and names sorting correctly as
strings. None of them survives ten robots, and none of them fails loudly.
"""

import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm import plant                                            # noqa: E402
from csm.adapters import roads                                   # noqa: E402

DECK_TOTAL = sum(plant.FLEET.values())


# ------------------------------------------------------ how legs are handed out

def test_three_robots_still_get_one_leg_each():
    """The fleet we have been running. Changing how legs are assigned must not
    move amr1, amr2 or amr3 — they drive home to their slots."""
    assert plant.assign_legs(3) == {"amr1": "A", "amr2": "B", "amr3": "C"}


def test_five_robots_put_the_spare_pair_on_the_busy_leg():
    """Leg C carries coater-to-slitter and the deck gives it six of ten."""
    assert Counter(plant.assign_legs(5).values()) == {"A": 1, "B": 1, "C": 3}


def test_ten_robots_reproduce_the_deck_exactly():
    """2 / 2 / 6 [S6]. The whole point of the proportional rule."""
    assert Counter(plant.assign_legs(10).values()) == plant.FLEET


def test_it_stops_at_the_deck_total():
    """There are only that many parking slots and that many chargers. A robot
    with nowhere to park is not a robot, so the shortage is shown, not hidden."""
    assert len(plant.assign_legs(20)) == DECK_TOTAL


def test_a_leg_never_gets_more_robots_than_the_deck_gives_it():
    for n in range(1, DECK_TOTAL + 1):
        counts = Counter(plant.assign_legs(n).values())
        for leg, given in counts.items():
            assert given <= plant.FLEET[leg], f"{n} robots overfilled leg {leg}"


def test_growing_the_fleet_never_moves_an_existing_robot():
    """A robot drives home to its slot. If adding a robot reshuffles the legs,
    every robot already on the floor is heading somewhere that is no longer
    theirs."""
    for n in range(1, DECK_TOTAL):
        smaller, bigger = plant.assign_legs(n), plant.assign_legs(n + 1)
        for name, leg in smaller.items():
            assert bigger[name] == leg, f"{name} moved when the fleet grew to {n + 1}"


# ------------------------------------------------------------- parking at scale

def test_no_two_robots_share_a_parking_slot():
    """A shared slot is a collision, not a scheduling problem."""
    slots = {}
    for name in plant.ROBOT_SEGMENT:
        slot = plant.parking_for(name)
        assert slot is not None, f"{name} has nowhere to park"
        assert slot not in slots, f"{name} and {slots[slot]} share {slot}"
        slots[slot] = name


def test_robots_are_ordered_numerically_not_alphabetically():
    """`amr10` sorts before `amr3` as a string.

    That would hand leg C's first slot to the tenth robot and shuffle everyone
    else's — a fault that cannot appear below ten robots and is silent above
    it until two robots drive to one bay.
    """
    assert plant.robot_number("amr10") == 10
    leg_c = sorted((n for n, s in plant.ROBOT_SEGMENT.items() if s == "C"),
                   key=plant.robot_number)
    assert plant.parking_for(leg_c[0]) == plant.PARKING_SLOTS["C"][0]
    assert plant.parking_for("amr10") != plant.PARKING_SLOTS["C"][0]


def test_every_robot_has_a_road_node_to_drive_home_to():
    for name in plant.ROBOT_SEGMENT:
        node = roads.park_node(name)
        assert node is not None, name
        assert roads.build().nodes[node] == plant.parking_for(name)


# -------------------------------------------------- five chargers, ten robots

def test_the_deck_gives_fewer_chargers_than_robots():
    """The fact that makes a reservation necessary rather than a nicety."""
    assert sum(len(v) for v in plant.CHARGERS.values()) == 5
    assert DECK_TOTAL == 10


def test_a_charger_is_a_preference_not_a_reservation():
    """`charger_for` names a place. It cannot promise nobody else is on it —
    two robots on leg C really do prefer the same plug."""
    preferred = [plant.charger_for(n) for n, s in plant.ROBOT_SEGMENT.items()
                 if s == "C"]
    assert len(preferred) > len(set(preferred)), \
        "leg C's robots must share, or this whole problem is imaginary"


def test_every_robot_is_offered_every_charger_on_its_own_leg():
    for name, leg in plant.ROBOT_SEGMENT.items():
        assert plant.chargers_for(name) == sorted(
            plant.CHARGERS[leg],
            key=lambda c: ((c[0] - plant.parking_for(name)[0]) ** 2
                           + (c[1] - plant.parking_for(name)[1]) ** 2))


def test_a_robot_never_gets_another_legs_charger():
    """Crossing the plant to another leg's plug crosses every lane it is bound
    to stay out of."""
    for name, leg in plant.ROBOT_SEGMENT.items():
        for spot in plant.chargers_for(name):
            assert spot in plant.CHARGERS[leg], f"{name} sent off its leg"


def test_a_charger_has_a_road_node_of_its_own():
    """A robot sent to charge is sent to somebody's parking slot — usually not
    its own — so that slot must be reachable by name."""
    for leg, spots in plant.CHARGERS.items():
        for spot in spots:
            assert roads.park_node_at(spot) is not None, spot


def test_most_robots_do_not_park_on_their_charger():
    """The assumption that broke: "its charger IS its parking slot" held only
    while every leg had one robot."""
    apart = [n for n in plant.ROBOT_SEGMENT
             if plant.charger_for(n) != plant.parking_for(n)]
    assert apart, "if every robot parks on its charger, the routing is untested"


# ----------------------------------------------------------- the launch side

def test_the_launch_fleet_order_is_generated_not_listed():
    """A hand-written tuple of three names was what capped the fleet."""
    launch = (pathlib.Path(__file__).resolve().parents[3]
              / "Sim" / "trnav_2ws_gazebo" / "launch" / "fleet.launch.py")
    if not launch.exists():                      # not checked out together
        return
    source = launch.read_text()
    assert "_FLEET_ORDER = tuple(" in source
    assert "'amr1', 'amr2', 'amr3'" not in source
