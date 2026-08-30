from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Phase2 (2026-06-09): /robot_pose 구독을 pose_topic 으로 remap. default=/robot_pose (현행).
    # 검증/적용 시 pose_topic:=/robot_pose_fused (fused odometry 노드 필요). 근거 docs/plan/2026-06-09_phase2_robot_pose_replacement.md
    pose_topic = LaunchConfiguration('pose_topic')
    return LaunchDescription([
        DeclareLaunchArgument('pose_topic', default_value='/robot_pose',
                              description='Phase2: /robot_pose_fused 설정 시 fused odometry 사용'),
        Node(
            package='trnav_motion_action_server',
            executable='amr_crab_linear_node',
            name='trnav_crab_linear_node',
            output='screen',
            parameters=[PathJoinSubstitution([
                FindPackageShare('trnav_motion_action_server'),
                'config', 'crab_linear_params.yaml'])],
            remappings=[('/robot_pose', pose_topic)],
        ),
    ])
