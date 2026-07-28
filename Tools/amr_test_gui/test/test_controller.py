"""AmrTestController 통합 테스트 (SimBus dry-run) — 하드웨어 무접촉.

정본 `TongyiSdoBackend` 를 실제로 브링업·구동하므로, 컨트롤러가 만든 지령이
**CAN 프레임 수준에서** 실측 정본과 일치하는지(조향 counts 항등, 구동 raw 부호) 검증한다.
"""
import os
import sys
import time

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..")))

from amr_test_gui import modes as M                                    # noqa: E402
from amr_test_gui.constants import (COUNTS_PER_DEG, STEER_HOME_COUNTS,  # noqa: E402
                                    VEL_MAX_UNITS, VEL_PER_MMPS)
from amr_test_gui.controller import AmrTestController                  # noqa: E402
from amr_test_gui.motor_control_import import NodeSilent               # noqa: E402
from amr_test_gui.sim_bus import SimBus                                # noqa: E402


def make(**bus_kw):
    """빠른 조향(2000 °/s)으로 램프를 실시간 대기 없이 돌리는 dry-run 컨트롤러."""
    logs = []
    c = AmrTestController(logger=logs.append)
    bus_kw.setdefault("steer_rate_dps", 2000.0)
    bus = {}
    c.connect(lambda: bus.setdefault("b", SimBus(logger=logs.append, **bus_kw)))
    return c, bus["b"], logs


def run_until(c, pred, timeout_s=8.0, dt=0.02):
    """조건 충족까지 tick. 마지막 상태를 반환한다."""
    t0 = time.monotonic()
    st = c.tick()
    while not pred(st) and time.monotonic() - t0 < timeout_s:
        time.sleep(dt)
        st = c.tick()
    return st


def propagate(c, secs=0.3):
    """backend TX 루프(50 Hz)가 지령을 실제 프레임으로 내보낼 때까지 tick 을 유지한다."""
    t0 = time.monotonic()
    st = c.tick()
    while time.monotonic() - t0 < secs:
        time.sleep(0.02)
        st = c.tick()
    return st


def settled(st):
    return st["ramp_state"] == "SETTLED"


def faulted(st):
    return st["ramp_state"] == "FAULT"


# ── 수명주기 ────────────────────────────────────────────────────────────────
def test_connect_and_disconnect():
    c, bus, _ = make()
    assert c.connected
    c.disconnect()
    assert not c.connected
    c.disconnect()          # 중복 호출 무해


def test_double_connect_rejected():
    c, _, _ = make()
    try:
        with pytest.raises(RuntimeError):
            c.connect(lambda: SimBus())
    finally:
        c.disconnect()


def test_bringup_failure_releases_bus():
    """브링업 실패(무응답 노드) 시 버스가 반드시 정리되어야 한다 — 제어권 방치 금지."""
    closed = []
    bus = SimBus(silent_nodes=(4,), logger=lambda *_: None)
    bus.shutdown = lambda: closed.append(True)
    c = AmrTestController(logger=lambda *_: None)
    with pytest.raises(NodeSilent):
        c.connect(lambda: bus)
    assert closed, "브링업 실패인데 버스가 release 되지 않았다"
    assert not c.connected


# ── 조향 counts 항등 (ADR §3 부호 투명 전송) ────────────────────────────────
@pytest.mark.parametrize("mode_key,deg", [("crab_left", 90.0), ("home", 0.0)])
def test_steer_counts_identity(mode_key, deg):
    """송신된 0x607A 목표가 `steer_home + deg×57344` 와 정확히 일치해야 한다."""
    c, bus, _ = make()
    try:
        c.set_mode(mode_key)
        st = run_until(c, settled)
        assert settled(st), st["ramp_detail"]
        for n in (3, 4):
            expect = STEER_HOME_COUNTS[n] + int(deg * COUNTS_PER_DEG)
            assert bus._steer_target[n] == expect, f"node{n} counts 불일치"
    finally:
        c.disconnect()


def test_negative_steer_also_reaches_target():
    c, bus, _ = make()
    try:
        c.set_mode("steer_only")
        c.set_steer_slider_deg(-90.0)
        st = run_until(c, settled)
        assert settled(st) and st["ramp_cmd_deg"] == pytest.approx(-90.0)
        for n in (3, 4):
            assert bus._steer_target[n] == STEER_HOME_COUNTS[n] - int(90 * COUNTS_PER_DEG)
    finally:
        c.disconnect()


