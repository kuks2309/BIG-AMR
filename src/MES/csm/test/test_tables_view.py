"""The records, shown raw.

Every other page shows them interpreted — a job on a map, a check with a
verdict. This is the view you want when the interpretation looks wrong and you
need to know whether the data underneath is wrong too.
"""

import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime                                    # noqa: E402

from csm.adapters.base import TaskType                           # noqa: E402
from csm.records import Decision, InMemoryRecords                # noqa: E402
from csm.records_sqlite import SqliteRecords                     # noqa: E402
from csm.ui import dashboard, nav, page as live, tables          # noqa: E402

RACKS = {"WIP_CTR": 3}


class _Store:
    def __init__(self, records):
        self.records = records


def filled(records):
    """A little of everything, so every table has something in it."""
    call = records.add_call("GRV1_LD", TaskType.LOAD, "machine", 1.0)
    records.acknowledge_call(call.call_id, at=2.0, job_id="job_0001")
    records.add_decision(Decision(job_id="job_0001", decided_at=1.0,
                                  chosen_source="ASRS", chosen_dest="GRV1_LD",
                                  reason="nearest source"))
    material = records.register_material(kind="roll", at=1.0, location="ASRS")
    records.move_material(material.material_ref, "GRV1_LD", at=3.0,
                          job_id="job_0001")
    records.park("WIP_CTR", material.material_ref, "job_0001", at=4.0)
    records.map_station("GRV1_LD", "2A01")
    return _Store(records)


def by_name(result):
    return {t["name"]: t for t in result["tables"]}


# ------------------------------------------------------------ with a database

def test_the_columns_come_from_the_database_itself(tmp_path):
    """Not from a list in this file. A page that lists the columns it BELIEVES
    exist keeps listing them after somebody adds a seventh."""
    store = filled(SqliteRecords(str(tmp_path / "t.db"), rack_sizes=RACKS))
    result = tables.collect(store)

    assert result["backend"] == "sqlite"
    calls = by_name(result)["calls"]
    assert "cancelled_at" in calls["columns"], \
        "a column added to the schema must appear without touching this page"


def test_every_record_type_is_there(tmp_path):
    store = filled(SqliteRecords(str(tmp_path / "t.db"), rack_sizes=RACKS))
    got = set(by_name(tables.collect(store)))
    assert {"calls", "decisions", "materials", "material_moves",
            "rack_slots", "stations"} <= got


def test_the_rows_are_the_real_ones(tmp_path):
    store = filled(SqliteRecords(str(tmp_path / "t.db"), rack_sizes=RACKS))
    calls = by_name(tables.collect(store))["calls"]

    assert calls["total"] == 1
    row = dict(zip(calls["columns"], calls["rows"][0]))
    assert row["station"] == "GRV1_LD"
    assert row["job_id"] == "job_0001"
    assert row["status"] == "acknowledged"


def test_newest_first(tmp_path):
    """The last thing that happened is what a person came to look at."""
    records = SqliteRecords(str(tmp_path / "t.db"), rack_sizes=RACKS)
    for i in range(5):
        records.add_call(f"GRV{i}_LD", TaskType.LOAD, "machine", float(i))
    calls = by_name(tables.collect(_Store(records)))["calls"]
    stations = [dict(zip(calls["columns"], r))["station"] for r in calls["rows"]]
    assert stations[0] == "GRV4_LD"


def test_only_a_screenful_is_returned(tmp_path):
    """Enough to see a pattern, few enough to read from across a room."""
    records = SqliteRecords(str(tmp_path / "t.db"), rack_sizes=RACKS)
    for i in range(60):
        records.add_call("GRV1_LD", TaskType.LOAD, "machine", float(i))
    calls = by_name(tables.collect(_Store(records)))["calls"]

    assert calls["total"] == 60, "the true count is still reported"
    assert len(calls["rows"]) == tables.LIMIT


def test_sqlite_internal_tables_are_hidden(tmp_path):
    store = filled(SqliteRecords(str(tmp_path / "t.db"), rack_sizes=RACKS))
    assert not [t for t in tables.collect(store)["tables"]
                if t["name"].startswith("sqlite_")]


# --------------------------------------------------------- without a database

def test_it_still_works_in_memory():
    """Most runs have no database. A page that is blank by default is a page
    nobody trusts when it does have something to say."""
    result = tables.collect(filled(InMemoryRecords(rack_sizes=RACKS)))

    assert result["backend"] == "memory"
    assert by_name(result)["calls"]["total"] == 1


def test_it_says_the_records_will_not_survive():
    result = tables.collect(filled(InMemoryRecords(rack_sizes=RACKS)))
    assert "restart" in result["note"]
    assert "db:=" in result["note"], "and how to change that"


def test_both_backends_show_the_same_columns(tmp_path):
    """Moving from memory to a database must not look like the data changed."""
    mem = by_name(tables.collect(filled(InMemoryRecords(rack_sizes=RACKS))))
    sql = by_name(tables.collect(
        filled(SqliteRecords(str(tmp_path / "t.db"), rack_sizes=RACKS))))
    for name in ("calls", "decisions", "materials", "material_moves",
                 "rack_slots", "stations"):
        assert mem[name]["columns"] == sql[name]["columns"], name


def test_a_store_with_no_records_does_not_crash():
    assert tables.collect(None)["tables"] == []
    assert tables.collect(_Store(None))["tables"] == []


def test_the_result_is_json_serialisable(tmp_path):
    json.dumps(tables.collect(
        filled(SqliteRecords(str(tmp_path / "t.db"), rack_sizes=RACKS))))


# ------------------------------------------------------------- navigation

def test_every_page_carries_every_link():
    """A fourth view must appear on all of them or none."""
    for html in (live.page(), dashboard.page(), tables.page()):
        for href, label in nav.PAGES:
            assert f'href="{href}"' in html, f"{label} missing"


def test_no_placeholder_survives_into_a_served_page():
    for html in (live.page(), dashboard.page(), tables.page()):
        assert "__NAV__" not in html
        assert "__NAVCSS__" not in html


def test_each_page_marks_itself_as_the_current_one():
    """Marked, not un-linked: a link that silently does nothing is worse than
    one that reloads."""
    for path, html in (("/", live.page()), ("/dashboard", dashboard.page()),
                       ("/tables", tables.page())):
        assert f'<a href="{path}" class="here">' in html, path


def test_the_records_page_is_self_contained():
    assert "http://" not in tables.page()
    assert "https://" not in tables.page()


def _script(html):
    return re.search(r"<script>(.*?)</script>", html, re.S).group(1)


def test_the_records_page_javascript_parses():
    if not shutil.which("gjs") and not shutil.which("node"):
        return
    exe = "gjs" if shutil.which("gjs") else "node"
    wrapped = "(function(){\n" + _script(tables.page()) + "\n});"
    args = [exe, "-c", wrapped] if exe == "gjs" else [exe, "--check", "-"]
    result = subprocess.run(args, input=None if exe == "gjs" else wrapped,
                            capture_output=True, text=True)
    assert "SyntaxError" not in (result.stderr or "") + (result.stdout or ""), \
        result.stderr
