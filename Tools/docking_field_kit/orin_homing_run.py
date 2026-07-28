#!/usr/bin/env python3
"""펌웨어 조향 호밍 시퀀서 실행·관측 (0xea 개시 / 0xeb 상태폴).

판다 펌웨어가 조향 호밍을 지휘하고, 본 스크립트는 개시·상태폴·CAN2 기록만 한다.
**모터 지령 프레임은 호스트가 보내지 않는다** — 전부 펌웨어가 보낸다.

동작: 제어권 획득(safety 30 + auth=PC + intercept) → 0xea 개시 → 0xeb 폴 → 종료 시 release.
⚠ 조향축이 원점(리밋)까지 갔다가 조향 0° 로 복귀한다. 접지 상태면 차체가 움직일 수 있다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panda import Panda  # noqa: E402

SEER_BUS, MOTOR_BUS = 0, 2
SEER_GATE, CAN_KBPS, HEARTBEAT_S = 30, 250, 0.4
CPD = 57344.0
STATE = {0: "IDLE", 1: "ENABLE", 2: "SET_SPEED", 3: "START", 4: "WAIT(원점탐색)",
         5: "DONE(0° 복귀완료)", 6: "ERR_TIMEOUT", 7: "ERR_ABORT", 8: "RESTORE",
         9: "GOZERO", 10: "ERR_GOZERO", 11: "GOZERO_W"}
TERMINAL = {0, 5, 6, 7, 10}
RD = {0x43: 4, 0x47: 3, 0x4B: 2, 0x4F: 1}


def s32(b):
    v = int.from_bytes(b[:4], "little")
    return v - (1 << 32) if v & 0x80000000 else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=200.0)
    ap.add_argument("--speed", type=int, default=0, help="0=펌웨어 기본(2500)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or f"/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Log/homing_run_{int(time.time())}.jsonl"

    p = Panda()
    print(f"판다: {p.get_version()}  bootstub={p.bootstub}", flush=True)
    p.set_safety_mode(0, 0)
    for b in (SEER_BUS, MOTOR_BUS):
        p.set_can_speed_kbps(b, CAN_KBPS)
        p.set_can_enable(b, True)
    time.sleep(0.2)
    p.can_recv()

    controlling = False
    t0 = time.time()
    last_state = None
    pos = {3: None, 4: None}
    log = open(out, "w")
    try:
        print(">>> 제어권 획득", flush=True)
        p.set_safety_mode(SEER_GATE, 0)
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 1, 0, b"")
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")
        controlling = True
        last_hb = time.time()
        time.sleep(1.0)   # 캐시 워밍

        ok = p._handle.controlRead(Panda.REQUEST_IN, 0xea, 1, args.speed, 1)
        print(f">>> 0xea 호밍 개시 → {'수락' if ok[0] == 1 else '거부'}", flush=True)
        if ok[0] != 1:
            return

        deadline = time.time() + args.timeout
        while time.time() < deadline:
            if (time.time() - last_hb) > HEARTBEAT_S:
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xf3, 0, 0, b"")
                last_hb = time.time()
            for addr, _, dat, bus in p.can_recv():
                if bus != MOTOR_BUS or not dat:
                    continue
                d = bytes(dat)
                log.write(json.dumps({"t": round(time.time() - t0, 4), "id": addr,
                                      "d": d.hex()}) + "\n")
                if 0x583 <= addr <= 0x584 and len(d) >= 8 and d[0] in RD:
                    if (d[1] | (d[2] << 8)) == 0x6064:
                        pos[addr - 0x580] = s32(d[4:8])
            r = p._handle.controlRead(Panda.REQUEST_IN, 0xeb, 0, 0, 8)
            st = r[0]
            if st != last_state:
                p3 = f"{pos[3] / CPD:+7.2f}°" if pos[3] is not None else "   ?   "
                p4 = f"{pos[4] / CPD:+7.2f}°" if pos[4] is not None else "   ?   "
                print(f"  [{time.time() - t0:6.2f}s] state={st} {STATE.get(st, '?'):<16s} "
                      f"원점={r[1]:#04x} 진행중관측={r[2]:#04x} 도달={r[7]:#04x}  "
                      f"DI3={r[5]:#04x} DI4={r[6]:#04x}  node3={p3} node4={p4}", flush=True)
                last_state = st
            if st in TERMINAL and st != 0:
                print(f"\n>>> 종료 상태: {st} ({STATE.get(st)})", flush=True)
                break
            time.sleep(0.1)
        else:
            print("\n>>> 스크립트 타임아웃 — 중단 명령 전송", flush=True)
            p._handle.controlRead(Panda.REQUEST_IN, 0xea, 0, 0, 1)
    finally:
        log.close()
        if controlling:
            try:
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
                p.set_safety_mode(0, 0)
                print("[finally] 제어권 반환 + passthrough 복귀", flush=True)
            except Exception as exc:
                print(f"[finally] ⚠ release 실패: {exc}", flush=True)
        try:
            p.close()
        except Exception:
            pass
    print(f"raw 로그: {out}", flush=True)


if __name__ == "__main__":
    main()
