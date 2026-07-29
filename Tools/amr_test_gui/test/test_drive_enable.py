"""구동축 운전 가능(CiA402) 회귀 — 지령만으로는 바퀴가 돌지 않는다.

**Qt 창을 열지 않는다** — `TongyiCan` 이 Qt 무의존이라 계층만 떼어 시험한다.

왜 필요한가 (2026-07-29 실기):
  `0x60FF=-1222` 를 3 초 넣었는데 두 구동축 엔코더가 **1 count 도 안 움직였다**
  (node1 -516,397 고정 / node2 222,376 고정). 원인은 지령이 아니라 **상태**였다 —
  양 구동축 `operation enabled`(상태워드 bit2) = 0, node1 은 `0x603F=0x0080`
  Motor overload alarm(Handbook §6.6.4). Seer 알람 `Motor Error:FrontWalk-0x80` 이
  독립 경로로 같은 것을 보고했다.

  그런데 GUI 에는 되살릴 수단이 없었다 — `drive()` 는 `0x60FF` 만 보내고 조향처럼
  `0x6040` 을 동반하지 않는다. 그동안은 Seer 가 켜 둔 상태를 물려받아 동작했을 뿐이다.

시퀀스 근거: Handbook §6.6.1 Controlword(0x6040) 명령표 —
  Bit0 Switch on · Bit1 Enable voltage · Bit2 Quick stop · Bit3 Enable Operation · Bit7 Fault Reset
  Shutdown 0x06 → Switch On 0x07 → Enable Operation 0x0F, Fault Reset 은 bit7 상승엣지.
"""
from __future__ import annotations

import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tongyi_can import (DRIVE_ENABLE_SEQ, SW_FAULT,  # noqa: E402
                        SW_OPERATION_ENABLED, TongyiCan)

ENABLED = SW_OPERATION_ENABLED
FAULTED = SW_FAULT


def _can(status=None):
    can = TongyiCan()
    sent = []
    can.sdo_write = lambda node, idx, val, size, sub=0: sent.append((node, idx, val))
    if status:
        can._status.update(status)
    return can, sent


def _cw(sent, node):
    """그 노드로 나간 컨트롤워드(0x6040) 값 순서."""
    return [v for n, idx, v in sent if n == node and idx == 0x6040]


# ── 상태 판정 ──────────────────────────────────────────────────────────────
def test_ready_reports_operation_enabled_bit():
    can, _ = _can({1: ENABLED, 2: 0})
    assert can.drives_ready() == {1: True, 2: False}


def test_ready_is_none_before_any_statusword():
    can, _ = _can()
    assert can.drives_ready() == {1: None, 2: None}


def test_faults_report_bit3():
    can, _ = _can({1: FAULTED, 2: ENABLED})
    assert can.drive_faults() == {1: True, 2: False}


# ── enable 시퀀스 (Handbook §6.6.1) ────────────────────────────────────────
def test_enable_sends_shutdown_switchon_enable_in_order():
    can, sent = _can({1: 0, 2: 0})
    can.enable_drives(timeout=0.2)
    for n in (1, 2):
        assert _cw(sent, n) == list(DRIVE_ENABLE_SEQ), f"node{n} 시퀀스가 다르다"
    assert list(DRIVE_ENABLE_SEQ) == [0x06, 0x07, 0x0F]


def test_fault_reset_uses_a_rising_edge_before_the_sequence():
    """bit7 을 0 으로 내렸다 1 로 올려야 fault 가 지워진다 — 계속 1 이면 엣지가 없다."""
    can, sent = _can({1: FAULTED, 2: 0})

    def clears():                                  # 리셋을 받고 fault 가 걷힌다
        time.sleep(0.1)
        can._status[1] = 0
    threading.Thread(target=clears, daemon=True).start()
    can.enable_drives(timeout=0.3)
    cw1 = _cw(sent, 1)
    assert cw1[:3] == [0x00, 0x80, 0x00], f"node1 fault reset 엣지가 없다: {cw1}"
    assert cw1[3:] == list(DRIVE_ENABLE_SEQ)
    assert _cw(sent, 2) == list(DRIVE_ENABLE_SEQ), "fault 없는 축엔 리셋을 보내지 않는다"


