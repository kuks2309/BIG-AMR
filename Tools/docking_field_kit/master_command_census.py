#!/usr/bin/env python3
"""마스터(Seer)가 **실제로 쓰는 명령 집합**을 캡처에서 뽑는다 — 「우리가 만든 것인가」 판정용.

## 왜 만들었나

2026-08-03 에 `can_relay` 의 `halt_steer`(조향 정지) 가 **벤더 문서에 없는 우회 기법**이라고
`docs/debt/registry.md` 에 적었다. 근거는 Handbook 대조와 `docs/` grep 뿐이었고, **저장소에 있는
실측 캡처(`Log/*.jsonl`, 25만 프레임)를 대조하지 않았다.** 사용자가 「can log 에 이 명령이 있는지?」
라고 물어 확인해 보니 **마스터가 같은 조합을 12,928 회 쓰고 있었다** — 판정이 틀렸다
(`docs/claude-mistake/2026-08-03-002_halt-steer-verdict-without-capture.md`).

그래서 같은 질문을 **기억이 아니라 원자료로** 답하게 만든다.

## 무엇을 답하나

1. 마스터가 어떤 객체에 쓰기를 하는가 (객체별 횟수·서로 다른 값)
2. controlword 로 어떤 값을 보내는가 — **Halt(bit8) 를 쓰는가**
3. `0x607A`(목표 위치) 송신이 **그 시점 실측(`0x6064`)과 같은가** (= 「현 위치 유지」패턴인가)
4. **이동 중에 목표를 바꾸는가** (직전 창의 위치 변동으로 판정)

## 쓰는 법

    python3 Tools/docking_field_kit/master_command_census.py Log/homing_capture_220350.jsonl
    python3 Tools/docking_field_kit/master_command_census.py Log/*.jsonl --nodes 3 4

캡처 형식: 한 줄 = `{"t": <초>, "id": <CAN id>, "d": "<hex>"}` (그 외 키는 무시).
**읽기 전용** — 장치에 접속하지 않는다.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys

WRITE_CMD = {0x2F: 1, 0x2B: 2, 0x23: 4}     # expedited download 크기
READ_RSP = {0x43: 4, 0x47: 3, 0x4B: 2, 0x4F: 1}
OBJ_NAME = {
    0x6040: "controlword", 0x6041: "statusword", 0x6060: "modes",
    0x6064: "position_actual", 0x606C: "velocity_actual", 0x6078: "current_actual",
    0x607A: "target_position", 0x60FF: "target_velocity", 0x6081: "profile_velocity",
    0x6083: "profile_acc", 0x6084: "profile_dec", 0x6098: "homing_method",
    0x6099: "homing_speed", 0x60FB: "vendor_60FB", 0x100C: "guard_time",
    0x100D: "life_factor", 0x6000: "digital_input",
}
NEAR_C = 200            # 「목표 ≈ 현재」로 볼 허용 counts
MOVING_C = 500          # 직전 창에서 이 이상 변하면 「이동 중」
WINDOW_S = 0.5


def census(paths, nodes):
    req = {0x600 + n: n for n in nodes}
    rsp = {0x580 + n: n for n in nodes}
    pos = {}
    hist = collections.defaultdict(list)
    writes = collections.Counter()          # (node, index) -> 횟수
    values = collections.defaultdict(collections.Counter)
    cw = collections.Counter()
    target_rows = []
    total = 0

    for path in paths:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    cid = r["id"]
                    d = bytes.fromhex(r["d"])
                except (ValueError, KeyError):
                    continue
                total += 1
                if len(d) < 8:
                    continue
                cmd, idx = d[0], d[1] | (d[2] << 8)
                t = float(r.get("t", 0.0))
                if cid in rsp and cmd in READ_RSP and idx == 0x6064:
                    n = rsp[cid]
                    v = int.from_bytes(d[4:8], "little", signed=True)
                    pos[n] = v
                    hist[n].append((t, v))
                elif cid in req and cmd in WRITE_CMD:
                    n = req[cid]
                    size = WRITE_CMD[cmd]
                    v = int.from_bytes(d[4:4 + size], "little", signed=(size == 4))
                    writes[(n, idx)] += 1
                    values[(n, idx)][v] += 1
                    if idx == 0x6040:
                        cw[v] += 1
                    elif idx == 0x607A:
                        target_rows.append((t, n, v, pos.get(n)))
    return dict(total=total, writes=writes, values=values, cw=cw,
                target_rows=target_rows, hist=hist)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("captures", nargs="+")
    ap.add_argument("--nodes", type=int, nargs="+", default=[1, 2, 3, 4])
    a = ap.parse_args()

    c = census(a.captures, a.nodes)
    print(f"캡처 {len(a.captures)}개 · 총 {c['total']:,} 프레임 · 노드 {a.nodes}")

    print("\n=== ① 마스터가 쓰기를 보내는 객체 ===")
    if not c["writes"]:
        print("  (쓰기 0건 — 이 캡처는 마스터 송신을 담고 있지 않다)")
    for (n, idx), cnt in sorted(c["writes"].items(), key=lambda x: -x[1]):
        name = OBJ_NAME.get(idx, "?")
        nv = len(c["values"][(n, idx)])
        print(f"  node{n} 0x{idx:04X} {name:18s} {cnt:7,}회 · 서로 다른 값 {nv}개")

    print("\n=== ② controlword 값 분포 — Halt(bit8) 사용 여부 ===")
    if not c["cw"]:
        print("  (controlword 쓰기 0건)")
    halt = 0
    for v, cnt in c["cw"].most_common(12):
        is_halt = bool(v & 0x0100)
        halt += cnt if is_halt else 0
        print(f"  0x{v:04X}  {cnt:7,}회   bit4(new setpoint)={'1' if v & 0x10 else '0'} "
              f"bit5(change immediately)={'1' if v & 0x20 else '0'} "
              f"bit8(Halt)={'1' if is_halt else '0'}")
    print(f"  → Halt(bit8) 포함 송신 **{halt}회**")

    print("\n=== ③ 0x607A 송신이 그 시점 실측과 같은가 (「현 위치 유지」 패턴) ===")
    rows = [r for r in c["target_rows"] if r[3] is not None]
    near = [r for r in rows if abs(r[2] - r[3]) <= NEAR_C]
    if not rows:
        print("  (비교 가능한 송신 0건 — 0x6064 응답이 없다)")
    else:
        print(f"  |목표 − 실측| ≤ {NEAR_C}c : **{len(near):,} / {len(rows):,}회** "
              f"({100.0 * len(near) / len(rows):.1f} %)")

    print("\n=== ④ 이동 중에 목표를 바꾸는가 ===")
    far = [r for r in rows if abs(r[2] - r[3]) > 1000]
    seen, mid_motion = set(), 0
    for t, n, v, cur in far:
        if (n, v) in seen:
            continue
        seen.add((n, v))
        prev = [p for tt, p in c["hist"][n] if t - WINDOW_S <= tt < t]
        moving = (max(prev) - min(prev)) if len(prev) > 1 else 0
        if moving > MOVING_C:
            mid_motion += 1
        print(f"  t={t:9.3f} node{n} 목표={v:,} 실측={cur:,} "
              f"Δ={(v - cur) / 57344:+.2f}° · 직전 {WINDOW_S}s 위치변동={moving:,}c"
              f"{'  ← 이동 중 목표 변경' if moving > MOVING_C else ''}")
    if not far:
        print("  (현재 위치에서 1000c 이상 떨어진 목표 송신 0건)")
    print(f"  → **이동 중 목표 변경 {mid_motion}건**")

    print("\n판정에 쓰는 법: ②가 0 이면 「마스터도 Halt 를 쓰지 않는다」, "
          "③이 높으면 「현 위치를 목표로 유지하는 것은 마스터의 상시 동작」,\n"
          "④가 0 이면 **「이동 중 정지」는 이 캡처로 뒷받침되지 않는다** — "
          "그 주장을 하려면 별도 실측이 필요하다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
