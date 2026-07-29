"""로컬 웹 대시보드 — 브라우저로 언제든 감시 결과를 본다. 표준 라이브러리만. ROS 무의존.

**샘플러와 분리돼 있다.** 본 서버는 `Log/health/*.jsonl` 을 **읽기만** 한다. 수집은 여전히
`sampler` 가 단독으로 하고, 서버가 죽어도 기록은 계속된다(그 반대도 성립). 감시기의 의존 표면과
실패 표면을 늘리지 않기 위한 분리다.

**읽기 전용이다.** 어떤 하드웨어도 제어하지 않고, 임계값도 바꾸지 않는다. POST 를 받지 않는다.

**기본 바인드는 127.0.0.1 이다.** 인증이 없으므로 외부 노출은 명시적 선택이어야 한다 —
같은 망의 다른 PC(Personal Computer)에서 보려면 `--bind 0.0.0.0` 을 직접 준다.

사용:
    python3 -m system_health.webview --log-dir Log/health            # http://127.0.0.1:8770
    python3 -m system_health.webview --log-dir Log/health --bind 0.0.0.0
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import parse_qs, urlparse

from .report import format_report, log_span, tail_records

DEFAULT_PORT = 8770
DEFAULT_BIND = "127.0.0.1"
#: 화면에 그리는 최근 표본 수 기본값. 5초 주기에서 약 30분.
DEFAULT_HISTORY = 360
MAX_HISTORY = 5000

#: 판정 등급 → (상태 팔레트 역할, 아이콘, 라벨). 색만으로 의미를 전달하지 않기 위해
#: 아이콘·라벨을 항상 함께 낸다(dataviz: 상태색은 icon+label 동반 필수).
LEVEL_VIEW = {
    "OK": ("good", "●", "정상"),
    "WARN": ("warning", "▲", "주의"),
    "ERROR": ("critical", "■", "이상"),
}


def latest_payload(records: Sequence[dict[str, Any]],
                   span: dict[str, Any] | None = None) -> dict[str, Any]:
    """가장 최근 표본 + 기록 구간 요약. 표본이 없으면 `{"empty": True}`.

    `records` 는 **꼬리 몇 개**만 받는다(전체가 아니다). 기록 전체에 대한 정보는 `span` 이
    담당하며, 그것도 파일 크기와 첫 줄만 보고 만든다 — 화면 갱신마다 전체를 세지 않기 위해서다.
    """
    if not records:
        return {"empty": True}
    last = dict(records[-1])
    if span:
        last["_first_time"] = span.get("first_time")
        last["_files"] = span.get("files")
        last["_bytes"] = span.get("bytes")
    return last


def history_payload(records: Sequence[dict[str, Any]], n: int) -> dict[str, Any]:
    """차트용 시계열 — 최근 `n` 개의 시각·최고온도·CPU·가용메모리·스왑.

    각 계열은 차트 하나에 **단독**으로 그린다(단일 축·범례 불필요). None 은 그대로 보내
    브라우저가 선을 끊게 한다 — 0 으로 채우면 없는 값이 '한가함'으로 오독된다.
    """
    sel = list(records)[-max(1, min(n, MAX_HISTORY)):]
    out: dict[str, list] = {"t": [], "temp": [], "cpu": [], "gpu": [], "mem": [],
                        "swaprate": [], "curr": []}
    for r in sel:
        temps = r.get("temperatures_c") or {}
        mem = r.get("memory") or {}
        out["t"].append((r.get("iso_time") or "")[11:])
        out["temp"].append(round(max(temps.values()), 1) if temps else None)
        out["cpu"].append(r.get("cpu_total_pct"))
        out["gpu"].append((r.get("gpu") or {}).get("load_pct"))
        out["mem"].append(round(mem["available_mb"], 0) if "available_mb" in mem else None)
        rails = r.get("power") or {}
        main_rail = rails.get("VDD_IN") or (next(iter(rails.values())) if rails else None)
        out["curr"].append(main_rail.get("ma") if main_rail else None)
        rate = r.get("swap_rate_pages_s")
        out["swaprate"].append(None if rate is None
                               else round((rate.get("in") or 0) + (rate.get("out") or 0), 1))
    return out


PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AMR PC 자원 감시</title>
<style>
:root{
  color-scheme: light dark;
  --surface-1:#fcfcfb; --surface-2:#f2f2f0; --line:#dcdcd8;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --text-muted:#7a7975;
  --series-1:#2a78d6; --grid:#e6e6e2;
  --good:#0ca30c; --warning:#fab219; --critical:#d03b3b;
}
@media (prefers-color-scheme: dark){:root{
  --surface-1:#1a1a19; --surface-2:#232322; --line:#3a3a38;
  --text-primary:#fff; --text-secondary:#c3c2b7; --text-muted:#8f8e86;
  --series-1:#3987e5; --grid:#2c2c2a;
}}
*{box-sizing:border-box}
body{margin:0;padding:16px;background:var(--surface-1);color:var(--text-primary);
 font:14px/1.5 system-ui,-apple-system,"Noto Sans KR",sans-serif}
h1{font-size:17px;margin:0 0 2px}
.sub{color:var(--text-muted);font-size:12px;margin-bottom:14px}
.banner{display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:8px;
 border:1px solid var(--line);background:var(--surface-2);margin-bottom:14px;font-weight:600}
.dot{font-size:15px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:10px;margin-bottom:18px}
.tile{border:1px solid var(--line);border-radius:8px;padding:10px 12px;background:var(--surface-2)}
.tile .k{font-size:11px;color:var(--text-secondary);letter-spacing:.02em}
.tile .v{font-size:24px;font-weight:650;font-variant-numeric:tabular-nums;margin-top:2px}
.tile .u{font-size:12px;color:var(--text-muted);font-weight:400}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;margin-bottom:18px}
.card{border:1px solid var(--line);border-radius:8px;padding:12px;background:var(--surface-2);overflow-x:auto}
.card h2{font-size:13px;margin:0 0 8px;font-weight:600;color:var(--text-secondary)}
svg{display:block;width:100%;height:120px;touch-action:none}
.gl{stroke:var(--grid);stroke-width:1}
.ln{fill:none;stroke:var(--series-1);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.ax{fill:var(--text-muted);font-size:10px}
.cx{stroke:var(--text-muted);stroke-width:1;stroke-dasharray:3 3;opacity:0}
.mk{fill:var(--series-1);stroke:var(--surface-2);stroke-width:2;opacity:0}
.tip{position:fixed;pointer-events:none;opacity:0;transition:opacity .08s;
 background:var(--surface-1);border:1px solid var(--line);border-radius:6px;
 padding:5px 8px;font-size:12px;font-variant-numeric:tabular-nums;
 box-shadow:0 2px 8px rgba(0,0,0,.18);z-index:9}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);
 font-variant-numeric:tabular-nums;white-space:nowrap}
th{color:var(--text-secondary);font-weight:600}
.f-good{color:var(--good)} .f-warning{color:var(--warning)} .f-critical{color:var(--critical)}
.wrap{overflow-x:auto}
footer{color:var(--text-muted);font-size:11px;margin-top:16px}
</style></head><body>
<h1>AMR PC 자원 감시</h1>
<div class="sub" id="sub">불러오는 중…</div>
<div class="banner" id="banner"><span class="dot" id="bdot">·</span><span id="btext">—</span></div>
<div class="tiles" id="tiles"></div>
<div class="charts">
  <div class="card"><h2>최고 존 온도 (°C)</h2><svg id="c-temp"></svg></div>
  <div class="card"><h2>CPU 사용률 (%)</h2><svg id="c-cpu"></svg></div>
  <div class="card"><h2>GPU 사용률 (%)</h2><svg id="c-gpu"></svg></div>
  <div class="card"><h2>입력 전류 VDD_IN (mA)</h2><svg id="c-curr"></svg></div>
  <div class="card"><h2>가용 메모리 (MB)</h2><svg id="c-mem"></svg></div>
  <div class="card"><h2>스왑 활동 (pages/s) — 사용량이 아니라 지금 쓰고 있는 양</h2><svg id="c-swap"></svg></div>
</div>
<div class="card" style="margin-bottom:16px"><h2>현재 경보</h2><div id="findings">—</div></div>
<div class="card" style="margin-bottom:16px"><h2>전원 레일</h2><div class="wrap" id="rails">—</div></div>
<div class="card" style="margin-bottom:16px"><h2>존별 온도 (°C)</h2><div class="wrap" id="zones">—</div></div>
<div class="card"><h2>최근 표본 (표 보기)</h2><div class="wrap" id="recent">—</div></div>
<div class="tip" id="tip"></div>
<footer>읽기 전용 — 아무것도 제어하지 않습니다. 5초마다 자동 갱신 ·
<a href="/api/report">텍스트 보고서</a> · <a href="/api/latest">JSON</a></footer>
<script>
const $=s=>document.querySelector(s), tip=$("#tip");
const LV={OK:["good","\\u25CF","정상"],WARN:["warning","\\u25B2","주의"],ERROR:["critical","\\u25A0","이상"]};
const fmt=(v,d=1)=>v===null||v===undefined?"\\u2014":Number(v).toFixed(d);

function line(sel,t,vals,unit,dec){
  const svg=$(sel); const W=svg.clientWidth||420, H=120, P={l:38,r:8,t:8,b:16};
  const pts=vals.map((v,i)=>[i,v]).filter(p=>p[1]!==null&&p[1]!==undefined);
  svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
  if(!pts.length){svg.innerHTML=`<text class="ax" x="${P.l}" y="${H/2}">값 없음</text>`;return;}
  let lo=Math.min(...pts.map(p=>p[1])), hi=Math.max(...pts.map(p=>p[1]));
  if(hi-lo<1e-9){hi=lo+1;lo=lo-1;}
  const pad=(hi-lo)*0.12; lo-=pad; hi+=pad;
  const X=i=>P.l+(W-P.l-P.r)*(vals.length<2?0.5:i/(vals.length-1));
  const Y=v=>P.t+(H-P.t-P.b)*(1-(v-lo)/(hi-lo));
  let g="";
  for(let k=0;k<=2;k++){const v=lo+(hi-lo)*k/2, y=Y(v);
    g+=`<line class="gl" x1="${P.l}" y1="${y}" x2="${W-P.r}" y2="${y}"/>`+
       `<text class="ax" x="2" y="${y+3}">${v.toFixed(dec)}</text>`;}
  const d=pts.map((p,j)=>`${j?"L":"M"}${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join("");
  svg.innerHTML=g+`<path class="ln" d="${d}"/>`+
    `<line class="cx" id="${sel.slice(1)}-cx" y1="${P.t}" y2="${H-P.b}"/>`+
    `<circle class="mk" id="${sel.slice(1)}-mk" r="4"/>`+
    `<text class="ax" x="${W-P.r}" y="${H-3}" text-anchor="end">${t[t.length-1]||""}</text>`+
    `<text class="ax" x="${P.l}" y="${H-3}">${t[0]||""}</text>`;
  const cx=$(`#${sel.slice(1)}-cx`), mk=$(`#${sel.slice(1)}-mk`);
  const move=e=>{const r=svg.getBoundingClientRect();
    const rx=(e.clientX-r.left)/r.width*W;
    let best=pts[0],bd=1e9;
    for(const p of pts){const dd=Math.abs(X(p[0])-rx); if(dd<bd){bd=dd;best=p;}}
    cx.setAttribute("x1",X(best[0]));cx.setAttribute("x2",X(best[0]));cx.style.opacity=.9;
    mk.setAttribute("cx",X(best[0]));mk.setAttribute("cy",Y(best[1]));mk.style.opacity=1;
    tip.textContent=`${t[best[0]]||""}  ${best[1].toFixed(dec)}${unit}`;
    tip.style.opacity=1;tip.style.left=Math.min(e.clientX+12,innerWidth-140)+"px";
    tip.style.top=(e.clientY-34)+"px";};
  svg.onpointermove=move; svg.onpointerdown=move;
  svg.onpointerleave=()=>{tip.style.opacity=0;cx.style.opacity=0;mk.style.opacity=0;};
}

function tile(k,v,u){return `<div class="tile"><div class="k">${k}</div>
  <div class="v">${v}<span class="u"> ${u||""}</span></div></div>`;}

async function tick(){
  let L,H;
  try{ L=await (await fetch("/api/latest",{cache:"no-store"})).json();
       H=await (await fetch("/api/history",{cache:"no-store"})).json(); }
  catch(e){ $("#sub").textContent="서버에 연결할 수 없습니다."; return; }
  if(L.empty){ $("#sub").textContent="표본이 없습니다 — 샘플러가 기록하지 못했습니다."; return; }
  const [role,icon,label]=LV[L.level]||["good","·","—"];
  $("#bdot").textContent=icon; $("#bdot").className="dot f-"+role;
  $("#btext").innerHTML=`판정 <span class="f-${role}">${label} (${L.level})</span>`
    +` · 경보 ${(L.findings||[]).length}건`;
  const temps=L.temperatures_c||{}, hot=Object.values(temps).length?Math.max(...Object.values(temps)):null;
  const m=L.memory||{}, dk=(L.disks||[{}])[0];
  const rails=L.power||{}, pw=rails["VDD_IN"]||Object.values(rails)[0]||null;
  $("#sub").textContent=`기록 ${L._first_time||"?"} ~ ${L.iso_time}`
    +` · 파일 ${L._files||0}개 ${(((L._bytes||0)/1048576)).toFixed(1)}MB`
    +` · 가동 ${((L.uptime_s||0)/3600).toFixed(1)}h`;
  $("#tiles").innerHTML=
     tile("최고 존 온도",fmt(hot),"°C")
    +tile("CPU 사용률",fmt(L.cpu_total_pct),"%")
    +tile("GPU 사용률",fmt(L.gpu&&L.gpu.load_pct),"%")
    +tile("GPU 주파수",L.gpu&&L.gpu.freq_hz?fmt(L.gpu.freq_hz/1e6,0):"\u2014","MHz")
    +tile("가용 메모리",fmt((m.available_mb||0)/1024,2),"GB")
    +tile("스왑 활동",L.swap_rate_pages_s?fmt((L.swap_rate_pages_s.in||0)+(L.swap_rate_pages_s.out||0),0):"\u2014","pages/s")
    +tile("스왑 누적",fmt(m.swap_used_mb,0),"MB")
    +tile("입력 전류",pw?fmt(pw.ma,0):"\\u2014","mA")
    +tile("입력 전력",pw?fmt(pw.mw/1000,1):"\\u2014","W")
    +tile("디스크 여유",fmt(dk.free_gb,1),"GB")
    +tile("팬 PWM",L.fan&&L.fan.pwm!==null?L.fan.pwm:"\\u2014","0-255")
    +tile("프로세스",L.process_count!==undefined?L.process_count:"\\u2014","개");
  line("#c-temp",H.t,H.temp,"°C",1); line("#c-cpu",H.t,H.cpu,"%",1);
  line("#c-gpu",H.t,H.gpu,"%",1);    line("#c-curr",H.t,H.curr," mA",0);
  line("#c-mem",H.t,H.mem,"MB",0);
  line("#c-swap",H.t,H.swaprate," p/s",0);
  const F=L.findings||[];
  $("#findings").innerHTML=F.length
    ? `<table><tr><th>등급</th><th>항목</th><th>내용</th></tr>`+F.map(f=>{
        const [r,i,l]=LV[f.level]||["good","·","—"];
        return `<tr><td class="f-${r}">${i} ${l}</td><td>${f.key}</td><td>${f.message}</td></tr>`;
      }).join("")+`</table>`
    : `<span class="f-good">\\u25CF 정상</span> — 임계 초과 항목 없음`;
  $("#rails").innerHTML=Object.keys(rails).length
    ? `<table><tr><th>레일</th><th>전압 V</th><th>전류 mA</th><th>전력 W</th></tr>`
      +Object.entries(rails).map(([k,v])=>`<tr><td>${k}</td><td>${fmt(v.mv/1000,2)}</td>`
      +`<td>${fmt(v.ma,0)}</td><td>${fmt(v.mw/1000,2)}</td></tr>`).join("")+`</table>`
    : "센서 없음";
  $("#zones").innerHTML=`<table><tr>`+Object.keys(temps).map(k=>`<th>${k.replace("-thermal","")}</th>`).join("")
    +`</tr><tr>`+Object.values(temps).map(v=>`<td>${fmt(v)}</td>`).join("")+`</tr></table>`;
  const n=Math.min(12,H.t.length);
  let rows="";
  for(let i=H.t.length-n;i<H.t.length;i++)
    rows=`<tr><td>${H.t[i]}</td><td>${fmt(H.temp[i])}</td><td>${fmt(H.cpu[i])}</td>`
        +`<td>${fmt(H.gpu[i])}</td><td>${fmt(H.mem[i],0)}</td><td>${fmt(H.swaprate[i],0)}</td></tr>`+rows;
  $("#recent").innerHTML=`<table><tr><th>시각</th><th>온도°C</th><th>CPU%</th><th>GPU%</th>`
    +`<th>가용MB</th><th>스왑p/s</th></tr>${rows}</table>`;
}
tick(); setInterval(tick,5000);
addEventListener("resize",()=>tick());
</script></body></html>
"""


