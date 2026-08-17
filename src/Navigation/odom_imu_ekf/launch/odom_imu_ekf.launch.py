# 휠 오도 + IMU 융합 노드 하나만 띄운다. 측위 스택(bringup)이 이것을 포함해 쓰거나,
#   이미 돌고 있는 스택에 한 칸 끼워 넣을 때 단독으로 쓴다.
#
#   ros2 launch odom_imu_ekf odom_imu_ekf.launch.py odom_topic:=/odom imu_topic:=/imu/data
#
# ⚠ IMU 가 오지 않으면 이 노드는 **아무것도 발행하지 않는다**(레거시와 같은 성질).
#   /diagnostics 에 ERROR 로 드러나므로 조용히 멈추지는 않는다.
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # 인자는 문자열로 들어온다 — 노드가 double 로 선언한 자리에 그대로 넘기면 타입이 어긋나
    #   InvalidParameterTypeException 으로 죽는다. 명시 변환해서 넘긴다.
    gate_deg = ParameterValue(LaunchConfiguration('imu_gate_rate_deg'), value_type=float)
    return LaunchDescription([
        DeclareLaunchArgument('odom_topic', default_value='/odom',
                              description='휠 오도 입력'),
        DeclareLaunchArgument('imu_topic', default_value='/imu/data',
                              description='IMU 입력 (iahrs_driver 기본 토픽)'),
        DeclareLaunchArgument('fused_topic', default_value='/odom_fused',
                              description='융합 결과 — 측위가 이것을 받는다'),
        DeclareLaunchArgument('imu_gate_rate_deg', default_value='1.0',
                              description='IMU 반영 게이트 [deg/s]. 원본 하드코딩 값이 1.0 이다'),
        Node(
            package='odom_imu_ekf', executable='odom_imu_ekf_node',
            name='odom_imu_ekf', output='screen',
            parameters=[{'imu_gate_rate_deg': gate_deg}],
            remappings=[('odom', LaunchConfiguration('odom_topic')),
                        ('imu', LaunchConfiguration('imu_topic')),
                        ('odom_fused', LaunchConfiguration('fused_topic'))],
        ),
    ])
