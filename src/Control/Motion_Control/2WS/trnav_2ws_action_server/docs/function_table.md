# trnav_2ws_action_server / turn · turn_reverse — 함수표 · 변수표 (모듈 로컬 권위본)

> 양식 권위는 `docs/claude_guideline/code_review/review.md` §Core 인벤토리 3·4.
> 이중 기록 — 루트 집계는 `docs/sw_structure/function_table.md`.
> 생성 사유: 2026-08-06 coding SOP §2 위반 소급 이행
> ([실수 기록 2026-08-06-003](../../../../../docs/claude-mistake/2026-08-06-003_coding-sop-skipped-tables-adr-selfapprove.md)).
>
> **범위 한정** — 본 표는 `turn`(2026-08-06 수정)과 `turn_reverse`(2026-08-09 신설)를 담는다.
> 같은 패키지의 나머지 8개 액션(`translate_forward`·`translate_reverse`·`mpc`·`mpc_reverse`·
> `spin`·`crab_linear`·`yaw_control`·`yaw_control_reverse`)은 **미작성**이므로 그 파일들에
> 대해서는 `coding-inventory-gate.py` 가 여전히 빈 통과한다. 등재는 별도 작업.

## 목적

R-turn(반경 R > 0 의 원호 주행) 액션 서버. 목표 각도까지 사다리꼴 각속도 프로파일로
회전하고, 잔여 각오차를 보정한 뒤 조향을 복귀시킨다. 각도 진행량은 IMU(Inertial
Measurement Unit) yaw 델타 누적으로 측정한다.

플랫폼은 inline dual-steer(2WS) — 전·후륜이 대칭 ±δ 로 꺾여 ICR(Instantaneous Center of
Rotation)이 **차체 중심**에 선다. R=1.0 m 에서 전륜 +31.13°/후륜 −30.80°.

## 함수 리스트 표

| # | 함수 | 입력 | 출력 | 기능 | 위치(file:line) |
| --- | --- | --- | --- | --- | --- |
| 1 | `TurnActionServer.TurnActionServer` | `node`, `action_mutex` | — | 베이스 초기화, `turn_params.yaml` 로드(coarse 하한·정착 tol·`pid_band_deg`·`kp_turn`·`kd_turn`·정착 게이트 2종·`start_yaw_avg_samples`) | `src/turn/turn_action_server.cpp:11` |
| 2 | `TurnActionServer.validateGoal` | `Turn::Goal` | `bool` | `turn_radius > 0`·`max_linear_speed > 0`·`accel_angle > 0` 검사. 위반 시 거부 | `src/turn/turn_action_server.cpp:31` |
| 3 | `TurnActionServer.execute` | `GoalHandle` | `void` | Phase 0 조향정렬 → **start_yaw 원형평균(절대 기준 확립)** → Stage 1 사다리꼴 coarse(진행량 = target−\|e\|) → \|e\|≤`pid_band` 인계 → **Stage 2 PD fine(오차 피드백)** + 정착 게이트 → Phase 4 조향복귀. 2026-08-09 구조 변경(ADR `2026-08-09-turn-error-feedback`) | `src/turn/turn_action_server.cpp:63` |

베이스 클래스(`trnav_2ws_motion/qd_action_server_base.hpp`)의 `publishWheelCmd`·
`guardSteer`·`wheelStateCallback`·`imuCallback` 등은 **별도 모듈**이므로 그 모듈의
표에 등재한다(현재 미작성).

**중복/유사 함수**: 없음(파일 내 함수 3개).

## execute 내부 단계 (플로우)

