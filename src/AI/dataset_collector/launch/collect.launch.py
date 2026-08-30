"""dataset_collector 실행 런치.

카메라 장치를 열지 않으므로 `usb_cam_publisher` 가 이미 떠 있는 상태에서 그대로 붙인다.

  ros2 launch dataset_collector collect.launch.py
  ros2 launch dataset_collector collect.launch.py out_dir:=/data/ds interval_s:=2.0
"""
import os
from datetime import datetime

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

DEFAULT_OUT_DIR = os.path.join(
    os.path.expanduser("~"), "dataset_capture", datetime.now().strftime("%Y-%m-%d"))


def generate_launch_description():
    args = [
        DeclareLaunchArgument("out_dir", default_value=DEFAULT_OUT_DIR,
                              description="저장 루트. 카메라별 하위 폴더가 생성된다."),
        DeclareLaunchArgument("interval_s", default_value="1.0",
                              description="샘플 주기(초). 카메라마다 이 주기로 최대 1장."),
        DeclareLaunchArgument("min_free_gb", default_value="5.0",
                              description="여유 공간 하한(GB). 이하이면 저장을 멈춘다."),
        DeclareLaunchArgument("min_mean_abs_diff", default_value="3.0",
                              description="신규 판정 임계(평균 절대차). 낮출수록 많이 저장한다."),
        DeclareLaunchArgument("jpeg_quality", default_value="92",
                              description="JPEG 품질(1~100)."),
    ]
    collector = Node(
        package="dataset_collector",
        executable="collector",
        name="dataset_collector",
        output="screen",
        parameters=[{
            "out_dir": LaunchConfiguration("out_dir"),
            "interval_s": LaunchConfiguration("interval_s"),
            "min_free_gb": LaunchConfiguration("min_free_gb"),
            "min_mean_abs_diff": LaunchConfiguration("min_mean_abs_diff"),
            "jpeg_quality": LaunchConfiguration("jpeg_quality"),
        }],
    )
    return LaunchDescription(args + [collector])
