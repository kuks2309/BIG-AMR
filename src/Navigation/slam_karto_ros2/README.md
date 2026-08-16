# slam_karto_ros2 — Seer SLAM 매핑 ROS2 어댑터

프레임워크-독립 코어 [`slam_karto_core`](../slam_karto_core)(Open Karto front-end + g2o backend)를
rclcpp 노드로 감싼다. 맵 저장은 형제 [`mcl2d_map`](../mcl2d_map) 의 `saveSmap()` 을 그대로 쓴다.

```
/scan_merged (LaserScan, BEST_EFFORT) ┐
                                       ├─> slam_mapping ─┬─> /map (OccupancyGrid, 0.02 m)
/odom        (Odometry,  BEST_EFFORT) ┘                  └─> ~/save_map → *.smap
```

---

## ⚠ TF 를 발행하지 않는다 / mcl2d 와 배타 실행

이 노드는 **TF 를 하나도 내지 않는다.** `map→odom` 은 `mcl2d` 소유로 확정돼 있고
(`docs/code_review/mcl2d-localization-chain/2026-08-07.md` H1), `odom→base_link` 는
`icp_odometry` 소유다. 매핑 노드가 `map→odom` 을 같이 내면 `odom` 프레임의 부모가 둘이 되어
TF 트리가 깨진다.

따라서 **매핑 중에는 `mcl2d_localization` 을 띄우지 말 것.** 프레임이 겹치는 문제만이 아니라,
같은 `/scan_merged`·`/odom` 을 무거운 소비자 둘이 나눠 갖게 되어 양쪽 다 처리율이 떨어진다.
`mcl2d_ros2` 의 bringup 을 쓸 때는 `localization:=false` 로 띄운다.

```bash
# 입력 체인만 (라이다 + 병합 + ICP 오도메트리)
ros2 launch mcl2d_ros2 bringup.launch.py localization:=false map_path:=''
# 또는 각각
ros2 launch dual_laser_merger sick_with_merger.launch.py
ros2 launch icp_odometry_bringup icp_odometry.launch.py
```

RViz 에서 `/map` 을 보려면 `map` 프레임이 TF 트리에 있어야 한다. 매핑 중에는 그 프레임을
아무도 내지 않으므로, 보고 싶을 때만 정적 TF 를 임시로 하나 걸어 둔다(매핑 결과에는 영향 없음):

```bash
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 map odom
```

---

## 사용법

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash

# 1) 기동 (기본은 auto_start:=true — 뜨자마자 스캔을 받는다)
ros2 launch slam_karto_ros2 slam_mapping.launch.py save_path:=/home/nvidia/map/new.smap

# 수동 시작을 원하면
ros2 launch slam_karto_ros2 slam_mapping.launch.py auto_start:=false save_path:=/home/nvidia/map/new.smap
ros2 service call /slam_mapping/start_mapping std_srvs/srv/Trigger

# 2) 로봇을 주행시켜 지도를 채운다. 진행 상황은 진단 서비스로 본다.
ros2 service call /slam_mapping/mapping_status std_srvs/srv/Trigger