| 단계 | 조향 | 구동 | 위치 |
| --- | --- | --- | --- |
| Phase 0 조향정렬 | 원호각으로 이동, 도달 대기(타임아웃 `steer_timeout_sec`) | 0 | `:125-` |
| Phase 1-3 프로파일 | 원호각 유지 | 사다리꼴 ω, `min_speed_dps` 하한 | `:186-290` |
| 정착 | 원호각 유지 | 0, `settling_delay_ms` 대기 | `:292-319` |
| Phase 3.5 미세보정 | **원호각 유지**(2026-08-06 변경) | 저속으로 원호 계속/되돌림 | `:321-406` |
| 정지 | **원호각 유지**(2026-08-06 변경) | 0 | `:408-412` |
| Phase 4 조향복귀 | `exit_steer_angle` 로 이동(`hold_steer` 면 생략) | 0 | `:415-` |

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
| 2 | `min_speed_dps_` (가변, 기동 후 불변) | 3 | **Stage 1(coarse) 전용** 각속도 하한. Stage 2(PD)에는 걸지 않는다 — 목표 근처 강제 최소속도는 한계진동 | `include/…/turn_action_server.hpp:43` |
| 3 | `fine_correction_threshold_deg_` (가변, 기동 후 불변) | 3 | Stage 2 정착 판정 각오차 tol. **잔여 오차를 사실상 이 값이 정한다** — SIL 에서 0.3→0.05 로 조이자 실제오차 −0.264°→−0.041° | `include/…/turn_action_server.hpp:44` |
| 4 | `pid_band_deg_` (가변, 기동 후 불변) | 3 | coarse→PD 인계 임계. `kp·band ≈ ω_max` 가 되게 잡아 인계 지점에서 지령이 튀지 않게 한다 | `include/…/turn_action_server.hpp:47` |
| 5 | `kp_turn_` · `kd_turn_` (가변, 기동 후 불변) | 3 | Stage 2 PD 게인. **`ki` 는 파라미터로도 없다**(사용자 지시 — 진동 위험; 항상 0 이어야 할 게인은 함정) | `include/…/turn_action_server.hpp:48-49` |
| 6 | `settle_rate_dps_` · `settle_count_` (가변, 기동 후 불변) | 3 | 정착 게이트 — \|e\|≤tol **AND** \|실측 회전율\|≤rate 가 count cycle 연속. \|e\|만 보면 아직 도는 중에 도달로 판정한다 | `include/…/turn_action_server.hpp:53-54` |
| 7 | `start_yaw_window_` (가변, 기동 후 불변) | 3 | `start_yaw` 원형 이동평균 샘플 수. 1회 샘플이면 그 순간 IMU 잡음이 절대 기준 전체를 오프셋 | `include/…/turn_action_server.hpp:55` |

**전역 필요성 평가**: 전부 파라미터 캐시로 클래스 멤버가 적절.

## 알려진 미해결 사항 (등재만 — 판단은 code_review 소관)

| 항목 | 내용 | 상태 |
| --- | --- | --- |
| A | ~~`:233` 주 루프가 방향을 보지 않는다~~ | **해결(2026-08-06)** — 측정 후 채택. 아래 §각도 계상 참조 |
| B | `settling_delay_ms: 200` 이 드라이브 관성(실측 0.57~0.65 s)보다 짧아 **기체가 멈추기 전에 잔여각을 읽는다** | 미조치. 동특성 켠 SIL 로 측정 후 판단 |
| C | 보정 속도 3.0 deg/s × 관성 0.6 s ≈ **1.8° 오버슛** vs 임계 0.3° — 수렴 불가 구조 | 미조치. B 와 함께 판단 |
| D | 액션이 엔코더(`/wheel_motor_state_detailed`)를 읽지 않고 IMU yaw 만 쓴다 | **QD 도 동일(참조 0건)** → 「QD 와 동일하게」에 따라 미변경 |

## 각도 계상 (2026-08-06 정정)

`turn` 은 진행량을 IMU yaw **델타 누적**으로 잰다. 계상 지점이 세 곳이고, 셋 다 목표 방향
성분만 세야 한다. 종전에는 **주 루프만** 방향을 무시했다.

| 지점 | 종전 | 현행 |
| --- | --- | --- |
| 주 루프 `:258` | `+= std::abs(delta_yaw)` — **방향무시** | `+= sign * delta_deg` |
| 정착 `:309·313` | `sign*delta_deg>0` 분기 | 동일(변경 없음) |
| 미세보정 `:382·386` | 동일 | 동일(변경 없음) |

세 형태는 수학적으로 동일하다 — `sign·d > 0` 이면 `|d| = sign·d`, `< 0` 이면 `|d| = −sign·d`.
즉 새 규칙이 아니라 **주 루프만 빠져 있던 같은 규약**을 맞춘 것이다.

**왜 지금까지 안 보였나** — 잡음 없는 즉응 플랜트에서는 델타 부호가 뒤집히지 않아
`std::abs` 와 부호 반영이 **완전히 같은 값**을 낸다(측정오차 0.000°). 플랜트에 관성과
IMU yaw 잡음을 넣고서야 드러났다.

**SIL 실측** (목표 45° · R=1.0 m · 관성 0.6 s · IMU yaw 잡음 0.05° 1σ, `--runs 5`):

