"""Tongyi 서보 CANopen SDO 프레임 인코드/디코드 (순수 함수 — 버스 라이브러리 무의존).

프로토콜 근거(1차 source·실측):
  [IxLII/IxLs/IxH Servo Driver Handbook V7.0, §6.7, page 156-157]
  ⚠ 판본 표기 주의(2026-07-27): 표지·파일명은 V7.0(2023-01)이나 본문 러닝헤더는 전 페이지
    "IxLII/IxLs/IxH Series Servo Driver Handbook V5.6" 다(…Handbook_V7.0.txt:8589, :9651, :9707).
    인용 시 양쪽 병기할 것. (§6.7 page 156-157 내용 자체는 이번 감사에서 재확인하지 않았다.)
  (References/Tongyi-Motor-Controller/manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf)
  + 실측 표: References/Tongyi-Motor-Controller/docs/tongyi-motor-protocol-tables.md
    ⚠ 경로 정정 (2026-07-28): 원문은 `References/Tongyi-Motor-Controller/tongyi-motor-protocol-tables.md`
      (docs/ 누락)라 존재하지 않는 경로였다. 실경로는 위와 같다
      (`find References/Tongyi-Motor-Controller -name 'tongyi-motor-protocol-tables.md'` → docs/ 하위 1건).
  ⚠ 좌표 재확인 (2026-07-28): §6.7 은 목차 ":102 6.7 SDO Communication …156" 및 본문 `:7738 "6.7 SDO Communication"`
    (페이지 푸터 156 = :7780, 157 = :7809) 로 **위치만** 대조했다. 본문 내용 자체의 대조는 여전히 미수행이다.
프레임(8B, little-endian): [cmd][idx_lo][idx_hi][sub][d0][d1][d2][d3]
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

# ── COB-ID 베이스 (Handbook §6.2 p137) ─────────────────────────────────────
SDO_RX_BASE = 0x600  # 마스터 → 드라이버 (요청)
SDO_TX_BASE = 0x580  # 드라이버 → 마스터 (응답)
GUARD_BASE = 0x700   # Node Guarding / Heartbeat

# ── 오브젝트 딕셔너리 (Handbook Appendix I p194-197, 정의 16종) ──────────────
# ⚠ 정정 (2026-07-27): 원문은 "실측 사용 8종" 이었으나 아래 OBJ_* 정의는 실제 16개다
#   (grep -c '^OBJ_' protocol.py = 16). 인벤토리 문서가 8종을 그대로 인용 중이었다.
OBJ_CONTROLWORD = 0x6040    # UINT16
OBJ_STATUSWORD = 0x6041     # UINT16
OBJ_ERROR_CODE = 0x603F     # UINT16
OBJ_MODES = 0x6060          # INT8: 1=PP, 3=PV
OBJ_POSITION_ACTUAL = 0x6064  # INT32
OBJ_CURRENT_ACTUAL = 0x6078   # INT16, 0.01 A
OBJ_TARGET_VELOCITY = 0x60FF  # INT32, 0.1 rpm(모터)
OBJ_TARGET_POSITION = 0x607A  # INT32, counts
OBJ_PROFILE_VELOCITY = 0x6081
OBJ_PROFILE_ACC = 0x6083
OBJ_PROFILE_DEC = 0x6084
OBJ_HOMING_SPEED = 0x6099
OBJ_GUARD_TIME = 0x100C
OBJ_LIFE_FACTOR = 0x100D
OBJ_DIGITAL_INPUT = 0x6000  # ARRAY. ⚠ 실제 DI 상태는 **sub 1**(sub 0 은 Number of Input = 항목 수)
#   sub 1 "Read Input 1h to 8h State" UINT8, default 0xBF —
#     Bit0 Servo Enable / Bit1 Positive Limit / Bit2 Alarm / Bit3 Negative Limit
#     [Handbook Appendix I page 197]
#     (References/.../IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.txt:9714-9718)
#   ✓ 실측: Seer 는 4노드 모두 sub=1 로 폴링(노드당 420회/180 s). 조향 node3·node4 만
#     0x01 → 0x09 (bit3 −Limit 셋) t=47.025 → 0x01 복귀 t=49.422; 구동 node1·2 는 0x01 고정.
#     (Log/homing_capture_220350.jsonl)
OBJ_VENDOR_60FB = 0x60FB    # RECORD. sub 0x04 = RstStart — "0-Reset off, 1-Reset on"
#   ⚠ 정정 (2026-07-27): 원문 주석은 "의미 ⚠"(미상) 이었으나 1차 source 에 명시돼 있다.
#     sub 4 에 1 을 쓰는 것은 **호밍 개시 = 조향축 물리 이동 명령**이다.
#     [Handbook V7.0 §6.9 Home, page 171] (…Handbook_V7.0.txt:8596-8597)
#     [같은 문서 Appendix I, page 196] (…:9659-9660)
#     [같은 문서 §4.6 Homing Operation, page 116-117] (…:5905, :5967)
#       ⚠ 페이지 정정 (2026-07-28): 원문은 두 좌표 모두 "page 116" 으로 묶었으나 대조 결과 갈린다 —
#         :5905 = 파라미터 표 행 `0x448F  SelfSofRst.uwRstStart  Start homing` → page 116
#           (페이지 푸터 115 = :5890, 116 = :5939)
#         :5967 = 인용문 "Start homing: Write SelfSofRst.uwRstStart = 1" (Case: Home 1 Operation Process, :5963)
#           → **page 117** (푸터 116 = :5939, 117 = :5976). 즉 인용 문장은 116 쪽이 아니다.
#   ✓ 실측 인과: Log/homing_capture_220350.jsonl — node3/4 sub4=1 write t=17.9252/17.9257
#     (180 s 중 노드당 1회) → 0x6041 bit15 1→0 → 0x6000.1 bit3 셋 t=47.025 → bit15 0→1 t≈49.0 (≈31.1 s)
#   ⚠ 같은 인덱스의 다른 sub 는 의미가 전혀 다르다 — sub1 Position_KP(위치루프 게인, RW),
#     sub2 Position_actual_Turn_value(RO), sub3 slAbsAngle(RO). sub 를 틀리면 게인이 덮어써진다.
#     [Handbook Appendix I page 196]
#   ⚠ 0x6098(Homing method)은 Seer 도 우리도 쓰지 않는다 — 본 캡처 180 s 전수에서 write·read 모두 0회.
#     호밍 방식은 드라이브 저장값(SelfSofRst.uwRstMode 0x448E, 공장 기본 1 = 음(−) 리밋 트리거)에 의존하며,
#     실기 판독(2026-07-27)에서도 전 노드 0x6098 = 1 이었다. [Handbook §4.6 page 116 표]
#     ✓ 좌표 대조 (2026-07-28): 이 인용은 실제로 맞다 —
#       `0x448E  SelfSofRst.uwRstMode  Home …  Default setting 1` (…Handbook_V7.0.txt:5901, page 116)
#       `Home 1: The home point is the negative limit triggering signal` (…:5927, page 116)

# Controlword 값 — Seer 실측 관례 (표준 06→07→0F 미사용, 벤더 허용)
CW_DRIVE_ENABLE = 0x86   # fault reset + enable
#   ⚠ 정정 (2026-07-27): 원문의 "(구동축, 기동 1회)" 는 원본 거동과 다르다. Seer 실측 —
#     구동축 node1·2: t=5.3432~17.8827 구간에서 8.5 Hz 로 **106회 반복 재-assert**(값 전부 0x86)
#     조향축 node3·4: 호밍 직전 t=17.910/17.911, 호밍 완료 후 t=49.084/49.003 — 국면 전환마다 1회씩 총 2회
#     (Log/homing_capture_220350.jsonl)
CW_STEER_SETPOINT = 0x3F  # 신규 setpoint + 즉시 적용 (조향축, setpoint 마다)
CW_DISABLE = 0x05        # servo enable 해제 (Handbook 0x6040 지령값 사전 p194)

_WRITE_CMD = {1: 0x2F, 2: 0x2B, 4: 0x23}
_READ_RESP_SIZE = {0x43: 4, 0x47: 3, 0x4B: 2, 0x4F: 1}


@dataclass(frozen=True)
class Frame:
    """버스 라이브러리 무의존 CAN 프레임 표현."""

    can_id: int
    data: bytes
    is_rtr: bool = False


@dataclass(frozen=True)
class SdoResponse:
    node: int
    kind: str        # "write_ack" | "read" | "abort"
    index: int
    sub: int
    value: int       # read: INT32 signed 해석값 / abort: 에러코드 / write_ack: 0
    raw: bytes


def sdo_write(node: int, index: int, value: int, size: int = 4, sub: int = 0) -> Frame:
    """SDO expedited 쓰기 요청 프레임 (size ∈ {1,2,4})."""
    cmd = _WRITE_CMD[size]
    payload = struct.pack("<I", value & 0xFFFFFFFF)[:size]  # signed/unsigned 모두 2의보수 그대로
    data = bytes([cmd, index & 0xFF, (index >> 8) & 0xFF, sub]) + payload + b"\x00" * (4 - size)
    return Frame(SDO_RX_BASE + node, data[:8])


def sdo_read(node: int, index: int, sub: int = 0) -> Frame:
    """SDO 읽기 요청 프레임 (cmd 0x40)."""
    return Frame(SDO_RX_BASE + node, bytes([0x40, index & 0xFF, (index >> 8) & 0xFF, sub, 0, 0, 0, 0]))


def guard_rtr(node: int) -> Frame:
    """Node Guarding RTR — 미송신 시 GuardTime(500ms)×LifeFactor(1) 초과로 드라이브 HALT (실측)."""
    return Frame(GUARD_BASE + node, b"", is_rtr=True)


def parse_sdo_response(can_id: int, data: bytes) -> SdoResponse | None:
    """0x580+N 응답 파싱. SDO 응답이 아니면 None.

    read 값은 INT32 signed 로 해석해 반환(0x6064·0x60FF 등 주 사용처 기준).
    UINT16 오브젝트(0x6041 등)는 호출측에서 `value & 0xFFFF` 로 재해석한다.
    """
    node = can_id - SDO_TX_BASE
    if not (1 <= node <= 0x7F) or len(data) < 8:
        return None
    cmd = data[0]
    index = data[1] | (data[2] << 8)
    sub = data[3]
    if cmd == 0x60:
        return SdoResponse(node, "write_ack", index, sub, 0, bytes(data))
    if cmd in _READ_RESP_SIZE:
        value = struct.unpack("<i", bytes(data[4:8]))[0]
        return SdoResponse(node, "read", index, sub, value, bytes(data))
    if cmd == 0x80:
        abort = struct.unpack("<I", bytes(data[4:8]))[0]
        return SdoResponse(node, "abort", index, sub, abort, bytes(data))
    return None
