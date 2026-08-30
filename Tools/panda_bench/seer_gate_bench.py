#!/usr/bin/env python3
"""Seer 게이트 PCAN 벤치 테스트 (실모터 없이 게이트 로직 검증).

목적: 블랙판다 도킹 릴레이 펌웨어(#1 RTR + #2 릴레이분리 + #C Seer 게이트)의
      실동작을 PCAN 2채널 + 판다로 검증. 근거: docs/adr/2026-07-20-panda-docking-firmware.md 3단계.

토폴로지 (판다 intercept 시 두 세그먼트 물리 분리):
    [PCAN can0 = 가짜 Seer] ── Seer 세그먼트(26핀 CAN0: 4/6) ── [판다 bus0]
                                                                     │ 펌웨어 게이트
    [PCAN can1 = 가짜 모터] ── 모터 세그먼트(클론 U3P 26핀 CAN2: H=23, L=24 — pin22 死핀) ── [판다 bus2]
  각 세그먼트 2노드(PCAN+판다) → ACK 성립. 종단은 PCAN 자체 120Ω + 하니스.

사전 (amap-1, root 1회):
    sudo ip link set can0 up type can bitrate 250000   # PCAN ch1 = Seer 세그먼트
    sudo ip link set can1 up type can bitrate 250000   # PCAN ch2 = 모터 세그먼트
    # 판다 USB 연결, udev 규칙 적용(bbaa:ddcc)

실행:
    python3 Tools/panda_bench/seer_gate_bench.py

검증 항목 (auth=PC, intercept):
  T1 passthrough(auth=Seer): can0 프레임 → can1 도달
  T2 Seer 쓰기 차단        : can0 SDO write → can1 미도달
  T3 가짜 ack 합성         : can0 SDO write → can0 이 0x581 60.. 수신
  T4 Seer 읽기 통과        : can0 SDO read  → can1 도달
  T5 guard RTR 통과(#1 검증): can0 0x701 RTR → can1 이 RTR 프레임 수신
  T6 PC 직접구동           : 판다 CAN_TX(bus2) → can1 도달
"""
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/T-Robotics/CAN_Relay"))

try:
    import can  # python-can
except ImportError:
    sys.exit("python-can 필요: pip3 install --user python-can")
from panda import Panda

SEER_IF = "can0"   # 가짜 Seer 세그먼트 (판다 bus0)
MOTOR_IF = "can1"  # 가짜 모터 세그먼트 (판다 bus2)
# 실 Tongyi 시스템 = 250k. 벤치 인터페이스가 다른 속도면 BENCH_KBPS 로 맞춘다
# (게이트 로직은 비트레이트 무관). 판다 버스 속도도 이 값으로 설정.
BENCH_KBPS = int(os.environ.get("BENCH_KBPS", "250"))
BITRATE = BENCH_KBPS * 1000
SAFETY_SEER_GATE = 30
PANDA_BUS_SEER = 0
PANDA_BUS_MOTOR = 2

# 판다 vendor request
REQ_RELAY_SET = 0xe8   # wValue 0=passthrough 1=intercept
REQ_AUTH_SET = 0xe9    # wValue 0=Seer 1=PC


def drain(bus, t=0.3):
    """t초 동안 수신 프레임 리스트."""
    out, end = [], time.time() + t
    while time.time() < end:
        m = bus.recv(timeout=0.05)
        if m is not None:
            out.append(m)
    return out


def has_id(msgs, arb_id, data0=None, rtr=None):
    for m in msgs:
        if m.arbitration_id != arb_id:
            continue
        if rtr is not None and bool(m.is_remote_frame) != rtr:
            continue
        if data0 is not None and (len(m.data) == 0 or m.data[0] != data0):
            continue
        return True
    return False


