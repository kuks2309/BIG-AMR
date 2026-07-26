# Copyright 2024 pradyum
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    calibration_file = os.path.join(
        get_package_share_directory('lidar_calibration_2d'),
        'config', 'calibration_result.yaml'
    )

    filter_config_file = os.path.join(
        get_package_share_directory('dual_laser_merger'),
        'config', 'filter_config.yaml'
    )

    ld = LaunchDescription()

    # base_link → scan_merged static TF (base_link과 동일 위치)
    base_to_merged_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_to_scan_merged_tf',
        arguments=['0', '0', '0', '0', '0', '0', 'base_link', 'scan_merged'],
    )

    dual_laser_merger_node = ComposableNodeContainer(
        name='merger_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container',
        composable_node_descriptions=[
            ComposableNode(
                package='dual_laser_merger',
                plugin='merger_node::MergerNode',
                name='dual_laser_merger',
                parameters=[
                    {'laser_1_topic': '/scan_front'},
                    {'laser_2_topic': '/scan_rear'},
                    {'merged_scan_topic': '/scan_merged'},
                    {'merged_cloud_topic': '/cloud_merged'},
                    {'target_frame': 'base_link'},
                    {'calibration_file': calibration_file},
                    {'merged_scan_frame': 'scan_merged'},
                    {'laser_1_frame': 'scan_front'},
                    {'laser_2_frame': 'scan_rear'},
                    {'laser_1_x_offset': 0.0},
                    {'laser_1_y_offset': 0.0},
                    {'laser_1_yaw_offset': 0.0},
                    {'laser_2_x_offset': 0.0},
                    {'laser_2_y_offset': 0.0},
                    {'laser_2_yaw_offset': 0.0},
                    {'tolerance': 0.01},
                    {'queue_size': 5},
                    {'angle_increment': 0.00436332},
                    {'scan_time': 0.067},
                    {'range_min': 0.05},
                    {'range_max': 40.0},
                    {'min_height': -1.0},
                    {'max_height': 1.0},
                    {'angle_min': -3.141592654},
                    {'angle_max': 3.141592654},
                    {'inf_epsilon': 1.0},
                    {'use_inf': True},
                    {'enable_dynamic_param_refresh': True},
                    {'enable_shadow_filter': False},
                    {'enable_average_filter': False},
                    # Exclusion zone filtering
                    {'filter_config_file': filter_config_file},
                    {'enable_exclusion_zones': True},
                    # Mapping mode (rear exclusion for human-following mapping)
                    # mapping_keep_angle_min/max define the KEPT angle range (radians).
                    # Points with atan2 angle OUTSIDE this range are removed.
                    # Default [-135, +135] deg keeps front 270 deg, removes rear 90 deg.
                    {'enable_mapping_mode': False},
                    {'mapping_keep_angle_min': -2.356194},  # -135 deg (= -3*PI/4)
                    {'mapping_keep_angle_max': 2.356194},   #  135 deg (= 3*PI/4)
                ],
            )
        ],
        output='screen',
    )

    ld.add_action(base_to_merged_tf)
    ld.add_action(dual_laser_merger_node)

    return ld
