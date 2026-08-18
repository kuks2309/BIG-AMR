"""The OPC-UA equipment model.

Source: `AGV与主机设备对接流程及协议.xlsx`, sheet 主机与AGV交互变量表 (held outside
this repository). These tests pin the CUSTOMER'S definitions, so that our own
earlier inventions cannot creep back in.
"""

import pytest

from csm.adapters.base import (DockingAxis, EquipmentType, MachineNumber,
                               MaterialPresence, Polarity, TaskProcessing)


# -- MC_Num: the station's real identity -------------------------------------

def test_machine_number_round_trips():
    assert str(MachineNumber.parse("1A01")) == "1A01"
    assert str(MachineNumber.parse("2T12")) == "2T12"


def test_machine_number_decodes_polarity_type_and_sequence():
    mc = MachineNumber.parse("1A01")
    assert mc.polarity is Polarity.ANODE
    assert mc.equipment is EquipmentType.GRAVURE
    assert mc.sequence == 1


def test_polarity_numbering_is_not_alphabetical():
    """1 = Anode, 2 = Cathode. Easy to assume the other way round."""
    assert Polarity.ANODE.value == 1
    assert Polarity.CATHODE.value == 2
    assert MachineNumber.parse("2A01").polarity is Polarity.CATHODE


def test_equipment_type_letters_are_the_customers():
    assert EquipmentType.GRAVURE.value == "A"
    assert EquipmentType.COATING.value == "T"
    assert EquipmentType.COLD_PRESS.value == "L"


@pytest.mark.parametrize("bad", ["", "1A", "1A001", "AA01", "1A0X", "11101"])
def test_a_malformed_machine_number_is_refused_not_guessed(bad):
    """A misread machine number sends a robot to the wrong machine."""
    with pytest.raises(ValueError):
        MachineNumber.parse(bad)


def test_machine_numbers_compare_and_hash_by_value():
    assert MachineNumber.parse("1A01") == MachineNumber.parse("1A01")
    assert len({MachineNumber.parse("1A01"), MachineNumber.parse("1A01")}) == 1


# -- MC_Axis_Num: a machine is four docking axes, not one port ---------------

def test_four_docking_axes_with_the_customers_numbering():
    assert DockingAxis.UNWIND_A.value == 1
    assert DockingAxis.UNWIND_B.value == 2
    assert DockingAxis.REWIND_A.value == 3
    assert DockingAxis.REWIND_B.value == 4


def test_axis_selects_which_half_of_the_duplicated_variable_block():
    """Every signal exists twice, _UW and _RW."""
    assert DockingAxis.UNWIND_A.suffix == "_UW"
    assert DockingAxis.UNWIND_B.suffix == "_UW"
    assert DockingAxis.REWIND_A.suffix == "_RW"
    assert DockingAxis.REWIND_B.suffix == "_RW"


# -- the three presence booleans replace our invented status enum ------------

def test_the_three_documented_combinations():
    assert MaterialPresence.from_signals(1, 0, 0) is MaterialPresence.FULL_ROLL
    assert MaterialPresence.from_signals(0, 1, 0) is MaterialPresence.NOTHING
    assert MaterialPresence.from_signals(0, 0, 1) is MaterialPresence.EMPTY_BOBBIN


def test_empty_bobbin_is_expressible():
    """The state that makes the six bobbin-return jobs observable."""
    assert MaterialPresence.from_signals(0, 0, 1) is MaterialPresence.EMPTY_BOBBIN


@pytest.mark.parametrize("signals", [
    (0, 0, 0),      # nothing asserted
    (1, 1, 0),      # full and empty at once
    (1, 0, 1),
    (0, 1, 1),
    (1, 1, 1),
])
def test_disagreeing_booleans_are_reported_not_rounded(signals):
    """A machine mid-transition can assert a combination that means nothing.

    Rounding that to the nearest sensible state would hide a real fault, so it
    gets its own value.
    """
    assert MaterialPresence.from_signals(*signals) is MaterialPresence.INCONSISTENT


# -- AGV_Task_Processing: nine codes, not one BUSY ---------------------------

def test_nine_status_codes_with_the_customers_numbering():
    assert [c.value for c in TaskProcessing] == [1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_code_four_is_the_wip_divert_trigger():
    """"Buffer full, no empty slot" — the customer's own reason to divert.

    Specification jobs 4, 8 and 12 exist for exactly this condition.
    """
    assert TaskProcessing(4) is TaskProcessing.BUFFER_FULL


def test_the_two_codes_we_previously_had_to_infer():
    assert TaskProcessing(6) is TaskProcessing.TRAFFIC_JAM
    assert TaskProcessing(7) is TaskProcessing.GOING_TO_CHARGE


def test_cancellation_has_its_own_code():
    """Step one of the four-step cancellation dance."""
    assert TaskProcessing(9) is TaskProcessing.TASK_CANCELLED
