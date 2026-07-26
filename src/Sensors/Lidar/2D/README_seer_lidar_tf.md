# Seer install_info → lidar TF (base_footprint → scan_front/scan_rear)

Seer(SRC)가 보유한 라이다 외부 캘리브(장착 pose)를 읽어 lidar TF 에 반영한다.
재측정 없이 Seer 를 단일 출처로 사용. (사용자 지시 2026-07-25: 자주 안 바뀌므로 **요청 시에만** 갱신)

## 권장: seer_lidar_tf 노드 (패키지)
`seer_lidar_tf/` ROS2 패키지. **2가지 모드**:

- **write 모드 (권장)** — Seer 조회 → merger `calibration_result.yaml` 로 값을 **복사 기록하고 즉시 종료**.
  런타임 TF 는 **merger 가 소유**(scan_merged→scan_front/rear) → 프레임 부모 충돌 없음.
  ```bash
  ros2 run seer_lidar_tf seer_lidar_tf_node --ros-args \
    -p calibration_out:=src/Sensors/Lidar/2D/lidar_calibration_2d/config/calibration_result.yaml
  ```
- **publish 모드** — `calibration_out` 미지정 시 base_footprint→scan_front/rear static TF 를 상주 발행.
  **merger 를 안 쓸 때만** 사용(merger 와 동시 상주 시 scan_front 부모 이중 = 충돌).
  ```bash
  ros2 run seer_lidar_tf seer_lidar_tf_node        # 또는 ros2 launch seer_lidar_tf seer_lidar_tf.launch.py
  ```

## 참고(구버전, 스냅샷): 아래 2개는 노드 이전의 수동 도구 — 노드로 대체됨
- `seer_lidar_tf_launch.py` — base_footprint → scan_front/scan_rear static TF (값 baking).
- `seer_read_lidar_install.py` — Seer 재조회로 install_info 출력(수동 복사용).

## 값 출처 (스냅샷 2026-07-25)
SEER SRC `192.168.44.82:19204`, Robot Status API **1009**(robot_status_laser_req) → **11009** 응답,
`lasers[].install_info`. ⇒ [References/Seer-Driver/robokit_tcp_api_laser.md](../../../../References/Seer-Driver/robokit_tcp_api_laser.md)

| child frame | device | x (m) | y (m) | z (m) | yaw (deg) |
|---|---|---|---|---|---|
| scan_front | FrontLiDAR | 0.8808743642346627 | -0.5783268634147752 | 0.0 | -45.57274026382727 |
| scan_rear | RearLiDAR | -0.8564035555844536 | 0.6067443643452458 | 0.0 | 135.0925107833687 |

- parent = **base_footprint** (사용자 지정), z=0 (⚠ **Seer install_info 는 2D(x/y/yaw)만 제공** — z/roll/pitch 미제공. 실제 장착 높이가 필요하면 launch 의 z 를 실측값으로 교체).
- child frame 은 sick_safetyscanners2 드라이버가 발행하는 scan frame_id(scan_front/scan_rear)와 일치.

## 실행
```bash
source /opt/ros/humble/setup.bash
ros2 launch src/Sensors/Lidar/2D/seer_lidar_tf_launch.py
# 검증
ros2 run tf2_ros tf2_echo base_footprint scan_front   # Translation [0.881,-0.578,0], yaw -45.573°
ros2 run tf2_ros tf2_echo base_footprint scan_rear    # Translation [-0.856,0.607,0], yaw 135.093°
```

## 갱신 절차 (재장착·재캘리브 시에만)
```bash
python3 src/Sensors/Lidar/2D/seer_read_lidar_install.py    # Seer 재조회, LIDARS 형식으로 출력
# 출력값을 seer_lidar_tf_launch.py 의 LIDARS 상수에 반영
```

## 검증 로그 (2026-07-25)
- 갱신 스크립트 조회값 = launch baking 값 일치(ret_code=0).
- tf2_echo: front [0.881,-0.578,0]/yaw-45.573°, rear [-0.856,0.607,0]/yaw135.093° — install_info 와 일치 확인.
