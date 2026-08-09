"""구동축 운전 가능(CiA402) 회귀 — **지령만으로는 바퀴가 돌지 않는다.**

## 무엇이 문제였나

2026-07-29 실기에서 조그를 눌러도 구동륜이 돌지 않았다. 로그는 정상으로 보였고
(`조향 정착 — 구동 raw=-1222`) 재송신도 돌고 있었다. 그런데 `0x60FF=-1222` 를 3 초 넣는
동안 **두 구동축 엔코더가 1 count 도 안 움직였다** — node1 `-516,397` 고정 / node2
`222,376` 고정.

원인은 지령이 아니라 **상태**였다:

- 양 구동축 `operation enabled`(상태워드 bit2) = 0
- node1 은 `0x603F = 0x0080` **Motor overload alarm**(Handbook §6.6.4 p.7614)
- Seer 알람 `Motor Error:FrontWalk-0x80` 이 독립 경로로 같은 것을 보고했다

**재송신은 이 상황을 못 고친다.** 지령을 반복할 뿐 꺼진 축을 켜지 못한다. 그리고 GUI 에는
되살릴 수단이 없었다 — `_drive()` 는 `0x60FF` 만 보내고 조향(`_steer_axis`)처럼 `0x6040` 을
동반하지 않는다. 그동안은 Seer 가 켜 둔 상태를 물려받아 동작했을 뿐이다.

시퀀스 근거: Handbook §6.6.1 Controlword(0x6040) 명령표 —
Bit0 Switch on · Bit1 Enable voltage · Bit2 Quick stop · Bit3 Enable Operation · Bit7 Fault Reset.
Shutdown `0x06` → Switch On `0x07` → Enable Operation `0x0F`, Fault Reset 은 bit7 상승엣지.

**Qt 창을 열지 않는다** — `test_safe_release.py` 와 같이 duck-typed 스텁에 비결합 호출
(`gui.MainWindow._enable_drives(stub)`)로 검증한다. 실기 전용 도구이므로 시험이 하드웨어를
만져서는 안 된다.
"""
from __future__ import annotations

import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import gui  # noqa: E402

ENABLED = gui.SW_OPERATION_ENABLED
FAULTED = gui.SW_FAULT


class _Stub:
    """`_enable_drives` 계열이 만지는 속성만 갖춘 최소 MainWindow 대역."""

    FAULT_CLEAR_S = gui.MainWindow.FAULT_CLEAR_S

    def __init__(self, status=None):
        self._status = dict(status or {})
        self._run = True
        self._jog_stop = False
        self._drive_units = 0
        self.sent: list[tuple] = []
        self.logs: list[str] = []
        self.log_line = type("S", (), {"emit": lambda _s, m: self.logs.append(m)})()

    def _sdo_write(self, node, idx, val, size, sub=0):
        self.sent.append((node, idx, val))

    def _drive(self, units):
        self._drive_units = int(units)
        for n in gui.DRIVE_NODES:
            self._sdo_write(n, 0x60FF, int(units), 4)

    # 비결합 호출로 실제 구현을 빌려 쓴다 — 스텁이 로직을 흉내내지 않게 한다.
    def _drives_ready(self):
        return gui.MainWindow._drives_ready(self)

    def _drive_faults(self):
        return gui.MainWindow._drive_faults(self)


def _cw(stub, node):
    """그 노드로 나간 컨트롤워드(0x6040) 값 순서."""
    return [v for n, idx, v in stub.sent if n == node and idx == 0x6040]


def _enable(stub, **kw):
    return gui.MainWindow._enable_drives(stub, **kw)


# ── 상태 판정 ──────────────────────────────────────────────────────────────
def test_ready_reports_operation_enabled_bit():
    s = _Stub({1: ENABLED, 2: 0})
    assert s._drives_ready() == {1: True, 2: False}


def test_ready_is_none_before_any_statusword():
    assert _Stub()._drives_ready() == {1: None, 2: None}


def test_faults_report_bit3():
    assert _Stub({1: FAULTED, 2: ENABLED})._drive_faults() == {1: True, 2: False}


