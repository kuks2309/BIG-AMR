# trnav_motion_core — code updates

2026-07-04 / 09:52 - (pending) / **문구 갱신** (코드 무변경) — AD-012 개정 반영

- 수정 `package.xml` description + `CMakeLists.txt` 주석 — "kinematics 는 trnav_qd_kinematics / trnav_dd_kinematics (src/Control/Kinematics/)" 로 위치 서술 갱신

2026-05-21 / 22:30 - (pending commit) / **삭제** (ADR-012 QD/DD 분리): 5 cpp + 6 hpp 를 `trnav_motion_qd` 패키지로 이전. core 는 platform-agnostic 만 잔존.

- 삭제 cpp (→ trnav_motion_qd): `src/inverse_kinematics.cpp`, `src/bicycle_model.cpp`, `src/path_controller.cpp`, `src/pure_pursuit_controller.cpp`, `src/wheel_set_packer.cpp`
- 삭제 hpp (→ trnav_motion_qd): `include/trnav_motion_core/inverse_kinematics.hpp`, `bicycle_model.hpp`, `path_controller.hpp`, `pure_pursuit_controller.hpp`, `wheel_set_packer.hpp`, `action_server_base.hpp` (header-only template 도 이전)
- 잔존 src: `motion_profile.cpp`, `transient_guard.cpp`, `localization_monitor.cpp` (3 library target)
- 잔존 헤더-only: `action_mutex.hpp`, `math_utils.hpp`, `recursive_moving_average.hpp`, `robot_geometry.hpp` (Platform enum + RobotGeometry struct + parsePlatform 보존 — 메타데이터로 모든 platform 공용)
- `CMakeLists.txt` 정리: `inverse_kinematics`, `bicycle_model`, `path_controller`, `pure_pursuit_controller`, `wheel_set_packer` 5 target 제거. `ament_export_targets` 갱신.
- 패키지 namespace `trnav_motion_core` 무변경. consumer 의 잔존 심볼 (`ActionMutex`, `normalizeAngle`, `RobotGeometry`, `Platform`, `parsePlatform`, `TrapezoidalProfile`, `TransientGuard`, `LocalizationMonitor`, `RecursiveMovingAverage`) 호출부 무변경.
- 빌드: `colcon build --packages-select trnav_motion_core trnav_motion_qd trnav_motion_dd trnav_motion_action_server --symlink-install` PASS (0 failures, 0 stderr).
- 관련: `docs/request/2026-05-21_qd_dd_layer_separation.md`, `docs/abstraction/architecture_decisions.md` AD-012, `docs/issues_fixes/issues_and_fixes.md` [2026-05-21 22:30]

---

2026-05-21 / 19:36 - (pending commit) / 추가: `PurePursuitController::setLookahead(double)`, `PurePursuitController::setMaxDelta(double)` — 핫스왑 setter

- `include/trnav_motion_core/pure_pursuit_controller.hpp`: 두 선언 추가 (`reset()` 다음 줄)
- `src/pure_pursuit_controller.cpp`: 구현 — `params_.lookahead_distance` / `params_.max_delta` 만 갱신, e_d_filter / path 누적상태 미변경
- 호출자: `pure_pursuit_action_server` / `pure_pursuit_reverse_action_server` 의 `add_on_set_parameters_callback`
- PathController 의 `setGains` 와 동일 정책 (50Hz 단일 thread + 콜백 thread race 무해)

---

2026-05-21 / 19:12 - (pending commit) / 추가: `PathController::setGains(Kp_h, Kd_h, K_st, K_so, max_delta_rad)` — 5 스칼라 게인 핫스왑 setter

