"""yolo_detector 실행 런치.

  ros2 launch yolo_detector detect.launch.py
  ros2 launch yolo_detector detect.launch.py detect_hz:=12.0 confidence:=0.5
  ros2 launch yolo_detector detect.launch.py model_path:=/path/to/custom.pt classes:='[person,pallet]'

카메라 발행자(usb_cam_publisher)가 먼저 떠 있어야 한다 — 이 노드는 장치를 열지 않는다.

구독 토픽은 **공용 로스터**(config/camera/camera_common.yaml)에서 파생한다 — 퍼블리셔·뷰어와
같은 단일 근원이다. 노드의 `DEFAULT_TOPICS`(`/cam0..5/image_raw`)에 의존하면 로스터에서 카메라
이름을 바꿨을 때 **에러 없이 검출 0** 이 된다(없는 토픽을 구독하므로). 2026-07-30 위치 기준 개명
때 실제로 이 경로였다 — ADR: docs/adr/2026-07-30-camera-position-naming.md
"""
import os

import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# 로스터를 못 찾을 때만 쓰는 안전값. 이 경로로 떨어지면 실제 카메라 이름과 다를 수 있으므로
# 검출이 0 이면 먼저 로스터 발견 여부를 확인할 것.
_FALLBACK_TOPICS = [f"/cam{i}/image_raw" for i in range(6)]


def _find_shared_config():
    """공용 로스터(config/camera/camera_common.yaml) 경로. 우선순위: CAMERA_CONFIG → 상위 탐색."""
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
    """로스터의 카메라 name 목록에서 `/<name>/image_raw` 토픽을 만든다."""
    path = _find_shared_config()
    if not path:
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
    args = [
        DeclareLaunchArgument("model_path", default_value="/home/nvidia/models/yolov8n.pt",
                              description="YOLO 가중치 경로(.pt)"),
        DeclareLaunchArgument("classes", default_value="[person]",
                              description="발행할 클래스 이름 목록. 비우면 전체."),
        DeclareLaunchArgument("confidence", default_value="0.35",
                              description="검출 신뢰도 임계"),
        DeclareLaunchArgument("detect_hz", default_value="10.0",
                              description="카메라 **한 대당** 검출률(Hz). 배치 추론이라 "
                                          "카메라 수로 나뉘지 않는다(ADR 2026-08-06)."),
        DeclareLaunchArgument("imgsz", default_value="640",
                              description="추론 입력 크기"),
        DeclareLaunchArgument("device", default_value="cuda",
                              description="추론 장치. cpu 는 실측 27배 느리다."),
    ]
    detector = Node(
        package="yolo_detector",
        executable="detector",
        name="yolo_detector",
        output="screen",
        parameters=[{
            "camera_topics": _camera_topics(),
            "model_path": LaunchConfiguration("model_path"),
            "classes": LaunchConfiguration("classes"),
            "confidence": LaunchConfiguration("confidence"),
            "detect_hz": LaunchConfiguration("detect_hz"),
            "imgsz": LaunchConfiguration("imgsz"),
            "device": LaunchConfiguration("device"),
        }],
    )
    return LaunchDescription(args + [detector])
