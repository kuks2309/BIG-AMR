#!/usr/bin/env python3
"""도킹 속임수 시나리오 벤치 (양방향) — PC가 모터 구동 + Seer 인식 유지.

2026-07-20 검증: 6/6 PASS. seer_gate_bench.py(게이트 단위검증)의 상위 — 실제 도킹 흐름을
한 번에 재현: PC가 CAN2로 모터를 구동하는 동안 Seer(CAN0)는 모터가 살아있다고 계속 인식.

토폴로지 (클론 U3P-3.2 핀맵 — comma 표준 아님!):
  PCAN can0 = 가짜 Seer  → 판다 CAN0 (H=pin4,  L=pin5·6)
  PCAN can1 = 가짜 모터  → 판다 CAN2 (H=pin23, L=pin24)   ← CAN2_H는 pin23!
  판다 = intercept + SEER_GATE + auth=PC

검증:
  A1 모터 guard응답(0x701)  → Seer 도달   (Seer가 모터 생존 인식)
  A2 모터 SDO응답(0x581)    → Seer 도달
  B1 PC 구동명령(0x601)     → 모터 도달   (PC가 CAN2로 모터 구동)
  B2 PC 명령이 Seer에 에코 안 됨         (PC 개입 은폐)
  C1 Seer 읽기(0x40)        → 모터 도달   (Seer 폴링 유지)
  C2 Seer guard RTR(0x701)  → 모터 도달(RTR)

사전: can0/can1 250k up, 판다 USB 연결. 실행: python3 Tools/panda_bench/docking_scenario_bench.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/T-Robotics/CAN_Relay"))
try:
    import can
except ImportError:
    sys.exit("python-can 필요: pip3 install --user python-can")
from panda import Panda

SEER, MOTOR = 0, 2
SAFETY_SEER_GATE = 30
KBPS = int(os.environ.get("BENCH_KBPS", "250"))


def main():
    p = Panda()
    p.set_safety_mode(SAFETY_SEER_GATE, 0)
    for b in (SEER, MOTOR):
        p.set_can_speed_kbps(b, KBPS)
        p.set_can_enable(b, True)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 1, 0, b"")   # auth=PC (게이트 ON)
    p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")   # intercept
    time.sleep(0.4)

    seer = can.Bus(channel="can0", interface="socketcan")   # 가짜 Seer
    motor = can.Bus(channel="can1", interface="socketcan")  # 가짜 모터
    results = []

    def drain(bus, t=0.35):
        out, end = [], time.time() + t
        while time.time() < end:
            m = bus.recv(timeout=0.05)
            if m is not None:
                out.append((m.arbitration_id, bool(m.is_remote_frame)))
        return out

    def has(msgs, aid, rtr=None):
        return any(a == aid and (rtr is None or r == rtr) for a, r in msgs)

    def chk(name, ok):
        results.append(ok)
        print(("  PASS " if ok else "  FAIL ") + name)

    try:
        # A. 모터 → Seer 인식신호
        drain(seer, 0.1)
        motor.send(can.Message(arbitration_id=0x701, data=bytes([0x05]), is_extended_id=False))
        motor.send(can.Message(arbitration_id=0x581, data=bytes([0x43, 0x64, 0x60, 0, 1, 2, 3, 4]), is_extended_id=False))
        s = drain(seer)
        chk("A1 모터 guard응답(0x701) → Seer 도달", has(s, 0x701))
        chk("A2 모터 SDO응답(0x581) → Seer 도달", has(s, 0x581))

        # B. PC 구동 + 에코 차단
        drain(motor, 0.1); drain(seer, 0.1)
        p.can_send(0x601, bytes([0x23, 0xFF, 0x60, 0, 0x8D, 0x09, 0, 0]), MOTOR)
        chk("B1 PC 구동명령(0x601) → 모터 도달", has(drain(motor), 0x601))
        chk("B2 PC 명령이 Seer에 에코 안 됨", not has(drain(seer), 0x601))

        # C. Seer 폴링 유지
        drain(motor, 0.1)
        seer.send(can.Message(arbitration_id=0x601, data=bytes([0x40, 0x64, 0x60, 0, 0, 0, 0, 0]), is_extended_id=False))
        chk("C1 Seer 읽기(0x40) → 모터 도달", has(drain(motor), 0x601))
        drain(motor, 0.1)
        seer.send(can.Message(arbitration_id=0x701, is_remote_frame=True, dlc=0, is_extended_id=False))
        chk("C2 Seer guard RTR → 모터 도달(RTR)", has(drain(motor), 0x701, rtr=True))
    finally:
        try:
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
            p.set_safety_mode(0, 0)
            p.close()
        except Exception:
            pass
        seer.shutdown(); motor.shutdown()

    npass = sum(results)
    print(f"\n=== {npass}/{len(results)} PASS ===")
    sys.exit(0 if npass == len(results) else 1)


if __name__ == "__main__":
    main()