- `include/trnav_motion_core/path_controller.hpp`: setMode 다음 줄에 선언 추가
- `src/path_controller.cpp`: 구현 — `params_` 의 5 필드만 갱신, filter buffer / path state / mode 미변경
- 동기화 정책: 50 Hz 단일 control thread 와 ROS2 콜백 thread 간 race 시 한 cycle 동안 mix 후 다음부터 일관. 게인 튜닝 한정 무해 (코멘트 명시)
- 호출자: `trnav_motion_action_server` 의 translate_forward / translate_reverse `add_on_set_parameters_callback` (별도 commit)
- crab_linear 도 PathController 사용하지만 자체 yaml/콜백 별도 — 본 작업 범위 외, 추후 동일 패턴 적용 가능
- 관련: [docs/request/2026-05-21_translate_kp_tuning.md](../../../../../docs/request/2026-05-21_translate_kp_tuning.md), [docs/issues_fixes/issues_and_fixes.md](../../../../../docs/issues_fixes/issues_and_fixes.md) [2026-05-21 19:10]

---

2026-05-19 / 00:30 - 176f2b5 / 수정: LocalizationMonitor Params.pose_qos default 2 (BEST_EFFORT) → 0 (RELIABLE) — QoS 규정 부합

이전 00:15 commit (f12a07d) 의 default `pose_qos=2` 가 CLAUDE.md "QoS 호환성" 위반 — 외부 관측 도구 default RELIABLE 과 incompatible (사용자 명시 지적 "QoS 불일치는 규정 위반").

- 수정: `include/trnav_motion_core/localization_monitor.hpp`
  - `Params.pose_qos` default `2` → `0` (RELIABLE depth=10)
  - 주석: 0=default(RELIABLE depth=10) / 1=reliable 명시(동일) / 2=BEST_EFFORT(SensorDataQoS)

publisher (`trnav_pose_publisher`) 도 동일하게 default 0 으로 변경 → DDS QoS matching 정상.

검증: rclpy 직접 측정 49.99 Hz / 251 msgs / 5.001s.

관련 mistake: `docs/claude-mistake/2026-05-18.md` [2026-05-19 00:45 KST] (QoS 규정 위반).
관련 이슈: `docs/issues_fixes/issues_and_fixes.md` [2026-05-19 00:30].

---

2026-05-19 / 00:15 - f12a07d / 재작성: LocalizationMonitor — TF lookup 폐기 + /robot_pose 토픽 구독 + atomic snapshot

사용자 정공법 결정 — robot pose 는 navigation 측 단일 publisher (`trnav_pose_publisher`) 가 `/robot_pose` 토픽 발행, 본 클래스는 구독자. 분산 TF lookup (6 action server 각자) 제거 + SSOT 통일.

- 수정: `include/trnav_motion_core/localization_monitor.hpp`
  - 제거: `tf_buffer_`, `tf_listener_`, `prev_tf_x_/y_/stamp_/valid_`, `geometry_msgs/transform_stamped.hpp` include
  - 신규 Params: `pose_topic` ("/robot_pose"), `pose_qos` (2=BEST_EFFORT default)
  - 신규 atomic snapshot: `last_x_/y_/yaw_` (double), `last_stamp_ns_` (int64_t), `pose_received_` (bool)
  - 신규 jump detection: callback thread 안 `prev_jump_x_/y_/stamp_/valid_` (mutex 보호) + atomic `jump_detected_` flag
  - 공개 API 시그니처 유지: `lookupMapToBase` 3/4-arg overload, `checkLocalizationHealth`, `getLastFailReason`, `setMaxCmdSpeed`, `setEnableWatchdog` — **6 action server 호출자 변경 0**
- 수정: `src/localization_monitor.cpp`
  - constructor: pose 구독자 생성 (QoS 분기 0/1/2)
  - `poseCallback`: quaternion→yaw 추출, jump 검사 (cmd_speed > 0.01 일 때만), atomic snapshot 갱신
  - `checkLocalizationHealth()`: pose_received_ check → jump check → stamp age check (이전 TF lookup 폐기, 토픽 stamp 사용)
  - `lookupMapToBase`: atomic snapshot 반환 (이전 `tf_buffer_->lookupTransform` 폐기)
  - `setEnableWatchdog`: off→on 전환 시 baseline reset (jump_mutex_ 안에서 prev_jump_valid_ = false)

검증: `colcon build --packages-up-to trnav_motion_action_server --symlink-install` PASS (motion_core 21.3s + 6 server 재컴파일 5min 14s).

