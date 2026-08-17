# SIL 플랜트(translate_sim_odom_node) 단독 기동.
#
# 파라미터는 두 겹이다:
#   sim_params.yaml   — 플랜트 동특성·시나리오 (플랫폼 무관)
#   robot_geometry_*  — 휠 기하 정본 (플랫폼별)
#
# 기하를 공유 파일에 두지 않는 이유: 2WS·QD SIL 이 같은 sim_params.yaml 을 받으므로
#   거기에 기하를 두면 **두 플랫폼이 같은 기하로 돈다.** 그러면 플랜트가 컨트롤러와 다른
#   기하로 도는 쪽이 생기고, SIL 이 검증하는 대상이 사라진다.
#
#   ros2 launch translate_sim_odom translate_sim_odom.launch.py \
#        geometry_package:=trnav_motion_core geometry_file:=robot_geometry_qd.yaml
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'geometry_package', default_value='trnav_2ws_core',
            description='휠 기하 정본을 담은 패키지. 이 저장소 기체는 Foil_A082(2WS) 다 — '
                        'QD 플랜트를 띄우려면 trnav_motion_core 로 바꾼다'),
        DeclareLaunchArgument(
            'geometry_file', default_value='robot_geometry_2ws.yaml',
            description='휠 기하 정본 파일명 (robot_geometry_2ws.yaml | robot_geometry_qd.yaml)'),
        Node(
            package='translate_sim_odom',
            executable='translate_sim_odom_node',
            name='translate_sim_odom_node',
            output='screen',
            parameters=[
                PathJoinSubstitution([
                    FindPackageShare('translate_sim_odom'),
                    'config', 'sim_params.yaml']),
                PathJoinSubstitution([
                    FindPackageShare(LaunchConfiguration('geometry_package')),
                    'config', LaunchConfiguration('geometry_file')]),
            ],
        ),
    ])
