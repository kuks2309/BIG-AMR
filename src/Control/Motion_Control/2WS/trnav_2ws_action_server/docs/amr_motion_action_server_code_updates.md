# trnav_2ws_action_server — code updates

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
- 수정 `src/yaw_control/…cpp`·`src/yaw_control_reverse/…cpp` — 「`lookupMapToBase` 는 **신선도를 보지 않는다**」가
  현재 구현과 모순(스탬프 나이가 `localization_timeout_sec` 초과면 false). 「−7 이 **0.2 s** 만에 발화」도
  cycle 계수 시절 수치라 같은 파일의 `1.0 s` 서술과 충돌 — pose 샘플 10개(실차 10 Hz ≈ 1.0 s)로 통일.
  `Pre-check: … 위치는 TF lookupMapToBase 가 처리`·`Acquire start pose from tf2` 도 `/robot_pose` 스냅샷으로 정정
  (저장소에서 이 4줄이 마지막 TF 잔재였다).
- 수정 `src/mpc/mpc_action_server.cpp` — `// ── Pure Pursuit update ──` → `// ── MPC update ──`.
  이 지점은 `TwoWsMpcController::update()` 로 NLopt SLSQP 를 1회 돌린다. PurePursuit 는 이 스택에 클래스도 없다.
- 수정 `src/spin/spin_action_server.cpp` — 「종료는 fine timeout 으로만」이 코드와 반대. 정상 종료 경로는
  settle 게이트(|e|≤threshold AND |회전율|≤settle_rate 가 settle_count cycle 연속)이고 timeout 은 미수렴 안전망이다.
  남은 오차 부호 규약도 CW(sign=−1)에서 반대였던 것을 「부호가 sign 과 같으면 더 회전 필요」로 정정.
- 수정 `src/crab_linear/…cpp`·`…hpp` — Crab IK 주석의 「양 휠 동일 steer」가 사실과 다르다
  (front=base, rear=base−δ_heading, 그 차이가 yaw 능동 보정 그 자체). wheel-state override 목적도
  「actual-steer-based speed」가 아니라 feedback 신선도 판정이다.
- 수정 `include/…/translate_reverse/…hpp` — `yaml — translate_reverse_*` 는 존재하지 않는 접두사.
  이 서버가 읽는 키는 forward 와 같은 `translate_*` 다(핫리로드 화이트리스트도 `translate_*` 5키).
- 수정 `config/turn_params.yaml`·`turn_reverse_params.yaml` — `trnav_2ws_core::loadGeometry` 는 존재하지 않는 심볼.
  실제 소유자는 `TwoWsActionServerBase::loadGeometry`(`trnav_2ws_motion/…/qd_action_server_base.hpp`).
  `turn_reverse_params.yaml` 머리의 「후진 원호는 아직 실측되지 않았다」도 같은 파일 43-47 의 실기·SIL 근거와 모순이라 정정.
- 수정 `launch/sil_{mpc,mpc_reverse,translate_forward,translate_reverse}.launch.py` — 에러 문구 인용에서
  「종전 문구 …는 교체됐고 지금은 QD 스택만 낸다」는 이력 제거, 현행 문구와 발생 위치만 유지.
  `/robot_pose` 발행자 안내도 디렉터리 나열을 빼고 배선 함정(저장소 유일 후보 `seer_pose_publisher` 의
  기본 발행은 `/seer/robot_pose`)만 남겼다.
- 수정 `launch/{crab_linear,mpc,translate_forward,yaw_control}.launch.py` — 부재 문서 인용을 삭제
  (부재 사실을 서술하지 않는다).
- 수정 `launch/sil_yaw_control.launch.py`·`sil_yaw_control_reverse.launch.py` — `yaw_offset` 산출이 「TF 경유」가
  아니라 `/robot_pose` 경유다.
- 수정 `launch/sil_spin.launch.py` — omega closed-loop 식이 분모 0 인 QD 분기(`(vx1-vx2)/dy`)였다.
  inline 2WS 는 x 간격이 분모(`(vy1-vy2)/dx`).
- 수정 `launch/sil_crab_linear.launch.py` — 살아 있는 발행 타입 `trnav_msgs::msg::SafetyStatus` 를
  「폐기된」 것으로 지목하던 서술 제거, 워치독 구독 타입 일치 요건만 남김.
- 수정 `include/…/mpc_reverse/…hpp` — `motion_source_id_` 주석의 계약 정본을 실재하는
  `trnav_motion_mux/config/trnav_motion_mux.yaml` Reserved IDs 주석으로 통일(전진판과 동일 표기).
- 수정 `CMakeLists.txt`·`include/…/turn_reverse/…hpp` — 노드·타깃 서술을 실제 구성에 맞춤.

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
- 수정 `src/{mpc,mpc_reverse,translate_forward,translate_reverse}/…cpp` — `LocalizationMonitor (TF-only, topic 폐기)`
  → **정반대**였다: `/robot_pose` 토픽 구독 기반이고 폐기된 쪽이 분산 TF lookup(2026-05-18).
- 수정 `src/crab_linear/crab_linear_action_server.cpp` — 파일 머리 알고리즘 서술이 실제 cruise 루프와 달랐다
  (`omega_cmd → DualSteerIK` → 실제는 `TwoWsCrabIK.compute(vx, theta_body, delta_cte, delta_heading)`, omega 0 고정).
- 수정 `src/spin/spin_action_server.cpp` — Stage 2(fine) 주석의 「|omega| 하한 `min_speed_dps_`」 삭제:
  하한 floor 는 Stage 1 에만 적용되고 fine 은 상한만 clamp 한다(:418 이 이미 그렇게 적고 있었다).
- 수정 `src/translate_reverse/…cpp` — 「램프 입력은 항상 ≥ 0」 → `kReverseDir(-1)` 이 곱해져 항상 ≤ 0
  (전진판 문장의 복사 잔재).
- 수정 `config/yaw_control_params.yaml` — 「`add_on_set_parameters_callback` 이 없어 `ros2 param set` 이 안 먹는다」
  → 콜백은 실재하며(`yaw_control_action_server.cpp:90`) 화이트리스트 10키는 hot-reload, 나머지는 명시적 거부.
- 수정 `config/*_params.yaml` 8종 — Tongyi 참조 줄 앵커 `…protocol-reference.md:11-15` → `:42-46`(휠 좌표표 실제 위치).
- 수정 `launch/sil_turn_reverse.launch.py` — docstring 이 `active source = turn, id=5`·`/motion/wheel_cmd/turn`
  로 전진판을 가리켰다 → `turn_reverse, id=12`·`/motion/wheel_cmd/turn_reverse`.
- 수정 `launch/{sil,hil}_mpc{,_reverse}.launch.py` — mux source id `7`/`10` → 실제 `8`/`9`.
- 수정 `launch/sil_{mpc,mpc_reverse,translate_forward,translate_reverse}.launch.py` — 인용한 에러 문구가 2026-08-10 에
  교체된 옛 문구(`TF2 map->base_link not available`)였다 → 현행 문구. 그 옛 문구는 이제 QD 스택에만 남아 있다.
- 수정 `launch/{crab_linear,mpc,translate_forward,yaw_control}.launch.py` — 부재 문서
  `docs/plan/2026-06-09_phase2_robot_pose_replacement.md` 를 「이 저장소에 없음」으로 명시.
- 수정 헤더 6종 — `docs/abstraction/motion_source_id_contract.md`(부재) → 계약 정본은 `trnav_motion_mux.yaml` 주석;
  `turn`/`turn_reverse` 의 `max_timeout_sec_` 옆 주석이 **다른 멤버(이동평균 샘플 수)** 설명이던 것 정정 등.

---

2026-07-04 / 09:52 - (pending) / **QD 운동학 include·link 경로 이관** (AD-012 개정 — `trnav_2ws_kinematics` 분리)

- 수정 헤더 8종 include 경로 `trnav_2ws_motion/qd_{bicycle_model,crab_inverse_kinematics}.hpp` → `trnav_2ws_kinematics/...`: `mpc`, `mpc_reverse`, `yaw_control`, `yaw_control_reverse`, `translate_forward`, `translate_reverse`, `turn` (bicycle), `crab_linear` (crab). `spin` 은 `qd_action_server_base` 만 사용 — 무변경
- 수정 `CMakeLists.txt` — `find_package(trnav_2ws_kinematics)` 추가 + link 16곳 `trnav_2ws_motion::qd_{inverse_kinematics×9,bicycle_model×6,crab_inverse_kinematics×1}` → `trnav_2ws_kinematics::`
- 수정 `package.xml` — `<depend>trnav_2ws_kinematics</depend>` 추가 (동작·로직 무변경, 경로만)

2026-06-19 / 13:00 - 6c0ae00 / **translate fwd·rev: skip_initial_pose_check 게이트 (on_position_mismatch=none 전파)**

- 수정 `src/translate_forward/translate_forward_action_server.cpp:409`, `src/translate_reverse/translate_reverse_action_server.cpp:404`: `if (goal->skip_initial_pose_check) { validateInitialPose 생략 + WARN } else { 기존 검사 → -2 }`.
- 의존: `trnav_2ws_interfaces` action(TranslateForward/Reverse)에 `bool skip_initial_pose_check false` 신규 필드 + `acs_gui/ros/goal_builder.py` 가 `on_position_mismatch=='none'` 시 true 전파.
- 배경: 06-19 L11 주행 -2(validateInitialPose) — GUI none 정책 미전파 (issues_fixes [2026-06-19 12:45]). 경로 밖 시작 허용(운영자 위치 책임). 나머지 검사(loc 수신·watchdog·jump) 유지.
- 검증: ros2 interface 필드 노출 / colcon build error0 / 서버 게이트 양쪽. **motion server 재기동 필요.**

2026-06-05 / HH:MM - (pending commit) / **translate_forward: heading yaw 소스 IMU 치환 토글 추가 (A/B 실험용)** — `src/translate_forward/translate_forward_action_server.{hpp,cpp}` + `config/translate_forward_params.yaml`

- 배경: 직선주행 조향 좌우 진동 분석 결과, heading 제어 항이 `/robot_pose` yaw(지연 66~155ms + 재측위 점프)를 입력받아 1~2Hz limit-cycle 유발(experiments/2026-06-05_robot_pose_yaw_vs_imu). IMU(iAHRS 9축, 지자기 융합·무지연·무점프) heading 으로 바꿨을 때 진동 감소 폐루프 검증용.
- 추가: param `translate_heading_source` (0=robot_pose 기본 / 1=IMU). `=1` 시 e_theta 용 `robot_yaw` 만 IMU 로 치환, **x,y(CTE Stanley 입력)는 항상 pose**. 출력/IK/watchdog/스핀 무수정.
- offset 처리(1a): 주행 시작 후 **첫 10 control sample(50Hz, 0.2s) 로 `(pose_yaw − imu_yaw)` 평균 → 고정**(RMA10). capture 중엔 pose yaw 유지(시작 안전), 고정 후 `robot_yaw = normalizeAngle(imu_yaw + offset)`. iAHRS yaw 가 지자기로 유계(§9)라 고정 offset 성립. `#include trnav_2ws_core/math_utils.hpp`(normalizeAngle).
- 기본값 0 → 기존 동작 무변경(회귀 안전). 빌드 PASS(-j1). **HIL/실차 미검증** — A/B(0 vs 1) 실차 주행 + cross-track/heading-error 측정 필요(드리프트 확인).

