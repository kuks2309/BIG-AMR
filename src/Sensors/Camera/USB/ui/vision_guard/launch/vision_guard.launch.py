# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
#
# Launch the AMR VisionGuard viewer. Camera topics are derived from the shared
# roster (config/camera/camera_common.yaml) so the viewer stays in sync with
# usb_cam_publisher — single source of truth, **정상 경로에 한해서만**.
# ⚠ roster 를 못 찾으면 `_FALLBACK_TOPICS`(4대)로 축소되어 현 로스터 6대 중 cam4·cam5 가
#   빠진다. 감시 누락이므로 fallback 진입 시 경고를 출력한다(아래 `_camera_topics`).
# Transport / layout remain launch arguments so the same node serves 1..N cameras.

import os

import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# 공용 roster 를 못 찾을 때의 **축소** 기본값 — 안전값이 아니라 최소 기동값이다.
# 현 로스터는 6대이므로 이 경로로 떨어지면 나열되지 않은 2대가 화면에서 사라진다.
# 이름은 장착 위치 기준(2026-07-30 개명, ADR: docs/adr/2026-07-30-camera-position-naming.md).
_FALLBACK_TOPICS = [
    "/cam_rf/image_raw",
    "/cam_lf/image_raw",
    "/cam_rr/image_raw",
    "/cam_f/image_raw",
]


def _find_shared_config():
    """공용 config(config/camera/camera_common.yaml) 를 찾는다.

    우선순위: CAMERA_CONFIG 환경변수 → 상위로 올라가며 탐색 → None.
    usb_cam_cctv.launch.py 와 동일 파일을 가리키게 하는 것이 목적.
    """
    env = os.environ.get("CAMERA_CONFIG")
    if env and os.path.exists(env):
        return env
    directory = os.path.dirname(os.path.realpath(__file__))
    for _ in range(10):
        candidate = os.path.join(directory, "config", "camera", "camera_common.yaml")
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return None


def _camera_topics():
    """공용 roster 의 카메라 name 목록에서 /<name>/image_raw 토픽을 만든다."""
    path = _find_shared_config()
    if not path:
        print(f"[vision_guard.launch] ⚠ 공용 roster 를 찾지 못해 축소 기본값 "
              f"{len(_FALLBACK_TOPICS)}대로 기동한다 — 로스터의 나머지 카메라는 "
              f"화면에 나오지 않는다.", flush=True)
        return _FALLBACK_TOPICS
    with open(path, "r") as handle:
        config = yaml.safe_load(handle) or {}
    topics = [
        f"/{cam['name']}/image_raw"
        for cam in (config.get("cameras") or [])
        if cam.get("name")
    ]
    return topics or _FALLBACK_TOPICS


def generate_launch_description():
    transport_arg = DeclareLaunchArgument(
        "image_transport",
        default_value="raw",
        description="Image transport: 'raw' or 'compressed' (compressed saves "
        "bandwidth with many cameras).",
    )
    layout_arg = DeclareLaunchArgument(
        "layout",
        default_value="",
        description="Initial grid preset, e.g. '2x3'. Empty auto-fits camera count.",
    )
    render_arg = DeclareLaunchArgument(
        "render_hz",
        default_value="10.0",
        description="화면 갱신 상한(Hz). 기본 10 — 30 은 설정에 도달하지도 못하면서(실측 12~14 fps) "
        "카메라 29.7→28.9, 탐지 29.3→25.4 Hz 로 끌어내린다(2026-07-29 실측).",
    )
    ai_arg = DeclareLaunchArgument(
        "ai_overlay",
        default_value="false",
        description="기동 시 AI 박스 표시 on/off. 화면의 'AI 표시' 체크박스로도 바꿀 수 있다. "
        "기본 off — 검출 0건을 '사람 없음' 으로 오독할 위험을 기본값으로 두지 않는다.",
    )

    viewer = Node(
        package="vision_guard",
        executable="vision_guard",
        name="vision_guard",
        output="screen",
        parameters=[
            {
                "camera_topics": _camera_topics(),
                "image_transport": LaunchConfiguration("image_transport"),
                "layout": LaunchConfiguration("layout"),
                "ai_overlay": LaunchConfiguration("ai_overlay"),
                "render_hz": LaunchConfiguration("render_hz"),
            }
        ],
    )

    return LaunchDescription([transport_arg, layout_arg, ai_arg, render_arg, viewer])
