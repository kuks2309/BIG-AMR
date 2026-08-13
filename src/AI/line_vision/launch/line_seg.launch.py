"""line_seg_node 실행 런치.

  ros2 launch line_vision line_seg.launch.py
  ros2 launch line_vision line_seg.launch.py direction:=reverse
  ros2 launch line_vision line_seg.launch.py model_path:=/path/to/best.pt

카메라 발행자(usb_cam_publisher)가 먼저 떠 있어야 한다 — 이 노드는 장치를 열지 않는다.

전·후방 카메라 이름은 **공용 로스터**(config/camera/camera_common.yaml)에서 파생한다.
노드 기본값에 의존하면 로스터에서 카메라 이름을 바꿨을 때 없는 토픽을 구독해 **에러 없이
검출 0** 이 된다(yolo_detector/detect.launch.py 와 같은 이유).
"""
import os

import yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# 로스터를 못 찾을 때만 쓰는 안전값. 이 경로로 떨어지면 실제 카메라 이름과 다를 수 있으므로
# 검출이 0 이면 먼저 로스터 발견 여부를 확인할 것.
_FALLBACK_FORWARD = "cam_f"
_FALLBACK_REVERSE = "cam_r"


def _find_shared_config():
    """공용 로스터 경로. 우선순위: CAMERA_CONFIG → 상위 탐색."""
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


def _roster_names():
    """로스터에 등재된 카메라 이름 집합."""
    path = _find_shared_config()
    if not path:
        return set()
    with open(path, "r") as handle:
        config = yaml.safe_load(handle) or {}
    return {cam["name"] for cam in (config.get("cameras") or []) if cam.get("name")}


def _camera(preferred, fallback):
    """로스터에 있으면 preferred, 없으면 fallback."""
    return preferred if preferred in _roster_names() else fallback


def generate_launch_description():
    args = [
        DeclareLaunchArgument("model_path",
                              default_value="/home/nvidia/models/line_seg_v1.pt",
                              description="YOLOv8-seg 가중치 경로(.pt)"),
        DeclareLaunchArgument("direction", default_value="forward",
                              description="forward = 전방 카메라, reverse = 후방 카메라"),
        DeclareLaunchArgument("conf_threshold", default_value="0.5",
                              description="세그멘테이션 신뢰도 임계"),
        DeclareLaunchArgument("control_row_ratio", default_value="0.8",
                              description="offset 측정 기준행(화면 높이 비율)"),
        DeclareLaunchArgument("publish_debug_image", default_value="true",
                              description="/line/debug_image 오버레이 발행 여부"),
        DeclareLaunchArgument("image_transport", default_value="compressed",
                              description="카메라 전송 형식(compressed | raw)"),
    ]
    node = Node(
        package="line_vision",
        executable="line_seg",
        name="line_seg_node",
        output="screen",
        parameters=[{
            "model_path": LaunchConfiguration("model_path"),
            "direction": LaunchConfiguration("direction"),
            "conf_threshold": LaunchConfiguration("conf_threshold"),
            "control_row_ratio": LaunchConfiguration("control_row_ratio"),
            "publish_debug_image": LaunchConfiguration("publish_debug_image"),
            "image_transport": LaunchConfiguration("image_transport"),
            "forward_camera": _camera("cam_f", _FALLBACK_FORWARD),
            "reverse_camera": _camera("cam_r", _FALLBACK_REVERSE),
        }],
    )
    return LaunchDescription(args + [node])
