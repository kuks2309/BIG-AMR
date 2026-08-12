"""
SIL closed-loop launch for amr_crab_linear_node.

체인:
  amr_crab_linear_node ─ /motion/wheel_cmd/crab_linear ─→ trnav_motion_mux
  trnav_motion_supervisor ─ service ─→ trnav_motion_mux  (active source = crab_linear, id=4)
  trnav_motion_mux ─ /motor/wheel_cmd ─→ translate_sim_odom_node
  translate_sim_odom_node ─→ TF + /rtabmap/localization_pose + /imu/data + /wheel_motor_state
  sil_pose_adapter_node  ─ /rtabmap/localization_pose ─→ /robot_pose
                            ─→ amr_crab_linear_node (LocalizationMonitor 피드백)

실 라이다·실 모터·실 IMU 미사용. 더미 safety publishers 추가.
sil_pose_adapter_node 는 SIL 전용 — PoseWithCovarianceStamped → PoseStamped
타입 변환만 수행하여 LocalizationMonitor /robot_pose cache 를 채운다.
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
            FindPackageShare('sil_pose_adapter'),
            'config', 'crab_linear_sim_params.yaml'])],
    )

    # SIL 전용 pose type adapter
    # /rtabmap/localization_pose (PoseWithCovarianceStamped, SensorDataQoS)
    #   → /robot_pose (PoseStamped, RELIABLE depth=10)
    # LocalizationMonitor 가 /robot_pose cache 만 사용하므로 SIL 에선 필수.
    pose_adapter_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('sil_pose_adapter'),
                'launch', 'sil_pose_adapter.launch.py'])
        )
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
        parameters=[{'target_source_id': 4}],  # source 4 = crab_linear
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
             # 워치독이 구독하는 타입과 일치해야 한다 — trnav_msgs::msg::SafetyStatus
             #   (amr_safety_watchdog_node.cpp:144).
             'trnav_msgs/msg/SafetyStatus',
             '{raw_data_safety_st: 0, field_data_safety_st: 0}',
             '--rate', '5'],
        output='screen',
    )

    crab_linear_node = Node(
        package='trnav_2ws_action_server',
        executable='amr_crab_linear_node',
        name='trnav_crab_linear_node',
        output='screen',
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_2ws_action_server'),
            'config', 'crab_linear_params.yaml'])],
    )

    return LaunchDescription([
        sim_node,
        pose_adapter_launch,
        mux_launch,
        supervisor_node,
        safety_watchdog_launch,
        dummy_estop,
        dummy_lidar,
        crab_linear_node,
    ])
