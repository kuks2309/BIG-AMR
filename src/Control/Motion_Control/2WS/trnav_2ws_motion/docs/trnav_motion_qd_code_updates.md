# trnav_2ws_motion — code updates

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
- 수정 `include/…/qd_wheel_set_packer.hpp`·`src/qd_wheel_set_packer.cpp` — 「neither is present in this
  repository」·「its in-repo trace is …code_updates.md」 등 감사 흔적 안내 제거. 남긴 것은 이 packer 가
  QD_DIAGONAL 2륜 pack 만 담당한다는 사실과 분리 근거(ADR-012) 인용.
- 수정 `include/…/qd_mpc_controller.hpp` — 클래스 설명이 실제 최적화 대상·반환 의미와 어긋난 부분 정정.
- 수정 `package.xml` — rosdep 키 표기 `nlopt` → **`libnlopt-dev`**. `rosdep resolve nlopt` 는 규칙이 없어 실패하며,
  바로 다음 줄이 선언하는 실제 키가 `libnlopt-dev` 다. 주석대로 되돌리면 `rosdep install` 이 깨진다.

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
- 수정 `include/…/qd_action_server_base.hpp` — `/motion/last_result` 종료 코드 목록에 실제로 발행되는
  **-7 heading_divergence · -8 steer_unreachable · -9 final_yaw_tolerance** 추가(yaw_control 계열 전용).
- 수정 `include/…/qd_path_controller.hpp` — `e_d` 부호 규약 반전 정정: `+ 경로 좌측` → `+ 로봇이 경로 우측`
  (`qd_path_controller.cpp:101` 의 `rx*uy_ - ry*ux_` 는 표준 좌측양수 cross-track 의 부호 반대).
- 수정 `include/…/qd_wheel_set_packer.hpp`·`src/qd_wheel_set_packer.cpp` — `wheels[0]=W1(전-좌)/[1]=W2(후-우)`
  → `(앞)/(뒤)`(정본 기하는 두 바퀴 모두 y=0); 부재 패키지 `trnav_motion_dd` 를 「이 저장소에 없음」으로 명시.
- 수정 `CMakeLists.txt`·`package.xml` — 부재 경로 `src/Control/Kinematics/` 정정, 존재하지 않는 클래스명
  (`PathController`·`MpcController`·`WheelSetPacker`) → 실제 `TwoWs*` 이름.

---

2026-07-26 / 12:3x - (pending) / **Big-AMR 이식 — NLopt rosdep 의존 명시** (ADR 2026-07-26-qd-motion-port)

- 수정 `package.xml` — `<depend>nlopt</depend>` 추가. 원본은 `qd_mpc_controller.cpp` 의 MPC SLSQP 솔버가 NLopt(`find_library(nlopt)`)를 쓰면서도 rosdep 미선언 → Big-AMR(Jetson/Humble)에서 `libnlopt` 부재로 configure 실패(`Could not find NLOPT_LIB`). rosdep key `nlopt`(→ libnlopt-cxx-dev/libnlopt-dev) 선언으로 보완.
- 동작·로직 무변경(선언만). 설치: `sudo apt-get install -y libnlopt-cxx-dev libnlopt-dev`(Ubuntu 22.04 2.7.1). 검증: colcon build error 0 / `amr_mpc_node` 등 9종 노드 링크 성공.

2026-07-04 / 09:52 - (pending) / **운동학 3종 분리 이동** (AD-012 개정) — `trnav_2ws_kinematics` 신설

- **삭제(이동)** `include/trnav_2ws_motion/{qd_inverse_kinematics,qd_crab_inverse_kinematics,qd_bicycle_model}.hpp` + `src/{동일 3종}.cpp` → `src/Control/Kinematics/trnav_2ws_kinematics/` (`git mv`)
- 수정 `CMakeLists.txt` — 3 add_library 블록·install 항목 제거, `find_package(trnav_2ws_kinematics)` + `ament_export_dependencies(trnav_2ws_kinematics)` 추가
- 수정 `package.xml` — `<depend>trnav_2ws_kinematics</depend>` 추가 + description 갱신
- 수정 `include/trnav_2ws_motion/qd_action_server_base.hpp:7` — IK include 경로 `trnav_2ws_kinematics/` 로
- 기록: `docs/request/2026-07-04_qd_kinematics_move.md`, AD-012 개정 (`docs/abstraction/architecture_decisions.md`)

2026-05-28 / HH:MM - (pending commit) / **PP → MPC controller 교체 (Phase B)** — kinematic bicycle MPC 신설 + PP/RPP library 제거

