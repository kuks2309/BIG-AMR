from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Phase2 (2026-06-09): yaw_control pose 소스 override. default=/robot_pose (현행 유지).
    # 검증/적용 시 yaw_control_pose_topic:=/robot_pose_fused (fused odometry 노드 가동 필수).
    # 근거 docs/plan/2026-06-09_phase2_robot_pose_replacement.md
    pose_topic = LaunchConfiguration('yaw_control_pose_topic')
    return LaunchDescription([
        DeclareLaunchArgument(
            'yaw_control_pose_topic',
            default_value='/robot_pose',
            description='Phase2: /robot_pose_fused 설정 시 fused odometry 사용 (fused 노드 필요)'),
        Node(
            package='trnav_motion_action_server',
            executable='amr_yaw_control_node',
            name='trnav_yaw_control_node',
            output='screen',
            parameters=[
                PathJoinSubstitution([
                    FindPackageShare('trnav_motion_action_server'),
                    'config', 'yaw_control_params.yaml']),
                {'yaw_control_pose_topic': pose_topic},
            ],
        ),
    ])
