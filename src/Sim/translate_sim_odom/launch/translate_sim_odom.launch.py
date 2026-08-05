from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='translate_sim_odom',
            executable='translate_sim_odom_node',
            name='translate_sim_odom_node',
            output='screen',
            parameters=[PathJoinSubstitution([
                FindPackageShare('translate_sim_odom'),
                'config', 'sim_params.yaml'])],
        ),
    ])
