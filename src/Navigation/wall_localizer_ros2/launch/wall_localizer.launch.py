# 벽 3면 라이다 정밀 측위 노드만 띄운다. 라이다 드라이버·TF(seer_lidar_tf)는 별도 기동.
#
# 입력  : scan (리맵 — 스테이션 벽이 전방이면 /scan_front, 필요 시 /scan_merged)
# 출력  : /wall_pose (PoseStamped, frame_id=station_frame — base_link 의 스테이션 내 자세)
#         /wall_localizer/diagnostics (DiagnosticArray — 상태·벽별 잔차, 매 스캔)
# 주의  : 유효 해(OK/DEGRADED)일 때만 /wall_pose 가 나온다. TF(base_link←라이다) 수신
#         전에는 측위하지 않는다.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory('wall_localizer_ros2'), 'config', 'wall_localizer.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file', default_value=default_params,
            description='wall_localizer 파라미터 YAML (기준 벽 좌표 포함 — 실측값 필수)'),
        DeclareLaunchArgument(
            'scan_topic', default_value='/scan_front',
            description='구독할 LaserScan 토픽'),
        Node(
            package='wall_localizer_ros2',
            executable='wall_localizer_node',
            name='wall_localizer',
            parameters=[LaunchConfiguration('params_file')],
            remappings=[('scan', LaunchConfiguration('scan_topic'))],
            output='screen',
        ),
    ])
