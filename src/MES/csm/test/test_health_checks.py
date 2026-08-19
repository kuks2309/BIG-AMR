"""The daily check, as queries.

CATL's own twelve-item list (CCS manual §6) turned into things this system can
answer. The point of these tests is not that the arithmetic works — it is that
each check FIRES when the condition it names is true, and stays quiet when it
is not. A check that cannot go off is decoration.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from csm.ui import health                                        # noqa: E402
from csm.ui.health import ALARM, OK, UNKNOWN, WARN               # noqa: E402


def snapshot(**over):
    """A plant with nothing wrong with it."""
    base = {
        "fleet": [{"name": "amr1", "battery": 80.0, "busy": False,
                   "charging_to": None}],
        "jobs": {"active": [], "finished": []},
        "calls": [],
        "materials": [],
        "racks": [{"rack": "WIP_CTR", "size": 13, "used": 0,
                   "slots": [{"slot": i, "material_ref": None,
                              "occupied": False} for i in range(1, 14)]}],
        "equipment": [{"station": "GRV1_LD", "status": "idle"}],
        "counters": {"commands_lost": 0, "calls_deferred": 0,
                     "jobs_created": 5, "unrested_decisions": 0,
                     "retried": 0, "abandoned": 0, "finished_jobs": 5},
    }
    base.update(over)
    return base


def check(snap, name, now=None):
    return next(c for c in health.run(snap, now=now) if c.name == name)


def test_a_healthy_plant_reports_healthy():
    assert health.worst(health.run(snapshot(), now=100.0)) == OK


def test_every_check_says_where_its_rule_came_from():
    """A threshold with no source is a number somebody invented, and reading
    the manual was how we stopped inventing them."""
    for c in health.run(snapshot(), now=100.0):
        assert c.source, f"{c.name} cites nothing"


# ------------------------------------------------------------ item 10: ageing

def test_a_job_stuck_for_twenty_minutes_is_an_alarm():
    """Their number, not ours: red at 20 minutes (§2.3, §4.3)."""
    snap = snapshot(jobs={"active": [{"job_id": "job_0001", "state": "MOVING",
                                      "state_since": 0.0, "from": "A",
                                      "to": "B"}], "finished": []})
    assert check(snap, "Jobs progressing", now=21 * 60).status is ALARM


def test_a_job_stuck_for_ten_minutes_is_a_warning():
    snap = snapshot(jobs={"active": [{"job_id": "job_0001", "state": "MOVING",
                                      "state_since": 0.0, "from": "A",
                                      "to": "B"}], "finished": []})
    assert check(snap, "Jobs progressing", now=11 * 60).status is WARN


def test_a_job_that_is_moving_along_is_fine():
    snap = snapshot(jobs={"active": [{"job_id": "job_0001", "state": "MOVING",
                                      "state_since": 0.0, "from": "A",
                                      "to": "B"}], "finished": []})
    assert check(snap, "Jobs progressing", now=60.0).status is OK


def test_the_stuck_job_is_named_so_somebody_can_act():
    snap = snapshot(jobs={"active": [{"job_id": "job_0042", "state": "MOVING",
                                      "state_since": 0.0, "from": "A",
                                      "to": "B"}], "finished": []})
    assert any("job_0042" in d
               for d in check(snap, "Jobs progressing", now=25 * 60).detail)


# ------------------------------------------------- item 11: the empty-rack floor

def test_a_full_rack_is_an_alarm():
    """"送满后空车就走" — deliver a full pallet and drive away empty, because
    there is nowhere to put what should have been collected."""
    snap = snapshot(racks=[{"rack": "WIP_CTR", "size": 2, "used": 2,
                            "slots": [{"slot": 1, "material_ref": "m1",
                                       "occupied": True},
                                      {"slot": 2, "material_ref": "m2",
                                       "occupied": True}]}])
    assert check(snap, "Rack headroom").status is ALARM


def test_fewer_than_five_free_slots_is_a_warning():
    """Their floor, stated twice in the manual (§5.3, §6 item 11)."""
    snap = snapshot(racks=[{"rack": "WIP_CTR", "size": 10, "used": 7,
                            "slots": []}])
    assert check(snap, "Rack headroom").status is WARN


def test_plenty_of_room_is_fine():
    assert check(snapshot(), "Rack headroom").status is OK


# ------------------------------------------------- items 1 and 9: availability

def test_a_faulted_station_is_an_alarm():
    snap = snapshot(equipment=[{"station": "GRV1_LD", "status": "fault"},
                               {"station": "CTR1_LD", "status": "idle"}])
    result = check(snap, "Stations available")
    assert result.status is ALARM
    assert result.detail == ["GRV1_LD"]


# ------------------------------------------------------ item 12: reconciliation

def test_material_on_a_rack_with_no_record_is_an_alarm():
    """One of their four record-versus-reality mismatches (§3.4)."""
    snap = snapshot(racks=[{"rack": "WIP_CTR", "size": 2, "used": 1,
                            "slots": [{"slot": 1, "material_ref": "ghost",
                                       "occupied": True}]}],
                    materials=[])
    assert check(snap, "Records match the racks").status is ALARM


def test_material_that_is_on_record_is_fine():
    snap = snapshot(racks=[{"rack": "WIP_CTR", "size": 2, "used": 1,
                            "slots": [{"slot": 1, "material_ref": "lot1",
                                       "occupied": True}]}],
                    materials=[{"lot_id": "lot1", "location": "WIP_CTR"}])
    assert check(snap, "Records match the racks").status is OK


# ------------------------------------------------------------------- ours

def test_a_flat_robot_is_an_alarm():
    snap = snapshot(fleet=[{"name": "amr1", "battery": 0.0, "busy": False,
                            "charging_to": None}])
    assert check(snap, "Batteries").status is ALARM


def test_a_low_robot_is_a_warning():
    snap = snapshot(fleet=[{"name": "amr1", "battery": 22.0, "busy": False,
                            "charging_to": None}])
    assert check(snap, "Batteries").status is WARN


def test_a_robot_told_to_charge_and_still_very_low_is_flagged():
    """The 2026-08-19 bug made visible: parked 0.6 m from the charger, idle,
    reporting charging_to 90, and discharging."""
    snap = snapshot(fleet=[{"name": "amr1", "battery": 8.0, "busy": False,
                            "charging_to": 90.0}])
    assert check(snap, "Charging works").status is WARN


def test_abandoned_work_is_an_alarm_and_retried_work_is_a_warning():
    """They mean different things. A retry is the system coping; an
    abandonment is a machine alarmed and a person needed."""
    counters = dict(snapshot()["counters"])
    assert check(snapshot(counters={**counters, "retried": 2}),
                 "Work completed").status is WARN
    assert check(snapshot(counters={**counters, "abandoned": 1}),
                 "Work completed").status is ALARM


def test_a_lost_command_is_visible_here_or_nowhere():
    counters = dict(snapshot()["counters"], commands_lost=3)
    assert check(snapshot(counters=counters), "Commands took effect").status is WARN


# ------------------------------------------- not knowing is not the same as fine

def test_using_material_without_knowing_if_it_rested_reports_unknown():
    """OK would be a lie and ALARM would be a guess. Customer decision #6."""
    counters = dict(snapshot()["counters"], unrested_decisions=4)
    assert check(snapshot(counters=counters),
                 "Resting respected").status is UNKNOWN


