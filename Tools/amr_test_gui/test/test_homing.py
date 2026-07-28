"""조향 원점 복귀(호밍) 회귀 — CAN 프레임과 완료 판정을 하드웨어 없이 고정한다.

호밍은 **로봇을 크게 움직이는** 지령이라(`0x60FB:04=1`) 프레임이 틀리면 실기에서
확인된다. 그래서 송신 바이트를 여기서 못박는다. `_sdo_write` 만 가짜로 바꾸므로
CAN 도 판다도 열리지 않는다.

고정하는 사실:
  · 조향 노드 3·4 에만 나간다 — 구동 노드(1·2)는 기계적 원점이 없어 호밍하지 않는다.
  · `0x6098`(homing method)은 절대 쓰지 않는다 — 덮어쓰면 리셋 모드가 꺼진다.
  · 트리거는 서브인덱스 4 다(`0x60FB:04`). 서브인덱스가 0 으로 나가면 다른 객체가 된다.
  · 완료 판정은 bit15 의 **0→1 전이**다. 1 만 보면 이미 호밍된 축을 즉시 완료로 오독한다.
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
import tongyi_can  # noqa: E402

BIT15 = 1 << 15


@pytest.fixture(scope="module")
def app():
    yield QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def win(app):
    w = gui.MainWindow()
    w.can.HOMING_START_S = 1.0      # 테스트를 초 단위로 유지
    w.can.HOMING_TIMEOUT_S = 3.0
    yield w
    w._seer_run = False
    w.can.running = False
    w.can.homing = False


@pytest.fixture
def sent(win, monkeypatch):
    """`sdo_write` 를 가로채 (node, idx, val, size, sub) 로 기록한다."""
    log = []
    monkeypatch.setattr(win.can, "sdo_write",
                        lambda node, idx, val, size, sub=0: log.append((node, idx, val, size, sub)))
    return log


# ── SDO 프레임 인코딩 ──────────────────────────────────────────────────────
def test_subindex_lands_in_byte3(win, monkeypatch):
    """서브인덱스는 SDO 프레임의 4번째 바이트다 — 0 으로 나가면 다른 객체를 건드린다."""
    frames = []

    class FakePanda:
        def can_send(self, addr, data, bus):
            frames.append((addr, bytes(data), bus))

    win.can.panda = FakePanda()
    win.can.sdo_write(3, 0x60FB, 1, 1, sub=4)
    addr, data, bus = frames[0]
    assert addr == 0x603                      # 0x600 + node
    assert bus == tongyi_can.MOTOR_BUS
    assert data[0] == 0x2F                    # 1 바이트 expedited 쓰기
    assert (data[1], data[2]) == (0xFB, 0x60)  # 인덱스 리틀엔디안
    assert data[3] == 4                        # ← 서브인덱스
    assert data[4] == 1


def test_default_subindex_is_zero(win, monkeypatch):
    frames = []
    win.can.panda = type("P", (), {"can_send": lambda _s, a, d, b: frames.append(bytes(d))})()
    win.can.sdo_write(3, 0x6099, 2500, 4)
    assert frames[0][3] == 0


# ── 호밍 시퀀스 ────────────────────────────────────────────────────────────
def _run_homing(win, sent, status_script):
    """호밍을 돌리되 상태워드는 스크립트대로 흘려준다."""
    win.can.running = True

    def feed():
        for delay, states in status_script:
            time.sleep(delay)
            win.can._status.update(states)

    t = threading.Thread(target=feed, daemon=True)
    win.can.homing = True
    t.start()
    win.can._homing_run()
    t.join(timeout=2)


def test_sequence_targets_steering_nodes_only(win, sent):
    _run_homing(win, sent, [(0.05, {3: 0, 4: 0}), (0.05, {3: BIT15, 4: BIT15})])
    homing_writes = [f for f in sent if f[1] in (0x6040, 0x6099, 0x60FB)]
    assert {f[0] for f in homing_writes} == {3, 4}, "구동 노드에는 호밍 지령이 가면 안 된다"


def test_homing_method_is_never_written(win, sent):
    """0x6098 을 쓰면 드라이브의 리셋 모드가 꺼져 호밍이 죽는다."""
    _run_homing(win, sent, [(0.05, {3: 0, 4: 0}), (0.05, {3: BIT15, 4: BIT15})])
    assert not [f for f in sent if f[1] == 0x6098]


def test_trigger_uses_subindex_four(win, sent):
    _run_homing(win, sent, [(0.05, {3: 0, 4: 0}), (0.05, {3: BIT15, 4: BIT15})])
    triggers = [f for f in sent if f[1] == 0x60FB]
    assert len(triggers) == 2                       # 노드당 1회뿐
    assert all(sub == 4 and val == 1 for _n, _i, val, _s, sub in triggers)


def test_drive_is_zeroed_before_the_trigger(win, sent):
    """구동이 돌아가는 중에 조향을 원점으로 보내면 안 된다."""
    _run_homing(win, sent, [(0.05, {3: 0, 4: 0}), (0.05, {3: BIT15, 4: BIT15})])
    first_trigger = next(i for i, f in enumerate(sent) if f[1] == 0x60FB)
    drive_zero = [i for i, f in enumerate(sent) if f[1] == 0x60FF and f[2] == 0]
    assert drive_zero and min(drive_zero) < first_trigger


def test_speed_is_sent_before_the_trigger(win, sent):
    _run_homing(win, sent, [(0.05, {3: 0, 4: 0}), (0.05, {3: BIT15, 4: BIT15})])
    for n in (3, 4):
        spd = next(i for i, f in enumerate(sent) if f[0] == n and f[1] == 0x6099)
        trg = next(i for i, f in enumerate(sent) if f[0] == n and f[1] == 0x60FB)
        assert spd < trg
        assert sent[spd][2] == win.can.HOMING_SPEED


# ── 완료 판정 ──────────────────────────────────────────────────────────────
def test_already_homed_axis_is_not_reported_complete(win):
    """시작 전부터 bit15=1 인 축을 즉시 '완료'로 읽으면 안 된다 — 대표 오판."""
    win.can._status = {3: BIT15, 4: BIT15}
    ok, why = win.can.wait_homed()
    assert ok is False
    assert "개시" in why


def test_completion_needs_both_axes(win):
    """한 축만 끝나도 완료가 아니다."""
    win.can._status = {3: 0, 4: 0}

    def feed():
        time.sleep(0.1)
        win.can._status[3] = BIT15      # node4 는 끝내 0 인 채로 둔다
    threading.Thread(target=feed, daemon=True).start()
    ok, _why = win.can.wait_homed()
    assert ok is False


def test_zero_then_one_is_success(win):
    win.can._status = {3: 0, 4: 0}

    def feed():
        time.sleep(0.1)
        win.can._status.update({3: BIT15, 4: BIT15})
    threading.Thread(target=feed, daemon=True).start()
    ok, why = win.can.wait_homed()
    assert ok is True
    assert "소요" in why


# ── 인터록 ────────────────────────────────────────────────────────────────
def test_jog_is_blocked_while_homing_but_stop_is_not(win, monkeypatch):
    win.can.running = True
    win.can.homing = True
    calls = []
    monkeypatch.setattr(win.can, "drive", lambda u: calls.append(u))
    win._jog("전진")
    assert calls == [], "호밍 중 조그가 나가면 안 된다"
    win._jog("정지")
    assert calls == [0], "정지는 호밍 중에도 들어야 한다"


def test_homing_refused_without_authority(win):
    win.can.running = False
    win._homing_clicked()           # 대화상자까지 가지 않고 거부돼야 한다
    assert win.can.homing is False


def test_position_is_not_trusted_while_homing(win):
    """호밍 중 0x6064 는 0 을 돌려준다 — 그대로 쓰면 바퀴 그림이 0° 로 튄다."""
    win.can.homing = True
    win.can._meas_deg = {3: None, 4: None}
    win._on_motor_data({3: {0x6064: 0}, 4: {0x6064: 0}})
    assert win.can._meas_deg == {3: None, 4: None}
    win.can.homing = False
    win._on_motor_data({3: {0x6064: tongyi_can.STEER_HOME[3]}})
    assert win.can._meas_deg[3] == pytest.approx(0.0)
