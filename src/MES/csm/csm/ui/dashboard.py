"""The management view — a separate page from the live one, on purpose.

The live view at `/` answers "what is happening right now": robots moving,
stations lit, jobs in flight. Somebody watching the floor wants that.

This answers a different question — "is anything quietly wrong, and how much
have we moved" — and it is the question you cannot answer from a snapshot. A
robot idle for twenty minutes looks perfectly healthy in a picture of the
plant. Splitting them is what CCS does too: a rack monitor for operators and a
big-screen gauge for management (manual §2.2 versus §4.3).

Deliberately plain. It is meant to be read from across a room, and every panel
carries the rule it applies and where that rule came from, so nobody has to
take a number on trust.
"""

from . import health

STATUS_TEXT = {health.OK: "OK", health.WARN: "CHECK",
               health.ALARM: "ACTION", health.UNKNOWN: "NO DATA"}

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CSM — line status</title>
<style>
 :root {
   --bg:#12141a; --card:#1b1e26; --line:#2b3040; --text:#e8eaf0;
   --dim:#9aa3b8; --ok:#3ecf8e; --warn:#f5a524; --alarm:#f2545b;
   --unknown:#7d8aa8;
 }
 * { box-sizing:border-box; }
 body { margin:0; background:var(--bg); color:var(--text);
        font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
 header { padding:20px 28px; border-bottom:1px solid var(--line);
          display:flex; align-items:baseline; gap:18px; flex-wrap:wrap; }
 h1 { margin:0; font-size:19px; font-weight:600; letter-spacing:.2px; }
 .verdict { font-size:13px; font-weight:700; padding:4px 12px;
            border-radius:99px; letter-spacing:.6px; }
 .stamp { color:var(--dim); font-size:13px; margin-left:auto; }
 main { padding:22px 28px 40px; max-width:1180px; }
 h2 { font-size:12px; text-transform:uppercase; letter-spacing:1.2px;
      color:var(--dim); margin:26px 0 12px; font-weight:600; }
 .pipe { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
         gap:12px; }
 .stage { background:var(--card); border:1px solid var(--line);
          border-radius:10px; padding:16px 18px; }
 .stage .n { font-size:32px; font-weight:650; line-height:1.1; }
 .stage .s { font-size:14px; margin-top:2px; }
 .stage .note { color:var(--dim); font-size:12.5px; margin-top:6px; }
 .checks { display:grid; gap:9px; }
 .check { background:var(--card); border:1px solid var(--line);
          border-left:4px solid var(--line); border-radius:9px;
          padding:13px 16px; display:grid;
          grid-template-columns:96px 1fr; gap:14px; align-items:start; }
 .check.ok { border-left-color:var(--ok); }
 .check.warn { border-left-color:var(--warn); }
 .check.alarm { border-left-color:var(--alarm); }
 .check.unknown { border-left-color:var(--unknown); }
 .badge { font-size:11px; font-weight:700; letter-spacing:.7px;
          padding:3px 0; text-align:center; border-radius:5px; }
 .ok .badge { background:rgba(62,207,142,.16); color:var(--ok); }
 .warn .badge { background:rgba(245,165,36,.16); color:var(--warn); }
 .alarm .badge { background:rgba(242,84,91,.16); color:var(--alarm); }
 .unknown .badge { background:rgba(125,138,168,.16); color:var(--unknown); }
 .name { font-weight:600; }
 .summary { color:var(--text); font-size:14px; margin-top:1px; }
 .source { color:var(--dim); font-size:12px; margin-top:5px; font-style:italic; }
 .detail { color:var(--dim); font-size:12.5px; margin-top:7px;
           font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
           white-space:pre-wrap; }
 .fleet { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
          gap:10px; }
 .robot { background:var(--card); border:1px solid var(--line);
          border-radius:9px; padding:12px 14px; }
 .robot .rn { font-weight:600; }
 .bar { height:6px; background:#262b36; border-radius:3px; margin-top:8px;
        overflow:hidden; }
 .bar i { display:block; height:100%; }
 .robot .st { color:var(--dim); font-size:12.5px; margin-top:6px; }
 footer { color:var(--dim); font-size:12px; padding:0 28px 30px;
          max-width:1180px; }
 a { color:#7fb2ff; }
</style></head>
<body>
<header>
  <h1>CSM — line status</h1>
  <span id="verdict" class="verdict">…</span>
  <span class="stamp">refreshes every 2 s · <a href="/">live view</a></span>
</header>
<main>
  <h2>Material in the line</h2>
  <div class="pipe" id="pipe"></div>

  <h2>Fleet</h2>
  <div class="fleet" id="fleet"></div>

  <h2>Daily check</h2>
  <div class="checks" id="checks"></div>
</main>
<footer id="foot"></footer>
<script>
const COLOUR = {ok:'var(--ok)', warn:'var(--warn)', alarm:'var(--alarm)',
                unknown:'var(--unknown)'};
const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

function render(d) {
  const v = document.getElementById('verdict');
  v.textContent = d.verdict_text;
  v.style.background = COLOUR[d.verdict] + '22';
  v.style.color = COLOUR[d.verdict];

  document.getElementById('pipe').innerHTML = d.pipeline.map(s =>
    `<div class="stage"><div class="n">${s.count}</div>
     <div class="s">${esc(s.stage)}</div>
     <div class="note">${esc(s.note)}</div></div>`).join('');

  document.getElementById('fleet').innerHTML = d.fleet.map(r => {
    const b = r.battery == null ? 0 : r.battery;
    const col = b <= 12 ? 'var(--alarm)' : b <= 30 ? 'var(--warn)' : 'var(--ok)';
    const what = r.charging_to != null ? 'charging to ' + r.charging_to + '%'
               : r.busy ? (r.leg_target ? 'to ' + esc(r.leg_target) : 'working')
               : 'idle';
    return `<div class="robot"><div class="rn">${esc(r.name)}</div>
      <div class="bar"><i style="width:${Math.max(0,Math.min(100,b))}%;
        background:${col}"></i></div>
      <div class="st">${b.toFixed(0)}% · ${what}</div></div>`;
  }).join('') || '<div class="robot"><div class="st">no robots</div></div>';

  document.getElementById('checks').innerHTML = d.checks.map(c =>
    `<div class="check ${c.status}">
       <div class="badge">${esc(c.status_text)}</div>
       <div><div class="name">${esc(c.name)}</div>
         <div class="summary">${esc(c.summary)}</div>
         <div class="source">${esc(c.source)}</div>
         ${c.detail && c.detail.length
            ? '<div class="detail">' + c.detail.map(esc).join('\\n') + '</div>'
            : ''}</div>
     </div>`).join('');

  document.getElementById('foot').textContent = d.footer;
}

async function tick() {
  try {
    const r = await fetch('/health', {cache:'no-store'});
    render(await r.json());
  } catch (e) {
    document.getElementById('verdict').textContent = 'NO CONNECTION';
  }
}
tick();
setInterval(tick, 2000);
</script>
</body></html>
"""


def report(snapshot, now=None):
    """The JSON the page draws. Kept apart from the HTML so it can be tested."""
    checks = health.run(snapshot, now=now)
    verdict = health.worst(checks)
    return {
        "verdict": verdict,
        "verdict_text": STATUS_TEXT[verdict],
        "pipeline": health.pipeline(snapshot),
        "fleet": snapshot.get("fleet", []),
        "checks": [{"name": c.name, "status": c.status,
                    "status_text": STATUS_TEXT[c.status],
                    "summary": c.summary, "source": c.source,
                    "detail": list(c.detail)} for c in checks],
        "footer": ("Checks follow the CCS manual's own daily list (§6) and "
                   "pipeline gauge (§4.3). Every panel names the rule it "
                   "applies. NO DATA means we cannot answer it yet, which is "
                   "not the same as nothing being wrong."),
    }


def page():
    return PAGE