def main():
    seer = can.Bus(channel=SEER_IF, interface="socketcan")
    motor = can.Bus(channel=MOTOR_IF, interface="socketcan")
    p = Panda()
    results = []

    def check(name, ok):
        results.append((name, ok))
        print(("  PASS " if ok else "  FAIL ") + name)

    try:
        # 판다 설정: 게이트 모드 + 250k + intercept
        p.set_safety_mode(SAFETY_SEER_GATE, 0)
        for b in (PANDA_BUS_SEER, PANDA_BUS_MOTOR):
            p.set_can_speed_kbps(b, BENCH_KBPS)
            p.set_can_enable(b, True)  # 트랜시버 enable (07-18 성공 스크립트 p2pcan.py 필수 호출)
        p._handle.controlWrite(Panda.REQUEST_OUT, REQ_RELAY_SET, 1, 0, b"")  # intercept ON
        time.sleep(0.3)

        # ---- T1: passthrough (auth=Seer) ----
        p._handle.controlWrite(Panda.REQUEST_OUT, REQ_AUTH_SET, 0, 0, b"")  # auth=Seer
        time.sleep(0.1); drain(motor, 0.1)
        seer.send(can.Message(arbitration_id=0x601, data=bytes([0x40, 0x64, 0x60, 0, 0, 0, 0, 0]), is_extended_id=False))
        check("T1 passthrough(auth=Seer): Seer→모터 도달", has_id(drain(motor), 0x601))

        # 이하 auth=PC (게이트 ON)
        p._handle.controlWrite(Panda.REQUEST_OUT, REQ_AUTH_SET, 1, 0, b"")  # auth=PC
        time.sleep(0.1)

        # ---- T2/T3: Seer SDO 쓰기 → 모터 미도달 + Seer 가짜 ack 수신 ----
        drain(motor, 0.1); drain(seer, 0.1)
        wr = can.Message(arbitration_id=0x601, data=bytes([0x2B, 0xFF, 0x60, 0, 0x8D, 0x09, 0, 0]), is_extended_id=False)
        seer.send(wr)
        mrx, srx = drain(motor, 0.3), drain(seer, 0.1)
        check("T2 Seer 쓰기 차단: 0x601 쓰기가 모터 미도달", not has_id(mrx, 0x601))
        check("T3 가짜 ack 합성: Seer 가 0x581 60.. 수신", has_id(srx, 0x581, data0=0x60))

        # ---- T4: Seer 읽기 통과 ----
        drain(motor, 0.1)
        seer.send(can.Message(arbitration_id=0x601, data=bytes([0x40, 0x64, 0x60, 0, 0, 0, 0, 0]), is_extended_id=False))
        check("T4 Seer 읽기 통과: 0x601 읽기가 모터 도달", has_id(drain(motor), 0x601, data0=0x40))

        # ---- T5: guard RTR 통과 (#1 RTR 패치 검증) ----
        drain(motor, 0.1)
        seer.send(can.Message(arbitration_id=0x701, is_remote_frame=True, dlc=0, is_extended_id=False))
        check("T5 guard RTR 통과(#1 RTR): 0x701 RTR 이 모터에 RTR 로 도달", has_id(drain(motor), 0x701, rtr=True))

        # ---- T6: PC 직접구동 (판다 CAN_TX → 모터) ----
        drain(motor, 0.1)
        p.can_send(0x601, bytes([0x23, 0xFF, 0x60, 0, 0x8D, 0x09, 0, 0]), PANDA_BUS_MOTOR)
        check("T6 PC 직접구동: 판다 CAN_TX 가 모터 도달", has_id(drain(motor), 0x601))

    finally:
        # 원복: passthrough + SILENT
        try:
            p._handle.controlWrite(Panda.REQUEST_OUT, REQ_RELAY_SET, 0, 0, b"")
            p._handle.controlWrite(Panda.REQUEST_OUT, REQ_AUTH_SET, 0, 0, b"")
            p.set_safety_mode(0, 0)
            p.close()
        except Exception:
            pass
        seer.shutdown(); motor.shutdown()

    npass = sum(1 for _, ok in results if ok)
    print(f"\n=== {npass}/{len(results)} PASS ===")
    sys.exit(0 if npass == len(results) else 1)


if __name__ == "__main__":
    main()
