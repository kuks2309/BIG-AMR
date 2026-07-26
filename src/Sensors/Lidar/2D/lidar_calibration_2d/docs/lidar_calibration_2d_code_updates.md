# lidar_calibration_2d Code Updates

## 2026-04-26 / (pending commit) — 본 레포 이식 (LiDAR Wave D)

- T-Robot_nav_ros2_ws/src/Sensor/Lidar/2D/lidar_calibration_2d 통째 복사 (32 파일, 348 KB)
- 변경: 없음 (Eigen SVD-ICP 기반 외부 캘리브 도구, 원본 라인별 동일)
- 의존: rclcpp / sensor_msgs / tf2 / tf2_eigen / message_filters (rclpy / numpy / scipy / PyQt5 / yaml — 실행 시)
- 빌드 검증: colcon build --packages-select lidar_calibration_2d (별도 결과 기록)
- 실행 검증: 실 라이다·UI 환경 필요 — 별도 세션

참조 원본: /home/tc/T-Robot_nav_ros2_ws/src/Sensor/Lidar/2D/lidar_calibration_2d
계획: docs/plan/2026-04-26_lidar_port.md
결정: docs/request/2026-04-26_lidar_port.md

---

## 2026-03-17

### 16:00

- **추가** `ui/calibration_main.ui` — Sensor Flip 그룹박스 추가
  - `chkFlipFront`: Front 센서 Z-180° 반전 체크박스
  - `chkFlipRear`: Rear 센서 Z-180° 반전 체크박스
- **수정** `scripts/calibration_ui_window.py` — 센서별 flip 제어 기능
  - `_on_flip_front_changed()`: Front 센서 flipped 상태 토글 → 스캔 데이터 Y축 반전
  - `_on_flip_rear_changed()`: Rear 센서 flipped 상태 토글 → 스캔 데이터 Y축 반전
  - `_on_load_tf()`: Config에서 로드 시 flip 체크박스 자동 동기화
  - `_on_symmetric_correction()`: 대칭 보정 — front/rear 양쪽 동시 조정
- **추가** `scripts/tf_calculator.py` — `apply_symmetric_correction()` 함수
  - ICP 보정값을 front(-half)/rear(+half) 균등 분배
  - 상대 변환(ICP 결과) 보존하면서 대칭 위치 산출
- **수정** `ui/calibration_main.ui` — "Symmetric Correction" 버튼 추가
- **추가** `src/calibration_node.cpp` — C++ 자동 캘리브레이션에 대칭 분석 기능 추가
  - `SymmetryResult` 구조체, `normalizeAngle()` 헬퍼 함수
  - `computeSymmetryAnalysis()`: base_link 프레임에서 front/rear 대칭 분석
    - 이상적 대칭 rear 위치 계산 (ideal_rear = -front)
    - 위치 delta 2mm, 각도 delta 0.5° 임계값 기반 판정
  - ICP 캘리브레이션 완료 후 대칭 분석 결과 터미널 출력
  - YAML 출력에 `symmetry_analysis` 섹션 추가 (ideal, delta, is_symmetric)
- **이슈 픽스** Config TF값 `calibration_result1.yaml` 보정값 기준으로 통일
  - **문제**: `calibration_params.yaml`, `calibration_ui_params.yaml`, `tf_publisher_params.yaml`이 구형 AMR 센서 위치 사용
  - **수정**: 3개 config 모두 `calibration_result1.yaml` ICP-corrected 값으로 갱신
    - front: tx=0.3656, ty=0.2534, yaw=0.791332 (45.34°), flipped=true
    - rear (ICP corrected): tx=-0.387, ty=-0.3098, yaw=-2.357067 (-135.05°), flipped=true
  - `calibration_result.yaml` ← `calibration_result1.yaml` 내용으로 교체
- **수정** `scripts/calibration_ui_window.py` — 저장 경로 상대경로로 변경
  - `script_dir` 기반 → `src/Sensor/Lidar/2D/lidar_calibration_2d/config` 상대경로
  - 불필요한 `script_dir` 변수 제거 (Save Results, Save Current Jog)

### 15:30

