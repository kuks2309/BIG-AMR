"""
SIL closed-loop launch for amr_mpc_reverse_node.

체인:
  amr_mpc_reverse_node ─ /motion/wheel_cmd/mpc_reverse ─→ trnav_motion_mux
  trnav_motion_supervisor ─ service ─→ trnav_motion_mux  (active source = mpc_reverse, id=10)
  trnav_motion_mux ─ /motor/wheel_cmd ─→ translate_sim_odom_node
  translate_sim_odom_node ─→ TF + /rtabmap/localization_pose + /imu/data + /wheel_motor_state

실 라이다·실 모터·실 IMU 미사용. 더미 safety publishers 추가.
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

    # SIL 전용 pose type adapter (2026-08-06 추가)
    # /rtabmap/localization_pose (PoseWithCovarianceStamped, SensorDataQoS)
    #   → /robot_pose (PoseStamped, RELIABLE depth=10)
    # LocalizationMonitor 는 **TF 가 아니라 /robot_pose 토픽 캐시**만 쓴다
    # (localization_monitor.cpp:137-150). SIL 에선 이 어댑터가 그 토픽을 낸다.
    # 없으면 액션이 시작 즉시 abort(-3) 한다 — 에러 문구는
    # "TF2 map->base_link not available" 이지만 실제 원인은 이 토픽 부재다.
    # ⚠ 실차에서 /robot_pose 를 무엇이 내는지는 **이 저장소에서 확인되지 않는다.**
    #   QD 문서가 `src/Navigation/trnav_pose_publisher` 를 가리키나 그 경로는 부재이고
    #   (src/Navigation/ = icp_odometry_bringup · mcl2d_*), 근거는 sil_pose_adapter_node.cpp:8
    #   주석 한 줄뿐이다. 실기 브링업에서 발행자를 확인할 것.
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
        parameters=[{'target_source_id': 9}],  # source 9 = mpc_reverse (2026-05-16 10→9)
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
        sim_node,
        pose_adapter_launch,
        mux_launch,
        supervisor_node,
        safety_watchdog_launch,
        dummy_estop,
        dummy_lidar,
        mpc_reverse_node,
    ])
