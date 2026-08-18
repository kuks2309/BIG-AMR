# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""라인 인식 뷰어 HTTP 서버 — JPEG 는 그대로 흘리고 오버레이는 브라우저가 그린다.

서버가 영상에 선을 그리려면 디코드·재인코딩이 필요하다. 그 비용은 인식률을 직접 깎는다
(720p 실측: 디버그 영상 발행 시 24.4 → 2.3 Hz). 그래서 이 서버는 바이트만 중계하고
좌표만 JSON 으로 보낸다. ROS 의존이 없어 가짜 store 로 단위 시험할 수 있다.
"""

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

BOUNDARY = "amrlineframe"

# 이 나이를 넘긴 오차는 「낡음」으로 표시한다 — 멈춘 값이 현재처럼 보이면 안 된다.
STALE_MS = 500

_PAGE_JS = """
<script>
(function () {
  const STALE_MS = %(stale)d;
  const svg = document.getElementById('ov');
  const line = document.getElementById('ln');
  const pt = document.getElementById('pt');
  const row = document.getElementById('row');
  const badge = document.getElementById('badge');
  const camName = document.getElementById('cam');
  const img = document.getElementById('view');
  const cells = {
    offset: document.getElementById('v-offset'),
    angle: document.getElementById('v-angle'),
    conf: document.getElementById('v-conf'),
    hz: document.getElementById('v-hz'),
    age: document.getElementById('v-age'),
  };

  function setBadge(text, cls) { badge.textContent = text; badge.className = 'badge ' + cls; }

  function hide() { line.style.display = 'none'; pt.style.display = 'none'; }

  async function tick() {
    try {
      const d = await (await fetch('/line', {cache: 'no-store'})).json();
      render(d);
    } catch (e) { setBadge('서버 응답 없음', 'bad'); hide(); }
    setTimeout(tick, 100);
  }

  function render(d) {
    if (!d.received) { setBadge('오차 수신 없음', 'bad'); hide(); return; }
    camName.textContent = d.camera || '(카메라 미상)';
    cells.offset.textContent = d.offset.toFixed(3);
    cells.angle.textContent = (d.angle * 180 / Math.PI).toFixed(1) + '°';
    cells.conf.textContent = d.confidence.toFixed(2);
    cells.hz.textContent = d.hz.toFixed(1) + ' Hz';
    cells.age.textContent = d.age_ms.toFixed(0) + ' ms';
    if (d.age_ms > STALE_MS) { setBadge('오차 낡음 ' + d.age_ms.toFixed(0) + 'ms', 'bad'); hide(); return; }
    if (!d.detected) { setBadge('라인 미검출', 'warn'); hide(); return; }
    setBadge('검출 conf ' + d.confidence.toFixed(2), 'ok');
    const g = d.geom;
    line.setAttribute('x1', g.x1 * 100); line.setAttribute('y1', g.y1 * 100);
    line.setAttribute('x2', g.x2 * 100); line.setAttribute('y2', g.y2 * 100);
    pt.setAttribute('cx', g.cx * 100); pt.setAttribute('cy', g.cy * 100);
    row.setAttribute('y1', g.cy * 100); row.setAttribute('y2', g.cy * 100);
    line.style.display = ''; pt.style.display = '';
  }

  document.querySelectorAll('[data-dir]').forEach(function (b) {
    b.addEventListener('click', async function () {
      const dir = b.dataset.dir;
      b.disabled = true;
      try {
        const r = await fetch('/direction', {method: 'POST', body: dir});
        const j = await r.json();
        if (j.ok) { img.src = '/stream/' + j.camera + '?t=' + Date.now(); }
        else { setBadge('전환 실패: ' + (j.error || ''), 'bad'); }
      } catch (e) { setBadge('전환 요청 실패', 'bad'); }
      b.disabled = false;
    });
  });
  tick();
})();
</script>
"""


def build_index_html(camera, control_row_ratio):
    """뷰어 페이지. 영상은 브라우저가 `/stream/<cam>` 에서 직접 받는다."""
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AMR 라인 인식</title>
<style>
  body {{ margin:0; background:#0d1117; color:#c9d1d9;
         font-family:system-ui,'Noto Sans KR',sans-serif; }}
  header {{ padding:8px 12px; font-weight:600; border-bottom:1px solid #30363d;
            display:flex; align-items:center; gap:12px; flex-wrap:wrap; }}
  header small {{ font-weight:400; color:#8b949e; }}
  .badge {{ font-size:12px; font-weight:600; padding:2px 8px; border-radius:10px; }}
  .badge.ok {{ background:#238636; color:#fff; }}
  .badge.warn {{ background:#9e6a03; color:#fff; }}
  .badge.bad {{ background:#da3633; color:#fff; }}
  button {{ background:#21262d; color:#c9d1d9; border:1px solid #30363d;
            border-radius:6px; padding:4px 10px; font-size:13px; cursor:pointer; }}
  button:hover {{ border-color:#8b949e; }}
  button:disabled {{ opacity:.5; cursor:default; }}
  main {{ padding:6px; display:grid; gap:6px;
          grid-template-columns:minmax(0,1fr) 220px; }}
  .frame {{ position:relative; line-height:0; background:#000;
            border:1px solid #30363d; border-radius:6px; overflow:hidden; }}
  img {{ width:100%; display:block; }}
  svg {{ position:absolute; inset:0; width:100%; height:100%; pointer-events:none; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ text-align:left; padding:4px 6px; border-bottom:1px solid #21262d; }}
  th {{ color:#8b949e; font-weight:400; }}
  td {{ font-variant-numeric:tabular-nums; }}
  aside {{ background:#161b22; border:1px solid #30363d; border-radius:6px; padding:6px; }}
  @media (max-width:760px) {{ main {{ grid-template-columns:1fr; }} }}
</style></head>
<body>
  <header>라인 인식
    <small>카메라 <span id="cam">{camera}</span> · JPEG 원본 전달(서버 디코드 없음)</small>
    <span id="badge" class="badge warn">대기</span>
    <button data-dir="forward">전진(cam_f)</button>
    <button data-dir="reverse">후진(cam_r)</button>
  </header>
  <main>
    <div class="frame">
      <img id="view" src="/stream/{camera}" alt="camera">
      <svg id="ov" viewBox="0 0 100 100" preserveAspectRatio="none">
        <line x1="50" y1="0" x2="50" y2="100" stroke="#6e7681"
              stroke-width="0.2" stroke-dasharray="1 1"></line>
        <line id="row" x1="0" y1="80" x2="100" y2="80" stroke="#6e7681"
              stroke-width="0.2" stroke-dasharray="1 1"></line>
        <line id="ln" x1="50" y1="0" x2="50" y2="100" stroke="#3fb950"
              stroke-width="0.5" style="display:none"></line>
        <circle id="pt" cx="50" cy="80" r="1" fill="#f85149" style="display:none"></circle>
      </svg>
    </div>
    <aside>
      <table>
        <tr><th>offset</th><td id="v-offset">–</td></tr>
        <tr><th>angle</th><td id="v-angle">–</td></tr>
        <tr><th>conf</th><td id="v-conf">–</td></tr>
        <tr><th>수신율</th><td id="v-hz">–</td></tr>
        <tr><th>나이</th><td id="v-age">–</td></tr>
        <tr><th>기준행</th><td>{control_row_ratio:g}</td></tr>
      </table>
    </aside>
  </main>
{_PAGE_JS % {"stale": STALE_MS}}
</body></html>
"""


