"""Everything the CSM knows, collected into one JSON-shaped dict.

WHAT THIS IS FOR. A simulation that only prints log lines can be watched but
not INSPECTED: you can see that a robot stopped, and not why; that a job is
waiting, and not what it is waiting for. Every one of those questions cost a
long detour today, and the answers were already in memory — just not reachable.

READ-ONLY, AND IT MATTERS. Nothing here writes, claims, decides or advances
anything. A view that can change what it is looking at is no longer a view, and
an operator screen that can accidentally dispatch a robot is worse than none.

⚠ It reads live objects. If a value is missing or half-written the answer is
None rather than an exception — a monitor that crashes the thing it is
monitoring is not a monitor.
"""

from .. import plant
from ..adapters import roads

#: The road graph, built once. It is static geometry — the same 119 nodes and
#: 304 one-way lanes every time — and building it on every poll would cost a
#: full clearance check twice a second for an answer that cannot change.
#:
#: `roads.build()` RAISES on an obstructed lane, and a view must never be the
#: thing that stops the plant, so a failure here leaves the map roadless
#: rather than taking the dashboard down with it.
try:
    _ROADS = roads.build()
except Exception:                                   # pragma: no cover
    _ROADS = None


def _safe(fn, default=None):
    """Read something from a live system without ever being the thing that fails."""
    try:
        return fn()
    except Exception:
        return default


def collect(node):
    """One snapshot: the plant, the fleet, the work and the records."""
    store = getattr(node, "app", None)
    store = getattr(store, "store", None)
    return {
        "plant": _plant(),
        "fleet": _fleet(node, store),
        "jobs": _jobs(store),
        "calls": _calls(store),
        "materials": _materials(store),
        "racks": _racks(store),
        "equipment": _equipment(node, store),
        "decisions": _decisions(store),
        "pda": _pda(node, store),
        "counters": _counters(node, store),
    }


def _plant():
    """The floor. Static, but the page needs it to draw anything."""
    return {
        "hall": {"w": plant.HALL_W, "e": plant.HALL_E,
                 "s": plant.HALL_S, "n": plant.HALL_N},
        "machine_size": [plant.MACHINE_W, plant.MACHINE_D],
        "robot_size": [plant.ROBOT_L, plant.ROBOT_W],
        "machines": [{"name": n, "x": xy[0], "y": xy[1],
                      "kind": _family(n)}
                     for n, xy in plant.OBSTACLES.items()],
        "docks": [{"name": n, "x": xy[0], "y": xy[1]}
                  for n, xy in plant.DOCKS.items()],
        "parking": [{"name": f"{seg}{i + 1}", "x": xy[0], "y": xy[1],
                     "leg": seg,
                     # A charger is a parking slot with power, so the map
                     # marks the slot rather than drawing a separate thing.
                     "charger": xy in plant.CHARGERS.get(seg, [])}
                    for seg, slots in plant.PARKING_SLOTS.items()
                    for i, xy in enumerate(slots)],
        "roads": _roads(),
    }


def _roads():
    """The lane network, as flat coordinate runs the page can draw directly.

    RULE 1 IS "EVERY ROBOT FOLLOWS THE LINES", and until now the lines were
    the one thing on the plant the map did not show. A robot standing still
    beside a machine and a robot standing still ON a one-way lane look
    identical without them.

    Grouped by kind rather than sent as objects: 304 lanes as
    ``{"x1":..,"y1":..}`` is three times the payload of four numbers each,
    twice a second, for geometry that never changes. Two decimals is a
    centimetre, which is finer than anything on a 64 m map can show.
    """
    if _ROADS is None:
        return {}
    out = {"inner": [], "outer": [], "spur": [], "cross": []}
    for a, b in _ROADS.lanes:
        (ax, ay), (bx, by) = _ROADS.nodes[a], _ROADS.nodes[b]
        if a.startswith(("dock_", "park_")) or b.startswith(("dock_", "park_")):
            kind = "spur"
        elif a.endswith("_inner") and b.endswith("_inner"):
            kind = "inner"
        elif a.endswith("_outer") and b.endswith("_outer"):
            kind = "outer"
        else:
            # One end on each ring: the cross-link that IS the ring change,
            # and the only place a robot may change ring.
            kind = "cross"
        out[kind] += [round(ax, 2), round(ay, 2), round(bx, 2), round(by, 2)]
    return out