2026-06-05 / HH:MM - (pending commit) / **spin: Stage2 fine settle 게이트 조기종료 (노드 회전 지체 제거)** — `src/spin/spin_action_server.cpp`

- 문제: Stage2 PID fine 이 `|e|≤threshold 즉시종료 제거`(과회전 방지) 후 **오직 fine_timeout(=3×총각/max_ω, 90°→18s)까지 회전/대기** → 노드마다 ~10s(최대 19s) 지체 (run_122138 bag: 회전 9회, 빠른 3.5s + 느린정착 10s).
- 수정 ①: Stage2 에 **settle 게이트 조기종료** — `|error_deg|≤fine_correction_threshold_deg(0.3°)` AND `|derivative|(=실측 회전율)≤settle_rate_dps(2°/s)` 가 `settle_count(5)` cycle 연속 → 종료. (이미 정의됐으나 미사용이던 `settle_rate_dps`/`settle_count` 활용.)
- 과회전 안전: 옛 즉시종료(|e|만)와 달리 **실측 회전율까지 정지 확인 후 종료** → coast 과회전 없음. fine_timeout 은 미수렴 안전망으로 유지(축소 안 함, 사용자 ①만 승인).
- 효과(예상): 회전당 ~10s → ~1.5s. 빌드 PASS(-j1). HIL 미검증.

2026-06-05 / HH:MM - (pending commit) / **translate_forward: 종단 fine-positioning(저속 P-creep closed-loop) 추가** — `src/translate_forward/translate_forward_action_server.{hpp,cpp}`

- 문제: 사다리꼴 feedforward + `projection≥target` 즉시 종료 → 종료 속도 min_vx_(0.02)에서 모터 coast 로 ±10~20cm 지나침(정지오차). 종단 위치 closed-loop 부재(사용자 지적).
- 추가: **exit_speed≤0 최종 정지 한정** 종단 분기. `remaining<fine_enter_dist(0.08)` 또는 DONE 시 min_vx_ floor 미적용, `vx=clamp(fine_kp·remaining, fine_v_min, fine_v_max)` 저속 creep(실 projection closed-loop), `remaining≤fine_tol_pos(0.02)` 수렴 정지 + `fine_timeout(5s)` 가드. exit_speed>0(체이닝)·조향·IK·watchdog 무수정.
- param: translate_fine_{enter_dist 0.08, tol_pos 0.02, kp 0.5, v_max 0.04, v_min 0.015, timeout 5.0}. `#include <algorithm>`(std::clamp).
- 빌드 PASS(-j1). HIL 미검증. plan: docs/plan/2026-06-05_translate_fine_positioning.md.

2026-06-02 / HH:MM - (pending commit) / **spin: 실차 HIL 게인 튜닝 완료 + 종료/타임아웃/콜백 개선** — `src/spin/spin_action_server.{hpp,cpp}` + `config/spin_params.yaml`

- **`|e|≤fine_correction_threshold` 즉시종료 제거** (Stage2): 옛 bang-bang exit 잔재. "움직이며 종료"→비결정/조기정지 유발 → PID 가 setpoint 잡고 정착하도록 제거 (사용자 지적).
- **fine 타임아웃 적응화**: 고정 3s → **`fine_timeout_sec = max(2, 3·target_abs/max_ω)`** (진행시간×3). 고정 타이머가 수렴 전에 0 강제종료(에러 잔존 wheel=0)하던 문제 해결.
- **Stage2 min_speed floor 제거** (fine): 목표 근처 한계진동(limit cycle) 원인. coarse 만 floor 유지 (yaw_control near_goal 패턴).
- **OnSetParametersCallback 추가**: `kp_spin/ki_spin/kd_spin/pid_band_deg/min_speed_dps/integral_limit_deg/fine_correction_threshold_deg/control_rate_hz/fine_correction_timeout_sec/spin_max_timeout_sec` 런타임 `ros2 param set` 반영 (재컴파일 없이 튜닝). control_rate_hz 는 다음 goal 부터 적용.
- **yaml 게인 확정 (실차 HIL 2026-06-02)**: `kp_spin 1.7 / ki_spin 0.0 / kd_spin 0.1 / pid_band_deg 30 / control_rate_hz 50`. (이전 SIL 시드 kp1.5/kd0.5/band5/20Hz 대체.)
- **검증**: 실차 HIL ±10/20/30/45/80/120/180.1 (양·음) 전 각도 **|오차|≤0.42°, overshoot~0, 단조, ±180 방향 일관**. 그래프 `experiments/2026-06-01_spin_pm180_hil/results/angles/`, 요약 `angle_sweep_summary.csv`.
- **핵심 교훈**: 제어 정밀도는 **steer return(Phase4) 전 `actual_angle`** 로 측정해야 함 (final_error 는 Phase4 후라 무관). control_rate 20→50Hz 가 고속 overshoot 를 절반↓ (이산화 지연). 상세 `docs/claude-mistake/2026-06-02_spin_overengineering_min_floor_oscillation.md`.

2026-06-01 / HH:MM - (pending commit) / **spin: ±180 엣지 수정 + 하이브리드(사다리꼴 coarse → PID fine) 제어** — `src/spin/spin_action_server.{hpp,cpp}` + `config/spin_params.yaml`

- **±180 수정** (실차 overshoot 분석 발단):
  - **경계 결정화** (sign 계산): `std::remainder` round-half-even 으로 180.0→+180(CCW)/180.001→−179.999(CW) 방향 반전 제거. `|정규화|>180−0.5°` 면 raw 입력 부호로 회전방향 고정 (shortest 유지). `target_imu_yaw` 앵커도 `sign*target_abs` 로 통일.
  - **start_yaw 원형 이동평균**: 단일 샘플 노이즈가 절대 target 오프셋 → Phase 0 정지 구간 N=10 샘플 `atan2(Σsin,Σcos)` (wrap-safe). param `start_yaw_avg_samples`.
  - 주석 정정: `math_utils.hpp:9-11`, spin:82-83 의 틀린 "−180 정착" → round-half-even 실동작.
- **하이브리드 제어 전환** (사용자 요청 구조): 기존 bang-bang fine correction → **PID** 로 교체, 사다리꼴은 coarse 단계로 유지.
  - **Stage1 (Coarse, 남은오차>pid_band)**: `TrapezoidalProfile` (accel/cruise/decel). 종료조건에 `남은오차 ≤ pid_band` 추가 → Stage2 인계. progress 는 target-anchored(`target_abs − |signed remaining|`, antipode-safe).
  - **Stage2 (Fine, PID, 남은오차≤pid_band)**: `ω_dps = kp·e + ki·∫e + kd·de/dt`, `e = normalizeAngle(target_imu_yaw − yaw)` (부호 포함 → overshoot 역보정; 스펙의 `target_abs−progress` 크기형은 부호 없어 보정 불가 + 180° antipode wrap → 부호형으로 구현). `|ω|` 하한 `min_speed_dps`(정지마찰)·상한 `max_angular_speed`, 방향 보존. 종료 `|e|≤fine_correction_threshold_deg(0.3)` or `fine_correction_timeout_sec`.
  - 신규 param: `pid_band_deg`(5.0) `kp_spin`(1.5) `ki_spin`(0.0) `kd_spin`(0.5) `integral_limit_deg`(30). `min_speed_dps`(2.0)·`fine_correction_timeout_sec`(3.0) 재사용. `settle_rate_dps`/`settle_count`/`fine_correction_speed_dps`/`settling_delay_ms` 미사용(yaml 호환).
  - 유지: Phase 0 steer align, Phase 4 steer return, mux select_motion_source, IMU 수신/Safety/Cancel 체크.
- **검증**: colcon build PASS (1m36s). ROS SIL (실제 노드+plant_sim, 정상 액추에이터) 90/180/180.001 전부 status=0, **overshoot ≤0.28°**, ±180 CCW 일관, <0.3° 정착, 정착 8.85/15.0s (순수 PID 대비 단축). 상세 `experiments/2026-06-01_spin_overshoot_sil/`.
- **실차 검증 예정** (2026-06-02 HIL): 계획 `docs/plan/2026-06-01_spin_pid_hil.md`, ±180 집중 스크립트 `experiments/2026-06-01_spin_pm180_hil/`. 액추에이터 지연 없음 가정(사용자 확정). 저게인 시작 + e-stop.

2026-05-28 / HH:MM - (pending commit) / **PP → MPC 마이그레이션 (Phase B)** — `pure_pursuit*/` 디렉터리 → `mpc*/`

- **dir rename**: `src/pure_pursuit/` → `src/mpc/`, `src/pure_pursuit_reverse/` → `src/mpc_reverse/` (헤더 동일: `include/trnav_2ws_action_server/{pure_pursuit,pure_pursuit_reverse}/` → `{mpc,mpc_reverse}/`)
- **파일 rename**: `pure_pursuit_action_server.{hpp,cpp}` → `mpc_action_server.{hpp,cpp}` / `pure_pursuit_main.cpp` → `mpc_main.cpp` (reverse 동일)
- **수정** `src/mpc/mpc_action_server.cpp` + `src/mpc_reverse/mpc_reverse_action_server.cpp`:
  - controller 교체 `TwoWsPurePursuitController` → `TwoWsMpcController` (NLopt SLSQP)
  - waypoints type `std::vector<std::pair<double,double>>` → `std::vector<MpcPose>` (yaw 직접 사용, path orientation 채택)
  - `update()` 5-arg signature (current_speed 추가)
  - anonymous namespace `PathHelperResult` 구조체 + `computePathHelper()` 헬퍼 신설 — `closest_seg` / `projection` / `lookahead_x/y` / `remaining_x` 계산 cpp 측 책임 (옛 PurePursuitOutput 의존 제거)
  - pp_params: PP 전용 필드 (`lookahead_distance`/`max_delta`/`heading_threshold`/`cte_filter_window`) 제거, `max_delta_rad` 사용
  - `setLookahead()` 호출 제거 (MpcController 미보유)
  - safeParam 키 prefix `pure_pursuit_*` → `mpc_*`
  - **TrapezoidalProfile 유지** (사용자 명시: "TrapezoidalProfile (가속/감속) 유지 해야 함")
