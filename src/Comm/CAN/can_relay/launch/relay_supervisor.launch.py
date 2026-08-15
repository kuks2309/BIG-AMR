"""can_relay 노드 감시자 기동.

드라이버와 **별도 프로세스·별도 launch** 다. 같이 띄우면 드라이버가 죽을 때 감시자도
함께 내려가(`on_exit=Shutdown()`) 정작 기록할 사건을 못 본다.

감시자는 제어 경로 밖이다 — CAN 에 쓰지 않고 판다를 열지 않는다. 하는 일은
`/diagnostics` 구독 · 상태 기록 · 재기동 후 `~/engage` 호출 셋뿐이다.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    args = [
        DeclareLaunchArgument(
            "target_node", default_value="can_relay_node",
            description="감시 대상 노드 이름(서비스 경로·프로세스 이름 양쪽에 쓴다)"),
        DeclareLaunchArgument(
            "restore_enabled", default_value="true",
            description="재기동 후 직전 제어권 상태로 되돌릴 것인가"),
        DeclareLaunchArgument(
            "state_dir", default_value="",
            description="상태 기록 위치. 빈 값이면 tmpfs 를 자동 선택"),
        DeclareLaunchArgument(
            "diag_timeout_s", default_value="3.0",
            description="진단이 이보다 끊기면 두절 판정. "
                        "⚠ 드라이버의 ros_alive_timeout_s(2.0) 보다 길어야 한다"),
    ]

    node = Node(
        package="can_relay",
        executable="relay_supervisor",
        name="relay_supervisor",
        output="screen",
        emulate_tty=True,
        parameters=[{
            "target_node": LaunchConfiguration("target_node"),
            "restore_enabled": LaunchConfiguration("restore_enabled"),
            "state_dir": LaunchConfiguration("state_dir"),
            "diag_timeout_s": LaunchConfiguration("diag_timeout_s"),
        }],
        # 감시자는 죽어도 로봇 안전에 영향이 없다(제어 경로 밖). 그래서 살아나는 쪽이
        # 이득이고, 드라이버와 달리 respawn 을 건다.
        respawn=True,
        respawn_delay=2.0,
    )
    return LaunchDescription(args + [node])
