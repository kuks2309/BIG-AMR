#!/usr/bin/env python3
"""
sim.launch.py — Foil_A082 (2WS inline dual-steer) Gazebo 시뮬레이션 기동.

띄우는 것:
    gzserver + gzclient (warehouse.world)
    robot_state_publisher   xacro → /robot_description + TF
    spawn_entity            로봇 스폰
    controller spawners     joint_state_broadcaster / steer / drive
    wheel_cmd_bridge        /cmd_vel · WheelSetArray → 조인트 명령  (모터계층 대체)
    wheel_odometry          /joint_states → /odom + odom→base_footprint TF

인자:
    gui:=false        headless (gzclient 생략)
    steer_lag:=0.8    조향 서보 1차 지연 재현 (기본 0 = 이상적)
    x:= y:= yaw:=     스폰 포즈
    rviz:=true        RViz 동시 기동

몰아보기:
    ros2 run teleop_twist_keyboard teleop_twist_keyboard
"""

import os

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, ExecuteProcess,
                            IncludeLaunchDescription, RegisterEventHandler,
                            SetEnvironmentVariable)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _strip_comments(node):
    """XML 주석 노드를 재귀적으로 제거한다.

    이유: gazebo_ros2_control 플러그인은 robot_description 을 controller_manager
    노드에 `--param robot_description:=<urdf>` CLI 오버라이드로 넘긴다. rcl 의
    파라미터 규칙 파서는 비-ASCII 바이트를 처리하지 못해
        "parser error Couldn't parse parameter override rule"
    로 죽고, 그러면 controller_manager 가 아예 뜨지 않아 스포너가 무한 대기한다.
    이 xacro 의 한글·em-dash 주석이 정확히 그 트리거였다(실측: 비-ASCII 346자가
    전부 주석 안, 주석 제거 시 0자). 주석은 소스 파일에 그대로 두고, ROS 로
    넘기는 문자열에서만 걷어낸다.
    """
    for child in list(node.childNodes):
        if child.nodeType == child.COMMENT_NODE:
            node.removeChild(child)
            child.unlink()
        else:
            _strip_comments(child)


def _build_robot_description(xacro_file):
    doc = xacro.process_file(xacro_file)
    _strip_comments(doc)
    urdf = doc.toxml()
    non_ascii = [c for c in urdf if ord(c) > 127]
    if non_ascii:
        raise RuntimeError(
            f'robot_description 에 비-ASCII 문자 {len(non_ascii)}개가 주석 밖에 남아 '
            f'있습니다 {sorted(set(non_ascii))[:10]} — gazebo_ros2_control 이 '
            f'controller_manager 를 띄우지 못합니다. 해당 문자를 ASCII 로 바꾸세요.')
    return urdf


def generate_launch_description():
    pkg_gazebo = get_package_share_directory('trnav_2ws_gazebo')
    pkg_desc = get_package_share_directory('trnav_2ws_description')
    gazebo_ros = get_package_share_directory('gazebo_ros')

    xacro_file = os.path.join(pkg_desc, 'urdf', 'foil_a082.urdf.xacro')
    world_file = os.path.join(pkg_gazebo, 'worlds', 'warehouse.world')

    gui = LaunchConfiguration('gui')
    rviz = LaunchConfiguration('rviz')
    steer_lag = LaunchConfiguration('steer_lag')
    x = LaunchConfiguration('x')
    y = LaunchConfiguration('y')
    yaw = LaunchConfiguration('yaw')

    args = [
        DeclareLaunchArgument('gui', default_value='true',
                              description='gzclient (Gazebo GUI) 표시'),
        DeclareLaunchArgument('rviz', default_value='false',
                              description='RViz 동시 기동'),
        DeclareLaunchArgument('steer_lag', default_value='0.0',
                              description='조향 서보 1차 지연 시상수 [s]'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
    ]

    # Gazebo 가 시스템 미디어(셰이더 등)를 계속 찾을 수 있도록 기존 값을 보존한다.
    _res = os.environ.get('GAZEBO_RESOURCE_PATH', '') or '/usr/share/gazebo-11'
    resource_path = SetEnvironmentVariable('GAZEBO_RESOURCE_PATH', _res)

    # ── Gazebo ──
    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros, 'launch', 'gzserver.launch.py')),
        launch_arguments={'world': world_file, 'verbose': 'true'}.items(),
    )
    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros, 'launch', 'gzclient.launch.py')),
        condition=IfCondition(gui),
    )

    # ── robot_description (주석 제거: _strip_comments 주석 참고) ──
    robot_description = _build_robot_description(xacro_file)

    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description,
                     'use_sim_time': True}],
    )

    spawn = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        output='screen',
        arguments=['-topic', 'robot_description',
                   '-entity', 'foil_a082',
                   '-x', x, '-y', y, '-z', '0.02', '-Y', yaw],
    )

    # ── 컨트롤러 (스폰 완료 후 순차 기동) ──
    jsb_spawner = Node(
        package='controller_manager', executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager',
                   '/controller_manager'],
        output='screen',
    )
    steer_spawner = Node(
        package='controller_manager', executable='spawner',
        arguments=['steer_position_controller', '--controller-manager',
                   '/controller_manager'],
        output='screen',
    )
    drive_spawner = Node(
        package='controller_manager', executable='spawner',
        arguments=['drive_velocity_controller', '--controller-manager',
                   '/controller_manager'],
        output='screen',
    )

    # ── 모터 계층 대체 노드 ──
    bridge = Node(
        package='trnav_2ws_gazebo', executable='wheel_cmd_bridge.py',
        name='wheel_cmd_bridge', output='screen',
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_2ws_core'), 'config', 'robot_geometry_2ws.yaml']), {'use_sim_time': True, 'steer_tau': steer_lag}],
    )
    odometry = Node(
        package='trnav_2ws_gazebo', executable='wheel_odometry.py',
        name='wheel_odometry', output='screen',
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_2ws_core'), 'config', 'robot_geometry_2ws.yaml']), {'use_sim_time': True}],
    )

    rviz_node = Node(
        package='rviz2', executable='rviz2', output='screen',
        condition=IfCondition(rviz),
        parameters=[{'use_sim_time': True}],
    )

    # spawn -> jsb -> steer -> drive -> bridge/odom, strictly one at a time.
    #
    # The controller spawners must NOT run concurrently. Starting steer and
    # drive together races on controller_manager's load service and one of them
    # dies with "Failed loading controller"; which one loses varies run to run,
    # so the symptom is an intermittently unsteerable robot. Chaining each
    # spawner off the previous one's exit removes the race.
    ordering = [
        RegisterEventHandler(OnProcessExit(
            target_action=spawn, on_exit=[jsb_spawner])),
        RegisterEventHandler(OnProcessExit(
            target_action=jsb_spawner, on_exit=[steer_spawner])),
        RegisterEventHandler(OnProcessExit(
            target_action=steer_spawner, on_exit=[drive_spawner])),
        RegisterEventHandler(OnProcessExit(
            target_action=drive_spawner, on_exit=[bridge, odometry, rviz_node])),
    ]

    return LaunchDescription(
        args + [resource_path, gzserver, gzclient, rsp, spawn] + ordering)
