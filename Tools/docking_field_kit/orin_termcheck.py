#!/usr/bin/env python3
"""debt-002 확정 검증 — intercept 중 per-bus CAN 에러(종단/신호) 실측.

가설: intercept로 버스 2분할 시 각 세그먼트가 판다측 종단 없음(§4) → under-termination
      반사 → CAN bit/stuff/ack 에러 → TX 실패 → 모터 무응답(52111)/odo 손실(52106).
검증: passthrough baseline(에러 0) → intercept engage(auth=Seer 투명, 순수 forwarding) →
      can_health(0xc3)로 REC/TEC/lec/esr 시간분해 판독. 에러 급증+lec가 bit/stuff/ack면 종단 확정.
안전: 0xf3 미전송, 종료 시 강제 passthrough. (Seer calibration은 일시현상, 복구됨.)
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panda import Panda

LEC = {0: "no-err", 1: "stuff", 2: "form", 3: "ack", 4: "bit-recess",
       5: "bit-dom", 6: "crc", 7: "no-chg"}


def snap(p):
    return {b: p.can_health(b) for b in (0, 2)}


def herr(p):
    h = p.health()
    return "send_errs=%d fwd_errs=%d rx_errs=%d" % (
        h.get("can_send_errs", -1), h.get("can_fwd_errs", -1), h.get("can_rx_errs", -1))


def fmt(tag, s):
    parts = [tag]
    for b, nm in ((0, "bus0(Seer)"), (2, "bus2(Mot)")):
        h = s[b]
        parts.append("%s REC=%d TEC=%d ep=%d ew=%d boff=%d lec=%s" % (
            nm, h["receive_error_cnt"], h["transmit_error_cnt"],
            h["error_passive"], h["error_warning"], h["bus_off"],
            LEC.get(h["last_error_code"], "?")))
    return "  ".join(parts)


def drain_count(p, dt):
    resp = poll = 0
    te = time.time() + dt
    while time.time() < te:
        for addr, _, dat, bus in p.can_recv():
            if 0x581 <= addr <= 0x584 and bus == 2:
                resp += 1
            elif 0x601 <= addr <= 0x604 and bus == 0:
                poll += 1
        time.sleep(0.002)
    return resp, poll


def main():
    p = Panda()
    p.set_safety_mode(30, 0)   # SEER_GATE, disable_checks=True (0xf3 안 보냄)
    for b in (0, 2):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")  # auth=Seer(투명, 게이트X)
    time.sleep(0.3)
    p.can_recv()
    try:
        r, po = drain_count(p, 0.5)
        print(fmt("PASS baseline resp=%d poll=%d" % (r, po), snap(p)) + "  [" + herr(p) + "]")
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # intercept ON
        t0 = time.time()
        while time.time() - t0 < 3.0:
            r, po = drain_count(p, 0.4)
            print(fmt("INTC t=%.1f resp=%d poll=%d" % (time.time() - t0, r, po), snap(p)) + "  [" + herr(p) + "]")
    finally:
        try:
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
            p.set_safety_mode(0, 0)
        except Exception:
            pass
        try:
            p.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
