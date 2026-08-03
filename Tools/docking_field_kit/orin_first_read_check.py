#!/usr/bin/env python3
"""engage 직후 첫 `0x6064` 판독이 실제 위치와 일치하는가 — 재현 확인용.

## 왜 만들었나 (2026-08-03 22:29 관측)

`can_relay` 드라이버로 제어권을 얻은 직후 조향 위치가 **홈 상수와 5 counts 차**로 읽혔고
(N3 7,871,810 / N4 7,840,091), 26 ms 뒤 같은 축이 **7,798,142 / 7,759,482** 로 읽혔다.
수동 판독(`orin_steer_crosscheck.py`, 송신 0건 20 초 2,109 샘플)은 **후자가 참**이라고 한다
(Seer 1040 도 +1.285° / +1.406° 로 정합).

문제는 `stop_all` → `halt_steer` 가 **읽은 값을 그대로 조향 목표(0x607A)로 써 넣는다**는 것이다.
첫 판독이 실제와 1.3° 다르면 **정지 명령이 축을 1.3° 움직이라고 지시**한다.

이 스크립트는 그 첫 판독을 시간순으로 남긴다. **조향 목표를 설정하지 않으므로 0x607A 를 내지
않는다**(구동은 0x60FF=0 = 정지 지령만 나간다).

⚠ 종료 시 `engage false` 경로가 `halt_steer` 를 부르며, 그때는 판독이 안정된 뒤라 참값이
목표가 된다. 그래도 축이 미세하게 움직일 수 있으므로 이동구역을 확인하고 실행할 것.
"""
from __future__ import annotations

import argparse
import json
import os
import time

from can_relay.backend import RelayBackend, RelayConfig
from can_relay.link import PandaLink

HOME = {3: 7871815, 4: 7840086}
COUNTS_PER_DEG = 57344.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--secs", type=float, default=6.0)
    args = ap.parse_args()

    link = PandaLink(log=lambda m: print(f"  [link] {m}", flush=True))
    cfg = RelayConfig(steer_home=dict(HOME), require_homed_for_steer=False,
                      poll_hz=10.0, cmd_hz=20.0)
    be = RelayBackend(link, cfg, log=lambda m: print(f"  [be] {m}", flush=True))

    rows = []
    try:
        link.open()
        link.acquire()
        t0 = time.monotonic()
        be.start()
        last = {}
        while time.monotonic() - t0 < args.secs:
            snap = be.snapshot()
            for n in (3, 4):
                p = snap["nodes"][n]["position"]
                if p is not None and last.get(n) != p:
                    last[n] = p
                    rows.append({"t_ms": round((time.monotonic() - t0) * 1000, 1),
                                 "node": n, "pos": p,
                                 "deg": round((p - HOME[n]) / COUNTS_PER_DEG, 4),
                                 "sw": snap["nodes"][n]["statusword"]})
            time.sleep(0.01)
    finally:
        try:
            be.shutdown()
        finally:
            link.release()
            link.close()

    print(f"\n=== engage 직후 위치 판독 변화 ({len(rows)} 건) ===")
    for r in rows[:24]:
        print(f"  t={r['t_ms']:7.1f} ms  N{r['node']}  pos={r['pos']:>10,}  "
              f"{r['deg']:+.4f}°  sw={r['sw']}")
    for n in (3, 4):
        vals = [r["pos"] for r in rows if r["node"] == n]
        if vals:
            print(f"  N{n}: 첫 판독 {vals[0]:,} · 마지막 {vals[-1]:,} · "
                  f"차 {vals[-1]-vals[0]:+,} counts "
                  f"({(vals[-1]-vals[0])/COUNTS_PER_DEG:+.3f}°)")

    repo = os.path.dirname(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Log")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"first_read_{time.strftime('%y%m%d_%H%M%S')}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"home": HOME, "rows": rows}, fh, ensure_ascii=False, indent=1)
    print(f"  산출물 {path}")


if __name__ == "__main__":
    main()
