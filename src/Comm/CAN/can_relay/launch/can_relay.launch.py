"""can_relay 드라이버 기동.

⚠ 이 launch 는 노드를 **대기 상태**로 띄운다. 제어권은 잡지 않는다 —
`ros2 service call /can_relay_node/engage std_srvs/srv/SetBool "{data: true}"`
를 명시 호출해야 Seer 에게서 버스를 가져온다.
launch 만으로 로봇이 움직일 수 있는 상태를 만들지 않는 것이 의도다.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory("can_relay"), "config", "can_relay.yaml")

    params_arg = DeclareLaunchArgument(
        "params_file", default_value=default_params,
        description="can_relay 파라미터 YAML")
    link_arg = DeclareLaunchArgument(
        "link", default_value="panda",
        description="panda | mock — mock 은 하드웨어 무접속 시험용")

    node = Node(
        package="can_relay",
        executable="can_relay_node",
        name="can_relay_node",
        output="screen",
        emulate_tty=True,
        parameters=[LaunchConfiguration("params_file"),
                    {"link": LaunchConfiguration("link")}],
        # 드라이버가 죽으면 살아 있는 척하지 않는다. respawn 하지 않는다 —
        # 재기동은 제어권을 다시 잡는 행위이고 사람이 판단해야 한다.
        on_exit=Shutdown(),
    )
    return LaunchDescription([params_arg, link_arg, node])
