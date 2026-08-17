"""
SIL closed-loop launch for amr_spin_node.

체인:
  amr_spin_node ─ /motion/wheel_cmd/spin ─→ trnav_motion_mux
  trnav_motion_supervisor ─ service ─→ trnav_motion_mux  (active source = spin, id=3)
  trnav_motion_mux ─ /motor/wheel_cmd ─→ translate_sim_odom_node
  translate_sim_odom_node ─→ TF + /rtabmap/localization_pose + /imu/data + /wheel_motor_state

실 라이다·실 모터·실 IMU 미사용. 더미 safety publishers 추가.
spin 은 LocalizationMonitor 미사용 (IMU yaw 만 사용) → sil_pose_adapter 불포함.
translate_sim_odom 은 omega closed-loop (inline 2WS 는 x 간격이 분모: omega=(vy1-vy2)/dx, dyaw=omega·dt) 로
제자리 회전 yaw 적분을 시뮬 → /imu/data yaw 가 실제로 변하므로 spin 완주 검증 가능.
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.actions import IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    sim_node = Node(
        package='translate_sim_odom',
        executable='translate_sim_odom_node',
        name='translate_sim_odom_node',
        output='screen',
        parameters=[
            # 플랜트 동특성·시나리오
            PathJoinSubstitution([
                FindPackageShare('translate_sim_odom'),
                'config', 'sim_params.yaml']),
            # 휠 기하 정본 — 플랜트가 컨트롤러와 다른 기하로 돌면 SIL 이 검증하는 대상이 사라진다.
            #   플랫폼별로 갈리므로 런치가 고른다(공유 파일에 두면 두 플랫폼이 같은 값으로 돈다).
            PathJoinSubstitution([
                FindPackageShare('trnav_2ws_core'),
                'config', 'robot_geometry_2ws.yaml']),
        ],
    )

    mux_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('trnav_motion_mux'),
                'launch', 'trnav_motion_mux.launch.py'])
        )
    )

    supervisor_node = Node(
        package='trnav_motion_supervisor',
        executable='trnav_motion_supervisor_node',
        name='trnav_motion_supervisor',
        output='screen',
        parameters=[{'target_source_id': 3}],  # source 3 = spin
    )

    safety_watchdog_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('amr_safety_watchdog'),
                'launch', 'amr_safety_watchdog.launch.py'])
        )
    )

    # 더미 safety publishers (estop=false, lidar=safe)
    dummy_estop = ExecuteProcess(
        cmd=['ros2', 'topic', 'pub', '/safety/estop',
             'std_msgs/msg/Bool', '{data: false}', '--rate', '5'],
        output='screen',
    )
    dummy_lidar = ExecuteProcess(
        cmd=['ros2', 'topic', 'pub', '/safety/lidar',
             'trnav_msgs/msg/SafetyStatus',
             '{raw_data_safety_st: 0, field_data_safety_st: 0}',
             '--rate', '5'],
        output='screen',
    )

    spin_node = Node(
        package='trnav_2ws_action_server',
        executable='amr_spin_node',
        name='trnav_spin_node',
        output='screen',
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_2ws_action_server'),
            'config', 'spin_params.yaml'])],
    )

    return LaunchDescription([
        sim_node,
        mux_launch,
        supervisor_node,
        safety_watchdog_launch,
        dummy_estop,
        dummy_lidar,
        spin_node,
    ])