# ── enable 시퀀스 (Handbook §6.6.1) ────────────────────────────────────────
def test_enable_sends_shutdown_switchon_enable_in_order():
    s = _Stub({1: 0, 2: 0})
    _enable(s, timeout=0.2)
    for n in gui.DRIVE_NODES:
        assert _cw(s, n) == list(gui.DRIVE_ENABLE_SEQ), f"node{n} 시퀀스가 다르다"
    assert list(gui.DRIVE_ENABLE_SEQ) == [0x06, 0x07, 0x0F]


def test_fault_reset_uses_a_rising_edge_before_the_sequence():
    """bit7 을 0 으로 내렸다 1 로 올려야 fault 가 지워진다 — 계속 1 이면 엣지가 없다."""
    s = _Stub({1: FAULTED, 2: 0})

    def clears():
        time.sleep(0.1)
        s._status[1] = 0
    threading.Thread(target=clears, daemon=True).start()
    _enable(s, timeout=0.3)
    assert _cw(s, 1)[:3] == [0x00, 0x80, 0x00], f"fault reset 엣지가 없다: {_cw(s, 1)}"
    assert _cw(s, 1)[3:] == list(gui.DRIVE_ENABLE_SEQ)
    assert _cw(s, 2) == list(gui.DRIVE_ENABLE_SEQ), "fault 없는 축엔 리셋을 보내지 않는다"


def test_enable_waits_for_fault_to_clear_before_transitions():
    """fault 가 걷히기 전에 Shutdown 을 보내면 드라이브가 무시하고 멈춘다.

    2026-07-29 실기: 리셋 직후 50 ms 간격으로 `0x06`/`0x07`/`0x0F` 를 몰아 보냈더니
    node1 이 fault 만 걷히고 `Switch On Disabled`(`0x8050`)에 머물렀다.
    """
    s = _Stub({1: FAULTED, 2: 0})
    s.FAULT_CLEAR_S = 0.3
    assert _enable(s, timeout=0.3) is False
    assert _cw(s, 1) == [0x00, 0x80, 0x00], "fault 중인데 전이 시퀀스가 나갔다"
    assert _cw(s, 2) == [], "fault 대기 중 다른 축에도 전이가 나가면 안 된다"


def test_enable_returns_true_when_both_axes_come_up():
    s = _Stub({1: 0, 2: 0})

    def poll():
        time.sleep(0.1)
        s._status.update({1: ENABLED, 2: ENABLED})
    threading.Thread(target=poll, daemon=True).start()
    assert _enable(s, timeout=2.0) is True


def test_enable_returns_false_when_an_axis_stays_down():
    assert _enable(_Stub({1: ENABLED, 2: 0}), timeout=0.3) is False


# ── 제어권 획득 시 자동 복구 ───────────────────────────────────────────────
# Seer 에 제어권을 넘겼다 되찾으면 구동축이 Switch On Disabled 로 떨어져 있다.
# 잡는 쪽이 필요한 상태를 갖춰야 하므로 획득 직후 점검·복구한다.
def _ensure(stub, **kw):
    gui.MainWindow._ensure_drives_enabled(stub, **kw)


def test_ensure_enables_when_axis_is_down_without_fault():
    s = _Stub({1: 0, 2: ENABLED})
    s._enable_drives = lambda **kw: gui.MainWindow._enable_drives(s, **kw)
    _ensure(s, delay=0.02)
    time.sleep(0.5)
    assert _cw(s, 1) == list(gui.DRIVE_ENABLE_SEQ), "떨어진 축을 자동으로 살리지 않았다"


def test_ensure_does_nothing_when_both_axes_are_up():
    s = _Stub({1: ENABLED, 2: ENABLED})
    s._enable_drives = lambda **kw: gui.MainWindow._enable_drives(s, **kw)
    _ensure(s, delay=0.02)
    time.sleep(0.3)
    assert s.sent == [], "이미 운전 가능한데 프레임이 나갔다"


def test_ensure_refuses_to_auto_enable_a_faulted_axis():
    """fault 가 있으면 **자동으로 켜지 않는다** — 원인 모른 채 재기동 금지."""
    s = _Stub({1: FAULTED, 2: ENABLED})
    s._enable_drives = lambda **kw: gui.MainWindow._enable_drives(s, **kw)
    _ensure(s, delay=0.02)
    time.sleep(0.3)
    assert s.sent == [], "fault 축을 자동으로 켰다"
    assert any("자동 활성화하지 않습니다" in m for m in s.logs), f"사유 미고지: {s.logs}"
