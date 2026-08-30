#!/usr/bin/env python3
"""debt-002 전환 글리치 시간분해 계측 (실차 orin, 0xf3 미전송).

재호밍 트리거 = 전환 순간 Seer가 모터 응답/guard를 잃는 것(단절 감지). 그래서 intercept
engage 전후를 200ms 버킷으로 계측:
  seer_poll(bus0 0x601~604) · motor_resp(bus2 0x581~584) · guard(0x701~704) · leak(bus2 write)
버킷별 응답수가 baseline 대비 급락하는 구간 = 통신 갭 = 재호밍 위험.

절차: (1) passthrough에서 baseline 1s → (2) 0xe8=1 intercept engage → 이후 계측 →
      (3) 강제 passthrough. 0xf3 미전송(게이트 유지). 실 로봇 정차·attended 전제.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panda import Panda

SEER_BUS, MOTOR_BUS = 0, 2
DL_CMDS = (0x23, 0x27, 0x2B, 0x2F)
BUCKET = 0.2   # 200ms


def classify(addr, dat, bus):
    if 0x601 <= addr <= 0x604:
        if bus == MOTOR_BUS and len(dat) >= 1 and dat[0] in DL_CMDS:
            return "leak"
        if bus == SEER_BUS:
            return "poll"
    elif 0x581 <= addr <= 0x584 and bus == MOTOR_BUS:
        return "resp"
    elif 0x701 <= addr <= 0x704:
        return "guard"
    return None


def measure(p, secs, label, buckets):
    t0 = time.time()
    while time.time() - t0 < secs:
        bi = int((time.time() - t0) / BUCKET)
        while len(buckets) <= bi:
            buckets.append({"poll": 0, "resp": 0, "guard": 0, "leak": 0, "t": label})
        for addr, _, dat, bus in p.can_recv():
            c = classify(addr, dat, bus)
            if c:
                buckets[bi][c] += 1
        time.sleep(0.002)


def main():
    p = Panda()
    p.set_safety_mode(30, 0)   # SEER_GATE, disable_checks=True(0xf3 안 보냄)
    for b in (SEER_BUS, MOTOR_BUS):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    p.can_recv()
    buckets = []
    try:
        # (1) passthrough baseline 1s (relay off)
        measure(p, 1.0, "PASS", buckets)
        # (2) intercept engage
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # relay ON
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 1, 0, b"")  # auth=PC
        engage_bucket = len(buckets)
        measure(p, 3.0, "INTC", buckets)
    finally:
        try:
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
            p.set_safety_mode(0, 0)
        except Exception:
            pass
        try:
            p.close()
        except Exception:
            pass
    print("engage @ bucket %d (t=%.1fs). 버킷=%dms" % (engage_bucket, engage_bucket * BUCKET, int(BUCKET * 1000)))
    print("bkt  구간   poll resp guard leak")
    for i, b in enumerate(buckets):
        mark = " <== ENGAGE" if i == engage_bucket else ""
        print("%3d  %-4s  %4d %4d %5d %4d%s" % (i, b["t"], b["poll"], b["resp"], b["guard"], b["leak"], mark))
    # 응답 갭 탐지
    base = [b["resp"] for b in buckets[:5] if b["t"] == "PASS"]
    base_avg = sum(base) / max(1, len(base))
    gaps = [i for i, b in enumerate(buckets) if b["t"] == "INTC" and b["resp"] < 0.4 * base_avg]
    print("baseline resp/버킷=%.0f · 응답갭(0.4x미만) 버킷=%s" % (base_avg, gaps if gaps else "없음"))


if __name__ == "__main__":
    main()
