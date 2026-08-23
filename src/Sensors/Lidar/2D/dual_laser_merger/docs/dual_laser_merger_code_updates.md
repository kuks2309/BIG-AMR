# dual_laser_merger Code Updates

## 2026-08-23 / (pending commit) - launch 전 노드 respawn + merger 를 단독 실행판으로 전환

- **목적**: 노드 사망 시 자동 재기동(운용 회복력). 사용자 지시(2026-08-23 "launch 에 respawn 부터 적용").
- **변경**: `launch/dual_sick_merger.launch.py` — ① static TF·merger 에 `respawn=True, respawn_delay=2.0`
  ② merger 를 `ComposableNodeContainer`(merger_container) → 단독 실행판 `dual_laser_merger_node` 로 전환
  (파라미터 동일, CMake 가 이미 `EXECUTABLE dual_laser_merger_node` 를 생성하고 있어 빌드 변경 없음).
- **전환 사유**: Humble launch_ros 는 컨테이너 respawn 시 컴포넌트를 재적재하지 않는다
  (`composable_node_container.py`·`load_composable_nodes.py` 에 respawn 처리 부재를 실기 설치본에서 확인)
  — respawn 을 걸면 빈 컨테이너만 살아나는 조용한 고장이 된다. 컴포넌트가 merger 1개뿐이라
  composition(프로세스 내 통신) 이득도 없다.
- **검증(실기 2026-08-23)**: `kill -9` → launch 가 died 감지·재기동(pid 2420402→2421612),
  `/scan_merged` 34.06 Hz 회복(스트림 공백 최대 0.094 s 관측), Calibration mode 파라미터 유지.
- **내구(실기 2026-08-23, 120분)**: 15분 간격 6노드 순환 `kill -9`(merger 포함) 전 건 회복 —
  merger proc 2.15 s / `/scan_merged` 3.7 s. 전 구간 프로세스 121/121 점검 6/6, merger 자체
  5 s 통계로 34 pairs/s 연속 확인(공백 0). 마지막 30분 무교란 소크 무결.
- **함수표 갱신**: `docs/code_review/dual-laser-merger-sync/2026-08-08.md` #21·B-3 (루트+병기 동기).

## 2026-08-20 / (pending commit) - 캘리브 패키지 하드 의존 제거: 없으면 우회

- **증상**: `lidar_calibration_2d` 가 설치되지 않은 기체에서 `dual_sick_merger.launch.py` 가
  `PackageNotFoundError` 로 **launch 전체를 죽였다**. 그 위에 얹힌 상위 진입점
  (`mcl2d_ros2/bringup.launch.py` 의 `lidar:=true` 계층)까지 같이 실패한다.
  실측: LGIT MOMA 기체(lgit-c6-4)에서 bringup 이 이 예외로 중단, 라이다·측위 모두 미기동.
- **원인**: `generate_launch_description()` 첫 줄에서 캘리브 결과 경로를 **무조건** 만들었다
  (`get_package_share_directory('lidar_calibration_2d')`). 캘리브 결과는 구동 필수물이 아니고
  (merger 는 빈 값이면 TF 경로로 동작), 캘리브레이션 자체도 상시 수행 대상이 아니다.
- **조치**: 그 조회를 `try/except PackageNotFoundError` 로 감싸 **없으면 `calibration_file=''`**.
  캘리브 패키지가 있는 기체(Big-AMR)는 거동 불변 - 같은 파일을 그대로 넘긴다.
- **파일**: `launch/dual_sick_merger.launch.py` (import 1줄 + 조회 블록)
- **검증**: 구문 검사 통과. 캘리브 있는 이 장비에서 경로 산출값이 종전과 동일함을 확인.

## 2026-07-25 / (pending commit) — Big-AMR extrinsic/exclusion 을 SEER install_info 로 교정

- **증상**: Big-AMR 에서 merge 구동 시 `/scan_merged` 지오메트리 오류 소지. calibration_result.yaml 이
  **참조 로봇(TR_Nav) 값**(front 0.504,-0.254 / rear -0.502,0.243)이라 Big-AMR 실장착(front 0.881,-0.578 /
  rear -0.856,0.607)과 radial 거리 약 2배 차이 → 두 스캔 상대배치 왜곡.