영향:
- 6 action server (translate_forward/_reverse, pure_pursuit/_reverse, yaw_control/_reverse): 코드 변경 0 (lookupMapToBase API 호환 보존)
- 토픽 발행자 부재 시 모든 consumer health fail (의도된 단일 SSOT 동작)

관련 plan: `docs/plan/2026-05-18_robot_pose_publisher.md`.
관련 이슈: `docs/issues_fixes/issues_and_fixes.md` [2026-05-19 00:15].
관련 navigation: `src/Navigation/trnav_pose_publisher/docs/trnav_pose_publisher_code_updates.md`.

---

2026-05-18 / 22:10 - (pending commit) / 추가: LocalizationMonitor per-goal `enable_watchdog_` atomic + `setEnableWatchdog(bool)` API (B patch)

B patch: 6 action server 가 goal->enable_localization_watchdog 를 받아 execute() 진입부 에서 per-goal 로 watchdog 활성/비활성 override 할 수 있도록 새 API.

- 수정: `include/trnav_motion_core/localization_monitor.hpp`
  - Params.enable_watchdog 는 초기값 의미로 유지 + 신규 `std::atomic<bool> enable_watchdog_{true}` 멤버 (런타임 override)
  - 신규 public `void setEnableWatchdog(bool)` — off→on 전환 시 baseline reset (`prev_tf_valid_=false`, `last_fail_reason_=NONE`) 로 stale baseline false jump 방지 (Codex 리뷰 반영)
- 수정: `src/localization_monitor.cpp`
  - constructor 에서 `enable_watchdog_.store(params_.enable_watchdog)` 초기화
  - `checkLocalizationHealth()` 가 `!enable_watchdog_.load()` 검사 (기존 `!params_.enable_watchdog` 대체) — atomic 으로 setEnableWatchdog 즉시 반영

검증: `colcon build --packages-up-to trnav_motion_action_server --symlink-install` PASS (4 packages, 9min 47s).

리뷰: Codex (`/ccg`) — verdict minor-fix, 2 fix 모두 적용. Gemini API 503 retry 실패.

관련 이슈: `docs/issues_fixes/issues_and_fixes.md` [2026-05-18 22:10] B patch.
관련 action server: `src/Control/AMR-Motion/trnav_motion_action_server/docs/amr_motion_action_server_code_updates.md` [2026-05-18 22:10].

---

2026-05-18 / 21:30 - (pending commit) / 수정: LocalizationMonitor topic 의존 완전 폐기 + TF-only health + lookupMapToBase 2-overload (SSOT)

이전 step 1 (14:50 timeout TF 통일) 적용 후에도 jump 검사가 topic 기반으로 남아 실차 -5 (loc_jump) 회귀 발생. 사용자 정공법 ("위치는 TF") 완전 적용 + DRY 위반 (`checkLocalizationHealth` 안 inline TF lookup) 동시 해소.

- 수정: `include/trnav_motion_core/localization_monitor.hpp`
  - Params: `pose_topic`, `pose_qos` 필드 제거 (topic 폐기)
  - 클래스 멤버: `pose_sub_`, `loc_x_/y_/yaw_` atomic, `pose_received_`, `pose_time_mutex_`, `last_pose_time_`, `prev_loc_x_/y_/initialized_`, `position_jump_detected_` — 전부 제거
  - 신규 멤버: `prev_tf_valid_`, `prev_tf_x_/y_`, `prev_tf_stamp_` (TF 기반 jump baseline)
  - 신규 4-arg overload: `bool lookupMapToBase(double &x, double &y, double &yaw, rclcpp::Time &stamp) const`
  - 기존 3-arg: 4-arg 위임 (stamp discard) — 6 action server 호출자 호환 유지
  - `poseReceived()` accessor 제거 (topic 의존)
  - `geometry_msgs::msg::pose_with_covariance_stamped.hpp` include 제거
