"""The records, as tables — what is actually stored, field by field.

Section 7 names six records and every other page shows them interpreted: a job
on a map, a check with a verdict. This shows them RAW, which is the view you
want when the interpretation looks wrong and you need to know whether the data
underneath is wrong too.

IT WORKS WITH OR WITHOUT A DATABASE, and says which. With `--db` the columns
and rows come from SQLite itself — `sqlite_master` and `PRAGMA table_info` —
so the page cannot drift from the real schema. Without one it renders the same
six collections from memory under the same column names, because the SQL schema
was derived from those dataclasses in the first place.

Reading the schema from the database rather than hard-coding it is the whole
point: a page that lists the columns it *believes* exist is a page that will
keep listing them after somebody adds a seventh.
"""

from . import nav

#: How many rows of each table to show. Enough to see a pattern, few enough to
#: read from across a room.
LIMIT = 20

#: The order a person reads them in: what was asked for, what we decided, what
#: it moved, and where things are.
ORDER = ("calls", "decisions", "materials", "material_moves", "rack_slots",
         "stations", "racks")


def collect(store, limit=LIMIT):
    """Every table, newest rows first. Never raises — this is a view."""
    records = getattr(store, "records", None)
    if records is None:
        return {"backend": "none", "note": "no records store", "tables": []}

    db = getattr(records, "db", None)
    if db is not None:
        return {"backend": "sqlite",
                "note": _sqlite_note(records),
                "tables": _from_sqlite(db, limit)}
    return {"backend": "memory",
            "note": ("In memory — nothing here survives a restart. "
                     "Start with db:=<file> to keep it."),
            "tables": _from_memory(records, limit)}


def _sqlite_note(records):
    return ("SQLite — these are the real tables, read from the database "
            "itself, so this page cannot drift from the schema.")


# --------------------------------------------------------------- from SQLite

def _from_sqlite(db, limit):
    out = []
    names = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    for name in _ordered(names):
        columns = [r[1] for r in db.execute(f"PRAGMA table_info({name})")]
        total = db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        # Newest first: the last thing that happened is what a person came to
        # look at. rowid is insertion order and every table here has one.
        rows = db.execute(
            f"SELECT * FROM {name} ORDER BY rowid DESC LIMIT ?", (limit,))
        out.append({"name": name, "columns": columns, "total": total,
                    "rows": [[_cell(v) for v in row] for row in rows]})
    return out


def _cell(value):
    if value is None:
        return None
    if isinstance(value, float):
        # Timestamps are monotonic seconds and print unreadably long.
        return round(value, 2)
    return value


def _ordered(names):
    known = [n for n in ORDER if n in names]
    return known + [n for n in sorted(names) if n not in known]


# --------------------------------------------------------------- from memory

def _from_memory(records, limit):
    """The same six collections, under the same column names.

    Deliberately mirrors the SQL schema rather than exposing whatever the
    dataclasses happen to hold: the two must look the same, or moving from one
    to the other would look like the data changed.
    """
    calls = list(getattr(records, "_calls", {}).values())
    decisions = list(getattr(records, "_decisions", []))
    materials = list(getattr(records, "_materials", {}).values())
    moves = list(getattr(records, "_moves", []))
    stations = list(getattr(records, "_stations", {}).values())
    slots = [s for rack in getattr(records, "_racks", {}).values()
             for s in rack]

    return [
        _table("calls",
               ["call_id", "station", "instance", "task_type", "source",
                "raised_at", "acknowledged_at", "cancelled_at", "job_id",
                "status"],
               [[c.call_id, c.station, c.instance,
                 getattr(c.task_type, "name", c.task_type), c.source,
                 _cell(c.raised_at), _cell(c.acknowledged_at),
                 _cell(getattr(c, "cancelled_at", None)), c.job_id,
                 getattr(c.status, "value", c.status)] for c in calls],
               limit),
        # `seq` is the decisions table's primary key in SQL and is the
        # position in the list here. Same fact, so it is shown either way —
        # otherwise switching backends would look like a column appeared.
        _table("decisions",
               ["seq", "job_id", "decided_at", "chosen_source", "chosen_dest",
                "priority_given", "reason"],
               [[i, d.job_id, _cell(d.decided_at), d.chosen_source,
                 d.chosen_dest, d.priority_given, d.reason]
                for i, d in enumerate(decisions, start=1)], limit),
        # The four routing fields sit at the end, in the order the SQLite
        # schema declares them — the two backends must present the same table
        # or moving from memory to a database looks like the data changed.
        _table("materials",
               ["material_ref", "lot_id", "kind", "created_at", "location",
                "ready_at", "expires_at", "attribute", "drum_type",
                "material_type", "state"],
               [[m.material_ref, m.lot_id, m.kind, _cell(m.created_at),
                 m.location, _cell(m.ready_at), _cell(m.expires_at),
                 getattr(m.attribute, "name", m.attribute), m.drum_type,
                 m.material_type, getattr(m.state, "name", m.state)]
                for m in materials], limit),
        _table("material_moves",
               ["material_ref", "seq", "at", "from_location", "to_location",
                "job_id", "note"],
               [[m.material_ref, m.seq, _cell(m.at), m.from_location,
                 m.to_location, m.job_id, m.note] for m in moves], limit),
        _table("rack_slots",
               ["rack", "slot", "material_ref", "parked_by_job", "parked_at",
                "retrieved_at"],
               [[s.rack, s.slot, s.material_ref, s.parked_by_job,
                 _cell(s.parked_at), _cell(s.retrieved_at)] for s in slots],
               limit),
        _table("stations",
               ["our_name", "instance", "customer_port_id"],
               [[s.our_name, s.instance, s.customer_port_id]
                for s in stations], limit),
    ]