- **진단**: merger 는 calibration_file 존재 시 Calibration mode 로 그 YAML extrinsic 을 사용(src:47-59,200-292).
  로그의 `scan_merged→scan_front/rear` 값이 참조 로봇 값으로 찍힘.
- **조치**:
  - `lidar_calibration_2d/config/calibration_result.yaml` → **SEER install_info(API 1009) 값으로 교정**
    (front 0.8809/-0.5783/-45.573°, rear -0.8564/0.6067/135.093°, icp=0). 원본 백업: scratchpad/calibration_result_ORIG.yaml.
  - `config/filter_config.yaml` robot_body exclusion → 두 센서 bbox+10cm(x[-0.96,0.98] y[-0.68,0.71])로 확대.
- **검증**: SICK 2센서 + merger 재구동 → merger 로그 extrinsic = Seer 값 일치, `/scan_merged` **34.0Hz(std 0.0005)**,
  360°, 유효 1009점(0.72~22.4m). Seer 는 유니캐스트 테스트 후 ret_code=0/lasers=2 정상 원복.
- **잔여(⚠)**: ① `flipped=true` 는 참조와 동일 가정 — rviz 시각 검증 필요. ② TF 소유권: merger 가
  scan_merged→scan_front/rear 발행 → seer_lidar_tf 노드(base_footprint→scan_front/rear)와 병행 시 프레임
  부모 충돌 → 둘 중 하나만 사용. ③ Seer 공존은 멀티캐스트 그룹 일치 필요(유니캐스트 테스트는 Seer 점유).
- 출처: [References/Seer-Driver/robokit_tcp_api_laser.md](../../../../../References/Seer-Driver/robokit_tcp_api_laser.md),
  [seer_lidar_tf](../../seer_lidar_tf/)

## 2026-07-09 / (pending commit) — 🔴 병합 반쪽 프레임의 원인은 본 패키지 아님 (참조 기록)

- `/scan_merged` 반쪽 프레임 (도킹 이상 기동 FAILURES #29) 조사 결과 merger 무혐의 확정 — 두 병합 경로
  모두 한쪽 클라우드 empty 시 전체 기각 (반쪽 생성 불가). 원인 = 상류 sick 드라이버 UDP 버퍼 오버플로우.
- 상세: [sick_safetyscanners2/docs/2026-07-09_udp_rcvbuf_critical.md](../../sick_safetyscanners2/docs/2026-07-09_udp_rcvbuf_critical.md)

## 2026-04-26 / (pending commit) — 본 레포 이식 (LiDAR Wave B)

- T-Robot_nav_ros2_ws/src/Sensor/Lidar/2D/dual_laser_merger 통째 복사 (16 파일, 23 MB)
- 변경: 없음 (외부 패키지, 원본 라인별 동일 유지)
- bag/dual_lidar/dual_lidar_0.db3 (~23 MB) 포함 — 디버깅 자료 보존
- 의존: pcl_ros / pcl_conversions / laser_geometry / tf2_sensor_msgs / message_filters / yaml-cpp (apt ROS2 Humble 표준)
- 빌드 검증: colcon build --packages-select dual_laser_merger (별도 결과 기록)

참조 원본: /home/tc/T-Robot_nav_ros2_ws/src/Sensor/Lidar/2D/dual_laser_merger
계획: docs/plan/2026-04-26_lidar_port.md
결정: docs/request/2026-04-26_lidar_port.md

---

## 2026-02-18

### 14:20

- **추가** `config/filter_config.yaml` - AMR 바디 반사 제거용 exclusion zone 설정 파일
- **수정** `include/dual_laser_merger/dual_laser_merger.hpp` - ExclusionZone 구조체, 필터 멤버변수/메서드 선언 추가
- **수정** `src/dual_laser_merger.cpp` - load_filter_config(), apply_exclusion_zones(), apply_mapping_mode_filter() 구현, 파이프라인 통합, 파라미터 선언/검증 추가
- **수정** `launch/dual_sick_merger.launch.py` - filter_config_file, enable_exclusion_zones, enable_mapping_mode, mapping_keep_angle_min/max 파라미터 추가

## 2026-02-17

### 20:01

- **수정** `launch/dual_sick_merger.launch.py` - range_max: 5.5 → 40.0 (SICK 센서 최대 거리에 맞춤)

### 15:48

- **수정** `launch/dual_sick_merger.launch.py` - scan_merged TF Z=0.2865 → Z=0 (base_link과 동일 위치)
