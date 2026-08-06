# trnav_2ws_action_server / turn — 함수표 · 변수표 (모듈 로컬 권위본)

> 양식 권위는 `docs/claude_guideline/code_review/review.md` §Core 인벤토리 3·4.
> 이중 기록 — 루트 집계는 `docs/sw_structure/function_table.md`.
> 생성 사유: 2026-08-06 coding SOP §2 위반 소급 이행
> ([실수 기록 2026-08-06-003](../../../../../docs/claude-mistake/2026-08-06-003_coding-sop-skipped-tables-adr-selfapprove.md)).
>
> **범위 한정** — 본 표는 2026-08-06 에 수정한 `turn` 액션만 담는다. 같은 패키지의 나머지
> 8개 액션(`translate_forward`·`translate_reverse`·`mpc`·`mpc_reverse`·`spin`·`crab_linear`·
> `yaw_control`·`yaw_control_reverse`)은 **미작성**이므로 그 파일들에 대해서는
> `coding-inventory-gate.py` 가 여전히 빈 통과한다. 등재는 별도 작업.

## 목적

R-turn(반경 R > 0 의 원호 주행) 액션 서버. 목표 각도까지 사다리꼴 각속도 프로파일로
회전하고, 잔여 각오차를 보정한 뒤 조향을 복귀시킨다. 각도 진행량은 IMU(Inertial
Measurement Unit) yaw 델타 누적으로 측정한다.

플랫폼은 inline dual-steer(2WS) — 전·후륜이 대칭 ±δ 로 꺾여 ICR(Instantaneous Center of
Rotation)이 **차체 중심**에 선다. R=1.0 m 에서 전륜 +31.13°/후륜 −30.80°.

## 함수 리스트 표

| # | 함수 | 입력 | 출력 | 기능 | 위치(file:line) |
| --- | --- | --- | --- | --- | --- |
| 1 | `TurnActionServer.TurnActionServer` | `node`, `action_mutex` | — | 베이스 초기화, `turn_params.yaml` 파라미터 로드(IMU 데드밴드·최소속도·미세보정 3종·정착지연) | `src/turn/turn_action_server.cpp:11` |
| 2 | `TurnActionServer.validateGoal` | `Turn::Goal` | `bool` | `turn_radius > 0`·`max_linear_speed > 0`·`accel_angle > 0` 검사. 위반 시 거부 | `src/turn/turn_action_server.cpp:31` |
| 3 | `TurnActionServer.execute` | `GoalHandle` | `void` | Phase 0 조향정렬 → Phase 1-3 사다리꼴 프로파일 → 정착 → Phase 3.5 미세보정 → 정지 → Phase 4 조향복귀 | `src/turn/turn_action_server.cpp:63` |

베이스 클래스(`trnav_2ws_motion/qd_action_server_base.hpp`)의 `publishWheelCmd`·
`guardSteer`·`wheelStateCallback`·`imuCallback` 등은 **별도 모듈**이므로 그 모듈의
표에 등재한다(현재 미작성).

**중복/유사 함수**: 없음(파일 내 함수 3개).

## execute 내부 단계 (플로우)

| 단계 | 조향 | 구동 | 위치 |
| --- | --- | --- | --- |
| Phase 0 조향정렬 | 원호각으로 이동, 도달 대기(타임아웃 `steer_timeout_sec`) | 0 | `:125-` |
| Phase 1-3 프로파일 | 원호각 유지 | 사다리꼴 ω, `min_speed_dps` 하한 | `:186-263` |
| 정착 | 원호각 유지 | 0, `settling_delay_ms` 대기 | `:265-292` |
| Phase 3.5 미세보정 | **원호각 유지**(2026-08-06 변경) | 저속으로 원호 계속/되돌림 | `:294-379` |
| 정지 | **원호각 유지**(2026-08-06 변경) | 0 | `:381-385` |
| Phase 4 조향복귀 | `exit_steer_angle` 로 이동(`hold_steer` 면 생략) | 0 | `:388-` |

⚠ **2026-08-06 변경 전**에는 Phase 3.5 와 정지 단계가 `computeSpin` 으로 **±90° 스핀
자세**를 실었다. 정지 단계는 미세보정 `if` **밖**이라 보정이 발동하지 않아도 매 turn 마다
실행됐다. 돌연변이 확인 결과 그 한 블록만 되돌리면 조향 최대가 31.13°/30.80° →
**90.00°/90.00°** 로 되돌아온다(결과각·소요시간 동일).

## 전역 변수 / 모듈 상수 표

**파일 스코프 전역 변수·모듈 상수 없음** (`static`·파일 스코프 `const` 0건).

## 클래스 멤버 상태 표

