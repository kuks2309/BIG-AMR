"""`DirectBackend` 가 **제어권 획득 경로에서** 구동축 브링업을 보내는가 (debt-045).

## 왜 이 시험이 필요한가

2026-08-08 실기에서 `can_relay` **프로세스 재시작** 뒤 구동축이 `0x60FF` 를 받고도 돌지 않는
상태가 재현됐다. 브링업 시퀀스를 보내자 복귀했다. 그 수정이 `RelayBackend` **한쪽에만** 들어가
UI 직결 경로(`DirectBackend`)는 같은 고장이 그대로 재현되는 상태로 남았다(`debt-045`).

## 왜 `_write_bringup()` 을 직접 부르지 않는가

핸들러를 직접 부르면 **배선을 지나가지 않는다.** `set_engaged` 에서 호출을 지워도 시험이
통과해 버린다 — 2026-08-04 의 실패(`claude-mistake/2026-08-04-001`)가 정확히 그 형태였다.
그래서 여기서는 **가짜 판다로 `set_engaged(True)` 를 끝까지 돌리고** 프레임을 관찰한다.

## 검출력

`set_engaged` 의 `self._write_bringup()` 한 줄을 지우면 `test_engage_sends_drive_bringup` 이
실패한다. 통과 숫자가 아니라 이 사실이 커버리지의 근거다 — 돌연변이 확인으로 증명한다.
"""
import threading

import time

import pytest

from can_relay import protocol as P
import can_relay.ui.backend_direct as bd
from can_relay.ui.backend_direct import (DRIVE_NODES, MOTOR_BUS, STEER_NODES,
                                         DirectBackend)


class _FakeHandle:
    def __init__(self):
        self.ctrl = []

    def controlWrite(self, req_type, req, val, idx, data):  # noqa: N802 (판다 API 이름)
        self.ctrl.append((req, val))


class _FakePanda:
    """`set_engaged` 가 부르는 것만 흉내낸다. 버스로 나가는 프레임을 모은다."""

    REQUEST_OUT = 0x40

    def __init__(self):
        self._handle = _FakeHandle()
        self.frames = []
        self.safety = None
        self.speeds = {}
        self.enabled = {}

    def set_safety_mode(self, mode, param):
        self.safety = (mode, param)

    def set_can_speed_kbps(self, bus, kbps):
        self.speeds[bus] = kbps

    def set_can_enable(self, bus, on):
        self.enabled[bus] = on

    def can_send(self, can_id, data, bus):
        self.frames.append((can_id, bytes(data), bus))

    def can_recv(self):
        """폴 루프가 매 회전 부른다. **유효한 SDO 응답 1개를 돌려준다.**

        빈 리스트를 돌려주면 `_rx_at` 이 영영 갱신되지 않아 **RX 워치독(1.0 s)이 먼저
        발화**한다. 그러면 「지령 워치독이 구동을 0 으로 만들었다」는 시험이 실제로는
        RX 워치독 때문에 통과한다 — 지령 워치독을 통째로 지워도 초록이 뜬다(실측 확인).
        두 워치독을 분리해서 보려면 수신은 살아 있어야 한다.

        ⚠ 이 메서드가 **없어서 폴 스레드가 첫 회전에서 조용히 죽고 있었다** —
          `_loop` 의 `except Exception` 이 `AttributeError` 를 삼켜 `_run=False` 로 내리는데
          `set_engaged` 는 이미 `(True, …)` 를 반환한 뒤라 아무도 알아채지 못했다.
          그래서 「가짜 판다로 set_engaged 를 끝까지 돌린다」는 주장의 실제 범위는
          **폴 루프 1회전의 앞부분까지**였고 재송신·워치독·흡수는 한 번도 실행되지 않았다.
        """
        return [(0x581, 0, bytes([0x43, 0x64, 0x60, 0x00, 0, 0, 0, 0]), MOTOR_BUS)]


@pytest.fixture()
def engaged_backend():
    """`set_engaged(True)` 를 끝까지 돌린 뒤 폴 스레드를 정리한다."""
    be = DirectBackend()
    fake = _FakePanda()
    be.panda = fake
    be._cls = _FakePanda          # `P_ = self._cls` 가 REQUEST_OUT 을 읽는다
    ok, msg = be.set_engaged(True)
    assert ok, msg
    time.sleep(0.3)
    assert be._run is True, f"폴 스레드가 죽었다 — 죽은 루프 위의 관찰은 근거가 아니다: {be._log_lines[-1] if getattr(be, '_log_lines', None) else ''}"
    yield be, fake
    be._run = False
    if be._th is not None:
        be._th.join(timeout=2.0)


def _expected_bringup():
    exp = []
    for n in DRIVE_NODES:
        for f in P.drive_init_frames(n, MOTOR_BUS):
            exp.append((f.can_id, bytes(f.data[:8]), f.bus))
    return exp


def test_engage_sends_drive_bringup(engaged_backend):
    """제어권 획득 시 구동축 브링업 프레임이 **전부** 나갔는가."""
    _be, fake = engaged_backend
    for item in _expected_bringup():
        assert item in fake.frames, (
            f"브링업 프레임 누락: id=0x{item[0]:X} data={item[1].hex()} bus={item[2]}. "
            f"이것이 없으면 프로세스 재시작 뒤 구동축이 0x60FF 를 받고도 돌지 않는다(debt-045).")


