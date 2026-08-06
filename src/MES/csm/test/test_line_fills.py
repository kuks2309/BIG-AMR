"""The line must fill past its first stage, which it could not.

A machine's output appears at its UNLOAD port, a different station from where
material went in. Without that link a coater job asks the gravure's unload port
for material, nothing ever puts any there, and the job is never created — 16
coater and slitter calls were raised in one run and produced zero jobs, so amr2
and amr3 never moved at all.
"""

import pytest

from csm import plant
from csm.adapters.base import StationStatus
from csm.adapters.mock import MockEquipment


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture
def equipment():
    clock = Clock()
    eq = MockEquipment(list(plant.DOCKS), clock, process_seconds=10.0)
    eq.mark_store("ASRS")
    for load, unload in plant.PORT_LINKS:
        eq.link_ports(load, unload)
    return eq, clock


def test_delivering_to_a_load_port_feeds_the_unload_port(equipment):
    eq, clock = equipment
    assert eq.get_station_status("GRV1_ULD") is StationStatus.IDLE

    eq.send_station_command("GRV1_LD", "delivered")
    assert eq.get_station_status("GRV1_ULD") is StationStatus.IDLE, \
        "nothing to collect until the machine has run"

    clock.t += 11.0
    assert eq.get_station_status("GRV1_ULD") is StationStatus.FINISHED, \
        "the machine's output must appear at its unload port"


def test_the_load_port_is_free_again_afterwards(equipment):
    eq, clock = equipment
    eq.send_station_command("GRV1_LD", "delivered")
    clock.t += 11.0
    eq.get_station_status("GRV1_ULD")
    assert eq.get_station_status("GRV1_LD") is StationStatus.IDLE, \
        "the load port must accept the next roll"


def test_a_load_port_is_settled_even_though_nobody_asks_about_it(equipment):
    """Nobody ever queries a load port — the monitor asks about SOURCES.

    Settling only the queried station left the load port BUSY for ever, its
    timer never examined, and the material stopped dead inside the machine.
    """
    eq, clock = equipment
    eq.send_station_command("GRV2_LD", "delivered")
    clock.t += 11.0
    # Ask ONLY about the unload port, as the equipment monitor does.
    assert eq.get_station_status("GRV2_ULD") is StationStatus.FINISHED


def test_each_machine_feeds_its_own_pair_not_the_first_one(equipment):
    """All four coaters were once fed from GRV1_ULD alone."""
    eq, clock = equipment
    eq.send_station_command("GRV3_LD", "delivered")
    clock.t += 11.0
    assert eq.get_station_status("GRV3_ULD") is StationStatus.FINISHED
    assert eq.get_station_status("GRV1_ULD") is StationStatus.IDLE
    assert plant.FEEDS["CTR3_LD"] == "GRV3_ULD"


def test_the_whole_chain_fills_one_stage_at_a_time(equipment):
    """ASRS -> gravure -> coater -> slitter, each gated on the one before."""
    eq, clock = equipment

    # amr1 delivers a roll to gravure 2.
    eq.send_station_command("GRV2_LD", "delivered")
    assert eq.get_station_status(plant.FEEDS["CTR2_LD"]) is not StationStatus.FINISHED
    clock.t += 11.0
    assert eq.get_station_status(plant.FEEDS["CTR2_LD"]) is StationStatus.FINISHED, \
        "amr2's work becomes servable one process cycle after amr1 delivers"

    # amr2 collects it and delivers to coater 2.
    eq.send_station_command("GRV2_ULD", "collected")
    eq.send_station_command("CTR2_LD", "delivered")
    assert eq.get_station_status(plant.FEEDS["SLT_LD2"]) is not StationStatus.FINISHED
    clock.t += 11.0
    assert eq.get_station_status(plant.FEEDS["SLT_LD2"]) is StationStatus.FINISHED, \
        "amr3's work becomes servable one cycle after amr2 delivers"


def test_the_store_never_needs_processing(equipment):
    eq, _ = equipment
    assert eq.get_station_status("ASRS") is StationStatus.FINISHED
