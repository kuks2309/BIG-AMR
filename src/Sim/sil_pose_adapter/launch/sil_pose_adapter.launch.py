"""
SIL pose type adapter launch.

/rtabmap/localization_pose (PoseWithCovarianceStamped, SensorDataQoS)
  → /robot_pose (PoseStamped, RELIABLE depth=10)

본 launch 는 SIL closed-loop 시나리오에서만 사용. 실차 미사용.
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='sil_pose_adapter',
            executable='sil_pose_adapter_node',
            name='sil_pose_adapter_node',
            output='screen',
        ),
    ])
