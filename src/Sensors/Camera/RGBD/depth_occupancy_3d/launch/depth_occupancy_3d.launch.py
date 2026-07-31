# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
#
# surround depth 융합 노드만 띄운다. 카메라는 orbbec_multi_bringup 이 별도로 띄운다:
#
#   ros2 launch orbbec_multi_bringup surround_depth.launch.py   # 먼저 (RGB 스택 정지 후)
#   ros2 launch depth_occupancy_3d depth_occupancy_3d.launch.py # 그다음
#
# 두 패키지를 나눈 이유: 카메라 기동과 융합은 수명주기가 다르다. 융합 파라미터를 바꿔가며
# 튜닝할 때 카메라를 다시 열면 USB 재열거 비용이 들고, 재열거가 곧 대역 재협상이라
# 측정 조건이 흔들린다.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory("depth_occupancy_3d"),
        "config",
        "depth_occupancy_3d.yaml",
    )

    params_arg = DeclareLaunchArgument(
        "params_file",
        default_value=default_params,
        description="융합 노드 파라미터 파일.",
    )
    log_level_arg = DeclareLaunchArgument(
        "log_level",
        default_value="info",
        description="rclcpp 로그 수준. 주기별 집계를 보려면 debug.",
    )

    fusion_node = Node(
        package="depth_occupancy_3d",
        executable="depth_occupancy_3d_node",
        name="depth_occupancy_3d",
        parameters=[LaunchConfiguration("params_file")],
        arguments=["--ros-args", "--log-level", LaunchConfiguration("log_level")],
        output="screen",
    )

    return LaunchDescription([params_arg, log_level_arg, fusion_node])
