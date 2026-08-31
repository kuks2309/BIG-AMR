"""공용 카메라 설정(config/camera/camera_common.yaml) 로더.

Python 도구가 C++ 퍼블리셔와 **동일한** 캡처 설정·시리얼 로스터를 쓰도록 하는
단일 근원. 하드코딩 대신 이 로더를 통해 값을 읽는다. PyYAML 만 의존.
"""
from __future__ import annotations

import os

import yaml

_CAPTURE_DEFAULTS = {
    "image_width": 1280,
    "image_height": 720,
    "framerate": 30.0,
    "pixel_format": "MJPG",
    "buffersize": 2,
    "power_line_frequency": 2,
}


def default_config_path():
    """repo-root config/camera/camera_common.yaml 경로(이 파일 기준 산출)."""
    here = os.path.dirname(os.path.abspath(__file__))
    # Tools/CameraCalibration → 2 단계 위가 repo root.
    root = os.path.dirname(os.path.dirname(here))
    return os.path.join(root, "config", "camera", "camera_common.yaml")


def load_camera_config(path=None):
    """공용 카메라 설정을 로드한다. 파일 부재/누락 필드는 기본값으로 보강.

    반환 dict: capture(설정), by_id_prefix, cameras(로스터), path.
    """
    path = path or os.environ.get("CAMERA_CONFIG") or default_config_path()
    cfg = {}
    try:
        with open(path) as fh:
            cfg = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        cfg = {}
    capture = dict(_CAPTURE_DEFAULTS)
    capture.update(cfg.get("capture", {}) or {})
    return {
        "capture": capture,
        "by_id_prefix": cfg.get("by_id_prefix", ""),
        "cameras": cfg.get("cameras", []) or [],
        "path": path,
    }