# ── 구동 raw 부호 = modes.py 인용 테이블 ────────────────────────────────────
@pytest.mark.parametrize("mode_key,expect_sign", [
    ("forward", -1),      # docking_drive.py:93 '전진=음(실측)'
    ("backward", +1),
    ("crab_left", +1),    # 2026-07-27 실측 (조향+90° + raw 양수 → 왼쪽)
    ("crab_right", -1),
])
def test_raw_sign_follows_cited_mode_table(mode_key, expect_sign):
    c, bus, _ = make()
    try:
        c.set_speed_mmps(50.0)
        c.set_mode(mode_key)
        st = run_until(c, settled)
        assert settled(st), st["ramp_detail"]
        st = propagate(c)
        assert st["raw_units"] == expect_sign * int(round(50.0 * VEL_PER_MMPS))
        for n in (1, 2):
            assert bus._vel[n] == st["raw_units"], "backend 가 부호를 변형했다(항등 전송 위반)"
    finally:
        c.disconnect()


def test_speed_saturates_at_vel_max():
    c, _, _ = make()
    try:
        c.set_speed_mmps(10_000.0)
        c.set_mode("forward")
        st = run_until(c, settled)
        assert abs(st["raw_units"]) == VEL_MAX_UNITS
    finally:
        c.disconnect()


# ── 구동 게이트 ─────────────────────────────────────────────────────────────
def test_drive_is_zero_while_ramping():
    """정착 전에는 어떤 tick 에서도 raw 가 0 이어야 한다."""
    c, _, _ = make(steer_rate_dps=30.0)      # 느린 조향 → 램프 구간을 길게 관측
    try:
        c.set_speed_mmps(50.0)
        c.set_mode("crab_left")
        t0 = time.monotonic()
        while time.monotonic() - t0 < 3.0:
            st = c.tick()
            if st["ramp_state"] != "SETTLED":
                assert st["raw_units"] == 0, "정착 전에 구동 raw 가 나갔다"
            time.sleep(0.02)
    finally:
        c.disconnect()


def test_estop_zeroes_drive_even_when_settled():
    c, bus, _ = make()
    try:
        c.set_speed_mmps(50.0)
        c.set_mode("forward")
        st = run_until(c, settled)
        assert st["raw_units"] != 0
        c.estop(True)
        st = propagate(c)
        assert st["raw_units"] == 0 and st["estop"]
        for n in (1, 2):
            assert bus._vel[n] == 0
    finally:
        c.disconnect()


def test_stop_mode_zeroes_drive():
    c, _, _ = make()
    try:
        c.set_speed_mmps(50.0)
        c.set_mode("forward")
        run_until(c, settled)
        c.set_mode("stop")
        st = run_until(c, lambda s: s["raw_units"] == 0)
        assert st["raw_units"] == 0
    finally:
        c.disconnect()


# ── FAULT 경로 (2026-07-27 node4 사고 재현) ─────────────────────────────────
def test_stuck_steer_node_faults_and_homes():
    """node4 가 지령을 안 따라오면 FAULT → 그 축 즉시 홈 · 구동 금지 (사고 유형 회귀 방지)."""
    c, bus, _ = make(steer_rate_dps=2000.0)
    try:
        c.set_speed_mmps(50.0)
        bus.set_stuck(4, True)               # RearSteer 고착
        c.set_mode("crab_left")
        st = run_until(c, faulted, timeout_s=12.0)
        assert faulted(st), f"고착 노드인데 FAULT 가 나지 않았다: {st['ramp_detail']}"
        assert st["per_axis"][4]["cmd"] == 0.0, "FAULT 축이 홈으로 강제되지 않았다"
        assert st["raw_units"] == 0 and not st["drive_allowed"]
        assert "N4" in st["ramp_detail"], "어느 축이 문제인지 표시되지 않았다"
        # 래치 확인: 고착을 풀어도 reset 전까지 FAULT 유지
        bus.set_stuck(4, False)
        assert faulted(c.tick())
        c.reset_fault()
        assert c.tick()["ramp_state"] != "FAULT"
    finally:
        c.disconnect()