class _Handler(BaseHTTPRequestHandler):
    """읽기 전용 핸들러. GET 만 처리한다."""

    log_dir: str = "."
    prefix: str = "health"
    interval_s: float = 5.0
    server_version = "system_health-webview"

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        """접속 로그를 끈다 — 감시 대상 PC 에 불필요한 I/O 를 만들지 않는다."""

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, payload: Any) -> None:
        self._send(200, json.dumps(payload, ensure_ascii=False, default=str).encode(),
                   "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802 - http.server 규약
        url = urlparse(self.path)
        try:
            if url.path == "/":
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif url.path == "/api/latest":
                self._json(latest_payload(tail_records(self.log_dir, 1, self.prefix),
                                          log_span(self.log_dir, self.prefix)))
            elif url.path == "/api/history":
                q = parse_qs(url.query)
                n = int(q.get("n", [DEFAULT_HISTORY])[0])
                self._json(history_payload(tail_records(self.log_dir, n, self.prefix), n))
            elif url.path == "/api/report":
                text = format_report(self.log_dir, self.interval_s, self.prefix)
                self._send(200, text.encode("utf-8"), "text/plain; charset=utf-8")
            else:
                self._send(404, b"not found\n", "text/plain; charset=utf-8")
        except (ValueError, OSError) as exc:
            # 서버가 죽으면 사람이 상태를 못 보게 되므로 요청 단위로만 실패시킨다.
            self._send(500, f"error: {exc}\n".encode(), "text/plain; charset=utf-8")

    do_HEAD = do_GET


def make_server(log_dir: str | Path, *, bind: str = DEFAULT_BIND, port: int = DEFAULT_PORT,
                prefix: str = "health", interval_s: float = 5.0) -> ThreadingHTTPServer:
    """서버 인스턴스를 만든다(아직 듣지 않는다 — 테스트가 port 0 으로 잡을 수 있게 분리).

    Args:
        log_dir: 읽을 JSONL 로그 디렉토리.
        bind: 바인드 주소. 기본 127.0.0.1(인증이 없으므로 외부 노출은 명시적 선택이어야 한다).
        port: 포트. 0 이면 임의 포트.
        prefix: 로그 파일명 접두.
        interval_s: 텍스트 보고서의 목표 주기.
    Returns:
        `ThreadingHTTPServer`.
    """
    handler = type("_Bound", (_Handler,), {
        "log_dir": str(log_dir), "prefix": prefix, "interval_s": interval_s})
    return ThreadingHTTPServer((bind, port), handler)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="system_health.webview",
        description="자원 감시 로컬 웹 대시보드 (읽기 전용 — 아무것도 제어하지 않는다)")
    p.add_argument("--log-dir", required=True, help="JSONL 로그 디렉토리")
    p.add_argument("--bind", default=DEFAULT_BIND,
                   help=f"바인드 주소 (기본 {DEFAULT_BIND}. 같은 망에서 보려면 0.0.0.0 — "
                        "인증이 없으므로 신뢰된 망에서만)")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"포트 (기본 {DEFAULT_PORT})")
    p.add_argument("--prefix", default="health", help="로그 파일명 접두")
    p.add_argument("--interval", type=float, default=5.0, help="텍스트 보고서의 목표 주기(초)")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """진입점. Ctrl+C 로 종료."""
    args = _parse_args(argv)
    srv = make_server(args.log_dir, bind=args.bind, port=args.port,
                      prefix=args.prefix, interval_s=args.interval)
    host, port = srv.server_address[:2]
    shown = "127.0.0.1" if str(host) in ("0.0.0.0", "::") else host
    print(f"대시보드: http://{shown}:{port}/   (로그 {args.log_dir})", flush=True)
    if args.bind not in ("127.0.0.1", "localhost", "::1"):
        print("⚠ 외부 바인드 — 인증이 없으므로 신뢰된 망에서만 사용하십시오.", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("종료", flush=True)
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