- **추가** `include/trnav_2ws_motion/qd_mpc_controller.hpp` + `src/qd_mpc_controller.cpp` — `trnav::motion::two_ws::MpcController` (NLopt SLSQP, kinematic bicycle, horizon N=10, dt=0.1s, receding horizon, cost = `w_lat·lat² + w_hdg·hdg² + w_du·Δδ² + w_goal·goal_dist²`, finite-diff gradient)
  - params: `wheelbase`, `max_delta_rad`, `max_lateral_offset`, `w_lat=100`, `w_hdg=5`, `w_du=0.5`, `w_goal=20`, `N=10`, `dt_mpc=0.1`
  - I/O: `MpcPose{x,y,yaw}` waypoints (path orientation 직접 사용), `MpcOutput{e_d, e_theta, delta_f}` (헬퍼 출력 closest_seg/projection 등은 caller 측에서 별도 계산)
- **삭제** `include/trnav_2ws_motion/qd_pure_pursuit_controller.hpp` + `src/qd_pure_pursuit_controller.cpp` — PP 본체 (옛 lookahead 기반 추종)
- **삭제** `include/trnav_2ws_motion/qd_regulated_pure_pursuit_controller.hpp` + `src/qd_regulated_pure_pursuit_controller.cpp` — RPP (nav2 fork, 5/26 시도 후 폐기. final approach lookahead clamp 발산)
- **삭제** `test/pure_pursuit_unit_test.cpp` — PP/RPP/MPC 3-way standalone test. MPC 비교 자료는 [`experiments/2026-05-26_pp_rpp_mpc_unit_test/`](../../../../experiments/2026-05-26_pp_rpp_mpc_unit_test/README.md) 로 이전
- **수정** `CMakeLists.txt:73-84,100-111,128-143,145-159`:
  - `add_library(qd_pure_pursuit_controller)` 블록 삭제
  - `add_library(qd_regulated_pure_pursuit_controller)` 블록 삭제
  - `add_executable(pure_pursuit_unit_test) + install(TARGETS pure_pursuit_unit_test)` 블록 삭제
  - `add_library(qd_mpc_controller)` 블록 유지 (NLopt link, 신설)
  - `install(TARGETS …)` 목록에서 PP/RPP 제거, `qd_mpc_controller` 유지

검증: `colcon build --packages-select trnav_2ws_motion` 1.66s PASS. 의존 패키지 `trnav_2ws_action_server` 8.33s PASS.

알고리즘 SIL 결과 (5/26 비교): HF5 R=1m 90° arc 종점 hdg **MPC 0.22° vs PP 4.96° (20× 우위)**, HF1~HF5 + JAGGED 모두 MPC PASS. PP→MPC 채택 결정 근거.

2026-05-26 / 17:00 - (pending commit) / **변경**: `TwoWsCrabIK` state-aware 분리 (Phase 0 결정 → cruise clamp)

- 인터페이스: `setInitial(initial_base_steer, initial_walk_dir)` 추가. `isInitialized()` 조회.
- `compute()` 동작:
  - **initialized 시 (cruise)**: base_raw = theta_body + delta_cte. initial 과 차이 |diff|>π/2 면 base_raw ± π wrap 으로 initial 영역 (|diff|≤π/2) 으로 옮김. 그 후 ±25° clamp. walk dir = initial_walk_dir 고정 (wrap 없음).
  - **미초기화 시 (Phase 0 fallback)**: 기존 ±π/2+25° wrap (legacy).
- 사용자 의도 정공법 구현: "1단계 (Phase 0) 가 부호 결정 → 2단계 (cruise) 는 그 안에서 ±25° 변화".
- 사유: Phase 0 (DualSteerIK ±π/2 strict) 와 cruise (TwoWsCrabIK ±π/2+25°) 가 stateless 독립 wrap → boundary 영역 (theta_body=+90.8° 등) 에서 부호 충돌. 사용자 ACS L4 (path +90°) 진행 시 robot 정반대 방향 진행 (status 0 SUCCESS but 의도 반대) 으로 발견.
- 검증: to_n3_stateaware (path_yaw=+130°, theta_body=+130.5°) — Phase 0 -49.5° → setInitial(-49.5°, -1) → cruise wheel -49.5° 일관, final_heading_error +0.206°, final_lateral +12.8mm SUCCESS ✓.
- 관련: [docs/issues_fixes/issues_and_fixes.md](../../../../../docs/issues_fixes/issues_and_fixes.md) [2026-05-26 17:00], [amr_motion_action_server_code_updates.md](../../trnav_2ws_action_server/docs/amr_motion_action_server_code_updates.md).

