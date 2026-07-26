# trnav_2ws_interfaces — code updates

2026-05-28 / HH:MM - (pending commit) / **PP → MPC 마이그레이션 (Phase B)** — action type rename

- **rename** `action/AMRMotionPurePursuit.action` → `action/AMRMotionMpc.action` (git mv, 필드 동일)
- **rename** `action/AMRMotionPurePursuitReverse.action` → `action/AMRMotionMpcReverse.action` (git mv, 필드 동일)
- **수정** `CMakeLists.txt:23-24` — `rosidl_generate_interfaces` 목록 `AMRMotionPurePursuit{,Reverse}.action` → `AMRMotionMpc{,Reverse}.action` + 코멘트 (HF5 R=1m 90° MPC hdg 0.22° vs PP 4.96° 20× 우위 결정 근거)

Cross-platform 영향: `trnav_motion_dd/src/dd_pure_pursuit_action_server.cpp` 가 `AMRMotionPurePursuit` 공용 사용 (DD source_id 57 = `DRIVE_DD_PURE_PURSUIT` 의 action server) → 본 rename 으로 DD 빌드 linker 실패. 사용자 결정 "DD는 아직 고려 대상 아님" 으로 `trnav_motion_dd/COLCON_IGNORE` 추가 (Phase 2 재개 시 DD action type 분리 결정 필요).

전체 `colcon build` 49 packages PASS (DD 제외).

---

2026-05-21 / HH:MM - (pending commit) / 변경: `AMRMotionCrab.action` 폐기 + `AMRMotionCrabLinear.action` 신규 (target_yaw 능동 유지 + start↔end 직선 closed-loop)

기존 crab (body-frame open-loop 적분, heading 단순 모니터링) 폐기. 사용자 요청 ([docs/request/2026-05-20_crab_target_yaw_path_following.md](../../../../docs/request/2026-05-20_crab_target_yaw_path_following.md)) 의 target_yaw 명시·유지 + world-frame 직선 closed-loop 추종을 단일 action 으로 교체.

- 삭제: `action/AMRMotionCrab.action` + `CMakeLists.txt` entry (line 26 옛 entry)
- 추가: `action/AMRMotionCrabLinear.action` (Goal: start_x/y, end_x/y, target_yaw_deg, max_linear_speed, acceleration, hold_steer, exit_steer_angle, exit_speed, entry_speed, has_next, enable_localization_watchdog)
- `CMakeLists.txt:25` entry 교체 (AMRMotionCrab → AMRMotionCrabLinear) + 변경 코멘트 추가
- mux source_id=4 슬롯 재사용 (별도 신규 슬롯 없음). 짝 패턴: 단일 (path 방향 sign 으로 양방향 표현).
- Result status 의미: 0=success / -1=cancelled / -2=invalid_param (초기 heading > threshold 포함) / -3=timeout / -4=heading_abort | loc_timeout / -5=loc_jump / -6=tf_lookup_fail
- 관련 action server: `src/Control/AMR-Motion/trnav_2ws_action_server/docs/amr_motion_action_server_code_updates.md` [2026-05-21]
- 관련 plan: [docs/plan/2026-05-20_crab_linear_action_implementation.md](../../../../docs/plan/2026-05-20_crab_linear_action_implementation.md)

---

2026-05-18 / 22:10 - (pending commit) / 추가: 6 .action 의 goal 에 `bool enable_localization_watchdog true` 필드 (B patch)

acs_gui Link.enable_localization_watchdog → goal 전달 인터페이스.

- 수정 (.action 6 파일, goal 의 마지막 필드 직전 / `---` 구분자 직전):
  - `action/AMRMotionTranslateForward.action`
  - `action/AMRMotionTranslateReverse.action`
  - `action/AMRMotionPurePursuit.action`
  - `action/AMRMotionPurePursuitReverse.action`
  - `action/AMRMotionYawControl.action`
  - `action/AMRMotionYawControlReverse.action`
- 새 필드: `bool enable_localization_watchdog true` (literal default — ROS msg/action default. unset → true 보장. Codex 리뷰 반영 fix 1)
- 비변경: AMRMotionSpin / AMRMotionCrab / AMRMotionTurn (loc_monitor 미사용 — scope 외)
- Effective rule: client 가 set 안 해도 default true → AND-결합 시 watchdog 기본 ON 보존