def _family(name):
    for prefix, kind in (("ASRS", "store"), ("GRV", "gravure"),
                         ("CTR", "coater"), ("SLT", "slitter"),
                         ("WIP", "rack")):
        if name.startswith(prefix):
            return kind
    return "other"


#: How a drum type reads on the map. The customer's own four values, and the
#: rule that comes with them: >= 500 is a single-bobbin pallet, < 500 is a
#: dual-bobbin pallet (CCS manual §4.6.5, and the rack PLC table).
_DRUM_SIZES = {360: 0.34, 430: 0.40, 500: 0.46, 580: 0.52}


def _payload(store, row):
    """What this robot is carrying, for the map to draw.

    Joined by JOB ID, not held on the robot. The vehicle layer observes only
    that something is on its deck (`loaded`); WHAT it is belongs to the CSM's
    material record, and a second copy on the robot would be a second copy
    that drifts.

    Everything here degrades to None rather than guessing. A robot carrying
    something we cannot describe still draws — as an unlabelled shape — because
    "carrying something unknown" is a real and interesting state, and drawing
    nothing would report an empty robot.
    """
    if not row.get("loaded"):
        return None
    #: Loaded, and we cannot say what. Every failure below lands here rather
    #: than on None: the robot IS carrying something, and reporting an empty
    #: robot because our own lookup failed is a worse answer than admitting we
    #: do not know what is on the deck.
    unknown = {"kind": "roll"}
    if store is None:
        return unknown
    job_id = row.get("job_id")
    if not job_id:
        return unknown
    # The active list is the only index there is, and it is short — ten robots
    # means at most ten jobs in flight. A dict keyed by id would be faster and
    # would be a second thing to keep in step with `active`.
    job = _safe(lambda: next((r.job for r in store.active
                              if r.job.job_id == job_id), None))
    ref = getattr(job, "material_ref", None) if job else None
    if not ref:
        return unknown
    m = _safe(lambda: store.records.material(ref))
    if m is None:
        return unknown
    face = getattr(getattr(m, "attribute", None), "face", None)
    return {
        "ref": m.material_ref,
        "kind": m.kind,                                  # roll | bobbin
        "drum_type": m.drum_type,
        "size": _DRUM_SIZES.get(m.drum_type, 0.40),
        #: bright / dark. The attribute IS a face colour, which is why it is
        #: what the map colours by — and it varies, where polarity in this
        #: simulator does not (the whole line modelled is cathode).
        "face": getattr(face, "value", face),
        #: The other half of the attribute. Drawn as a clock hand rather than
        #: a colour because it is the SOFT half: a 180° turn of the pallet
        #: swaps it, and that turn is a first-class AGV task (§1.3, §3.8).
        #: The face cannot be fixed by any manoeuvre, which is why the face
        #: gets the colour.
        "rotation": getattr(getattr(getattr(m, "attribute", None),
                                    "rotation", None), "value", None),
        #: The customer's 1-4, so a reader can name what they are looking at.
        "attribute": getattr(getattr(m, "attribute", None), "value", None),
        "material_type": m.material_type,
    }


