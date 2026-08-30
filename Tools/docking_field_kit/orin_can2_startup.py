#!/usr/bin/env python3
"""정공법 — 모터 CAN2 갭(40~234ms)의 정체 규명.

engage 직후 bus2의 CAN 에러상태(REC/TEC/bus_off/ep/ew/lec)를 고속 샘플하며 첫 모터응답까지 시간 측정.
판별: bus2 에러상태(bus_off/ep) → 판다 CAN2 컨트롤러 startup 문제 /
      bus2 깨끗한데 resp만 오래 0 → 모터 드라이버가 순간단절에 반응해 전송 멈춤(모터측).
auth=Seer 투명, 종료 시 강제 passthrough.
"""
import sys
import time

sys.path.insert(0, "/home/nvidia/Project/CAN-Relay/docking_field_kit")
from panda import Panda

LEC = {0: "no-err", 1: "stuff", 2: "form", 3: "ack", 4: "bit-rec", 5: "bit-dom", 6: "crc", 7: "no-chg"}


def main():
    p = Panda()
    p.set_safety_mode(30, 0)
    for b in (0, 2):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
    time.sleep(0.3)
    p.can_recv()
    h0 = p.can_health(2)
    samples = []
    first_resp = None
    t_eng = time.time()
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # engage
    try:
        while (time.time() - t_eng) < 0.4:
            fr = p.can_recv()
            resp = sum(1 for a, _, d, bs in fr if 0x581 <= a <= 0x584 and bs == 2)
            if resp and first_resp is None:
                first_resp = (time.time() - t_eng) * 1000
            h = p.can_health(2)
            samples.append(((time.time() - t_eng) * 1000, h["receive_error_cnt"],
                            h["transmit_error_cnt"], h["bus_off"], h["error_passive"],
                            h["error_warning"], h["last_error_code"], resp))
    finally:
        try:
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
            p.set_safety_mode(0, 0)
            p.close()
        except Exception:
            pass
    print("baseline bus2: REC=%d TEC=%d boff=%d ep=%d" % (
        h0["receive_error_cnt"], h0["transmit_error_cnt"], h0["bus_off"], h0["error_passive"]))
    print("첫 모터응답까지: %s ms" % (round(first_resp, 1) if first_resp else ">400 (미수신)"))
    print("t(ms)  REC TEC boff ep ew  lec       resp")
    prev_resp0 = True
    for t, rec, tec, bo, ep, ew, lec, resp in samples:
        # resp 0→nonzero 전이 근처 + 처음 몇 개만 촘촘히, 나머지는 솎기
        if t < 30 or resp > 0 or (prev_resp0 and resp > 0):
            print("%5.0f  %3d %3d %4d %2d %2d  %-8s %3d" % (t, rec, tec, bo, ep, ew, LEC.get(lec, "?"), resp))
        prev_resp0 = (resp == 0)


if __name__ == "__main__":
    main()
