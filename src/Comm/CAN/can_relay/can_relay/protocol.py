#!/usr/bin/env python3
"""CANopen SDO 코덱 — 버스·판다 무의존 순수 함수.

이 모듈은 **바이트만 다룬다.** 어떤 전송로로 나가는지, 어떤 노드가 살아 있는지 모른다.
그래서 하드웨어 없이 전량 회귀 시험할 수 있다.
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
OBJ_POSITION_ACTUAL = 0x6064    # counts
OBJ_VELOCITY_ACTUAL = 0x606C    # 0.1 r/min
OBJ_CURRENT_ACTUAL = 0x6078     # 0.01 A
OBJ_TARGET_VELOCITY = 0x60FF    # 0.1 r/min
OBJ_TARGET_POSITION = 0x607A    # counts
OBJ_PROFILE_VELOCITY = 0x6081
OBJ_PROFILE_ACC = 0x6083
OBJ_PROFILE_DEC = 0x6084
OBJ_HOMING_SPEED = 0x6099       # sub 0 단일값. 0.1 r/min
OBJ_GUARD_TIME = 0x100C         # ms
OBJ_LIFE_FACTOR = 0x100D
OBJ_DIGITAL_INPUT = 0x6000      # sub **1** 이 비트맵(sub 0 은 엔트리 수)
#   bit0 Servo Enable · bit1 +Limit · bit2 Alarm · bit3 −Limit
OBJ_VENDOR_60FB = 0x60FB        # sub 4 = RstStart. 1 을 쓰면 호밍이 물리적으로 시작된다
OBJ_HOMING_METHOD = 0x6098      # INT8. 1 = −리밋 트리거 · 35 = 현재 위치를 홈으로

# CiA402 homing method 35 — 드라이브가 현재 모터 위치를 홈으로 기록하고 현재 각도를 0 으로
# 만든 뒤 리셋 모드를 되돌린다. 전원이 들어와 있을 때만 유효하므로 전원 사이클마다 재호밍이
# 필요하고, 호밍 후에는 0x6064 ≈ 0 이 직진이라 홈 상수가 필요 없다.
HOMING_METHOD_CURRENT_POS = 35
STATUSWORD_TARGET_REACHED = 1 << 10     # bit10 — 도착 판정 비트

# ── Controlword 값 ────────────────────────────────────────────────────────
CW_FAULT_RESET_ENABLE = 0x86    # 축 준비(Fault Reset 상승에지)
CW_STEER_SETPOINT = 0x3F        # 신규 setpoint 즉시 적용. 조향 0x607A 직후에 보낸다
CW_DISABLE = 0x05               # servo-off(freewheel). ⚠ 홀딩토크 상실

# ── SDO 커맨드 바이트 ──────────────────────────────────────────────────────
_WRITE_CMD = {1: 0x2F, 2: 0x2B, 4: 0x23}
_READ_REQ = 0x40
# 응답 커맨드 → 유효 데이터 바이트 수. 크기를 무시하고 항상 4바이트를 읽으면
# 0x4B(2B) 응답에서 상위 2바이트가 오염된다.
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
    """SDO expedited download 요청 프레임을 만든다.

    `size` 는 1·2·4 만 유효하며 그 외는 `KeyError` 다. 값이 `size` 에 안 들어가면
    조용히 자르지 않고 `ValueError` 를 낸다 — 조용한 절단은 지령을 바꿔 버린다.
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
    """SDO upload(읽기) 요청 프레임을 만든다."""
    data = bytes([_READ_REQ, index & 0xFF, index >> 8, sub, 0, 0, 0, 0])
    return Frame(SDO_RX_BASE + node, data, bus)


