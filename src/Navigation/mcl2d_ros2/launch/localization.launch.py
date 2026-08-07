# mcl2d 위치추정 노드만 띄운다. 라이다·오도메트리는 별도(→ bringup.launch.py).
#
# 입력  : /odom (BEST_EFFORT), /scan_front, /scan_rear
# 출력  : /mcl_pose + TF map→odom  ※ map→base_link 이 아니다 — odom→base_link 는 오도메트리 소유다
#         (코드리뷰 2026-08-07 H1: 두 노드가 base_link 부모를 중복 생성하면 TF 트리가 깨진다)
# 맵    : map_path 필수. 비면 노드가 FATAL 로 기동을 중단한다(같은 리뷰 H2).

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory('mcl2d_ros2'), 'config', 'mcl2d.yaml')

    map_path = LaunchConfiguration('map_path')
    params_file = LaunchConfiguration('params_file')

    return LaunchDescription([
        DeclareLaunchArgument(
            'map_path', default_value='',
            description='Seer .smap 절대경로. **필수** — 비우면 노드가 FATAL 로 죽는다. '
                        '현재 맵은 Tools/seer_map/download_map.py 로 받는다'),
        DeclareLaunchArgument(
            'params_file', default_value=default_params,
            description='mcl2d 파라미터 YAML. 기본값은 패키지 동봉 config/mcl2d.yaml'),
        DeclareLaunchArgument(
            'odom_topic', default_value='/odom',
            description='구독할 오도메트리 토픽'),
        Node(
            package='mcl2d_ros2',
            executable='mcl2d_localization_node',
            name='mcl2d_localization',
            # YAML 을 먼저 깔고 map_path 를 나중에 얹는다 — 명령줄 인자가 파일 값을 이긴다.
            parameters=[params_file, {'map_path': map_path}],
            remappings=[('odom', LaunchConfiguration('odom_topic'))],
            output='screen',
        ),
    ])
