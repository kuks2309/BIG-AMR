# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
#
# Launch one usb_cam_publisher_node per camera in the shared camera config.
# Capture settings + serial roster come from the single shared source
# config/camera/camera_common.yaml (also read by the Python calibration UI),
# falling back to the package-local cameras.yaml for backward compatibility.

import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node


def _load_camera_config(config_path):
    with open(config_path, "r") as handle:
        return yaml.safe_load(handle)


def _device_path(by_id_prefix, serial):
    # Matches: /dev/v4l/by-id/usb-<prefix>_<serial>-video-index0
    return f"/dev/v4l/by-id/usb-{by_id_prefix}_{serial}-video-index0"


def _find_shared_config():
    """공용 config(config/camera/camera_common.yaml) 를 찾는다.

    우선순위: CAMERA_CONFIG 환경변수 → 상위로 올라가며 탐색 → None(패키지 fallback).
    Python 로더(camera_config.py)와 동일 파일을 가리키게 하는 것이 목적.
    """
    env = os.environ.get("CAMERA_CONFIG")
    if env and os.path.exists(env):
        return env
    directory = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        candidate = os.path.join(directory, "config", "camera", "camera_common.yaml")
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return None


def generate_launch_description():
    shared = _find_shared_config()
    if shared:
        config_path = shared
    else:
        pkg_share = get_package_share_directory("usb_cam_publisher")
        config_path = os.path.join(pkg_share, "config", "cameras.yaml")

    config_arg = DeclareLaunchArgument(
        "config_file",
        default_value=config_path,
        description="Path to the shared camera config (capture settings + roster).",
    )

    config = _load_camera_config(config_path)
    prefix = config["by_id_prefix"]
    # 새 스키마는 'capture:', 레거시는 'defaults:' — 둘 다 지원.
    caps = config.get("capture") or config.get("defaults") or {}

    nodes = []
    for cam in config["cameras"]:
        name = cam["name"]
        device = _device_path(prefix, cam["serial"])
        params = {
            "video_device": device,
            "camera_name": name,
            "frame_id": f"{name}_optical_frame",
            "image_width": cam.get("image_width", caps.get("image_width", 1280)),
            "image_height": cam.get("image_height", caps.get("image_height", 720)),
            "framerate": float(cam.get("framerate", caps.get("framerate", 30.0))),
            "pixel_format": cam.get("pixel_format", caps.get("pixel_format", "MJPG")),
            "buffersize": int(cam.get("buffersize", caps.get("buffersize", 2))),
            "power_line_frequency": int(
                cam.get("power_line_frequency", caps.get("power_line_frequency", 2))
            ),
            "fps_report_interval_sec": float(
                cam.get(
                    "fps_report_interval_sec",
                    caps.get("fps_report_interval_sec", 5.0),
                )
            ),
            # compressed = 카메라 MJPEG 를 디코드 없이 전달(기본). raw | both 도 지원.
            "publish_mode": cam.get(
                "publish_mode", caps.get("publish_mode", "compressed")
            ),
        }
        nodes.append(
            Node(
                package="usb_cam_publisher",
                executable="usb_cam_publisher_node",
                name=f"usb_cam_publisher_{name}",
                parameters=[params],
                output="screen",
            )
        )

    return LaunchDescription([config_arg, *nodes])
