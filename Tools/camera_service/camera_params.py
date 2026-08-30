"""카메라 1대의 실행 파라미터를 공용 로스터에서 해석한다 — 순수 로직(단위 테스트 가능).

`config/camera/camera_common.yaml` 이 카메라 설정의 단일 근원(SSOT)이다. 본 모듈은 그 파일을
읽어 **한 대분** 파라미터만 뽑는다. systemd 인스턴스마다 노드를 하나씩 띄우기 위한 것으로,
`usb_cam_cctv.launch.py`(6대 일괄)와 같은 값을 쓰되 카메라별로 분리 기동하는 것이 목적이다.

기존 `usb_cam_publisher` 패키지는 건드리지 않는다 — 본 도구는 배포 계층이다.
"""
from __future__ import annotations

import os

import yaml

# 런치 파일(usb_cam_cctv.launch.py)과 동일한 기본값. 로스터에 값이 없을 때만 쓰인다.
CAPTURE_DEFAULTS = {
    "image_width": 1280,
    "image_height": 720,
    "framerate": 30.0,
    "pixel_format": "MJPG",
    "buffersize": 2,
    "power_line_frequency": 2,
    "fps_report_interval_sec": 5.0,
}
# 정수로 넘겨야 하는 파라미터 — ROS2 는 타입에 엄격해 1280.0 을 int 파라미터로 못 받는다.
_INT_KEYS = ("image_width", "image_height", "buffersize", "power_line_frequency")
_FLOAT_KEYS = ("framerate", "fps_report_interval_sec")


def load_roster(config_path: str) -> dict:
    """공용 카메라 설정을 읽는다.

    Args:
        config_path: `camera_common.yaml` 경로.
    Returns:
        파싱된 설정 딕셔너리.
    Raises:
        OSError: 파일이 없을 때.
        ValueError: 필수 키(`by_id_prefix`·`cameras`)가 없을 때.
    """
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"설정이 매핑이 아니다: {config_path}")
    for key in ("by_id_prefix", "cameras"):
        if key not in config:
            raise ValueError(f"필수 키 '{key}' 없음: {config_path}")
    return config


def device_path(by_id_prefix: str, serial: str) -> str:
    """시리얼 기반 안정 심링크 경로.

    `/dev/videoN` 인덱스는 재부팅·재연결로 바뀌므로 by-id 를 쓴다
    (`usb_cam_cctv.launch.py:_device_path` 와 동일 규칙).
    """
    return f"/dev/v4l/by-id/usb-{by_id_prefix}_{serial}-video-index0"


def camera_names(config: dict) -> list[str]:
    """로스터에 등재된 카메라 이름 목록(등재 순)."""
    return [cam["name"] for cam in config["cameras"]]


def camera_params(config: dict, name: str) -> dict:
    """카메라 한 대의 노드 파라미터. 카메라별 값이 공통 기본값을 덮어쓴다.

    Args:
        config: `load_roster` 결과.
        name: 카메라 논리 이름(예: "cam0").
    Returns:
        노드 파라미터 딕셔너리(`video_device` 포함).
    Raises:
        KeyError: 로스터에 없는 카메라 이름일 때.
    """
    entry = next((c for c in config["cameras"] if c["name"] == name), None)
    if entry is None:
        raise KeyError(f"로스터에 없는 카메라: {name} (등재: {', '.join(camera_names(config))})")

    # 새 스키마 'capture:', 레거시 'defaults:' 둘 다 지원(런치 파일과 동일).
    shared = config.get("capture") or config.get("defaults") or {}
    params = {"video_device": device_path(config["by_id_prefix"], entry["serial"]),
              "camera_name": name,
              "frame_id": f"{name}_optical_frame"}
    for key, fallback in CAPTURE_DEFAULTS.items():
        value = entry.get(key, shared.get(key, fallback))
        if key in _INT_KEYS:
            value = int(value)
        elif key in _FLOAT_KEYS:
            value = float(value)
        params[key] = value
    return params


def ros_run_argv(name: str, params: dict) -> list[str]:
    """`ros2 run` 실행 인자. 노드 이름은 일괄 런치와 같은 규칙으로 맞춘다.

    Args:
        name: 카메라 논리 이름.
        params: `camera_params` 결과.
    Returns:
        execvp 에 넘길 argv (선두 "ros2" 포함).
    """
    argv = ["ros2", "run", "usb_cam_publisher", "usb_cam_publisher_node",
            "--ros-args", "-r", f"__node:=usb_cam_publisher_{name}"]
    for key, value in params.items():
        argv += ["-p", f"{key}:={_literal(value)}"]
    return argv


def _literal(value) -> str:
    """ROS2 파라미터 리터럴. bool 은 소문자, 나머지는 str 그대로."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def default_config_path(repo_root: str) -> str:
    """저장소 기준 공용 설정 경로."""
    return os.path.join(repo_root, "config", "camera", "camera_common.yaml")
