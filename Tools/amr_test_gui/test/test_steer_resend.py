"""조향 setpoint 재송신 회귀 — 한 축이 첫 지령을 놓쳐도 따라오게 하는 성질.

**Qt 창을 열지 않는다** — `TongyiCan` 이 Qt 무의존이라 계층만 떼어 시험한다.
`sdo_write` 만 가짜로 바꾸므로 CAN 도 판다도 열리지 않는다.

왜 필요한가 (2026-07-29 실기):
  45° 크랩에서 node3 는 −45.000° 에 정확히 도달했는데 node4 는 −0.00003°, 즉 전혀
  움직이지 않았다. 원인은 500여 회 재시도에도 재현되지 않았으나(상태 차이·bit4 엣지·
  폴링 과부하·점프 크기·프레임 유실 전부 반증), **1회 발사 후 확인도 재시도도 없는**
  구조 자체가 결손을 영구화한다. 구 GUI 는 setpoint 를 50 Hz 로 계속 보내 같은 결손이
  20 ms 만에 메워졌다.

  A/B 실측: 한 축에만 −10° 를 넣어 결손을 만든 뒤
    재송신 없음 → 6 s 내내 미복구 (정착 실패)
    재송신 있음 → 0.5 s 만에 양축 정착 (재송신 6회)
"""
from __future__ import annotations

import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tongyi_can import STEER_HOME, TongyiCan, steer_counts  # noqa: E402


def _feed(can, **deg):
    """실제 폴링처럼 `decode_frames` 를 거쳐 실측을 넣는다(신선도 타임스탬프 포함).

    직접 `_meas_deg` 에 써 넣으면 타임스탬프가 없어 낡은 값으로 취급된다 — 그것이
    바로 `wait_settle` 이 막아야 할 상태다.
    """
    can.decode_frames({int(k[1:]): {0x6064: steer_counts(int(k[1:]), v)[1]}
                       for k, v in deg.items()})


def _can():
    """`sdo_write` 를 가로채는 CAN 계층. 반환 `(can, 송신기록)`."""
    can = TongyiCan()
    sent = []
    can.sdo_write = lambda node, idx, val, size, sub=0: sent.append((node, idx, val))
    return can, sent


def _targets(sent, deg):
    """`sent` 안에서 각 조향축에 나간 0x607A(deg) 프레임 수."""
    return {n: sum(1 for node, idx, val in sent
                   if node == n and idx == 0x607A and val == steer_counts(n, deg)[1])
            for n in (3, 4)}


# ── 재송신이 도는가 ────────────────────────────────────────────────────────
def test_setpoint_is_resent_while_not_settled():
    """정착 못 한 동안 setpoint 가 반복해서 나가야 한다."""
    can, sent = _can()
    can._meas_deg = {3: 0.0, 4: 0.0}            # 목표 −10° 에 한참 못 미침
    assert can.wait_settle(-10.0, 3.0, timeout=0.6) is False
    n = _targets(sent, -10.0)
    assert n[3] >= 3 and n[4] >= 3, f"재송신이 부족하다: {n}"


def test_resend_targets_both_steer_axes_every_round():
    """재송신은 **양축 모두**에 나가야 한다 — 뒤처진 축을 메우는 것이 목적이다."""
    can, sent = _can()
    can._meas_deg = {3: 0.0, 4: 0.0}
    can.wait_settle(-10.0, 3.0, timeout=0.6)
    n = _targets(sent, -10.0)
    assert n[3] == n[4], f"축별 재송신 횟수가 다르다: {n}"


def test_each_resend_carries_the_apply_command():
    """0x607A 만 보내면 적용되지 않는다 — 0x6040=0x3F 가 뒤따라야 한다."""
    can, sent = _can()
    can._meas_deg = {3: 0.0, 4: 0.0}
    can.wait_settle(-10.0, 3.0, timeout=0.4)
    for i, (node, idx, _v) in enumerate(sent):
        if idx == 0x607A:
            assert sent[i + 1] == (node, 0x6040, 0x3F), f"node{node} 적용 지령 누락"


