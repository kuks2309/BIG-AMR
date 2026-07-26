import os

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_dir = get_package_share_directory('lidar_calibration_2d')

    config_file = os.path.join(pkg_dir, 'config', 'calibration_params.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock if true',
        ),

        Node(
            package='lidar_calibration_2d',
            executable='lidar_calibration_2d_node',
            name='lidar_calibration_2d_node',
            output='screen',
            parameters=[
                config_file,
                {'use_sim_time': use_sim_time},
            ],
        ),
    ])