- 수정: `src/localization_monitor.cpp`
  - constructor: tf_buffer + tf_listener 만 초기화. pose 구독 코드 삭제
  - `poseCallback`: 전체 함수 삭제
  - `checkLocalizationHealth()`: TF SSOT 호출 (`lookupMapToBase(x, y, yaw, stamp)`) → age/jump 검사. inline `tf_buffer_->lookupTransform(...)` 제거 (DRY 적용)
  - `lookupMapToBase` 2-overload 구현: 4-arg = 실제 TF lookup, 3-arg = 4-arg 위임
  - WARN 로그 정책: 4-arg 1회 (TransformException catch) + checkLocalizationHealth 보조 context 로그 1줄 (cmd_speed)

빌드: `colcon build --packages-up-to trnav_motion_action_server --symlink-install` PASS (4 packages, 4min 11s).

영향: 6 action server (translate_forward/_reverse, pure_pursuit/_reverse, yaw_control/_reverse) 의 `poseReceived()` 사전 체크 코드 + Params `pose_topic`/`pose_qos` 사용 코드 모두 별도 제거 필요 (action_server 측 patch — `amr_motion_action_server_code_updates.md` 참조).

관련 이슈: `docs/issues_fixes/issues_and_fixes.md` [2026-05-18 21:30].
관련 mistake: `docs/claude-mistake/2026-05-18.md` [2026-05-18 20:50 KST].

---

2026-05-18 / 16:30 - (pending commit) / 추가: LocalizationMonitor HealthFailReason enum + getLastFailReason() (status code 분기용)

`checkLocalizationHealth()` fail 시 호출자 (action server) 가 fail 원인을 분간할 수 있도록 reason 노출.

- 수정: `include/trnav_motion_core/localization_monitor.hpp`
  - `enum class HealthFailReason { NONE=0, TIMEOUT=1, JUMP=2, TF_LOOKUP_FAIL=3 }` public
  - `HealthFailReason getLastFailReason() const` 공개 메서드 (atomic load)
  - `std::atomic<HealthFailReason> last_fail_reason_{HealthFailReason::NONE}` private 멤버
- 수정: `src/localization_monitor.cpp` `checkLocalizationHealth()`
  - 정지 skip path: `last_fail_reason_.store(NONE)`
  - TF stamp age > timeout: `store(TIMEOUT)` (return false)
  - TF TransformException: `store(TF_LOOKUP_FAIL)` (return false)
  - position_jump_detected_ true: `store(JUMP)` (return false)
  - 성공: `store(NONE)` (return true)

빌드: `colcon build --packages-up-to trnav_motion_action_server --symlink-install` PASS.

영향: 6 action server (translate_forward/reverse, pure_pursuit/_reverse, yaw_control/_reverse) 가 본 enum 으로 finish_abort 코드 -4/-5/-6 분기 가능 (`trnav_motion_action_server` 별도 patch).

관련 이슈: `docs/issues_fixes/issues_and_fixes.md` [2026-05-18 16:30].

---

2026-05-18 / 14:50 - (pending commit) / 수정: LocalizationMonitor.checkLocalizationHealth() TF 통일 (topic 의존 폐기)

사용자 정공법 결정 — 위치는 TF (lookupMapToBase) 로 통일. 다만 `checkLocalizationHealth()` 의 timeout 검사가 topic (`/rtabmap/localization_pose`) 의 `last_pose_time_` 의존이었음. RTAB-Map 환경별 발행 주기 (실차 1.13Hz) 와 `localization_timeout_sec=0.5s` 부적합으로 진행 중 false timeout fail 빈번.

- 수정: `src/localization_monitor.cpp` `checkLocalizationHealth()` 재작성:
  - 정지 상태 (`max_cmd_speed_ ≤ 0.01`) → 검사 자체 skip + `position_jump_detected_.store(false)` silent reset (Run 1차 stale state 해소)
  - TF `lookupTransform("map", "base_link", TimePointZero)` → `tf.header.stamp` 기반 age 계산 → `age > localization_timeout_sec` 시 fail
  - TF lookup 실패 (TransformException) → fail + WARN
  - jump 검사는 topic 기반 그대로 (안전 장치 유지, 향후 TF 기반으로 step 2 patch)
- 검증: `colcon build --packages-up-to trnav_motion_action_server` PASS

