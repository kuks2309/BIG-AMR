"""PGV 읽기 헤드 드라이버 기동 — 파라미터는 config/pgv_driver.yaml 이 정본."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_config = os.path.join(
        get_package_share_directory("pgv_driver"), "config", "pgv_driver.yaml"
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "config",
                default_value=default_config,
                description="pgv_driver 파라미터 yaml 경로",
            ),
            Node(
                package="pgv_driver",
                executable="pgv_driver_node",
                name="pgv_driver",
                output="screen",
                parameters=[LaunchConfiguration("config")],
            ),
        ]
    )
