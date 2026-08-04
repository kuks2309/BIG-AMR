from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    mux_launch = os.path.join(
        get_package_share_directory('trnav_motion_mux'),
        'launch', 'trnav_motion_mux.launch.py')
    supervisor_launch = os.path.join(
        get_package_share_directory('trnav_motion_supervisor'),
        'launch', 'trnav_motion_supervisor.launch.py')

    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(mux_launch)),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(supervisor_launch)),
    ])
