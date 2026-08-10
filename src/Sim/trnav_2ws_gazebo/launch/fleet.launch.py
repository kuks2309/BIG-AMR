"""fleet.launch.py — several robots in one Gazebo world.

    ros2 launch trnav_2ws_gazebo fleet.launch.py robots:=3

`sim.launch.py` stays as it is: one robot on the global topics, which is what
everything else in this repository still expects. This is additive, so a broken
fleet launch can never stop the single-robot simulation working.

Each robot gets its own namespace — `amr1`, `amr2`, `amr3` — and under it:

    /amrN/cmd_vel · /amrN/odom_truth · /amrN/scan_front · /amrN/scan_rear
    /amrN/controller_manager  and its three controllers
    tf frames prefixed amrN_

**Why the namespace has to reach the controller manager.** Without it every
robot loads its controllers into one shared manager. The second spawn either
fails with a name clash or, worse, succeeds and drives another robot's wheels.
The URDF takes an `ns` argument for exactly this; see foil_a082.urdf.xacro.

**Why the spawners are chained per robot.** Starting `steer` and `drive`
together races on the controller manager's load service and one dies with
"Failed loading controller" — which one loses varies between runs, so the
symptom is an intermittently unsteerable robot. Each robot's spawners are
chained off the previous one's exit. Different robots are independent and may
start in parallel, because they have separate managers.
"""

import os
import xml.dom.minidom

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            SetEnvironmentVariable, TimerAction)
from launch.actions import RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

#: Where each robot parks at spawn — one bay per AGV class, on a spur off the
#: cross aisle at the end of that class's own run, so an idle robot never stands
#: on a lane another class needs. Positions come from csm/plant.py PARKING.
START_POSES = [
    (-21.5, 1.5, 0.0),      # amr1 — 1.5T AGV A, west end (ASRS -> Gravure LD)
    (17.5, 1.5, 0.0),       # amr2 — 1.5T AGV B, east end (Gravure ULD -> Coater LD)
    (17.5, -1.5, 0.0),      # amr3 — 3.5T AGV,   east end (Coater ULD -> Slitter LD)
]
#: One pose per robot, and the count is clamped to len(START_POSES) — so this
#: list, not FLEET_ROBOTS, is the ceiling on fleet size. Each pose must match
#: the parking bay its robot's segment owns in csm/plant.py PARKING, because a
#: robot spawns where it would park and homes back to the same place.
#:
#: There is no spare pose. A robot spawned without an entry in plant.py
#: ROBOT_SEGMENT is offered no work at all and sits idle for ever, which looks
#: like a navigation fault and is not one — test_roads.py asserts against it.

#: The parking row used to sit in the middle of the traffic, and idle robots
#: were repeatedly driven into by working ones. It is now off the aisles.
#:
#: An earlier note here recorded 1.4 m of drift by robots that were "idle and
#: uncommanded", and blamed the spawn or the casters. That was wrong: the world
#: had many stacked launches in it and ten leftover wheel_cmd_bridge nodes per
#: robot were publishing wheel commands the whole time. In a clean world all
#: three settle 0.07 m.


def _strip_comments(node):
    """Remove XML comments from the robot description.

    gazebo_ros2_control passes the URDF to controller_manager as a
    `--param robot_description:=<urdf>` CLI override, and rcl's parser rejects
    non-ASCII bytes. Every non-ASCII character in this model is inside a
    comment, so dropping comments is enough — and it fails loudly rather than
    leaving controller_manager silently absent with the spawners hanging.
    """
    for child in list(node.childNodes):
        if child.nodeType == child.COMMENT_NODE:
            node.removeChild(child)
        else:
            _strip_comments(child)


def _description(xacro_file, ns):
    doc = xacro.process_file(xacro_file, mappings={'ns': ns})
    dom = xml.dom.minidom.parseString(doc.toxml())
    _strip_comments(dom)
    urdf = dom.toxml()
    bad = [c for c in urdf if ord(c) > 127]
    if bad:
        raise RuntimeError(
            f"{len(bad)} non-ASCII characters remain outside comments in the "
            f"robot description; rcl cannot parse it and controller_manager "
            f"will not start. Replace them with ASCII.")
    return urdf