- **launch rename**: `launch/{pure_pursuit,pure_pursuit_reverse,sil_pure_pursuit,sil_pure_pursuit_reverse,hil_pure_pursuit,hil_pure_pursuit_reverse}.launch.py` → `mpc{,_reverse,sil_mpc,sil_mpc_reverse,hil_mpc,hil_mpc_reverse}.launch.py` (6종 — `sed` mass-replace executable/node_name/params yaml 경로/topic 코멘트/source 코멘트)
- **config rename**: `config/pure_pursuit{,_reverse}_params.yaml` → `mpc{,_reverse}_params.yaml` + yaml key prefix `pure_pursuit_*` → `mpc_*` + 네임스페이스 `/trnav_pure_pursuit{,_reverse}_node` → `/trnav_mpc{,_reverse}_node`
- **수정** `CMakeLists.txt:229-263, 301-337, 340-351` — executable `amr_pure_pursuit{,_reverse}_node` → `amr_mpc{,_reverse}_node` + `target_link_libraries qd_pure_pursuit_controller` → `qd_mpc_controller` + install TARGETS 갱신 + 코멘트 갱신 (PP → MPC, NLopt SLSQP)

검증: `colcon build --packages-select trnav_2ws_action_server` 8.33s PASS (1 format warning std::size_t %d). 전체 `colcon build` 49 packages PASS.

2026-05-28 / 16:38 - 86b252e / 변경: `config/translate_forward_params.yaml:23-25` heading PD + K_stanley **원위치 복원** — `Kp_heading: 0.4→0.7`, `Kd_heading: 0.7→0.3`, `K_stanley: 1.5→2.0`

- 사용자 요청 (gain 원위치). 본 세션 16:10 / 16:13 변경 2건 모두 복원.
- 적용: yaml + 런타임 `ros2 param set` × 3 모두 PASS. `ros2 param get` 검증 PASS (0.7 / 0.3 / 2.0).
- bag 16:08 + 16:32 운용 결과 40 motion ABORT 0건 정상 (heading PD 새 gain 안정성 입증). 본 복원은 추가 튜닝 baseline 으로 복귀.

2026-05-28 / 16:13 - 86b252e / 변경: `config/translate_forward_params.yaml:25` `translate_K_stanley: 2.0 → 1.5` (Stanley CTE gain 완화, control_mode=3 적용 시 사용)

- 사용자 요청. 변경 분류 L2. Pre-impact-search 직전 16:10 entry 와 동일 (translate_K_stanley 는 화이트리스트 범위 [0,10]).
- 적용: yaml 수정 + 런타임 `ros2 param set /trnav_translate_forward_node translate_K_stanley 1.5` PASS. `ros2 param get` 검증 PASS.
- control_mode=3 (Stanley) 사용 시점에서만 효력. 현재 default control_mode=1 (Bicycle) 이므로 본 세션 직진은 Bicycle 만 영향, Stanley 미사용.

2026-05-28 / 16:10 - 86b252e / 변경: `config/translate_forward_params.yaml:23-24` `translate_Kp_heading: 0.7 → 0.4`, `translate_Kd_heading: 0.3 → 0.7` (heading PD 재튜닝 — P 감소 + D 증가)

- 사용자 요청 기반. 변경 분류 L2 (단일 yaml). Pre-impact-search: forward/reverse cpp + dd yaml + dd cpp 총 4 파일 grep — 신규 consumer 없음, hot-reload 화이트리스트 등록 확인.
- 범위 제약 충족: Kp [0,5] / Kd [0,2].
- 적용: yaml 수정 + 런타임 `ros2 param set /trnav_translate_forward_node translate_Kp_heading 0.4 / translate_Kd_heading 0.7` 모두 PASS. `ros2 param get` 검증 PASS.
- reverse 노드 (`config/translate_reverse_params.yaml` Kp=1.0, Kd=0.3) 는 본 변경 범위 외. 사용자 별도 요청 시 적용.
- 관련: [docs/issues_fixes/issues_and_fixes.md](../../../../../docs/issues_fixes/issues_and_fixes.md) (직전 14:12 N1 overshoot 분석에서 heading PD 영향 가능성 거론).

2026-05-26 / 17:00 - (pending commit) / **변경**: crab_linear Phase 0 끝 시점 `TwoWsCrabIK::setInitial` 호출 (state-aware, L3)

- `src/crab_linear/crab_linear_action_server.cpp` (line 466 직후):
  ```cpp
  RCLCPP_INFO(node_->get_logger(), "CrabLinear Phase 0 complete, ...");
  crab_ik_->setInitial(align_steer_f, ik_align.wheels[0].direction);
  ```
- 의도: Phase 0 (DualSteerIK ±π/2 strict wrap) 의 결정 (align_steer_f, walk dir) 을 cruise 의 TwoWsCrabIK 에 전달. cruise compute() 가 본 state 기준 ±25° clamp + dir 고정 → 두 단계 부호 일관.
- 사유: 사용자 ACS L4 (path_yaw=+90°) 진행 시 Phase 0 (-89° wrap) 와 cruise (+90° no-wrap) 부호 충돌 → robot 정반대 방향 진행. state-aware 로 정공법 정정.
- 검증: to_n3_stateaware (path +130°) SUCCESS, final_heading 0.206°, final_lateral +12.8mm.
- entry_speed > 0 (Phase 0 skip) case 는 미초기화 fallback (legacy ±π/2+25° wrap) — 후속 보강 필요.
- 관련: [trnav_2ws_motion_code_updates.md](../../trnav_2ws_motion/docs/trnav_2ws_motion_code_updates.md), [docs/issues_fixes/issues_and_fixes.md](../../../../../docs/issues_fixes/issues_and_fixes.md) [2026-05-26 17:00].

---

2026-05-25 / 22:30 - (pending commit) / **변경**: crab_linear cruise heading PD rear-steer 추가 (yaw 능동 보정, L3)

- `src/crab_linear/crab_linear_action_server.cpp`:
  - cruise loop 진입 전 `prev_yaw_err` 멤버 초기화
  - cruise 본문에 heading PD: `de_yaw = (yaw_err - prev_yaw_err)/dt`, `delta_heading = Kp_heading × yaw_err + Kd_heading × de_yaw`, saturate ±15°
  - `crab_ik_->compute(vx_profile, theta_body, delta_cte, delta_heading)` 4번째 인자 전달
  - feedback_fresh 시 `ik_for_speed = crab_ik_->compute(..., delta_heading)` 도 동일 전달
- 의도: target_yaw_deg 능동 유지. rear wheel offset 으로 robot yaw 회전 토크 발생 (bicycle-like).
- 검증: target_yaw 10° → final 0.354°, -10° → 0.94°, -90° (spin+crab 시퀀스) → 0.379°.
- 관련: [trnav_2ws_motion_code_updates.md](../../trnav_2ws_motion/docs/trnav_2ws_motion_code_updates.md) TwoWsCrabIK 인터페이스 확장.

---

2026-05-24 / 22:00 - (pending commit) / **변경**: crab_linear cruise 경로 `TwoWsDualSteerIK` → `TwoWsCrabIK` 교체 (±90° normalize edge sweep 제거, L3)

- **배경**: HIL bag `n2_cte_fix_181446` (path_yaw=-92°) 에서 wheel steer 가 +88° ↔ -88° saturate sweep + walk direction flip 46.4% 발생. theta_body 평균 -92.76° (CRAB sideways) 영역에서 DualSteerIK 의 `|angle|>π/2 → angle -= sign(angle)*π + direction flip` 가 부적절.
- `include/.../crab_linear_action_server.hpp` — include `trnav_2ws_motion/qd_crab_inverse_kinematics.hpp` 추가 + 멤버 `crab_ik_: std::unique_ptr<TwoWsCrabIK>` 추가.
- `src/crab_linear/crab_linear_action_server.cpp`:
  - constructor (path_ctrl_ 초기화 직후): `crab_ik_ = std::make_unique<TwoWsCrabIK>(geom.num_wheels, geom.wheel_radius, geom.gear_walk)` 추가.
  - cruise 본문: `delta_cte = atan2(K_stanley × pc_out.e_d, K_soft + |vx|)` 식 유지. vx_nom/vy_nom 회전 행렬 + `ik_->compute(vel_cmd)` 패턴 → `crab_ik_->compute(vx_profile, theta_body, delta_cte)` 단순화. 양 휠 동일 steer/speed/dir 출력.
  - actual-steer-based wheel speed 재계산 (feedback_fresh) 호출도 `crab_ik_` 로 교체.
  - Phase 0 alignment (`ik_->compute(align_cmd)`) 은 그대로 (omega 회전 align 에 DualSteerIK 적합).
  - 미사용 `omega_cmd_raw` / `prev_yaw_err` 제거 — heading 보정 omega 적용 시 재도입.
- `CMakeLists.txt` — `amr_crab_linear_node` target_link_libraries 에 `trnav_2ws_motion::qd_crab_inverse_kinematics` 추가.
- **검증**:
  - Static/Regression: `colcon build --packages-select trnav_2ws_motion trnav_2ws_action_server` PASS (warning 0)
  - bag 시뮬레이션 (`experiments/2026-05-24_crab_linear_hil_real/verify_crab_ik.py`): steer span 180°→7.4°, direction flips 46.4%→0% (동일 robot_pose 입력)
  - 실차: 내일 진행 예정 (N3→N2 동일 시나리오)
- 관련: [docs/issues_fixes/issues_and_fixes.md](../../../../../docs/issues_fixes/issues_and_fixes.md) [2026-05-24 22:00], [trnav_2ws_motion_code_updates.md](../../trnav_2ws_motion/docs/trnav_2ws_motion_code_updates.md).

---

2026-05-22 / 00:30 - (pending commit) / **변경**: Spin·Turn `target_angle` 입력 정규화 (wrap-around -3 timeout 회귀 fix, L2)

- **배경**: 실차 spin 명령 -3 timeout 반복. bag `experiments/acs_run_bags/run_2026-05-21_210957` 분석 — goal `7a325f640cb7` 60초 정확 timeout, phase=1 stuck 52.8s, `cmd vel ±0.0124 m/s` (=`min_speed_dps=2°/s` floor) 지속, IMU 정상 92Hz. 원인: `sign/target_abs/spin_angle_rad` 미정규화 (큰쪽 명령) vs `remaining/traveled = normalizeAngle(...)` (작은쪽 측정) 비일관. yaw wrap 시 `traveled_deg` 0 clamp → profile stuck.
- **정책**: `target_angle` 입력은 `normalizeAngleDeg` 로 [-180°,+180°] 정규화하여 **절대값 작은쪽 방향 회전**. |target| > 180° 자동 변환.
- `src/spin/spin_action_server.cpp` — 4 hunk:
  - 진입부: `const double target_angle_deg = trnav_2ws_core::normalizeAngleDeg(goal->target_angle);` 신규 (L82)
  - early-exit (L88-92): 비교 + 로그 → 정규화 변수 사용 + 원본/정규화 둘 다 로깅
  - sign / target_abs (L105-106): 정규화 변수 사용
  - spin_angle_rad (L173): 정규화 변수 사용
  - final log (L364-366): "Spin complete: target=%.1f° (normalized=%.1f°), …"
