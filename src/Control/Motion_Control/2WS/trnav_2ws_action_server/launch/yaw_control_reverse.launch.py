from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='trnav_2ws_action_server',
            executable='amr_yaw_control_reverse_node',
            name='trnav_yaw_control_reverse_node',
            output='screen',
            parameters=[PathJoinSubstitution([
                FindPackageShare('trnav_2ws_action_server'),
                'config', 'yaw_control_reverse_params.yaml'])],
        ),
    ])
