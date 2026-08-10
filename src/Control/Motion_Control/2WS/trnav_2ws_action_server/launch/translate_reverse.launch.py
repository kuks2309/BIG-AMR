from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # 측위 자세 토픽 리다이렉트. 전진 쌍둥이(`translate_forward`·`mpc`)에는 있고 여기만
    # 없었다 — 그 결과 이 서버들은 **리다이렉트 수단이 아예 없었다**(yaml 의
    # `*_pose_topic` 키는 코드가 읽지 않는 죽은 키였고, 그 값
    # `/rtabmap/localization_pose` 는 발행자 0 인 토픽이었다 — 2026-08-06 실측).
    pose_topic = LaunchConfiguration('pose_topic')
    return LaunchDescription([
        DeclareLaunchArgument('pose_topic', default_value='/robot_pose',
                              description='LocalizationMonitor 가 구독할 자세 토픽'),
        Node(
            package='trnav_2ws_action_server',
            executable='amr_translate_reverse_node',
            name='trnav_translate_reverse_node',
            output='screen',
            parameters=[PathJoinSubstitution([
                FindPackageShare('trnav_2ws_action_server'),
                'config', 'translate_reverse_params.yaml'])],
            remappings=[('/robot_pose', pose_topic)],
        ),
    ])
