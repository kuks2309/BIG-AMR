#!/usr/bin/env python3

import os

from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

from launch_ros.actions import Node

# this is the function launch  system will look for
def generate_launch_description():

    iahrs_driver_node = Node(
        package='iahrs_driver',
        executable='iahrs_driver',
        output='screen',
        # /dev/imu(ttyUSB0) 가 직전 인스턴스/타 프로세스에 일시 점유되면 iahrs 가
        # "Failed to open" → FATAL 종료하여 /imu/data 가 영영 안 나온다. respawn 으로
        # 2초마다 재시도 → 포트가 풀리면 자동 복구.
        respawn=True,
        respawn_delay=2.0,
        parameters=[
            {"serial_port": "/dev/imu"},  # udev 심링크(→ttyUSB0). 대문자 /dev/IMU 는 미존재
            # m_bSingle_TF_option=False: 드라이버의 동적 base_link->imu_link(=IMU 자세값을
            # 회전으로 싣는) TF 를 끈다. SLAM 등 IMU 융합에는 고정(static) 마운트 TF 가
            # 필요하다(동적이면 IMU 변환이 시변→부정확). 마운트 TF 는 아래 static_transform_publisher 가 발행.
            {"m_bSingle_TF_option": False},
            # tf_translation_z 는 드라이버 자체 TF(m_bSingle_TF_option=True)에서만 쓰이는 값 →
            # 위에서 False 이므로 현재 무효(dead). 실제 마운트 높이는 아래 static TF 의 --z 값이다.
            {"tf_translation_z": 0.2}
        ]
    )

    # base_link -> imu_link 정적 마운트 TF — 단일 발행원(SSOT). 다른 launch 에서
    # base_link->imu_link 를 중복 발행하지 말 것(TF 충돌).
    # 아래 (-0.37, 0, 0.29) identity 값은 이식 원본(TR-AMR) 실측값이며 Big-AMR 차체 값이 아니다.
    # (원본 기준: iAHRS 중앙 뒤 37cm·바닥+29cm·x 정렬, 평지 2D 가정.)
    # TODO(debt-002): (-0.37, 0, 0.29) 는 TR-AMR 실측값 — Big-AMR 실장착 위치로 재측정·수정 필요.
    static_tf_base_to_imu = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_base_to_imu',
        arguments=['--x', '-0.37', '--y', '0', '--z', '0.29',
                   '--roll', '0', '--pitch', '0', '--yaw', '0',
                   '--frame-id', 'base_link', '--child-frame-id', 'imu_link'],
        output='screen',
    )

    # create and return launch description object
    return LaunchDescription(
        [
            iahrs_driver_node,
            static_tf_base_to_imu
        ]
    )
