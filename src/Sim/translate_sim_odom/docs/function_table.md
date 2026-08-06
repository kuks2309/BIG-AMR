# translate_sim_odom — 함수표 · 변수표 (모듈 로컬 권위본)

> 양식 권위는 `docs/claude_guideline/code_review/review.md` §Core 인벤토리 3·4.
> 이중 기록 — 루트 집계는 `docs/sw_structure/function_table.md`.
> 생성 사유: 2026-08-06 coding SOP §2 위반 소급 이행
> ([실수 기록 2026-08-06-003](../../../../docs/claude-mistake/2026-08-06-003_coding-sop-skipped-tables-adr-selfapprove.md)).
> 이 표가 있어야 `coding/hooks/coding-inventory-gate.py` 가 이 모듈 수정 시 선독을 강제한다
> (표 부재 시 게이트는 무조건 통과 — `coding.md:53`).

## 목적

폐쇄 루프 SIL(Software In the Loop) 플랜트. `/motor/wheel_cmd`(휠별 속도·조향)를 받아
2륜 정기구학으로 차체 속도를 풀고 Euler 적분해 TF·pose·IMU(Inertial Measurement Unit)·
휠 상태를 낸다. QD·2WS 의 SIL/HIL(Hardware In the Loop) 런치 **19개가 공유**하며 그중
**8개가 검증 완료된 QD 런치**다 — 기본 거동을 바꾸면 그 검증이 무효가 된다.

## 함수 리스트 표

| # | 함수 | 입력 | 출력 | 기능 | 위치(file:line) |
| --- | --- | --- | --- | --- | --- |
| 1 | `main` | `argc`, `argv` | `int` 종료코드 | 노드 생성·spin·shutdown | `src/main.cpp:5` |
| 2 | `TranslateSimOdomNode.TranslateSimOdomNode` | 없음(생성자) | — | 파라미터 선언(기하·초기자세·**동특성**·**엔코더 환산**·IMU 잡음), 구독/발행자·TF 브로드캐스터·적분 타이머 생성, 동특성 활성 여부 로그 | `src/translate_sim_odom_node.cpp:11` |
| 3 | `TranslateSimOdomNode.wheelCmdCallback` | `WheelSetArray::SharedPtr` | `void` | 최신 휠 지령(`cmd_v0_`·`cmd_s0_`·`cmd_v1_`·`cmd_s1_`)을 뮤텍스 아래 갱신. 휠 2개 미만이면 throttle 경고 후 무시 | `src/translate_sim_odom_node.cpp:92` |
| 4 | `TranslateSimOdomNode.integrateAndPublish` | 없음(타이머) | `void` | dt 산출 → 동특성 적용 → **실제값**으로 정기구학 → Euler 적분 → 휠 주행거리 누적 → TF·pose·IMU·휠상태·**엔코더 상세** 발행 | `src/translate_sim_odom_node.cpp:108` |
| 4a | `integrateAndPublish.slew_vel` | `actual`, `target`, `step_dt` | `double` 갱신 속도 | 구동 가감속 한계 적용. 크기가 줄어드는 방향(부호 반전 포함)이면 감속 한계, 늘어나면 가속 한계. 한계 0 이면 target 즉시 반환(종전 즉응) | `src/translate_sim_odom_node.cpp:145` |
| 4b | `integrateAndPublish.slew_ang` | `actual`, `target`, `step_dt` | `double` 갱신 각 | 조향 슬루율 제한. 조향축은 ±115° **비순환** 축이라 최단경로 보정 없이 선형 이동 | `src/translate_sim_odom_node.cpp:156` |

**중복/유사 함수**: 없음. `slew_vel`/`slew_ang` 는 한계 종류(가감속 2종 vs 슬루 1종)와
분기 규칙이 달라 통합 시 조건이 늘어난다 — 분리 유지가 타당.

## 전역 변수 / 모듈 상수 표

**파일 스코프 전역 변수·모듈 상수 없음** (`static`·파일 스코프 `const` 0건, 네임스페이스
선언만 존재 — `src/translate_sim_odom_node.cpp:8`). 상태는 전부 클래스 멤버다.

## 클래스 멤버 상태 표

