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
import sys
import xml.dom.minidom

import xacro
from ament_index_python.packages import get_package_share_directory

# The plant is the single source of truth for where things are — see its
# header. Importing it is what stops the launch and the CSM disagreeing
# about the floor they are both standing on.
from csm import plant
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            SetEnvironmentVariable, TimerAction)
from launch.actions import RegisterEventHandler
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

#: Where each robot parks at spawn — one bay per AGV class, on a spur off the
#: cross aisle at the end of that class's own run, so an idle robot never stands
#: on a lane another class needs.
#:
#: IMPORTED from csm/plant.py, not copied. The old copy said "Positions come
#: from csm/plant.py PARKING" and then drifted from it: commit 5745612 moved
#: PARK_X[1] from 17.5 to 23.5 to make room for leg C's WIP rack, and these
#: three literals stayed at 17.5. amr2 and amr3 then spawned 6 m from the bays
#: the CSM believed they were in, drove east to reach them, and wedged against
#: a wall — the same commit had also grown HALL_E from 20 to 26 without
#: regenerating factory.world, so the building was still the old size. A
#: comment cannot keep two files in step; an import can.
#:
#: Order is the AGV class order, which is what binds a robot to a leg:
#:   A = 1.5T AGV A, west end   (ASRS -> Gravure LD)
#:   B = 1.5T AGV B, east end   (Gravure ULD -> Coater LD)
#:   C = 3.5T AGV,   east end   (Coater ULD -> Slitter LD)
#: Spawn each robot in ITS OWN queue slot, by name, exactly where the CSM will
#: later send it home to. Taking the leg's slot instead put every robot of a
#: class on one point — fine with one robot per class, a collision with two.
_FLEET_ORDER = ('amr1', 'amr2', 'amr3')
START_POSES = [plant.parking_for(n) + (0.0,) for n in _FLEET_ORDER]
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