| | 종전 `std::abs` | 현행 부호반영 |
| --- | --- | --- |
| 실제오차 평균 | −0.536° | **−0.211°** |
| 실제오차 \|최대\| | **0.846°** | **0.298°** |
| 실제오차 σ | 0.221° | **0.065°** |
| 미세보정 임계 0.3° | **달성 불가** | 달성(여유 0.002° — **빠듯함**) |

⚠ 잡음 0.05° 1σ 는 **가정값**이다 — `References/` 에 iAHRS 자료가 없어 실기 잡음 크기는
모른다. 기전과 방향(항상 부족 회전)은 확정, 실기에서의 크기는 미확정.
⚠ 임계 0.3° 여유가 0.002° 뿐이라 실기 잡음이 조금만 커도 초과한다. `spin` 방식
(절대 목표 yaw 대조, `spin_action_server.cpp:276`)으로 옮기면 델타 누적 자체가 없어져
편향이 원천 소거되나, 이는 구조 변경이라 별건.

**회귀 고정**(⚠ 2026-08-10 폐기): `Tools/motion_chain_check/turn_angle_accounting_check.py` 가 세 지점을
소스에서 재도출해 하나라도 방향을 무시하면 `exit 1`. 검출력 확인 — 종전 형태가 남아 있는
QD 상류를 `--path` 로 지정하면 `:233` 을 잡고 `exit 1` 이 난다.

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
| **돌연변이** | `:408` 정지 블록만 종전 복원 후 재실행 | 조향 최대 **90.00°/90.00°** 로 회귀 → 원인 확정 |
| ~~각도 계상 회귀~~ | **2026-08-10 폐기** — `Tools/motion_chain_check/turn_angle_accounting_check.py` 삭제 | 검사 대상(델타 누적)이 구조 변경으로 사라졌고, 남겨 두면 무관한 `std::fabs` 를 잡아 **없는 부호 결함을 있다고 보고**했다(오탐, exit 1). 고칠 대상이 없으므로 폐기 |
| 잔여각 (즉응·무잡음) | `turn_residual_probe.py --runs 3` | 45.172° · σ 0.000 — **변경 전과 완전 동일**(무회귀) |
| 잔여각 (동특성+잡음) | `turn_residual_probe.py --runs 5` | 실제오차 \|최대\| 0.298° (종전 0.846°) |

⚠ **최종 verdict 는 저자가 찍지 않는다**(`coding.md:88`). 위는 실행 관측 기록이며
승인이 아니다 — 외부 리뷰 패스 필요.


---

# turn_reverse — 후진 원호 (2026-08-09 신설)

> ADR: [2026-08-09-turn-reverse](../../../../../docs/adr/2026-08-09-turn-reverse.md)

## 목적

전진판 `turn` 과 **같은 원호를 반대 방향으로** 그린다. `target_angle` 의 의미는 전진판과
동일한 **헤딩 변화량**(+CCW)이고, IK(Inverse Kinematics) 입력의 `vx` 만 음수가 된다.
그러면 `R = v/ω` 의 부호가 뒤집혀 ICR 이 반대편으로 옮겨간다 = 후진 원호.

## 함수 리스트 표

| # | 함수 | 입력 | 출력 | 기능 | 위치(file:line) |
| --- | --- | --- | --- | --- | --- |
| 1 | `TurnReverseActionServer.TurnReverseActionServer` | `node`, `action_mutex` | — | 베이스 초기화, `turn_reverse_params.yaml` 로드. 액션명 `amr_motion_turn_reverse_abstract`, 발행 `/motion/wheel_cmd/turn_reverse` | `src/turn_reverse/turn_reverse_action_server.cpp:10` |
| 2 | `TurnReverseActionServer.validateGoal` | `TurnReverse::Goal` | `bool` | `turn_radius > 0`·`max_linear_speed > 0`(**magnitude**)·`accel_angle > 0` 검사 | `src/turn_reverse/turn_reverse_action_server.cpp:31` |
| 3 | `TurnReverseActionServer.execute` | `GoalHandle` | `void` | Phase 0 조향정렬 → start_yaw 원형평균 → Stage 1 사다리꼴 coarse → Stage 2 PD fine + 정착 게이트 → Phase 4 조향복귀. 전진판과 동일 구조(`vx` 부호만 반전) | `src/turn_reverse/turn_reverse_action_server.cpp:63` |

## 전진판과의 차이 — IK 입력 `vx` 부호 3곳

