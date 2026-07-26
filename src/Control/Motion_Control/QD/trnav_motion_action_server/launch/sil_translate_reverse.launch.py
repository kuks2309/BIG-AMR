"""
SIL closed-loop launch for amr_translate_reverse_node.

체인:
  amr_translate_reverse_node ─ /motion/wheel_cmd/translate_reverse ─→ trnav_motion_mux
  trnav_motion_supervisor ─ service ─→ trnav_motion_mux  (active source = translate_reverse, id=2)
  trnav_motion_mux ─ /motor/wheel_cmd ─→ translate_sim_odom_node
  translate_sim_odom_node ─→ TF + /rtabmap/localization_pose + /imu/data + /wheel_motor_state
                            ─→ amr_translate_reverse_node (피드백)

실 라이다·실 모터·실 IMU 미사용. 더미 safety publishers 추가.

검증 시나리오:
  - 정렬: yaw=0, start=(1,0)→end=(0,0) — 차량 yaw 그대로 후진
  - 비정렬: yaw=0, start=(0,0)→end=(-1,+0.176) — e_theta_init≈10°
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
        parameters=[PathJoinSubstitution([
            FindPackageShare('translate_sim_odom'),
            'config', 'sim_params.yaml'])],
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
        parameters=[{'target_source_id': 2}],  # source 2 = translate_reverse
    )

    safety_watchdog_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('amr_safety_watchdog'),
                'launch', 'amr_safety_watchdog.launch.py'])
        )
    )

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

    translate_reverse_node = Node(
        package='trnav_motion_action_server',
        executable='amr_translate_reverse_node',
        name='trnav_translate_reverse_node',
        output='screen',
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_motion_action_server'),
            'config', 'translate_reverse_params.yaml'])],
    )

    return LaunchDescription([
        sim_node,
        mux_launch,
        supervisor_node,
        safety_watchdog_launch,
        dummy_estop,
        dummy_lidar,
        translate_reverse_node,
    ])