def test_unknown_is_not_swallowed_by_the_overall_verdict():
    """The whole failure mode this page catches is a quiet-looking system.
    'No data' must never render as 'no problem'."""
    counters = dict(snapshot()["counters"], unrested_decisions=1)
    assert health.worst(health.run(snapshot(counters=counters), now=1.0)) is UNKNOWN


def test_alarm_outranks_everything():
    snap = snapshot(fleet=[{"name": "amr1", "battery": 0.0, "busy": False,
                            "charging_to": None}],
                    counters=dict(snapshot()["counters"], unrested_decisions=1))
    assert health.worst(health.run(snap, now=1.0)) is ALARM


# ------------------------------------------------------------- the §4.3 gauge

def test_the_pipeline_shows_where_material_is_piling_up():
    snap = snapshot(
        jobs={"active": [{"job_id": "j1", "state": "WAITING"},
                         {"job_id": "j2", "state": "MOVING"}], "finished": []},
        racks=[{"rack": "WIP_CTR", "size": 13, "used": 4, "slots": []}])
    stages = {s["stage"]: s["count"] for s in health.pipeline(snap)}
    assert stages["Waiting to start"] == 1
    assert stages["Robot on the way"] == 1
    assert stages["Parked on a rack"] == 4
    assert stages["Delivered"] == 5


def test_every_pipeline_stage_explains_itself():
    for stage in health.pipeline(snapshot()):
        assert stage["note"], f"{stage['stage']} has no explanation"
