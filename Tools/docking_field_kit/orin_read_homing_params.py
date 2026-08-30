#!/usr/bin/env python3
"""조향 호밍 파라미터 + 정지 수단 설정 판독 — 드라이브 상주 설정을 읽는다.

⚠ 확정 (2026-07-28): 정지 수단 관련 판독을 수행했고 결과는 아래와 같다.
  전문 기록은 docs/can_relay/drive-stop-config-2026-07-28.md.
    · 4노드 전부 0x100C = 500 ms, 0x100D = 1 → **node guarding 무장, 타임아웃 500 ms**
      → 마스터가 0x700+node RTR 폴을 500 ms 멈추면 드라이브가 토크를 유지한 채 자동 HALT
        [Handbook V7.0 §6.4.3, page 142 — "without powering off the motor"]
      → 이 하드웨어에서 **원문으로 보증된 유일한 토크 유지 정지 수단**이다.
    · 4노드 전부 0x605A = 0, 0x605D = 0, 0x6085 = 0
      → Handbook 이 이 값들의 의미를 기재하지 않으므로 **0x6040 = 0x010F(Halt) 의 거동은 미정의**.
        능동 정지 프레임을 fail-safe 수단으로 채택할 근거가 현재 없다.

목적: 우리 추론("드라이브 저장 method = 1, 음의 리밋 트리거")을 실기 값으로 확인한다.
  ⚠ 정정/확정 (2026-07-27): 이 확인은 **이미 수행됐고 결과는 전 노드 0x6098 = 1** 이다
  — 방식은 Home 1(음(−)의 리밋 트리거), 조향축에 리밋 스위치가 실재한다.
  (Handbook 기본 RstMode 도 1 [같은 문서, §4.6, page 116].) 재실행은 재확인 목적일 때만.
  [IxLII/IxLs/IxH Servo Driver Handbook V7.0, §6.9, page 171-172]
    0x6098 Homing method  : 0=off, 1~37 (1=−리밋, 2=+리밋, 35=현위치, 36/37=기계 하드스톱)
    0x6099 Homing speeds  : 0.1 r/min
    0x607C Homing offset  : 65536 = 1회전
    0x609A Homing accel   : ms
    0x6000 Digital Input  : **배열 오브젝트 — 실입력은 sub 1** (sub 0 은 항목수=2, UINT8).
                            bit0 Servo Enable, bit1 +Limit, bit2 Alarm, bit3 −Limit
                            [같은 문서, Appendix I(Object Dictionary), page 197 —
                             "Bit0: Servo Enable State / Bit1: Positive Limit State /
                              Bit2: Alarm State / Bit3: Negative Limit State"]
                            ※ 1차 source 기재 사항이다(파생문서 추정 아님).
    0x6041 Statusword     : bit15 = 0 호밍 진행중 / 1 완료

**모터를 움직이는 프레임은 한 개도 보내지 않는다** — SDO 읽기(0x40)만 송신한다.
0x6098 에 대한 **쓰기는 어떤 경로로도 하지 않는다**(드라이브 상주 설정이라 되돌리기 어렵고,
Handbook §4.6 page 122 상 35 를 쓰면 method 가 0 으로 리셋되어 Seer 호밍이 죽는다).

⚠ 제어권에 관하여: Seer 가 폴링 중인 노드에 SDO 읽기를 끼워넣으면 in-flight 트랜잭션이 깨져
  Seer 가 노드 상실(52111)로 판단할 수 있다(docs/can_relay/field-record-orin-nx-2026-07-25.md:123).
  그래서 기본 동작은 intercept(제어권 획득) 상태에서 읽는다 — 이때 판다가 Seer 에게 캐시로
  대신 답하므로 Seer 는 노드를 잃지 않는다.
  ⚠ **release(제어권 반환) 시 재호밍이 일어날 수 있다** — 접지 상태면 조향축이 약 137° 스윙한다.
  --no-take 를 주면 제어권을 잡지 않고 읽지만, 위 SDO 충돌 위험을 감수하는 것이다.

사용:
  python3 orin_read_homing_params.py              # intercept 잡고 읽고 반환
  python3 orin_read_homing_params.py --no-take    # 제어권 미획득(충돌 위험 감수)
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from panda import Panda  # noqa: E402

SEER_BUS, MOTOR_BUS = 0, 2
SEER_GATE = 30
CAN_KBPS = 250
HEARTBEAT_S = 0.4

NODES = (1, 2, 3, 4)
STEER_NODES = (3, 4)
# (index, sub, 이름, 해석함수 키)
OBJECTS = [
    (0x6098, 0, "Homing method", "method"),
    (0x6099, 0, "Homing speed (0.1 r/min)", "int"),
    (0x607C, 0, "Homing offset (65536=1rev)", "int"),
    (0x609A, 0, "Homing accel (ms)", "int"),
    (0x6060, 0, "Modes of operation", "modes"),
    (0x6041, 0, "Statusword", "status"),
    (0x6000, 1, "Digital Input (sub1=실입력)", "din"),   # sub0 은 항목수(=2), 실값은 sub1
    # --- 2026-07-28 추가: fail-safe 재설계용 (전부 읽기 전용, 모션 지령 아님) ---
    #   0x100C/0x100D  Node Protection — 마스터가 0x700+node RTR 폴을 멈추면
    #                  monitoring_time × life_time_factor 후 드라이브가 HALT,
    #                  "without powering off the motor"
    #                  [Handbook V7.0 §6.4.3, page 142]
    #                  둘 중 하나라도 0 이면 이 보호는 동작하지 않는다(같은 절).
    (0x100C, 0, "Guard Time (ms)", "int"),
    (0x100D, 0, "Life Time Factor", "int"),
    #   0x605A/0x605D  정지 옵션코드 — Handbook 전문에 **이름만** 있고 값 의미·기본값 미기재
    #                  (0x605A: page 143 표 / 0x605D: 명칭이 Halt_option_code ↔
    #                   Stop_option_Code 로 문서 내 불일치). 그래서 실기 판독이 필요하다.
    (0x605A, 0, "Quick stop option code", "int"),
    (0x605D, 0, "Halt option code", "int"),
    (0x6085, 0, "Quick stop deceleration", "int"),
]
RD_RESP = {0x43: 4, 0x47: 3, 0x4B: 2, 0x4F: 1}

METHOD_NAME = {
    0: "호밍 꺼짐",
    1: "Home 1 — 음(−)의 리밋 트리거 신호",
    2: "Home 2 — 양(+)의 리밋 트리거 신호",
    35: "Home 35 — 현재 위치를 원점으로",
    36: "Home 36 — 음의 기계 하드스톱",
    37: "Home 37 — 양의 기계 하드스톱",
}
MODES_NAME = {1: "PP (위치)", 3: "PV (속도)", 6: "Homing mode"}


def s32(b: bytes) -> int:
    v = int.from_bytes(b[:4], "little")
    return v - (1 << 32) if v & 0x80000000 else v


def describe(kind: str, val: int) -> str:
    if kind == "method":
        return METHOD_NAME.get(val, f"Home {val}" if 1 <= val <= 37 else "정의 밖")
    if kind == "modes":
        return MODES_NAME.get(val, "?")
    if kind == "status":
        sw = val & 0xFFFF
        return (f"0x{sw:04x}  bit15(호밍)={(sw >> 15) & 1} bit10(도달)={(sw >> 10) & 1} "
                f"상태니블={sw & 0xF:04b}")
    if kind == "din":
        v = val & 0xFFFFFFFF
        return (f"0x{v:08x}  ServoEnable={v & 1} +Limit={(v >> 1) & 1} "
                f"Alarm={(v >> 2) & 1} −Limit={(v >> 3) & 1}")
    return str(val)


def read_object(p, node: int, index: int, sub: int, timeout: float = 0.5):
    """SDO 읽기 1건. (value, raw) 또는 ('ABORT', code) 또는 None(무응답)."""
    req = bytes([0x40, index & 0xFF, (index >> 8) & 0xFF, sub, 0, 0, 0, 0])
    p.can_send(0x600 + node, req, MOTOR_BUS)
    deadline = time.time() + timeout
    while time.time() < deadline:
        for addr, _, dat, bus in p.can_recv():
            if bus != MOTOR_BUS or addr != (0x580 + node) or len(dat) < 8:
                continue
            d = bytes(dat)
            if (d[1] | (d[2] << 8)) != index or d[3] != sub:
                continue
            if d[0] in RD_RESP:
                return ("ok", s32(d[4:8]), d)
            if d[0] == 0x80:
                return ("abort", int.from_bytes(d[4:8], "little"), d)
        time.sleep(0.002)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-take", action="store_true",
                    help="제어권을 잡지 않고 읽는다 (Seer SDO 충돌 위험 감수)")
    ap.add_argument("--settle", type=float, default=1.0, help="take 후 안정화 대기 초")
    args = ap.parse_args()

    p = Panda()
    print(f"판다 연결: fw={p.get_version()}", flush=True)

    # heartbeat 임계 판정 — check_started() 가 참이면 5 s, 거짓이면 2 s 가 적용된다
    # (board/main.c 의 HEARTBEAT_IGNITION_CNT_ON/OFF). check_started() 는
    # current_board->check_ignition() || ignition_can 이므로 아래 두 값으로 확정된다.
    h = p.health()
    print(f"health: ignition_line={h.get('ignition_line')} ignition_can={h.get('ignition_can')} "
          f"safety_mode={h.get('safety_mode')} heartbeat_lost={h.get('heartbeat_lost')}",
          flush=True)

    p.set_safety_mode(0, 0)
    for b in (SEER_BUS, MOTOR_BUS):
        p.set_can_speed_kbps(b, CAN_KBPS)
        p.set_can_enable(b, True)
    time.sleep(0.2)
    p.can_recv()

    controlling = False
    last_hb = 0.0
    try:
        if not args.no_take:
            print(">>> 제어권 획득 (safety=30, auth=PC, intercept) — 모터 지령은 보내지 않음",
                  flush=True)
            p.set_safety_mode(SEER_GATE, 0)
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 1, 0, b"")
            p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 1, 0, b"")
            controlling = True
            last_hb = time.time()
            time.sleep(args.settle)

        print("\n" + "=" * 78, flush=True)
        for node in NODES:
            role = "조향" if node in STEER_NODES else "구동"
            print(f"\n--- node{node} ({role}) ---", flush=True)
            for index, sub, name, kind in OBJECTS:
                if controlling and (time.time() - last_hb) > HEARTBEAT_S:
                    p._handle.controlWrite(Panda.REQUEST_OUT, 0xf3, 0, 0, b"")
                    last_hb = time.time()
                r = read_object(p, node, index, sub)
                if r is None:
                    print(f"  0x{index:04X}.{sub}  {name:<30s} : 무응답", flush=True)
                elif r[0] == "abort":
                    print(f"  0x{index:04X}.{sub}  {name:<30s} : ABORT 0x{r[1]:08X} "
                          f"(이 오브젝트 미지원 가능)", flush=True)
                else:
                    print(f"  0x{index:04X}.{sub}  {name:<30s} : {r[1]:<12d} {describe(kind, r[1])}",
                          flush=True)
        print("\n" + "=" * 78, flush=True)
        print("판정: 조향 노드(3·4)의 0x6098 이 1 이면 '음의 리밋 트리거'가 드라이브 저장값이며,",
              flush=True)
        print("      2026-07-27 캡처에서 관측된 −Limit(0x6000 bit3) 트리거와 정합한다.", flush=True)
    finally:
        if controlling:
            try:
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe9, 0, 0, b"")
                p._handle.controlWrite(Panda.REQUEST_OUT, 0xe8, 0, 0, b"")
                p.set_safety_mode(0, 0)
                print("\n[finally] 제어권 반환 + passthrough 복귀", flush=True)
                print("⚠ Seer 가 재호밍을 개시할 수 있습니다 — 조향축 스윙 주의", flush=True)
            except Exception as exc:
                print(f"\n[finally] ⚠ release 실패: {exc} — heartbeat 소실로 fail-safe 복귀 예정",
                      flush=True)
        try:
            p.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
