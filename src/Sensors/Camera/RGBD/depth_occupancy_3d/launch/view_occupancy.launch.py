# Copyright 2026 Ford_CATL_AMR
# Licensed under the Apache License, Version 2.0.
#
# surround 점유맵을 RViz2 로 본다. 표시만 하며 맵은 만들지 않는다 —
# 맵 구성은 depth_occupancy_3d 노드가 하고 이 launch 는 그 결과를 그릴 뿐이다.
#
# 사전 조건 (순서대로):
#   ros2 launch orbbec_multi_bringup surround_depth.launch.py     # 카메라 6대 (RGB 스택 정지 후)
#   ros2 launch depth_occupancy_3d depth_occupancy_3d.launch.py   # 융합
#   ros2 launch depth_occupancy_3d view_occupancy.launch.py       # 보기
#
# 원격(AnyDesk 등)으로 볼 때는 RViz2 자체의 렌더링 비용이 이 장비 CPU 에 더해진다는 점을
# 감안한다 — 융합 노드 자체는 CPU 17% 로 가볍지만 뷰어는 그렇지 않다.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_config = os.path.join(
        get_package_share_directory("depth_occupancy_3d"),
        "rviz",
        "surround_occupancy.rviz",
    )

    config_arg = DeclareLaunchArgument(
        "rviz_config",
        default_value=default_config,
        description="RViz2 설정 파일. 발행자가 best-effort 라 QoS 가 그 안에 박혀 있다.",
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="surround_occupancy_view",
        arguments=["-d", LaunchConfiguration("rviz_config")],
        output="screen",
    )

    return LaunchDescription([config_arg, rviz_node])