def test_fault_on_one_axis_sends_the_other_axis_home():
    """한 축이 FAULT 면 정상 축도 홈으로 되돌린다 — 검증된 적 없는 비대칭 자세로 방치 금지."""
    c, bus, _ = make(steer_rate_dps=2000.0)
    try:
        bus.set_stuck(4, True)
        c.set_mode("steer_only")
        c.set_steer_slider_deg(60.0)
        st = run_until(c, faulted, timeout_s=12.0)
        assert faulted(st)
        assert c.ramps[3].target_deg == 0.0, "정상 축(N3) 목표가 홈으로 되돌려지지 않았다"
        st = run_until(c, lambda s: abs(s["per_axis"][3]["cmd"]) < 1e-9, timeout_s=8.0)
        assert abs(st["per_axis"][3]["cmd"]) < 1e-9, "정상 축이 홈에 도달하지 않았다"
    finally:
        c.disconnect()


def test_stuck_axis_does_not_advance_and_drive_stays_zero():
    """고착 축은 다음 단계로 전진하지 못하고, 그 동안 구동은 계속 0 이어야 한다.

    축별 램프로 바뀌면서 '정상 축이 먼저 진행'하는 것은 정상이다. 지켜야 할 불변식은
    ① 고착 축의 지령이 첫 단계를 넘지 않는다 ② 양 축이 다 정착하기 전엔 구동 raw = 0.
    """
    c, bus, _ = make(steer_rate_dps=2000.0)
    try:
        c.set_speed_mmps(50.0)
        bus.set_stuck(4, True)
        c.set_mode("steer_only")
        c.set_steer_slider_deg(60.0)
        t0 = time.monotonic()
        while time.monotonic() - t0 < 2.0:
            st = c.tick()
            assert abs(st["per_axis"][4]["cmd"]) <= 30.0 + 1e-9, \
                "고착 축이 다음 단계로 전진했다"
            assert st["raw_units"] == 0, "한 축이 미정착인데 구동 raw 가 나갔다"
            time.sleep(0.02)
    finally:
        c.disconnect()


# ── 상태 표면 ───────────────────────────────────────────────────────────────
def test_status_exposes_all_nodes_with_roles():
    c, _, _ = make()
    try:
        st = run_until(c, lambda s: len(s["nodes"]) == 4)
        assert [r["node"] for r in st["nodes"]] == [1, 2, 3, 4]
        assert st["nodes"][2]["role"].startswith("FrontSteer")
        assert st["nodes"][2]["deg"] is not None      # 조향은 각도 환산 제공
        assert st["nodes"][0]["deg"] is None          # 구동은 각도 없음
        assert st["tx"] > 0 and st["rx"] > 0
    finally:
        c.disconnect()


def test_mode_basis_is_cited_for_every_mode():
    """모든 모드가 부호 근거를 문자열로 보유해야 한다(추측 금지 규칙의 코드 표현)."""
    for m in M.ALL_MODES:
        assert m.basis and len(m.basis) > 5, f"{m.key} 에 근거 인용이 없다"


def test_direct_measured_modes_cite_their_measurement():
    """직접 실측에 뿌리를 둔 모드는 근거에 '실측' 이 명시돼야 한다."""
    for key in ("forward", "crab_left"):
        assert "실측" in M.BY_KEY[key].basis


def test_crab_and_forward_share_one_motor_polarity():
    """crab 은 조향 자세만 다르고 모터 극성은 전진/후진과 같은 축에 있다.

    전진(raw −) 과 crab_left(raw +) 가 반대 부호인 것은, 조향 +90° counts 가 CW(−θ)라는
    해석 하에서 정합한다(ADR §부호 정합). 부호가 같아지면 그 해석이 깨진 것이므로 회귀로 잡는다.
    """
    assert M.FORWARD.raw_sign == -M.BACKWARD.raw_sign
    assert M.CRAB_LEFT.raw_sign == -M.CRAB_RIGHT.raw_sign
    assert M.CRAB_LEFT.steer_deg == M.CRAB_RIGHT.steer_deg == 90.0
    assert M.FORWARD.steer_deg == M.BACKWARD.steer_deg == 0.0
