"""조향 원점 — `/motor/low_cmd` 지령과 `/motor/low_state` 피드백이 홈 기준인가.

## 왜 별도 파일인가

기존 `test_backend.py` 의 저수준 경로 시험은 픽스처가 `steer_home = {3: 0, 4: 0}` 이다
(`test_backend.py:496` 「raw 계산을 읽기 쉽게」). 홈이 0 이면 **원점을 더하든 안 더하든 결과가
같아서**, 원점 처리를 통째로 지워도 그 시험들은 전부 통과한다. 여기서는 실기 캘리브레이션
값(`config/machine/foil_a082.yaml:136`)을 그대로 써서 그 눈먼 구간을 덮는다.

근거 사건: docs/claude-mistake/INDEX.md 2026-08-04-001 — 「시험을 추가한 것과 시험이 검출하는
것을 같게 취급한다」. 이 파일의 시험은 원점 처리를 지우면 **반드시 실패해야 한다**.
"""

import pytest

from can_relay import protocol as P
from can_relay import safety as S
from can_relay.backend import RelayBackend, RelayConfig
from can_relay.link import MockLink

# 실기 값 — config/machine/foil_a082.yaml:136 `steer_home_counts`
HOME = {3: 7_871_815, 4: 7_840_086}
COUNTS_PER_DEG = 57344.0          # 같은 파일 :20


def homed_real(**kw):
    """실기 홈 값을 쓰는 백엔드. `test_backend.homed()` 는 홈이 0 이라 원점을 못 본다."""
    kw.setdefault("steer_home", dict(HOME))
    kw.setdefault("steer_counts_per_deg", COUNTS_PER_DEG)
    cfg = RelayConfig(cmd_hz=100.0, poll_hz=50.0, cmd_timeout_s=0.15,
                      require_homed_for_steer=True, **kw)
    link = MockLink()
    link.open()
    link.acquire()
    be = RelayBackend(link, cfg)
    be._homed = True
    return link, be


def mc(mid, tpos=0, mode=P.MODE_POSITION, tvel=0, pvel=30000):
    return (mid, mode, tvel, tpos, pvel)


# ── 지령 방향 ──────────────────────────────────────────────────────────────

def test_zero_command_is_straight_not_clamped():
    """0°(직진) 지령이 홈으로 가야 한다.

    원점을 더하지 않으면 상대 0 이 절대 0 으로 읽혀 클램프 하한(홈−90°)까지 잘린다 —
    3톤 차체가 직진 지령에 90° 꺾인다(2026-08-05 리뷰 Critical).
    """
    _, be = homed_real()
    notes = be.set_motor_cmds([mc(3, tpos=0), mc(4, tpos=0)])
    assert notes == [], f"직진 지령이 클램프/거부됐다: {notes}"
    assert be._steer_counts[3] == HOME[3]
    assert be._steer_counts[4] == HOME[4]


@pytest.mark.parametrize("deg", [-90.0, -30.0, -1.0, 0.0, 1.0, 30.0, 90.0])
def test_command_matches_deg_path(deg):
    """raw 경로가 실기 검증된 각도 경로(`set_steer_deg`)와 같은 counts 를 내야 한다.

    두 경로가 갈리면 GUI 로 세운 각과 모션 스택이 세운 각이 달라진다.
    """
    _, be_deg = homed_real()
    be_deg.set_steer_deg(deg)
    expected = dict(be_deg._steer_counts)

    _, be_raw = homed_real()
    rel = int(round(deg * COUNTS_PER_DEG))
    be_raw.set_motor_cmds([mc(3, tpos=rel), mc(4, tpos=rel)])

    assert be_raw._steer_counts == expected


def test_command_clamp_is_around_home():
    """한계를 넘는 지령은 **홈 기준** ±90° 로 잘린다(절대 0 기준이 아니다)."""
    _, be = homed_real()
    over = int(round(200.0 * COUNTS_PER_DEG))       # +200° 시도
    notes = be.set_motor_cmds([mc(3, tpos=over)])
    assert any("클램프" in n for n in notes)
    limit_c = int(round(90.0 * COUNTS_PER_DEG))
    assert be._steer_counts[3] == HOME[3] + limit_c


def test_clamp_note_reports_relative_counts():
    """클램프 사유의 숫자도 홈 기준이어야 한다 — 절대 counts 를 보이면 상류가 오독한다."""
    _, be = homed_real()
    over = int(round(200.0 * COUNTS_PER_DEG))
    notes = be.set_motor_cmds([mc(3, tpos=over)])
    limit_c = int(round(90.0 * COUNTS_PER_DEG))
    assert any(str(limit_c) in n for n in notes), notes
    assert not any(str(HOME[3] + limit_c) in n for n in notes), notes


