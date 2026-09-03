# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""CCTV 웹 뷰어 실행 런치.

구독 토픽은 **공용 로스터**(config/camera/camera_common.yaml)에서 파생한다 — 퍼블리셔·
탐지기와 같은 단일 근원이다. 로스터 이름을 바꿨을 때 이 노드만 옛 이름을 구독해
조용히 빈 화면이 되는 사고를 막는다(2026-07-30 개명 때 탐지기가 그 경로였다).

    ros2 launch cctv_webview cctv_webview.launch.py
    ros2 launch cctv_webview cctv_webview.launch.py port:=8080 stream_hz:=15.0
"""
import os

import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

_FALLBACK = [f"/cam_{p}/image_raw/compressed"
             for p in ("rf", "lf", "rr", "f", "r", "lr")]


def _find_shared_config():
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
    path = _find_shared_config()
    if not path:
        return _FALLBACK
    with open(path, "r") as handle:
        config = yaml.safe_load(handle) or {}
    topics = [f"/{cam['name']}/image_raw/compressed"
              for cam in (config.get("cameras") or []) if cam.get("name")]
    return topics or _FALLBACK


def _flipped_cameras():
    """로스터에서 `flip: true` 인 카메라 이름 — 대문 페이지가 CSS 로 180° 돌린다.

    빈 목록이면 [""] 를 돌려준다 — rclpy 는 빈 리스트 파라미터의 타입을 추론하지
    못하므로 빈 문자열 1개를 sentinel 로 쓰고 노드가 걸러낸다.
    """
    path = _find_shared_config()
    if not path:
        return [""]
    with open(path, "r") as handle:
        config = yaml.safe_load(handle) or {}
    flipped = [cam["name"] for cam in (config.get("cameras") or [])
               if cam.get("name") and cam.get("flip", False)]
    return flipped or [""]


def generate_launch_description():
    args = [
        DeclareLaunchArgument("port", default_value="8080",
                              description="HTTP 포트"),
        DeclareLaunchArgument("bind", default_value="0.0.0.0",
                              description="바인드 주소. 로컬만 열려면 127.0.0.1"),
        DeclareLaunchArgument("stream_hz", default_value="10.0",
                              description="시청자당 스트림 상한(Hz). 대역·부하를 정한다."),
    ]
    node = Node(
        package="cctv_webview",
        executable="cctv_webview",
        name="cctv_webview",
        output="screen",
        parameters=[{
            "camera_topics": _camera_topics(),
            "flipped_cameras": _flipped_cameras(),
            "port": LaunchConfiguration("port"),
            "bind": LaunchConfiguration("bind"),
            "stream_hz": LaunchConfiguration("stream_hz"),
        }],
    )
    return LaunchDescription(args + [node])
