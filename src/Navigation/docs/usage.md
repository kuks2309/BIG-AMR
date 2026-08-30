# mcl2d 사용법 (간단)

## ROS2 노드

```bash
ros2 run mcl2d_ros2 mcl2d_localization_node \
  --ros-args -p map_path:=/path/to/map.smap \
  -p init_x:=0.0 -p init_y:=0.0 -p init_theta:=0.0
```

| 구분 | 이름 | 타입 |
| --- | --- | --- |
| 구독 | `odom` | nav_msgs/Odometry |
| 구독 | `scan_front`, `scan_rear` | sensor_msgs/LaserScan |
| 발행 | `mcl_pose` | geometry_msgs/PoseWithCovarianceStamped (+TF) |

파라미터: `map_path`(Seer `.smap`), `init_x`/`init_y`/`init_theta`(초기 자세, m/rad).
주의: 듀얼 라이다 장착 위치는 현재 Roll_A084 값으로 코드에 고정
(`mcl2d_localization_node.cpp:42` — 다른 차량이면 이 줄 수정).

## 비-ROS2 (Tools/mcl2d_standalone)

`Mcl2dLocalizer` 파사드 호출 순서:

```cpp
Mcl2dLocalizer loc(Mcl2dParams{}, seed);
loc.loadMap(obstacles, reflectors);   // .smap 로더(mcl2d_map) 결과 전달
loc.setLasers({{x, y, yaw}, ...});    // 라이다 장착 위치(m/rad)
loc.setInitialPose({x, y, theta});
loc.update(prev_odom, cur_odom, {front_scan, rear_scan}, stopped, dt);  // 주기 호출 → 추정 자세 반환
loc.lastExtraMove();   // 이번 주기에 선택된 산포 크기·모드(1~5) — 진단용
```

`stopped`(오도 정지 보고)를 넘기면 그 주기의 결정론 이동(kMove)을 생략한다 — 원본 `DoMoveAction` 의
`is_stop` 분기와 같다. 넘기지 않으면 기본 `false` 라 정지 중에도 이동이 적용되니, 정지 신호가 있으면
반드시 배선할 것(슬립 복구 판정도 `stopped`·`dt` 를 쓴다).

데모 실행: `Tools/mcl2d_standalone/build/mcl2d_non_ros_demo`
