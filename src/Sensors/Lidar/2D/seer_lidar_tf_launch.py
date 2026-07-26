#!/usr/bin/env python3
"""base_footprint -> scan_front / scan_rear static TF.

값 출처: SEER SRC(192.168.44.82:19204) Robot Status API 1009(robot_status_laser_res)
의 laser[].install_info 스냅샷 (2026-07-25 판독). install_info 는 2D(x/y/yaw)만
제공하므로 z/roll/pitch = 0. yaw 는 도→라디안 변환. 재장착·재캘리브 시에만
seer_read_lidar_install.py 로 재조회하여 아래 값을 갱신한다(사용자 지시: 요청 시에만 변경).

실행: ros2 launch src/Sensors/Lidar/2D/seer_lidar_tf_launch.py
"""
import math
from launch import LaunchDescription
from launch_ros.actions import Node

PARENT = "base_footprint"

# SEER install_info 스냅샷 (base_footprint 기준, m / deg). Seer 미제공 → z/roll/pitch=0.
LIDARS = [
    # child_frame,  x,                    y,                     z,   yaw_deg
    ("scan_front",  0.8808743642346627,  -0.5783268634147752,   0.0, -45.57274026382727),
    ("scan_rear",  -0.8564035555844536,   0.6067443643452458,   0.0, 135.0925107833687),
]


def generate_launch_description():
    nodes = []
    for child, x, y, z, yaw_deg in LIDARS:
        nodes.append(
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name=f"tf_{child}",
                arguments=[
                    "--x", str(x), "--y", str(y), "--z", str(z),
                    "--roll", "0.0", "--pitch", "0.0", "--yaw", str(math.radians(yaw_deg)),
                    "--frame-id", PARENT, "--child-frame-id", child,
                ],
            )
        )
    return LaunchDescription(nodes)
