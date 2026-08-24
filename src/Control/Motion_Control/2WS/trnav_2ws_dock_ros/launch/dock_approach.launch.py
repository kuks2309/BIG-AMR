# 도킹 접근 액션 서버만 띄운다. 선행: wall_localizer(측위)·trnav_motion_mux·translator 체인.
#
# 입력  : /wall_pose (wall_localizer) · 액션 goal (amr_motion_dock_approach)
# 출력  : /motion/wheel_cmd/dock (mux source 40) · 액션 feedback/result
# 주의  : goal 수락 시 /select_motion_source(40) 전환, 종료 시 mux_restore_id 로 복원.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    default_params = os.path.join(
        get_package_share_directory('trnav_2ws_dock_ros'), 'config',
        'dock_approach_params.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file', default_value=default_params,
            description='도킹 파라미터 YAML (게인·arm — 실기 튜닝 대상)'),
        Node(
            package='trnav_2ws_dock_ros',
            executable='dock_approach_action_server',
            name='dock_approach_server',
            parameters=[LaunchConfiguration('params_file')],
            output='screen',
        ),
    ])
