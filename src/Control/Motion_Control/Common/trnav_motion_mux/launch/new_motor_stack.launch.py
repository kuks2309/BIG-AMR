"""
new_motor_stack.launch.py

모터 파이프라인 통합 런치.

LaunchArgument:
  use_new_motor_stack (default: 'true')
    true  : amr_motor_cmd_translator + amr_canopen_motor_driver  (실차 — CAN 필요)
    false : tc_motors/motors_node  (레거시 경로 롤백)
    sim   : amr_motor_cmd_translator + amr_canopen_sim  (SIL — CAN 불필요)

trnav_motion_mux 는 이 런치에서 실행하지 않는다.
  이유: mux 는 모든 모드에서 공통 필요하며 상위 런치(amr_full_stack 등)가 이미 관리한다.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.conditions import LaunchConfigurationEquals
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    arg_mode = DeclareLaunchArgument(
        'use_new_motor_stack',
        default_value='true',
        choices=['true', 'false', 'sim'],
        description=(
            'true=translator+amr_canopen_motor_driver (실차, CAN 필요), '
            'false=tc_motors 레거시, '
            'sim=translator+amr_canopen_sim (SIL)'
        ),
    )

    mode = LaunchConfiguration('use_new_motor_stack')

    # ---------- 공통 노드 정의 ----------

    node_translator = Node(
        package='amr_motor_cmd_translator',
        executable='amr_motor_cmd_translator_node',
        name='amr_motor_cmd_translator',
        output='screen',
        parameters=[
            # 2026-07-13 수정: 기존 'amr_motor_cmd_translator.yaml' 은 **존재하지 않는 파일**이라
            # params 로드가 조용히 실패 → 노드가 코드 기본값으로만 동작했다(조향 영점 보정 미적용).
            # 실제 파일명은 _qd 접미사. (config/ 에 amr_motor_cmd_translator_qd.yaml 만 존재)
            PathJoinSubstitution([
                FindPackageShare('amr_motor_cmd_translator'),
                'config', 'amr_motor_cmd_translator_qd.yaml',
            ])
        ],
    )

    node_canopen_driver = Node(
        package='amr_canopen_motor_driver',
        executable='amr_canopen_motor_driver_node',
        name='amr_canopen_motor_driver',
        output='screen',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('amr_canopen_motor_driver'),
                'config', 'amr_canopen_motor_driver.yaml',
            ])
        ],
    )

    node_canopen_sim = Node(
        package='amr_canopen_sim',
        executable='amr_canopen_sim_node',
        name='amr_canopen_sim',
        output='screen',
        parameters=[
            PathJoinSubstitution([
                FindPackageShare('amr_canopen_sim'),
                'config', 'amr_canopen_sim.yaml',
            ])
        ],
    )

    node_legacy = Node(
        package='tc_motors',
        executable='motors_node',
        name='motors_canopen',
        output='screen',
    )

    # ---------- 모드별 그룹 ----------

    group_true = GroupAction(
        condition=LaunchConfigurationEquals('use_new_motor_stack', 'true'),
        actions=[node_translator, node_canopen_driver],
    )

    group_sim = GroupAction(
        condition=LaunchConfigurationEquals('use_new_motor_stack', 'sim'),
        actions=[node_translator, node_canopen_sim],
    )

    group_false = GroupAction(
        condition=LaunchConfigurationEquals('use_new_motor_stack', 'false'),
        actions=[node_legacy],
    )

    return LaunchDescription([
        arg_mode,
        group_true,
        group_sim,
        group_false,
    ])
