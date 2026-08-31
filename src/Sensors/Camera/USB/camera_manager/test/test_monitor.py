# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""CameraMonitor 상태기계 단위 테스트 — 시각 주입으로 결정론 실행."""
import pytest

from camera_manager.monitor import (
    STATE_NO_DEVICE,
    STATE_OK,
    STATE_RESTARTING,
    STATE_STALL,
    STATE_STOPPED,
    STATE_SUPPRESSED,
    STATE_UNKNOWN,
    CameraInputs,
    CameraMonitor,
    MonitorConfig,
)

CFG = MonitorConfig(stall_sec=10.0, restart_cooldown_sec=30.0, startup_grace_sec=20.0)


def _inputs(age=1.0, unit=True, device=True, depth=False):
    return CameraInputs(
        frame_age=age, unit_active=unit, device_present=device, depth_active=depth)


def _monitor(start=0.0):
    return CameraMonitor("cam_t", CFG, start)


def test_fresh_frame_is_ok():
    decision = _monitor().evaluate(_inputs(age=1.0), now=100.0, auto_enabled=True)
    assert decision.state == STATE_OK
    assert decision.restart is False


def test_never_received_within_grace_waits():
    monitor = _monitor(start=0.0)
    decision = monitor.evaluate(_inputs(age=None), now=5.0, auto_enabled=True)
    assert decision.state == STATE_RESTARTING
    assert decision.restart is False


def test_stall_after_grace_triggers_restart():
    monitor = _monitor(start=0.0)
    decision = monitor.evaluate(_inputs(age=15.0), now=25.0, auto_enabled=True)
    assert decision.restart is True
    assert decision.state == STATE_RESTARTING
    assert monitor.consecutive_restarts == 1


def test_restart_reopens_grace_then_cooldown_then_second_restart():
    monitor = _monitor(start=0.0)
    assert monitor.evaluate(_inputs(age=15.0), now=25.0, auto_enabled=True).restart
    # 재시작 직후: 유예(20초) 안 — 관망.
    decision = monitor.evaluate(_inputs(age=None), now=30.0, auto_enabled=True)
    assert decision.state == STATE_RESTARTING and not decision.restart
    # 유예는 지났으나 쿨다운(30초) 안 — STALL 로 알리되 손대지 않음.
    decision = monitor.evaluate(_inputs(age=None), now=50.0, auto_enabled=True)
    assert decision.state == STATE_STALL and not decision.restart
    # 쿨다운 경과 — 두 번째 재시작.
    decision = monitor.evaluate(_inputs(age=None), now=56.0, auto_enabled=True)
    assert decision.restart is True
    assert monitor.consecutive_restarts == 2


def test_recovery_resets_consecutive_counter():
    monitor = _monitor(start=0.0)
    assert monitor.evaluate(_inputs(age=15.0), now=25.0, auto_enabled=True).restart
    decision = monitor.evaluate(_inputs(age=0.5), now=40.0, auto_enabled=True)
    assert decision.state == STATE_OK
    assert monitor.consecutive_restarts == 0


def test_depth_active_suppresses_even_when_stale():
    decision = _monitor().evaluate(
        _inputs(age=999.0, depth=True), now=100.0, auto_enabled=True)
    assert decision.state == STATE_SUPPRESSED
    assert decision.restart is False


def test_missing_device_reports_without_restart():
    decision = _monitor().evaluate(
        _inputs(age=None, device=False), now=100.0, auto_enabled=True)
    assert decision.state == STATE_NO_DEVICE
    assert decision.restart is False


def test_inactive_unit_is_treated_as_intentional_stop():
    decision = _monitor().evaluate(
        _inputs(age=None, unit=False), now=100.0, auto_enabled=True)
    assert decision.state == STATE_STOPPED
    assert decision.restart is False


def test_unknown_unit_state_never_restarts():
    decision = _monitor().evaluate(
        _inputs(age=None, unit=None), now=100.0, auto_enabled=True)
    assert decision.state == STATE_UNKNOWN
    assert decision.restart is False


def test_auto_disabled_reports_stall_without_restart():
    decision = _monitor().evaluate(_inputs(age=15.0), now=100.0, auto_enabled=False)
    assert decision.state == STATE_STALL
    assert decision.restart is False


def test_external_restart_reopens_grace():
    monitor = _monitor(start=0.0)
    monitor.note_external_restart(now=100.0)
    decision = monitor.evaluate(_inputs(age=None), now=110.0, auto_enabled=True)
    assert decision.state == STATE_RESTARTING
    assert decision.restart is False


def test_fresh_wins_over_stale_unit_cache():
    # systemctl 캐시가 inactive 라도 프레임이 오면 살아있는 것이다.
    decision = _monitor().evaluate(
        _inputs(age=0.2, unit=False), now=100.0, auto_enabled=True)
    assert decision.state == STATE_OK


@pytest.mark.parametrize("age", [10.0, 9.99])
def test_stall_threshold_boundary_is_inclusive_fresh(age):
    decision = _monitor().evaluate(_inputs(age=age), now=100.0, auto_enabled=True)
    assert decision.state == STATE_OK