def _one_robot(name, pose, xacro_file, steer_lag, after=None):
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
        # The same wheel geometry the odometry node gets. eead4a6 made this
        # bridge REQUIRE w1_x/w1_y/w2_x/w2_y/wheel_radius — it declares them
        # NaN and raises if they are still NaN — but only the odometry node was
        # given the file. Every robot's bridge then died at startup with
        # "휠 기하 파라미터 미주입", nothing was left subscribing /amrN/cmd_vel,
        # and the whole fleet spawned and sat still. Both nodes read one file so
        # they cannot disagree about where the wheels are.
        # The dict comes second so steer_tau, a launch argument, still wins.
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_2ws_core'), 'config', 'robot_geometry_2ws.yaml']),
            {'use_sim_time': True, 'steer_tau': steer_lag}],
    )
    odometry = Node(
        package='trnav_2ws_gazebo', executable='wheel_odometry.py',
        name='wheel_odometry', namespace=name, output='screen',
        parameters=[PathJoinSubstitution([
            FindPackageShare('trnav_2ws_core'), 'config', 'robot_geometry_2ws.yaml']),
            {'use_sim_time': True}],
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
    # ONE ROBOT AT A TIME, CHAINED — not staggered on a timer.
    #
    # Three robots starting together race: each brings up its own
    # gazebo_ros2_control plugin, and they contend on the shared
    # robot_state_publisher service and on Gazebo's model insertion. Observed
    # with no delay at all: amr2 loaded all three controllers, amr1 loaded
    # none, amr3 loaded one — while the launch log claimed all three had
    # activated.
    #
    # That was mitigated with an 8 s stagger, and the mitigation was not
    # enough. Measured 2026-08-18 across two runs of the same build:
    #
    #   run A  amr1's controller_manager answered immediately
    #   run B  amr1's controller_manager took OVER 10 s — its first spawner
    #          logged "Failed getting a result ... in 10.0 (Attempt 1 of 3)"
    #
    # 10 s is longer than the 8 s stagger, so in run B amr2 began spawning
    # while amr1's manager was still coming up. amr1's broadcaster activated
    # and then stopped publishing; the CSM correctly refused to give it work,
    # and that leg completed zero jobs for the whole run.
    #
    # A LONGER TIMER WOULD ONLY MAKE IT RARER. What removes the race is not
    # starting the next robot until the previous one's controllers are
    # actually up — which is exactly what the per-robot chain below already
    # proves, so the fleet is chained the same way.
    #
    # Cost is a slower start: serial rather than overlapped, about 40 s for
    # three robots against about 30 s before. Ten seconds once, for a fleet
    # that comes up the same way every time.
    actions = [rsp, spawn] + ordering
    if after is not None:
        actions = [RegisterEventHandler(
            OnProcessExit(target_action=after, on_exit=actions))]
    #: The last spawner in this robot's chain. The NEXT robot starts when this
    #: exits, which is the point at which this robot's controllers are up.
    return actions, drive


def _robot_count():
    """How many robots to spawn, resolved before the description is built.

    The count decides how many nodes exist, so it cannot be a
    LaunchConfiguration — those are not resolved until later. It is read
    straight from argv instead, which is what makes `robots:=N` behave like
    every other launch argument here.

    Until 2026-08-18 this read FLEET_ROBOTS alone and `robots:=N` was declared
    but never looked at, so `robots:=2` silently spawned three anyway. The
    argument is honoured first now; FLEET_ROBOTS still works and is still what
    docs/verification/2026-08-10-two-robot-one-hour-soak.md uses.
    """
    for arg in sys.argv[1:]:
        if arg.startswith('robots:='):
            try:
                return int(arg.split(':=', 1)[1])
            except ValueError:
                # Let the declared argument's own validation report it rather
                # than dying here with a traceback out of a helper.
                break
    return int(os.environ.get('FLEET_ROBOTS', '3'))


def generate_launch_description():
    pkg_gazebo = get_package_share_directory('trnav_2ws_gazebo')
    pkg_desc = get_package_share_directory('trnav_2ws_description')
    gazebo_ros = get_package_share_directory('gazebo_ros')
    xacro_file = os.path.join(pkg_desc, 'urdf', 'foil_a082.urdf.xacro')
    world = os.path.join(pkg_gazebo, 'worlds', 'factory.world')

    args = [
        DeclareLaunchArgument('robots', default_value='3',
                              description='how many robots to spawn (1-3); '
                                          'FLEET_ROBOTS is the fallback'),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('steer_lag', default_value='0.0',
                              description='steering servo lag, seconds'),
        DeclareLaunchArgument('mes', default_value='true',
                              description='also start the MES that gives the '
                                          'robots work; false leaves them '
                                          'spawned but idle'),
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
    # not resolved until later. See _robot_count.
    count = _robot_count()
    count = max(1, min(count, len(START_POSES)))

    robots = []
    previous = None
    for i in range(count):
        actions, previous = _one_robot(
            f'amr{i + 1}', START_POSES[i], xacro_file,
            LaunchConfiguration('steer_lag'), after=previous)
        robots += actions

    # The MES. Without it the fleet spawns, activates every controller, and
    # then stands still for ever — nothing publishes /amrN/cmd_vel, which reads
    # exactly like a broken simulation and is not one. It was a separate
    # `ros2 run csm sim_node` that was simply easy to forget.
    #
    # `count` is passed from the same variable that built the robots, so the
    # fleet and the MES cannot disagree about how many robots exist. Getting
    # that wrong is silent: sim_node's own default is 0, which means the
    # single-robot world, and it then drives nothing in a namespaced fleet.
    #
    # DELAYED, not started with everything else. Robots come up staggered
    # (delay=i * 8.0 above) and the ACS picks the robot nearest the pickup,
    # where one that has not reported odometry yet sorts last but is still
    # eligible — see sim_acs.py, _dispatch. Offered work before any robot has a
    # pose it would hand the job to whichever sorted first.
    #
    # The margin is 30 s, not the ~12 s a controller bring-up takes, because
    # the bring-up RACES. This launch already staggers robots 8 s apart for
    # that reason (see the note on _one_robot). With a 15 s margin the MES
    # started at 31 s while the last robot's spawn_entity was still waiting on
    # Gazebo's /spawn_entity service; that spawn then hung, its controllers and
    # wheel bridge never started, and the robot sat immobile — while the MES,
    # seeing a robot with a valid pose, gave it a job. Another robot
    # manoeuvring nearby drove into it. Starting the MES after the fleet is
    # fully up costs 15 s once and removes that whole class of failure.
    mes = TimerAction(
        # Robots are chained now, so this is no longer a stagger plus a guess:
        # it is how long a serial fleet bring-up takes. ~14 s per robot from
        # the measurements above, plus margin.
        period=count * 14.0 + 10.0,
        actions=[Node(
            package='csm', executable='sim_node', output='screen',
            arguments=['--robots', str(count)],
            condition=IfCondition(LaunchConfiguration('mes')),
        )],
    )

    return LaunchDescription(
        args + [resource_path, gzserver, gzclient] + robots + [mes])
