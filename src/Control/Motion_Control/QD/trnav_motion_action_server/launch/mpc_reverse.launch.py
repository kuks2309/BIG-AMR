from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    mpc_reverse_node = Node(
        package='trnav_motion_action_server',
        executable='amr_mpc_reverse_node',
        name='trnav_mpc_reverse_node',
        output='screen',
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_motion_action_server'),
            'config', 'mpc_reverse_params.yaml'])],
    )

    return LaunchDescription([mpc_reverse_node])