def test_bringup_is_first_and_in_order(engaged_backend):
    """브링업이 **폴 루프보다 먼저**, 정해진 순서로 나가는가.

    ⚠ 종전 이름은 `..._matches_relay_backend_bytes` 였고 docstring 은 「`RelayBackend` 와
      같은 바이트」라고 주장했지만, 이 함수는 `RelayBackend` 를 import 도 인스턴스화도 하지
      않는다 — `protocol.drive_init_frames` 를 자기 자신과 비교할 뿐이다. 두 경로가 **같은
      출처 함수**를 쓴다는 것이 실제로 보증되는 범위이고, 그것은 별도 시험이 본다.
      여기서 보는 것은 **순서**다: 브링업은 폴 스레드가 뜨기 전에 끝나야 한다.
      (제어권을 쥔 직후 fault reset 이 폴 루프의 재송신과 뒤섞이면 순서가 비결정이 된다.)
    """
    _be, fake = engaged_backend
    exp = _expected_bringup()
    head = fake.frames[:len(exp)]
    assert head == exp, (
        "브링업이 맨 앞에 순서대로 나가지 않았다 — 폴 루프가 먼저 돌았거나 내용이 바뀌었다.\n"
        f"기대 {[hex(f[0]) for f in exp]}\n실제 {[hex(f[0]) for f in head]}")


def test_bringup_excludes_steer_axes(engaged_backend):
    """조향축에는 보내지 않는가.

    2026-08-08 실기: 조향축까지 브링업을 보냈더니 fault reset 이 위치 카운터를 지워
    **조향 0° 기준이 무효**가 됐고, 그 상태의 「0° 로 가라」 지령에 전륜이 실제로 움직였다.
    조향 기준 복구는 호밍 소관이며 브링업이 대신할 수 있는 일이 아니다.
    """
    _be, fake = engaged_backend
    # ⚠ 「조향축으로 나간 모든 프레임」을 보면 안 된다 — 폴 루프가 조향축의 0x6064·0x606C·
    #   0x6078·0x6041 을 **읽는다**(SDO upload, 명령 바이트 0x40). 그것은 정상 동작이다.
    #   판정 대상은 **브링업 쓰기**뿐이므로, 조향축에 대한 브링업 프레임을 그대로 만들어 대조한다.
    forbidden = set()
    for n in STEER_NODES:
        for f in P.drive_init_frames(n, MOTOR_BUS):
            forbidden.add((f.can_id, bytes(f.data[:8]), f.bus))
    sent = [f for f in fake.frames if f in forbidden]
    assert not sent, (
        f"조향축으로 브링업이 나갔다: {[(hex(i), d.hex()) for i, d, _b in sent]}")


def test_bringup_before_poll_thread(engaged_backend):
    """폴 스레드 시작 **전**에 보내는가 — `RelayBackend.start()` 와 같은 순서.

    순서가 뒤바뀌면 심박·재송신이 브링업보다 먼저 나가 드라이브 상태 전이와 겹칠 수 있다.
    """
    be, fake = engaged_backend
    assert isinstance(be._th, threading.Thread)
    exp_first = _expected_bringup()[0]
    assert exp_first in fake.frames
    # 브링업 첫 프레임이 폴 루프의 첫 SDO 읽기(0x6064)보다 앞서야 한다.
    idx_bringup = fake.frames.index(exp_first)
    read_ids = [i for i, (cid, data, _b) in enumerate(fake.frames)
                if data[:1] == b"\x40"]          # 0x40 = SDO upload(read) 요청
    if read_ids:
        assert idx_bringup < read_ids[0], "브링업이 폴 루프의 읽기보다 뒤에 나갔다"


# ── 지령 워치독 ──────────────────────────────────────────────────────────────
def test_command_watchdog_zeroes_drive_when_commands_stop(engaged_backend):
    """새 지령이 끊기면 구동을 0 으로 수렴시킨다.

    DirectBackend 에는 RX 워치독뿐이라, 드라이브가 응답을 잘 주는 한 마지막 구동 지령이
    **영구히 재송신**됐다. 조그 스레드가 예외로 죽거나 Qt 메인 스레드가 블록되면 아무도
    새 지령을 내지 않는데 로봇은 계속 주행한다 — 남는 정지 수단이 하드웨어 E-STOP 뿐이다.
    `RelayBackend` 는 `cmd_timeout_s=0.3` 으로 같은 일을 한다.
    """
    be, _fake = engaged_backend
    be.drive(100.0)
    assert be._drive_units != 0, "지령이 반영되지 않았다"

    # TTL 안에서는 유지돼야 한다(성급한 0 화는 주행을 끊는다)
    time.sleep(bd.CMD_TTL_S * 0.4)
    assert be._drive_units != 0, "TTL 이 지나지 않았는데 0 이 됐다"

    # TTL 을 넘기면 0 으로 수렴한다
    deadline = time.monotonic() + bd.CMD_TTL_S + 2.0
    while time.monotonic() < deadline and be._drive_units != 0:
        time.sleep(0.05)
    assert be._drive_units == 0, "새 지령이 끊겼는데 구동 지령이 살아 있다"


def test_rx_watchdog_is_armed_at_engage(engaged_backend):
    """`_rx_at` 이 engage 시점에 무장된다.

    초기값 0.0 은 falsy 라 워치독 조건의 첫 항이 계속 거짓이었다 — 응답을 **한 번도**
    못 받으면(송신은 되고 수신만 죽은 경우) 워치독이 영원히 잠든 채 구동 지령만 나갔다.
    """
    be, _fake = engaged_backend
    assert be._rx_at > 0.0, "engage 했는데 RX 워치독이 무장되지 않았다"