def test_enable_waits_for_fault_to_clear_before_transitions():
    """fault 가 걷히기 전에 Shutdown 을 보내면 드라이브가 무시하고 멈춘다.

    2026-07-29 실기: 리셋 직후 50 ms 간격으로 0x06/0x07/0x0F 를 몰아 보냈더니 node1 이
    fault 만 걷히고 Switch On Disabled(0x8050)에 머물렀다.
    """
    can, sent = _can({1: FAULTED, 2: 0})
    can.FAULT_CLEAR_S = 0.3
    assert can.enable_drives(timeout=0.3) is False      # fault 가 안 걷히면
    assert _cw(sent, 1) == [0x00, 0x80, 0x00], "fault 중인데 전이 시퀀스가 나갔다"
    assert _cw(sent, 2) == [], "fault 대기 중 다른 축에도 전이가 나가면 안 된다"


def test_enable_returns_true_when_both_axes_come_up():
    can, _sent = _can({1: 0, 2: 0})

    def poll():
        time.sleep(0.1)
        can._status.update({1: ENABLED, 2: ENABLED})

    threading.Thread(target=poll, daemon=True).start()
    assert can.enable_drives(timeout=2.0) is True


def test_enable_returns_false_when_an_axis_stays_down():
    can, _sent = _can({1: ENABLED, 2: 0})
    assert can.enable_drives(timeout=0.3) is False


# ── 조그가 조용히 실패하지 않는가 (핵심 회귀) ──────────────────────────────
def test_jog_refuses_to_drive_when_axes_are_not_enabled():
    """운전 불가 상태에서 구동 지령을 내보내면 안 된다 — 조용히 실패해 원인을 가린다."""
    can, sent = _can({1: 0, 2: 0})
    can._meas_deg = {3: 0.0, 4: 0.0}
    can._meas_at = {3: time.time() + 5, 4: time.time() + 5}   # 정착은 통과시킨다
    logs = []
    can._log_cb = logs.append
    can._jog_run("전진", 0.0, -1, 50.0, 3.0)
    assert not [v for n, idx, v in sent if idx == 0x60FF and v != 0], \
        "운전 불가인데 0 아닌 구동 지령이 나갔다"
    assert any("운전 가능 상태가 아닙니다" in m for m in logs), f"사유를 알리지 않았다: {logs}"


def test_jog_drives_when_axes_are_enabled():
    can, sent = _can({1: ENABLED, 2: ENABLED})
    can._meas_deg = {3: 0.0, 4: 0.0}
    can._meas_at = {3: time.time() + 5, 4: time.time() + 5}
    can._jog_run("전진", 0.0, -1, 50.0, 3.0)
    assert [v for n, idx, v in sent if idx == 0x60FF and v != 0] == [-1222, -1222]


# ── 제어권 획득 시 자동 복구 ───────────────────────────────────────────────
# Seer 에게 넘겼다 되찾으면 구동축이 Switch On Disabled 로 떨어져 있다
# (2026-07-29 실기: 13:24:35 반환 → 13:33:54 재획득 시 node1 enabled=False).
def test_ensure_enables_when_axis_is_down_without_fault():
    can, sent = _can({1: 0, 2: ENABLED})
    can.ensure_drives_enabled(delay=0.02)
    time.sleep(0.4)
    assert _cw(sent, 1) == list(DRIVE_ENABLE_SEQ), "떨어진 축을 자동으로 살리지 않았다"


def test_ensure_does_nothing_when_both_axes_are_up():
    can, sent = _can({1: ENABLED, 2: ENABLED})
    can.ensure_drives_enabled(delay=0.02)
    time.sleep(0.3)
    assert sent == [], "이미 운전 가능한데 프레임이 나갔다"


def test_ensure_refuses_to_auto_enable_a_faulted_axis():
    """fault 가 있으면 **자동으로 켜지 않는다** — 원인 모른 채 재기동 금지."""
    can, sent = _can({1: FAULTED, 2: ENABLED})
    logs = []
    can._log_cb = logs.append
    can.ensure_drives_enabled(delay=0.02)
    time.sleep(0.3)
    assert sent == [], "fault 축을 자동으로 켰다"
    assert any("자동 활성화하지 않습니다" in m for m in logs), f"사유를 안 알렸다: {logs}"
