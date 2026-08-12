"""
SIL closed-loop launch for amr_mpc_node.

체인:
  amr_mpc_node ─ /motion/wheel_cmd/mpc ─→ trnav_motion_mux
  trnav_motion_supervisor ─ service ─→ trnav_motion_mux  (active source = mpc, id=8)
  trnav_motion_mux ─ /motor/wheel_cmd ─→ translate_sim_odom_node
  translate_sim_odom_node ─→ TF + /rtabmap/localization_pose + /imu/data + /wheel_motor_state
                            ─→ amr_mpc_node (피드백)

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
    # "/robot_pose 미수신 또는 낡음(신선도 초과) — TF 문제가 아니다 …" 다
    # (mpc_action_server.cpp:487).
    # ⚠ 실차에서 /robot_pose 를 무엇이 내는지는 **이 저장소에서 확인되지 않는다.**
    #   QD 문서가 `src/Navigation/trnav_pose_publisher` 를 가리키나 그 경로는 부재이고
    #   (저장소 유일 후보 seer_pose_publisher 의 기본 발행은 `/seer/robot_pose` 라 그대로는 맞지 않는다),
    #   배선 정리는 docs/code_review/pose-topic-wiring/2026-08-10.md 를 볼 것.
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
        parameters=[{'target_source_id': 8}],  # source 8 = mpc (2026-05-16 7→8)
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

    mpc_node = Node(
        package='trnav_2ws_action_server',
        executable='amr_mpc_node',
        name='trnav_mpc_node',
        output='screen',
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_2ws_action_server'),
            'config', 'mpc_params.yaml'])],
    )

    return LaunchDescription([
        sim_node,
        pose_adapter_launch,
        mux_launch,
        supervisor_node,
        safety_watchdog_launch,
        dummy_estop,
        dummy_lidar,
        mpc_node,
    ])