- `src/turn/turn_action_server.cpp` — 3 hunk:
  - 신규 include `trnav_2ws_core/math_utils.hpp` (L2)
  - 진입부: 정규화 변수 신규 (L99)
  - sign / target_abs (L107-108): 정규화 변수 사용
  - final log (L457-460): "Turn complete: target=%.1f° (normalized=%.1f°), …"
- `launch/sil_spin.launch.py` — **신규** SIL closed-loop launch (spin). `sil_crab_linear.launch.py` 패턴: `amr_spin_node` + `trnav_motion_mux` + `trnav_motion_supervisor`(source_id=3) + `translate_sim_odom_node` + `amr_safety_watchdog` + dummy safety pub. spin 은 LocalizationMonitor 미사용 → `sil_pose_adapter` 불포함.
- **검증**:
  - 단위: Python `math.remainder` (= C++ `std::remainder`) 거동 표 PASS — ±90°→±90° / +270°→-90° / -270°→+90° / +360°→0° / +540°→-180° / -540°→+180° / ±180° 부호 유지 (IEEE 754 round-half-to-even)
  - 빌드: `colcon build --packages-select trnav_2ws_action_server --symlink-install` PASS (1m 37s, 0 stderr) + launch 추가 후 재빌드 PASS
  - SIL: **7/7 PASS** — `experiments/2026-05-22_spin_normalization_sil/`. 시나리오 +45/+90/-90/+270/-270/+540/+180 전 status=0 (-3 timeout 0건), IMU yaw delta 부호+크기 정규화 expected 일치. 최대 elapsed 10.1s.
  - 사용자 검증 필요: Turn 은 SIL 미포함 — 실차/HIL 에서 turn goal 검증 필요
- 관련: [issues_and_fixes.md](../../../../../docs/issues_fixes/issues_and_fixes.md) [2026-05-22 00:30], `experiments/2026-05-21_spin_minus3_analysis/`, `experiments/2026-05-22_spin_normalization_sil/`

---

2026-05-21 / 22:30 - (pending commit) / **변경** (ADR-012 QD/DD 분리 consumer 갱신): 22 파일 — 9 hpp + 9 cpp + CMakeLists.txt + package.xml.

- **include path 갱신 (6 종)**: `#include "trnav_2ws_core/{bicycle_model,inverse_kinematics,path_controller,pure_pursuit_controller,wheel_set_packer,action_server_base}.hpp"` → `#include "trnav_2ws_motion/qd_*.hpp"`. 잔존 (`action_mutex`, `math_utils`, `motion_profile`, `transient_guard`, `localization_monitor`, `robot_geometry`, `recursive_moving_average`) 무변경.
- **qualified type 갱신 (17 종)**: `trnav_2ws_core::{ActionServerBase, BicycleModel, DualSteerIK, PathController, PurePursuitController, WheelSetPacker, BicycleCommand, DualBicycleCommand, BicycleState, ControlMode, TravelDirection, PathControlOutput, PurePursuitOutput, WheelPosition, VelocityCommand, WheelOutput, IKResult}` → `trnav::motion::two_ws::TwoWs*` / `trnav::motion::two_ws::*`. 잔존 (`ActionMutex`, `normalizeAngle`, `RobotGeometry`, `Platform`, `parsePlatform`, `TrapezoidalProfile`, `ProfilePhase`, `ProfileOutput`, `TransientGuard`, `LocalizationMonitor`, `RecursiveMovingAverage`) 무변경.
- **base class** 모든 9 action server: `trnav_2ws_core::ActionServerBase<T>` → `trnav::motion::two_ws::TwoWsActionServerBase<T>`. 호출 site 의 ctor + `wheelStateCallback` 슈퍼 콜 갱신.
- **CMakeLists.txt**: `find_package(trnav_2ws_motion REQUIRED)` 추가, `target_link_libraries` 5 target rename (`trnav_2ws_core::bicycle_model` → `trnav_2ws_motion::qd_bicycle_model` 외), `ament_target_dependencies` 9 블록에 `trnav_2ws_motion` 추가.
- **package.xml**: `<depend>trnav_2ws_motion</depend>` 추가 (`<depend>trnav_2ws_core</depend>` 다음 줄).
- **main.cpp 9 파일**: 변경 없음 (`action_mutex.hpp` 만 include — core 잔존).
- 빌드: 4 패키지 (trnav_2ws_core, trnav_2ws_motion, trnav_motion_dd, trnav_2ws_action_server) PASS, 0 failures, 0 stderr. trnav_2ws_action_server 빌드 5m 9s.
- 관련: `docs/request/2026-05-21_qd_dd_layer_separation.md`, `docs/abstraction/architecture_decisions.md` AD-012, `docs/issues_fixes/issues_and_fixes.md` [2026-05-21 22:30]

---

2026-05-21 / 19:35 - (pending commit) / 변경: 나머지 모션 노드 핫 리로드 확장 (Wave 2)