---

2026-05-25 / 22:30 - (pending commit) / **변경**: `TwoWsCrabIK` 인터페이스 확장 (delta_heading rear-steer) + ±90° wrap 마진 25° (boundary 진동 회피)

- **인터페이스 확장** (`include/trnav_2ws_motion/qd_crab_inverse_kinematics.hpp`):
  - `compute(vx_path, theta_body, delta_cte, delta_heading=0.0)` 4번째 인자 추가
  - rear wheel (dir>0: W2, dir<0: W1) 만 `rear = base - delta_heading` offset 적용
  - 양 휠 base/dir 별도 wrap 처리 (front_dir/rear_dir 독립). w2_is_rear 판정은 wrap 후 front_dir 기준.
- **부호 정공법** (`src/qd_crab_inverse_kinematics.cpp`):
  - 1차 시뮬에서 walk dir wrap flip effect 누락 → 실차 -45° abort (status=-4) 로 발견
  - 정정: `rear = base - delta_heading` (front_dir 무관). yaw_err>0 (CCW 필요) → δ_h>0 → rear<base → ω+CCW. wrap 후 walk dir flip 이 ω 부호 자동 정정.
- **WRAP_MARGIN = 25°** (2026-05-25 22:30): wrap threshold ±π/2 → ±π/2+25° 마진. 사유: theta_body 가 ±90° 정확히 boundary 시 delta_cte 미세 진동 → wrap on/off 토글 → walk dir flip → cmd_vel +/- 진동 → robot CRAB 중 후퇴/진동. HIL 9 bag 분석 cruise max ±6.21° → 25° 마진 안전마진 19° 잉여.
- **검증**: HIL 다수 시나리오 PASS — N2↔N3 (+89°), recover→N3 (+131°), N3→N1 (-135°), spin+crab -90°, target_yaw 10°/-10° heading PD, ACS Run All test7.json L4 (boundary 정확히 +90°). 양 휠 대칭 max F-R diff 15° (heading PD saturate ±15° case).

---

2026-05-24 / 22:00 - (pending commit) / **신규 추가**: `TwoWsCrabIK` 클래스 (CRAB linear 전용 IK, DualSteerIK 의 ±90° normalize edge 회피)

- 신규 파일: `include/trnav_2ws_motion/qd_crab_inverse_kinematics.hpp` + `src/qd_crab_inverse_kinematics.cpp`
- 인터페이스: `TwoWsCrabIK(num_wheels, wheel_radius, gear_walk)` + `compute(vx_path, theta_body, delta_cte) → IKResult`
- 차이점 (vs `TwoWsDualSteerIK::computeWheel`): `atan2(vy,vx)` + `±90° normalize` 없음. wheel_steer = `theta_body + delta_cte` 직접 출력, walk direction = sign(vx_path) 고정. 양 휠 동일 출력.
- 적용 영역: CRAB sideways (path_yaw - robot_yaw ≈ ±90°) — DualSteerIK 가 `|angle|>π/2` 에서 wrap + direction flip 하여 wheel steer 가 +89° ↔ -89° 점프하는 edge effect 제거.
- CMakeLists: lib `qd_crab_inverse_kinematics` 추가 (link to `qd_inverse_kinematics`) + install + EXPORT.
- 검증: bag 시뮬레이션 (`experiments/2026-05-24_crab_linear_hil_real/verify_crab_ik.py`) — DualSteerIK steer span 180° → TwoWsCrabIK 7.4°, direction flips 46.4% → 0%.
- 관련: [docs/issues_fixes/issues_and_fixes.md](../../../../../docs/issues_fixes/issues_and_fixes.md) [2026-05-24 22:00].

---

2026-05-21 / 22:30 - (pending commit) / **신규 패키지 생성** (ADR-012 QD/DD layer 분리)

QD diagonal platform 전용 라이브러리 패키지. 기존 `trnav_2ws_core` 의 platform-specific 코드 (BICYCLE kinematics 기반) 를 본 패키지로 이전 + 식별자 3중 prefix 적용.

### 패키지 구조

