"""
SIL(Software In the Loop) closed-loop launch for amr_turn_node.

체인:
  amr_turn_node ─ /motion/wheel_cmd/turn ─→ trnav_motion_mux
  trnav_motion_supervisor ─ service ─→ trnav_motion_mux  (active source = turn, id=5)
  trnav_motion_mux ─ /motor/wheel_cmd ─→ translate_sim_odom_node
  translate_sim_odom_node ─→ TF + /rtabmap/localization_pose + /imu/data + /wheel_motor_state

turn 은 **반경 R 의 원호 주행**이다(spin 은 제자리 회전). `v = ω·R` 로 병진과 회전이 함께
나가므로 플랜트가 둘 다 되돌려야 검증이 성립한다 — spin SIL 이 회전만 보는 것과 다르다.

turn 은 spin 과 마찬가지로 **IMU yaw 만** 쓰고 LocalizationMonitor 를 쓰지 않는다
(turn_action_server.cpp 는 robot_pose 를 구독하지 않는다) → sil_pose_adapter 불포함.

⚠ 2026-08-05 신설. 상류(kuks2309/TR_Nav_ros2_ws)에도 sil_turn 은 없다 — turn 은 상류에서도
   SIL 로 돌려본 적이 없다(있는 것은 플랜트 없는 turn.launch.py 뿐).

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
    # ── 플랜트 동특성 인자 (2026-08-06 추가) ──
    # 기본값 0 = 제한 없음 = **종전 즉응 거동 그대로**. 인자를 주지 않으면 이 런치의
    # 결과는 추가 전과 동일하다. 잔여각 바닥값을 재려면 실기 유래값을 명시적으로 준다:
    #   drive_decel:=0.0833 drive_accel:=0.0833 steer_rate:=57.1
    # 근거는 translate_sim_odom_node.hpp 주석(감속=실측 역산 / 조향=설정 유도) 참조.
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
            # 휠 기하 정본 — 플랜트가 컨트롤러와 다른 기하로 돌면 SIL 이 검증하는 대상이 사라진다.
            #   플랫폼별로 갈리므로 런치가 고른다(공유 파일에 두면 두 플랫폼이 같은 값으로 돈다).
            PathJoinSubstitution([
                FindPackageShare('trnav_2ws_core'),
                'config', 'robot_geometry_2ws.yaml']),
            {   # YAML 뒤에 오므로 이 값이 우선한다
                'drive_accel_mps2': _f('drive_accel'),
                'drive_decel_mps2': _f('drive_decel'),
                'steer_rate_dps': _f('steer_rate'),
                'imu_yaw_noise_deg': _f('imu_yaw_noise'),
            },
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
        parameters=[{'target_source_id': 5}],  # source 5 = turn
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

    turn_node = Node(
        package='trnav_2ws_action_server',
        executable='amr_turn_node',
        name='trnav_turn_node',
        output='screen',
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_2ws_action_server'),
            'config', 'turn_params.yaml'])],
    )

    return LaunchDescription(args + [
        sim_node,
        mux_launch,
        supervisor_node,
        safety_watchdog_launch,
        dummy_estop,
        dummy_lidar,
        turn_node,
    ])