# ── 결손 복구 (핵심 회귀) ──────────────────────────────────────────────────
def test_lagging_axis_recovers_and_settles():
    """한 축이 뒤처져 있어도 재송신 뒤 따라오면 정착으로 판정돼야 한다."""
    can, sent = _can()

    def poll():                                  # 폴링이 도는 상황을 흉내낸다
        for _ in range(6):                       # node4 만 첫 지령을 놓친 상태
            _feed(can, n3=-10.0, n4=0.0)
            time.sleep(0.05)
        while True:                              # 재송신을 받고 뒤늦게 따라온다
            _feed(can, n3=-10.0, n4=-10.0)
            time.sleep(0.05)

    threading.Thread(target=poll, daemon=True).start()
    assert can.wait_settle(-10.0, 3.0, timeout=2.0) is True
    assert _targets(sent, -10.0)[4] >= 1, "뒤처진 축에 재송신이 가지 않았다"


def test_without_resend_a_lagging_axis_never_settles():
    """재송신을 끄면 결손이 영구화된다 — 이 대비가 재송신의 존재 이유다."""
    can, sent = _can()
    stop = []

    def poll():
        while not stop:
            _feed(can, n3=-10.0, n4=0.0)         # node4 는 끝내 안 따라온다
            time.sleep(0.05)

    threading.Thread(target=poll, daemon=True).start()
    assert can.wait_settle(-10.0, 3.0, timeout=0.5, resend=False) is False
    stop.append(1)
    assert sent == [], "resend=False 인데 지령이 나갔다"


# ── 멈춰야 할 때 멈추는가 ──────────────────────────────────────────────────
def test_no_resend_once_already_settled():
    """이미 정착해 있으면 한 프레임도 보내지 않는다 — 유휴는 읽기 전용이다."""
    can, sent = _can()
    stop = []

    def poll():
        while not stop:
            _feed(can, n3=-10.0, n4=-10.0)
            time.sleep(0.02)

    threading.Thread(target=poll, daemon=True).start()
    assert can.wait_settle(-10.0, 3.0, timeout=1.0) is True
    stop.append(1)
    assert sent == [], f"정착 상태인데 {len(sent)}프레임이 나갔다"


def test_resend_stops_when_stop_is_pressed():
    """정지가 눌리면 즉시 그만둔다 — 재송신이 정지를 덮어쓰면 안 된다."""
    can, sent = _can()
    can._meas_deg = {3: 0.0, 4: 0.0}
    can._jog_stop = True
    assert can.wait_settle(-10.0, 3.0, timeout=1.0) is False
    assert sent == [], "정지 중에 setpoint 가 나갔다"


def test_resend_uses_clamped_counts():
    """재송신도 ±90° 클램프를 거친 counts 여야 한다 — 우회 경로가 생기면 안 된다."""
    can, sent = _can()
    can._meas_deg = {3: 0.0, 4: 0.0}
    can.wait_settle(137.0, 3.0, timeout=0.4)     # 가동범위 밖
    for n in (3, 4):
        assert all(val == STEER_HOME[n] + 90 * 57344
                   for node, idx, val in sent if node == n and idx == 0x607A)


# ── 신선도 게이트 (거짓 정착 방지) ─────────────────────────────────────────
def test_stale_measurement_never_settles():
    """지령 전 자세가 우연히 목표 근처여도 **새 표본 없이** 통과하면 안 된다.

    실기(2026-07-29): 호밍 탐색 31 s 동안 `0x6064` 표본 1,310/1,312 이 0 이라 전부
    필터되고 `_meas_deg` 가 호밍 **이전** 값(0.00°)으로 남았다. 그 상태에서 0° 복귀
    정착을 물으니 낡은 0.00° 를 보고 즉시 통과했고 — 바퀴는 리밋(−137°)에 있었는데
    "조향 0° 복귀 확인" 이 찍혔다.
    """
    can, sent = _can()
    can._meas_deg = {3: 0.0, 4: 0.0}            # 낡은 값(타임스탬프 없음)
    assert can.wait_settle(0.0, 3.0, timeout=0.5) is False, "낡은 실측으로 정착했다"


def test_measurement_taken_before_the_wait_is_ignored():
    """대기 시작 **이전**에 받은 표본은 인정하지 않는다."""
    can, sent = _can()
    _feed(can, n3=0.0, n4=0.0)                  # 대기 시작 전에 도착
    time.sleep(0.05)
    assert can.wait_settle(0.0, 3.0, timeout=0.4) is False


def test_fresh_measurement_settles():
    """대기 시작 이후 표본이 목표에 들면 정착한다."""
    can, sent = _can()

    def poll():
        time.sleep(0.1)
        _feed(can, n3=0.0, n4=0.0)

    threading.Thread(target=poll, daemon=True).start()
    assert can.wait_settle(0.0, 3.0, timeout=2.0) is True