- `crab_linear_action_server.hpp/cpp`:
  - 멤버 3 추가 (`K_stanley_`, `K_soft_`, `max_delta_`) + 핸들 `params_cb_handle_`
  - 생성자 locals (K_stanley, K_soft, max_delta) → 멤버 캐시
  - `pc_params.X = local` → `pc_params.X = 멤버`
  - 생성자 끝에 5 키 콜백 등록 (`crab_linear_Kp_heading` 등, 범위는 translate_ 와 동일)
  - Kp/Kd 자체 omega PD ([crab_linear_action_server.cpp:517](../src/crab_linear/crab_linear_action_server.cpp#L517)) 와 PathController setGains 동시 반영
- `pure_pursuit_action_server.hpp/cpp`, `pure_pursuit_reverse_action_server.hpp/cpp`:
  - 핸들 `params_cb_handle_` 추가
  - 생성자 끝에 2 키 콜백 (`pure_pursuit_lookahead_distance` [0.1,5.0]m, `pure_pursuit_max_delta_deg` [10,90]°)
  - `pp_ctrl_->setLookahead/setMaxDelta` 호출
- 빌드: `colcon build --packages-select trnav_2ws_core trnav_2ws_action_server --symlink-install` PASS (1m 52s)
- 사용법: `ros2 param set /trnav_crab_linear_node crab_linear_Kp_heading 0.7` 등 — INFO 로그 + 다음 cycle 반영
- 관련: [docs/issues_fixes/issues_and_fixes.md](../../../../../docs/issues_fixes/issues_and_fixes.md) [2026-05-21 19:35], [docs/request/2026-05-21_translate_kp_tuning.md](../../../../../docs/request/2026-05-21_translate_kp_tuning.md)

---

2026-05-21 / 19:10 - (pending commit) / 변경: PathController 5 게인 핫 리로드 (`ros2 param set` 으로 kill 없이 튜닝)

- `include/.../translate_forward/translate_forward_action_server.hpp`: 멤버 5개 (`Kp_heading_`, `Kd_heading_`, `K_stanley_`, `K_soft_`, `params_cb_handle_`) 추가
- `src/translate_forward/translate_forward_action_server.cpp`:
  - 생성자 local `double Kp_heading = ...` → 멤버 캐시 `Kp_heading_ = ...` (4 곳)
  - `pc_params.Kp_heading = Kp_heading` → `pc_params.Kp_heading = Kp_heading_` (4 곳)
  - 생성자 끝에 `add_on_set_parameters_callback` 등록 (5 키 화이트리스트 + 범위 검증 + path_ctrl_->setGains)
- `include/.../translate_reverse/translate_reverse_action_server.hpp`, `src/translate_reverse/translate_reverse_action_server.cpp`: 동일 패턴 적용
- 신규 핫 리로드 키 (화이트리스트, 범위): `translate_Kp_heading` [0,5], `translate_Kd_heading` [0,2], `translate_K_stanley` [0,10], `translate_K_soft` [0.1,5], `translate_max_delta_deg` [10,90]°
- 사용법: `ros2 param set /trnav_translate_forward_node translate_Kp_heading 0.6` → INFO 로그 + 다음 control cycle 부터 반영
- 빌드: `colcon build --packages-select trnav_2ws_core trnav_2ws_action_server --symlink-install` PASS (1m 51s)
- 관련: [docs/issues_fixes/issues_and_fixes.md](../../../../../docs/issues_fixes/issues_and_fixes.md), [docs/request/2026-05-21_translate_kp_tuning.md](../../../../../docs/request/2026-05-21_translate_kp_tuning.md)

---

2026-05-21 / 19:10 - (pending commit) / 변경: `trnav_2ws_core` `PathController::setGains` 신규 (5 스칼라 게인 핫스왑 setter)

- `include/trnav_2ws_core/path_controller.hpp`: `void setGains(double Kp_h, double Kd_h, double K_s, double K_so, double max_delta_rad)` 선언 추가 (setMode 다음 줄)
- `src/path_controller.cpp`: 구현. `params_` 의 5 필드만 갱신, filter buffer / path state 미변경. 50Hz 단일 thread 가정 — race 발생 시 1 cycle mix 후 다음부터 일관.
- 호출자: translate_forward / translate_reverse 의 params 콜백
- (crab_linear 도 PathController 사용. 본 commit 범위 외 — 사용자 요청 시 추가)

---

2026-05-21 / 18:55 - 53ed3ab / 변경: `config/translate_forward_params.yaml:23` `translate_Kp_heading: 0.8 → 0.7` (직진 조향 오실레이션 2차 튜닝, Phase 2)

Phase 1 (1.0→0.8) 후속. 동일 file/line/key 만 값 변경. install share 가 src symlink 이므로 rebuild 불필요. ACS GUI 자식 launch 구조라 GUI 전체 재기동 후 `ros2 param get` 확인. Pre-impact-search Phase 1 결과 (translate_Kp_heading 4 파일 grep) 유효 — 신규 consumer 없음. Phase 1, 2 누적 결과 비교 예정. 관련: [docs/issues_fixes/issues_and_fixes.md](../../../../../docs/issues_fixes/issues_and_fixes.md), [docs/request/2026-05-21_translate_kp_tuning.md](../../../../../docs/request/2026-05-21_translate_kp_tuning.md).

---

2026-05-21 / 18:42 - 53ed3ab / 변경: `config/translate_forward_params.yaml:23` `translate_Kp_heading: 1.0 → 0.8` (직진 조향 오실레이션 1차 튜닝, Phase 1)

배경: bag `experiments/acs_run_bags/run_2026-05-21_183710` cruise 191.5s 동안 cmd_front std=4.16°/span=58°, lateral_error 평균 3 cm. front/rear 반대부호 동시 swing → `delta_f/r = stanley ± heading` 의 heading PD 항이 진동 driver. Stanley 항 산술 검산 (e_d=0.031m, vx=1.0) δ_stanley ≈ 1.8° 로 작음. P 항 20% 감으로 driver 검증 1차 실험. install share 가 src yaml symlink 이므로 rebuild 불필요. ACS GUI 자식 launch 구조라 GUI 전체 재시작 후 `ros2 param get` 으로 0.8 확인. 관련: [docs/issues_fixes/issues_and_fixes.md](../../../../../docs/issues_fixes/issues_and_fixes.md), [docs/request/2026-05-21_translate_kp_tuning.md](../../../../../docs/request/2026-05-21_translate_kp_tuning.md).

---

2026-05-21 / HH:MM - (pending commit) / 변경: `amr_crab_node` 폐기 + `amr_crab_linear_node` 신규 (target_yaw 능동 유지 + start↔end 직선 closed-loop)

사용자 요청 ([docs/request/2026-05-20_crab_target_yaw_path_following.md](../../../../docs/request/2026-05-20_crab_target_yaw_path_following.md)) — 기존 crab 의 open-loop 적분 + heading 모니터링만 하던 구조를, target_yaw 명시·능동 유지 + world-frame 직선 closed-loop 추종 단일 action 으로 교체. source_id=4 슬롯 재사용.

- 삭제 (8):
  - `include/trnav_2ws_action_server/crab/` (hpp 1)
  - `src/crab/crab_main.cpp`, `src/crab/crab_action_server.cpp`
  - `config/crab_params.yaml`, `launch/crab.launch.py`
  - `CMakeLists.txt:125-149` (`amr_crab_node` add_executable + link) + `CMakeLists.txt:326` install entry
  - (별도 패키지) `trnav_2ws_interfaces/action/AMRMotionCrab.action` + entry
  - (별도 패키지) `trnav_motor_control_ui/crab_action_test_logic.py` + `motor_control_ui.py` 의 crab 호출 5 블록 (import / setup / connections / IMU monitor / odom monitor / handlers)
- 추가 (8):
  - `include/trnav_2ws_action_server/crab_linear/crab_linear_action_server.hpp`
  - `src/crab_linear/crab_linear_main.cpp`, `src/crab_linear/crab_linear_action_server.cpp`
  - `config/crab_linear_params.yaml`, `launch/crab_linear.launch.py`
  - `CMakeLists.txt` `amr_crab_linear_node` add_executable + link (path_controller / transient_guard / localization_monitor 의존) + install entry
  - (별도 패키지) `trnav_2ws_interfaces/action/AMRMotionCrabLinear.action` + entry
  - (verify) `tools/verify/smoke_run/amr_motion_crab_linear_node.sh`
- 알고리즘 (translate_forward 패턴 차용 + IK 명령 직접 구성):
  - PathController 는 projection / e_d / e_theta 측정용 (δ_f/δ_r 출력 무시)
  - theta_body = wrap_pi(path_yaw − robot_yaw) — path 진행 방향을 body frame 으로 사영
  - omega_cmd = Kp_heading · yaw_err + Kd_heading · de_yaw  (yaw_err = wrap_pi(target_yaw − robot_yaw))
  - VelocityCommand = {vx · cos(theta_body), vx · sin(theta_body), omega_cmd} → DualSteerIK.compute → wheel cmd
  - heading abort: |yaw_err| > crab_linear_heading_threshold_deg → status=-4 (초기 검사 시 -2)
  - TransientGuard, steer rate limiter, steer convergence scale, walk velocity profile 은 translate_forward 와 동일
- 갱신:
  - `trnav_motion_mux.yaml` source_4 name `crab`→`crab_linear`, topic `/motion/wheel_cmd/crab`→`/motion/wheel_cmd/crab_linear`, 코멘트
  - `acs_gui/run_tab.py:1350` 토픽 문자열 동일 갱신
  - `acs_msgs/Link.msg` line 17 (단일 spin/crab_linear/turn), line 57-58 (7 action server — crab_linear 포함)
  - 도메인 문서: `motion_source_id_contract.md` (12-row 표 + 짝 + cpp 위치), `motion_mux_io_contract.md` §0/§6, `tm_nav_editor/docs/edge_characteristics.md` (CrabLinear 파라미터 정의)
- 변경 분류: L3 (멀티파일 + .action 인터페이스 변경)
- 관련 plan: [docs/plan/2026-05-20_crab_linear_action_implementation.md](../../../../docs/plan/2026-05-20_crab_linear_action_implementation.md)
- 관련 request: [docs/request/2026-05-20_crab_target_yaw_path_following.md](../../../../docs/request/2026-05-20_crab_target_yaw_path_following.md)

---

2026-05-20 / 08:36 - (pending commit) / 수정: `src/spin/spin_action_server.cpp` — execute() 진입부에 early-exit gate 추가 + start_time 선언 위치 이동

Spin 의 `target_angle` 이 `fine_correction_threshold_deg_` (default 0.3°) 미만일 때 Phase 0 (Steer Align) 가 무조건 실행되어 steer 모터가 회전하던 문제 해소. 사용자 지적: "현재 위치에 와 있으면 바로 종료, 현재는 모터 회전 후에 체크함".

- 수정 cpp 1개 (1 hunk):
  - `src/spin/spin_action_server.cpp:81-95` — `auto start_time = node_->now();` 를 line 98 → result 선언 직후 (line 84) 로 이동 후 그 직후에 early-exit gate 삽입
  - 게이트 조건: `std::abs(goal->target_angle) < fine_correction_threshold_deg_`
  - 게이트 통과 시: `result->status=0, actual_angle=0, elapsed_time=(now-start_time)` 후 `goal_handle->succeed(result); return;` — 어떤 Phase 도 진입하지 않음 (Phase 0 / 1-3 / 3.5 / 4 모두 skip)
  - 임계값: 기존 `fine_correction_threshold_deg_` 재사용 (yaml `fine_correction_threshold_deg`, default 0.3°) — 새 파라미터 신설 없음
- 변경 분류: L2 (단일 파일 코드 추가)
- Static: `colcon build --packages-select trnav_2ws_action_server --symlink-install` PASS (45.6s, exit 0)
- Smoke Run (SIL — spin node 단독 + `ros2 action send_goal /amr_motion_spin_abstract`):
  - Early-exit case (`target_angle=0.1`): status=0, actual_angle=0, elapsed_time=1.017e-05s, `/motion/wheel_cmd/spin` publish 0회 PASS
  - Regression case (`target_angle=90`): Phase 0 진입, `/motion/wheel_cmd/spin` 20Hz publish 4 window 확인 (IMU 미수신 → -3 timeout 5.0s expected) PASS
- 영향 없음: hpp (멤버 변수 추가 없음) / yaml (기존 키 재사용)
- 관련 이슈: `docs/issues_fixes/issues_and_fixes.md` 2026-05-20 08:36 항목

2026-05-20 / 07:50 - 27f2c16 / 수정: 9 yaml 첫 줄 node name `/amr_*_node:` → `/trnav_*_node:` (launch `name=` 일치)

9개 motion node 의 yaml param scope 가 launch 의 `name='trnav_*_node'` override 와 불일치하여 통째로 무시되던 문제 해소. 사용자가 튜닝한 모든 `translate_*` / `pp_*` / 등 파라미터가 코드 default 로 동작 중이던 systemic mismatch.

- 수정 yaml 9개 (모두 `config/` 하위, 첫 줄 only):
  - `config/translate_forward_params.yaml:1`
  - `config/translate_reverse_params.yaml:1`
  - `config/spin_params.yaml:1`
  - `config/crab_params.yaml:1`
  - `config/turn_params.yaml:1`
  - `config/yaw_control_params.yaml:1`
  - `config/yaw_control_reverse_params.yaml:1`
  - `config/pure_pursuit_params.yaml:1`
  - `config/pure_pursuit_reverse_params.yaml:1`
- executable name (`amr_*_node` in CMakeLists / `executable='amr_*_node'` in launch) 는 변경 없음 — bin name 과 node name 분리
- 빌드 검증: `colcon build --packages-select trnav_2ws_action_server` PASS (3min 8s, exit 0)
- 동작 검증: 사용자 측 — action server 재기동 후 `ros2 param get /trnav_translate_forward_node translate_heading_threshold_deg` → 90.0 (default 45.0 X)
- 관련 이슈: `docs/issues_fixes/issues_and_fixes.md` 2026-05-20 07:50 항목

2026-05-18 / 22:10 - (pending commit) / 수정: 6 action server per-goal `enable_localization_watchdog` override (B patch)

acs_gui Link.enable_localization_watchdog 토글이 .action goal 필드를 거쳐 action server 의 LocalizationMonitor 까지 전달되도록 wiring.

- 수정 cpp `.cpp` 6 개 (각 execute() 진입부 `auto goal = goal_handle->get_goal();` 직후 1 line 추가):
  - `src/translate_forward/translate_forward_action_server.cpp:222`
  - `src/translate_reverse/translate_reverse_action_server.cpp:230`
  - `src/pure_pursuit/pure_pursuit_action_server.cpp:223`
  - `src/pure_pursuit_reverse/pure_pursuit_reverse_action_server.cpp:221`
  - `src/yaw_control/yaw_control_action_server.cpp:136`
  - `src/yaw_control_reverse/yaw_control_reverse_action_server.cpp:137`
  - 패턴: `loc_monitor_->setEnableWatchdog(goal->enable_localization_watchdog && enable_localization_watchdog_);`
  - Effective rule: AND — goal 필드 AND node param 둘 다 true 여야 watchdog 활성 (안전 정책)
- 비변경: spin / crab / turn (loc_monitor 미사용 → 본 patch 무관)
- 비변경: 9 .action 중 spin/crab/turn 3개 (goal 필드 미추가)

검증: `colcon build --packages-up-to trnav_2ws_action_server --symlink-install` PASS (4 packages, 9min 47s).

리뷰: Codex (`/ccg`) — A 수명 / B atomic 순서 / C/F 호출 위치 / G AND 의미 — 모두 OK 판정.

관련 core: `src/Control/AMR-Motion/trnav_2ws_core/docs/amr_motion_core_code_updates.md` [2026-05-18 22:10].
관련 .action: `src/Control/AMR-Motion/trnav_2ws_interfaces/docs/amr_interfaces_code_updates.md` [2026-05-18 22:10].
관련 이슈: `docs/issues_fixes/issues_and_fixes.md` [2026-05-18 22:10] B patch.

---

2026-05-18 / 21:30 - (pending commit) / 수정: 6 action server LocalizationMonitor topic 의존 잔여 제거 (TF-only 정공법 완전 적용)

motion_core 의 LocalizationMonitor topic 의존 폐기 patch (`amr_motion_core_code_updates.md` [2026-05-18 21:30]) 와 짝. action_server 측에서 더 이상 의미 없는 topic 관련 코드 제거.

- 수정 (cpp `.cpp` 6 개):
  - `src/translate_forward/translate_forward_action_server.cpp`
  - `src/translate_reverse/translate_reverse_action_server.cpp`
  - `src/pure_pursuit/pure_pursuit_action_server.cpp`
  - `src/pure_pursuit_reverse/pure_pursuit_reverse_action_server.cpp`
  - `src/yaw_control/yaw_control_action_server.cpp`
  - `src/yaw_control_reverse/yaw_control_reverse_action_server.cpp`
- 각 파일 공통 변경:
  - 생성자 안 `safeParam("*_pose_topic", ...)` + `safeParam("*_pose_qos", ...)` 호출 제거
  - `lm_params.pose_topic = ...` + `lm_params.pose_qos = ...` 할당 제거 (Params 측에서도 제거됨)
  - RCLCPP_INFO initialization 로그에서 `pose_topic=%s, qos=%d` format + 인자 제거, "TF-only" 표기 추가
  - execute() 초입 `if (!loc_monitor_->poseReceived())` 사전 체크 블록 제거 (메서드 자체가 motion_core 에서 제거됨 — 빌드 fail 방지 목적)

빌드: `colcon build --packages-up-to trnav_2ws_action_server --symlink-install` PASS (4 packages, 4min 11s).

검증 grep: `pose_topic|pose_qos|poseReceived|pose_received_|pose_sub_|poseCallback` 잔재 **0건**.

실차 검증 필요: motion 8 server 재기동 후 Run 1차 클릭 → -5 (jump) 재현 안 되는지 + bag 분석으로 정상 케이스/실제 RTAB loop closure 케이스 분리 확인.

관련 core: `src/Control/AMR-Motion/trnav_2ws_core/docs/amr_motion_core_code_updates.md` [2026-05-18 21:30].
관련 이슈: `docs/issues_fixes/issues_and_fixes.md` [2026-05-18 21:30].
관련 mistake: `docs/claude-mistake/2026-05-18.md` [2026-05-18 20:50 KST].

---

2026-05-18 / 16:30 - (pending commit) / 수정: 6 action server `checkLocalizationHealth()` fail 분기 (-4/-5/-6) + .action status 주석 통일

`LocalizationMonitor::getLastFailReason()` (trnav_2ws_core 측 patch 동반) 을 사용해 fail 원인별 status code 반환.

- 수정 (cpp `.cpp` 6 개, 각 2 분기 + include 1):
  - `src/translate_forward/translate_forward_action_server.cpp`
    - line ~414: mid-execute `lookupMapToBase` retry 한도 초과 fail → `-4` → `-6`
    - line ~440: `checkLocalizationHealth()` fail → `-4` 단일 → `getLastFailReason()` 분기 (`-4`/`-5`/`-6`) + reason_str 로그
  - `src/translate_reverse/translate_reverse_action_server.cpp` (동일 2 분기, kDir 인자 보존)
  - `src/pure_pursuit/pure_pursuit_action_server.cpp` (동일 2 분기, pp_out 사용) + `#include "trnav_2ws_core/localization_monitor.hpp"` 추가
  - `src/pure_pursuit_reverse/pure_pursuit_reverse_action_server.cpp` (동일 + include)
  - `src/yaw_control/yaw_control_action_server.cpp` (동일 + include) — feedback 파라미터 (current_distance, calibrated_yaw) 유지
  - `src/yaw_control_reverse/yaw_control_reverse_action_server.cpp` (동일 + include)
- 수정 (.action 6 개, status 주석):
  - `trnav_2ws_interfaces/action/AMRMotionTranslateForward.action`
  - `trnav_2ws_interfaces/action/AMRMotionTranslateReverse.action`
  - `trnav_2ws_interfaces/action/AMRMotionPurePursuit.action`
  - `trnav_2ws_interfaces/action/AMRMotionPurePursuitReverse.action`
  - `trnav_2ws_interfaces/action/AMRMotionYawControl.action`
  - `trnav_2ws_interfaces/action/AMRMotionYawControlReverse.action`
  - 통일 주석: `# 0=success, -1=cancelled, -2=invalid_param, -3=timeout, -4=loc_timeout, -5=loc_jump, -6=tf_lookup_fail`
- 비변경: spin / crab / turn (loc_monitor 미사용) — status 코드 0/-1/-2/-3 유지.
- 미변경 path:
  - init `poseReceived` / init `lookupMapToBase` 실패 (`-3` 유지) — 본 패치는 mid-execute runtime fail 만 대상 (사용자 보고 -4 회귀가 runtime fail)

빌드 검증: `colcon build --packages-up-to trnav_2ws_action_server --symlink-install` PASS (4 packages, 7min, exit 0).

실차 검증 필요: motion 8 server 재기동 후 Run 1차 클릭 → 새 코드 -4/-5/-6 중 어떤게 반환되는지 사용자 확인 필요.

관련 이슈: `docs/issues_fixes/issues_and_fixes.md` [2026-05-18 16:30].
관련 core: `src/Control/AMR-Motion/trnav_2ws_core/docs/amr_motion_core_code_updates.md` [2026-05-18 16:30].

---

2026-05-16 / HH:MM - (pending commit) / 변경: source_id 재할당 (forward-reverse 인접 짝 패턴) — action_server 기본값 + launch 동기

mux yaml source_id 재할당 (`docs/abstraction/motion_source_id_contract.md` SSOT) 에 따라 action_server 기본값 + launch target_source_id 동기 갱신.

- 수정: `include/trnav_2ws_action_server/pure_pursuit/pure_pursuit_action_server.hpp:64` — `motion_source_id_{7}` → `{8}`
- 수정: `src/pure_pursuit/pure_pursuit_action_server.cpp:104` — `safeParam("motion_source_id", 7)` → `8`
- 수정: `include/trnav_2ws_action_server/pure_pursuit_reverse/pure_pursuit_reverse_action_server.hpp:66` — `motion_source_id_{10}` → `{9}`
- 수정: `src/pure_pursuit_reverse/pure_pursuit_reverse_action_server.cpp:101` — `safeParam("motion_source_id", 10)` → `9`
- 수정: `include/trnav_2ws_action_server/yaw_control_reverse/yaw_control_reverse_action_server.hpp:49` — `motion_source_id_{9}` → `{7}`
- 수정: `src/yaw_control_reverse/yaw_control_reverse_action_server.cpp:66` — `safeParam("motion_source_id", 9)` → `7`
- 수정: `launch/hil_pure_pursuit.launch.py:37` — `target_source_id: 7` → `8`
- 수정: `launch/sil_pure_pursuit.launch.py:46` — `target_source_id: 7` → `8`
- 수정: `launch/hil_pure_pursuit_reverse.launch.py:37` — `target_source_id: 10` → `9`
- 수정: `launch/sil_pure_pursuit_reverse.launch.py:45` — `target_source_id: 10` → `9`
- 영향: translate_forward(1) / translate_reverse(2) / spin(3) / crab(4) / turn(5) / yaw_control(6) 의 기본값 변경 없음.

검증: `colcon build --packages-up-to trnav_2ws_action_server` + 각 action_server smoke run 시 `/select_motion_source` 호출 success 확인.

관련 SSOT: `docs/abstraction/motion_source_id_contract.md`.
관련 이슈: `docs/issues_fixes/issues_and_fixes.md` [2026-05-16 source_id 재할당].

---

2026-04-30 / 08:30 - (pending commit) / 수정: pure_pursuit_action_server.cpp — path 연장 fix 적용 (forward, reverse 와 동일)
- `src/pure_pursuit/pure_pursuit_action_server.cpp` (line 224 부근)
  - reverse 와 동일: 마지막 segment tangent 따라 path 를 `lookahead_distance + 0.2m` 만큼 연장 (3 sample)
  - 원래 goal pose / 원래 path 길이 보존, profile decel + stop 판정은 원래 goal 기준
- 검증: HIL 5 시나리오 (HF1~HF5) ALL PASS, 직선 final_hdg=-2.08° / sharp R=1m 90° final_hdg=17.54°
- 관련 이슈: `docs/issues_fixes/issues_and_fixes.md` (2026-04-30 08:30)
- 실험: `experiments/2026-04-30_pure_pursuit_forward_hil/`

---

2026-04-30 / 03:30 - (pending commit) / 수정: pure_pursuit_reverse_action_server.cpp — path 연장 fix (lookahead clamp 결함 해소)
- `src/pure_pursuit_reverse/pure_pursuit_reverse_action_server.cpp` (line 221~270 영역)
  - waypoints 구성 직후: 원래 goal pose + 원래 path 길이 보존
  - 마지막 segment tangent 따라 path 를 `lookahead_distance + 0.2m` 만큼 연장 (3 sample)
  - `pp_ctrl_->setPath(extended_waypoints)` — lookahead 가 path 끝 너머에서도 실제 waypoint 가리킴
  - `target_distance` 는 *원래* 값 — profile decel + stop 판정은 원래 goal 기준 (overshoot 방지)
- 검증: SIL S1/S2/S2b1/S2b2/S3 ALL PASS, final_hdg 6~17× 개선
- 관련 이슈: `docs/issues_fixes/issues_and_fixes.md` (2026-04-30 03:30)
- CCG 토론: `.omc/artifacts/ask/{codex,gemini}-*.md`

---

2026-04-30 / 01:00 - (pending commit) / 추가: hil_pure_pursuit_reverse.launch.py — 후진 PP HIL launch
- `launch/hil_pure_pursuit_reverse.launch.py` (신규)
  - `hil_pure_pursuit.launch.py` 기반, mux source_id=10 (pure_pursuit_reverse)
  - translate_sim_odom 미사용 — 실차 RTAB-Map / IMU / 모터 외부 stack 사용
- 빌드 검증: `colcon build` PASS, install share/launch 확인.
- 실험: `experiments/2026-04-29_pure_pursuit_reverse_hil/` (HR1 = H1 forward arc 역순 후진)

---

2026-04-30 / 00:30 - (pending commit) / 수정: pure_pursuit_reverse_action_server.cpp — rear-steering 매핑 fix (PP delta_f → DualBicycleCommand.delta_r)
- `src/pure_pursuit_reverse/pure_pursuit_reverse_action_server.cpp`
  - line 287~291 (Phase 0 Steer Align): `align_steer_f = pp_first.delta_f` → `align_steer_r = pp_first.delta_f`, `align_steer_f = 0.0`
  - line 437~441 (제어 루프): `DualBicycleCommand{vx, pp_out.delta_f, 0.0}` → `DualBicycleCommand{vx, 0.0, pp_out.delta_f}`
  - 키네마틱 근거: 후진 시 effective front = w2 (robot rear). PurePursuit 의 delta_f 는 effective frame 의 front steer → 실제 wheel 은 w2 (rear steering) 로 보내야 키네마틱 일치
- 검증: SIL S1/S2/S2b1/S2b2/S3 ALL PASS (이전 catastrophic 발산 → e_d_max < 0.07m)
- 관련 이슈: `docs/issues_fixes/issues_and_fixes.md` (2026-04-30 00:30)
- config: `config/pure_pursuit_reverse_params.yaml` — `pure_pursuit_lookahead_distance` 0.6 → 0.4m (1차 SIL S2 fail 분석에서 적용)

---

2026-04-29 / HH:MM - (pending commit) / 추가: hil_pure_pursuit.launch.py — 실차 HIL launch (sim_odom/dummy pub 제거)
- `launch/hil_pure_pursuit.launch.py` (신규)
  - SIL launch 에서 translate_sim_odom / dummy_estop / dummy_lidar 제거
  - 포함: trnav_motion_mux + trnav_motion_supervisor(target_id=7) + amr_safety_watchdog + amr_pure_pursuit_node
  - 실 RTAB-Map, 실 IMU, 실 모터 드라이버가 외부 스택에서 실행된다고 가정
- 빌드 검증: `colcon build --base-paths src --packages-select trnav_2ws_action_server` PASS, `hil_pure_pursuit.launch.py` install 확인.
- 실험: `experiments/2026-04-29_pure_pursuit_hil/`

---

2026-04-29 / HH:MM - (pending commit) / 추가: amr_pure_pursuit_node — nav_msgs/Path 다중 waypoint 추종 (BICYCLE 전륜)
- **PurePursuit** (신규 작성):
  - `include/trnav_2ws_action_server/pure_pursuit/pure_pursuit_action_server.hpp`
  - `src/pure_pursuit/pure_pursuit_action_server.cpp`
  - `src/pure_pursuit/pure_pursuit_main.cpp`
  - 액션: `/amr_motion_pure_pursuit_abstract` (`trnav_2ws_interfaces/action/AMRMotionPurePursuit`)
  - 발행 토픽: `/motion/wheel_cmd/pure_pursuit` (mux source_id=7)
  - 골격: translate_forward 그대로 재사용 (Phase 0/1-3/4, TrapezoidalProfile, TransientGuard, LocalizationMonitor, walk profile, steer-rate, steer-converge, IK)
  - 차이:
    1. 입력 = `nav_msgs/Path` (≥2 poses, frame_id="map") — translate_forward 의 (start_x,...,end_x) 4점 직선 입력 대체
    2. PathController → `PurePursuitController` (lookahead point 기반) 교체
    3. BicycleModel 호출 시 `DualBicycleCommand{vx, delta_f, 0.0}` — 전륜만 조향, δ_r=0 강제
    4. 종료 조건 OR: profile DONE OR projection ≥ target_distance OR `pp_out.remaining_x < goal_reach_threshold` (base_link x 잔여거리)
    5. Phase 0 alignment 목표 = 첫 update 의 `delta_f` (path 시작점 정렬)
    6. Feedback 에 `lookahead_x/y` 추가
- **launch / config**:
  - `launch/pure_pursuit.launch.py` (단일 노드)
  - `launch/sil_pure_pursuit.launch.py` (mux + supervisor target_id=7 + safety + dummy + sim)
  - `config/pure_pursuit_params.yaml` (`pure_pursuit_*` prefix; lookahead_distance=0.6 m default)
- **CMakeLists.txt** — `amr_pure_pursuit_node` 타겟 등록 + `pure_pursuit_controller` 링크 + install 항목 추가

빌드 검증: `colcon build --base-paths src --packages-up-to trnav_2ws_action_server` 4 packages PASS, stderr 0.
설치 확인: `install/trnav_2ws_action_server/lib/trnav_2ws_action_server/amr_pure_pursuit_node` symlink + yaml/launch share 디렉터리 정상.

요청: `docs/request/2026-04-29_pure_pursuit_port.md`
플랜: `docs/plan/2026-04-29_pure_pursuit_implementation.md`

---

2026-04-28 / 19:00 - (pending commit) / 수정: yaw_control_reverse 이중 부호 반전 fix (R1 SIL 1차 발견)
- `src/yaw_control_reverse/yaw_control_reverse_action_server.cpp`:
  - 출력 부호 곱하기 제거 — `vel_f`, `vel_r`, `w1/w2_drive_rpm` 모두 `* kReverseDir(-1)` 삭제
  - `vx_signed = -vx_profile` 입력으로 IK 가 wheel direction 자동 처리 — 추가 부호는 이중 반전
- `include/.../yaw_control_reverse_action_server.hpp`: 차이 주석 정정 ("wheel velocity 출력 부호 반전" 항목 제거)
- 발견 경로: SIL R1 → status=-4 → tf 가 reverse 와 반대 방향 적분 → 부호 분석
- 정정 후 SIL 8/8 PASS

이슈 기록: `docs/issues_fixes/issues_and_fixes.md` ([2026-04-28 19:00])

---

2026-04-28 / 12:00 - (pending commit) / 추가: yaw_control_reverse 노드 (yaw_control 의 reverse 분리, translate_reverse 패턴 미러링)
- **YawControlReverse** (신규 작성):
  - `include/trnav_2ws_action_server/yaw_control_reverse/yaw_control_reverse_action_server.hpp`
  - `src/yaw_control_reverse/yaw_control_reverse_action_server.cpp`
  - `src/yaw_control_reverse/yaw_control_reverse_main.cpp`
  - 액션: `/amr_motion_yaw_control_reverse_abstract` (`trnav_2ws_interfaces/action/AMRMotionYawControlReverse`)
  - 발행 토픽: `/motion/wheel_cmd/yaw_control_reverse`
  - yaw_control 대비 차이 (3가지):
    1. `vx_max` 인터페이스 magnitude(>0), 내부 `vx_signed = -vx_profile`
    2. PID `err_deg = -(target − current)` 항상 부호 반전 (forward 분기 제거)
    3. wheel velocity 출력 `* kReverseDir(-1)` 명시, feedback `current_vx` / `w*_drive_rpm` 항상 ≤ 0
  - effective_yaw 보정 미적용 — translate_reverse 의 `+π` 보정은 PathController(forward 전용) 재사용 trick 인 반면, yaw_control 계열은 IMU yaw 직접 PID 추종이라 불필요.
  - walk velocity profile 도 translate_reverse 와 동일하게 magnitude 기반 비교(가·감속 비대칭 방지)로 작성.
- **launch / config**:
  - `launch/yaw_control_reverse.launch.py`
  - `config/yaw_control_reverse_params.yaml` (`yaw_control_reverse_*` prefix)
- **CMakeLists.txt**:
  - `amr_yaw_control_reverse_node` add_executable + ament_target_dependencies + target_link_libraries (base + bicycle_model + transient_guard + localization_monitor — yaw_control 동일 구성)
  - install(TARGETS) 에 노드 추가

빌드: `colcon build --base-paths src --packages-up-to trnav_2ws_action_server trnav_motion_mux` 5 packages finished, no stderr.
검증:
- `install/trnav_2ws_action_server/lib/trnav_2ws_action_server/amr_yaw_control_reverse_node` 산출물 확인
- `ros2 interface show trnav_2ws_interfaces/action/AMRMotionYawControlReverse` 노출 확인

이슈 기록: `docs/issues_fixes/issues_and_fixes.md` ([2026-04-28 12:00] 항목)
요청: `docs/request/2026-04-28_yaw_control_reverse.md`

---

2026-04-28 / 07:31 - (pending commit) / 추가: Turn (원본 이식) + YawControl (ROS1 개념 신규) 두 노드
- **Turn** (T-Robot ROS2 원본 그대로 이식, 알고리즘 무변경):
  - `include/trnav_2ws_action_server/turn/turn_action_server.hpp`
  - `src/turn/turn_action_server.cpp` (~428 LOC)
  - `src/turn/turn_main.cpp`
  - 변경: namespace `amr_motion_control` → `trnav_2ws_action_server::turn`,
    include `amr_motion_control/...` → `trnav_2ws_action_server/turn/...` + `trnav_2ws_core/...`,
    ActionServerBase 인자 `(node, mutex, "amr_motion_turn")` → `trnav_2ws_core::ActionServerBase<Turn>(node, mutex, "amr_motion_turn_abstract", "/motion/wheel_cmd/turn")`
  - 알고리즘/파라미터/Phase 분할 모두 동일 (라인별 검증)
- **YawControl** (ROS1 개념 + bicycle model + 거리 종료, 신규 작성):
  - `include/trnav_2ws_action_server/yaw_control/yaw_control_action_server.hpp`
  - `src/yaw_control/yaw_control_action_server.cpp` (~558 LOC)
  - `src/yaw_control/yaw_control_main.cpp`
  - PID(yaw error) → steering δ → BicycleModel(vx, δ_f, δ_r) → IK → wheel cmd
  - `counter_steer` bool 분기: false → δ_f=δ, δ_r=0 (전륜만) / true → δ_f=δ, δ_r=-δ (4WS)
  - 시작 1회 `yaw_offset = wrap(start_yaw_map_tf2 - start_yaw_imu)` calibration, 이후 `calibrated_yaw = imu + offset`
  - 거리: `LocalizationMonitor::lookupMapToBase` → 시작 위치 기준 시작 yaw 방향 projection
  - reverse(`vx_max<0`) 시 PID 부호 반전 (ROS1 일치)
  - TrapezoidalProfile + 4-Phase (steer_align / accel-cruise-decel / steer_return)
  - 자체 IMU sub 없음 — base 의 `last_yaw_rad_` atomic 직접 사용
- **launch / config**:
  - `launch/turn.launch.py`, `config/turn_params.yaml`
  - `launch/yaw_control.launch.py`, `config/yaw_control_params.yaml`
- **CMakeLists.txt**:
  - `amr_turn_node`, `amr_yaw_control_node` add_executable + ament_target_dependencies + target_link_libraries (turn = base 만; yaw_control = base + bicycle_model + transient_guard + localization_monitor)
  - install(TARGETS) 에 두 노드 추가
- **중복 정리** (CLAUDE.md 규칙 5):
  - 작성 중 익명 namespace 의 `wrapPi/wrapDeg` 사용 → `trnav_2ws_core::normalizeAngle/normalizeAngleDeg` 재사용으로 교체 (11개 호출 위치)

빌드: `colcon build --packages-up-to trnav_2ws_action_server` 4 packages finished, no stderr (4회 반복).
인터페이스: `ros2 interface list` 에 두 액션 노출 확인.

이슈 기록: `docs/issues_fixes/issues_and_fixes.md` ([2026-04-28 07:31] 항목)
계획: `docs/plan/2026-04-27_turn_yawcontrol_port.md`
요청: `docs/request/2026-04-28_turn_yawcontrol_port.md`

---

2026-04-27 / 21:30 - (pending commit) / 수정: Crab 액션 일반화 (direction_deg)
- `src/crab/crab_action_server.cpp`:
  - 헤더 주석에 일반화 의도 명시 ("body-frame translation, heading maintained (omega=0)").
  - validateGoal 에 `direction_deg ∈ [-180, 180]` 체크 추가, 로그 메시지에 direction 출력.
  - execute() 에 `direction_rad/dir_x/dir_y` 로컬 추가.
  - Phase 0 steer-align IK: `compute({sign·0.1·dir_x, sign·0.1·dir_y, 0})`
  - Phase 1-3 motion IK: `compute({sign·v·dir_x, sign·v·dir_y, 0})` — vx/vy 동시 사용 가능.
  - omega=0 유지 → heading 보존. legacy 사용자(direction_deg=90) 동작 변화 없음.
- `trnav_2ws_interfaces/action/AMRMotionCrab.action` 변경 (별도 패키지지만 본 노드와 한 쌍):
  - `float64 direction_deg 90.0` 필드 추가 (default 90 = legacy lateral 호환).
  - 헤더 주석 "Body-frame translation, heading maintained (omega=0)" 로 갱신.
- 빌드: `colcon build --packages-select trnav_2ws_interfaces trnav_2ws_action_server --symlink-install` (실행 중).
- HIL 자료: `experiments/2026-04-27_crab_hil_real/{README.md, scripts/send_crab_goal.py}` (target=1.0, direction=-30°) — 사용자 시나리오 (전방-우 30° 대각 1m).

참조 결정: `docs/request/2026-04-27_crab_hil.md`, `docs/plan/2026-04-27_crab_hil.md`
이슈 기록: `docs/issues_fixes/issues_and_fixes.md` ([2026-04-27 21:30] 항목)

---

2026-04-27 / 10:20 - (pending commit) / 수정: translate_reverse 기술부채 fix (velProfile lambda + feedback sign)
- `src/translate_reverse/translate_reverse_action_server.cpp`
  - **velProfile lambda magnitude-based fix** (L535-559): 부호 비교 → 절댓값 비교 (`|tgt|>|cur|` 가속 / `|tgt|<|cur|` 감속) + `tgt*cur<0` 분기. reverse(tgt<0) 에서 walk_accel/walk_decel 매핑 swap 버그 해소 (critic CRITICAL). forward 는 vx_profile≥0 이라 기존 lambda 정상 → 미수정.
  - **feedback body-frame sign 일관** (L498-502): `cmd_vy *= kReverseDir`, `cmd_omega *= kReverseDir` 추가. cmd_vx/vy/omega, fb_w*_rpm 모두 reverse 시 음수 일관 (critic IMPORTANT).
- 빌드: `colcon build --packages-select trnav_2ws_action_server --symlink-install` 성공.
- 검증: `experiments/2026-04-27_translate_reverse_split_sil/`
  - 일반 (max=0.2): status=0, dist=1.000, lat=−0.024, hdg=0.81° (회귀 비파괴)
  - stress (max=0.5, accel=1.5): per-cycle ACCEL=−0.500 m/s²(walk_accel), DECEL=+0.934 m/s²(walk_decel) 정확

---
2026-04-27 / 07:43 - (pending commit) / 분할: Translate → Forward + Reverse (대칭 명명)
- `action/AMRMotionTranslate.action` → `action/AMRMotionTranslateForward.action` (rename, `bool reverse` 필드 제거)
- `action/AMRMotionTranslateReverse.action` 신규 (forward 동일 필드)
- `src/translate/` → `src/translate_forward/` rename, namespace `trnav_2ws_action_server::translate_forward`
- `src/translate_reverse/translate_reverse_{action_server,main}.cpp` 신규
  - `effective_yaw = real_yaw + π` 보정 3 곳 (validateInitialPose, main loop, final_pc)
  - `kDir = TravelDirection::REVERSE` PathController.update() 6 곳
  - 입력은 forward kinematics (vx>0), wheel 출력에 `kReverseDir = -1` 곱
- `CMakeLists.txt`: `amr_translate_node` → `amr_translate_forward_node` + `amr_translate_reverse_node` 신규
- `launch/`: `sil_translate.launch.py` → `sil_translate_forward.launch.py` rename + `sil_translate_reverse.launch.py` 신규 (target_source_id: 2)
- `config/`: `translate_params.yaml` → `translate_forward_params.yaml` rename + `translate_reverse_params.yaml` 신규

---
2026-04-26 / 20:45 - (pending commit) / 추가: Crab 파일럿 — amr_crab_node (lateral translation, heading 유지)
- `include/trnav_2ws_action_server/crab/crab_action_server.hpp`
  - `trnav_2ws_core::ActionServerBase<AMRMotionCrab>` 상속, namespace `trnav_2ws_action_server::crab`
  - 파라미터 멤버: `min_speed_mps_`, `settling_delay_ms_`, `crab_max_timeout_sec_`
- `src/crab/crab_action_server.cpp` (원본 `amr_motion_control::CrabActionServer` 이식)
  - ActionServerBase 초기화: `"amr_motion_crab_abstract"` + `"/motion/wheel_cmd/crab"` (4-arg ctor)
  - 헤더 주석 (의도적 open-loop 명시): "Spin uses IMU yaw feedback for completion; Translate uses localization pose. Crab is INTENTIONALLY open-loop on lateral distance — accumulated_distance is integrated from the commanded wheel-IK output (v_mps * dt)."
  - **변경점 (timeout 강화)**: Phase 1-3 루프에 `crab_max_timeout_sec` 글로벌 timeout 가드 추가 (spin 패턴 미러, 원본 미존재).
  - **변경점 (drive_rpm)**: 원본 `float32 → float64` 메시지 타입 통일. 발행 값은 magnitude 유지 (translate 와 동일).
  - Phase 0 steer-align → Phase 1-3 TrapezoidalProfile + IK(`compute({0, sign*v, 0})`) → settling → Phase 4 steer-return 원본 흐름 유지.
- `src/crab/crab_main.cpp` (spin_main 동형, 노드명 `amr_crab_node`)
- `launch/crab.launch.py` + `config/crab_params.yaml`
  - crab-specific: `crab_min_speed_mps: 0.005`, `settling_delay_ms: 200`, `crab_max_timeout_sec: 60.0`
  - 공통 (spin 미러): platform/geometry/control_rate_hz/steer_tolerance_deg/steer_timeout_sec
- `CMakeLists.txt`:
  - `amr_crab_node` executable 추가 (link: `inverse_kinematics`, `motion_profile`, `wheel_set_packer` — translate 와 달리 bicycle/path/transient/loc 미사용)
  - install TARGETS 에 `amr_crab_node` 포함

빌드 검증: `colcon build --packages-select trnav_2ws_interfaces trnav_2ws_action_server trnav_motion_mux --symlink-install` 성공 (2min 10s, 경고 없음).
사전 단계: stale build symlink 충돌(trnav_2ws_interfaces) → `rm -rf build/trnav_2ws_interfaces install/trnav_2ws_interfaces` 후 재빌드.

런타임 확인:
- action `/amr_motion_crab_abstract` (server `/amr_crab_node`)
- topic publish `/motion/wheel_cmd/crab` → mux subscribe (Subscription count: 1)
- mux 검증: `Registered source id=4 name=crab`, Config validation passed.

참조 원본: `/home/tc/T-Robot_nav_ros2_ws/src/Control/AMR-Motion-Control/amr_motion_control/src/crab_action_server.{hpp,cpp}`
요청 기록: `docs/request/2026-04-26_crab_motion_connection.md`
이슈 기록: `docs/issues_fixes/issues_and_fixes.md` ([2026-04-26 20:45] 항목)

---

2026-04-24 / 08:45 - (pending commit) / 추가: Translate Wave 4 — amr_translate_node 파일럿
- `include/trnav_2ws_action_server/translate/translate_action_server.hpp`
  - `trnav_2ws_core::ActionServerBase<AMRMotionTranslate>` 상속
  - 모듈 unique_ptr: `BicycleModel`, `PathController`, `TransientGuard`, `LocalizationMonitor`
  - Path viz (`nav_msgs::Path`) + Debug (`std_msgs::Float64MultiArray`) publisher
- `src/translate/translate_action_server.cpp` (원본 `amr_motion_control::TranslateActionServer` 이식)
  - ActionServerBase 초기화: `"amr_motion_translate_abstract"` + `"/motion/wheel_cmd/translate"`
  - default_mode_ = `ControlMode::BICYCLE` 고정 (Wave 4 범위)
  - validateGoal: `goal->control_mode` 가 0 또는 1 외면 reject (Mode 2/3 은 후속 Wave)
  - Phase 0 (steer align) / Phase 1-3 (TrapezoidalProfile + PathController + TransientGuard + LocalizationMonitor) / Phase 4 (steer return) 원본 로직 유지
  - **변경점 (Safety 제거)**: 원본의 `tc_msgs::SafetyStatus`/`/safety/speed_limit` 구독 및 execute 내 safety block 제거 (Q1 결정)
  - **변경점 (VY_OMEGA 제거)**: execute 내 `if (local_mode != ControlMode::VY_OMEGA)` 분기의 else 삭제. PathController BICYCLE 축소판과 정합. `steer_converge_scale`, actual-steer-based IK 블록은 항상 적용.
- `src/translate/translate_main.cpp` (spin_main 동형)
- `launch/translate.launch.py` + `config/translate_params.yaml`
  - translate-specific 파라미터 + robot geometry 공통 + TransientGuard/LocalizationMonitor 파라미터 포함
  - `translate_control_mode: 1` (BICYCLE)
- `CMakeLists.txt`:
  - find_package 에 `geometry_msgs`, `nav_msgs`, `tf2_ros` 추가
  - `amr_translate_node` executable 추가 (link: bicycle_model, path_controller, transient_guard, localization_monitor, + 기존 inverse_kinematics/motion_profile/wheel_set_packer)
  - install TARGETS 에 `amr_translate_node` 포함
- `package.xml` — `geometry_msgs`, `nav_msgs`, `tf2_ros` depend 추가

빌드 검증: `colcon build --packages-select trnav_2ws_action_server` 성공 (46.8s, 경고 없음).
`amr_spin_node`, `amr_translate_node` executable 정상 설치.

런타임 확인 (launch 기동 후 `ros2 action/topic list`):
- action `/amr_motion_translate_abstract`
- topic `/motion/wheel_cmd/translate`, `/translate_debug`, `/translate_path`

참조 원본: `/home/tc/T-Robot_nav_ros2_ws/src/Control/AMR-Motion-Control/amr_motion_control/src/translate_action_server.{hpp,cpp}`
계획: `docs/plan/2026-04-24_amr_translate_port.md`
결정 기록: `docs/request/2026-04-24_amr_translate_port.md`