검증: `colcon build --packages-up-to trnav_2ws_action_server --symlink-install` PASS (4 packages, 9min 47s).

관련 이슈: `docs/issues_fixes/issues_and_fixes.md` [2026-05-18 22:10] B patch.
관련 action server: `src/Control/AMR-Motion/trnav_2ws_action_server/docs/amr_motion_action_server_code_updates.md` [2026-05-18 22:10].

---

2026-04-29 / HH:MM - (pending commit) / 추가: AMRMotionPurePursuit action (nav_msgs/Path 다중 waypoint, BICYCLE 전륜)
- `action/AMRMotionPurePursuit.action` (신규)
  - Goal: `nav_msgs/Path path` (map frame, ≥2 poses), max_linear_speed, acceleration, hold_steer, exit_steer_angle, exit_speed, entry_speed, has_next, control_mode (BICYCLE)
  - Result: status, actual_distance, final_lateral_error, final_heading_error, elapsed_time
  - Feedback: current_distance, current_lateral_error, current_heading_error, current_vx/vy/omega, phase, w1/w2_drive_rpm, lookahead_x, lookahead_y
  - 알고리즘: Pure Pursuit base_link frame 변환 후 직접형 — `delta_f = atan2(2*L*L_y, L_x²+L_y²)`, delta_r=0
- `CMakeLists.txt` — `rosidl_generate_interfaces` 에 PurePursuit 추가, `find_package(nav_msgs)` + `DEPENDENCIES nav_msgs` 추가, Wave 주석 갱신 (2026-04-29 PurePursuit)
- `package.xml` — `<depend>nav_msgs</depend>` 추가

빌드 검증: `colcon build --base-paths src --packages-select trnav_2ws_interfaces` 성공.
`ros2 interface show trnav_2ws_interfaces/action/AMRMotionPurePursuit` 노출 확인 (nav_msgs/Path 정상 expand).

요청: `docs/request/2026-04-29_pure_pursuit_port.md`
플랜: `docs/plan/2026-04-29_pure_pursuit_implementation.md`

---

2026-04-28 / 19:00 - (pending commit) / 정정: AMRMotionYawControlReverse 주석 — wheel 부호 반전 항목 제거 (R1 SIL 1차 fix 반영)
- `action/AMRMotionYawControlReverse.action`:
  - "wheel velocity 출력 부호 반전 (vel *= -1)" 항목 제거
  - 부연: IK 가 vx_signed<0 입력으로 wheel direction 자동 처리, 출력단 추가 부호 곱하기 없음
  - translate_reverse 의 vel*=-1 패턴은 PathController forward 재사용 trick 의 부산물이라 본 액션엔 부적용 명시
- 정정 사유: SIL R1 에서 이중 부호 반전 발견 (이슈 [2026-04-28 19:00])

---

