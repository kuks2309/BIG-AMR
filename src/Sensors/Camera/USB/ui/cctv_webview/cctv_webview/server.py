# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""JPEG 바이트를 그대로 흘리는 HTTP 서버 — multipart/x-mixed-replace(MJPEG).

브라우저가 디코드하므로 로봇 PC 는 픽셀을 만지지 않는다. ROS 의존이 없어 가짜
FrameStore 로 단위 시험할 수 있다.
"""

import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .frame_store import display_name

BOUNDARY = "amrcctvframe"


# 화면 배치를 실제 차량에서 내려다본 것과 같게 놓는다 — 왼쪽 타일이 차량 왼쪽이다.
# 이름 -> CSS grid-area. 가운데 열은 차체가 차지해 배치가 무엇을 뜻하는지 드러낸다.
#
#          전면 F
#   좌전 LF  [차체]  우전 RF
#   좌후 LR  [차체]  우후 RR
#          후면 R
LAYOUT_AREAS = {
    "cam_f": "f", "cam_lf": "lf", "cam_rf": "rf",
    "cam_lr": "lr", "cam_rr": "rr", "cam_r": "r",
}


def _tile(name, area=None):
    style = f' style="grid-area:{area}"' if area else ""
    return (f'      <figure{style}><figcaption>{display_name(name)} '
            f'<span class="topic">{name}</span>'
            f'<span class="det" data-det="{name}"></span></figcaption>'
            f'<div class="frame"><img src="/stream/{name}" alt="{name}">'
            f'<div class="ov" data-ov="{name}"></div></div></figure>')


# 박스 나이 판정 — Qt 뷰어와 같은 기준을 쓴다(신선/낡음/만료).
_OVERLAY_JS = """
<script>
(function () {
  const FRESH_MS = 150, STALE_MS = 400;
  const box = document.getElementById('ai-toggle');
  let on = true;
  box.addEventListener('change', () => { on = box.checked; if (!on) clearAll(); });

  function clearAll() {
    document.querySelectorAll('[data-ov]').forEach(o => { o.innerHTML = ''; });
    document.querySelectorAll('[data-det]').forEach(d => { d.textContent = ''; });
  }

  async function tick() {
    if (on) {
      try {
        const res = await fetch('/detections', {cache: 'no-store'});
        render(await res.json());
      } catch (e) { /* 서버가 잠깐 없어도 다음 주기에 다시 시도한다 */ }
    }
    setTimeout(tick, 200);
  }

  function render(data) {
    document.querySelectorAll('[data-ov]').forEach(function (ov) {
      const name = ov.dataset.ov;
      const label = document.querySelector('[data-det="' + name + '"]');
      const entry = data[name];
      ov.innerHTML = '';
      if (!entry) { if (label) label.textContent = ''; return; }
      // 만료된 결과는 그리지 않는다 — 낡은 박스가 현재처럼 보이면 안 된다.
      if (entry.age_ms > STALE_MS) {
        if (label) label.textContent = '· 검출 낡음';
        return;
      }
      const fresh = entry.age_ms <= FRESH_MS;
      const w = entry.width || 1280, h = entry.height || 720;
      entry.boxes.forEach(function (b) {
        const el = document.createElement('div');
        el.className = 'box' + (fresh ? '' : ' aged');
        el.style.left = (b.x / w * 100) + '%';
        el.style.top = (b.y / h * 100) + '%';
        el.style.width = (b.w / w * 100) + '%';
        el.style.height = (b.h / h * 100) + '%';
        el.innerHTML = '<span>' + b.label + ' ' +
          Math.round(b.conf * 100) + '%</span>';
        ov.appendChild(el);
      });
      if (label) {
        label.textContent = entry.boxes.length
          ? '· ' + entry.boxes.length + '명' : '';
      }
    });
  }
  tick();
})();
</script>
"""


def build_index_html(names, stream_hz):
    """카메라 타일 페이지. 이미지 자체는 브라우저가 각 스트림에서 직접 받는다.

    로스터가 여섯 장착 위치를 모두 담고 있으면 **차량 배치대로** 놓고, 그렇지 않으면
    (카메라를 빼거나 이름이 다르면) 순서대로 흐르는 격자로 물러난다 — 위치를 모르는
    카메라를 임의 자리에 놓으면 방향을 오독하게 되므로 배치를 주장하지 않는다.
    """
    positioned = all(n in LAYOUT_AREAS for n in names) and len(names) == len(LAYOUT_AREAS)
    if positioned:
        order = ["cam_f", "cam_lf", "cam_rf", "cam_lr", "cam_rr", "cam_r"]
        tiles = "\n".join(_tile(n, LAYOUT_AREAS[n]) for n in order)
        body = ('      <div class="body" aria-hidden="true">'
                '<span class="arrow">▲</span><span>Big AMR</span></div>\n')
        grid_class = "grid vehicle"
    else:
        tiles = "\n".join(_tile(n) for n in names)
        body = ""
        grid_class = "grid flow"

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AMR CCTV</title>
<style>
  body {{ margin:0; background:#0d1117; color:#c9d1d9;
         font-family:system-ui,'Noto Sans KR',sans-serif; }}
  header {{ padding:8px 12px; font-weight:600; border-bottom:1px solid #30363d; }}
  header small {{ font-weight:400; color:#8b949e; margin-left:8px; }}
  .grid {{ display:grid; gap:6px; padding:6px; }}
  .flow {{ grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); }}
  /* 차량을 위에서 내려다본 배치. 가운데 열이 차체다. */
  .vehicle {{
    /* 세 열을 같은 폭으로 — 전면·후면 타일이 좌우 타일보다 작아 보이면 안 된다.
       가운데 열은 1행(전면)·4행(후면)에서는 카메라가, 2~3행에서는 차체가 쓴다. */
    grid-template-columns:repeat(3,1fr);
    grid-template-areas:
      ".  f    ."
      "lf body rf"
      "lr body rr"
      ".  r    .";
  }}
  .body {{ grid-area:body; display:flex; flex-direction:column; align-items:center;
           justify-content:center; gap:6px; border:1px dashed #30363d; border-radius:8px;
           color:#6e7681; font-size:12px; letter-spacing:1px; }}
  .body .arrow {{ font-size:20px; color:#58a6ff; }}
  figure {{ margin:0; background:#161b22; border:1px solid #30363d; border-radius:6px;
            overflow:hidden; }}
  figcaption {{ padding:4px 8px; font-size:13px; color:#58a6ff; }}
  .topic {{ color:#6e7681; font-size:11px; }}
  .det {{ color:#3fb950; font-size:11px; margin-left:6px; }}
  .frame {{ position:relative; line-height:0; }}
  img {{ width:100%; display:block; background:#000; }}
  .ov {{ position:absolute; inset:0; pointer-events:none; }}
  /* 신선한 검출은 초록 실선, 낡은 검출은 노란 점선 — Qt 뷰어와 같은 기준. */
  .box {{ position:absolute; border:2px solid #3fb950; border-radius:2px; }}
  .box.aged {{ border-style:dashed; border-color:#d29922; }}
  .box span {{ position:absolute; top:-18px; left:0; font-size:11px; line-height:16px;
               padding:0 4px; background:#3fb950; color:#0d1117; border-radius:2px;
               white-space:nowrap; }}
  .box.aged span {{ background:#d29922; }}
  header label {{ font-weight:400; font-size:13px; color:#c9d1d9; margin-left:12px;
                  cursor:pointer; }}
  /* 좁은 화면에서는 배치를 포기하고 한 줄씩 — 타일이 뭉개지는 것보다 낫다. */
  @media (max-width:860px) {{
    .vehicle {{ grid-template-columns:1fr; grid-template-areas:none; }}
    .vehicle figure {{ grid-area:auto !important; }}
    .body {{ display:none; }}
  }}
</style></head>
<body>
  <header>AMR CCTV<small>{len(names)}대 · 스트림 {stream_hz:g} Hz ·
    JPEG 원본 전달(서버 디코드 없음){' · 차량 배치' if positioned else ''}</small>
    <label><input type="checkbox" id="ai-toggle" checked> AI 표시</label></header>
  <div class="{grid_class}">
{tiles}
{body}  </div>
{_OVERLAY_JS}
</body></html>
"""


