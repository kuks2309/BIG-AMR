# trnav_2ws_interfaces — code updates

2026-08-13 / 04:21 - (pending) / **주석 라인 단위 재독 — 남은 모순 정정 + 주석에서 이력 제거** (코드 무변경)

- 규약 확정: **코드 주석에는 이력을 넣지 않는다.** 주석은 코드가 지금 무엇을 하는지만 적고,
  「무엇을 언제 왜 바꿨나」는 본 문서(code updates)가 보유한다. 직전 커밋 `6fb9663` 이 주석에
  변경 이력·감사 서술(「종전 …이었다」·「…교체됐고」·「…정정해 해소했다」·「(YYYY-MM-DD 확인)」·
  「… 는 이 저장소에 없다」)을 섞어 넣었던 것을 이번에 전량 걷어냈다.
- 범위: 2WS 스택 **16,174줄 전량**을 12 슬라이스로 나눠 라인 단위 재독.
  슬라이스마다 적대적 반박 2인(원문 변호 / 대체문 감사)이 코드로 재검증.
  86후보 → **69 적용**(모순 정정 47 + 이력 제거 22) / **17 기각**(변호 성립으로 원상 유지).
- 코드 무변경 증명: 변경 45파일을 언어별 파서로 대조 — C++ 16개 `gcc -fpreprocessed -E -P` 출력 동일,
  Python 13개 AST(Abstract Syntax Tree) 동일(모듈 docstring 제외), YAML/`.action`/CMake 13개
  `#` 주석 제거 후 동일, `package.xml` 3개 `<description>` 제외 XML 동일. **차이 0건.**
  이력 문구 잔존 스캔(`종전|정정해|해소했|교체됐|이 저장소에 없다|확인\)|not present in this repository`) **0건**.
- 검증: `colcon build --packages-up-to trnav_2ws_action_server …` 6패키지 PASS(0 error) ·
  `colcon test --packages-select trnav_2ws_core trnav_2ws_kinematics` 67 tests / 0 failures / 0 errors.
- 기각 사례(재발 방지용 기록) — 지적이 틀렸던 것들:
  · `amr_dock_align` 은 패키지가 아니라 **노드(실행파일) 이름**이라 「부재 패키지」 지적이 오독이었다.
  · turn 의 `R > 1.44 m`(v=0.05 기준 ω_max < 하한 2.0 dps)를 `1.43` 으로 「정밀화」하려 했으나
    R=1.431 m 에서 ω_max=2.0019 dps 라 **거짓이 된다** — 원문이 옳다.
  · `−dir × delta_heading` 은 죽은 표기가 아니라 QD 형제 코드(`trnav_qd_kinematics`)에 살아 있는
    grep 앵커이자 미결 쟁점의 참조점이라 토큰을 보존했다.
  · `분산 TF lookup 폐기`·`src/Control/Kinematics/` 언급은 이력이 아니라 **설계 근거·범위 제약**이라 유지.
- 수정 `action/AMRMotionTranslateForward.action`·`TranslateReverse`·`CrabLinear` — `final_lateral_error` /
  `current_lateral_error` 의 부호 규약 `+ left, - right` → **`+ robot right of path, - robot left of path`**.
  값은 `TwoWsPathController` 의 `e_d`(`rx*uy_ - ry*ux_`)라 경로 진행방향 기준 우측이 양수다.
- 수정 `action/AMRMotionTranslateReverse.action`·`AMRMotionMpc.action` — `control_mode` 서술 정정.
  서버는 0·1 만 수락하고 둘 다 BICYCLE 로 고정하며, 존재하지 않는 모드 2·3 을 선택지처럼 적고 있었다.
  `0=node param default` 도 사실이 아니다(읽고 버리거나 대응 param 자체가 없다).
- 수정 `action/AMRMotionMpc.action` — `enable_localization_watchdog` 의 짝 node param 이름
  `translate_enable_localization_watchdog` → `mpc_enable_localization_watchdog`(전자는 이 액션에 없다).
  「Reverse 방향은 후속 wave 에서 분리」는 이미 분리 완료라 실제 액션명으로 교체.
- 수정 `action/AMRMotionCrabLinear.action`·`Mpc`·`MpcReverse` — `has_next` 를 미사용 필드로 명시
  (서버가 읽지 않는다 — 속도 연속 종료는 `exit_speed>0`).

---

2026-08-11 / 22:37 - (pending) / **주석 감사 — 코드와 모순되는 주석 일괄 정정** (코드 무변경)

- 범위: 2WS 스택 전체(~15,400줄). **주석·docstring·`<description>` 만 수정, 실행 코드는 한 줄도 바꾸지 않았다.**
- 방법: 10인 독립 리더가 슬라이스별로 후보를 내고 슬라이스마다 적대적 반박 2인(원문 변호 / 대체문 감사)이
  코드로 재검증. 1차 82후보 → 반박 통과 79 + 저자 판정 3 = 82 적용. 2차(죽은 참조·inline↔대각 잔재·
  1차 0건 파일 전수 재독) 39후보 → 29 적용, 9 기각(변호인 반박 성립), 1 중복.
- 코드 무변경 증명: 변경 63파일 전부를 언어별 파서로 대조 — C++ 28개 `gcc -fpreprocessed -E -P` 출력 동일,
  Python 13개 AST(Abstract Syntax Tree) 동일(모듈 docstring 제외), YAML/`.action`/CMake 19개 `#` 주석 제거 후 동일,
  `package.xml` 3개 `<description>` 제외 XML 동일. **차이 0건.**
- 검증: `colcon build --packages-up-to trnav_2ws_action_server …` 6패키지 PASS(0 error) ·
  `colcon test` 67 tests / 0 failures / 0 errors.
- 기각 사례(기록): 상류 설계문서 인용(`AMR_Motion_Control_Implementation_Plan.md` §1.6.2,
  `Implementation Plan §5.4.3`, `trnav_motion_mux_architecture.md`, `dual_steer_engine.py … lines N-M`,
  `ADR-012`)을 「죽은 참조」로 고치려던 5건은 **반박당해 원상 유지**했다 — 저장소 상대경로가 아니라
  이식물의 정상적인 출처 표기이고, 「고치면」 오히려 이 저장소에서 확인되지 않는 상류 소재를
  새로 심게 된다. `Platform::QD_DIAGONAL` enum 정의 주석 계열 4건도 taxonomy 서술이라 기각.
- 수정 `action/AMRMotionMpcReverse.action`·`AMRMotionMpc.action` — 헤더가 자기 이름·경로를 폐기된
  `AMRMotionPurePursuit(Reverse)` 로, 컨트롤러를 `PurePursuitController` 로 적고 있었다 → 실제 이름·`TwoWsMpcController`.
- 수정 `action/AMRMotionCrabLinear.action` — 매 cycle 계산 서술이 서버 동작과 달랐다(`omega_cmd → VelocityCommand →
  DualSteerIK`) → 실제 `delta_cte`/`delta_heading` → `TwoWsCrabIK.compute`(omega 지령 없음); status -2 코드명 정정.
- 수정 `action/AMRMotionTranslateForward.action`·`TranslateReverse` — `has_next # true=다음 Segment 존재 → 감속 안 함`
  → 서버가 읽지 않는 미사용 필드임을 명시(속도 연속은 `exit_speed>0` 로 지정).
- 수정 `action/AMRMotionYawControl.action`·`YawControlReverse` — 형제 복사 잔재 및 값 불일치 정정.

---

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
