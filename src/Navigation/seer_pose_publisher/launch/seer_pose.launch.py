"""Seer 위치 → PoseStamped 발행 노드 런치.

읽기 전용 — 상태 포트 19204 만 연다. 로봇을 움직이지 않는다.

## ⚠ 발행 토픽과 「결속」

기본 발행은 **`/seer/robot_pose`** 다(`/robot_pose` 가 아니다 — 종전 docstring 이 틀렸다).
설계상 `/robot_pose` 는 **PC 측위가 채우는 정본**이고 본 노드는 그 옆의 참조다
(`seer_pose_publisher/pose_node.py:20-31`).

그런데 이 저장소에는 그 정본 발행자가 **아직 없다**. 그래서 2WS 액션 서버
(`LocalizationMonitor` 로 `/robot_pose` 구독)를 실기에서 돌리려면 **두 끝을 손으로 이어야
한다.** 그 결속이 어디에도 선언돼 있지 않아 재현 가능한 기동 절차가 없었다 —
`pose_topic` 을 런치 인자로 노출해 **명시적으로 선언**할 수 있게 한다:

    # (a) Seer 를 유일 측위원으로 쓰는 구성 — 노드가 의존성 경고를 남긴다
    ros2 launch seer_pose_publisher seer_pose.launch.py pose_topic:=/robot_pose

    # (b) 참조로만 두고 액션 서버 쪽을 돌리는 구성
    ros2 launch seer_pose_publisher seer_pose.launch.py            # /seer/robot_pose
    ros2 launch trnav_2ws_action_server yaw_control.launch.py \
         yaw_control_pose_topic:=/seer/robot_pose

어느 쪽이든 **결속을 명령줄에 적어 남긴다.** 기본값은 바꾸지 않았다 — 「Seer 의존」은
설계 결정이며 운용자가 의식적으로 골라야 한다.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pose_topic = LaunchConfiguration("pose_topic")
    return LaunchDescription([
        DeclareLaunchArgument(
            "pose_topic", default_value="/seer/robot_pose",
            description="발행 토픽. 액션 서버를 Seer 자세로 돌리려면 /robot_pose 로 지정 "
                        "(그때 노드가 의존성 경고를 남긴다)."),
        Node(
            package="seer_pose_publisher",
            executable="seer_pose_publisher_node",
            name="seer_pose_publisher",
            output="screen",
            parameters=[
                PathJoinSubstitution([
                    FindPackageShare("seer_pose_publisher"),
                    "config", "seer_pose.yaml"]),
                {"pose_topic": pose_topic},      # yaml 뒤에 두어 인자가 이긴다
            ],
        ),
    ])