def _table(name, columns, rows, limit):
    """Newest last in memory, so the tail is the newest — same as SQLite's
    `ORDER BY rowid DESC`, which is what the reader is comparing against."""
    return {"name": name, "columns": columns, "total": len(rows),
            "rows": list(reversed(rows))[:limit]}


# ------------------------------------------------------------------ the page

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CSM — records</title>
<style>
 :root { --bg:#12141a; --card:#1b1e26; --line:#2b3040; --text:#e8eaf0;
         --dim:#9aa3b8; --accent:#7fb2ff; }
 * { box-sizing:border-box; }
 body { margin:0; background:var(--bg); color:var(--text);
        font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
 header { padding:16px 24px; border-bottom:1px solid var(--line);
          display:flex; align-items:center; gap:20px; flex-wrap:wrap; }
 h1 { margin:0; font-size:18px; font-weight:600; }
 __NAVCSS__
 .backend { font-size:12.5px; color:var(--dim); margin-left:auto;
            max-width:520px; text-align:right; }
 main { padding:18px 24px 40px; }
 .tbl { background:var(--card); border:1px solid var(--line);
        border-radius:10px; margin-bottom:18px; overflow:hidden; }
 .cap { padding:11px 15px; border-bottom:1px solid var(--line);
        display:flex; align-items:baseline; gap:12px; }
 .cap b { font-size:14.5px; font-family:ui-monospace,Menlo,monospace; }
 .cap span { color:var(--dim); font-size:12.5px; }
 .scroll { overflow-x:auto; }
 table { border-collapse:collapse; width:100%;
         font:12.5px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace; }
 th { text-align:left; padding:7px 12px; color:var(--dim);
      border-bottom:1px solid var(--line); white-space:nowrap;
      font-weight:600; position:sticky; top:0; background:var(--card); }
 td { padding:6px 12px; border-bottom:1px solid rgba(43,48,64,.5);
      white-space:nowrap; }
 tr:last-child td { border-bottom:none; }
 .null { color:#5b6478; font-style:italic; }
 .empty { padding:14px 15px; color:var(--dim); font-size:13px; }
</style></head>
<body>
<header>
  <h1>CSM — records</h1>
  __NAV__
  <span class="backend" id="backend">…</span>
</header>
<main id="tables"></main>
<script>
const esc = (s) => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
                            .replace(/>/g,'&gt;');

function render(d) {
  document.getElementById('backend').textContent = d.note;
  document.getElementById('tables').innerHTML = d.tables.map(t => {
    const head = t.columns.map(c => `<th>${esc(c)}</th>`).join('');
    const body = t.rows.map(r => '<tr>' + r.map(v =>
      v === null ? '<td class="null">null</td>' : `<td>${esc(v)}</td>`
    ).join('') + '</tr>').join('');
    const shown = t.rows.length;
    return `<div class="tbl">
      <div class="cap"><b>${esc(t.name)}</b>
        <span>${t.columns.length} fields ·
          ${t.total} row${t.total === 1 ? '' : 's'}${
            t.total > shown ? ', newest ' + shown + ' shown' : ''}</span></div>
      ${shown ? `<div class="scroll"><table><thead><tr>${head}</tr></thead>
                 <tbody>${body}</tbody></table></div>`
              : `<div class="scroll"><table><thead><tr>${head}</tr></thead>
                 </table></div><div class="empty">no rows yet</div>`}
    </div>`;
  }).join('') || '<div class="empty">no tables</div>';
}

async function tick() {
  try { render(await (await fetch('/tables.json', {cache:'no-store'})).json()); }
  catch (e) { document.getElementById('backend').textContent = 'no connection'; }
}
tick();
setInterval(tick, 3000);
</script>
</body></html>
"""


def page():
    return (PAGE.replace("__NAV__", nav.bar("/tables"))
                .replace("__NAVCSS__", nav.CSS))
