#!/usr/bin/env python3
"""can_protocol 회귀 — SDO/RTR 인코딩이 원본 direct_driver(can.Message) 와 **바이트 동일**한지 고정.

stdlib 전용 (python-can 불요, tegra 실행 가능). ADR 2026-07-28 리버스-엔지니어링 제1원칙 게이트.
골든 벡터(수기 검증) + 원본 표현식 등가(fuzz) 이중 확인.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from can_protocol import (  # noqa: E402
    CanFrame, guard_rtr, sdo_decode, sdo_encode_read, sdo_read, sdo_write, to_signed,
)


def _ref_sdo_write(node, index, value, size=4):
    """원본 direct_driver.sdo_write 의 인코딩 표현식(대조 기준선) — can 미의존 바이트만."""
    cmd = {1: 0x2F, 2: 0x2B, 4: 0x23}[size]
    data = bytes([cmd, index & 0xFF, (index >> 8) & 0xFF, 0]) + struct.pack("<i", value)[:size] + b"\x00" * (4 - size)
    return 0x600 + node, data[:8]


GOLDEN = [  # (frame, expected_arb, expected_hex, expected_remote, expected_dlc)
    (sdo_write(1, 0x6040, 0x86, size=2), 0x601, "2b 40 60 00 86 00 00 00", False, 8),
    (sdo_write(1, 0x60FF, 0, size=4),    0x601, "23 ff 60 00 00 00 00 00", False, 8),
    (sdo_write(2, 0x60FF, -1000, size=4), 0x602, "23 ff 60 00 18 fc ff ff", False, 8),
    (sdo_write(3, 0x607A, 5160960, size=4), 0x603, "23 7a 60 00 00 c0 4e 00", False, 8),
    (sdo_encode_read(3, 0x6064, 0), 0x603, "40 64 60 00 00 00 00 00", False, 8),
]


def test_golden_vectors():
    for fr, arb, hexstr, remote, dlc in GOLDEN:
        assert fr.arb_id == arb, (hex(fr.arb_id), hex(arb))
        assert fr.data.hex(" ") == hexstr, (fr.data.hex(" "), hexstr)
        assert fr.is_remote == remote
        assert fr.effective_dlc() == dlc
        assert fr.is_extended is False


def test_guard_rtr():
    fr = guard_rtr(3)
    assert fr.arb_id == 0x703 and fr.is_remote is True and fr.effective_dlc() == 0 and fr.data == b""


def test_sdo_write_matches_reference_expression():
    # 원본 표현식과 바이트 동일 — 크기·값·인덱스·노드 스윕
    for size in (1, 2, 4):
        for value in (0, 1, -1, 0x86, -1000, 5160960, (1 << (8 * size)) - 1 if size < 4 else 2147483647):
            for node in (1, 2, 3, 4):
                for index in (0x6040, 0x607A, 0x60FF, 0x6064):
                    fr = sdo_write(node, index, value, size=size)
                    ref_arb, ref_data = _ref_sdo_write(node, index, value, size=size)
                    assert fr.arb_id == ref_arb and fr.data == ref_data, (size, value, node, hex(index))


def test_sdo_decode_roundtrip():
    # 응답 프레임(0x43=4B) → decode → (unsigned, 4)
    for node, index, val in [(3, 0x6064, 7871815), (4, 0x6064, 7840086), (1, 0x606C, 0)]:
        data = bytes([0x43, index & 0xFF, (index >> 8) & 0xFF, 0]) + (val & 0xFFFFFFFF).to_bytes(4, "little")
        r = sdo_decode(CanFrame(arb_id=0x580 + node, data=data), node, index)
        assert r == (val & 0xFFFFFFFF, 4), r
    # 크기별 코드
    for code, nb in [(0x4F, 1), (0x4B, 2), (0x47, 3), (0x43, 4)]:
        data = bytes([code, 0x64, 0x60, 0]) + b"\x01\x02\x03\x04"
        r = sdo_decode(CanFrame(arb_id=0x583, data=data), 3, 0x6064)
        assert r is not None and r[1] == nb


def test_sdo_decode_mismatch_and_abort():
    good = bytes([0x43, 0x64, 0x60, 0, 1, 0, 0, 0])
    assert sdo_decode(None, 3, 0x6064) is None
    assert sdo_decode(CanFrame(0x999, good), 3, 0x6064) is None              # 잘못된 arb
    assert sdo_decode(CanFrame(0x583, good), 3, 0x6099) is None              # 잘못된 index
    assert sdo_decode(CanFrame(0x583, bytes([0x80, 0x64, 0x60, 0, 0, 0, 0, 0])), 3, 0x6064) is None  # abort
    assert sdo_decode(CanFrame(0x583, good, is_remote=True), 3, 0x6064) is None  # RTR


def test_to_signed():
    assert to_signed(0xFFFFFFFF, 32) == -1
    assert to_signed(0x7FFFFFFF, 32) == 2147483647
    assert to_signed(0xFFFF, 16) == -1
    assert to_signed(0x7FFF, 16) == 32767
    assert to_signed(5160960, 32) == 5160960


def test_sdo_read_via_mock():
    # transport 인자 경로 (can_transport.MockTransport 사용)
    from can_transport import MockTransport
    t = MockTransport().open(); t.arm()
    t.program_sdo_read(3, 0x6064, 7871815)
    assert sdo_read(t, 3, 0x6064) == (7871815, 4)
    assert sdo_read(t, 3, 0x6064, timeout=0.05) is None  # 큐 소진 → 시간초과 None


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    ok = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS {fn.__name__}"); ok += 1
        except AssertionError as e:
            print(f"  FAIL {fn.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"can_protocol: {ok}/{len(fns)} PASS")
    return ok == len(fns)


if __name__ == "__main__":
    sys.exit(0 if _run() else 1)
