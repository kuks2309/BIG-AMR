# SLAM 매핑 노드 단독 기동.
#
#   ros2 launch slam_karto_ros2 slam_mapping.launch.py
#   ros2 launch slam_karto_ros2 slam_mapping.launch.py save_path:=/home/nvidia/map/new.smap
#   ros2 launch slam_karto_ros2 slam_mapping.launch.py auto_start:=false
#
# ⚠ 입력(/scan_merged, /odom)은 이 런치가 띄우지 않는다. 라이다+병합기+ICP 오도메트리는
#   mcl2d_ros2 의 bringup 에서 localization:=false 로 띄우거나 각각 직접 띄운다:
#     ros2 launch dual_laser_merger sick_with_merger.launch.py
#     ros2 launch icp_odometry_bringup icp_odometry.launch.py
#
# ⚠ **mcl2d 와 동시에 띄우지 말 것.** 이 노드는 TF 를 내지 않지만, 매핑과 측위를 같이 돌리면
#   같은 /scan_merged·/odom 을 두 무거운 소비자가 나눠 갖고 map 프레임의 의미도 이중이 된다.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    params_file = LaunchConfiguration('params_file')
    save_path = LaunchConfiguration('save_path')
    auto_start = LaunchConfiguration('auto_start')

    default_params = PathJoinSubstitution(
        [FindPackageShare('slam_karto_ros2'), 'config', 'slam_mapping.yaml'])

    mapping_node = Node(
        package='slam_karto_ros2',
        executable='slam_mapping_node',
        name='slam_mapping',
        output='screen',
        # YAML 을 먼저 깔고 그 위에 런치 인자를 덮는다(뒤에 온 dict 가 이긴다).
        parameters=[params_file,
                    {'save_path': save_path,
                     'auto_start': auto_start}],
    )

    return LaunchDescription([
        DeclareLaunchArgument('params_file', default_value=default_params,
                              description='slam_mapping 파라미터 YAML'),
        DeclareLaunchArgument('save_path', default_value='',
                              description='~/save_map 이 쓸 .smap 절대경로 (비우면 save_map 실패)'),
        DeclareLaunchArgument('auto_start', default_value='true',
                              description='true 면 기동 즉시 스캔을 받는다 (false 면 ~/start_mapping 대기)'),
        mapping_node,
    ])
