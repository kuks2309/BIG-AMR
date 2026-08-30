"""protocol.py 단위 검증 — 기동 캡처 실측 바이트와 대조.

실측 벡터 출처: experiences/can-decode/captures/tongyi_250k_startup_20260708_103448_can0.asc
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from motor_control import protocol as P  # noqa: E402


def test_sdo_write_matches_captured_enable():
    # 실측: "601 ... 2B 40 60 00 86 00 00 00" (t=45.695)
    f = P.sdo_write(1, P.OBJ_CONTROLWORD, P.CW_DRIVE_ENABLE, size=2)
    assert f.can_id == 0x601
    assert f.data == bytes.fromhex("2B40600086000000")


def test_sdo_write_matches_captured_velocity_zero():
    # 실측: "601 ... 23 FF 60 00 00 00 00 00"
    f = P.sdo_write(1, P.OBJ_TARGET_VELOCITY, 0, size=4)
    assert f.data == bytes.fromhex("23FF600000000000")


def test_sdo_write_matches_captured_steer_home():
    # 실측: "603 ... 23 7A 60 00 47 1D 78 00" (7,871,815 = 0x781D47)
    f = P.sdo_write(3, P.OBJ_TARGET_POSITION, 7871815, size=4)
    assert f.can_id == 0x603
    assert f.data == bytes.fromhex("237A6000471D7800")


def test_sdo_write_matches_captured_life_factor():
    # 실측: "601 ... 2F 0D 10 00 01 00 00 00"
    f = P.sdo_write(1, P.OBJ_LIFE_FACTOR, 1, size=1)
    assert f.data == bytes.fromhex("2F0D100001000000")


def test_sdo_write_vendor_sub_index():
    # 실측: 기동 시 0x60FB.04 = 1
    f = P.sdo_write(3, P.OBJ_VENDOR_60FB, 1, size=1, sub=0x04)
    assert f.data == bytes.fromhex("2FFB600401000000")


def test_sdo_write_negative_velocity_two_complement():
    f = P.sdo_write(2, P.OBJ_TARGET_VELOCITY, -2445, size=4)
    r = P.parse_sdo_response(0x582, bytes([0x43]) + f.data[1:])
    assert r.value == -2445


def test_sdo_read_matches_captured_position_request():
    # 실측: "603 ... 40 64 60 00 00 00 00 00" (t=45.703)
    f = P.sdo_read(3, P.OBJ_POSITION_ACTUAL)
    assert f.can_id == 0x603
    assert f.data == bytes.fromhex("4064600000000000")


def test_guard_rtr():
    f = P.guard_rtr(4)
    assert f.can_id == 0x704 and f.is_rtr and f.data == b""


def test_parse_read_response_signed():
    # node4 위치 -39 = 0xFFFFFFD9
    r = P.parse_sdo_response(0x584, bytes.fromhex("43646000D9FFFFFF"))
    assert r is not None and r.kind == "read" and r.node == 4 and r.value == -39


def test_parse_write_ack_and_abort():
    a = P.parse_sdo_response(0x581, bytes.fromhex("6040600000000000"))
    assert a.kind == "write_ack" and a.index == 0x6040
    b = P.parse_sdo_response(0x581, bytes.fromhex("80FF600011000502"))
    assert b.kind == "abort" and b.value == 0x02050011


def test_parse_rejects_non_sdo():
    assert P.parse_sdo_response(0x701, b"\x00" * 8) is None
    assert P.parse_sdo_response(0x581, b"\x60\x40") is None