- **이슈 픽스** `config/calibration_result.yaml` — 휴머노이더 AMR 센서 장착 변경 반영
  - **문제**: 이전 calibration_result.yaml이 잘못된 값으로 저장됨 (구형 AMR 설정)
  - **수정**: calibration_result1.yaml (정상 결과)로 교체
  - 센서 위치: front (0.32, 0.39, yaw=45°), rear (-0.32, -0.39, yaw=-135°)
  - **문제**: scan_front, scan_rear 위아래 반전됨 (RViz에서 스캔 방향 뒤집힘)
  - **수정**: flipped: false → true로 변경 (전방, 후방 순차 확인 후 적용)
  - ICP 보정: dx=0.067, dy=0.020, dyaw=0.27°, 대응거리=0.018m
- **수정** `config/calibration_params.yaml` — 새 장착 위치 반영
  - front: tx=0.32, ty=0.39, yaw=0.785398, upside_down=false
  - rear: tx=-0.32, ty=-0.39, yaw=-2.356194, upside_down=false
- **수정** `scripts/calibration_ui_window.py` — 저장 기본 경로를 install/ → src/ 폴더로 변경
  - 빌드 시 덮어쓰기 방지
- **수정** `ui/calibration_main.ui` — 캔버스 가로 200px 축소 (1280→1080), 컨트롤 패널 100px 확대 (330→430)
- **수정** `docs/sensor_mounting.md` — 휴머노이더 AMR 기준으로 센서 장착 정보 갱신

## 2026-02-17

### 20:01

- **수정** `config/calibration_params.yaml` - max_range: 8.0 → 40.0 (SICK 센서 사양 반영)
- **수정** `config/calibration_ui_params.yaml` - max_range: 12.0 → 40.0 (SICK 센서 사양 반영)

### 18:30

- **수정** `scripts/tf_calculator.py` — 대칭 분석/미러 함수 추가
  - `normalize_angle()`: 각도 [-pi, pi] 정규화
  - `compute_symmetry_info()`: front/rear 대칭 분석 (이상적 대칭 rear 계산, 비대칭 delta 산출)
  - `mirror_front_to_rear()`: front 기준 완전 대칭 rear TF 생성
- **수정** `ui/calibration_main.ui` — Symmetry Review 그룹박스 추가
  - `textSymmetry`: 대칭 분석 결과 표시 (읽기 전용)
  - `btnCheckSymmetry`: 대칭 검토 버튼
  - `btnMirrorFrontToRear`: Front→Rear 미러 버튼
  - `btnSaveCurrentJog`: 현재 스핀박스 값 저장 버튼 추가
- **수정** `scripts/calibration_ui_window.py` — 대칭 검토/미러/저장 기능 추가
  - `_on_check_symmetry()`: 현재 jog 값 대칭 분석
  - `_on_mirror_front_to_rear()`: front 기준 rear 미러 적용
  - `_on_save_current_jog()`: 현재 스핀박스 값으로 YAML 저장
  - `_on_apply_broadcast()`: ICP output 대신 현재 스핀박스 값 브로드캐스트하도록 수정
  - import에 `compute_symmetry_info`, `mirror_front_to_rear`, `save_calibration_yaml` 추가

### 17:12

- **수정** `scripts/calibration_ui_main.py` — 종료 시 lidar_tf_publisher 노드 확인 후 종료 기능 추가
  - `ros2 node list`로 실행 여부 확인 → `pkill -INT`로 종료 요청

### 17:05

- **수정** `scripts/scan_canvas.py` — `_draw_origin` ROS2 축 색상 규약 적용
  - X축(수직선): 빨강(RED), Y축(수평선): 초록(GREEN)
  - 축 레이블 "X", "Y" 추가, 원점 "M" 위치 조정

### 16:57

- **수정** `scripts/scan_canvas.py` — 캔버스 좌표계를 탑다운 로봇 뷰로 회전 (X+=위, Y+=왼쪽)
  - `_w2s`: World X→화면 세로(위), World Y→화면 가로(왼쪽)
  - `_s2w`: 역변환 업데이트
  - `_draw_sensor_crosshairs`: X축 화살표 방향 업데이트

