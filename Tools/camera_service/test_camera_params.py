"""camera_params 단위 테스트 — 카메라·ROS 무접촉."""
import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from camera_params import (camera_names, camera_params, default_config_path,
                           device_path, load_roster, ros_run_argv)

# <repo>/Tools/camera_service/test_camera_params.py → 세 단계 위가 저장소 루트
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROSTER = {
    "by_id_prefix": "Prefix_Name",
    "capture": {"image_width": 640, "image_height": 480, "framerate": 15.0,
                "pixel_format": "MJPG", "buffersize": 2, "power_line_frequency": 2},
    "cameras": [
        {"name": "cam0", "serial": "AAA"},
        {"name": "cam1", "serial": "BBB", "image_width": 1920, "framerate": 60.0},
    ],
}


def write_roster(tmp_path, data):
    path = tmp_path / "camera_common.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return str(path)


# ── load_roster ─────────────────────────────────────────────────────────────
def test_load_roster_reads_yaml(tmp_path):
    config = load_roster(write_roster(tmp_path, ROSTER))
    assert config["by_id_prefix"] == "Prefix_Name"


def test_load_roster_rejects_missing_required_key(tmp_path):
    bad = {"cameras": [{"name": "cam0", "serial": "AAA"}]}      # by_id_prefix 없음
    with pytest.raises(ValueError, match="by_id_prefix"):
        load_roster(write_roster(tmp_path, bad))


def test_load_roster_raises_on_missing_file(tmp_path):
    with pytest.raises(OSError):
        load_roster(str(tmp_path / "nope.yaml"))


# ── device_path ─────────────────────────────────────────────────────────────
def test_device_path_uses_stable_by_id_symlink():
    assert device_path("Pfx", "S1") == "/dev/v4l/by-id/usb-Pfx_S1-video-index0"


# ── camera_params ───────────────────────────────────────────────────────────
def test_shared_capture_defaults_apply():
    p = camera_params(ROSTER, "cam0")
    assert p["image_width"] == 640
    assert p["framerate"] == 15.0


def test_per_camera_value_overrides_shared():
    p = camera_params(ROSTER, "cam1")
    assert p["image_width"] == 1920
    assert p["framerate"] == 60.0
    assert p["image_height"] == 480          # 미지정 항목은 공통값 유지


def test_frame_id_follows_camera_name():
    assert camera_params(ROSTER, "cam0")["frame_id"] == "cam0_optical_frame"


def test_unknown_camera_raises_with_roster_listed():
    with pytest.raises(KeyError, match="cam9"):
        camera_params(ROSTER, "cam9")


def test_int_params_stay_int_not_float():
    """ROS2 는 타입에 엄격 — 1280.0 을 int 파라미터로 넘기면 거부된다."""
    roster = {**ROSTER, "capture": {**ROSTER["capture"], "image_width": 1280.0}}
    assert isinstance(camera_params(roster, "cam0")["image_width"], int)


def test_float_params_stay_float():
    roster = {**ROSTER, "capture": {**ROSTER["capture"], "framerate": 30}}
    assert isinstance(camera_params(roster, "cam0")["framerate"], float)


def test_legacy_defaults_key_is_supported():
    legacy = {"by_id_prefix": "P", "defaults": {"image_width": 800},
              "cameras": [{"name": "cam0", "serial": "S"}]}
    assert camera_params(legacy, "cam0")["image_width"] == 800


# ── ros_run_argv ────────────────────────────────────────────────────────────
def test_node_name_matches_batch_launch_convention():
    argv = ros_run_argv("cam2", camera_params(ROSTER, "cam0"))
    assert "__node:=usb_cam_publisher_cam2" in argv


def test_argv_starts_with_ros2_run():
    argv = ros_run_argv("cam0", camera_params(ROSTER, "cam0"))
    assert argv[:4] == ["ros2", "run", "usb_cam_publisher", "usb_cam_publisher_node"]


def test_every_param_is_passed():
    params = camera_params(ROSTER, "cam0")
    argv = ros_run_argv("cam0", params)
    for key in params:
        assert any(a.startswith(f"{key}:=") for a in argv), f"{key} 누락"


# ── 실제 저장소 로스터 (정본과의 정합) ──────────────────────────────────────
def test_real_roster_loads_and_lists_cameras():
    config = load_roster(default_config_path(REPO_ROOT))
    names = camera_names(config)
    assert len(names) >= 1
    assert names == sorted(set(names), key=names.index), "카메라 이름 중복"


def test_real_roster_every_camera_resolves():
    config = load_roster(default_config_path(REPO_ROOT))
    for name in camera_names(config):
        params = camera_params(config, name)
        assert params["video_device"].startswith("/dev/v4l/by-id/")