def _fleet(node, store=None):
    acs = getattr(node, "acs", None)
    if acs is None or not hasattr(acs, "fleet_status"):
        return []
    rows = _safe(acs.fleet_status, []) or []
    for row in rows:
        row["payload"] = _payload(store, row)
        # The page draws a heading, which fleet_status does not carry.
        robot = next((r for r in getattr(acs, "robots", [])
                      if r.name == row.get("name")), None)
        row["yaw"] = _safe(lambda: robot.pose[2]) if robot else None
        row["goal"] = _safe(lambda: list(robot._goal)) if robot else None
        row["leg_target"] = _safe(
            lambda: robot._to if robot._leg == "deliver" else robot._from
        ) if robot else None
    return rows


def _jobs(store):
    if store is None:
        return {"active": [], "finished": []}

    def row(job, finished):
        return {
            "job_id": job.job_id,
            "state": job.state_name,
            "from": job.from_station,
            "to": job.to_station,
            "from_instance": job.from_instance,
            "to_instance": job.to_instance,
            "object": _safe(lambda: job.carries.value),
            "priority": job.priority,
            "call_id": job.call_id,
            "material_ref": job.material_ref,
            "acs_order_id": job.acs_order_id,
            "created_at": job.created_at,
            "state_since": job.state_since,
            "failure_reason": job.failure_reason,
            "finished": finished,
        }

    return {
        "active": [row(r.job, False) for r in _safe(lambda: list(store.active), []) or []],
        # Newest first: the last thing that happened is what a person looks at.
        "finished": [row(j, True) for j in
                     list(reversed(_safe(lambda: list(store.finished), []) or []))[:40]],
    }


def _calls(store):
    records = getattr(store, "records", None)
    if records is None:
        return []
    calls = _safe(lambda: list(records._calls.values()), []) or []
    return [{
        "call_id": c.call_id, "station": c.station, "instance": c.instance,
        "task_type": _safe(lambda: c.task_type.name),
        "source": c.source, "status": _safe(lambda: c.status.value),
        "raised_at": c.raised_at, "acknowledged_at": c.acknowledged_at,
        "job_id": c.job_id,
    } for c in calls[-60:]]


def _materials(store):
    records = getattr(store, "records", None)
    if records is None:
        return []
    materials = _safe(lambda: list(records._materials.values()), []) or []
    return [{
        "lot_id": m.lot_id, "kind": m.kind, "location": m.location,
        "created_at": m.created_at, "ready_at": m.ready_at,
        "moves": len(_safe(lambda: records.history_of(m.material_ref), []) or []),
    } for m in materials[-60:]]


def _racks(store):
    records = getattr(store, "records", None)
    if records is None:
        return []
    out = []
    for rack in _safe(lambda: list(records._racks), []) or []:
        slots = _safe(lambda: records.slots(rack), []) or []
        out.append({
            "rack": rack,
            "size": len(slots),
            "used": sum(1 for s in slots if s.occupied),
            "slots": [{"slot": s.slot, "material_ref": s.material_ref,
                       "job": s.parked_by_job, "occupied": s.occupied}
                      for s in slots],
        })
    return out


def _equipment(node, store):
    """Per station, what the machine itself is saying.

    This is the part with no other way to see it: presence booleans and entry
    permission never appear in a log line, and they are exactly what decides
    whether a robot may move.
    """
    equipment = getattr(node, "equipment", None)
    if equipment is None:
        return []
    stations = _safe(equipment.list_stations, []) or []
    out = []
    for s in stations:
        out.append({
            "station": s,
            "mc_num": _safe(lambda: str(equipment.machine_number(s))
                            if equipment.machine_number(s) else None),
            "status": _safe(lambda: equipment.get_station_status(s).value),
            "presence": _safe(lambda: equipment.presence(s).value
                              if equipment.presence(s) else None),
            "task_processing": _safe(
                lambda: equipment.task_processing(s).name
                if equipment.task_processing(s) else None),
            "can_accept": _safe(lambda: equipment.can_accept(s)),
            "enter_permitted": _safe(
                lambda: equipment._enter_permitted.get(s)),
            "heartbeat": _safe(lambda: equipment._heartbeat_on.get(s)),
        })
    return out