def test_command_reaches_can_as_absolute():
    """CAN 으로는 **절대** counts 가 나가야 한다 — 드라이브 0x607A 는 절대 좌표다."""
    link, be = homed_real()
    be.set_motor_cmds([mc(3, tpos=0)])
    be.start()
    try:
        import time
        t0 = time.monotonic()
        frames = []
        while time.monotonic() - t0 < 2.0:
            frames = [f for f in link.sent
                      if (f.data[1] | (f.data[2] << 8)) == P.OBJ_TARGET_POSITION
                      and f.data[0] != 0x40 and f.can_id == 0x603]
            if frames:
                break
            time.sleep(0.01)
        assert frames, "0x607A 프레임이 나가지 않았다"
        val = int.from_bytes(frames[-1].data[4:8], "little", signed=True)
        assert val == HOME[3]
    finally:
        be.shutdown()


# ── 피드백 방향 ────────────────────────────────────────────────────────────

def test_feedback_is_relative_to_home():
    """직진 자세의 실측 절대 counts 는 상류에 **0 근처**로 보고돼야 한다.

    절대값을 그대로 올리면 7,871,815 / 57,344 = 137.3° 로 읽힌다.
    """
    _, be = homed_real()
    with be._lock:
        be.nodes[3].position = HOME[3]
        be.nodes[4].position = HOME[4] + int(round(10.0 * COUNTS_PER_DEG))

    states = {s["motor_id"]: s for s in be.motor_states()}
    assert states[3]["fb_pos"] == 0
    assert states[4]["fb_pos"] == int(round(10.0 * COUNTS_PER_DEG))
    assert abs(states[3]["fb_pos"] / COUNTS_PER_DEG) < 0.001


def test_feedback_drive_axis_untouched():
    """구동축에는 홈이 없다 — 빼면 안 된다."""
    _, be = homed_real()
    with be._lock:
        be.nodes[1].position = 123_456
    states = {s["motor_id"]: s for s in be.motor_states()}
    assert states[1]["fb_pos"] == 123_456


def test_feedback_roundtrip_with_command():
    """지령한 각을 실측이 따라왔을 때, 피드백이 그 각을 그대로 돌려줘야 한다."""
    _, be = homed_real()
    rel = int(round(-25.0 * COUNTS_PER_DEG))
    be.set_motor_cmds([mc(3, tpos=rel)])
    with be._lock:
        be.nodes[3].position = be._steer_counts[3]      # 목표 도달 가정

    states = {s["motor_id"]: s for s in be.motor_states()}
    assert states[3]["fb_pos"] == rel


def test_feedback_without_home_config_is_raw():
    """홈이 설정되지 않은 노드는 빼지 않는다 — 없는 값을 지어내지 않는다."""
    _, be = homed_real(steer_home={3: HOME[3]})         # node4 홈 없음
    with be._lock:
        be.nodes[3].position = HOME[3]
        be.nodes[4].position = 999_999
    states = {s["motor_id"]: s for s in be.motor_states()}
    assert states[3]["fb_pos"] == 0
    assert states[4]["fb_pos"] == 999_999


# ── 안전 게이트가 원점 도입으로 약해지지 않았는가 ──────────────────────────

def test_estop_still_blocks_with_real_home():
    _, be = homed_real()
    be.estop(True)
    notes = be.set_motor_cmds([mc(3, tpos=0)])
    assert any("E-stop" in n for n in notes)
    assert 3 not in be._steer_counts


def test_unhomed_still_rejected_with_real_home():
    _, be = homed_real()
    be._homed = False
    notes = be.set_motor_cmds([mc(3, tpos=0)])
    assert any("호밍 미완료" in n for n in notes)
    assert 3 not in be._steer_counts


def test_missing_home_still_rejected():
    """홈이 없는 조향 노드는 거부한다 — 원점 0 으로 가정하지 않는다."""
    _, be = homed_real(steer_home={3: HOME[3]})
    notes = be.set_motor_cmds([mc(4, tpos=0)])
    assert any("홈 미설정" in n for n in notes)
    assert 4 not in be._steer_counts


def test_drive_axis_unaffected_by_origin():
    _, be = homed_real()
    notes = be.set_motor_cmds([(1, P.MODE_VELOCITY, 1234, 0, 0)])
    assert notes == []
    assert be._drive_units_by_node[1] == 1234
