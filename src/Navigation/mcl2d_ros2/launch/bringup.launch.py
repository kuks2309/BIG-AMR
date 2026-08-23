# 위치추정 구동 체인을 한 번에 띄운다.
#
#   sick_safetyscanners2 x2 ──> dual_laser_merger ──/scan_merged──> icp_odometry ──/odom──┐
#                          └────/scan_front,/scan_rear──────────────────────────────────> mcl2d
#   smap_map_server(같은 map_path) ──/map(latch)──> rviz·costmap
#
# imu_fusion:=true 면 오도와 측위 사이에 융합기가 한 칸 들어간다(Seer 레거시 배선과 같은 자리):
#   icp_odometry ──/odom──┐
#                          ├─> odom_imu_ekf ──/odom_fused──> mcl2d
#   iahrs_driver ─/imu/data┘
#
#   ⚠ 기본값 false — IMU 를 못 받으면 융합기가 아무것도 발행하지 않아 측위가 이동량을 잃는다.
#     켜기 전에 /imu/data 가 실제로 흐르는지 확인할 것(융합기 /diagnostics 가 ERROR 로 드러낸다).
#   ⚠ 레거시의 융합 입력은 휠 오도였다. 여기서는 ICP 오도를 넣는다 — 휠 오도는 조향 부호가
#     확정되기 전까지(debt-004·debt-007) 신뢰할 수 없다.
#   측위는 오도 토픽을 **증분 예측**에만 쓰고 map→odom 은 TF 를 되짚어 역산하므로,
#     융합 토픽을 물려도 TF 체인은 어긋나지 않는다.
#
# 구동 한 줄 (라이다 + 오도메트리 + 측위 + 맵 서버 전부):
#   ros2 launch mcl2d_ros2 bringup.launch.py map_path:=/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/map/260709_test.smap
#   (rviz 까지 같이 띄우려면 로봇 화면에서 rviz:=true 를 덧붙인다 — DISPLAY 필요라 기본 false)
#
# 계층별로 끌 수 있다 — 이미 떠 있는 것을 중복 기동하지 않도록:
#   ros2 launch mcl2d_ros2 bringup.launch.py map_path:=… lidar:=false        # 라이다는 이미 떠 있음
#   ros2 launch mcl2d_ros2 bringup.launch.py map_path:=… lidar:=false icp:=false
#   ros2 launch mcl2d_ros2 bringup.launch.py map_path:=… map_server:=false   # /map 발행 불요 시
#
# ⚠ 전제 — 라이다 네트워크. 센서는 eth1 유선이고 호스트에 192.168.192.10/24 와 센서별 /32 라우트
#   (src 명시)가 있어야 한다. 재부팅하면 사라진다. 절차: docs/network/seer_network_access.md.
#   이 launch 는 네트워크를 건드리지 않는다 — 없으면 드라이버가 timeout 으로 죽는다.
#
# TF 소유권(코드리뷰 2026-08-07 H1): odom→base_link 는 icp_odometry, map→odom 은 mcl2d 가 낸다.
#   둘 다 base_link 를 자식으로 두지 않으므로 부모 중복이 생기지 않는다.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # ⚠ 포함 대상 경로는 **치환(substitution)으로** 만든다. get_package_share_directory() 를 쓰면
    #   런치 기술 생성 시점에 즉시 평가되어, lidar:=false 로 꺼 놓아도 그 패키지가 없으면
    #   PackageNotFoundError 로 전체가 죽는다(실측 확인). FindPackageShare 는 액션 실행 시점에
    #   풀리므로 조건이 거짓이면 아예 해석되지 않는다.
    def share(pkg, *parts):
        return PathJoinSubstitution([FindPackageShare(pkg), *parts])

    lidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            share('dual_laser_merger', 'launch', 'sick_with_merger.launch.py')),
        condition=IfCondition(LaunchConfiguration('lidar')),
    )
    icp_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            share('icp_odometry_bringup', 'launch', 'icp_odometry.launch.py')),
        condition=IfCondition(LaunchConfiguration('icp')),
    )
    fusion_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            share('odom_imu_ekf', 'launch', 'odom_imu_ekf.launch.py')),
        condition=IfCondition(LaunchConfiguration('imu_fusion')),
        launch_arguments={
            'odom_topic': LaunchConfiguration('odom_topic'),
            'imu_topic': LaunchConfiguration('imu_topic'),
            'fused_topic': '/odom_fused',
        }.items(),
    )
    # 측위가 구독할 오도. imu_fusion 일 때만 융합 출력으로 돌린다 — 꺼져 있으면 현행 그대로다.
    loc_odom_topic = PythonExpression(
        ["'/odom_fused' if '", LaunchConfiguration('imu_fusion'),
         "'.lower() in ('true', '1') else '", LaunchConfiguration('odom_topic'), "'"])
    loc_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            share('mcl2d_ros2', 'launch', 'localization.launch.py')),
        condition=IfCondition(LaunchConfiguration('localization')),
        launch_arguments={
            'map_path': LaunchConfiguration('map_path'),
            'params_file': LaunchConfiguration('params_file'),
            'odom_topic': loc_odom_topic,
        }.items(),
    )
    # 맵 서버 — 측위와 같은 .smap 을 OccupancyGrid(/map, latch)로 발행한다. rviz·costmap 소비용.
    map_server = Node(
        package='mcl2d_ros2',
        executable='smap_map_server',
        name='smap_map_server',
        parameters=[{'map_path': LaunchConfiguration('map_path')}],
        output='screen',
        condition=IfCondition(LaunchConfiguration('map_server')),
        # /map 은 latch — 새로 붙는 구독자(rviz·costmap)는 발행자가 살아 있어야 맵을
        # 받으므로 respawn 으로 발행자를 유지한다. rviz 는 사람이 여닫는 창이라 respawn 제외.
        respawn=True,
        respawn_delay=2.0,
    )
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', share('mcl2d_ros2', 'config', 'mcl2d_check.rviz')],
        output='screen',
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'map_path', default_value='',
            description='Seer .smap 절대경로. **필수** — 비우면 mcl2d 가 FATAL 로 죽는다'),
        DeclareLaunchArgument(
            'params_file', default_value=share('mcl2d_ros2', 'config', 'mcl2d.yaml'),
            description='mcl2d 파라미터 YAML'),
        DeclareLaunchArgument(
            'lidar', default_value='true',
            description='SICK 스캐너 2대 + dual_laser_merger 를 함께 띄운다'),
        DeclareLaunchArgument(
            'icp', default_value='true',
            description='icp_odometry(/odom, TF odom→base_link)를 함께 띄운다'),
        DeclareLaunchArgument(
            'localization', default_value='true',
            description='mcl2d 위치추정(/mcl_pose, TF map→odom)을 함께 띄운다'),
        DeclareLaunchArgument(
            'map_server', default_value='true',
            description='smap_map_server(/map latch, 같은 map_path)를 함께 띄운다'),
        DeclareLaunchArgument(
            'rviz', default_value='false',
            description='rviz2(mcl2d_check.rviz)를 함께 띄운다 — DISPLAY 필요, 로봇 화면에서만 true'),
        DeclareLaunchArgument(
            'imu_fusion', default_value='false',
            description='odom_imu_ekf 를 끼워 오도·IMU 융합본(/odom_fused)을 측위에 물린다. '
                        'IMU 미수신 시 융합기가 무발행이라 측위가 멈춘다 — 켜기 전 /imu/data 확인'),
        DeclareLaunchArgument(
            'odom_topic', default_value='/odom',
            description='오도메트리 토픽. imu_fusion 이면 융합기 입력, 아니면 측위 입력이 된다'),
        DeclareLaunchArgument(
            'imu_topic', default_value='/imu/data',
            description='IMU 토픽(iahrs_driver 발행). imu_fusion 일 때만 쓰인다'),
        lidar_launch,
        icp_launch,
        fusion_launch,
        loc_launch,
        map_server,
        rviz,
    ])
