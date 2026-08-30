#!/usr/bin/env python3
"""실차(orin) 게이트 단위검증 — 0xf3(heartbeat) 미전송판.

가설: amap2_monitor gatecheck 누출의 원인은 0xf3 전송(→heartbeat_disabled=false→fail-safe→릴레이 OFF).
검증: set_safety_mode(disable_checks=True)로 heartbeat 비활성 유지(0xf3 안 보냄) + intercept + auth=PC.
      실 Seer의 SDO write(0x2B/0x23 등)가 모터측(bus2)에 도달하는지(=누출) 카운트.
기대: 0xf3 안 보내면 게이트 유지 → bus2 누출 0.
안전: 실 로봇 정차·attended 전제. 종료 시 강제 passthrough. 지정 초(기본 8s)만 개입.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panda import Panda

SEER_GATE = 30
SEER_BUS, MOTOR_BUS = 0, 2
DL_CMDS = (0x23, 0x27, 0x2B, 0x2F)   # SDO expedited download(쓰기)


def main():
    secs = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    p = Panda()
    p.set_safety_mode(SEER_GATE, 0)   # disable_checks=True → heartbeat_disabled=true (0xf3 안 보냄)
    for b in (SEER_BUS, MOTOR_BUS):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # intercept ON
    time.sleep(0.3)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 1, 0, b"")  # auth=PC
    # 전환 글리치/버스트 제외: 2초 정착 후 flush 하고 정상상태만 측정
    settle_leak = 0
    ts = time.time()
    while time.time() - ts < 2.0:
        for m in p.can_recv():
            a, _, d, bs = m
            if bs == MOTOR_BUS and 0x601 <= a <= 0x604 and len(d) >= 1 and d[0] in DL_CMDS:
                settle_leak += 1
        time.sleep(0.003)
    print("정착 2s 동안 bus2 누출(전환/초기)=%d" % settle_leak)
    p.can_recv()  # flush
    leak_w = 0        # bus2에 도달한 Seer 쓰기(누출)
    seer_w = 0        # bus0에서 관측된 Seer 쓰기(참고)
    resp = 0          # 모터 응답(0x581~584)
    guard = 0
    t0 = time.time()
    try:
        while time.time() - t0 < secs:
            for msg in p.can_recv():
                addr, _, dat, bus = msg
                if 0x601 <= addr <= 0x604 and len(dat) >= 1 and dat[0] in DL_CMDS:
                    if bus == SEER_BUS:
                        seer_w += 1
                    elif bus == MOTOR_BUS:
                        leak_w += 1
                elif 0x581 <= addr <= 0x584:
                    resp += 1
                elif 0x701 <= addr <= 0x704:
                    guard += 1
            time.sleep(0.003)
    finally:
        # 강제 passthrough 복귀
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
    print("intercept %ds (0xf3 미전송) 결과:" % secs)
    print("  Seer쓰기(bus0 관측)=%d  모터응답=%d  guard=%d" % (seer_w, resp, guard))
    print("  ⇒ 모터측(bus2) Seer쓰기 누출 = %d  (0=게이트 차단 정상, >0=누출)" % leak_w)
    print("판정: %s" % ("✅ 게이트 유지(누출 0) — 0xf3 미전송이 정답" if leak_w == 0
                        else "⚠ 누출 %d — 재해석 필요" % leak_w))


if __name__ == "__main__":
    main()
