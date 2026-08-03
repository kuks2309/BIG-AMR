"""SDO 코덱 회귀 — 실측 캡처 바이트를 고정한다.

기대 바이트의 근거는 `Log/homing_capture_220350.jsonl`(Seer 마스터 180 s) 과
`Tools/amr_test_gui/gui.py` 의 실기 검증 프레임이다. 이 파일이 통과한다는 것은
"우리가 만든 바이트가 실기에서 오간 바이트와 같다"는 뜻이다.
"""
import pytest

from can_relay import protocol as P


def hexs(frame):
    return frame.data.hex()


# ── 쓰기 인코딩 ────────────────────────────────────────────────────────────
def test_write_4byte_matches_capture():
    # 0x60FF = 0 (구동 정지). 캡처의 0x60FF 쓰기와 동일 형태.
    f = P.sdo_write(1, P.OBJ_TARGET_VELOCITY, 0, 4)
    assert f.can_id == 0x601
    assert hexs(f) == "23ff600000000000"


def test_write_controlword_exact():
    # 바이트 배치: [cmd, idx_lo, idx_hi, sub, payload...] — sub 가 4번째다.
    f = P.sdo_write(3, P.OBJ_CONTROLWORD, 0x3F, 2)
    assert hexs(f) == "2b4060003f000000"


def test_write_fault_reset_enable():
    f = P.sdo_write(3, P.OBJ_CONTROLWORD, 0x86, 2)
    assert hexs(f) == "2b40600086000000"


def test_homing_trigger_subindex_lands_in_byte3():
    """0x60FB:04 = 1 — sub 가 4번째 바이트에 들어가야 한다. 여기서 축이 움직인다."""
    f = P.sdo_write(3, P.OBJ_VENDOR_60FB, 1, 1, sub=4)
    assert f.can_id == 0x603
    assert f.data[0] == 0x2F        # 1바이트 쓰기
    assert f.data[1:3] == bytes([0xFB, 0x60])
    assert f.data[3] == 4
    assert f.data[4] == 1


def test_homing_speed_value_matches_capture():
    """캡처 t=17.918 의 0x6099 = 2500 (0.1 r/min → 250 r/min)."""
    f = P.sdo_write(3, P.OBJ_HOMING_SPEED, 2500, 4)
    assert hexs(f) == "2399" + "60" + "00" + "c4090000"


def test_negative_velocity_encodes_two_complement():
    f = P.sdo_write(1, P.OBJ_TARGET_VELOCITY, -4889, 4)
    assert f.data[4:8] == (-4889 & 0xFFFFFFFF).to_bytes(4, "little")


def test_write_rejects_oversize_value_instead_of_truncating():
    """조용한 절단은 지령을 바꾼다 — 예외로 막는다."""
    with pytest.raises(ValueError):
        P.sdo_write(1, P.OBJ_CONTROLWORD, 70000, size=2)


def test_write_rejects_unknown_size():
    with pytest.raises(KeyError):
        P.sdo_write(1, P.OBJ_CONTROLWORD, 1, size=3)


def test_read_request_bytes():
    f = P.sdo_read(2, P.OBJ_POSITION_ACTUAL)
    assert f.can_id == 0x602
    assert hexs(f) == "4064600000000000"


def test_digital_input_polls_subindex_one():
    """sub 0 은 엔트리 수라 리밋 판정이 죽는다. 반드시 sub 1."""
    frames = P.poll_frames([3])
    di = [f for f in frames if f.data[1] | (f.data[2] << 8) == P.OBJ_DIGITAL_INPUT]
    assert len(di) == 1
    assert di[0].data[3] == 1


# ── 읽기 디코딩 ────────────────────────────────────────────────────────────
def test_parse_4byte_signed():
    data = bytes([0x43, 0x64, 0x60, 0x00]) + (-1234).to_bytes(4, "little", signed=True)
    r = P.parse_sdo_response(0x581, data)
    assert (r.node, r.kind, r.index, r.value, r.size) == (1, "read", 0x6064, -1234, 4)


def test_parse_2byte_does_not_read_trailing_bytes():
    """0x4B(2B) 응답에서 상위 2바이트를 함께 읽으면 값이 오염된다."""
    data = bytes([0x4B, 0x41, 0x60, 0x00, 0x37, 0x06, 0xAA, 0xBB])
    r = P.parse_sdo_response(0x581, data)
    assert r.value == 0x0637        # 0xBBAA0637 이 아니다
    assert r.size == 2


def test_parse_statusword_homed_bit():
    data = bytes([0x4B, 0x41, 0x60, 0x00, 0x50, 0x94, 0x00, 0x00])
    r = P.parse_sdo_response(0x583, data)
    assert r.value & 0xFFFF == 0x9450


def test_parse_write_ack():
    data = bytes([0x60, 0xFF, 0x60, 0x00, 0, 0, 0, 0])
    r = P.parse_sdo_response(0x581, data)
    assert r.kind == "write_ack"


def test_parse_abort_carries_code_and_reason():
    data = bytes([0x80, 0x7A, 0x60, 0x00]) + (0x08000022).to_bytes(4, "little")
    r = P.parse_sdo_response(0x584, data)
    assert r.kind == "abort" and r.value == 0x08000022
    assert P.abort_text(r.value) == "현재 장치 상태에서 전송 불가"


def test_parse_ignores_non_sdo_and_short_frames():
    assert P.parse_sdo_response(0x701, bytes(8)) is None      # guard 응답
    assert P.parse_sdo_response(0x581, bytes(4)) is None      # 길이 부족
    assert P.parse_sdo_response(0x580, bytes(8)) is None      # node 0


