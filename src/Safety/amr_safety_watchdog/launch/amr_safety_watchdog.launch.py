from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    pkg_dir = get_package_share_directory('amr_safety_watchdog')
    config = os.path.join(pkg_dir, 'config', 'amr_safety_watchdog.yaml')

    return LaunchDescription([
        Node(
            package='amr_safety_watchdog',
            executable='amr_safety_watchdog_node',
            name='amr_safety_watchdog',
            output='screen',
            parameters=[config],
        )
    ])
