"""우리 코드가 내는 프레임 ↔ **마스터(Seer) 실측 캡처 원본** 바이트 대조.

## 왜 이 파일이 필요한가

`halt_steer` 는 실측 대조 없이 도입됐고(`docs/claude-mistake/2026-08-03-003`), 3일 뒤에야
사람이 물어서 캡처와 맞춰 봤다. 그 대조를 **회귀로 고정**해 다음부터는 코드가 바뀌면 즉시 깨지게 한다.

「우리가 만든 명령인가」를 문서 grep 이 아니라 **원자료**로 답한다
(재발 방지 자산 `Tools/docking_field_kit/master_command_census.py` 와 같은 원칙).

대조 대상 캡처: `Log/homing_capture_220350.jsonl` (마스터 Seer 180 s · 253,510 프레임).
캡처가 없으면 skip 한다 — 이 파일은 캡처를 **만들지 않는다**(장치 미접속·송신 0건).
"""
import json
import os

import pytest

from can_relay import protocol as P
from can_relay.link import _find_repo_root

CAPTURE = os.path.join(_find_repo_root(__file__), "Log", "homing_capture_220350.jsonl")
STEER_REQ = {0x603: 3, 0x604: 4}


def _master_frames():
    """캡처에서 마스터가 조향 노드로 보낸 **쓰기 프레임 원본**을 (can_id, bytes) 로 모은다."""
    if not os.path.isfile(CAPTURE):
        # 이 함수는 :44 에서 **모듈 최상위**로 호출되므로 `allow_module_level` 이 필요하다.
        # 없으면 skip 이 아니라 수집 오류가 되어 같은 디렉터리의 다른 시험까지 함께 죽는다.
        pytest.skip(f"캡처 없음: {CAPTURE}", allow_module_level=True)
    out = set()
    with open(CAPTURE, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
                cid = r["id"]
                d = bytes.fromhex(r["d"])
            except (ValueError, KeyError):
                continue
            if cid in STEER_REQ and len(d) == 8 and d[0] in (0x23, 0x2B, 0x2F):
                out.add((cid, d))
    return out


MASTER = _master_frames()


def _idx(d):
    return d[1] | (d[2] << 8)


def test_capture_actually_loaded():
    """위양성 차단 — 캡처가 비었는데 통과하는 일이 없게 한다."""
    assert len(MASTER) >= 4, f"마스터 쓰기 프레임이 너무 적다: {len(MASTER)}"


@pytest.mark.parametrize("node,counts", [
    (3, 7_871_815), (4, 7_840_086),      # 0° 부근 — 마스터가 상시 유지하는 목표
    (3, 7_882_020), (4, 7_859_062),      # 호밍 후 정착 목표
])
def test_our_steer_target_frames_are_byte_identical_to_master(node, counts):
    """`steer_target_frames` 가 만드는 2프레임이 **캡처 원본과 바이트 동일**한가.

    이것이 `halt_steer` 가 보내는 바로 그 프레임이다.
    """
    ours = P.steer_target_frames(node, counts, bus=2)
    for f in ours:
        key = (0x600 + node, bytes(f.data[:8]))
        assert key in MASTER, (
            f"node{node} 0x{_idx(bytes(f.data)):04X} 프레임이 마스터 캡처에 없다: "
            f"{bytes(f.data[:8]).hex()}")


def test_master_never_sends_halt_bit():
    """마스터는 Halt(bit8)를 쓰지 않는다 — 우리가 안 쓰는 근거."""
    cw = [d for cid, d in MASTER if _idx(d) == P.OBJ_CONTROLWORD]
    assert cw, "controlword 쓰기가 캡처에 없다"
    for d in cw:
        val = int.from_bytes(d[4:6], "little")
        assert not (val & 0x0100), f"마스터가 Halt 를 썼다: 0x{val:04X}"


def test_our_controlword_value_is_one_the_master_uses():
    """`0x6040 = 0x3F` 가 마스터가 실제로 쓰는 값인가."""
    master_vals = {int.from_bytes(d[4:6], "little")
                   for cid, d in MASTER if _idx(d) == P.OBJ_CONTROLWORD}
    assert P.CW_STEER_SETPOINT in master_vals, (
        f"우리 controlword 0x{P.CW_STEER_SETPOINT:02X} 가 마스터 사용값 "
        f"{[hex(v) for v in sorted(master_vals)]} 에 없다")


def test_drive_init_and_steer_init_frames_exist_in_capture():
    """브링업 시퀀스도 마스터가 낸 것과 같은 바이트인지 — 실기 미검증 경로의 최소 근거."""
    missing = []
    for f in P.steer_init_frames(3, bus=2) + P.steer_init_frames(4, bus=2):
        if (0x600 + (f.can_id - 0x600), bytes(f.data[:8])) not in MASTER:
            missing.append((f.can_id - 0x600, f"0x{_idx(bytes(f.data)):04X}",
                            bytes(f.data[:8]).hex()))
    assert not missing, f"캡처에 없는 브링업 프레임: {missing}"
