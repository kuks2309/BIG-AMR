"""yolo_detector 실행 런치.

  ros2 launch yolo_detector detect.launch.py
  ros2 launch yolo_detector detect.launch.py total_hz:=12.0 confidence:=0.5
  ros2 launch yolo_detector detect.launch.py model_path:=/path/to/custom.pt classes:='[person,pallet]'

카메라 발행자(usb_cam_publisher)가 먼저 떠 있어야 한다 — 이 노드는 장치를 열지 않는다.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    args = [
        DeclareLaunchArgument("model_path", default_value="/home/nvidia/models/yolov8n.pt",
                              description="YOLO 가중치 경로(.pt)"),
        DeclareLaunchArgument("classes", default_value="[person]",
                              description="발행할 클래스 이름 목록. 비우면 전체."),
        DeclareLaunchArgument("confidence", default_value="0.35",
                              description="검출 신뢰도 임계"),
        DeclareLaunchArgument("total_hz", default_value="30.0",
                              description="전체 추론 주기(Hz). 카메라 수로 나눠 라운드로빈."),
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
            "model_path": LaunchConfiguration("model_path"),
            "classes": LaunchConfiguration("classes"),
            "confidence": LaunchConfiguration("confidence"),
            "total_hz": LaunchConfiguration("total_hz"),
            "imgsz": LaunchConfiguration("imgsz"),
            "device": LaunchConfiguration("device"),
        }],
    )
    return LaunchDescription(args + [detector])