# ── 시퀀스 ────────────────────────────────────────────────────────────────
def test_homing_never_writes_homing_method():
    """0x6098 을 덮어쓰면 리셋 모드가 꺼져 호밍이 동작하지 않는다."""
    for f in P.homing_frames(3):
        assert (f.data[1] | (f.data[2] << 8)) != 0x6098


def test_homing_frame_order():
    """축 준비 → 호밍 속도 → RstStart. 순서가 곧 사양이다."""
    idxs = [(f.data[1] | (f.data[2] << 8)) for f in P.homing_frames(4)]
    assert idxs == [P.OBJ_CONTROLWORD, P.OBJ_HOMING_SPEED, P.OBJ_VENDOR_60FB]


def test_steer_target_sends_setpoint_controlword_after_position():
    frames = P.steer_target_frames(3, 7871815)
    idxs = [(f.data[1] | (f.data[2] << 8)) for f in frames]
    assert idxs == [P.OBJ_TARGET_POSITION, P.OBJ_CONTROLWORD]
    assert frames[1].data[4] == P.CW_STEER_SETPOINT


def test_drive_init_sets_pv_and_guard():
    idxs = [(f.data[1] | (f.data[2] << 8)) for f in P.drive_init_frames(1)]
    assert idxs == [P.OBJ_CONTROLWORD, P.OBJ_TARGET_VELOCITY,
                    P.OBJ_LIFE_FACTOR, P.OBJ_GUARD_TIME, P.OBJ_MODES]
    assert P.drive_init_frames(1)[-1].data[4] == 3          # PV


def test_steer_init_sets_pp_and_profile():
    frames = P.steer_init_frames(3)
    idxs = [(f.data[1] | (f.data[2] << 8)) for f in frames]
    assert P.OBJ_MODES in idxs and P.OBJ_PROFILE_VELOCITY in idxs
    mode = frames[idxs.index(P.OBJ_MODES)]
    assert mode.data[4] == 1                                # PP


def test_init_sequences_contain_no_homing_trigger():
    """브링업이 조용히 호밍을 걸면 100° 스윙이 예고 없이 일어난다."""
    for n in (1, 2):
        for f in P.drive_init_frames(n):
            assert (f.data[1] | (f.data[2] << 8)) != P.OBJ_VENDOR_60FB
    for n in (3, 4):
        for f in P.steer_init_frames(n):
            assert (f.data[1] | (f.data[2] << 8)) != P.OBJ_VENDOR_60FB


def test_poll_frames_are_all_reads():
    """폴링에 지령이 섞이면 안 된다."""
    for f in P.poll_frames([1, 2, 3, 4]):
        assert f.data[0] == 0x40


def test_guard_time_is_500ms_uint16():
    f = [x for x in P.drive_init_frames(1)
         if (x.data[1] | (x.data[2] << 8)) == P.OBJ_GUARD_TIME][0]
    assert f.data[0] == 0x2B                                 # 2바이트
    assert int.from_bytes(f.data[4:6], "little") == 500


# ── method 35 프레임 (2026-08-03 리뷰: 시험 0건이었다) ────────────────────
def test_home35_move_frames_match_upstream_order():
    """상류 `can_open.hpp:483-486` 과 같은 순서·객체다: 0x607A → 0x6081 → 0x6040."""
    frames = P.home35_move_frames(3, 1234, profile_vel=2500)
    idxs = [(f.data[1] | (f.data[2] << 8)) for f in frames]
    assert idxs == [P.OBJ_TARGET_POSITION, P.OBJ_PROFILE_VELOCITY, P.OBJ_CONTROLWORD]
    assert int.from_bytes(frames[0].data[4:8], "little", signed=True) == 1234
    assert int.from_bytes(frames[1].data[4:8], "little") == 2500
    assert int.from_bytes(frames[2].data[4:6], "little") == P.CW_STEER_SETPOINT


def test_home35_move_frames_carry_negative_offset():
    """오프셋은 음수일 수 있다 — 부호 없이 인코딩하면 반대편으로 간다."""
    f = P.home35_move_frames(4, -5_000_000)[0]
    assert int.from_bytes(f.data[4:8], "little", signed=True) == -5_000_000


def test_home35_set_frame_is_single_byte_35():
    """`0x6098 = 35` 는 INT8 이다 — 4바이트로 쓰면 드라이브가 길이 불일치로 거부한다."""
    frames = P.home35_set_frames(3)
    assert len(frames) == 1
    f = frames[0]
    assert (f.data[1] | (f.data[2] << 8)) == P.OBJ_HOMING_METHOD
    assert f.data[0] == 0x2F                       # 1바이트 expedited download
    assert f.data[4] == P.HOMING_METHOD_CURRENT_POS == 35


def test_home35_reached_requires_both_conditions():
    """상태워드 bit10 **과** 잔차 둘 다여야 도착이다(상류 can_open.hpp:489)."""
    assert P.home35_reached(P.STATUSWORD_TARGET_REACHED, 1000, 1000, 50) is True
    assert P.home35_reached(P.STATUSWORD_TARGET_REACHED, 1051, 1000, 50) is False
    assert P.home35_reached(0, 1000, 1000, 50) is False


def test_home35_reached_is_false_when_unknown():
    """모르는 것은 참이 아니다 — 미상이면 도착으로 치지 않는다."""
    assert P.home35_reached(None, 1000, 1000, 50) is False
    assert P.home35_reached(P.STATUSWORD_TARGET_REACHED, None, 1000, 50) is False
