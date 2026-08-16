"""
SIL(Software In the Loop) closed-loop launch for amr_line_follow_node.

체인 — **폐루프가 닫힌다**:
  amr_line_follow_node ─ /motion/wheel_cmd/line_follow ─→ trnav_motion_mux
  trnav_motion_supervisor ─ service ─→ trnav_motion_mux  (active source = line_follow, id=13)
  trnav_motion_mux ─ /motor/wheel_cmd ─→ translate_sim_odom_node
  translate_sim_odom_node ─→ map→base_link TF + /rtabmap/localization_pose + /imu/data
                             + /wheel_motor_state
  sil_pose_adapter_node ─ /rtabmap/localization_pose ─→ /robot_pose (PoseStamped)
  line_sim_sensor_node ─ map→base_link TF ─→ /line/error ─→ amr_line_follow_node
                                                              └─ 여기서 고리가 닫힌다

**다른 SIL 런치와 다른 점 — `line_sim_sensor_node` 를 포함한다.**
라인 추종은 영상 폐루프다. 오차를 고정값으로 주입하면 「조향 부호가 맞는가」까지만 보이고
**「그 조향이 오차를 줄이는가」는 보이지 않는다.** 가상 센서가 자세로부터 오차를 역산해야
수렴을 관측할 수 있다.

`sil_pose_adapter_node` 도 포함한다 — `line_follow` 는 `LocalizationMonitor`(`/robot_pose`)로
거리를 적산하고 측위 두절·점프를 감시한다(`yaw_control` 과 같은 이유).

라인 배치는 `line_sim_sensor/config/line_sim_params.yaml` 이 정하며 기준계는 **로봇 시작
자세**다(`line_frame: start`). 플랜트 초기 자세가 시나리오 웨이포인트(4.952, -2.327)이므로
맵 절대좌표로 놓으면 라인이 화각 밖에 떨어진다. 기본값은 시작 지점 왼쪽 10 cm 에 나란한
10 m 직선이라 **초기 횡오차에서 시작해 수렴을 보고**, 라인 끝에서 소실 → coast →
abort(-9) 경로까지 이어진다.

⚠ 즉응 플랜트(기본)는 조향 지연이 없어 `TransientGuard` 의 `gate_blocked` 가 발생하지 않는다 —
   조향 미도달 감시(`status −8`)를 보려면 `steer_rate` 를 낮게 준다.

실 라이다·실 모터·실 카메라 미사용. 더미 safety publishers 추가.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    args = [
        DeclareLaunchArgument('drive_accel', default_value='0.0',
                              description='구동 가속 한계 m/s² (0=제한없음)'),
        DeclareLaunchArgument('drive_decel', default_value='0.0',
                              description='구동 감속 한계 m/s² (0=제한없음). 실기 유래 0.0833'),
        DeclareLaunchArgument('steer_rate', default_value='0.0',
                              description='조향 슬루율 deg/s (0=제한없음). 설정 유도 57.1'),
        DeclareLaunchArgument('imu_yaw_noise', default_value='0.0',
                              description='발행 yaw 잡음 1σ deg (0=무잡음)'),
        DeclareLaunchArgument('line_y0', default_value='0.10',
                              description='라인의 초기 횡 offset m (로봇 왼쪽이 +)'),
        DeclareLaunchArgument('line_heading_deg', default_value='0.0',
                              description='라인 heading deg (맵 기준)'),
        DeclareLaunchArgument('line_length', default_value='10.0',
                              description='라인 길이 m — 끝에서 소실 경로가 시험된다'),
        DeclareLaunchArgument('line_curvature', default_value='0.0',
                              description='라인 곡률 1/m (0=직선, +=좌선회). 반경 = 1/|값|'),
        DeclareLaunchArgument('direction', default_value='forward',
                              description='가상 센서 방향 — goal 의 reverse 와 맞춰야 한다'),
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

    pose_adapter_node = Node(
        package='sil_pose_adapter',
        executable='sil_pose_adapter_node',
        name='sil_pose_adapter_node',
        output='screen',
    )

    line_sensor_node = Node(
        package='line_sim_sensor',
        executable='line_sim_sensor_node',
        name='line_sim_sensor',
        output='screen',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('line_sim_sensor'),
                'config', 'line_sim_params.yaml']),
            {
                'line_y0': _f('line_y0'),
                'line_heading_deg': _f('line_heading_deg'),
                'line_length': _f('line_length'),
                'line_curvature': _f('line_curvature'),
                'direction': LaunchConfiguration('direction'),
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
        parameters=[{'target_source_id': 13}],  # source 13 = line_follow
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

    line_follow_node = Node(
        package='trnav_2ws_action_server',
        executable='amr_line_follow_node',
        name='trnav_line_follow_node',
        output='screen',
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_2ws_action_server'),
            'config', 'line_follow_params.yaml'])],
    )

    return LaunchDescription(args + [
        sim_node,
        pose_adapter_node,
        line_sensor_node,
        mux_launch,
        supervisor_node,
        safety_watchdog_launch,
        dummy_estop,
        dummy_lidar,
        line_follow_node,
    ])
