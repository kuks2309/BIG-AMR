import os

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_dir = get_package_share_directory('lidar_calibration_2d')

    ui_config_file = os.path.join(pkg_dir, 'config', 'calibration_ui_params.yaml')
    tf_config_file = os.path.join(pkg_dir, 'config', 'tf_publisher_params.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Use simulation clock if true',
        ),

        Node(
            package='lidar_calibration_2d',
            executable='lidar_tf_publisher',
            name='lidar_tf_publisher',
            output='screen',
            parameters=[tf_config_file],
        ),

        Node(
            package='lidar_calibration_2d',
            executable='calibration_ui_main.py',
            name='lidar_calibration_2d_ui',
            output='screen',
            parameters=[
                ui_config_file,
                {'use_sim_time': use_sim_time},
            ],
        ),
    ])