```
trnav_2ws_motion/
├── package.xml                 (depend: trnav_2ws_core, trnav_2ws_msgs, rclcpp, geometry_msgs, sensor_msgs, std_msgs)
├── CMakeLists.txt              (5 library target + ament_export_targets)
├── include/trnav_2ws_motion/
│   ├── qd_inverse_kinematics.hpp           (TwoWsDualSteerIK + WheelPosition, VelocityCommand, WheelOutput, IKResult struct)
│   ├── qd_bicycle_model.hpp                (TwoWsBicycleModel + BicycleCommand, DualBicycleCommand, BicycleState struct)
│   ├── qd_path_controller.hpp              (TwoWsPathController + ControlMode, TravelDirection enum, PathControlOutput struct)
│   ├── qd_pure_pursuit_controller.hpp      (TwoWsPurePursuitController + PurePursuitOutput struct)
│   ├── qd_wheel_set_packer.hpp             (TwoWsWheelSetPacker)
│   └── qd_action_server_base.hpp           (header-only template: TwoWsActionServerBase<ActionT>)
├── src/
│   ├── qd_inverse_kinematics.cpp
│   ├── qd_bicycle_model.cpp
│   ├── qd_path_controller.cpp
│   ├── qd_pure_pursuit_controller.cpp
│   └── qd_wheel_set_packer.cpp
└── docs/
    └── trnav_2ws_motion_code_updates.md     (본 파일)
```

### 식별자 정책

- **namespace**: `trnav::motion::two_ws` (C++17 nested namespace)
- **클래스명 prefix**: `TwoWs*` (PascalCase) — `TwoWsDualSteerIK`, `TwoWsBicycleModel`, `TwoWsPathController`, `TwoWsPurePursuitController`, `TwoWsWheelSetPacker`, `TwoWsActionServerBase<T>`
- **파일명 prefix**: `qd_*.{cpp,hpp}`
- **CMake target prefix**: `qd_*` — 5 library
- **struct/enum 무 prefix**: namespace 내에서 식별 — `WheelPosition`, `VelocityCommand`, `BicycleCommand`, `ControlMode`, `TravelDirection`, `PathControlOutput`, `PurePursuitOutput` 등
- **method/멤버 무 prefix**: 클래스명 + namespace 가 이미 식별자 — C 스타일 메서드 prefix 회피

### Cross-package 의존

- `trnav_2ws_core::RecursiveMovingAverage`: `qd_path_controller`, `qd_pure_pursuit_controller` 가 fully qualified 사용
- `trnav_2ws_core::normalizeAngle` (math_utils): `qd_path_controller.cpp`, `qd_pure_pursuit_controller.cpp` 가 호출
- `trnav_2ws_core::RobotGeometry`, `::Platform`, `::parsePlatform`: `qd_wheel_set_packer`, `qd_action_server_base` 가 사용
- `trnav_2ws_core::ActionMutex`: `qd_action_server_base` 가 사용

### CMake target

| target | 종류 | 의존 |
|---|---|---|
| `qd_inverse_kinematics` | STATIC library | trnav_2ws_core (헤더만) |
| `qd_bicycle_model` | STATIC library | qd_inverse_kinematics (link) + trnav_2ws_core (헤더만) |
| `qd_path_controller` | STATIC library | trnav_2ws_core (헤더만 — RMA + math_utils) |
| `qd_pure_pursuit_controller` | STATIC library | trnav_2ws_core (헤더만) |
| `qd_wheel_set_packer` | STATIC library | trnav_2ws_msgs (target dep) + trnav_2ws_core (헤더만) |
| `qd_action_server_base.hpp` | header-only template | install(DIRECTORY include/) — consumer 가 위 5 target link 시 자동 포함 |

### CMake keyword/plain form 충돌 회피

`ament_target_dependencies` 는 내부적으로 **plain-form** `target_link_libraries` 사용. 본 패키지의 `target_link_libraries(qd_bicycle_model qd_inverse_kinematics)` 라인은 plain form 으로 작성 (PUBLIC keyword 사용 시 CMake error "All uses of target_link_libraries with a target must be either all-keyword or all-plain.")

### 빌드 검증

`colcon build --packages-select trnav_2ws_motion --symlink-install` PASS, 3.78s (4 패키지 통합 빌드 시).

### 관련

- 요청 기록: `docs/request/2026-05-21_qd_dd_layer_separation.md`
- ADR: `docs/abstraction/architecture_decisions.md` AD-012
- 인덱스: `docs/abstraction/package_index.md` Motion Library Layer
- consumer 측 변경: `src/Control/AMR-Motion/trnav_2ws_action_server/docs/amr_motion_action_server_code_updates.md` [2026-05-21 22:30]
- 이슈: `docs/issues_fixes/issues_and_fixes.md` [2026-05-21 22:30]