def _pda(node, store):
    """The handheld's side of things: what a person has raised.

    TWO DIFFERENT THINGS, and they are kept apart on purpose. An abnormal
    report is a person saying something is wrong and is not in specification
    section 7 at all; a manual call is ordinary work that happens to have been
    raised by hand. Merging them would hide the first inside the volume of the
    second.

    Reports are counted whether open or closed, because "none open" and "none
    ever" are different states and only one of them is good news.
    """
    pda = getattr(node, "pda", None)
    if pda is None:
        return {"available": False, "reports": [], "open_reports": 0,
                "manual_calls": 0, "position_codes": 0}

    # From the RECORDS STORE, not from the PDA object. Reports moved there on
    # 2026-08-21 so they survive a restart; reading the old private dict here
    # silently showed zero after the move, which is exactly the kind of stale
    # read a panel cannot report on itself.
    records = getattr(store, "records", None)
    reports = _safe(lambda: records.reports(), []) or []
    calls = _safe(lambda: list(records._calls.values()), []) or []
    return {
        "available": True,
        # Empty until customer question Q18 is answered; shown so the gap is
        # visible on the page rather than only in a document.
        "position_codes": len(getattr(pda, "position_codes", {}) or {}),
        "open_reports": sum(1 for r in reports if r.open),
        "total_reports": len(reports),
        "manual_calls": sum(1 for c in calls
                            if _safe(lambda: c.source) == "PDA"),
        "reports": [{
            "report_id": r.report_id,
            "station": r.station,
            "description": r.description,
            "reported_by": r.reported_by,
            "reported_at": r.reported_at,
            "open": r.open,
        } for r in reports[-20:]],
    }


def _decisions(store):
    records = getattr(store, "records", None)
    if records is None:
        return []
    decisions = _safe(lambda: list(records._decisions), []) or []
    return [{"job_id": d.job_id, "at": d.decided_at,
             "source": d.chosen_source, "dest": d.chosen_dest,
             "priority": d.priority_given, "reason": d.reason}
            for d in decisions[-40:]][::-1]


def _counters(node, store):
    """The numbers that say whether anything is quietly going wrong."""
    app = getattr(node, "app", None)
    tasks = _safe(lambda: list(app.tasks), []) or []
    monitor = next((t for t in tasks if t.name == "equipment_monitor"), None)
    records = getattr(store, "records", None)
    return {
        "jobs_created": _safe(lambda: monitor.created, 0),
        "bobbins_returned": _safe(lambda: monitor.returned, 0),
        "diverted_to_rack": _safe(lambda: monitor.diverted, 0),
        # Cumulative, one per CALL — not one per poll. The gauge beside it is
        # what says whether the line is behind right now; the total only says
        # it happened at some point during the run.
        "calls_deferred": _safe(lambda: monitor.deferred, 0),
        "calls_deferred_now": _safe(lambda: monitor.deferred_now, 0),
        # Calls refused because their leg had reached its §2.15 ceiling. Apart
        # from the rest because the cure is opposite: this line is full, rather
        # than nothing upstream having anything to give.
        "calls_at_ceiling": _safe(lambda: monitor.at_ceiling, 0),
        # Commands accepted and never seen to take effect. On this protocol
        # that is the only way a lost command is visible at all.
        "commands_lost": _safe(lambda: monitor.commands_lost, 0),
        # How often material was used without knowing whether it had rested.
        # Blocked on customer open decision #6.
        "unrested_decisions": _safe(lambda: records.unrested_decisions, 0),
        "active_jobs": _safe(lambda: len(store.active), 0),
        "finished_jobs": _safe(lambda: len(store.finished), 0),
        # Work raised again after a failure, and work finally given up on.
        # Apart from each other on purpose: a retry is the system coping, an
        # abandonment is a machine alarmed and a person needed.
        "retried": _safe(lambda: store.retried, 0),
        "abandoned": _safe(lambda: store.abandoned, 0),
    }
