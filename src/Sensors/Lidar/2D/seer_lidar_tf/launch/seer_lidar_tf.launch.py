#!/usr/bin/env python3
"""seer_lidar_tf_node 실행 launch (파라미터 override 예시 포함)."""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="seer_lidar_tf",
            executable="seer_lidar_tf_node",
            name="seer_lidar_tf",
            output="screen",
            parameters=[{
                "seer_ip": "192.168.44.82",
                "seer_port": 19204,
                "parent_frame": "base_footprint",
                "front_frame": "scan_front",
                "rear_frame": "scan_rear",
                "z_front": 0.0,   # Seer 미제공 → 실측 장착 높이로 교체 가능
                "z_rear": 0.0,
                "poll_period": 0.0,   # 0=1회 latch, >0=주기(초) 재조회
            }],
        ),
    ])
