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
  /* RULE 1's lines, in the same colours the Gazebo world paints them. */
  .lane      { fill:none; stroke-linecap:round; }
  .lane.in   { stroke:#4c9aff; stroke-width:0.16; }
  .lane.out  { stroke:#d29922; stroke-width:0.16; }
  .lane.spur { stroke:#3fb950; stroke-width:0.11; opacity:.75; }
  .lane.cross{ stroke:#db61a2; stroke-width:0.11; opacity:.75; }
  .arrow.in  { fill:#4c9aff; } .arrow.out { fill:#d29922; }
  #roads.off { display:none; }
  .key { font-size:11px; color:var(--dim); display:inline-flex; gap:10px;
         align-items:center; margin-left:10px; }
  .key i { width:12px; height:0; border-top:2px solid; display:inline-block;
           margin-right:4px; vertical-align:middle; }
  .park { fill:none; stroke:#39465a; stroke-dasharray:2 2; }
  .lbl  { fill:#6b7688; font-size:1.05px; }
  .rname{ fill:#dbe4f0; font-size:1.5px; font-weight:600; }
  /* What a robot is carrying. Size is the drum type, colour is the face,
     and an empty bobbin is hollow where a loaded roll is filled. */
  .load        { stroke-width:0.10; }
  .load.bright { fill:#e8c46a; stroke:#f0d9a0; }
  .load.dark   { fill:#7a5cc4; stroke:#a68ee0; }
  .load.plain  { fill:#5b6b80; stroke:#8a97ab; }
  .load.hollow { fill:none; }
  /* The winding direction, as a clock hand. The SOFT half of the attribute:
     a 180 degree turn of the pallet swaps it. */
  .spin { stroke:#0b0e13; stroke-width:0.09; stroke-linecap:round; }
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
  <span class="stat" id="s-pda">PDA open <b id="c-pdaopen">0</b></span>
  <span class="stat">updated <b id="c-age">–</b></span>
  <span id="stale">— not updating —</span>
</header>

<main>
  <section class="wide">
    <h2>plant <span id="m-note" class="muted"></span>
      <span class="key">
        <label><input type="checkbox" id="showroads" checked> road</label>
        <span><i style="border-color:#4c9aff"></i>inner ring</span>
        <span><i style="border-color:#d29922"></i>outer ring</span>
        <span><i style="border-color:#3fb950"></i>spur</span>
        <span><i style="border-color:#db61a2"></i>ring change</span>
        <span style="margin-left:6px" title="The face is the half of the
          material attribute that MUST match to feed a machine. Rotation need
          not: a 180 degree turn of the pallet swaps it.">carried face &mdash;
          must match:
          <b style="color:#e8c46a">&#9679;</b> bright 亮面
          <b style="color:#7a5cc4">&#9679;</b> dark 暗面
          <b style="color:#8a97ab">&#9675;</b> empty core
          &nbsp;|&nbsp; hand = winding, fixable by a 180&deg; turn</span>
      </span>
    </h2>
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
    <h2>PDA — reported by a person <span id="n-pda"></span></h2>
    <div class="scroll"><table id="t-pda"></table></div>
    <p class="muted" id="pda-note"></p>
  </section>

  <section>
    <h2>decisions — why <span id="n-dec"></span></h2>
    <div class="scroll"><table id="t-dec"></table></div>
  </section>
</main>

<script>
const $ = id => document.getElementById(id);
let PLANT = null, PLANT_STAMP = null, failures = 0;

/* Everything drawPlant() reads. Cheap enough to compute twice a second, and it
   changes if the hall moves, a machine moves, or a dock or bay is added. */
function plantStamp(p) {
  return [p.hall.w, p.hall.e, p.hall.s, p.hall.n,
          p.machine_size, p.robot_size,
          p.machines.length, p.docks.length, p.parking.length,
          Object.entries(p.roads || {}).map(([k, v]) => k + v.length).join(','),
          p.machines.map(m => `${m.name}:${m.x},${m.y}`).join('|')].join(';');
}

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
  /* THE LINES, under everything else. A robot standing on a one-way lane and
     a robot standing beside a machine look identical without them. Drawn once
     and cached by plantStamp — this is 304 lanes of static geometry. */
  s += '<g id="roads">';
  const lanes = p.roads || {};
  const draw = (key, cls, arrow) => {
    const v = lanes[key] || [];
    let d = '';
    for (let i = 0; i < v.length; i += 4)
      d += `M${X(v[i])} ${Y(v[i+1])}L${X(v[i+2])} ${Y(v[i+3])}`;
    if (d) s += `<path class="lane ${cls}" d="${d}"/>`;
    if (!arrow) return;
    /* One chevron per lane, at the midpoint, pointing the way the traffic
       goes. The rings are one-way and that is the whole point of them; the
       spurs are driven both ways, so they get none. */
    for (let i = 0; i < v.length; i += 4) {
      const x1 = X(v[i]), y1 = Y(v[i+1]), x2 = X(v[i+2]), y2 = Y(v[i+3]);
      const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy);
      if (L < 1.2) continue;
      const ux = dx / L, uy = dy / L, px = -uy, py = ux;
      const cx = x1 + dx * 0.5, cy = y1 + dy * 0.5, a = 0.42, b = 0.22;
      s += `<polygon class="arrow ${cls}" points="`
         + `${cx + ux*a},${cy + uy*a} `
         + `${cx - ux*a + px*b},${cy - uy*a + py*b} `
         + `${cx - ux*a - px*b},${cy - uy*a - py*b}"/>`;
    }
  };
  draw('spur', 'spur', false);
  draw('cross', 'cross', false);
  draw('inner', 'in', true);
  draw('outer', 'out', true);
  s += '</g>';

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
  applyRoadToggle();
}

function applyRoadToggle() {
  const g = $('roads'), box = $('showroads');
  if (g && box) g.classList.toggle('off', !box.checked);
}

/* WHAT IS ON THE DECK. Drawn inside the robot's own transform, so it turns
   with the body — which is what makes a crab across a lane read as a robot
   carrying something sideways rather than two unrelated shapes.

   Size is the drum type (360/430/500/580), colour is the bright or dark face,
   and an EMPTY BOBBIN is hollow where a loaded roll is filled. That is three
   facts in one shape and no legend: what, which way up, and whether it is
   going somewhere full or coming back empty.

   A robot carrying something we cannot describe still draws, in grey. "Loaded
   with something unknown" is a real state and worth seeing; drawing nothing
   would report an empty robot, which is worse than admitting ignorance. */
function carried(r) {
  const L = r.payload;
  if (!L) return '';
  const radius = L.size || 0.40;
  const face = L.face === 'bright' ? 'bright' : (L.face === 'dark' ? 'dark' : 'plain');
  const hollow = L.kind === 'bobbin' ? ' hollow' : '';
  let out = `<circle class="load ${face}${hollow}" cx="0" cy="0" r="${radius}"/>`;
  /* The winding direction as a clock hand: up-and-right for clockwise,
     up-and-left for anticlockwise. Drawn only when we know it — an empty core
     has no winding, and unknown must not look like a value. */
  if (L.rotation === 'clockwise' || L.rotation === 'anticlockwise') {
    const dx = (L.rotation === 'clockwise' ? 1 : -1) * radius * 0.62;
    out += `<line class="spin" x1="0" y1="0" x2="${dx}" y2="${-radius*0.62}"/>`;
  }
  return out;
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
            ${carried(r)}
          </g>
          <text class="rname" x="${X(x)}" y="${Y(y)-1.1}"
                text-anchor="middle">${r.agv || r.name}</text>`;
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
  /* REDRAW THE FLOOR WHEN THE FLOOR CHANGES.
     This was `if (!PLANT)` — drawn once on the first poll and never again. Robot
     positions kept updating every 500 ms against a frozen backdrop, so any change
     to the layout left an open tab showing robots in new coordinates on the old
     hall. On 2026-08-24 the plant was scaled 1.2x and a tab that had been open
     across the change showed robots outside the walls and offset from the
     stations they were actually docked at. It read as a navigation fault and
     was reported as one; the robots were correct and the picture was stale.
     A view that can be wrong without saying so is worse than no view. */
  const stamp = plantStamp(d.plant);
  if (stamp !== PLANT_STAMP) {
    PLANT = d.plant; PLANT_STAMP = stamp; drawPlant(PLANT);
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

  const pda = d.pda || {available:false, reports:[], open_reports:0};
  $('c-pdaopen').textContent = pda.open_reports || 0;
  $('s-pda').className = 'stat' + (pda.open_reports ? ' bad' : '');
  $('n-pda').textContent = pda.available
    ? `${pda.open_reports} open of ${pda.total_reports||0}` : 'not running';
  table($('t-pda'), ['report','station','what','raised by','state'],
    (pda.reports||[]).slice().reverse(),
    r => [r.report_id, r.station, r.description, r.reported_by,
          r.open ? 'OPEN' : 'closed']);
  // The position-code gap is a fact about the system, so it belongs on the
  // page rather than only in a document. Zero codes means a worker's manual
  // call cannot be resolved to a station at all - customer question Q18.
  $('pda-note').textContent = pda.available
    ? `${pda.manual_calls||0} call(s) raised by hand · `
      + (pda.position_codes
         ? `${pda.position_codes} position codes mapped`
         : 'no position codes mapped yet — manual calls cannot resolve a station (Q18)')
    : 'no PDA in this run';

  $('n-fleet').textContent = d.fleet.length;
  table($('t-fleet'), ['robot','leg','battery','busy','job','going to','at','responsive','halted because'],
    d.fleet, r => [(r.agv ? `${r.agv} <span class="muted">${r.name}</span>`
                          : r.name), r.leg, battery(r),
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
$('showroads').addEventListener('change', applyRoadToggle);
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