def parse_sdo_response(can_id: int, data: bytes) -> Optional[SdoResponse]:
    """SDO 응답을 디코드한다. 해당 없으면 `None`.

    read 응답은 **커맨드 바이트가 알려주는 크기만큼만** 부호 있는 정수로 언팩한다.
    abort 응답의 `value` 는 abort 코드다.
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
    """abort 코드를 사람이 읽는 사유로 옮긴다. 모르는 코드는 "사유 미상"."""
    return ABORT_REASON.get(code, "사유 미상")


# ── 시퀀스 ────────────────────────────────────────────────────────────────

def drive_init_frames(node: int, bus: int = 0) -> list[Frame]:
    """구동축 브링업 5프레임 — Fault Reset · 속도 0 · 노드가딩 · PV 모드.

    `0x100D`(life factor) 1 · `0x100C`(guard time) 500 ms 로 노드가딩을 세우고
    `0x6060` 을 3(Profile Velocity)으로 둔다.
    """
    return [
        sdo_write(node, OBJ_CONTROLWORD, CW_FAULT_RESET_ENABLE, 2, bus=bus),
        sdo_write(node, OBJ_TARGET_VELOCITY, 0, 4, bus=bus),
        sdo_write(node, OBJ_LIFE_FACTOR, 1, 1, bus=bus),
        sdo_write(node, OBJ_GUARD_TIME, 500, 2, bus=bus),
        sdo_write(node, OBJ_MODES, 3, 1, bus=bus),          # PV
    ]


def steer_init_frames(node: int, bus: int = 0) -> list[Frame]:
    """조향축 브링업 7프레임 — Fault Reset · 노드가딩 · PP 모드 · 프로파일 속도/가감속.

    호밍 트리거(`0x60FB:04`)는 포함하지 않는다. 호밍은 물리 스윙 100°+ 를 일으키므로
    별도 명시 요청으로만 수행한다(`homing_frames`).
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
    """조향 호밍 개시 3프레임(SDO 직접 경로). ⚠ **이 패키지의 실행 경로에서는 쓰지 않는다.**

    실행 경로의 호밍은 펌웨어 시퀀서(`link.homing_start`, 0xea) 또는 method 35 다.
    이 함수는 **바이트 대조 기준**으로 남아 있어, 펌웨어 시퀀서가 내는 프레임을 이것과
    대조할 수 있다. 새 코드에서 호출하지 말 것 — 이 경로로 시작한 호밍의 취소는 호스트
    프로세스가 살아 있을 때만 성립한다.

    `0x6098`(homing method)은 쓰지 않는다 — 드라이브 저장값(−리밋 트리거)을 덮어쓰면
    리셋 모드가 꺼져 호밍이 동작하지 않는다. 구동축은 기계적 원점이 없어 대상이 아니다.
    """
    return [
        sdo_write(node, OBJ_CONTROLWORD, CW_FAULT_RESET_ENABLE, 2, bus=bus),
        sdo_write(node, OBJ_HOMING_SPEED, speed, 4, bus=bus),
        sdo_write(node, OBJ_VENDOR_60FB, 1, 1, sub=4, bus=bus),   # 여기서 움직인다
    ]


def home35_move_frames(node: int, home_offset: int, profile_vel: int = 2500,
                       bus: int = 0) -> list[Frame]:
    """method 35 호밍 1단계 — 지정한 **절대 카운트로 이동**한다.

    `0x607A` = `home_offset` · `0x6081` = `profile_vel` · `0x6040` = 0x3F 순서다.

    ⚠ 이 프레임은 **바퀴를 움직인다.** `home_offset` 이 그 기체 값이 아니면 엉뚱한 곳으로
    간다 — 호출 전에 현재 위치가 예상 범위 안인지 확인할 것(`safety.home_search_allowed`).
    """
    return [
        sdo_write(node, OBJ_TARGET_POSITION, home_offset, 4, bus=bus),
        sdo_write(node, OBJ_PROFILE_VELOCITY, profile_vel, 4, bus=bus),
        sdo_write(node, OBJ_CONTROLWORD, CW_STEER_SETPOINT, 2, bus=bus),
    ]


def home35_set_frames(node: int, bus: int = 0) -> list[Frame]:
    """method 35 호밍 2단계 — `0x6098=35` 로 **현재 위치를 홈으로 선언**한다(각도가 0 이 된다).

    1단계 도착을 확인한 **뒤에만** 보내야 한다 — 안 그러면 엉뚱한 자세가 0° 가 된다.
    """
    return [sdo_write(node, OBJ_HOMING_METHOD, HOMING_METHOD_CURRENT_POS, 1, bus=bus)]


def home35_reached(statusword, position, home_offset: int, tol: int) -> bool:
    """method 35 1단계 도착 판정 — bit10 이 서고 잔차가 `tol` 미만인 **2조건**이다.

    상태워드나 위치를 모르면 도착으로 치지 않는다 — 모르는 것은 참이 아니다.
    """
    if statusword is None or position is None:
        return False
    if not (statusword & STATUSWORD_TARGET_REACHED):
        return False
    return abs(int(position) - int(home_offset)) < int(tol)


def steer_target_frames(node: int, counts: int, bus: int = 0) -> list[Frame]:
    """조향 절대위치 지령 2프레임(`0x607A` 목표 + `0x6040=0x3F` 적용).

    단계로 쪼개지 않고 최종 목표를 그대로 보낸다.
    """
    return [
        sdo_write(node, OBJ_TARGET_POSITION, counts, 4, bus=bus),
        sdo_write(node, OBJ_CONTROLWORD, CW_STEER_SETPOINT, 2, bus=bus),
    ]


def drive_velocity_frame(node: int, units: int, bus: int = 0) -> Frame:
    """구동 속도 지령 프레임(0.1 r/min raw). `units=0` 이 정지 지령이다."""
    return sdo_write(node, OBJ_TARGET_VELOCITY, units, 4, bus=bus)


# ── MotorCmd.mode — 상류 `trnav_msgs/MotorCmd.msg` 와 같은 값 ──────────────
#   조향축에 VELOCITY 가 오면 미설정 target_pos(=0)를 위치로 읽어 한계까지 스윙하므로
#   축 종류와 모드가 맞는지 지령 수리 시점에 검사한다.
MODE_DISABLED, MODE_VELOCITY, MODE_POSITION, MODE_TORQUE = 0, 1, 2, 3
MODE_NAME = {0: "DISABLED", 1: "VELOCITY", 2: "POSITION", 3: "TORQUE"}


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
