"""The management view.

Separate from the live view on purpose: one answers "what is happening now",
the other "is anything quietly wrong". A robot idle for twenty minutes looks
perfectly healthy in a picture of the plant.
"""

import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.ui import dashboard, health                             # noqa: E402
from csm.ui.health import ALARM, OK, UNKNOWN                     # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_health_checks import snapshot                          # noqa: E402


# ------------------------------------------------------------------ the data

def test_the_report_is_json_serialisable():
    """It goes down a socket. A dataclass or an enum in there is a 500."""
    json.dumps(dashboard.report(snapshot(), now=100.0))


def test_a_healthy_plant_reads_ok():
    assert dashboard.report(snapshot(), now=100.0)["verdict_text"] == "OK"


def test_the_worst_check_sets_the_headline():
    snap = snapshot(fleet=[{"name": "amr1", "battery": 0.0, "busy": False,
                            "charging_to": None}])
    assert dashboard.report(snap, now=100.0)["verdict"] == ALARM


def test_no_data_is_not_reported_as_ok():
    """The failure this page exists to catch is a quiet-looking system."""
    counters = dict(snapshot()["counters"], unrested_decisions=3)
    report = dashboard.report(snapshot(counters=counters), now=100.0)
    assert report["verdict"] == UNKNOWN
    assert report["verdict_text"] == "NO DATA"


def test_every_check_reaches_the_page_with_its_source():
    report = dashboard.report(snapshot(), now=100.0)
    assert len(report["checks"]) == len(health.run(snapshot(), now=100.0))
    for c in report["checks"]:
        assert c["source"], f"{c['name']} arrives with no source"
        assert c["status_text"]


def test_the_pipeline_reaches_the_page():
    assert len(dashboard.report(snapshot(), now=100.0)["pipeline"]) == 4


def test_a_missing_clock_does_not_crash_it():
    """The server passes None when the node's clock cannot be read."""
    report = dashboard.report(snapshot(), now=None)
    assert report["verdict_text"]


def test_it_survives_a_snapshot_with_nothing_in_it():
    """The page is served before the first job exists, and during shutdown."""
    report = dashboard.report({}, now=1.0)
    assert report["checks"]


# ------------------------------------------------------------------ the page

def test_the_page_is_self_contained():
    """No CDN, no external stylesheet. The plant network has no internet."""
    page = dashboard.page()
    assert "http://" not in page.replace("http://localhost", "")
    assert "https://" not in page


def test_the_page_asks_for_the_endpoint_that_exists():
    assert "'/health'" in dashboard.page()


def test_the_page_links_back_to_the_live_view():
    """They are two views of one system, and a person will want both."""
    assert 'href="/"' in dashboard.page()


def _script_of(page):
    found = re.search(r"<script>(.*?)</script>", page, re.S)
    assert found, "the page has no script block"
    return found.group(1)


def _js_engine():
    """Something that can PARSE JavaScript, or None.

    `gjs` is SpiderMonkey and ships with GNOME, so it is present on the
    development machines here where node is not. It reports a syntax error on
    stderr and still exits 0, so the exit code cannot be the test.
    """
    for exe, args in (("node", ["--check", "-"]), ("gjs", ["-c"])):
        if shutil.which(exe):
            return exe, args
    return None, None


def _parses(script):
    """(ok, message). Wrapped in an uncalled function so it parses but never
    runs — the page's script touches `document` and `fetch`, which do not
    exist outside a browser, and a ReferenceError is not a syntax error."""
    exe, args = _js_engine()
    if exe is None:
        return None, "no JavaScript engine installed"
    wrapped = "(function(){\n" + script + "\n});"
    if exe == "node":
        result = subprocess.run([exe] + args, input=wrapped,
                                capture_output=True, text=True)
    else:
        result = subprocess.run([exe] + args + [wrapped],
                                capture_output=True, text=True)
    output = (result.stderr or "") + (result.stdout or "")
    if "SyntaxError" in output:
        return False, output.strip()
    return result.returncode == 0, output.strip()


@pytest.mark.skipif(_js_engine()[0] is None, reason="no JavaScript engine")
def test_the_javascript_actually_parses():
    """A LOST CHARACTER KILLED THIS UI ONCE.

    On 2026-08-18 an edit turned `const cls = (v, good) =>` into `= `, a
    SyntaxError that killed the whole script. The page still served, the data
    still flowed, and every check made was on the half that worked — the
    failure was only visible by loading the page, which nothing did.

    Python's test suite cannot see a JavaScript syntax error. This can.
    """
    ok, message = _parses(_script_of(dashboard.page()))
    assert ok, message


@pytest.mark.skipif(_js_engine()[0] is None, reason="no JavaScript engine")
def test_the_live_view_javascript_parses_too():
    from csm.ui.page import PAGE

    ok, message = _parses(_script_of(PAGE))
    assert ok, message


@pytest.mark.skipif(_js_engine()[0] is None, reason="no JavaScript engine")
def test_the_check_would_have_caught_the_bug_that_happened():
    """A guard nobody has seen fail is a guard nobody should trust."""
    ok, _ = _parses("const cls = (v, good) => v > 1;")
    assert ok, "valid code must pass"
    ok, message = _parses("const = (v, good) => v > 1;")
    assert not ok, "the exact 2026-08-18 edit must be rejected"
    assert "SyntaxError" in message


def test_the_script_balances_even_without_an_engine():
    """A crude fallback for a machine with neither node nor gjs.

    ⚠ It would NOT have caught the 2026-08-18 bug — `const = x` balances
    perfectly. It catches the other common shape, a truncated edit, and it is
    stated plainly here so nobody reads a green run as full coverage.
    """
    for page in (dashboard.page(), __import__(
            "csm.ui.page", fromlist=["PAGE"]).PAGE):
        script = _script_of(page)
        assert script.count("{") == script.count("}"), "unbalanced braces"
        assert script.count("(") == script.count(")"), "unbalanced brackets"


# ------------------------------------------------------------ one clock only

def test_the_ageing_check_uses_the_stores_own_clock():
    """TWO CLOCKS IS NOT A SMALL ERROR.

    The store stamps jobs with `time.monotonic()` — seconds since boot — and
    the ROS clock reads wall time. Comparing one to the other gives about 1.7
    billion seconds, so every job reads as older than twenty minutes and the
    ageing check reports ACTION permanently. Always-on reads as noise, which
    is worse than off.
    """
    source = (pathlib.Path(__file__).resolve().parents[1]
              / "csm" / "ui" / "server.py").read_text()
    body = source.split("def _clock")[1].split("\ndef ")[0]

    assert "store.clock()" in body, "the ageing check must use the store's clock"
    assert "get_clock().now()" not in body, "the ROS clock is a different clock"


def test_monotonic_stamps_against_wall_time_would_be_caught():
    """The exact numbers from the run. A guard nobody has seen fire is a guard
    nobody should trust."""
    snap = snapshot(jobs={"active": [{"job_id": "job_0003", "state": "RUNNING",
                                      "state_since": 32748.76, "from": "A",
                                      "to": "B"}], "finished": []})
    # Same clock: a job seconds old is fine.
    assert dashboard.report(snap, now=32750.0)["verdict"] != ALARM
    # Mixed clocks: it screams, which is what we saw.
    assert dashboard.report(snap, now=1787128426.6)["verdict"] == ALARM
