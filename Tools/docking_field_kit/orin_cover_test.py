#!/usr/bin/env python3
"""FW 전환 커버 검증 — engage 시 Seer Motor timeout(52111/52106)이 안 나는지.

절차: SEER_GATE + auth=Seer(투명) → 캐시 채우기 2s 대기 → engage(0xe8=1, 커버 300ms 발동) → 8s 유지.
매 1s Seer 알람(1050) + resp 측정. 커버 성공 시 52111/52106 미발생.
종료 시 강제 passthrough.
"""
import sys
import time

sys.path.insert(0, "/home/nvidia/Project/CAN-Relay/docking_field_kit")
sys.path.insert(0, "/home/nvidia/T-Robot_seer_gui")
from panda import Panda
from seer_core.client import RobokitClient

LASER = ("52102", "52103")


def can_errs(c):
    al = c.call("status", 1050)
    e = []
    for x in (al.get("errors") or []):
        for k in x:
            if k not in ("desc", "times", "describe", "method", "reason") and k not in LASER:
                e.append(k)
    w = []
    for x in (al.get("warnings") or []):
        for k in x:
            if k not in ("desc", "times", "describe", "method", "reason"):
                w.append(k)
    return e, ("54301" in w)


def drain(p, dt):
    resp = 0
    te = time.time() + dt
    while time.time() < te:
        for a, _, d, bs in p.can_recv():
            if 0x581 <= a <= 0x584 and bs == 2:
                resp += 1
        time.sleep(0.002)
    return resp


def main():
    p = Panda()
    p.set_safety_mode(30, 0)   # SEER_GATE → fwd훅 활성(캐시 시작)
    for b in (0, 2):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")  # auth=Seer 투명
    print("SEER_GATE + 캐시 채우기 2s...")
    time.sleep(2.0)
    p.can_recv()
    c = RobokitClient("192.168.44.82", timeout=4.0)
    try:
        e, cal = can_errs(c)
        print("engage 전 baseline: CAN오류=%s calib=%s" % (e or "없음", cal))
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # engage → 커버 발동
        t0 = time.time()
        while time.time() - t0 < 8.0:
            r = drain(p, 1.0)
            try:
                e, cal = can_errs(c)
            except Exception as ex:
                e, cal = ["<q>"], False
            print("INTC t=%4.1f: resp=%4d | Seer CAN오류=%s calib=%s" % (
                time.time() - t0, r, e or "없음", "Y" if cal else "-"))
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
    print("=== 판정: engage/유지 중 CAN오류 없으면 커버 성공 ===")


if __name__ == "__main__":
    main()