| # | 멤버 | 사용처(함수) | 기능 | 위치(file:line) |
| --- | --- | --- | --- | --- |
| 1 | `w1_x_`·`w1_y_`·`w2_x_`·`w2_y_` (가변, 기동 후 불변) | 4 | 휠 좌표. 정기구학의 ω 분모 선택(x 간격 vs y 간격)에 쓰임 | `include/…_node.hpp:54-57` |
| 2 | `initial_x_`·`initial_y_`·`initial_yaw_` (가변, 기동 후 불변) | 2 | 초기 자세 | `include/…_node.hpp:60-62` |
| 3 | `imu_yaw_offset_rad_` (가변, 기동 후 불변) | 2, 4 | IMU 자체 yaw 0 과 map yaw 0 의 어긋남 모사(S7 calibration) | `include/…_node.hpp:69` |
| 4 | `x_`·`y_`·`yaw_` (가변, `std::atomic`) | 2, 4 | 적분된 지상진값 자세 | `include/…_node.hpp:72-74` |
| 5 | `cmd_mtx_` | 3, 4 | 지령 4필드 보호 | `include/…_node.hpp:77` |
| 6 | `cmd_v0_`·`cmd_s0_`·`cmd_v1_`·`cmd_s1_`·`cmd_received_` (가변) | 3, 4 | 최신 휠 지령 | `include/…_node.hpp:78-82` |
| 7 | `drive_accel_mps2_`·`drive_decel_mps2_`·`steer_rate_rad_s_` (가변, 기동 후 불변) | 2, 4a, 4b | **동특성 한계. 기본 0 = 제한 없음 = 종전 즉응 거동** — 공유 런치 19개의 기존 결과 보존 | `include/…_node.hpp:91-93` |
| 8 | `act_v0_`·`act_s0_`·`act_v1_`·`act_s1_` (가변) | 4 | 동특성 적용 **후** 실제값. 정기구학은 지령이 아니라 이 값으로 푼다 | `include/…_node.hpp:96-99` |
| 9 | `travel0_m_`·`travel1_m_` (가변) | 4 | 휠 누적 주행거리(m). 엔코더 counts 의 원천 — **관성 구간 이동도 포함** | `include/…_node.hpp:102-103` |
| 10 | `wheel_radius_`·`pulses_per_rev_`·`gear_walk_`·`gear_steer_` (가변, 기동 후 불변) | 2, 4 | 엔코더 환산 상수. translator YAML 과 같은 값을 써야 한다 | `include/…_node.hpp:104-107` |
| 11 | `imu_yaw_noise_rad_`·`noise_rng_`·`noise_dist_` (가변) | 2, 4 | 발행 yaw 에만 실리는 잡음. 지상진값(TF·pose) 불변. **고정 시드**라 같은 설정이면 같은 수열 | `include/…_node.hpp:111-113` |
| 12 | `wheel_cmd_sub_`·`loc_pose_pub_`·`imu_pub_`·`wheel_state_pub_`·`wheel_state_detailed_pub_`·`tf_broadcaster_` | 2, 4 | 통신 핸들 | `include/…_node.hpp:116-121` |
| 13 | `integrate_timer_`·`integrate_rate_hz_`·`last_integrate_time_`·`first_step_` (가변) | 2, 4 | 적분 주기·dt 산출 상태 | `include/…_node.hpp:124-127` |

**전역 필요성 평가**: 전부 노드 인스턴스 상태로 클래스 멤버가 적절하다. 모듈 전역으로
올릴 대상 없음. ⚠ `#8 act_*` 는 타이머 스레드에서만 접근하므로 원자성 불요이나,
향후 다른 스레드에서 읽게 되면 `#4` 와 같이 `std::atomic` 이 필요하다.

## 공개 인터페이스 (ROS)

| 종류 | 이름 | 타입 | 비고 |
| --- | --- | --- | --- |
| 구독 | `/motor/wheel_cmd` | `trnav_msgs/WheelSetArray` | RELIABLE |
| 발행 | `/rtabmap/localization_pose` | `PoseWithCovarianceStamped` | SensorDataQoS |
| 발행 | `/imu/data` | `sensor_msgs/Imu` | SensorDataQoS |
| 발행 | `/wheel_motor_state` | `trnav_msgs/WheelMotor` | **실제값**(2026-08-06 이전에는 지령 되울림) |
| 발행 | **`/wheel_motor_state_detailed`** | `trnav_msgs/WheelMotorState` | **2026-08-06 신설** — 엔코더 counts |
| 발행 | TF `map`→`base_link` | — | |
| 파라미터 | `w1_x`·`w1_y`·`w2_x`·`w2_y`·`initial_*`·`integrate_rate_hz`·`imu_yaw_offset_deg` | — | 기존 |
| 파라미터 | **`drive_accel_mps2`·`drive_decel_mps2`·`steer_rate_dps`·`wheel_radius`·`pulses_per_rev`·`gear_walk`·`gear_steer`·`imu_yaw_noise_deg`** | — | **2026-08-06 신설** — 전부 기본 0 또는 translator 동일값 |

## 의존성 3-tier

| Tier | 대상 | 버전/제약 | 부재 시 동작 | 근거(파일:line) |
| --- | --- | --- | --- | --- |
| 빌드 | `rclcpp`·`trnav_msgs`·`geometry_msgs`·`sensor_msgs`·`tf2`·`tf2_ros`·`tf2_geometry_msgs` | ROS 2 Humble | 빌드 실패 | `package.xml` |
| 런타임 필수 | `/motor/wheel_cmd` 발행자(통상 `trnav_motion_mux`) | — | **지령 미수신 → `received=false` → 속도 0, 자세 정지**(오류 아님) | `src/…_node.cpp:135-141` |
| 런타임 선택 | 없음 | — | — | — |

## 검증

| 항목 | 도구 | 결과 |
| --- | --- | --- |
| 동특성 OFF = 종전 거동 | `Tools/motion_chain_check/plant_dynamics_check.py` | 정지 0.020 s · 감속 중 중간 속도값 **0개** |
| 동특성 ON = 실측 재현 | 동상 | 정지 0.620 s(실측 0.57~0.65 s 구간 내) · 엔코더 +15.5 mm(v²/2a = 15.0 mm) |
| 엔코더 발행 | 동상 | 두 모드 모두 수신 |
| 환산식 | `--selftest` | 5/5 |

⚠ **최종 verdict 는 저자가 찍지 않는다**(`coding.md:88` never-self-approve). 위는 실행
관측 기록이며 승인이 아니다 — 외부 리뷰 패스 필요.
