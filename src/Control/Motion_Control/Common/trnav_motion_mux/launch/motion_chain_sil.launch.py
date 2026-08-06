"""
모션→모터 **전 체인** 통합 런치 (SIL / Software In the Loop).

지금까지의 SIL 런치(`sil_*.launch.py`)는 플랜트가 `/motor/wheel_cmd` 를 **직접** 받아
`amr_motor_cmd_translator` 와 `can_relay` 를 건너뛰었다. 즉 SI→raw 환산과 조향 원점·클램프가
체인 안에서 한 번도 함께 돌아본 적이 없다. 본 런치가 그 두 노드를 체인에 넣는다.

체인:
  액션 서버 ─ /motion/wheel_cmd/<action> ─→ trnav_motion_mux
  trnav_motion_mux ─ /motor/wheel_cmd ─┬─→ amr_motor_cmd_translator ─ /motor/low_cmd ─→ can_relay
                                        └─→ translate_sim_odom (플랜트: TF·pose·imu·wheel_state)
  can_relay ─ /motor/low_state ─→ amr_motor_cmd_translator (역환산)

translator 의 legacy `wheel_motor_state` 발행은 **끈다** — 플랜트가 같은 토픽을 내므로
켜 두면 발행자가 둘이 되어 액션 서버가 어느 쪽을 받을지 알 수 없다.

## 차량은 움직이지 않는다

`link:=mock` 이 기본이라 하드웨어에 **연결조차 하지 않는다**(`driver_node.py:167-169`).
실 링크(`link:=panda`)로 바꿔도 can_relay 는 기동만으로 제어권을 잡지 않으며
(`driver_node.py:231`), 제어권 없이는 백엔드가 기동을 거부한다(`backend.py:170-171`).
조향은 호밍 전까지 거부된다(`require_homed_for_steer`). 실제 구동은 명시 3단계가 필요하다:

    ros2 service call /can_relay_node/engage std_srvs/srv/SetBool "{data: true}"
    ros2 service call /can_relay_node/home   std_srvs/srv/Trigger {}
    ros2 action send_goal /amr_motion_<action>_abstract ...

## 인자

  link         mock | panda      (기본 mock — 하드웨어 무접속)
  action       crab_linear | spin | turn   (기동할 액션 서버, 기본 crab_linear)
  source_id    mux 활성 소스 id  (기본 4 = crab_linear. spin=3, turn=5)
  plant        true | false      (translate_sim_odom 기동 여부, 기본 true)
"""

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, GroupAction,
                            IncludeLaunchDescription)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (LaunchConfiguration, PathJoinSubstitution,
                                  PythonExpression)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    arg_link = DeclareLaunchArgument(
        'link', default_value='mock', choices=['mock', 'panda'],
        description='can_relay 링크. mock = 하드웨어 무접속(기본)')
    arg_action = DeclareLaunchArgument(
        'action', default_value='crab_linear',
        choices=['crab_linear', 'spin', 'turn'],
        description='기동할 액션 서버')
    arg_source = DeclareLaunchArgument(
        'source_id', default_value='4',
        description='mux 활성 소스 id (crab_linear=4, spin=3, turn=5)')
    arg_plant = DeclareLaunchArgument(
        'plant', default_value='true', choices=['true', 'false'],
        description='translate_sim_odom(플랜트) 기동 여부')

    link = LaunchConfiguration('link')
    action = LaunchConfiguration('action')
    source_id = LaunchConfiguration('source_id')
    plant = LaunchConfiguration('plant')

    # ── 플랜트 (SIL 전용) ────────────────────────────────────────────────
    plant_node = Node(
        package='translate_sim_odom',
        executable='translate_sim_odom_node',
        name='translate_sim_odom_node',
        output='screen',
        condition=IfCondition(plant),
        parameters=[PathJoinSubstitution([
            FindPackageShare('translate_sim_odom'), 'config', 'sim_params.yaml'])],
    )

    # SIL 전용 pose 어댑터 — PoseWithCovarianceStamped → PoseStamped(/robot_pose).
    # ⚠ crab_linear 의 LocalizationMonitor 가 /robot_pose 를 쓴다. 빼면 크랩이
    #   "TF2 map->base_link not available" 로 즉시 abort 한다(2026-08-06 실측).
    #   spin·turn 은 IMU yaw 만 쓰므로 있어도 무해하다.
    pose_adapter_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('sil_pose_adapter'), 'launch', 'sil_pose_adapter.launch.py'])),
        condition=IfCondition(plant))

    # ── 체인 중간: mux → translator → can_relay ─────────────────────────
    mux_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('trnav_motion_mux'), 'launch', 'trnav_motion_mux.launch.py'])))

    translator_node = Node(
        package='amr_motor_cmd_translator',
        executable='amr_motor_cmd_translator_node',
        name='amr_motor_cmd_translator',
        output='screen',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('amr_motor_cmd_translator'),
                'config', 'amr_motor_cmd_translator_qd.yaml']),
            # 플랜트가 같은 토픽을 내므로 발행자가 둘이 되지 않게 끈다.
            {'publish_legacy_wheel_motor_state': False,
             'publish_legacy_wheel_motor_state_detailed': False},
        ],
    )

    can_relay_node = Node(
        package='can_relay',
        executable='can_relay_node',
        name='can_relay_node',
        output='screen',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('can_relay'), 'config', 'can_relay.yaml']),
            PathJoinSubstitution([
                FindPackageShare('can_relay'), 'config', 'machine', 'foil_a082.yaml']),
            {'link': link},
        ],
    )

    # ── 소스 선택 · 안전 ────────────────────────────────────────────────
    supervisor_node = Node(
        package='trnav_motion_supervisor',
        executable='trnav_motion_supervisor_node',
        name='trnav_motion_supervisor',
        output='screen',
        parameters=[{'target_source_id': source_id}],
    )

    safety_watchdog_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('amr_safety_watchdog'), 'launch', 'amr_safety_watchdog.launch.py'])))

    dummy_estop = ExecuteProcess(
        cmd=['ros2', 'topic', 'pub', '/safety/estop',
             'std_msgs/msg/Bool', '{data: false}', '--rate', '5'],
        output='log')
    dummy_lidar = ExecuteProcess(
        cmd=['ros2', 'topic', 'pub', '/safety/lidar',
             'trnav_msgs/msg/SafetyStatus',
             '{raw_data_safety_st: 0, field_data_safety_st: 0}', '--rate', '5'],
        output='log')

    # ── 액션 서버 (하나만) ──────────────────────────────────────────────
    def action_node(name, executable, node_name, params):
        return Node(
            package='trnav_2ws_action_server', executable=executable, name=node_name,
            output='screen',
            condition=IfCondition(PythonExpression(["'", action, "' == '", name, "'"])),
            parameters=[PathJoinSubstitution([
                FindPackageShare('trnav_2ws_action_server'), 'config', params])])

    actions = GroupAction([
        action_node('crab_linear', 'amr_crab_linear_node', 'trnav_crab_linear_node',
                    'crab_linear_params.yaml'),
        action_node('spin', 'amr_spin_node', 'trnav_spin_node', 'spin_params.yaml'),
        action_node('turn', 'amr_turn_node', 'trnav_turn_node', 'turn_params.yaml'),
    ])

    return LaunchDescription([
        arg_link, arg_action, arg_source, arg_plant,
        plant_node,
        pose_adapter_launch,
        mux_launch,
        translator_node,
        can_relay_node,
        supervisor_node,
        safety_watchdog_launch,
        dummy_estop,
        dummy_lidar,
        actions,
    ])
