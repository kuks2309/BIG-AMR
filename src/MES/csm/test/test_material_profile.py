"""Material described at birth, so the rules that read it can work.

Material was minted with a LOT id and nothing else, which had three effects and
none of them cosmetic:

  * CCS manual §1.3 refuses to feed a machine from an area holding material
    whose type and attribute are not recorded. With nothing recorded,
    `racks_fit_to_feed` answers "no" for every area in the plant and can never
    answer anything else - the rule is present and permanently inert.
  * the rotation rules (face must match, rotation may be fixed by turning the
    pallet 180°) have nothing to operate on.
  * the map draws every payload the same grey, because size is the drum type
    and colour is the face.
"""

import pytest

from csm.material import KNOWN_DRUM_TYPES, Face, MaterialAttribute
from csm.material_profile import MaterialProfile, simulator_profile
from csm.records import InMemoryRecords


# --------------------------------------------------------------- the profile

def test_a_station_with_no_entry_describes_nothing():
    """A real state, not an error - it is exactly what §1.3 excludes, and the
    simulator must be able to produce it on purpose."""
    p = MaterialProfile()

    assert p.describe("GRV1_LD") == {}


def test_a_described_station_gives_all_three_fields():
    p = MaterialProfile({"GRV1_LD": {"material_type": 302,
                                     "attribute": MaterialAttribute.DARK_CW,
                                     "drum_type": 500}})

    got = p.describe("GRV1_LD")

    assert got["material_type"] == 302
    assert got["attribute"] is MaterialAttribute.DARK_CW
    assert got["drum_type"] == 500


def test_an_empty_bobbin_gets_a_drum_type_and_nothing_else():
    """A bobbin is the bare core. It HAS a drum type - that is a property of
    the core - but no face and no material type, because there is no material
    on it. Describing one as though it carried material would put a face on a
    cardboard tube, and §1.3 would then feed a machine on the strength of it.
    """
    p = MaterialProfile({"GRV1_LD": {"material_type": 302,
                                     "attribute": MaterialAttribute.DARK_CW,
                                     "drum_type": 500}})

    got = p.describe("GRV1_LD", kind="bobbin")

    assert got == {"drum_type": 500}


# ------------------------------------------------ the simulator's stand-in

def test_every_station_gets_a_profile():
    stations = ["GRV1_LD", "GRV1_ULD", "CTR1_LD", "SLT_LD1", "ASRS"]
    p = simulator_profile(stations)

    for s in stations:
        assert p.describe(s), f"{s} has no profile"


def test_it_is_deterministic():
    """A profile that varied would make every selection rule
    non-reproducible and every bug unrepeatable."""
    stations = ["GRV1_LD", "CTR1_LD", "SLT_LD1"]

    first = simulator_profile(stations).describe("CTR1_LD")
    again = simulator_profile(stations).describe("CTR1_LD")

    assert first == again


def test_all_four_attributes_and_all_four_drum_types_appear():
    """A plant where everything is 亮面顺时针 cannot exercise the matching
    rules at all - the face must match and the rotation may differ."""
    stations = [f"S{i}" for i in range(12)]
    p = simulator_profile(stations)
    described = [p.describe(s) for s in stations]

    assert {d["attribute"] for d in described} == set(MaterialAttribute)
    assert {d["drum_type"] for d in described} == set(KNOWN_DRUM_TYPES)


# ---------------------------------------- what it unblocks, end to end

def test_a_described_rack_can_be_fed_from_and_an_undescribed_one_cannot():
    """The whole point. §1.3's test flips from permanently-no to answerable."""
    area = ["WIP_A", "WIP_B", "WIP_C"]
    p = simulator_profile(["SRC"])
    described = p.describe("SRC")

    blind = InMemoryRecords(rack_sizes={r: 4 for r in area})
    blind.park("WIP_A", "R-1", "j1", at=0.0)                    # nothing recorded
    assert blind.racks_fit_to_feed(area) is False

    seeing = InMemoryRecords(rack_sizes={r: 4 for r in area})
    seeing.park("WIP_A", "R-1", "j1", at=0.0,
                material_type=described["material_type"],
                material_attribute=described["attribute"],
                bobbin_type=described["drum_type"])

    assert seeing.racks_fit_to_feed(area) is True


def test_a_described_material_gives_the_map_a_size_and_a_colour():
    from csm.ui.state import _DRUM_SIZES, _payload

    records = InMemoryRecords()
    described = simulator_profile(["SRC"]).describe("SRC")
    m = records.register_material(kind="roll", at=0.0, **described)

    class Job:
        job_id, material_ref = "job_0001", m.material_ref

    class Record:
        job = Job()

    class Store:
        active = [Record()]
        def __init__(self):
            self.records = records

    got = _payload(Store(), {"loaded": True, "job_id": "job_0001"})

    assert got["face"] in (Face.BRIGHT.value, Face.DARK.value)
    assert got["size"] == _DRUM_SIZES[described["drum_type"]]


def test_the_monitor_describes_at_birth_and_defaults_to_not():
    import inspect

    from csm.runtime.tasks.equipment_monitor import EquipmentMonitorTask

    src = inspect.getsource(EquipmentMonitorTask._claim_material)
    assert "self.profile.describe(location, kind)" in src
    assert "**described" in src

    task = object.__new__(EquipmentMonitorTask)
    task.profile = None
    assert task.profile is None, "no profile must mint exactly as before"


def test_the_simulator_actually_sets_one():
    import inspect

    from csm import sim_node

    src = inspect.getsource(sim_node)
    assert "profile=simulator_profile(plant.STATIONS)" in src
    assert "INVENTED" in src, "a stand-in must say that it is one"


def test_describe_plugs_straight_into_register_material():
    """THE REGRESSION. The profile returned the RACK's field names, so every
    mint raised TypeError inside the monitor's try/except and the simulator
    ran for five minutes creating no material at all while reporting nothing
    worse than "step failed". A unit test on the profile alone could not see
    it; this calls the two together, which is where the mismatch lived."""
    records = InMemoryRecords()
    described = simulator_profile(["SRC"]).describe("SRC")

    m = records.register_material(kind="roll", at=0.0, location="SRC",
                                  **described)

    assert m.attribute is not None
    assert m.drum_type in KNOWN_DRUM_TYPES
    assert m.material_type is not None


def test_a_bobbin_also_plugs_straight_in():
    records = InMemoryRecords()
    described = simulator_profile(["SRC"]).describe("SRC", kind="bobbin")

    m = records.register_material(kind="bobbin", at=0.0, **described)

    assert m.drum_type in KNOWN_DRUM_TYPES
    assert m.attribute is None, "a bare core has no face"
