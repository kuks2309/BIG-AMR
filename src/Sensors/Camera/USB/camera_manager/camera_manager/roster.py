# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
"""공용 카메라 로스터 로더 — ROS 무의존.

로스터의 단일 근원은 `config/camera/camera_common.yaml` 이다. 탐색·경로 규칙은
`usb_cam_cctv.launch.py` 와 동일하게 맞춘다(값이 갈리면 관리 대상과 관리자가
서로 다른 카메라 목록을 보게 된다).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import yaml

# 공용 설정 상향 탐색 최대 깊이 — launch 파일(_find_shared_config)과 동일.
_DEFAULT_WALK_UP = 10


@dataclass(frozen=True)
class Camera:
    """로스터 1행 — 논리 이름(토픽·유닛 인스턴스명의 근원)과 장치 경로."""

    name: str
    serial: str
    device: str


def device_path(by_id_prefix: str, serial: str) -> str:
    """시리얼 기반 안정 심링크 — /dev/videoN 은 재부팅·재연결마다 바뀐다."""
    return f"/dev/v4l/by-id/usb-{by_id_prefix}_{serial}-video-index0"


def find_shared_config(start: str | None = None) -> str | None:
    """공용 설정 파일을 찾는다.

    우선순위: `CAMERA_CONFIG` 환경변수 → start(기본: 본 파일 위치)에서 상위로
    올라가며 `config/camera/camera_common.yaml` 탐색 → None.
    """
    env = os.environ.get("CAMERA_CONFIG")
    if env and os.path.exists(env):
        return env
    directory = os.path.dirname(os.path.abspath(start or __file__))
    for _ in range(_DEFAULT_WALK_UP):
        candidate = os.path.join(directory, "config", "camera", "camera_common.yaml")
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return None


def load_roster(config_path: str) -> list[Camera]:
    """공용 yaml → Camera 목록.

    Raises:
        OSError: 파일이 없을 때.
        ValueError: 필수 키(by_id_prefix·cameras)가 없거나 형식이 틀릴 때.
    """
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"설정이 매핑이 아니다: {config_path}")
    for key in ("by_id_prefix", "cameras"):
        if key not in config:
            raise ValueError(f"필수 키 '{key}' 없음: {config_path}")
    prefix = config["by_id_prefix"]
    cameras = []
    for row in config["cameras"]:
        if not isinstance(row, dict) or "name" not in row or "serial" not in row:
            raise ValueError(f"로스터 행에 name/serial 없음: {row!r}")
        cameras.append(
            Camera(row["name"], row["serial"], device_path(prefix, row["serial"])))
    return cameras
