#!/usr/bin/env python3
"""순수 CANopen SDO/RTR 코덱 — stdlib 전용 (python-can 불요).

CanFrame(프레임 정본형) + SDO 인코드/디코드. direct_driver.py 가 can.Message 를 직접 생성하던
로직을 **바이트 동일**하게 이관 — 트랜스포트 계층(can_transport)이 CanFrame↔백엔드 네이티브
(can.Message 등)를 변환한다. python-can 미설치 환경(tegra)에서도 import·단위테스트 가능.

바이트 동일 보증(리버스 엔지니어링 제1원칙): sdo_write/guard_rtr/sdo_encode_read 의 프레임
바이트는 원본 direct_driver.py:49-66 과 문자 그대로 동일한 표현식으로 생성한다. 회귀테스트
test_can_protocol.py 가 크기별·RTR·dlc 라운드트립을 고정한다.

프로토콜 근거: References/Tongyi-Motor-Controller/tongyi-canopen-protocol-reference.md,
  Handbook V7.0 §6.7 (p.156-157). 노드 1/2=구동(0x60FF)·3/4=조향(0x607A), enable 0x6040.
"""
import struct
import time
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CanFrame:
    """CAN 프레임 정본형 (백엔드 무관·불변). dlc=None 이면 유효 dlc = len(data)."""
    arb_id: int
    data: bytes = b""
    is_remote: bool = False
    is_extended: bool = False
    dlc: Optional[int] = None

    def effective_dlc(self) -> int:
        return self.dlc if self.dlc is not None else len(self.data)


# ── SDO/RTR 인코딩 (원본 direct_driver.py 와 바이트 동일) ───────────────────
def sdo_write(node: int, index: int, value: int, size: int = 4) -> CanFrame:
    """SDO expedited download (0x600+node). 원본 direct_driver.sdo_write 바이트 동일."""
    cmd = {1: 0x2F, 2: 0x2B, 4: 0x23}[size]
    data = bytes([cmd, index & 0xFF, (index >> 8) & 0xFF, 0]) + struct.pack("<i", value)[:size] + b"\x00" * (4 - size)
    return CanFrame(arb_id=0x600 + node, data=data[:8])


def guard_rtr(node: int) -> CanFrame:
    """Node Guarding RTR (0x700+node, dlc=0, 원본 direct_driver.guard_rtr 동일)."""
    return CanFrame(arb_id=0x700 + node, is_remote=True, dlc=0)


def sdo_encode_read(node: int, index: int, sub: int = 0) -> CanFrame:
    """SDO expedited upload 요청 (0x40). 원본 direct_driver.sdo_read 의 요청프레임 동일."""
    return CanFrame(arb_id=0x600 + node,
                    data=bytes([0x40, index & 0xFF, (index >> 8) & 0xFF, sub, 0, 0, 0, 0]))


def sdo_decode(frame: Optional[CanFrame], node: int, index: int, sub: int = 0):
    """SDO upload 응답 → (unsigned값, 바이트수) 또는 None(불일치/abort).

    원본 direct_driver.sdo_read 의 응답 파싱부(0x4F/4B/47/43 → 1/2/3/4바이트)와 동일 판정.
    """
    if frame is None or frame.arb_id != 0x580 + node or frame.is_remote or len(frame.data) < 4:
        return None
    d = frame.data
    if d[1] != (index & 0xFF) or d[2] != ((index >> 8) & 0xFF) or d[3] != sub:
        return None
    nbytes = {0x4F: 1, 0x4B: 2, 0x47: 3, 0x43: 4}.get(d[0])
    if nbytes is None:  # 0x80 abort 포함
        return None
    return (int.from_bytes(d[4:4 + nbytes], "little"), nbytes)


def to_signed(v: int, bits: int) -> int:
    return v - (1 << bits) if v >= (1 << (bits - 1)) else v


def sdo_read(transport, node: int, index: int, sub: int = 0, timeout: float = 0.2):
    """SDO expedited upload: 요청 송신 후 응답 폴 (bus 인자를 transport 로 대체).

    원본 direct_driver.sdo_read 와 동일 흐름 — transport.send(요청) 후 timeout 내 transport.recv()
    를 돌며 sdo_decode 로 판정. 불일치 프레임은 무시하고 계속, 매칭 응답(값/abort) 또는 시간초과 시 반환.
    """
    transport.send(sdo_encode_read(node, index, sub))
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        frame = transport.recv(timeout=timeout)
        if frame is None or frame.arb_id != 0x580 + node or frame.is_remote or len(frame.data) < 4:
            continue
        d = frame.data
        if d[1] != (index & 0xFF) or d[2] != ((index >> 8) & 0xFF) or d[3] != sub:
            continue
        nbytes = {0x4F: 1, 0x4B: 2, 0x47: 3, 0x43: 4}.get(d[0])
        if nbytes is None:  # abort — 원본과 동일하게 즉시 None
            return None
        return (int.from_bytes(d[4:4 + nbytes], "little"), nbytes)
    return None
