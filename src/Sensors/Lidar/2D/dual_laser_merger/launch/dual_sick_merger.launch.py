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
from launch_ros.actions import Node
from ament_index_python.packages import PackageNotFoundError, get_package_share_directory


def generate_launch_description():

    # 캘리브레이션 결과는 **있으면 쓰고 없으면 쓰지 않는다** — merger 는 빈 값이면 TF
    #   (base_link→scan_*) 경로로 동작한다(dual_laser_merger.cpp:47-59, 202).
    #   종전에는 이 경로를 무조건 만들어, 캘리브 패키지가 없는 기체에서 PackageNotFoundError 로
    #   **launch 전체가 죽었다** — 라이다 구동과 무관한 산출물 때문에 구동이 막히는 형태였다.
    #   캘리브레이션은 상시 수행 대상이 아니므로 하드 의존으로 두지 않는다.
    try:
        calibration_file = os.path.join(
            get_package_share_directory('lidar_calibration_2d'),
            'config', 'calibration_result.yaml'
        )
    except PackageNotFoundError:
        calibration_file = ''

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
        respawn=True,
        respawn_delay=2.0,
    )

    # 단독 실행판(dual_laser_merger_node)을 쓴다 — 컨테이너(component_container)는 respawn 시
    #   컴포넌트를 재적재하지 않아(Humble launch_ros 에 해당 처리 부재) 빈 컨테이너만 살아나는
    #   조용한 고장이 된다. 컴포넌트가 merger 하나뿐이라 composition 이득도 없다.
    dual_laser_merger_node = Node(
        package='dual_laser_merger',
        executable='dual_laser_merger_node',
        name='dual_laser_merger',
        respawn=True,
        respawn_delay=2.0,
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
            # ── 쌍 동기화 ──
            # tolerance 는 시간 허용오차가 아니다. message_filters 의 setAgePenalty 가중치로,
            # "후보를 얼마나 오래 붙들 것인가"를 매칭 비용에 반영할 뿐이다.
            {'tolerance': 0.01},                  # s, age penalty (상한 아님)
            {'queue_size': 5},                    # 개, 동기화 입력 덱 깊이
            # 실제 상한. 0.0 = 무제한(상류 기본 동작).
            # ⚠ 실기 실측(2026-08-08, 507초): 두 SICK 은 자유구동이라 쌍 어긋남이
            #    0.5 ms ↔ 14.2 ms 를 주기 260초로 왕복한다. 좁게 걸면 역위상 구간에서
            #    발행이 멈춘다 — 값 변경 전 `~/sync_skew` 로 분포를 먼저 재라.
            #    docs/issues_and_fixes/issues_and_fixes.md 2026-08-08 항목 참조.
            {'max_pair_skew': 0.0},               # s, 0 = 무제한
            # 출력 스탬프 출처. laser_1 = 상류 기본 동작(전방 스탬프, 후방 시각은 버려짐).
            # 도킹처럼 시각 정합이 중요한 경로에서는 latest 를 검토할 것.
            {'output_stamp': 'laser_1'},          # laser_1|laser_2|latest|earliest|midpoint
            {'publish_sync_diagnostics': True},   # ~/sync_skew 발행 + 주기 통계 로그
            {'sync_report_period': 5.0},          # s, 통계 로그 주기
            {'angle_increment': 0.00436332},
            # 실측 정정(2026-08-08): SICK 자기신고 scan_time 은 0.030 s, merged 발행 주기는
            # 0.0293 s(34.1 Hz)인데 0.067(=14.9 Hz)을 실어 보내고 있었다. scan_time 은 하류의
            # 모션 왜곡 보정 입력이므로 2배 이상 틀리면 보정이 어긋난다.
            # 근거: bag 0528_speed_1.5_test_20260530_125451 및 2026-08-08 실기 507초 관측
            #       (merged.scan_time 0.067 vs front.scan_time 0.030, 스탬프 간격 중앙 29.3 ms)
            {'scan_time': 0.0293},
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
        output='screen',
    )

    ld.add_action(base_to_merged_tf)
    ld.add_action(dual_laser_merger_node)

    return ld