영향: motion stack 8 action server (translate_forward/reverse, spin, crab, turn, yaw_control/_reverse, pure_pursuit/_reverse) 모두 새 lib 사용 — Run 1차 시 RTAB-Map topic 발행 주기와 무관하게 TF 가 정상이면 healthy.

배경: 사용자 보고 "Run 1차 항상 -4 + Run 2차 OK" 의 회귀 root cause = RTAB-Map 1.13Hz vs 0.5s threshold 부적합. bag 분석 (`experiments/acs_run_bags/run_2026-05-18_142858`) 으로 확정.

---

2026-04-29 / HH:MM - (pending commit) / 추가: PurePursuitController 라이브러리 (nav_msgs/Path 다중 waypoint, BICYCLE 전륜)
- `include/trnav_motion_core/pure_pursuit_controller.hpp` (신규)
- `src/pure_pursuit_controller.cpp` (신규)
- API:
  - `setPath(vector<pair<double,double>>)` — waypoints (≥2) 검증 + 세그먼트 길이/누적거리 계산
  - `update(rx, ry, ryaw, dt)` → `PurePursuitOutput { e_d, e_theta, projection, remaining_x, delta_f, alpha, lookahead_x, lookahead_y, closest_seg }`
  - `validateInitialPose(rx, ry, ryaw)` — closest segment 까지 lateral offset / heading_threshold 검증
- 알고리즘:
  - closest segment 찾기 (모든 segment 점-사영 후 거리 최소)
  - lookahead point: closest segment 사영 위치에서 path 따라 `lookahead_distance` 만큼 전진 (segment 경계 이월 처리, 끝 도달 시 last waypoint)
  - base_link frame 변환 후 Form 2 직접형: `delta_f = atan2(2 * wheelbase * L_y, L_x²+L_y²)`, clamp |delta_f|≤max_delta, delta_r=0
  - `remaining_x = (last_wp - robot) · base_link_x` — 호출자 종료 판정용
- 디버그: `alpha = atan2(L_y, L_x)` 별도 1줄 계산 (출력만, steering 식 자체는 self-consistent denominator 사용)
- `e_d` 는 RMA 필터 적용 (cte_filter_window 파라미터)
- `CMakeLists.txt` — `pure_pursuit_controller` static library 추가 + install TARGETS 항목
- ROS dep 없음 (header-only math_utils + recursive_moving_average)

빌드 검증: `colcon build --base-paths src --packages-select trnav_motion_core` PASS, `libpure_pursuit_controller.a` 정상 install.

요청: `docs/request/2026-04-29_pure_pursuit_port.md`
플랜: `docs/plan/2026-04-29_pure_pursuit_implementation.md`

---

2026-04-28 / 07:31 - (pending commit) / 추가: math_utils 에 normalizeAngleDeg 추가
- `include/trnav_motion_core/math_utils.hpp`
  - 기존 `normalizeAngle(double rad) → [-π, π]` 옆에 `normalizeAngleDeg(double deg) → [-180, +180]` 신규 inline 함수 추가
  - 둘 다 `std::remainder` 기반 (NaN-safe, 무한 루프 방지)
- 사용처: `trnav_motion_action_server::yaw_control` 의 yaw error / offset 계산 (기존 익명 namespace 의 while-loop wrapPi/wrapDeg 대체)

빌드: header-only inline 추가 → core 라이브러리 재컴파일 불필요. action_server 재빌드 시 자동 반영.

이슈 기록: `docs/issues_fixes/issues_and_fixes.md` ([2026-04-28 07:31] 항목)
계획: `docs/plan/2026-04-27_turn_yawcontrol_port.md`

---

2026-04-27 / 09:50 - (pending commit) / 수정: PathController BICYCLE direction-aware (Translate Forward/Reverse 분리 Step 6)
- `include/trnav_motion_core/path_controller.hpp`
  - `enum class TravelDirection { FORWARD=0, REVERSE=1 };` 신규 (default FORWARD — 기존 호출자 비파괴)
  - `update(robot_x, robot_y, robot_yaw, vx, dt, TravelDirection dir = FORWARD)` — vx 는 magnitude (양수 강제)
  - `computeBicycle(...)` 에 `TravelDirection dir` 파라미터 추가 (private)