| # | 멤버 | 사용처(함수) | 기능 | 위치(file:line) |
| --- | --- | --- | --- | --- |
| 1 | `motion_source_id_` (가변, 기동 후 불변) | 1, 3 | mux 소스 id = 5. 액션이 스스로 `/select_motion_source` 호출 | `include/…/turn_action_server.hpp:30` |
| 2 | `imu_deadband_rad_` (가변, 기동 후 불변) | 3 | yaw 델타 잡음 임계. **스킵 시 `prev_yaw` 를 갱신하지 않으므로 각이 소실되지 않고 이월된다**(최종 미계상 ≤ 임계) | `include/…/turn_action_server.hpp:33` |
| 3 | `min_speed_dps_` (가변, 기동 후 불변) | 3 | 감속 구간 각속도 하한 | `include/…/turn_action_server.hpp:34` |
| 4 | `fine_correction_threshold_deg_` (가변, 기동 후 불변) | 3 | Phase 3.5 진입 임계(0.3°) | `include/…/turn_action_server.hpp:35` |
| 5 | `fine_correction_speed_dps_` (가변, 기동 후 불변) | 3 | 보정 각속도(3.0 deg/s) | `include/…/turn_action_server.hpp:36` |
| 6 | `fine_correction_timeout_sec_` (가변, 기동 후 불변) | 3 | 보정 타임아웃(3.0 s) | `include/…/turn_action_server.hpp:37` |
| 7 | `settling_delay_ms_` (가변, 기동 후 불변) | 3 | 프로파일 종료 후 정착 대기(200 ms) | `include/…/turn_action_server.hpp:38` |

**전역 필요성 평가**: 전부 파라미터 캐시로 클래스 멤버가 적절.

## 알려진 미해결 사항 (등재만 — 판단은 code_review 소관)

| 항목 | 내용 | 상태 |
| --- | --- | --- |
| A | `:233` 주 루프가 `accumulated_angle += std::abs(delta_yaw)` 로 **방향을 보지 않는다**(정착 `:282`·보정 `:355` 는 부호 판정 있음) | **QD 상류와 글자 그대로 동일**. QD 는 실기 검증됨 → 사용자 지시 「QD 와 동일하게」에 따라 미변경. 해로운지는 미측정 |
| B | `settling_delay_ms: 200` 이 드라이브 관성(실측 0.57~0.65 s)보다 짧아 **기체가 멈추기 전에 잔여각을 읽는다** | 미조치. 동특성 켠 SIL 로 측정 후 판단 |
| C | 보정 속도 3.0 deg/s × 관성 0.6 s ≈ **1.8° 오버슛** vs 임계 0.3° — 수렴 불가 구조 | 미조치. B 와 함께 판단 |
| D | 액션이 엔코더(`/wheel_motor_state_detailed`)를 읽지 않고 IMU yaw 만 쓴다 | **QD 도 동일(참조 0건)** → 「QD 와 동일하게」에 따라 미변경 |

## 의존성 3-tier

| Tier | 대상 | 버전/제약 | 부재 시 동작 | 근거(파일:line) |
| --- | --- | --- | --- | --- |
| 빌드 | `rclcpp`·`rclcpp_action`·`trnav_2ws_interfaces`·`trnav_2ws_core`·`trnav_2ws_motion`·`trnav_2ws_kinematics` | ROS 2 Humble | 빌드 실패 | `package.xml` |
| 런타임 필수 | `/imu/data` | `sensor_msgs/Imu` | **yaw 갱신 없음 → `accumulated_angle` 정체 → 프로파일 미완료로 지속 회전** | `qd_action_server_base.hpp:85` |
| 런타임 필수 | `trnav_motion_mux` (`/select_motion_source`) | — | 소스 선택 실패 시 지령이 하류로 안 나감 | `qd_action_server_base.hpp` |
| 런타임 선택 | `wheel_motor_state` | `trnav_msgs/WheelMotor` | 미수신 시 `last_angle_*_` 이 갱신 안 됨 → Phase 0/4 도달판정이 타임아웃으로 종료 | `qd_action_server_base.hpp:78` |

## 검증

| 항목 | 방법 | 결과 |
| --- | --- | --- |
| 빌드 | `colcon build --packages-select trnav_2ws_action_server` | 통과 |
| 기능 | SIL 목표 45° · R=1.0 m (`ROS_DOMAIN_ID=43`) | status 0 · actual_angle 45.178° · 7.40 s |
| 조향 범위 | `Tools/motion_chain_check/sil_record_steer.py` | W1 +0.00~+31.13° · W2 −30.80~+0.00° · 90° 초과 0표본 |
| **돌연변이** | `:381` 정지 블록만 종전 복원 후 재실행 | 조향 최대 **90.00°/90.00°** 로 회귀 → 원인 확정 |

⚠ **최종 verdict 는 저자가 찍지 않는다**(`coding.md:88`). 위는 실행 관측 기록이며
승인이 아니다 — 외부 리뷰 패스 필요.
