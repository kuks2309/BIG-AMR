#!/usr/bin/env python3
"""Seer↔모터 SDO 폴링 패턴 캡처 (passthrough SILENT 탭, 읽기전용).

FW 가짜응답 커버 설계용: Seer가 읽는(0x40) SDO 객체(node·index·sub)와 모터의 응답 프레임을
열거해 '무엇을 캐시/합성해야 하는지' 확정. + 쓰기·guard도 집계.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panda import Panda

SECS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
UP_REQ = 0x40
UP_RESP = {0x43: 4, 0x47: 3, 0x4B: 2, 0x4F: 1, 0x42: 0}  # 읽기 응답
WR_CMDS = {0x2F: 1, 0x2B: 2, 0x27: 3, 0x23: 4, 0x22: 0}


def main():
    p = Panda()
    p.set_safety_mode(0, 0)   # SILENT 탭(읽기전용)
    for b in (0, 2):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    time.sleep(0.2)
    p.can_recv()
    reads = {}    # (node,index,sub) -> count  (Seer 읽기요청)
    resps = {}    # (node,index,sub) -> (cmd, datahex, count)  (모터 읽기응답)
    writes = {}   # (node,index,sub) -> count
    acks = {}     # node -> count (0x60)
    guard_req = {}
    guard_resp = {}
    t0 = time.time()
    while time.time() - t0 < SECS:
        for addr, _, dat, bus in p.can_recv():
            if not dat:
                continue
            if 0x601 <= addr <= 0x604:
                node = addr - 0x600
                cmd = dat[0]
                if cmd == UP_REQ and len(dat) >= 4:
                    idx = dat[1] | (dat[2] << 8); sub = dat[3]
                    reads[(node, idx, sub)] = reads.get((node, idx, sub), 0) + 1
                elif cmd in WR_CMDS and len(dat) >= 4:
                    idx = dat[1] | (dat[2] << 8); sub = dat[3]
                    writes[(node, idx, sub)] = writes.get((node, idx, sub), 0) + 1
            elif 0x581 <= addr <= 0x584:
                node = addr - 0x580
                cmd = dat[0]
                if cmd in UP_RESP and len(dat) >= 4:
                    idx = dat[1] | (dat[2] << 8); sub = dat[3]
                    k = (node, idx, sub)
                    resps[k] = (cmd, dat.hex() if hasattr(dat, "hex") else bytes(dat).hex(),
                                resps.get(k, (0, "", 0))[2] + 1)
                elif cmd == 0x60:
                    acks[node] = acks.get(node, 0) + 1
            elif 0x701 <= addr <= 0x704:
                guard_resp[addr - 0x700] = guard_resp.get(addr - 0x700, 0) + 1
    p.close()

    print("=== Seer 읽기요청(0x40) — 캐시/합성 대상 ===")
    for (n, i, s), c in sorted(reads.items()):
        print("  node%d  0x%04X:%02X  x%d  (%.0f/s)" % (n, i, s, c, c / SECS))
    print("=== 모터 읽기응답(0x4x) — 캐시할 응답 프레임 ===")
    for (n, i, s), (cmd, hx, c) in sorted(resps.items()):
        print("  node%d  0x%04X:%02X  cmd=0x%02X data=%s  x%d" % (n, i, s, cmd, hx, c))
    print("=== Seer 쓰기(정차중 position-hold) ===")
    for (n, i, s), c in sorted(writes.items()):
        print("  node%d  0x%04X:%02X  x%d" % (n, i, s, c))
    print("=== 쓰기ack(0x60) per node:", acks, "===")
    print("=== nodeguard 응답(0x70x) per node:", guard_resp, "===")


if __name__ == "__main__":
    main()
