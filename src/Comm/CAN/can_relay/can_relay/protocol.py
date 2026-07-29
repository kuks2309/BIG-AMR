#!/usr/bin/env python3
"""CANopen SDO 코덱 — 버스·판다 무의존 순수 함수.

이 모듈은 **바이트만 다룬다.** 어떤 전송로로 나가는지, 어떤 노드가 살아 있는지
모른다. 그래서 하드웨어 없이 전량 회귀 시험할 수 있다.

객체 인덱스와 값의 근거는 실측 캡처다 — `Log/homing_capture_220350.jsonl`
(Seer 마스터 180 s, 253,510 프레임). 아래 주석의 `t=` 는 그 캡처의 초 단위 시각이다.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional

# ── COB-ID 베이스 ──────────────────────────────────────────────────────────
SDO_RX_BASE = 0x600     # 마스터 → 슬레이브 요청
SDO_TX_BASE = 0x580     # 슬레이브 → 마스터 응답
GUARD_BASE = 0x700      # Node Guarding

# ── 객체 사전 ──────────────────────────────────────────────────────────────
OBJ_CONTROLWORD = 0x6040
OBJ_STATUSWORD = 0x6041
OBJ_ERROR_CODE = 0x603F
OBJ_MODES = 0x6060              # 3=PV(구동) · 1=PP(조향)
OBJ_POSITION_ACTUAL = 0x6064
OBJ_VELOCITY_ACTUAL = 0x606C    # 0.1 r/min
OBJ_CURRENT_ACTUAL = 0x6078     # 0.01 A
OBJ_TARGET_VELOCITY = 0x60FF    # 0.1 r/min
OBJ_TARGET_POSITION = 0x607A    # counts
OBJ_PROFILE_VELOCITY = 0x6081
OBJ_PROFILE_ACC = 0x6083
OBJ_PROFILE_DEC = 0x6084
OBJ_HOMING_SPEED = 0x6099       # sub 0 단일값. 캡처 t=17.918 에서 2500(=250 r/min)
OBJ_GUARD_TIME = 0x100C         # ms
OBJ_LIFE_FACTOR = 0x100D
OBJ_DIGITAL_INPUT = 0x6000      # ★ sub **1** 이 비트맵(sub 0 은 엔트리 수).
#   bit0 Servo Enable · bit1 +Limit · bit2 Alarm · bit3 −Limit
#   구 판다 펌웨어가 sub 0 을 폴해 리밋 판정이 죽어 있던 이력이 있다
#   (`Log/homing_run_1785160148.jsonl` 에서 응답 0x02 = 엔트리 수). sub 1 을 쓸 것.
OBJ_VENDOR_60FB = 0x60FB        # sub 4 = RstStart. 1 을 쓰면 호밍이 **물리적으로 시작**된다.

# ── Controlword 값 ────────────────────────────────────────────────────────
CW_FAULT_RESET_ENABLE = 0x86    # 축 준비(Fault Reset 상승에지). 캡처 t=17.883·17.910
CW_STEER_SETPOINT = 0x3F        # 신규 setpoint 즉시 적용. 조향 0x607A 직후에 보낸다
CW_DISABLE = 0x05               # servo-off(freewheel). ⚠ 홀딩토크 상실

# ── SDO 커맨드 바이트 ──────────────────────────────────────────────────────
_WRITE_CMD = {1: 0x2F, 2: 0x2B, 4: 0x23}
_READ_REQ = 0x40
# 응답 커맨드 → 유효 데이터 바이트 수. **이 표를 실제로 써야 한다** —
# 크기를 무시하고 항상 4바이트를 읽으면 0x4B(2B) 응답에서 상위 2바이트가 오염된다.
_READ_RESP_SIZE = {0x43: 4, 0x47: 3, 0x4B: 2, 0x4F: 1}
_WRITE_ACK = 0x60
_ABORT = 0x80

# SDO abort 코드 — 드라이브가 쓰기를 거부한 사유(진단 전용).
ABORT_REASON = {
    0x05040001: "명령 지정자 불량",
    0x06010002: "읽기 전용 객체에 쓰기",
    0x06020000: "객체 없음",
    0x06090011: "서브인덱스 없음",
    0x06090030: "값 범위 초과",
    0x06070010: "데이터 길이 불일치",
    0x08000020: "저장 불가",
    0x08000022: "현재 장치 상태에서 전송 불가",
}


@dataclass(frozen=True)
class Frame:
    """전송로 무의존 CAN 프레임 값객체."""

    can_id: int
    data: bytes
    bus: int = 0


@dataclass(frozen=True)
class SdoResponse:
    """SDO 응답 디코드 결과. `kind` ∈ {"write_ack", "read", "abort"}."""

    node: int
    kind: str
    index: int
    sub: int
    value: Optional[int]
    size: Optional[int]


def sdo_write(node: int, index: int, value: int, size: int = 4, sub: int = 0,
              bus: int = 0) -> Frame:
    """SDO expedited download 요청.

    `size` 는 1·2·4 만 유효하며 그 외는 KeyError 다. 값이 size 에 안 들어가면
    조용히 자르지 않고 ValueError 를 낸다 — 조용한 절단은 지령을 바꿔 버린다.
    """
    cmd = _WRITE_CMD[size]
    masked = value & 0xFFFFFFFF
    if size < 4 and masked >> (size * 8):
        raise ValueError(
            f"value 0x{masked:X} 가 size={size}B 에 들어가지 않는다 "
            f"(node={node} index=0x{index:04X}:{sub:02X})")
    payload = struct.pack("<I", masked)[:size]
    data = bytes([cmd, index & 0xFF, index >> 8, sub]) + payload
    data += b"\x00" * (8 - len(data))
    return Frame(SDO_RX_BASE + node, data, bus)


def sdo_read(node: int, index: int, sub: int = 0, bus: int = 0) -> Frame:
    """SDO upload 요청."""
    data = bytes([_READ_REQ, index & 0xFF, index >> 8, sub, 0, 0, 0, 0])
    return Frame(SDO_RX_BASE + node, data, bus)


def parse_sdo_response(can_id: int, data: bytes) -> Optional[SdoResponse]:
    """SDO 응답 디코드. 해당 없으면 None.

    read 응답은 **커맨드 바이트가 알려주는 크기만큼만** 언팩한다.
    """
    if not (SDO_TX_BASE < can_id <= SDO_TX_BASE + 0x7F):
        return None
    if len(data) < 8:
        return None
    node = can_id - SDO_TX_BASE
    cmd = data[0]
    index = data[1] | (data[2] << 8)
    sub = data[3]
    if cmd == _WRITE_ACK:
        return SdoResponse(node, "write_ack", index, sub, None, None)
    if cmd in _READ_RESP_SIZE:
        size = _READ_RESP_SIZE[cmd]
        value = int.from_bytes(data[4:4 + size], "little", signed=True)
        return SdoResponse(node, "read", index, sub, value, size)
    if cmd == _ABORT:
        code = int.from_bytes(data[4:8], "little")
        return SdoResponse(node, "abort", index, sub, code, 4)
    return None


def abort_text(code: int) -> str:
    return ABORT_REASON.get(code, "사유 미상")


# ── 검증된 시퀀스 (실측 캡처 순서 그대로) ──────────────────────────────────

def drive_init_frames(node: int, bus: int = 0) -> list[Frame]:
    """구동축 브링업. 캡처 t=17.883~17.904 의 Seer 순서와 객체·값이 일치한다.

    ⚠ `Tools/amr_test_gui/gui.py` 에는 이 시퀀스가 **없다** — 그 코드는 Seer 가
    이미 브링업해 둔 축에 올라타 0x60FF 만 덮어쓴다. 즉 여기는 실기 검증 이력이
    없는 구간이므로 잭업 상태에서 먼저 확인할 것(debt-017).

    부정형 단정의 근거 명령(2026-07-29 실행, 0건):
        grep -nE '0x6060|0x100C|0x100D|0x6081|0x6083|0x6084' Tools/amr_test_gui/gui.py
    범위 주의 — gui.py 가 controlword 자체를 안 쓰는 것은 아니다. `gui.py:942` 가
    `0x6040=0x86` 을 쓰지만 그것은 `for n in (3, 4)` 안, 즉 **조향축 호밍 전용**이다.
    구동축 루프(`gui.py:839` `for n in (1, 2)`)는 `0x60FF` 만 쓴다.
    """
    return [
        sdo_write(node, OBJ_CONTROLWORD, CW_FAULT_RESET_ENABLE, 2, bus=bus),
        sdo_write(node, OBJ_TARGET_VELOCITY, 0, 4, bus=bus),
        sdo_write(node, OBJ_LIFE_FACTOR, 1, 1, bus=bus),
        sdo_write(node, OBJ_GUARD_TIME, 500, 2, bus=bus),
        sdo_write(node, OBJ_MODES, 3, 1, bus=bus),          # PV
    ]


def steer_init_frames(node: int, bus: int = 0) -> list[Frame]:
    """조향축 브링업. 캡처 t=49.012~49.133 의 Seer 순서(호밍 **완료 후** 국면 B).

    ⚠ 호밍 트리거(0x60FB:04)는 포함하지 않는다. 호밍은 물리 스윙 100°+ 를
    일으키므로 별도 명시 요청으로만 수행한다(`homing_frames`).
    """
    return [
        sdo_write(node, OBJ_CONTROLWORD, CW_FAULT_RESET_ENABLE, 2, bus=bus),
        sdo_write(node, OBJ_LIFE_FACTOR, 1, 1, bus=bus),
        sdo_write(node, OBJ_GUARD_TIME, 500, 2, bus=bus),
        sdo_write(node, OBJ_MODES, 1, 1, bus=bus),          # PP
        sdo_write(node, OBJ_PROFILE_VELOCITY, 30000, 4, bus=bus),
        sdo_write(node, OBJ_PROFILE_ACC, 250, 4, bus=bus),
        sdo_write(node, OBJ_PROFILE_DEC, 250, 4, bus=bus),
    ]


def homing_frames(node: int, speed: int = 2500, bus: int = 0) -> list[Frame]:
    """조향 호밍 개시. `gui.py:942-944` 의 실기 검증 시퀀스와 바이트 동일.

    `0x6098`(homing method)은 **쓰지 않는다** — 드라이브 저장값(전 노드 Home 1,
    −리밋 트리거)을 덮어쓰면 리셋 모드가 꺼져 호밍이 동작하지 않는다.
    구동축(1·2)은 기계적 원점이 없어 호밍 대상이 아니다.
    """
    return [
        sdo_write(node, OBJ_CONTROLWORD, CW_FAULT_RESET_ENABLE, 2, bus=bus),
        sdo_write(node, OBJ_HOMING_SPEED, speed, 4, bus=bus),
        sdo_write(node, OBJ_VENDOR_60FB, 1, 1, sub=4, bus=bus),   # 여기서 움직인다
    ]


def steer_target_frames(node: int, counts: int, bus: int = 0) -> list[Frame]:
    """조향 절대위치 지령 2프레임. 단계로 쪼개지 않고 최종 목표를 그대로 보낸다.

    (실측: Seer 도 node3 에 0x607A 를 6,464 회 보내지만 서로 다른 값은 4 개뿐이다.)
    """
    return [
        sdo_write(node, OBJ_TARGET_POSITION, counts, 4, bus=bus),
        sdo_write(node, OBJ_CONTROLWORD, CW_STEER_SETPOINT, 2, bus=bus),
    ]


def drive_velocity_frame(node: int, units: int, bus: int = 0) -> Frame:
    """구동 속도 지령(0.1 r/min raw). units=0 이 정지 지령이다."""
    return sdo_write(node, OBJ_TARGET_VELOCITY, units, 4, bus=bus)


POLL_OBJECTS = (
    (OBJ_POSITION_ACTUAL, 0),
    (OBJ_VELOCITY_ACTUAL, 0),
    (OBJ_CURRENT_ACTUAL, 0),
    (OBJ_STATUSWORD, 0),
    (OBJ_DIGITAL_INPUT, 1),     # sub 1 — 리밋 스위치 비트맵
)


def poll_frames(nodes, bus: int = 0) -> list[Frame]:
    """피드백 폴링 요청 묶음. 읽기만 하며 지령은 하나도 들어 있지 않다."""
    return [sdo_read(n, idx, sub, bus) for n in nodes for idx, sub in POLL_OBJECTS]
