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
        "fleet": _fleet(node),
        "jobs": _jobs(store),
        "calls": _calls(store),
        "materials": _materials(store),
        "racks": _racks(store),
        "equipment": _equipment(node, store),
        "decisions": _decisions(store),
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
    }


def _family(name):
    for prefix, kind in (("ASRS", "store"), ("GRV", "gravure"),
                         ("CTR", "coater"), ("SLT", "slitter"),
                         ("WIP", "rack")):
        if name.startswith(prefix):
            return kind
    return "other"


def _fleet(node):
    acs = getattr(node, "acs", None)
    if acs is None or not hasattr(acs, "fleet_status"):
        return []
    rows = _safe(acs.fleet_status, []) or []
    for row in rows:
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
        "calls_deferred": _safe(lambda: monitor.deferred, 0),
        # Commands accepted and never seen to take effect. On this protocol
        # that is the only way a lost command is visible at all.
        "commands_lost": _safe(lambda: monitor.commands_lost, 0),
        # How often material was used without knowing whether it had rested.
        # Blocked on customer open decision #6.
        "unrested_decisions": _safe(lambda: records.unrested_decisions, 0),
        "active_jobs": _safe(lambda: len(store.active), 0),
        "finished_jobs": _safe(lambda: len(store.finished), 0),
    }
