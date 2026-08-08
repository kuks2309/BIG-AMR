"""이식 동등성 회귀 — 원본 `gui.py` 와 이식본이 **같은 조작에 같은 CAN 바이트**를 내는가.

ADR `docs/adr/2026-08-03-amr-test-gui-ros2-port.md` §Verification 게이트 4 의 **무동작 부분**이다.

## 이 파일이 판정하는 것과 못 하는 것

- **판정한다**: 지령 생성 경로의 바이트 동등성. 같은 조향각·같은 속도에 대해 두 구현이
  만드는 프레임이 바이트까지 같은지. 이것이 「동일 구현」 주장의 핵심이다.
- **판정하지 못한다**: USB·릴레이 거동, 타이밍, 드라이브 응답. 그건 잭업 실기 몫이며
  **이 파일이 통과해도 실기 검증을 대신하지 않는다.**

모터를 움직이지 않는다 — 원본의 `_sdo_write` 를 가로채고(하드웨어 미접속), 이식본은 MockLink 를
쓴다. **USB 를 열지 않으며 프레임은 한 장도 버스로 나가지 않는다.**
"""
import importlib.util
import os

import pytest

from can_relay import protocol as P
from can_relay.backend import RelayBackend, RelayConfig
from can_relay.link import MockLink, _find_repo_root

# 원본은 PyQt5 를 import 한다 — 없으면 대조 자체가 불가능하므로 skip.
pytest.importorskip("PyQt5", reason="PyQt5 미설치 — 원본 GUI 를 로드할 수 없다")

# ⚠ 깊이를 세지 않는다. 처음에 `dirname` 5회로 적었다가 `.../Big-AMR/src` 를 루트로 잡아
#   **원본을 못 찾고 시험 전체가 조용히 skip** 됐다 — `link.py:_find_repo_root` 가 문서화해 둔
#   것과 똑같은 off-by-one 이다. 그 함수(마커 탐색)를 그대로 쓴다.
_REPO = _find_repo_root(__file__)
_ORIG = os.path.join(_REPO, "Tools", "amr_test_gui", "gui.py")