class _Handler(BaseHTTPRequestHandler):
    store = None
    state = None
    geom_fn = None
    set_direction = None
    camera_of = None
    control_row_ratio = 0.8
    image_aspect = 16.0 / 9.0
    stream_hz = 15.0
    log = None

    def log_message(self, fmt, *args):  # noqa: A003 - BaseHTTPRequestHandler 규약
        if self.log is not None:
            self.log.debug(f"{self.address_string()} - {fmt % args}")

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler 규약
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send_html(build_index_html(self.camera_of(), self.control_row_ratio))
        elif path.startswith("/stream/"):
            self._send_stream(path[len("/stream/"):])
        elif path == "/line":
            self._send_json(self._line_payload())
        elif path == "/status":
            self._send_json(self.store.stats())
        else:
            self.send_error(404, "not found")

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler 규약
        if urlparse(self.path).path != "/direction":
            self.send_error(404, "not found")
            return
        length = int(self.headers.get("Content-Length") or 0)
        want = self.rfile.read(length).decode("utf-8").strip().lower()
        if want not in ("forward", "reverse"):
            self._send_json({"ok": False, "error": "forward|reverse 만 허용"})
            return
        ok, err = self.set_direction(want)
        self._send_json({"ok": ok, "error": err, "camera": self.camera_of()})

    def _line_payload(self):
        payload = self.state.snapshot()
        if payload.get("received") and payload.get("detected"):
            payload["geom"] = self.geom_fn(payload["offset"], payload["angle"],
                                           self.control_row_ratio, self.image_aspect)
        return payload

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_stream(self, name):
        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}")
        self.end_headers()
        period = 1.0 / self.stream_hz if self.stream_hz > 0 else 0.0
        last_seq = 0
        try:
            while True:
                entry = self.store.get_newer_than(name, last_seq)
                if entry is None:
                    # 새 프레임이 없으면 잠깐 쉰다 — 같은 프레임을 다시 보내지 않는다.
                    time.sleep(min(period, 0.05) or 0.01)
                    continue
                data, _stamp, last_seq = entry
                self.wfile.write(f"--{BOUNDARY}\r\n".encode("ascii"))
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(data)}\r\n\r\n".encode("ascii"))
                self.wfile.write(data)
                self.wfile.write(b"\r\n")
                if period:
                    time.sleep(period)
        except (BrokenPipeError, ConnectionResetError):
            pass  # 시청자가 탭을 닫은 것 — 정상 종료다.


def make_server(store, state, geom_fn, camera_of, set_direction, port=8081,
                bind="0.0.0.0", stream_hz=15.0, control_row_ratio=0.8,
                image_aspect=16.0 / 9.0, log=None):
    """설정을 주입한 ThreadingHTTPServer. 시청자마다 스레드 하나."""
    handler = type("LineHandler", (_Handler,), {
        "store": store,
        "state": state,
        "geom_fn": staticmethod(geom_fn),
        "camera_of": staticmethod(camera_of),
        "set_direction": staticmethod(set_direction),
        "control_row_ratio": control_row_ratio,
        "image_aspect": image_aspect,
        "stream_hz": stream_hz,
        "log": log,
    })
    server = ThreadingHTTPServer((bind, port), handler)
    server.daemon_threads = True
    return server
