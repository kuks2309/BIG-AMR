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


@pytest.fixture(scope="module")
def master():
    """캡처에서 마스터가 조향 노드로 보낸 **쓰기 프레임 원본**을 (can_id, bytes) 로 모은다.

    ⚠ **fixture 여야 한다 — 모듈 최상위에서 부르면 안 된다.**
    종전에는 `master = _master_frames()` 로 최상위에서 호출하고 캡처 부재 시
    `pytest.skip(..., allow_module_level=True)` 를 냈다. 그러면 **디렉터리 전체 수집이
    중단된다** — `pytest test/` 가 `collected 0 items / 1 skipped` 로 끝나고, 알파벳 순서상
    앞선 파일들까지 하나도 수집되지 않는다(pytest 6.2.5 실측). 출력이 `1 skipped` 뿐이라
    **「돌릴 게 없다/문제 없다」로 읽히고 다른 시험의 실패가 보이지 않는다.**
    fixture 안에서 skip 하면 **이 파일의 시험만** 건너뛰고 나머지는 정상 수집·실행된다.
    """
    if not os.path.isfile(CAPTURE):
        pytest.skip(f"캡처 없음: {CAPTURE}")
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


def _idx(d):
    return d[1] | (d[2] << 8)


def test_capture_actually_loaded(master):
    """위양성 차단 — 캡처가 비었는데 통과하는 일이 없게 한다."""
    assert len(master) >= 4, f"마스터 쓰기 프레임이 너무 적다: {len(master)}"


@pytest.mark.parametrize("node,counts", [
    (3, 7_871_815), (4, 7_840_086),      # 0° 부근 — 마스터가 상시 유지하는 목표
    (3, 7_882_020), (4, 7_859_062),      # 호밍 후 정착 목표
])
def test_our_steer_target_frames_are_byte_identical_to_master(node, counts, master):
    """`steer_target_frames` 가 만드는 2프레임이 **캡처 원본과 바이트 동일**한가.

    ⚠ 2026-08-05: 이 프레임을 **정지 경로에서는 더 이상 보내지 않는다**(옛 `halt_steer`/
    `hold_steer_at_measured` 제거 — `docs/claude-mistake/2026-08-05-001`). 여기서 고정하는 것은
    **조향 지령(`set_steer_deg`·`set_steer_axis_deg`)이 내는 프레임이 마스터와 같은가**이며,
    그것은 여전히 유효하다 — 마스터도 조향 목표를 이 조합으로 낸다(캡처 12,928회).
    """
    ours = P.steer_target_frames(node, counts, bus=2)
    for f in ours:
        key = (0x600 + node, bytes(f.data[:8]))
        assert key in master, (
            f"node{node} 0x{_idx(bytes(f.data)):04X} 프레임이 마스터 캡처에 없다: "
            f"{bytes(f.data[:8]).hex()}")


def test_master_never_sends_halt_bit(master):
    """마스터는 Halt(bit8)를 쓰지 않는다 — 우리가 안 쓰는 근거."""
    cw = [d for cid, d in master if _idx(d) == P.OBJ_CONTROLWORD]
    assert cw, "controlword 쓰기가 캡처에 없다"
    for d in cw:
        val = int.from_bytes(d[4:6], "little")
        assert not (val & 0x0100), f"마스터가 Halt 를 썼다: 0x{val:04X}"


def test_our_controlword_value_is_one_the_master_uses(master):
    """`0x6040 = 0x3F` 가 마스터가 실제로 쓰는 값인가."""
    master_vals = {int.from_bytes(d[4:6], "little")
                   for cid, d in master if _idx(d) == P.OBJ_CONTROLWORD}
    assert P.CW_STEER_SETPOINT in master_vals, (
        f"우리 controlword 0x{P.CW_STEER_SETPOINT:02X} 가 마스터 사용값 "
        f"{[hex(v) for v in sorted(master_vals)]} 에 없다")


def test_drive_init_and_steer_init_frames_exist_in_capture(master):
    """브링업 시퀀스도 마스터가 낸 것과 같은 바이트인지 — 실기 미검증 경로의 최소 근거."""
    missing = []
    for f in P.steer_init_frames(3, bus=2) + P.steer_init_frames(4, bus=2):
        if (0x600 + (f.can_id - 0x600), bytes(f.data[:8])) not in master:
            missing.append((f.can_id - 0x600, f"0x{_idx(bytes(f.data)):04X}",
                            bytes(f.data[:8]).hex()))
    assert not missing, f"캡처에 없는 브링업 프레임: {missing}"
