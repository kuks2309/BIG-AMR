"""motor_control_node 기동 — config/tongyi_amr.yaml 파라미터 로드."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory("motor_control"), "config", "tongyi_amr.yaml")
    return LaunchDescription([
        DeclareLaunchArgument("params_file", default_value=default_params),
        Node(
            package="motor_control",
            executable="motor_control_node",
            name="motor_control_node",
            parameters=[LaunchConfiguration("params_file")],
            output="screen",
        ),
    ])