| # | 위치 | 전진판 | 후진판 | 비고 |
| --- | --- | --- | --- | --- |
| 1 | `:121` Phase 0 조향정렬 | `{ max_v, 0, sign·ω}` | `{-max_v, 0, sign·ω}` | 원호 자세 결정 |
| 2 | `:216` 주 루프 | `{ v, 0, sign·ω}` | `{-v, 0, sign·ω}` | — |
| 3 | `:368` Phase 3.5 미세보정 | `{ v_fine, 0, ω}` | `{-v_fine, 0, ω}` | **`v_fine` 만 반전.** `ω` 는 `travel_dir` 로 이미 뒤집히므로 `v/ω` 가 주 루프와 같은 부호 반경(−R)이 되어 조향 자세가 보존된다. 둘 다 반전하면 +R 이 되어 전진 원호 자세로 튄다 |

**`ω` 부호는 유지한다** — `target_angle` 이 헤딩 변화량이라는 의미를 전진판과 공유하기 위함.

## 클래스 멤버 상태 표

전진판과 동일하되 `motion_source_id_` 만 다르다.

| # | 멤버 | 사용처(함수) | 기능 | 위치(file:line) |
| --- | --- | --- | --- | --- |
| 1 | `motion_source_id_` (가변, 기동 후 불변) | 1, 3 | mux 소스 id = **12**. 10·11 은 stanley 예약이라 침범하지 않는다. 계약 정본은 `trnav_motion_mux.yaml` 의 Reserved IDs 주석 | `include/…/turn_reverse_action_server.hpp:40` |
| 2~7 | `min_speed_dps_` · `fine_correction_threshold_deg_` · `pid_band_deg_` · `kp_turn_` · `kd_turn_` · `settle_rate_dps_` · `settle_count_` · `start_yaw_window_` | 3 | 전진판과 같은 yaml 키·같은 의미. 삭제된 이름: `imu_deadband_deg` · `fine_correction_speed_dps` · `fine_correction_timeout_sec` · `settling_delay_ms` | `include/…/turn_reverse_action_server.hpp:52-65` |

## 검증 이력 (2026-08-09)

| 항목 | 도구·조건 | 결과 |
| --- | --- | --- |
| ~~각도 계상 회귀~~ | **2026-08-10 폐기** — `Tools/motion_chain_check/turn_angle_accounting_check.py` 삭제 | 검사 대상(델타 누적)이 구조 변경으로 사라졌고, 남겨 두면 무관한 `std::fabs` 를 잡아 **없는 부호 결함을 있다고 보고**했다(오탐, exit 1). 고칠 대상이 없으므로 폐기 |
| SIL 후진 | 헤딩 +20°, R=1.0 | 헤딩 +20.16° · 변위 350 mm · 차체기준 −170.0°(후진) · 반경 1.000 m · 조향 (−31.1, +30.8) |
| SIL 전진 대조 | 같은 목표 | 차체기준 +10.0°(전진) · 조향 (+31.1, −30.8) — **부호만 반전, 나머지 동일** |
| 실기 후진 | 헤딩 +10°, R=1.0, 0.05 m/s | 측위 +10.38° · IMU +10.30° · 변위 181 mm · −173.5°(후진) · 반경 0.998 m · 조향 (−31.13, +30.80) · 구동 2축 차 2.4 mm |
| 실기 왕복 폐합 ① | 후진 +10.38° → 전진 −10.38° | **잔차 위치 5 mm · 헤딩 0.15°** — 같은 호를 되짚음이 실증 |
| 실기 왕복 폐합 ② (반대쪽 호) | 후진 −10.01° → 전진 +9.66° | **잔차 위치 6 mm · 헤딩 −0.38°** · 반경 1.008 / 1.003 m |

## 알려진 미해결 사항 (등재만 — 판단은 code_review 소관)

| # | 항목 | 상태 |
| --- | --- | --- |
| 1 | **`turn` 계열 허용 오차 미정** | spin 은 ≤0.40°(사용자 승인)로 정했으나 turn 계열은 규격이 없다. 실측 오차는 전진 −0.19° · 후진 +0.38° |
| 2 | **표본 1회** | 전진·후진 각 1회, 왕복 1회. 반복 시험 미실시 |
| 3 | **코드 중복** | `turn` 과 `turn_reverse` 가 `vx` 부호 3곳을 빼면 같은 코드다. 한쪽 수정 시 다른 쪽도 고쳐야 한다(ADR 이 비용을 명시적으로 수용). 공통 코어 추출은 범위 밖 |
| 4 | **후진 원호 파라미터 미조정** | `turn_reverse_params.yaml` 은 전진값을 그대로 옮긴 것이다. 정밀도 요구가 생기면 별도 조정 필요 |
