"""The page itself. One file, no build step, no external assets.

Embedded as a string rather than shipped as a data file so that colcon has
nothing to package and the view cannot go missing from an install.
"""

from . import nav

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>CSM — live</title>
<style>
__NAVCSS__
  :root {
    --bg:#0e1116; --panel:#161b22; --line:#242c38; --ink:#d6deeb;
    --dim:#7d8799; --accent:#4c9aff; --ok:#3fb950; --warn:#d29922;
    --bad:#f85149; --roll:#4c9aff; --bobbin:#bc8cff;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:13px/1.45 ui-monospace,"SF Mono",Menlo,Consolas,monospace; }
  header { display:flex; align-items:baseline; gap:16px; padding:10px 16px;
           border-bottom:1px solid var(--line); position:sticky; top:0;
           background:var(--bg); z-index:5; flex-wrap:wrap; }
  h1 { font-size:14px; margin:0; letter-spacing:.08em; text-transform:uppercase; }
  .stat { color:var(--dim); }
  .stat b { color:var(--ink); font-weight:600; }
  .stat.bad b { color:var(--bad); }
  .stat.warn b { color:var(--warn); }
  #stale { color:var(--bad); display:none; }
  main { display:grid; grid-template-columns: 1fr 1fr; gap:12px; padding:12px; }
  section { background:var(--panel); border:1px solid var(--line);
            border-radius:6px; overflow:hidden; }
  section.wide { grid-column:1 / -1; }
  h2 { font-size:11px; margin:0; padding:7px 10px; color:var(--dim);
       letter-spacing:.1em; text-transform:uppercase;
       border-bottom:1px solid var(--line); display:flex; gap:8px; }
  h2 span { color:var(--ink); }
  table { width:100%; border-collapse:collapse; }
  th { text-align:left; font-weight:500; color:var(--dim); padding:4px 8px;
       border-bottom:1px solid var(--line); position:sticky; top:0;
       background:var(--panel); font-size:11px; }
  td { padding:3px 8px; border-bottom:1px solid rgba(255,255,255,.03);
       white-space:nowrap; }
  tr:hover td { background:rgba(76,154,255,.06); }
  .scroll { max-height:260px; overflow:auto; }
  .tall { max-height:420px; }
  .muted { color:var(--dim); }
  .ok { color:var(--ok); } .warn { color:var(--warn); } .bad { color:var(--bad); }
  .pill { padding:0 6px; border-radius:9px; font-size:11px;
          border:1px solid var(--line); }
  .empty { padding:14px; color:var(--dim); }
  svg { display:block; width:100%; height:auto; background:#0b0e13; }
  .mach { fill:#1d2530; stroke:#2d3a4d; }
  .mach.store { fill:#3a2f12; stroke:#7a6320; }
  .mach.rack  { fill:#2a2136; stroke:#4d3b63; }
  .dock { fill:#2b3442; }
  .park { fill:none; stroke:#39465a; stroke-dasharray:2 2; }
  .lbl  { fill:#6b7688; font-size:1.05px; }
  .rname{ fill:#dbe4f0; font-size:1.5px; font-weight:600; }
</style>
</head>
<body>
<header>
  <h1>CSM live</h1>
  __NAV__
  <span class="stat">jobs <b id="c-active">0</b> active / <b id="c-done">0</b> done</span>
  <span class="stat">created <b id="c-created">0</b></span>
  <span class="stat">bobbins <b id="c-bobbin">0</b></span>
  <span class="stat">diverted <b id="c-divert">0</b></span>
  <span class="stat">deferred <b id="c-defer">0</b></span>
  <span class="stat" id="s-lost">cmds lost <b id="c-lost">0</b></span>
  <span class="stat" id="s-unrested">unrested <b id="c-unrested">0</b></span>
  <span class="stat">updated <b id="c-age">–</b></span>
  <span id="stale">— not updating —</span>
</header>

<main>
  <section class="wide">
    <h2>plant <span id="m-note" class="muted"></span></h2>
    <svg id="map" viewBox="0 0 100 60" preserveAspectRatio="xMidYMid meet"></svg>
  </section>

  <section>
    <h2>fleet <span id="n-fleet"></span></h2>
    <div class="scroll"><table id="t-fleet"></table></div>
  </section>

  <section>
    <h2>equipment <span id="n-equip"></span></h2>
    <div class="scroll"><table id="t-equip"></table></div>
  </section>

  <section>
    <h2>active jobs <span id="n-jobs"></span></h2>
    <div class="scroll tall"><table id="t-jobs"></table></div>
  </section>

  <section>
    <h2>finished <span id="n-fin"></span></h2>
    <div class="scroll tall"><table id="t-fin"></table></div>
  </section>

  <section>
    <h2>racks <span id="n-racks"></span></h2>
    <div class="scroll"><table id="t-racks"></table></div>
  </section>

  <section>
    <h2>materials <span id="n-mat"></span></h2>
    <div class="scroll"><table id="t-mat"></table></div>
  </section>

  <section>
    <h2>calls <span id="n-calls"></span></h2>
    <div class="scroll"><table id="t-calls"></table></div>
  </section>

  <section>
    <h2>decisions — why <span id="n-dec"></span></h2>
    <div class="scroll"><table id="t-dec"></table></div>
  </section>
</main>

<script>
const $ = id => document.getElementById(id);
let PLANT = null, failures = 0;

function table(el, cols, rows, cell) {
  if (!rows.length) { el.innerHTML =
      '<tr><td class="empty">nothing yet</td></tr>'; return; }
  let h = '<tr>' + cols.map(c => '<th>' + c + '</th>').join('') + '</tr>';
  for (const r of rows) h += '<tr>' + cell(r).map(v =>
      '<td>' + (v === null || v === undefined ? '<span class="muted">–</span>' : v)
      + '</td>').join('') + '</tr>';
  el.innerHTML = h;
}
const n1 = v => (v === null || v === undefined) ? null : (+v).toFixed(1);
function battery(r) {
  if (r.battery === null || r.battery === undefined) return null;
  const v = r.battery;
  const c = v <= 12 ? 'bad' : (v <= 30 ? 'warn' : 'ok');
  const charging = r.charging_to ? ' <span class="muted">&#8593;'
                                   + r.charging_to + '</span>' : '';
  return `<span class="${c}">${v.toFixed(0)}%</span>${charging}`;
}
const cls = (v, good) => '<span class="' + (v === good ? 'ok' : 'bad') + '">' + v + '</span>';

/* ---- the map ------------------------------------------------------- */
function drawPlant(p) {
  const pad = 1.5;
  const w = p.hall.e - p.hall.w + pad * 2, h = p.hall.n - p.hall.s + pad * 2;
  const svg = $('map');
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  // y is flipped: the plant has north up, SVG has y growing downward.
  const X = x => x - p.hall.w + pad, Y = y => p.hall.n - y + pad;
  let s = `<rect x="0" y="0" width="${w}" height="${h}" fill="#0b0e13"/>`;
  s += `<rect x="${X(p.hall.w)}" y="${Y(p.hall.n)}" width="${p.hall.e-p.hall.w}"
        height="${p.hall.n-p.hall.s}" fill="none" stroke="#2a3341" stroke-width="0.25"/>`;
  const [mw, md] = p.machine_size;
  for (const m of p.machines) {
    s += `<rect class="mach ${m.kind}" x="${X(m.x)-mw/2}" y="${Y(m.y)-md/2}"
          width="${mw}" height="${md}" rx="0.3"/>`;
    s += `<text class="lbl" x="${X(m.x)}" y="${Y(m.y)+0.4}"
          text-anchor="middle">${m.name}</text>`;
  }
  for (const d of p.docks)
    s += `<circle class="dock" cx="${X(d.x)}" cy="${Y(d.y)}" r="0.3"/>`;
  const [rl, rw] = p.robot_size;
  for (const k of p.parking)
    s += `<rect class="park" x="${X(k.x)-rl/2}" y="${Y(k.y)-rw/2}"
          width="${rl}" height="${rw}" rx="0.2"
          ${k.charger ? 'stroke="#d29922" stroke-dasharray="none"' : ''}/>`;
  for (const k of p.parking) if (k.charger)
    s += `<text class="lbl" x="${X(k.x)}" y="${Y(k.y)+0.4}"
          text-anchor="middle" fill="#d29922">&#9889;</text>`;
  s += '<g id="robots"></g>';
  svg.innerHTML = s;
}

function drawRobots(fleet) {
  const p = PLANT, pad = 1.5;
  const X = x => x - p.hall.w + pad, Y = y => p.hall.n - y + pad;
  const [rl, rw] = p.robot_size;
  let s = '';
  for (const r of fleet) {
    if (!r.position) continue;
    const [x, y] = r.position;
    const deg = -(r.yaw || 0) * 180 / Math.PI;
    const colour = !r.responsive ? '#f85149'
      : (r.charging_to ? '#d29922' : (r.busy ? '#4c9aff' : '#3d4a5c'));
    s += `<g transform="translate(${X(x)},${Y(y)}) rotate(${deg})">
            <rect x="${-rl/2}" y="${-rw/2}" width="${rl}" height="${rw}" rx="0.2"
                  fill="${colour}" stroke="#0b0e13" stroke-width="0.12"/>
            <rect x="${rl/2-0.35}" y="${-0.12}" width="0.3" height="0.24"
                  fill="#0b0e13"/>
          </g>
          <text class="rname" x="${X(x)}" y="${Y(y)-1.1}"
                text-anchor="middle">${r.name}</text>`;
    if (r.goal)
      s += `<line x1="${X(x)}" y1="${Y(y)}" x2="${X(r.goal[0])}" y2="${Y(r.goal[1])}"
             stroke="#4c9aff" stroke-width="0.08" stroke-dasharray="0.4 0.4"
             opacity="0.6"/>`;
  }
  const g = document.getElementById('robots');
  if (g) g.innerHTML = s;
}

/* ---- refresh ------------------------------------------------------- */
let lastOk = 0;

/* A rendering error used to reject silently: polling continued, the page
   froze, and it looked exactly like a live view of a stopped factory. Now the
   banner says which it is. */
async function tick() {
  try { await refresh(); }
  catch (e) {
    if (++failures > 2) {
      const el = $('stale');
      el.textContent = '— view error: ' + (e && e.message ? e.message : e) + ' —';
      el.style.display = 'inline';
    }
    return;
  }
}

function age() {
  if (!lastOk) return;
  const secs = (Date.now() - lastOk) / 1000;
  $('c-age').textContent = secs < 2 ? 'now' : secs.toFixed(0) + 's ago';
  // Data older than five seconds is not live, whatever the page looks like.
  $('c-age').className = secs > 5 ? 'bad' : '';
}
setInterval(age, 500);

async function refresh() {
  const d = await (await fetch('/state', {cache:'no-store'})).json();
  failures = 0; lastOk = Date.now();
  $('stale').style.display = 'none';
  if (!PLANT) { PLANT = d.plant; drawPlant(PLANT);
    $('m-note').textContent =
      `${PLANT.machines.length} machines · ${PLANT.docks.length} docks · `
      + `${PLANT.parking.length} parking slots`; }
  drawRobots(d.fleet);

  const c = d.counters;
  $('c-active').textContent = c.active_jobs;
  $('c-done').textContent   = c.finished_jobs;
  $('c-created').textContent= c.jobs_created;
  $('c-bobbin').textContent = c.bobbins_returned;
  $('c-divert').textContent = c.diverted_to_rack;
  $('c-defer').textContent  = c.calls_deferred;
  $('c-lost').textContent   = c.commands_lost;
  $('c-unrested').textContent = c.unrested_decisions;
  $('s-lost').className = 'stat' + (c.commands_lost ? ' bad' : '');
  $('s-unrested').className = 'stat' + (c.unrested_decisions ? ' warn' : '');

  $('n-fleet').textContent = d.fleet.length;
  table($('t-fleet'), ['robot','leg','battery','busy','job','going to','at','responsive','halted because'],
    d.fleet, r => [r.name, r.leg, battery(r),
      r.busy ? 'yes' : '<span class="muted">idle</span>',
      r.job_id, r.leg_target,
      r.position ? `${n1(r.position[0])},${n1(r.position[1])}` : null,
      cls(r.responsive ? 'yes' : 'NO', 'yes'),
      r.busy && r.halted_because ? '<span class="warn">' + r.halted_because + '</span>' : null]);

  $('n-equip').textContent = d.equipment.length;
  table($('t-equip'), ['station','MC_Num','status','presence','code','accepts','entry','beat'],
    d.equipment, e => [e.station, e.mc_num, e.status,
      e.presence, e.task_processing,
      e.can_accept === null ? null : (e.can_accept ? 'yes' : 'no'),
      e.enter_permitted === null ? null : cls(e.enter_permitted ? 'yes':'NO','yes'),
      e.heartbeat === null ? null : cls(e.heartbeat ? 'ok':'STOPPED','ok')]);

  $('n-jobs').textContent = d.jobs.active.length;
  table($('t-jobs'), ['job','state','from','to','obj','call','material','why not'],
    d.jobs.active, j => [j.job_id, j.state,
      j.from + (j.from_instance ? ' #'+j.from_instance : ''),
      j.to + (j.to_instance ? ' #'+j.to_instance : ''),
      `<span class="pill" style="color:${j.object==='bobbin'?'var(--bobbin)':'var(--roll)'}">${j.object}</span>`,
      j.call_id || '<span class="muted">no caller</span>',
      j.material_ref, j.failure_reason]);

  $('n-fin').textContent = d.jobs.finished.length;
  table($('t-fin'), ['job','state','from','to','obj','reason'],
    d.jobs.finished, j => [j.job_id,
      j.state === 'DONE' ? '<span class="ok">DONE</span>'
                         : '<span class="bad">FAILED</span>',
      j.from, j.to, j.object, j.failure_reason]);

  $('n-racks').textContent = d.racks.length;
  table($('t-racks'), ['rack','used','free','slots'], d.racks, r => [r.rack,
    r.used, r.size - r.used,
    r.slots.map(s => s.occupied
      ? `<span class="pill" title="${s.material_ref}">${s.slot}</span>`
      : `<span class="pill muted">${s.slot}</span>`).join(' ')]);

  $('n-mat').textContent = d.materials.length;
  table($('t-mat'), ['LOT id','kind','where','moves'], d.materials,
    m => [m.lot_id, m.kind, m.location, m.moves]);

  $('n-calls').textContent = d.calls.length;
  table($('t-calls'), ['call','station','#','type','source','status','job'],
    d.calls.slice().reverse(), c => [c.call_id, c.station, c.instance,
      c.task_type, c.source, c.status, c.job_id]);

  $('n-dec').textContent = d.decisions.length;
  table($('t-dec'), ['job','source','dest','why'], d.decisions,
    x => [x.job_id, x.source, x.dest, x.reason]);
}
tick(); setInterval(tick, 500);
</script>
</body>
</html>
"""


def page():
    """The live view, with the shared navigation filled in.

    A function rather than a constant so the nav lives in one place. Every page
    does this the same way — a fourth view must appear on all of them or none.
    """
    return (PAGE.replace("__NAV__", nav.bar("/"))
                .replace("__NAVCSS__", nav.CSS))
