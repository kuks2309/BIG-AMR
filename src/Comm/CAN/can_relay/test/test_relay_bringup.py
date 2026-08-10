"""`RelayBackend.start()` 가 구동축 브링업을 보내는가 (debt-047 중 미커버 절반).

## 왜 필요한가

2026-08-08 실기에서 `can_relay` **프로세스 재시작** 뒤 구동축이 `0x60FF` 를 받고도 돌지 않는
상태가 재현됐고, 브링업 시퀀스를 보내자 복귀했다. 그 수정에 **회귀가 없었다** —
`start()` 의 호출 한 줄을 지워도 전량 시험이 그대로 통과했다(돌연변이로 확인).

같은 날의 다른 수정(조향 호밍 게이트 통일)은 이미 고정돼 있다
(`test_backend.py::test_low_cmd_steer_allowed_when_drive_reports_homed`) — 그쪽은 되돌리면
1 failed 로 잡힌다. 여기서 메우는 것은 **브링업 쪽 절반**이다.

## 왜 `_write_bringup()` 을 직접 부르지 않는가

핸들러를 직접 부르면 배선을 지나가지 않아 `start()` 에서 호출을 지워도 통과한다
(`claude-mistake/2026-08-04-001` 의 실패 형태). 여기서는 **`start()` 를 돌려** 프레임을 본다.

## 검출력

`start()` 의 `if self.cfg.allow_bringup: self._write_bringup()` 두 줄을 지우면
`test_start_sends_drive_bringup_when_enabled` 가 실패한다 — 돌연변이 확인으로 증명한다.
"""
import pytest

from can_relay import protocol as P
from can_relay.backend import RelayBackend, RelayConfig
from can_relay.link import MockLink


def _make(**kw):
    kw.setdefault("require_homed_for_steer", False)
    kw.setdefault("steer_home", {3: 7871815, 4: 7840086})
    cfg = RelayConfig(cmd_hz=100.0, poll_hz=50.0, **kw)
    link = MockLink()
    link.open()
    link.acquire()
    return link, RelayBackend(link, cfg)


def _expected(cfg):
    exp = []
    for n in cfg.drive_nodes:
        for f in P.drive_init_frames(n, cfg.bus):
            exp.append((f.can_id, bytes(f.data[:8])))
    return exp


def _sent(link):
    return [(f.can_id, bytes(f.data[:8])) for f in link.sent]


def _distinctive(cfg):
    """브링업 **고유** 프레임만. `0x60FF=0`(목표속도 0)은 정상 지령 루프도 보내므로 뺀다.

    ⚠ 이걸 빼지 않으면 「브링업이 안 나갔다」를 검사할 수 없다 — 루프의 정상 정지 지령이
    같은 바이트라 항상 걸린다(실제로 걸렸다). 남는 4개(`0x6040=0x86` · `0x100C` ·
    `0x100D` · `0x6060=3`)는 브링업 외에는 아무도 보내지 않는다.
    """
    out = []
    for cid, data in _expected(cfg):
        if (data[1] | (data[2] << 8)) != P.OBJ_TARGET_VELOCITY:
            out.append((cid, data))
    return out


def test_start_sends_drive_bringup_when_enabled():
    """`allow_bringup=True` 면 `start()` 가 구동축 브링업을 **전부** 보낸다."""
    link, be = _make(allow_bringup=True)
    be.start()
    try:
        sent = _sent(link)
        for item in _expected(be.cfg):
            assert item in sent, (
                f"브링업 프레임 누락: id=0x{item[0]:X} data={item[1].hex()}. "
                f"이것이 없으면 프로세스 재시작 뒤 구동축이 0x60FF 를 받고도 돌지 않는다(debt-047).")
    finally:
        be.shutdown()


def test_bringup_is_not_sent_to_steer_axes():
    """조향축에는 보내지 않는다.

    2026-08-08 실기: 조향축까지 브링업을 보냈더니 fault reset 이 위치 카운터를 지워
    **조향 0° 기준이 무효**가 됐고, 그 상태의 「0° 로 가라」 지령에 전륜이 실제로 움직였다.
    조향 기준 복구는 호밍 소관이며 브링업이 대신할 수 있는 일이 아니다.
    """
    link, be = _make(allow_bringup=True)
    be.start()
    try:
        forbidden = set()
        for n in be.cfg.steer_nodes:
            for f in P.drive_init_frames(n, be.cfg.bus):
                forbidden.add((f.can_id, bytes(f.data[:8])))
        hit = [x for x in _sent(link) if x in forbidden]
        assert not hit, f"조향축으로 브링업이 나갔다: {[(hex(i), d.hex()) for i, d in hit]}"
    finally:
        be.shutdown()


def test_no_bringup_when_disabled():
    """`allow_bringup=False`(코드 기본값)면 보내지 않는다 — 플래그가 실제로 산다."""
    link, be = _make(allow_bringup=False)
    be.start()
    try:
        sent = _sent(link)
        hit = [x for x in _distinctive(be.cfg) if x in sent]
        assert not hit, f"비활성인데 브링업이 나갔다: {[(hex(i), d.hex()) for i, d in hit]}"
    finally:
        be.shutdown()


def test_bringup_matches_direct_backend_bytes():
    """UI 직결 경로와 **같은 바이트**인가.

    두 백엔드가 갈라지면 「UI 는 같은데 백엔드만 다르다」는 비교 기준이 무너진다.
    양쪽 다 `protocol.drive_init_frames` 를 쓰므로 출처가 하나여야 한다.
    """
    from can_relay.ui.backend_direct import DRIVE_NODES, MOTOR_BUS

    link, be = _make(allow_bringup=True)
    try:
        assert tuple(be.cfg.drive_nodes) == tuple(DRIVE_NODES), (
            f"구동 노드가 다르다: relay={tuple(be.cfg.drive_nodes)} direct={tuple(DRIVE_NODES)}")
        assert be.cfg.bus == MOTOR_BUS, f"버스가 다르다: relay={be.cfg.bus} direct={MOTOR_BUS}"
    finally:
        pass


def test_start_requires_authority_before_bringup():
    """제어권 없이는 브링업도 나가지 않는다 — 순서가 곧 안전이다."""
    link = MockLink()
    link.open()                      # acquire 하지 않는다
    be = RelayBackend(link, RelayConfig(allow_bringup=True))
    with pytest.raises(RuntimeError):
        be.start()
    assert not _sent(link), f"제어권 없이 프레임이 나갔다: {len(_sent(link))} 장"
