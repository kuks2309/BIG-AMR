#!/usr/bin/env python3
"""조향축 `0x6064` 를 **제어권 상태 3구간**(미취득 → 취득 → 반환)에서 읽어 대조한다.

제어권을 쥐면 판다가 동결 스냅샷으로 응답하므로(`safety_seer_gate.h:88-96`), 판독이
구간에 따라 달라지는지 확인한다. 조향은 움직이지 않는다.

안전: 송신은 제어권 전환(`0xe8`/`0xe9`)·heartbeat(`0xf3`)·SDO 업로드 요청뿐이다.
`0x607A`·`0x60FF`·`0xea` 는 호출하지 않는다.
⚠ 제어권 반환 시 Seer 가 재호밍(조향 137° 스윙)을 개시할 수 있다 — 이동구역을 비울 것.

2026-08-03 19:05 결과: 세 구간 모두 실값(0 발생 0/7 × 3구간 × 2노드) — 구간 의존성 없음.
`debt-036` 의 오전 `0x6064`=0 은 드라이브가 죽어 있었던 것으로 종결됐다(registry 참조).

사용:
  python3 orin_frozen_readback.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from orin_home_experiment import OBJ_POS, Rig  # noqa: E402

OBJ_SW = 0x6041
NODES = (3, 4)
N_READ = 7          # 중앙값용 — 단발 판독 흔들림 제거


def sample(rig: Rig, tag: str) -> dict:
    out = {"tag": tag, "t": round(time.monotonic(), 3)}
    for n in NODES:
        pos = [v for v in (rig.sdo_read(n, OBJ_POS) for _ in range(N_READ)) if v is not None]
        sw = rig.sdo_read(n, OBJ_SW)
        out[f"pos{n}"] = int(statistics.median(pos)) if pos else None
        out[f"pos{n}_n"] = len(pos)
        out[f"pos{n}_zero"] = sum(1 for v in pos if v == 0)
        out[f"sw{n}"] = sw
        out[f"bit15_{n}"] = None if sw is None else (sw >> 15) & 1
    return out


def show(s: dict) -> None:
    print(f"  [{s['tag']:>22s}]", end="", flush=True)
    for n in NODES:
        p, z, cnt = s[f"pos{n}"], s[f"pos{n}_zero"], s[f"pos{n}_n"]
        sw, b = s[f"sw{n}"], s[f"bit15_{n}"]
        ps = "None" if p is None else f"{p:>10,}"
        print(f"  node{n} pos={ps} (0 이 {z}/{cnt})"
              f" sw={'None' if sw is None else f'0x{sw:04X}'} bit15={b}", end="")
    print(flush=True)


def main() -> int:
    print("=== 0x6064 제어권 3구간 판독 대조 — 읽기 전용·조향 무동작 ===", flush=True)
    print("⚠ 제어권 반환 시 Seer 가 재호밍(137° 스윙)을 낼 수 있다. 이동구역 확인.", flush=True)

    stamp = time.strftime("%y%m%d_%H%M%S")
    log = os.path.join(HERE, "..", "..", "Log", f"frozen_readback_{stamp}.json")
    log = os.path.abspath(log)
    rig = Rig(log.replace(".json", ".jsonl"))
    rows = []
    try:
        print("\n── A) passthrough (제어권 없음)", flush=True)
        rig.drain()
        a = sample(rig, "A_passthrough")
        rows.append(a)
        show(a)

        print("\n── B) pc_authority 취득 (조향 지령 없음)", flush=True)
        rig.take(settle=1.5)
        b = sample(rig, "B_authority")
        rows.append(b)
        show(b)

        print("\n── C) 반환 후 passthrough", flush=True)
        rig.release()
        time.sleep(1.5)
        rig.drain()
        c = sample(rig, "C_released")
        rows.append(c)
        show(c)

        # ---- 판정 ----
        print("\n=== 판정 ===", flush=True)
        verdict = []
        for n in NODES:
            za, zb, zc = a[f"pos{n}_zero"], b[f"pos{n}_zero"], c[f"pos{n}_zero"]
            na, nb, nc = a[f"pos{n}_n"], b[f"pos{n}_n"], c[f"pos{n}_n"]
            if nb and zb == nb and za == 0 and zc == 0:
                v = "제어권 구간에서만 0 — 판독이 제어권 상태에 의존"
            elif zb == 0 and za == 0 and zc == 0:
                v = "미재현 — 세 구간 모두 실값(이번 조건에서는 0 이 나오지 않음)"
            elif za or zc:
                v = "제어권 밖에서도 0 — 제어권 상태와 무관"
            else:
                v = "혼재 — 판정 보류"
            print(f"  node{n}: A {za}/{na} · B {zb}/{nb} · C {zc}/{nc}  ⇒ {v}", flush=True)
            verdict.append({"node": n, "zero": [za, zb, zc], "n": [na, nb, nc], "verdict": v})

        with open(log, "w", encoding="utf-8") as fh:
            json.dump({"rows": rows, "verdict": verdict}, fh, ensure_ascii=False, indent=2)
        print(f"\n산출: {log}", flush=True)
        return 0
    finally:
        try:
            rig.release()
        except Exception:
            pass
        rig.close()


if __name__ == "__main__":
    sys.exit(main())
