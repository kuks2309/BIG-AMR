# Big-AMR ICP(Iterative Closest Point) 오도메트리 — 휠 오도 부재 대체.
#
# 모터 제어 미완성으로 엔코더 오도메트리가 없어, 2D 라이다 스캔 정합으로 odom→base_link 를 만든다.
# 입력  : /scan_merged  (dual_laser_merger 가 SensorDataQoS=BEST_EFFORT 로 발행)
# 출력  : /odom (nav_msgs/Odometry) + /odom_info + TF odom→base_link
# 소비처: src/Navigation/mcl2d_ros2 의 mcl2d_localization_node (odom 구독)
#
# 전제(본 launch 가 띄우지 않음 — 부재 시 스캔 대기로 조용히 멈춘다):
#   ros2 launch dual_laser_merger sick_with_merger.launch.py
#   → /scan_front·/scan_rear 발행 + /scan_merged 병합 + base_link→scan_merged static TF
#
# 근거·리뷰: docs/code_review/trnav-icp-odometry/2026-07-28.md
#            docs/adr/2026-07-28-icp-odometry-bringup.md

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    params_file = os.path.join(
        get_package_share_directory('icp_odometry_bringup'), 'config', 'icp_odometry.yaml')

    scan_topic = LaunchConfiguration('scan_topic')
    odom_topic = LaunchConfiguration('odom_topic')
    publish_tf = LaunchConfiguration('publish_tf')
    force_3dof = LaunchConfiguration('force_3dof')
    reset_countdown = LaunchConfiguration('reset_countdown')

    icp_odometry = Node(
        package='rtabmap_odom',
        executable='icp_odometry',
        name='icp_odometry',
        parameters=[
            params_file,
            {
                # bool 파라미터에 LaunchConfiguration 을 그냥 넘기면 문자열로 전달되어
                # 타입 불일치로 거부된다 → ParameterValue 로 타입을 명시한다.
                'publish_tf': ParameterValue(publish_tf, value_type=bool),
                # 평면 3자유도(x,y,yaw) 강제. rtabmap 기본값은 "false" 이며,
                # TR_Nav 는 icp_odometry 에 이 값을 넣지 않아 평면 스캔에 6자유도 ICP 를
                # 돌리고 있었다(원저자도 미해결로 기록). Big-AMR 은 2D 전용이라 true 가 기본.
                'Reg/Force3DoF': ParameterValue(force_3dof, value_type=str),
                # 연속 N 프레임 정합 실패 시 자동 리셋. 0 = 비활성(rtabmap 기본).
                # TR_Nav 는 미설정이라 트래킹 상실 후 347 s 미복구 사례가 있었다.
                'Odom/ResetCountdown': ParameterValue(reset_countdown, value_type=str),
            },
        ],
        remappings=[
            ('scan', scan_topic),
            ('odom', odom_topic),
        ],
        output='screen',
        # 죽으면 자동 재기동. ⚠ 재기동한 icp 는 odom 을 원점(항등)부터 다시 적산하므로
        # odom→base_link 가 점프한다 — 하류 mcl2d 는 재수렴이 필요할 수 있다(initialpose 재지정).
        respawn=True,
        respawn_delay=2.0,
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'scan_topic', default_value='/scan_merged',
            description='입력 LaserScan 토픽 (dual_laser_merger 병합 출력)'),
        DeclareLaunchArgument(
            'odom_topic', default_value='/odom',
            description='출력 Odometry 토픽 (mcl2d_localization_node 가 구독하는 이름)'),
        DeclareLaunchArgument(
            'publish_tf', default_value='true',
            description='odom→base_link TF 발행 여부. 실차는 true. '
                        '다른 오도 소스가 이미 같은 TF 를 내면 false 로 충돌 회피'),
        DeclareLaunchArgument(
            'force_3dof', default_value='true',
            description='Reg/Force3DoF — 평면 3자유도(x,y,yaw) 강제, z/roll/pitch=0. '
                        'TR_Nav 기준선을 그대로 재현하려면 false'),
        DeclareLaunchArgument(
            'reset_countdown', default_value='0',
            description='Odom/ResetCountdown — 연속 실패 N 프레임 후 자동 리셋. '
                        '0=비활성(기본, TR_Nav 와 동일). 효과 측정 후 1 이상으로 올릴 것'),
        icp_odometry,
    ])