# 3) 종료 + 저장
ros2 service call /slam_mapping/stop_mapping std_srvs/srv/Trigger
ros2 service call /slam_mapping/save_map     std_srvs/srv/Trigger
```

`save_path` 는 런타임에 바꿔도 된다 — `~/save_map` 은 호출 시점의 파라미터를 읽는다.

```bash
ros2 param set /slam_mapping save_path /home/nvidia/map/another.smap
```

`~/stop_mapping` 은 **그래프를 지우지 않는다.** 멈춘 뒤에 저장할 수 있어야 하기 때문이다.
그래프를 비우는 것은 `~/start_mapping` 이다(= 새 매핑 세션 시작).

---

## 토픽

| 방향 | 토픽 | 타입 | QoS | 비고 |
|---|---|---|---|---|
| 구독 | `/scan_merged` | `sensor_msgs/LaserScan` | `SensorDataQoS` (BEST_EFFORT, depth 5) | 병합 스캔. RELIABLE 로 구독하면 QoS 불일치로 한 건도 오지 않는다 |
| 구독 | `/odom` | `nav_msgs/Odometry` | BEST_EFFORT, depth 200 | `icp_odometry`(rtabmap_odom)가 BEST_EFFORT 로 낸다 |
| 발행 | `/map` | `nav_msgs/OccupancyGrid` | RELIABLE + TRANSIENT_LOCAL, depth 1 | 늦게 붙는 RViz 가 마지막 맵을 받도록 |
| 발행 | `/tf`, `/tf_static` | — | — | **발행하지 않는다** (위 참조) |

`/map` 래스터화 규칙: 점군을 `map_resolution`(기본 0.02 m) 격자에 찍어 **점유셀만 100**,
나머지는 **미지(-1)** 로 둔다. **free space 라이캐스팅은 하지 않는다** — 원본 산출물은 점군이고
자유공간 판정의 근거가 아직 없다. 필요해지면 별도 결정으로 추가한다.

## 서비스 (전부 `std_srvs/srv/Trigger`)

| 서비스 | 원본 대응 | 동작 |
|---|---|---|
| `~/start_mapping` | `6100` | 그래프를 새로 만들고 스캔 수용 시작. 카운터도 초기화 |
| `~/stop_mapping` | `6101` | 스캔 수용 중단. 그래프·맵은 유지(이어서 저장 가능) |
| `~/save_map` | `4010` | `buildMap()` → `mcl2d::SmapMap` → `saveSmap(save_path)` |
| `~/mapping_status` | — | 처리·폐기 카운터와 g2o 계측을 문자열로 반환 |

`~/mapping_status` 응답 예:

```
accepting=1 scans=30 queue=0/50 added=30 gate_rejected=90 invalid=0
dropped_queue_full=0 dropped_no_odom=0
g2o_compute_calls=0 nodes=30 edges=29 edges_rejected=0 last_iterations=0 has_fixed_node=1
```

- `gate_rejected` 는 Karto 의 이동 게이트(0.2 m / 0.05 rad) 미달이다 — **정상 동작**이다.
- `g2o_compute_calls=0` 은 루프클로저가 한 번도 성립하지 않았다는 뜻이다(직선 주행이면 정상).
- `has_fixed_node=0` 이면 맵 원점 앵커가 걸리지 않은 것이다 — SE(2) 게이지 자유도가 남는다.

---

## 파라미터

정본은 [`config/slam_mapping.yaml`](config/slam_mapping.yaml) 이며 **거기 적힌 값이 곧 노드 기본값**이다.

| 파라미터 | 기본값 | 단위 | 설명 |
|---|---|---|---|
| `scan_topic` / `odom_topic` / `map_topic` | `/scan_merged` `/odom` `/map` | — | 토픽 이름 |
| `map_frame` | `map` | — | `OccupancyGrid` 의 `frame_id` |
| `laser_offset_x` / `_y` / `_yaw` | `0.0` | m, m, rad | **스캔 토픽 프레임 기준** 라이다 장착 오프셋 (아래 참조) |
| `min_range` / `max_range` | `0.05` / `30.0` | m | 유효 거리 구간. 밖의 빔은 무반사(=`max_range`)로 정규화 |
| `map_resolution` | `0.02` | m/cell | 원본 해상도. 근거: 회수 실맵 헤더 `"resolution":0.02` |
| `max_map_cells` | `25000000` | cell | 격자 상한. `OccupancyGrid.data` 는 셀당 1 byte = 메시지 크기 |
| `map_publish_period` | `2.0` | s | `/map` 재산출 주기. `buildMap()` 은 전 스캔을 훑는다 |
| `rssi_threshold` | `0.0` | — | 이 값을 **초과**하는 `intensities` 빔만 `rssiPosList` 로 |
| `g2o_max_iterations` | `100` | 회 | LM 반복 상한 |
| `queue_size` | `50` | 개 | 처리 큐 길이 |
| `queue_full_policy` | `keep_latest` | — | `keep_latest`(오래된 것 폐기) \| `drop_newest`(새 것 폐기) |
| `odom_match_max_dt` | `0.035` | s | 스캔↔오도 시각차 게이트 |
| `auto_start` | `true` | — | `false` 면 `~/start_mapping` 전까지 스캔을 받지 않는다 |
| `save_path` | `""` | — | `~/save_map` 저장 경로. 비면 `save_map` 이 실패한다 |
| `map_name` / `smap_version` | `slam_map` / `1.0.6` | — | `.smap` 헤더 |

### 라이다 장착 오프셋이 왜 0 인가

기본 입력 `/scan_merged` 의 `frame_id` 는 `scan_merged` 이고, 그 프레임은 `base_link` 와
**동일 위치**로 static TF 가 걸린다
(`src/Sensors/Lidar/2D/dual_laser_merger/launch/dual_sick_merger.launch.py:41-43` — 인자 전 성분 0).
병합기가 두 센서의 빔을 이미 이 프레임으로 옮겨 놓으므로, 여기서 또 오프셋을 주면 **이중 적용**이다.

원시 단일 라이다(`/scan_front`·`/scan_rear`)를 직접 물릴 때만 그 센서의 실측 장착값을 넣는다.
Foil_A082 정값(`src/Navigation/mcl2d_ros2/config/mcl2d.yaml:26-27`, Seer 컨트롤러 1500 조회 2026-08-07):

| 센서 | x (m) | y (m) | yaw (rad) |
|---|---|---|---|
| FrontLiDAR | `0.881676` | `-0.578664` | `-0.785398` (-45.000°) |
| RearLiDAR | `-0.857000` | `0.597100` | `2.361256` (135.290°) |

---

## 구조

- **워커 스레드**가 `processRecord`(스캔매칭 + 루프클로저 + g2o)를 돌린다. 콜백 스레드에서
  직접 부르면 executor 가 수백 ms 막혀 구독이 밀린다. 콜백은 오도 짝짓기와 큐 삽입만 한다.
- **오도 짝짓기는 최근접(nearest-in-time)** 이다. 선형보간을 쓰지 않은 이유: 이 스택의 `/odom` 은
  바로 그 `/scan_merged` 로부터 `icp_odometry` 가 산출한다
  (`icp_odometry_bringup/launch/icp_odometry.launch.py:4,63`). 스캔과 오도가 같은 원천·같은
  주기라 스캔 시각을 감싸는 두 표본이 있는 상황 자체가 드물고, 있어도 보간은 ICP 가 보고하지
  않은 중간 운동을 지어내는 셈이 된다. 대신 `odom_match_max_dt` 게이트로 멀면 버리고 그 수를 센다.
- **큐 포화**는 `queue_full_policy` 로 정하고, 폐기 수는 throttle 로그와 `~/mapping_status` 에 낸다.
  `dropped_queue_full` 이 계속 늘면 매핑이 입력보다 느린 것이다 — 주행 속도를 낮추거나
  `g2o_max_iterations` 를 줄인다.

### 빌드 결합 방식

`slam_karto_core` 는 **설치 규칙이 없는** 순수 CMake 프로젝트라(`install(` 0건) `find_package` 로
쓸 임포트 타깃이 없다. 그래서 형제 `mcl2d_ros2` 선례대로 **코어 소스를 이 패키지에서 직접
컴파일**한다(`add_subdirectory` 아님). 다만 동봉 Open Karto 가 LGPL-3.0 이므로 정적으로 뭉치지
않고 `libkarto_vendored.so` · `libslam_karto_core.so` · `libsmap_io.so` 로 **분리 빌드**한다.

**g2o RPATH 함정**: `libg2o_types_slam2d.so` 는 `libg2o_opengl_helper.so` 를 `NEEDED` 로 갖는데
자기 `RUNPATH` 가 없다. `DT_RUNPATH` 는 그 객체의 직접 `NEEDED` 에만 적용되고 전이되지 않으므로
기본 링크로는 전이 해석에 실패한다. 코어와 동일하게 `-Wl,--disable-new-dtags` 로 **`DT_RPATH`** 를
낸다(전이됨). 확인:

```
$ readelf -d install/slam_karto_ros2/lib/slam_karto_ros2/slam_mapping_node | grep RPATH
 0x...f (RPATH)  Library rpath: [/opt/ros/humble/lib/aarch64-linux-gnu:$ORIGIN:$ORIGIN/..]
```

---

## 원본(Seer) 대응표

| 원본 | 여기 |
|---|---|
| API `6100` 매핑 시작 | `~/start_mapping` |
| API `6101` 매핑 종료 | `~/stop_mapping` |
| API `4010` 맵 저장 | `~/save_map` → `.smap` |
| `Message_MapLogData` | `slam_karto_core::MapLogRecord` (스캔 + 오도) |
| `Message_Map` | `slam_karto_core::MapResult` → `mcl2d::SmapMap` |
| `normalPosList` | `MapResult::normal_pos_list` → `/map` 점유셀 · `.smap` 장애물 |
| `rssiPosList` | `MapResult::rssi_pos_list` (임계 `rssi_threshold` 초과 빔) |

## 알려진 격차

코어 헤더([`seer_slam_mapper.hpp`](../slam_karto_core/include/slam_karto_core/seer_slam_mapper.hpp))가
명시한 것 외에, 이 어댑터 계층의 미해결 항목:

1. `rssi_threshold` 의 원본 런타임값(`RssiThres`)이 미확정이다. 기본 `0.0` 은 구현자 선택이다.
2. 원본 후처리(HTLine Hough 벽각 보정)는 여기에도 없다.
3. `/map` 은 점군 래스터화만 한다 — free space 라이캐스팅 미구현(의도적).
4. 실기 `/scan_merged`·`/odom` 으로 한 바퀴 돌려 루프클로저(`g2o_compute_calls > 0`)까지 확인한
   기록은 아직 없다. 현재 검증은 합성 입력 기동 스모크까지다.
