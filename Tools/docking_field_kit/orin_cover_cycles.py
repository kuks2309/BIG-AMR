#!/usr/bin/env python3
"""FW 커버 반복 신뢰성 — engage/release 여러 번, 매번 52111/52106 안 나는지.

간헐적이던 문제라 N회 반복 검증. auth=Seer 투명, 커버는 0xe8 engage시 자동 발동.
"""
import sys
import time

sys.path.insert(0, "/home/nvidia/Project/CAN-Relay/docking_field_kit")
sys.path.insert(0, "/home/nvidia/T-Robot_seer_gui")
from panda import Panda
from seer_core.client import RobokitClient

LASER = ("52102", "52103")


def state(c):
    al = c.call("status", 1050)
    e = [k for x in (al.get("errors") or []) for k in x
         if k not in ("desc", "times", "describe", "method", "reason") and k not in LASER]
    w = [k for x in (al.get("warnings") or []) for k in x
         if k not in ("desc", "times", "describe", "method", "reason")]
    return e, ("54301" in w)


def drainms(p, dt):
    te = time.time() + dt
    while time.time() < te:
        p.can_recv()
        time.sleep(0.003)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    p = Panda()
    p.set_safety_mode(30, 0)
    for b in (0, 2):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")  # auth=Seer
    print("캐시 채우기 2s...")
    time.sleep(2.0)
    p.can_recv()
    c = RobokitClient("192.168.44.82", timeout=4.0)
    fired = 0
    try:
        for i in range(1, n + 1):
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # engage
            drainms(p, 2.5)
            e, cal = state(c)
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")  # release
            drainms(p, 2.0)
            e2, cal2 = state(c)
            can_bad = [x for x in e if x in ("52111", "52106")]
            if can_bad:
                fired += 1
            print("cycle %d: engage중 CAN오류=%s calib=%s | release후 CAN오류=%s" % (
                i, can_bad or "없음", "Y" if cal else "-", e2 or "없음"))
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
    print("=== %d회 중 52111/52106 발생 = %d회 (0이면 커버 신뢰) ===" % (n, fired))


if __name__ == "__main__":
    main()
