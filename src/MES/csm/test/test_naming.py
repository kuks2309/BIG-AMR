"""Job and task names, against the deck's own worked examples.

`TR_F Project SW 워크샵 2차.pptx` slide 6 gives three job names in full. Those
are the specification here — if this module cannot reproduce them, it is wrong,
whatever else it does.

The deck is internal material and lives outside this repository. Only the three
example strings appear here, because they are what is being asserted.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm import naming                                            # noqa: E402
from csm.adapters.base import TaskKind                            # noqa: E402
from csm.job import Carried, Job                                  # noqa: E402


def a_job(frm, to, carries=Carried.ROLL):
    return Job(job_id="job_0001", from_station=frm, to_station=to,
               carries=carries)


# ------------------------------------------------ the deck's own examples


def test_slide_six_first_example():
    """ASRS asks; a roll goes ASRS -> Gravure LD, on leg A."""
    job = a_job("ASRS", "GRV1_LD", Carried.ROLL)
    assert naming.job_name(job, "A") == "JB_CELL_LOWBIGA_ASRS_ASRS_GRVPRTLD_ROLL"


def test_slide_six_third_example():
    """Gravure LD asks; a bobbin goes back Gravure LD -> ASRS."""
    job = a_job("GRV1_LD", "ASRS", Carried.BOBBIN)
    assert naming.job_name(job, "A") == \
        "JB_CELL_LOWBIGA_GRVPRTLD_GRVPRTLD_ASRS_BOBBIN"


def test_slide_six_second_example_needs_an_explicit_requester():
    """The destination asked, not the source.

    This is the example that proves `requester` cannot be derived: material
    moves WIP Gravure -> Gravure LD, and it is the DESTINATION that raised the
    call. Defaulting to the source would name it WIPGP and be wrong.
    """
    job = a_job("WIP_GRV_1", "GRV1_LD", Carried.ROLL)
    assert naming.job_name(job, "A", requester="GRV1_LD") == \
        "JB_CELL_LOWBIGA_GRVPRTLD_WIPGP_GRVPRTLD_ROLL"


def test_the_task_example():
    assert naming.task_name(TaskKind.LOAD, "A") == "TK_CELL_LOWBIGA_LOAD"


# ------------------------------------------------------- station coding


def test_every_machine_of_a_family_shares_one_code():
    """The codes are per PROCESS, so the machine number is not in the name."""
    codes = {naming.station_code(f"GRV{n}_LD") for n in (1, 2, 3, 4)}
    assert codes == {"GRVPRTLD"}


def test_load_and_unload_are_different_codes():
    assert naming.station_code("GRV1_LD") != naming.station_code("GRV1_ULD")


def test_the_slitter_numbers_its_ports_the_other_way_round():
    """`SLT_LD1`, not `SLT1_LD`. The parser must cope with both shapes."""
    assert naming.station_code("SLT_LD1") == naming.station_code("SLT_LD4")
    assert naming.station_code("SLT_LD1") == "SLTLD"


def test_wip_racks_code_by_their_family():
    assert naming.station_code("WIP_GRV_1") == "WIPGP"
    assert naming.station_code("WIP_GRV_2") == "WIPGP"
    assert naming.station_code("WIP_CTR_1") != naming.station_code("WIP_GRV_1")


def test_an_unknown_station_is_loud_not_silent():
    """A wrong name is worse than an obviously missing one."""
    assert naming.station_code("NOWHERE_LD") == naming.UNKNOWN
    assert naming.station_code(None) == naming.UNKNOWN


def test_every_real_dock_gets_a_code():
    """No station in the plant may fall through the table unnoticed."""
    from csm import plant
    missing = [d for d in plant.DOCKS
               if naming.station_code(d) == naming.UNKNOWN]
    assert not missing, f"no code for: {missing}"


# ----------------------------------------------------------- agv types


def test_each_leg_has_its_own_agv_type():
    types = {naming.agv_type(leg) for leg in ("A", "B", "C")}
    assert len(types) == 3
    assert naming.agv_type("C") == "HIGHBIG"


def test_an_unknown_leg_does_not_invent_a_type():
    assert naming.agv_type("Z") == naming.UNKNOWN


# --------------------------------------------- what the name is NOT


def test_a_name_is_not_unique_and_this_test_says_so_out_loud():
    """Two different jobs, same name. This is why `job_id` still exists.

    If this ever starts failing because names were made unique, the change
    must be deliberate — `AcsOrder.id` depends on uniqueness.
    """
    first = Job(job_id="job_0001", from_station="ASRS",
                to_station="GRV1_LD", carries=Carried.ROLL)
    second = Job(job_id="job_0002", from_station="ASRS",
                 to_station="GRV3_LD", carries=Carried.ROLL)
    assert first.job_id != second.job_id
    assert naming.job_name(first, "A") == naming.job_name(second, "A")


def test_the_id_is_the_name_plus_a_counter():
    job = a_job("ASRS", "GRV1_LD", Carried.ROLL)
    assert naming.job_id(job, "A", 1) == \
        "JB_CELL_LOWBIGA_ASRS_ASRS_GRVPRTLD_ROLL_0001"


def test_the_counter_makes_identical_routes_distinguishable():
    """The whole reason a counter is appended."""
    job = a_job("ASRS", "GRV1_LD", Carried.ROLL)
    assert naming.job_id(job, "A", 1) != naming.job_id(job, "A", 2)


def test_the_counter_grows_past_four_digits_rather_than_wrapping():
    """Uniqueness beats alignment. A long run must not reuse an id."""
    job = a_job("ASRS", "GRV1_LD", Carried.ROLL)
    assert naming.job_id(job, "A", 12345).endswith("_12345")
    assert naming.job_id(job, "A", 9999) != naming.job_id(job, "A", 10000)


def test_confirmed_codes_are_not_quietly_extended():
    """Guard against a proposed code being promoted to confirmed by accident.

    Only three codes appear in the deck. Everything else is our extension and
    must stay labelled as such until somebody confirms it.
    """
    assert naming.CONFIRMED_CODES == {"ASRS", "GRV_LD", "WIP_GRV"}
    assert naming.CONFIRMED_CODES < set(naming.STATION_CODES)
