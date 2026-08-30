#!/usr/bin/env python3
"""debt-002 판별 — intercept(relay 끊김) 유지 중 Seer 오류가 지속되는지.

목적: (a)스위칭 순간 단절이 원인이면 → 오류는 engage 초기만 나고 유지 중 사라짐.
      (b)Seer가 원하는 CAN 데이터를 못 받는 게 원인이면 → intercept 유지 내내 오류 지속.
방법: intercept를 15s 유지하며 resp/poll(판다) + Seer 알람 1050(52111 등)을 1.5s마다 동시 측정.
안전: auth=Seer 투명(게이트X), 0xf3 미전송, 종료 시 강제 passthrough.
"""
import sys
import time

sys.path.insert(0, "/home/nvidia/Project/CAN-Relay/docking_field_kit")
sys.path.insert(0, "/home/nvidia/T-Robot_seer_gui")
from panda import Panda
from seer_core.client import RobokitClient

LASER = ("52102", "52103")


def codes(arr):
    out = []
    for x in (arr or []):
        for k in x:
            if k not in ("desc", "times", "describe", "method", "reason"):
                out.append(k)
    return out


def seer_alarms(c):
    al = c.call("status", 1050)
    return codes(al.get("errors")), codes(al.get("warnings"))


def drain_resp(p, dt):
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
    hold = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    p = Panda()
    p.set_safety_mode(30, 0)   # SEER_GATE, disable_checks (0xf3 안 보냄)
    for b in (0, 2):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")  # auth=Seer 투명(게이트X)
    time.sleep(0.3)
    p.can_recv()
    c = RobokitClient("192.168.44.82", timeout=4.0)
    try:
        r, po = drain_resp(p, 1.0)
        e, w = seer_alarms(c)
        print("PASS baseline: resp=%d poll=%d | seer_err=%s" % (r, po, [x for x in e if x not in LASER] or "없음"))
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # intercept ON — HOLD
        t0 = time.time()
        while time.time() - t0 < hold:
            r, po = drain_resp(p, 1.5)
            try:
                e, w = seer_alarms(c)
                can_err = [x for x in e if x not in LASER]
                calib = "Y" if "54301" in w else "-"
            except Exception as ex:
                can_err, calib = ["<q:%s>" % str(ex)[:15]], "?"
            print("INTC t=%4.1f: resp=%4d poll=%4d | Seer CAN오류=%s calib=%s" % (
                time.time() - t0, r, po, can_err if can_err else "없음", calib))
    finally:
        try:
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
            p.set_safety_mode(0, 0)
            p.close()
        except Exception:
            pass
        try:
            c.close()
        except Exception:
            pass
    print("=== 판정: 유지 내내 CAN오류 지속 → Seer 데이터 미전달 원인 / 초기만 → 스위칭 순간 원인 ===")


if __name__ == "__main__":
    main()
