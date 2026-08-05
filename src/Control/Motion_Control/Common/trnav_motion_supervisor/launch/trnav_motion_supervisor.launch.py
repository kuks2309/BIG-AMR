import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('trnav_motion_supervisor'),
        'config', 'trnav_motion_supervisor.yaml')
    return LaunchDescription([
        Node(
            package='trnav_motion_supervisor',
            executable='trnav_motion_supervisor_node',
            name='trnav_motion_supervisor',
            output='screen',
            parameters=[config],
        ),
    ])
