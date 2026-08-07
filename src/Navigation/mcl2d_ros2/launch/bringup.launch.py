# 위치추정 구동 체인을 한 번에 띄운다.
#
#   sick_safetyscanners2 x2 ──> dual_laser_merger ──/scan_merged──> icp_odometry ──/odom──┐
#                          └────/scan_front,/scan_rear──────────────────────────────────> mcl2d
#
# 계층별로 끌 수 있다 — 이미 떠 있는 것을 중복 기동하지 않도록:
#   ros2 launch mcl2d_ros2 bringup.launch.py map_path:=/…/map/x.smap
#   ros2 launch mcl2d_ros2 bringup.launch.py map_path:=… lidar:=false        # 라이다는 이미 떠 있음
#   ros2 launch mcl2d_ros2 bringup.launch.py map_path:=… lidar:=false icp:=false
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
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
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
    loc_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            share('mcl2d_ros2', 'launch', 'localization.launch.py')),
        condition=IfCondition(LaunchConfiguration('localization')),
        launch_arguments={
            'map_path': LaunchConfiguration('map_path'),
            'params_file': LaunchConfiguration('params_file'),
        }.items(),
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
        lidar_launch,
        icp_launch,
        loc_launch,
    ])
