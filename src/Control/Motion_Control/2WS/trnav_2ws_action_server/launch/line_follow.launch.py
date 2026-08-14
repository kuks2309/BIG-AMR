from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # 인식 계층(line_vision/line_seg.launch.py)과 trnav_motion_mux 가 먼저 떠 있어야 한다.
    # mux 가 없으면 /motion/wheel_cmd/line_follow 를 발행해도 하류로 나가지 않는다.
    pose_topic = LaunchConfiguration('line_follow_pose_topic')
    return LaunchDescription([
        DeclareLaunchArgument(
            'line_follow_pose_topic',
            default_value='/robot_pose',
            description='거리 적산·측위 감시에 쓰는 pose 토픽'),
        Node(
            package='trnav_2ws_action_server',
            executable='amr_line_follow_node',
            name='trnav_line_follow_node',
            output='screen',
            parameters=[
                PathJoinSubstitution([
                    FindPackageShare('trnav_2ws_action_server'),
                    'config', 'line_follow_params.yaml']),
                {'line_follow_pose_topic': pose_topic},
            ],
        ),
    ])
