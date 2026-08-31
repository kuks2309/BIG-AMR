# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""systemd_ctl 래퍼 단위 테스트 — 가짜 runner 주입, 실 systemctl 무호출."""
import subprocess
from types import SimpleNamespace

from camera_manager.systemd_ctl import SystemdControl, unit_name


def _result(rc=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=rc, stdout=stdout, stderr=stderr)


def test_unit_name_template():
    assert unit_name("cam_f") == "usb-cam@cam_f.service"


def test_is_active_true():
    ctl = SystemdControl(runner=lambda *a, **k: _result(0, "active\n"))
    assert ctl.is_active("cam_f") is True


def test_is_active_false_on_inactive_and_failed():
    for state in ("inactive", "failed"):
        ctl = SystemdControl(runner=lambda *a, s=state, **k: _result(3, f"{s}\n"))
        assert ctl.is_active("cam_f") is False


def test_is_active_none_on_runner_error():
    def _boom(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="systemctl", timeout=5)

    assert SystemdControl(runner=_boom).is_active("cam_f") is None


def test_control_success():
    calls = []

    def _runner(cmd, **kwargs):
        calls.append(cmd)
        return _result(0)

    ok, message = SystemdControl(runner=_runner).control("restart", "cam_f")
    assert ok is True
    assert calls[0][:2] == ["/usr/bin/sudo", "-n"]
    assert "usb-cam@cam_f.service" in calls[0]


def test_control_password_refusal_gives_install_hint():
    ctl = SystemdControl(
        runner=lambda *a, **k: _result(1, stderr="sudo: a password is required"))
    ok, message = ctl.control("restart", "cam_f")
    assert ok is False
    assert "install.sh" in message


def test_control_rejects_unknown_verb():
    ok, message = SystemdControl(runner=lambda *a, **k: _result(0)).control(
        "kill", "cam_f")
    assert ok is False
    assert "동사" in message