2026-04-28 / 12:00 - (pending commit) / 추가: AMRMotionYawControlReverse action (yaw_control 의 reverse 분리)
- `action/AMRMotionYawControlReverse.action` (신규)
  - Goal: target_yaw_deg, target_distance, **vx_max (magnitude, >0)**, acceleration, max_steer_deg, kp, kd, ki, i_max_deg, counter_steer, hold_steer, exit_steer_angle, max_timeout_sec
  - Result: status, actual_distance, final_yaw_deg, final_error_deg, elapsed_time
  - Feedback: current_distance/remaining_distance/yaw_deg/error_deg/steer_deg/**vx (signed, 항상 ≤ 0)**, phase, w1/w2_drive_rpm
  - 의미: vx_max 는 magnitude 만 받고 내부에서 항상 -vx 적용. target_yaw_deg / current_yaw_deg 는 yaw_control 과 동일 의미(map yaw absolute).
  - effective_yaw 보정 미적용 (PathController 미사용 — IMU yaw 직접 PID 추종).
- `CMakeLists.txt` — `rosidl_generate_interfaces` 에 항목 추가, Wave 주석 갱신 (2026-04-28: YawControl Forward(기본)/Reverse 분리)

빌드 검증: `colcon build --base-paths src --packages-select trnav_2ws_interfaces` 성공.
`ros2 interface show trnav_2ws_interfaces/action/AMRMotionYawControlReverse` 노출 확인.

이슈 기록: `docs/issues_fixes/issues_and_fixes.md` ([2026-04-28 12:00] 항목)
요청: `docs/request/2026-04-28_yaw_control_reverse.md`

---

2026-04-28 / 07:31 - (pending commit) / 추가: Turn + YawControl action 2종
- `action/AMRMotionTurn.action` (T-Robot ROS2 원본 그대로 복사)
  - Goal: target_angle, turn_radius, max_linear_speed, accel_angle, hold_steer, exit_steer_angle (float32)
  - Result/Feedback: 원본 그대로
- `action/AMRMotionYawControl.action` (ROS1 개념 + bicycle + 거리 종료, 신규 정의 — ROS2 원본 폐기)
  - Goal: target_yaw_deg, target_distance, vx_max, acceleration, max_steer_deg, kp, kd, ki, i_max_deg,
    **counter_steer (bool)**, hold_steer, exit_steer_angle, max_timeout_sec (float64)
    ※ 필드명 소문자 — rosidl 규칙 (`^[a-z][a-z0-9_]*$`)
  - Result: status, actual_distance, final_yaw_deg, final_error_deg, elapsed_time
  - Feedback: current_distance/remaining_distance/yaw_deg/error_deg/steer_deg/vx, phase, w1/w2_drive_rpm
- `CMakeLists.txt` — `rosidl_generate_interfaces` 에 두 항목 추가, Wave 주석 갱신 (2026-04-28: Turn 원본 이식 + YawControl 신규 설계)

빌드 검증: `colcon build --packages-select trnav_2ws_interfaces` 성공 (no stderr).
`ros2 interface list | grep AMRMotion(Turn|YawControl)` 노출 확인.

이슈 기록: `docs/issues_fixes/issues_and_fixes.md` ([2026-04-28 07:31] 항목)
계획: `docs/plan/2026-04-27_turn_yawcontrol_port.md`
요청: `docs/request/2026-04-28_turn_yawcontrol_port.md`

---

2026-04-24 / 08:30 - (pending commit) / 추가: Translate Wave 3 — AMRMotionTranslate action 추가
- `action/AMRMotionTranslate.action` (T-AMR 원본 그대로 복사)
  - Goal: start_x/y, end_x/y, max_linear_speed, acceleration, hold_steer, exit_steer_angle,
    exit_speed, entry_speed, has_next, control_mode (상수 CTRL_DEFAULT/CTRL_MODE_A/B/C)
  - Result: status, actual_distance, final_lateral_error, final_heading_error, elapsed_time
  - Feedback: current_distance/lateral_error/heading_error/vx/vy/omega, phase, w1/w2_drive_rpm
- `CMakeLists.txt` — `rosidl_generate_interfaces` 에 AMRMotionTranslate 추가,
  Wave 주석 갱신 (Wave 1 Spin → Wave 1+3 Spin+Translate)

빌드 검증: `colcon build --packages-select trnav_2ws_interfaces` 성공 (27.2s, 경고 없음).
`ros2 interface show trnav_2ws_interfaces/action/AMRMotionTranslate` 로 타입 생성 확인.

---

2026-04-23 / 18:06 - (pending commit) / 추가: Wave 1 이식
- `action/AMRMotionSpin.action` (T-AMR 원본 복사)
- `srv/AMRControlStop.srv` (T-AMR 원본 복사)
- `package.xml` (원본 그대로, `<name>trnav_2ws_interfaces</name>`)
- `CMakeLists.txt` (원본에서 Turn/Translate/Crab/YawControl/PurePursuit 제외, Spin + ControlStop 만 활성)
- `docs/trnav_2ws_interfaces_code_updates.md` 초기 기록

결정 배경: `docs/request/2026-04-23_trnav_2ws_interfaces_porting.md` (Wave 별 점진 이식, Wave 1 = Spin)
트리거: `docs/request/2026-04-23_imu_driver_porting.md` 후속 — Spin 통합 실행을 위한 선행 조건 충족
