"""Seer 위치 → /robot_pose 발행 노드 런치.

읽기 전용 — 상태 포트 19204 만 연다. 로봇을 움직이지 않는다.
"""

from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="seer_pose_publisher",
            executable="seer_pose_publisher_node",
            name="seer_pose_publisher",
            output="screen",
            parameters=[PathJoinSubstitution([
                FindPackageShare("seer_pose_publisher"),
                "config", "seer_pose.yaml"])],
        ),
    ])