def _load_original():
    """원본 `gui.py` 를 모듈로 로드한다. **모듈 레벨 코드만 돈다**(Qt 앱 생성 없음)."""
    if not os.path.isfile(_ORIG):
        # skip 하지 않는다 — 원본 부재는 「대조할 것이 없다」가 아니라 **전제 붕괴**다.
        raise AssertionError(
            f"원본을 찾지 못했다: {_ORIG} (저장소 루트 판정 = {_REPO})")
    spec = importlib.util.spec_from_file_location("orig_gui", _ORIG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


orig = _load_original()


class _FrameSpy:
    """원본의 `_sdo_write` 자리에 끼워 프레임을 모은다(송신 없음)."""

    def __init__(self):
        self.frames = []

    def sdo_write(self, node, idx, val, size, sub=0):
        """원본 `gui.py:840-849` 의 바이트 조립을 **그대로** 옮긴 것.

        원본 메서드는 `self.panda.can_send` 를 부르므로 하드웨어 없이 호출할 수 없다.
        조립 규칙만 복제해 같은 바이트를 만든다 — 이 복제가 원본과 어긋나면
        `test_spy_matches_original_assembly` 가 잡는다.
        """
        cmd = {1: 0x2F, 2: 0x2B, 4: 0x23}[size]
        payload = (val & 0xFFFFFFFF).to_bytes(4, "little")[:size]
        data = bytes([cmd, idx & 0xFF, idx >> 8, sub]) + payload + b"\x00" * (4 - size)
        self.frames.append((0x600 + node, data[:8]))
        return data[:8]


def _port_backend():
    """이식본 체인 — 드라이버 설정을 **원본 상수와 같게** 맞춘다.

    값은 원본에서 읽어 온다(하드코딩하지 않는다) — 원본이 바뀌면 이 시험이 먼저 깨져야 한다.
    """
    cfg = RelayConfig(
        steer_home=dict(orig.STEER_HOME),
        steer_counts_per_deg=float(orig.COUNTS_PER_DEG),
        drive_units_per_mmps=float(orig.VEL_PER_MMPS),
        vel_max_units=int(orig.VEL_MAX_UNITS),
        steer_limit_deg=float(orig.STEER_LIMIT_DEG),
        require_homed_for_steer=False,
        cmd_hz=100.0,
    )
    link = MockLink()
    link.open()
    link.acquire()
    return link, RelayBackend(link, cfg)


def _sent(link):
    return [(f.can_id, bytes(f.data[:8])) for f in link.sent]


# ── 조립 규칙이 원본과 같은지 먼저 확인(위양성 차단) ──────────────────────
def test_spy_matches_original_assembly():
    """대역이 원본 조립을 흉내내는 것이 맞는지 원문과 대조한다.

    이 확인이 없으면 「대역끼리 같다」를 「구현끼리 같다」로 착각할 수 있다.
    """
    src = open(_ORIG, encoding="utf-8").read()
    assert 'cmd = {1: 0x2F, 2: 0x2B, 4: 0x23}[size]' in src
    assert 'data = bytes([cmd, idx & 0xFF, idx >> 8, sub]) + payload + b"\\x00" * (4 - size)' in src
    assert 'self.panda.can_send(0x600 + node, data[:8], MOTOR_BUS)' in src


def test_constants_match_between_implementations():
    """이식본은 상수를 갖지 않고 드라이버 설정을 쓴다 — 그 설정이 원본과 같은 값인지."""
    link, be = _port_backend()
    assert be.cfg.steer_home == orig.STEER_HOME
    assert be.cfg.steer_counts_per_deg == orig.COUNTS_PER_DEG
    assert be.cfg.drive_units_per_mmps == orig.VEL_PER_MMPS
    assert be.cfg.vel_max_units == orig.VEL_MAX_UNITS


# ── 조향 — 축별 ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("node", [3, 4])
@pytest.mark.parametrize("deg", [0.0, 1.0, -1.0, 15.0, -30.0, 45.0, 89.0, -90.0, 90.0])
def test_steer_axis_frames_are_byte_identical(node, deg):
    """축별 조향: 원본 `_steer_axis` ↔ 이식본 `set_steer_axis_deg` 바이트 동일."""
    spy = _FrameSpy()
    applied, counts = orig.steer_counts(node, deg)
    spy.sdo_write(node, 0x607A, counts, 4)
    spy.sdo_write(node, 0x6040, 0x3F, 2)

    link, be = _port_backend()
    be.set_steer_axis_deg(node, deg)
    frames = []
    for n, c in sorted(be._steer_counts.items()):
        frames.extend(P.steer_target_frames(n, c, be.cfg.bus))
    port = [(f.can_id, bytes(f.data[:8])) for f in frames]

    assert port == spy.frames, (
        f"node{node} {deg}°: 원본 {spy.frames} ≠ 이식본 {port}")


@pytest.mark.parametrize("deg", [200.0, -200.0, 91.0])
def test_steer_axis_clamp_is_byte_identical(deg):
    """범위 밖도 같은 각으로 잘려야 한다 — 클램프 위치가 달라도 결과 바이트는 같다."""
    spy = _FrameSpy()
    _applied, counts = orig.steer_counts(3, deg)
    spy.sdo_write(3, 0x607A, counts, 4)

    link, be = _port_backend()
    be.set_steer_axis_deg(3, deg)
    port = P.steer_target_frames(3, be._steer_counts[3], be.cfg.bus)[0]
    assert (port.can_id, bytes(port.data[:8])) == spy.frames[0]


# ── 조향 — 전축(crab) ────────────────────────────────────────────────────
@pytest.mark.parametrize("deg", [0.0, 45.0, -45.0, 90.0])
def test_steer_all_axes_frames_are_byte_identical(deg):
    """crab: 원본 `_steer_to`(node 3·4 순차) ↔ 이식본 `set_steer_deg`."""
    spy = _FrameSpy()
    for n in (3, 4):
        _applied, counts = orig.steer_counts(n, deg)
        spy.sdo_write(n, 0x607A, counts, 4)
        spy.sdo_write(n, 0x6040, 0x3F, 2)

    link, be = _port_backend()
    be.set_steer_deg(deg)
    frames = []
    for n, c in sorted(be._steer_counts.items()):
        frames.extend(P.steer_target_frames(n, c, be.cfg.bus))
    port = [(f.can_id, bytes(f.data[:8])) for f in frames]
    assert port == spy.frames


# ── 구동 ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("mmps,sign", [(0, -1), (50, -1), (50, +1), (100, -1),
                                       (200, +1), (200, -1), (5, +1)])
def test_drive_frames_are_byte_identical(mmps, sign):
    """구동: 원본 `drive_units(mmps, raw_sign)` ↔ 이식본 `set_drive_mmps(sign*mmps)`.

    원본은 raw 부호를 직접 만들고, 이식본은 mm/s 에 부호를 실어 보낸 뒤 드라이버가 환산한다.
    **경로는 다르지만 나오는 바이트는 같아야 한다** — 그것이 이 시험의 요지다.
    """
    spy = _FrameSpy()
    units = orig.drive_units(mmps, sign)
    for n in (1, 2):
        spy.sdo_write(n, 0x60FF, units, 4)

    link, be = _port_backend()
    be.set_drive_mmps(sign * mmps)
    port = [(f.can_id, bytes(f.data[:8]))
            for f in be._drive_frames(be.snapshot()["drive_units"])]
    assert port == spy.frames, f"{sign*mmps} mm/s: 원본 {spy.frames} ≠ 이식본 {port}"


