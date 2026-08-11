"""
SIL(Software In the Loop) closed-loop launch for amr_yaw_control_node.

체인:
  amr_yaw_control_node ─ /motion/wheel_cmd/yaw_control ─→ trnav_motion_mux
  trnav_motion_supervisor ─ service ─→ trnav_motion_mux  (active source = yaw_control, id=6)
  trnav_motion_mux ─ /motor/wheel_cmd ─→ translate_sim_odom_node
  translate_sim_odom_node ─→ map→base_link TF + /rtabmap/localization_pose + /imu/data
                             + /wheel_motor_state
  sil_pose_adapter_node ─ /rtabmap/localization_pose ─→ /robot_pose (PoseStamped)

**다른 SIL 런치와 다른 점 — `sil_pose_adapter_node` 를 포함한다.**
`turn`·`spin` 등은 IMU yaw 만 쓰고 `LocalizationMonitor` 를 쓰지 않아 어댑터가 필요 없다.
`yaw_control` 은 다르다:
  · 시작 시 `yaw_offset = start_yaw_map − start_yaw_imu` 를 맵 자세로 잡는다(TF 경유)
  · 주행 중 헤딩 발산 탐지(`status −7`)가 맵 yaw 와 대조한다
  · `LocalizationMonitor` 가 `/robot_pose`(PoseStamped)를 구독한다
어댑터는 플랜트의 `/rtabmap/localization_pose`(PoseWithCovarianceStamped, BEST_EFFORT)를
`/robot_pose`(PoseStamped, RELIABLE)로 변환한다. 기본 토픽이 그대로 맞아 리맵이 필요 없다.

⚠ `yaw_control` 의 종료 조건은 **거리**다(헤딩 수렴이 아니다). 헤딩은 추종 목표일 뿐이며
   목표 heading 에 못 닿아도 `target_distance` 를 채우면 성공으로 끝난다. 헤딩 권한은
   `dψ/ds = tan(δ)/L` 로 주행거리에 비례하므로 거리와 게인을 함께 잡아야 한다.

실 라이다·실 모터·실 IMU 미사용. 더미 safety publishers 추가.
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    # ── 플랜트 동특성 인자 ──
    # 기본값 0 = 제한 없음 = 즉응 거동. 실기 유래값을 쓰려면 명시적으로 준다:
    #   drive_decel:=0.0833 drive_accel:=0.0833 steer_rate:=57.1
    # ⚠ 즉응 플랜트는 조향 지연이 없어 `TransientGuard` 의 `gate_blocked` 가 발생하지 않는다 —
    #   조향 미도달 감시(`status −8`)를 SIL 로 보려면 `steer_rate` 를 낮게 주어야 한다.
    args = [
        DeclareLaunchArgument('drive_accel', default_value='0.0',
                              description='구동 가속 한계 m/s² (0=제한없음)'),
        DeclareLaunchArgument('drive_decel', default_value='0.0',
                              description='구동 감속 한계 m/s² (0=제한없음). 실기 유래 0.0833'),
        DeclareLaunchArgument('steer_rate', default_value='0.0',
                              description='조향 슬루율 deg/s (0=제한없음). 설정 유도 57.1'),
        DeclareLaunchArgument('imu_yaw_noise', default_value='0.0',
                              description='발행 yaw 잡음 1σ deg (0=무잡음). 지상진값은 불변'),
    ]

    def _f(name):
        return ParameterValue(LaunchConfiguration(name), value_type=float)

    sim_node = Node(
        package='translate_sim_odom',
        executable='translate_sim_odom_node',
        name='translate_sim_odom_node',
        output='screen',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('translate_sim_odom'),
                'config', 'sim_params.yaml']),
            {   # YAML 뒤에 오므로 이 값이 우선한다
                'drive_accel_mps2': _f('drive_accel'),
                'drive_decel_mps2': _f('drive_decel'),
                'steer_rate_dps': _f('steer_rate'),
                'imu_yaw_noise_deg': _f('imu_yaw_noise'),
            },
        ],
    )

    # /rtabmap/localization_pose (PoseWithCovarianceStamped) → /robot_pose (PoseStamped).
    # LocalizationMonitor 를 쓰는 SIL 런치가 공통으로 포함한다 — sil_spin·sil_turn·sil_turn_reverse 만 제외.
    pose_adapter_node = Node(
        package='sil_pose_adapter',
        executable='sil_pose_adapter_node',
        name='sil_pose_adapter_node',
        output='screen',
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
        parameters=[{'target_source_id': 6}],  # source 6 = yaw_control
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

    yaw_control_node = Node(
        package='trnav_2ws_action_server',
        executable='amr_yaw_control_node',
        name='trnav_yaw_control_node',
        output='screen',
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_2ws_action_server'),
            'config', 'yaw_control_params.yaml'])],
    )

    return LaunchDescription(args + [
        sim_node,
        pose_adapter_node,
        mux_launch,
        supervisor_node,
        safety_watchdog_launch,
        dummy_estop,
        dummy_lidar,
        yaw_control_node,
    ])
