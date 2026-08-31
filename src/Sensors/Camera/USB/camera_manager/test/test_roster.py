# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""roster 로더 단위 테스트 — 임시 yaml 파일로 실파일 경로만 검증."""
import pytest

from camera_manager.roster import device_path, find_shared_config, load_roster

_VALID = """
by_id_prefix: "Vendor_Cam"
cameras:
  - name: "cam_a"
    serial: "S1"
  - name: "cam_b"
    serial: "S2"
"""


def test_load_roster_parses_names_and_devices(tmp_path):
    path = tmp_path / "camera_common.yaml"
    path.write_text(_VALID, encoding="utf-8")
    cameras = load_roster(str(path))
    assert [cam.name for cam in cameras] == ["cam_a", "cam_b"]
    assert cameras[0].device == "/dev/v4l/by-id/usb-Vendor_Cam_S1-video-index0"


def test_load_roster_rejects_missing_required_key(tmp_path):
    path = tmp_path / "camera_common.yaml"
    path.write_text("cameras: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="by_id_prefix"):
        load_roster(str(path))


def test_load_roster_rejects_malformed_row(tmp_path):
    path = tmp_path / "camera_common.yaml"
    path.write_text(
        'by_id_prefix: "V"\ncameras:\n  - name: "only_name"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="name/serial"):
        load_roster(str(path))


def test_device_path_matches_launch_convention():
    assert device_path("P", "S") == "/dev/v4l/by-id/usb-P_S-video-index0"


def test_find_shared_config_prefers_env(tmp_path, monkeypatch):
    path = tmp_path / "camera_common.yaml"
    path.write_text(_VALID, encoding="utf-8")
    monkeypatch.setenv("CAMERA_CONFIG", str(path))
    assert find_shared_config() == str(path)


def test_find_shared_config_walks_up(tmp_path, monkeypatch):
    monkeypatch.delenv("CAMERA_CONFIG", raising=False)
    config_dir = tmp_path / "config" / "camera"
    config_dir.mkdir(parents=True)
    (config_dir / "camera_common.yaml").write_text(_VALID, encoding="utf-8")
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    marker = deep / "marker.py"
    marker.write_text("", encoding="utf-8")
    assert find_shared_config(str(marker)) == str(config_dir / "camera_common.yaml")