def test_drive_speed_cap_is_byte_identical():
    """상한 클램프도 같은 값이어야 한다(원본 4889 = 이식본 vel_max_units)."""
    spy = _FrameSpy()
    units = orig.drive_units(10_000, -1)         # 상한을 훨씬 넘는 값
    spy.sdo_write(1, 0x60FF, units, 4)

    link, be = _port_backend()
    be.set_drive_mmps(-10_000.0)
    port = be._drive_frames(be.snapshot()["drive_units"])[0]
    assert (port.can_id, bytes(port.data[:8])) == spy.frames[0]
    assert abs(be.snapshot()["drive_units"]) == orig.VEL_MAX_UNITS


# ── 조그 8방향 전체 (원본 JOG 표를 그대로 돌린다) ────────────────────────
@pytest.mark.parametrize("label", list(orig.JOG))
def test_every_jog_direction_is_byte_identical(label):
    """8방향 전부 — 조향 프레임과 구동 프레임이 모두 같은지 한 번에 본다."""
    steer_deg, sign, _verified = orig.JOG[label]
    mmps = 50.0

    spy = _FrameSpy()
    for n in (3, 4):
        _a, counts = orig.steer_counts(n, steer_deg)
        spy.sdo_write(n, 0x607A, counts, 4)
        spy.sdo_write(n, 0x6040, 0x3F, 2)
    units = orig.drive_units(mmps, sign)
    for n in (1, 2):
        spy.sdo_write(n, 0x60FF, units, 4)

    link, be = _port_backend()
    be.set_steer_deg(steer_deg)
    be.set_drive_mmps(sign * mmps)
    port = []
    for n, c in sorted(be._steer_counts.items()):
        port.extend((f.can_id, bytes(f.data[:8]))
                    for f in P.steer_target_frames(n, c, be.cfg.bus))
    port.extend((f.can_id, bytes(f.data[:8]))
                for f in be._drive_frames(be.snapshot()["drive_units"]))
    assert port == spy.frames, f"조그 '{label}': 바이트 불일치"


# ── 의도된 차이 — 호밍은 **다른 경로**다 ─────────────────────────────────
def test_homing_path_differs_by_design():
    """호밍만은 바이트가 달라야 정상이다 — 이식본은 펌웨어 시퀀서를 쓴다.

    원본은 SDO 직접 송신(0x6040=0x86 · 0x6099 · 0x60FB:04=1)이고, 이식본은 USB `0xea` 로
    펌웨어 시퀀서를 부른다. **그래야 `~/home_cancel` 이 호스트 생사와 무관하게 성립**하며,
    그것이 이식의 목적 중 하나다(ADR §Decision ④).
    이 시험은 「같아야 한다」가 아니라 **「다르다는 것을 알고 있다」**를 고정한다.
    """
    src = open(_ORIG, encoding="utf-8").read()
    assert "0x60FB, 1, 1, sub=4" in src, "원본이 SDO 직접 호밍을 쓰지 않는다 — 전제가 바뀌었다"

    link, be = _port_backend()
    be.cfg.homing_method = "firmware"
    # 이 시험의 대상은 **호밍 경로의 바이트**(0xea 대 SDO 직접)뿐이다. 호밍 뒤에 이어지는
    # 조향 0° 복귀(ADR 2026-08-08)는 별개 계약이고 회귀도 별도다
    # (`test_steer_zero_return.py`) — 여기서 켜 두면 대역 피드백을 갖추는 부담만 늘고
    # 경로 대조에는 보태는 것이 없다.
    be.cfg.steer_zero_after_home = False
    be.start()
    try:
        link.homing_script = [MockLink.homing_state(5, elapsed_s=31, reached_mask=3)]
        ok, _why = be.home(poll_s=0.01, timeout_s=2.0)
        assert ok is True
        # 이식본은 `0x60FB` 를 **한 장도** 직접 보내지 않는다.
        assert not [f for f in link.sent
                    if (f.data[1] | (f.data[2] << 8)) == P.OBJ_VENDOR_60FB]
        assert any(s.startswith("homing_start") for s in link.log)
    finally:
        be.shutdown()
