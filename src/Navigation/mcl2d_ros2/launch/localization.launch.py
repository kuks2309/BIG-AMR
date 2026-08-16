# mcl2d 위치추정 lifecycle 노드만 띄운다. 라이다·오도메트리는 별도(→ bringup.launch.py).
#
# 입력  : /odom (BEST_EFFORT), /scan_merged
# 출력  : /mcl_pose + TF map→odom  ※ map→base_link 이 아니다 — odom→base_link 는 오도메트리 소유다
#         (두 노드가 base_link 부모를 중복 생성하면 TF 트리가 깨진다)
# 맵    : map_path 필수. 비면 configure 가 실패하고, autostart(기본)면 프로세스가 종료한다.
# 상태  : autostart:=true(기본) — 노드 main 이 spin 전에 configure→activate 를 동기 구동한다.
#         autostart:=false — unconfigured 로 떠 있고, ros2 lifecycle set 으로 수동 전이한다.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory('mcl2d_ros2'), 'config', 'mcl2d.yaml')

    map_path = LaunchConfiguration('map_path')
    params_file = LaunchConfiguration('params_file')
    # 문자열 'true'/'false' 가 그대로 string 파라미터로 넘어가면 노드의 bool 선언과 타입이
    # 어긋난다 — bool 로 명시 변환해 전달한다.
    autostart = ParameterValue(LaunchConfiguration('autostart'), value_type=bool)

    return LaunchDescription([
        DeclareLaunchArgument(
            'map_path', default_value='',
            description='Seer .smap 절대경로. **필수** — 비우면 configure 실패로 죽는다. '
                        '현재 맵은 Tools/seer_map/download_map.py 로 받는다'),
        DeclareLaunchArgument(
            'params_file', default_value=default_params,
            description='mcl2d 파라미터 YAML. 기본값은 패키지 동봉 config/mcl2d.yaml'),
        DeclareLaunchArgument(
            'odom_topic', default_value='/odom',
            description='구독할 오도메트리 토픽'),
        DeclareLaunchArgument(
            'scan_topic', default_value='/scan_merged',
            description='구독할 병합 LaserScan 토픽 (dual_laser_merger 출력)'),
        DeclareLaunchArgument(
            'autostart', default_value='true',
            description='기동 즉시 configure→activate (노드 main 수행, 실패 시 프로세스 종료). '
                        'false 면 unconfigured 로 뜨고 ros2 lifecycle set 으로 수동 전이'),
        Node(
            package='mcl2d_ros2',
            executable='mcl2d_localization_node',
            name='mcl2d_localization',
            # YAML 을 먼저 깔고 map_path 를 나중에 얹는다 — 명령줄 인자가 파일 값을 이긴다.
            parameters=[params_file, {'map_path': map_path, 'autostart': autostart}],
            remappings=[('odom', LaunchConfiguration('odom_topic')),
                        ('scan', LaunchConfiguration('scan_topic'))],
            output='screen',
        ),
    ])