class _Handler(BaseHTTPRequestHandler):
    store = None
    detections = None
    stream_hz = 10.0
    camera_names = ()
    log = None

    def log_message(self, fmt, *args):  # noqa: A003 - BaseHTTPRequestHandler 규약
        # ROS 로거는 stdlib logging 과 달리 printf 인자를 받지 않는다 — 미리 포맷한다.
        if self.log is not None:
            self.log.debug(f"{self.address_string()} - {fmt % args}")

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler 규약
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send_html(build_index_html(self.camera_names, self.stream_hz))
        elif path.startswith("/stream/"):
            self._send_stream(path[len("/stream/"):])
        elif path.startswith("/snapshot/"):
            self._send_snapshot(path[len("/snapshot/"):])
        elif path == "/status":
            self._send_status()
        elif path == "/detections":
            self._send_json({} if self.detections is None else self.detections.snapshot())
        else:
            self.send_error(404, "not found")

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_status(self):
        self._send_json(self.store.stats())

    def _send_json(self, payload):
        import json
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_snapshot(self, name):
        entry = self.store.get(name)
        if entry is None:
            self.send_error(503, "no frame yet")
            return
        data = entry[0]
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_stream(self, name):
        if name not in self.camera_names:
            self.send_error(404, "unknown camera")
            return
        self.send_response(200)
        self.send_header("Age", "0")
        self.send_header("Cache-Control", "no-cache, private")
        self.send_header("Pragma", "no-cache")
        self.send_header(
            "Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}")
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


def make_server(store, camera_names, port=8080, bind="0.0.0.0", stream_hz=10.0,
                log=None, detections=None):
    """설정을 주입한 ThreadingHTTPServer. 시청자마다 스레드 하나."""
    handler = type("CctvHandler", (_Handler,), {
        "store": store,
        "detections": detections,
        "camera_names": tuple(camera_names),
        "stream_hz": stream_hz,
        "log": log,
    })
    server = ThreadingHTTPServer((bind, port), handler)
    server.daemon_threads = True
    return server
