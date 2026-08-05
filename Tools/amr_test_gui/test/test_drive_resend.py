"""구동 지령 재송신·워치독 — 2026-08-03 리뷰 High ③ 재발 방지.

## 무엇이 문제였나

`_drive()` 가 `0x60FF` 를 **한 번** 보내고 끝이었다. 재송신도 워치독도 없어서
프레임 하나가 유실되면 지령이 통째로 사라지고, 반대로 지령이 들어간 뒤 상황이 바뀌어도
드라이브는 마지막 값을 물고 계속 갔다.

## 여기서 고정하는 것

1. 폴 루프가 마지막 지령을 **매 주기 재송신**한다(0 도 포함 — 정지야말로 유실되면 안 된다).
2. 응답이 `RX_TTL_S` 넘게 없으면 **구동을 0 으로** 내린다(버스 상태를 모르는 채 달리지 않는다).
3. 워치독은 「지령 만료」 방식이 **아니다** — 조그가 스스로 멈추면 안 되기 때문이다.
"""
from __future__ import annotations

import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip("PyQt5.QtWidgets")
import gui  # noqa: E402


class _RecordingPanda:
    """송신 프레임을 기록하는 대역. `can_recv` 는 대본대로 응답을 돌려준다."""

    class _Handle:
        def controlWrite(self, *_a, **_kw):
            return 0

    def __init__(self, replies=True):
        self.sent = []
        self._handle = self._Handle()
        self._replies = replies
        self._lock = threading.Lock()

    def can_send(self, addr, data, bus):
        with self._lock:
            self.sent.append((addr, bytes(data)))

    def can_recv(self):
        if not self._replies:
            return []
        # node3 위치 응답 1건 — 「버스가 살아 있다」 신호
        d = bytes([0x43, 0x64, 0x60, 0x00]) + (7_871_815).to_bytes(4, "little")
        return [(0x583, 0, d, gui.MOTOR_BUS)]

    def writes_to(self, idx):
        with self._lock:
            return [f for f in self.sent
                    if f[1][0] != 0x40 and (f[1][1] | (f[1][2] << 8)) == idx]


@pytest.fixture(scope="module")
def app():
    yield QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def win(app):
    w = gui.MainWindow()
    yield w
    w._run = False
    w._seer_run = False


def _spin(win, panda, secs):
    win.panda = panda
    win._run = True
    th = threading.Thread(target=win._loop, daemon=True)
    th.start()
    time.sleep(secs)
    win._run = False
    th.join(timeout=3.0)


def test_drive_command_is_resent_by_poll_loop(win):
    """단발이 아니라 **주기 재송신**이어야 한다."""
    panda = _RecordingPanda()
    win.panda = panda
    win._drive(1000)                      # 최초 1회 (2 프레임)
    first = len(panda.writes_to(0x60FF))
    assert first == 2
    _spin(win, panda, 0.8)
    assert len(panda.writes_to(0x60FF)) > first + 2, \
        "폴 루프가 구동 지령을 재송신하지 않는다"


def test_zero_is_also_resent(win):
    """정지도 재송신 대상이다 — 유실되면 안 되는 쪽은 오히려 이쪽이다."""
    panda = _RecordingPanda()
    win.panda = panda
    win._drive(1000)
    win._drive(0)
    n0 = len(panda.writes_to(0x60FF))
    _spin(win, panda, 0.6)
    frames = panda.writes_to(0x60FF)
    assert len(frames) > n0 + 2, "정지 지령이 재송신되지 않는다"
    for _addr, data in frames[n0:]:
        assert int.from_bytes(data[4:8], "little", signed=True) == 0, \
            "정지 뒤에 0 이 아닌 지령이 되살아났다"


def test_watchdog_zeroes_drive_when_bus_goes_silent(win, monkeypatch):
    """응답이 끊기면 **구동을 0 으로** 내린다 — 버스 상태를 모르는 채 달리지 않는다."""
    monkeypatch.setattr(gui, "RX_TTL_S", 0.3)
    panda = _RecordingPanda(replies=False)      # 응답 없음
    win.panda = panda
    win._rx_at = time.monotonic()               # 한때 살아 있었다
    win._drive(1000)
    _spin(win, panda, 1.0)
    assert win._drive_units == 0, "응답이 끊겼는데 구동 지령이 남아 있다"
    last = panda.writes_to(0x60FF)[-1]
    assert int.from_bytes(last[1][4:8], "little", signed=True) == 0


def test_watchdog_does_not_expire_a_live_command(win, monkeypatch):
    """응답이 오는 동안에는 조그가 **스스로 멈추면 안 된다**.

    「지령 만료」 방식 워치독을 쓰면 사람이 누른 조그가 0.3초 만에 꺼진다 — 그래서 안 쓴다.
    """
    monkeypatch.setattr(gui, "RX_TTL_S", 0.3)
    panda = _RecordingPanda(replies=True)       # 응답 정상
    win.panda = panda
    win._drive(1000)
    _spin(win, panda, 1.0)
    assert win._drive_units == 1000, "살아 있는 지령이 워치독에 잘렸다"
