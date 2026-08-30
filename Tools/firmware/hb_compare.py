#!/usr/bin/env python3
"""근본원인 실증: 0xf3(heartbeat) 전송이 게이트를 무너뜨리는지 벤치로 대조.

A) heartbeat 미전송(set_safety_mode 기본 disable_checks=True → heartbeat_disabled=true 유지):
   게이트가 Seer 쓰기를 차단해야 함(모터 미도달).
B) 0xf3 1회 전송(→ heartbeat_disabled=false 재활성) 후 3s 무전송(fail-safe 임계 2s 초과):
   fail-safe → SILENT → 릴레이 OFF(passthrough) → Seer 쓰기가 모터에 누출돼야 함.

A차단 & B누출 이면: '0xf3가 fail-safe를 켜고, 못 대면 릴레이가 passthrough로 복귀해 누출'을 실증.
"""
import sys
import time

import os
sys.path.insert(0, os.path.expanduser("~/T-Robotics/CAN_Relay"))
import can
from panda import Panda

SEER_GATE = 30
SEER_BUS, MOTOR_BUS = 0, 2
WR = [0x2B, 0xFF, 0x60, 0x00, 0x8D, 0x09, 0x00, 0x00]  # Seer SDO write (0x2B)


def drain(bus, t=0.3):
    out, end = [], time.time() + t
    while time.time() < end:
        m = bus.recv(timeout=0.05)
        if m is not None:
            out.append(m)
    return out


def reached(msgs, aid=0x601):
    return any(m.arbitration_id == aid for m in msgs)


def main():
    # seer_gate_bench 검증 구조 그대로 복제: 버스 먼저 → 판다 → intercept → T1워밍업 → auth=PC
    seer = can.Bus(channel="can0", interface="socketcan")
    motor = can.Bus(channel="can1", interface="socketcan")
    p = Panda()
    p.set_safety_mode(SEER_GATE, 0)   # disable_checks=True → 0xf8 → heartbeat_disabled=true
    for b in (SEER_BUS, MOTOR_BUS):
        p.set_can_speed_kbps(b, 250)
        p.set_can_enable(b, True)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")  # intercept ON
    time.sleep(0.3)
    rd = can.Message(arbitration_id=0x601, data=bytes([0x40, 0x64, 0x60, 0, 0, 0, 0, 0]),
                     is_extended_id=False)
    wr = can.Message(arbitration_id=0x601, data=bytes(WR), is_extended_id=False)
    try:
        # T1 워밍업(auth=Seer): 읽기 통과 확인 = 포워딩 활성
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")  # auth=Seer
        time.sleep(0.1)
        drain(motor, 0.1)
        seer.send(rd)
        warm = reached(drain(motor, 0.2))
        print("warmup(auth=Seer read 도달)=%s" % warm)
        # auth=PC
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 1, 0, b"")  # auth=PC
        time.sleep(0.1)
        # --- A: heartbeat 미전송 (disabled 유지) ---
        drain(motor, 0.1)
        seer.send(wr)
        a = drain(motor, 0.4)
        a_reached = reached(a)
        print("A) heartbeat 미전송: Seer write -> 모터 도달 = %s  (기대 False=차단)" % a_reached)

        # --- B: 0xf3 1회 후 3s 무전송 ---
        p._handle.controlWrite(Panda.REQUEST_OUT, 0xf3, 0, 0, b"")  # heartbeat check 재활성+리셋
        print("   0xf3 전송(heartbeat 체크 재활성). 3s 대기(추가 heartbeat 없음, 임계 2s)...")
        time.sleep(3.0)
        drain(motor, 0.1)
        seer.send(wr)
        b = drain(motor, 0.4)
        b_reached = reached(b)
        print("B) 0xf3+3s 갭: Seer write -> 모터 도달 = %s  (기대 True=누출)" % b_reached)

        verdict = (not a_reached) and b_reached
        print("=== 실증: %s ===" % (
            "성공 — A차단·B누출 → 0xf3가 fail-safe 켜고 릴레이 passthrough 복귀로 누출"
            if verdict else "불일치 — A도달=%s B도달=%s (재해석 필요)" % (a_reached, b_reached)))
    finally:
        try:
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
            p.set_safety_mode(0, 0)
            p.close()
        except Exception:
            pass
        seer.shutdown()
        motor.shutdown()


if __name__ == "__main__":
    main()
