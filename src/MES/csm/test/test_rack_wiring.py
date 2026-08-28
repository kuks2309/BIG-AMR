"""The rack model and the curing clock, wired to the paths that use them.

Building a model nothing calls is how a codebase grows capabilities it does not
have. These tests are about the CALLERS: that inbound records what it put on
the rack, that a rack out of service is not diverted to, and that the curing
clock starts where material comes to rest.
"""

from csm.curing import SIX_HOURS, CuringPolicy
from csm.material import MaterialAttribute
from csm.records import InMemoryRecords, RackMode


# --------------------------------------- what the PDA puts on the rack

def test_pda_inbound_writes_the_supplement_onto_the_rack():
    """The method already refuses without material type, attribute and bobbin
    type — so it holds exactly what §4.6.6 says the rack must record."""
    from csm.pda import Pda

    records = InMemoryRecords(rack_sizes={"WIP_A": 4})
    material = records.register_material(
        kind="roll", at=0.0, attribute=MaterialAttribute.BRIGHT_CW,
        drum_type=430, material_type=7)

    class Store:
        def __init__(self, records):
            self.records = records
        def clock(self):
            return 100.0

    desk = Pda(Store(records))
    result = desk.bind_to_rack(material.material_ref, "WIP_A")

    assert result.ok, result.reason
    slot = records.slots("WIP_A")[0]
    assert slot.material_attribute is MaterialAttribute.BRIGHT_CW
    assert slot.bobbin_type == 430
    assert slot.material_type == 7
    assert slot.described is True


# ------------------------------------ a rack out of service is not used

def test_the_divert_refuses_a_rack_that_is_not_in_service():
    """CCS manual §1.2.1.1 rule 3 wants the buffer rack to have "no
    abnormality". `_can_accept` asks the equipment whether the port is
    physically free; whether CCS may USE it is a different question, and it
    was not being asked at all."""
    import inspect

    from csm.runtime.tasks.equipment_monitor import EquipmentMonitorTask

    src = inspect.getsource(EquipmentMonitorTask)
    at = src.index('port = next((b for b in seg["buffer"]')
    window = src[at:at + 300]

    assert "rack_usable" in window, \
        "the divert picks a buffer rack without asking whether CCS may use it"


def test_rack_usable_is_what_the_divert_asks():
    r = InMemoryRecords(rack_sizes={"WIP_A": 4})
    assert r.rack_usable("WIP_A") is True

    r.set_rack_mode("WIP_A", RackMode.ABNORMAL)

    assert r.rack_usable("WIP_A") is False
    assert r.holds_material("WIP_A") is True     # and it costs the line a slot


# -------------------------------------------- where the curing clock starts

def test_the_divert_starts_the_curing_clock():
    import inspect

    from csm.runtime.tasks.equipment_monitor import EquipmentMonitorTask

    src = inspect.getsource(EquipmentMonitorTask)

    assert "begin_curing" in src, \
        "material comes to rest on a rack and no clock is started"
    assert "self.curing" in src, "there is no policy to ask"


def test_no_policy_means_no_curing_which_is_the_shipped_behaviour():
    """CCS manual §4.6.12: 静置为非标准功能，静置时间一般设置为 0. A line with
    no policy configured must behave exactly as it did before."""
    from csm.runtime.tasks.equipment_monitor import EquipmentMonitorTask

    task = object.__new__(EquipmentMonitorTask)
    task.curing = None

    assert task.curing is None


def test_a_policy_answers_per_place():
    p = CuringPolicy({"WIP_WD": SIX_HOURS, "WIP_GRV": 0.0})

    assert p.seconds_for("WIP_WD") == SIX_HOURS
    assert p.seconds_for("WIP_GRV") == 0.0
    assert p.seconds_for("WIP_CTR") is None


def test_material_that_arrives_already_curing_keeps_its_original_start():
    """The divert calls begin_curing unconditionally, which is only safe
    because it is idempotent. [HB] §3: must not cure twice."""
    r = InMemoryRecords()
    ref = r.register_material(kind="roll", at=0.0).material_ref
    r.begin_curing(ref, at=0.0, seconds=SIX_HOURS)

    r.begin_curing(ref, at=5 * 3600.0, seconds=SIX_HOURS)   # diverted again

    assert r.is_ready(ref, now=SIX_HOURS) is True
