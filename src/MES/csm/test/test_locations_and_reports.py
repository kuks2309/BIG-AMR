"""The last two tables: `locations` and `abnormal_reports`.

Both close a finding from the 2026-08-21 database review.

`locations` — `materials.location` was a free string that might name a machine
port, a buffer rack or the store, and only the first had a table. A reader
joining materials to stations lost every roll in the ASRS without being told.

`abnormal_reports` — a person could file a problem and it was written nowhere,
so it did not survive a restart. Which is the one thing a report has to do.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm import plant                                              # noqa: E402
from csm.records import (InMemoryRecords, LocationKind)            # noqa: E402
from csm.records_sqlite import SqliteRecords                       # noqa: E402


def stores(tmp_path):
    """Both backends, so neither can drift from the other."""
    return [InMemoryRecords(), SqliteRecords(str(tmp_path / "r.db"))]


# ============================================================== locations


def test_the_three_kinds_are_told_apart(tmp_path):
    for records in stores(tmp_path):
        records.define_location("GRV1_LD", LocationKind.PORT, segment="A")
        records.define_location("WIP_SLT_1", LocationKind.RACK, segment="C")
        records.define_location("ASRS", LocationKind.STORE, segment="A")

        assert records.location_kind("GRV1_LD") is LocationKind.PORT
        assert records.location_kind("WIP_SLT_1") is LocationKind.RACK
        assert records.location_kind("ASRS") is LocationKind.STORE


def test_an_undeclared_location_is_detectable(tmp_path):
    """The whole point: an unknown place is now knowable, not silent."""
    for records in stores(tmp_path):
        assert records.location_kind("NOWHERE") is None


def test_declaring_twice_does_not_duplicate(tmp_path):
    for records in stores(tmp_path):
        records.define_location("ASRS", LocationKind.STORE)
        records.define_location("ASRS", LocationKind.STORE, segment="A")
        assert len(records.locations()) == 1
        assert records.locations()[0].segment == "A"


def test_the_plant_declares_every_place_material_can_be():
    """The finding, closed: ASRS used to resolve to nothing."""
    records = InMemoryRecords()
    plant.declare_locations(records)

    kinds = {}
    for entry in records.locations():
        kinds.setdefault(entry.kind, []).append(entry.location)

    assert "ASRS" in kinds[LocationKind.STORE]
    assert "GRV1_LD" in kinds[LocationKind.PORT]
    assert any(name.startswith("WIP_") for name in kinds[LocationKind.RACK])


def test_no_dock_is_left_undeclared():
    """Every place a robot can be sent must resolve."""
    records = InMemoryRecords()
    plant.declare_locations(records)
    missing = [d for d in plant.DOCKS if records.location_kind(d) is None]
    assert not missing, f"undeclared: {missing}"


def test_a_material_location_now_resolves(tmp_path):
    """The join that used to lose rows."""
    for records in stores(tmp_path):
        plant.declare_locations(records)
        material = records.register_material(kind="roll", at=1.0,
                                             location="ASRS")
        where = records.locate(material.material_ref)
        assert records.location_kind(where) is LocationKind.STORE


def test_locations_survive_a_restart(tmp_path):
    path = str(tmp_path / "loc.db")
    first = SqliteRecords(path)
    plant.declare_locations(first)
    before = len(first.locations())
    first.close()

    reopened = SqliteRecords(path)
    assert len(reopened.locations()) == before
    assert reopened.location_kind("ASRS") is LocationKind.STORE


# ======================================================= abnormal reports


def test_a_report_can_be_filed_and_read_back(tmp_path):
    for records in stores(tmp_path):
        report = records.add_abnormal("GRV1_LD", "roll jammed", at=5.0)
        assert report.station == "GRV1_LD"
        assert report.open
        assert [r.report_id for r in records.open_reports()] == \
            [report.report_id]


def test_acknowledging_closes_it(tmp_path):
    for records in stores(tmp_path):
        report = records.add_abnormal("SLT_LD1", "guard open", at=5.0)
        records.acknowledge_report(report.report_id, at=9.0)
        assert not records.open_reports()
        assert records.reports()[0].acknowledged_at == 9.0


def test_acknowledging_something_that_is_not_there_is_not_an_error(tmp_path):
    for records in stores(tmp_path):
        assert records.acknowledge_report("abn_9999", at=1.0) is None


def test_reports_come_back_newest_first(tmp_path):
    for records in stores(tmp_path):
        for n in (1, 2, 3):
            records.add_abnormal("GRV1_LD", f"problem {n}", at=float(n))
        assert [r.description for r in records.reports()] == \
            ["problem 3", "problem 2", "problem 1"]


def test_open_and_none_ever_are_different_states(tmp_path):
    """"No open reports" and "nobody has ever filed one" are not the same."""
    for records in stores(tmp_path):
        assert records.open_reports() == [] and records.reports() == []
        report = records.add_abnormal("CTR1_LD", "alarm", at=1.0)
        records.acknowledge_report(report.report_id, at=2.0)
        assert records.open_reports() == []
        assert len(records.reports()) == 1


# ------------------------------------------------------- THE ACTUAL POINT


def test_a_report_survives_a_restart(tmp_path):
    """Before 2026-08-21 this was impossible: reports lived in a dict."""
    path = str(tmp_path / "reports.db")

    first = SqliteRecords(path)
    filed = first.add_abnormal("GRV2_ULD", "material stuck at the port",
                               reported_by="operator", at=11.0)
    first.close()

    reopened = SqliteRecords(path)
    back = reopened.open_reports()
    assert len(back) == 1, "the report did not survive"
    assert back[0].report_id == filed.report_id
    assert back[0].description == "material stuck at the port"
    assert back[0].reported_by == "operator"
    assert back[0].open


def test_report_ids_are_not_reused_after_a_restart(tmp_path):
    """A restart that reissues abn_0001 would overwrite the first report."""
    path = str(tmp_path / "seq.db")

    first = SqliteRecords(path)
    one = first.add_abnormal("GRV1_LD", "first", at=1.0)
    first.close()

    reopened = SqliteRecords(path)
    two = reopened.add_abnormal("GRV1_LD", "second", at=2.0)
    assert two.report_id != one.report_id
    assert len(reopened.reports()) == 2


def test_the_pda_files_into_the_store(tmp_path):
    """The PDA no longer keeps its own copy."""
    from csm.adapters.mock import ManualClock, MockAcs, MockEquipment
    from csm.pda import Pda
    from csm.runtime.job_store import JobStore

    clock = ManualClock()
    records = SqliteRecords(str(tmp_path / "pda.db"))
    store = JobStore(MockEquipment(list(plant.DOCKS), clock), MockAcs(clock),
                     clock, logger=lambda m: None, records=records)
    pda = Pda(store)

    pda.report_abnormal("CTR3_LD", "coater door will not close")
    assert len(records.open_reports()) == 1, "the PDA kept it to itself"
    assert not hasattr(pda, "_abnormal"), "the PDA still has a private copy"
