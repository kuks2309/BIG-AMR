"""
HIL closed-loop launch for amr_mpc_reverse_node.

체인:
  amr_mpc_reverse_node ─ /motion/wheel_cmd/mpc_reverse ─→ trnav_motion_mux
  trnav_motion_supervisor ─ service ─→ trnav_motion_mux  (active source = mpc_reverse, id=9)
  trnav_motion_mux ─ /motor/wheel_cmd ─→ 실차 amr_canopen_motor_driver
  실차 RTAB-Map ─→ /rtabmap/localization_pose + TF map→base_link
  실차 IMU ─→ /imu/data
  실차 motor feedback ─→ /wheel_motor_state

translate_sim_odom 미사용. safety 신호는 실 하드웨어(amr_safety_watchdog)에서 공급.
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
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
        parameters=[{'target_source_id': 9}],  # source 9 = mpc_reverse (2026-05-16 10→9)
    )

    safety_watchdog_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('amr_safety_watchdog'),
                'launch', 'amr_safety_watchdog.launch.py'])
        )
    )

    mpc_reverse_node = Node(
        package='trnav_2ws_action_server',
        executable='amr_mpc_reverse_node',
        name='trnav_mpc_reverse_node',
        output='screen',
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_2ws_action_server'),
            'config', 'mpc_reverse_params.yaml'])],
    )

    return LaunchDescription([
        mux_launch,
        supervisor_node,
        safety_watchdog_launch,
        mpc_reverse_node,
    ])
