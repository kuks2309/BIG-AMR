import os

from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_dir = get_package_share_directory('lidar_calibration_2d')

    config_file = os.path.join(pkg_dir, 'config', 'tf_publisher_params.yaml')

    return LaunchDescription([
        Node(
            package='lidar_calibration_2d',
            executable='lidar_tf_publisher',
            name='lidar_tf_publisher',
            output='screen',
            parameters=[config_file],
        ),
    ])