- `src/path_controller.cpp`
  - `computeBicycle` 안 reverse 시 `delta_heading = -delta_heading` 부호 반전 (BICYCLE omega = vx·(tan_f − tan_r)/L 식에서 vx<0 일 때 omega 부호 반전 보상)
  - `update` 가 `dir` 을 `computeBicycle` 로 전달
- forward 호출자 (amr_translate_forward_node) 는 default FORWARD → 동작 변화 없음
- reverse 호출자 (amr_translate_reverse_node) 는 REVERSE 명시 → e_theta 수렴 방향 정상화

빌드: `colcon build --packages-select trnav_motion_core` 성공 (~1.4s).
검증: `experiments/2026-04-27_translate_reverse_split_sil/` reverse 4 시나리오 PASS, forward SIL 회귀 status=0/dist=1.000/lat=0.0/hdg=0.0°.

---

2026-04-24 / 08:05 - (pending commit) / 추가: Translate Wave 2 — PathController(BICYCLE) + TransientGuard + LocalizationMonitor
- `include/trnav_motion_core/recursive_moving_average.hpp` (header-only, 원본 포팅)
- `include/trnav_motion_core/path_controller.hpp` + `src/path_controller.cpp`
  - BICYCLE 모드만 지원. enum `ControlMode::BICYCLE=1` 만 선언.
  - 미사용 모드/필드 제거 (cte_phase_, splitAntiParallel, computeVyOmega/PureStanley/SequentialCTE/FrontStanley 및 관련 Params).
  - 후속 Wave 에서 Mode 2+ 추가 시 enum · Params · computeXXX 함수 확장 예정.
- `include/trnav_motion_core/transient_guard.hpp` + `src/transient_guard.cpp` (원본 그대로 포팅, namespace 교체)
- `include/trnav_motion_core/localization_monitor.hpp` + `src/localization_monitor.cpp`
  (원본 그대로 포팅, namespace 교체, `geometry_msgs`/`tf2_ros` 의존 신규)
- `CMakeLists.txt` — STATIC 라이브러리 3개 신규 추가 (`path_controller`, `transient_guard`, `localization_monitor`).
  `find_package(geometry_msgs REQUIRED)`, `find_package(tf2_ros REQUIRED)`, `ament_export_dependencies` 에 추가.
- `package.xml` — `geometry_msgs`, `tf2_ros` depend 추가.

빌드 검증: `colcon build --packages-select trnav_motion_core` 성공 (12.0s, 경고 없음).
설치 산출물: `libpath_controller.a`, `libtransient_guard.a`, `liblocalization_monitor.a`.

참조 원본: 원본 패키지 동명 파일들 (`path_controller.{hpp,cpp}`, `transient_guard.{hpp,cpp}`, `localization_monitor.{hpp,cpp}`, `recursive_moving_average.hpp`)

---

2026-04-24 / 07:40 - 76a4bf0 / 추가: Translate Wave 1 — BicycleModel 이식
- `include/trnav_motion_core/bicycle_model.hpp` (원본 `amr_motion_control::BicycleModel` 포팅, namespace·include guard 교체, 로직 동일)
- `src/bicycle_model.cpp` (원본 로직 그대로, include 경로만 `trnav_motion_core/bicycle_model.hpp` 로 교체)
- `CMakeLists.txt` — STATIC 라이브러리 `bicycle_model` 추가, `inverse_kinematics` PUBLIC 링크, install TARGETS 에 포함
- `docs/trnav_motion_core_code_updates.md` 초기 생성

빌드 검증: `colcon build --packages-select trnav_motion_core` 성공 (1.9s, 경고 없음, `libbicycle_model.a` 설치).

참조 원본: `/home/tc/T-Robot_nav_ros2_ws/src/Control/AMR-Motion-Control/amr_motion_control/src/bicycle_model.cpp`
계획: `docs/plan/2026-04-24_amr_translate_port.md`
결정 기록: `docs/request/2026-04-24_amr_translate_port.md`