def _one_robot(name, pose, xacro_file, steer_lag, delay=0.0):
    """Everything one robot needs. Independent of every other robot."""
    x, y, yaw = pose
    urdf = _description(xacro_file, name)

    rsp = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        namespace=name, output='screen',
        parameters=[{'robot_description': urdf,
                     'use_sim_time': True,
                     # Without a frame prefix every robot publishes base_link,
                     # and the TF tree becomes one robot in several places.
                     'frame_prefix': f'{name}_'}],
    )

    spawn = Node(
        package='gazebo_ros', executable='spawn_entity.py', output='screen',
        arguments=['-topic', f'/{name}/robot_description',
                   '-entity', name,
                   '-x', str(x), '-y', str(y), '-z', '0.02', '-Y', str(yaw)],
    )

    def spawner(controller):
        return Node(
            package='controller_manager', executable='spawner',
            arguments=[controller,
                       '--controller-manager', f'/{name}/controller_manager'],
            output='screen',
        )

    jsb = spawner('joint_state_broadcaster')
    steer = spawner('steer_position_controller')
    drive = spawner('drive_velocity_controller')

    bridge = Node(
        # OUR bridge, not scripts/wheel_cmd_bridge.py — that one is another
        # author's file. Same kinematics, plus a per-robot dock/wheel_cmd input
        # so docking can command a steering angle at zero speed.
        package='trnav_2ws_gazebo', executable='fleet_wheel_bridge.py',
        name='fleet_wheel_bridge', namespace=name, output='screen',
        parameters=[{'use_sim_time': True, 'steer_tau': steer_lag}],
    )
    odometry = Node(
        package='trnav_2ws_gazebo', executable='wheel_odometry.py',
        name='wheel_odometry', namespace=name, output='screen',
        parameters=[{'use_sim_time': True}],
    )

    # Chained: spawn -> jsb -> steer -> drive -> bridge/odometry. One at a time
    # WITHIN a robot; robots are independent and overlap freely.
    ordering = [
        RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=[jsb])),
        RegisterEventHandler(OnProcessExit(target_action=jsb, on_exit=[steer])),
        RegisterEventHandler(OnProcessExit(target_action=steer, on_exit=[drive])),
        RegisterEventHandler(OnProcessExit(target_action=drive,
                                           on_exit=[bridge, odometry])),
    ]
    # STAGGERED. Three robots starting together race: each brings up its own
    # gazebo_ros2_control plugin, and they contend on the shared
    # robot_state_publisher service and on Gazebo's model insertion. Observed
    # with no delay: amr2 loaded all three controllers, amr1 loaded none, amr3
    # loaded one — while the launch log claimed all three had activated.
    #
    # The delay is per robot, so the fleet still comes up in seconds.
    if delay:
        return [TimerAction(period=delay, actions=[rsp, spawn] + ordering)]
    return [rsp, spawn] + ordering


def generate_launch_description():
    pkg_gazebo = get_package_share_directory('trnav_2ws_gazebo')
    pkg_desc = get_package_share_directory('trnav_2ws_description')
    gazebo_ros = get_package_share_directory('gazebo_ros')
    xacro_file = os.path.join(pkg_desc, 'urdf', 'foil_a082.urdf.xacro')
    world = os.path.join(pkg_gazebo, 'worlds', 'factory.world')

    args = [
        DeclareLaunchArgument('robots', default_value='3',
                              description='how many robots to spawn (1-3)'),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('steer_lag', default_value='0.0',
                              description='steering servo lag, seconds'),
    ]
    gui = LaunchConfiguration('gui')

    # Keep Gazebo able to find its system media (shaders). sim.launch.py has
    # always done this; the fleet launch did not, so `gui:=true` brought up
    # gzclient and it died immediately:
    #
    #   [Err] [RTShaderSystem.cc:480] Unable to find shader lib ...
    #   [Err] [RenderEngine.cc:197]   Failed to initialize scene
    #   gzclient: ... Assertion `px != 0' failed.        exit code -6
    #
    # gzserver is unaffected, so the fleet came up headless and looked fine
    # from the topics while there was simply no window to watch it in. Nothing
    # sources /usr/share/gazebo/setup.sh for us — not ~/.bashrc, not
    # start_sim.sh — so the launch has to set it itself.
    _res = os.environ.get('GAZEBO_RESOURCE_PATH', '') or '/usr/share/gazebo-11'
    resource_path = SetEnvironmentVariable('GAZEBO_RESOURCE_PATH', _res)

    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros, 'launch', 'gzserver.launch.py')),
        launch_arguments={'world': world, 'verbose': 'true'}.items(),
    )
    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros, 'launch', 'gzclient.launch.py')),
        condition=IfCondition(gui),
    )

    # The count is read at description time rather than as a substitution,
    # because the number of nodes depends on it and a LaunchConfiguration is
    # not resolved until later.
    count = int(os.environ.get('FLEET_ROBOTS', '3'))
    count = max(1, min(count, len(START_POSES)))

    robots = []
    for i in range(count):
        robots += _one_robot(f'amr{i + 1}', START_POSES[i],
                             xacro_file, LaunchConfiguration('steer_lag'),
                             delay=i * 8.0)

    return LaunchDescription(args + [resource_path, gzserver, gzclient] + robots)
