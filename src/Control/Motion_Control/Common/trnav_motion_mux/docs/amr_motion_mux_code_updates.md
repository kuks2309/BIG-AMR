# trnav_motion_mux — code updates

2026-07-13 / 14:00 - c8f2e9f / **new_motor_stack.launch.py params 경로 버그 수정** (선재 버그)

- **수정** `launch/new_motor_stack.launch.py:46-52` — `amr_motor_cmd_translator` 노드 params 경로:
  `amr_motor_cmd_translator.yaml` (**존재하지 않는 파일**) → `amr_motor_cmd_translator_qd.yaml` (실제 파일명)
- **추가** 동 위치 재발 방지 코멘트.

**영향**: ROS2 launch 는 없는 params 파일을 **에러 없이 조용히 skip** → `amr_motor_cmd_translator` 가 그동안 계속 **코드 기본값으로만** 동작했다 (`platform`, `gear_steer`, `direction_*` 등 yaml 값 전부 미적용). 코드 기본값이 yaml 과 대부분 일치해 증상이 드러나지 않다가, 조향 영점 오프셋(신규 파라미터) 이 안 먹혀서 발각.

**검증**: `colcon build --packages-select trnav_motion_mux` PASS → install launch/yaml 존재 확인 → 모터 스택 재기동 → `ros2 param get /amr_motor_cmd_translator steer_offset_front_deg` = `-1.676` **로딩 확인**.

일반화: **launch params 경로는 `ros2 param get` 으로 로딩 사후 검증 의무** (launch 성공 ≠ params 적용).

---

2026-05-28 / HH:MM - (pending commit) / **PP → MPC 마이그레이션 (Phase B)** — source_8/9 name + topic rename

- **수정** `config/trnav_motion_mux.yaml` source_8 + source_9 블록:
  - source_8: name `"pure_pursuit"` → `"mpc"`, topic `"/motion/wheel_cmd/pure_pursuit"` → `"/motion/wheel_cmd/mpc"`
  - source_9: name `"pure_pursuit_reverse"` → `"mpc_reverse"`, topic `"/motion/wheel_cmd/pure_pursuit_reverse"` → `"/motion/wheel_cmd/mpc_reverse"`
- **수정** `config/trnav_motion_mux.yaml:99-100` (source_8) + `:103-105` (source_9) + Reserved IDs 표 코멘트 (line 16/17/20) — `mpc_action_server` (NLopt SLSQP) 발행 표기
- **수정** `config/trnav_motion_mux.yaml:108,116` — Stanley 예약 블록 코멘트 (`pure_pursuit 대안` → `mpc 대안`, `pure_pursuit_reverse 패턴` → `mpc_reverse 패턴`)
- **수정** `src/trnav_motion_mux_node.cpp` Reserved name table V-16/V-17: `id=8 → "mpc"`, `id=9 → "mpc_reverse"` (FATAL 검증 의미 동일, 알고리즘 PP → MPC 만 교체)

매핑 의미 그대로 (source_id 8/9 슬롯, forward/reverse 짝 인접). controller 알고리즘만 PP → MPC (NLopt SLSQP) 교체. `colcon build --packages-select trnav_motion_mux` PASS.

---

2026-05-21 / HH:MM - (pending commit) / 변경: source_4 name `crab`→`crab_linear`, topic `/motion/wheel_cmd/crab`→`/motion/wheel_cmd/crab_linear` (slot 재사용)

기존 crab (open-loop 적분) 폐기 + crab_linear (target_yaw 능동 유지 + start↔end 직선 closed-loop) 단일 교체. source_id=4 슬롯 재사용. 매핑 변경 0건 (forward/reverse 짝 패턴 무영향).

- 수정 yaml 1개:
  - `config/trnav_motion_mux.yaml:12` Reserved IDs 표 4행 코멘트 `crab → crab_linear`
  - `config/trnav_motion_mux.yaml:55-61` source_4 블록 name / topic / 코멘트
- 영향: 다른 패키지 1 (acs_gui run_tab.py:1350 bag topic), Link.msg 코멘트 2 hunk
- 관련 SSOT: `docs/abstraction/motion_source_id_contract.md` (4행 갱신)
- 관련 plan: [docs/plan/2026-05-20_crab_linear_action_implementation.md](../../../../../docs/plan/2026-05-20_crab_linear_action_implementation.md)

---

2026-05-16 / HH:MM - (pending commit) / 변경: source_id 재할당 (forward-reverse 인접 짝 패턴) + spin(3) 활성화 + V-* 검증 SSOT 단일화

- `config/trnav_motion_mux.yaml`:
  - `source_ids: [0, 1, 2, 4, 5, 6, 7, 9, 10]` → `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]` (spin 3 활성화, 매핑 재할당)
  - `source_7` name "pure_pursuit" → "yaw_control_reverse" (이전 source_9 내용 이동)
  - `source_8` name "stanley(예약)" → "pure_pursuit" (이전 source_7 내용 이동)
  - `source_9` name "yaw_control_reverse" → "pure_pursuit_reverse" (이전 source_10 내용 이동)
  - `source_10` name "pure_pursuit_reverse" → "stanley(예약, 미구현)" (이전 source_8 내용 이동)
  - `source_11` (신규) — stanley_reverse 예약 슬롯 추가 (짝 패턴 일관성)
  - 헤더 주석의 Reserved IDs 표 12-row 신규 매핑 + 짝 패턴 명시
- `src/trnav_motion_mux_node.cpp`:
  - `kReservedRules` 12-row 상수 매핑 (uint8_t id / name / rule_id) 신규 추가 — docs/abstraction/motion_source_id_contract.md SSOT mirror
  - `validateSources()` 의 V-01/V-02/V-04/V-11 4개 하드코딩 if 블록 → `kReservedRules` 순회 단일 if 블록으로 통합
  - V-11 의 의미 변경 (옛 id=7→pure_pursuit, 신 id=7→yaw_control_reverse)
  - 신규 rule ID 발급: V-12(spin) / V-13(crab) / V-14(turn) / V-15(yaw_control) / V-16(pure_pursuit, id=8) / V-17(pure_pursuit_reverse, id=9) / V-18(stanley, id=10 예약) / V-19(stanley_reverse, id=11 예약) — 모든 Reserved name 검증 SSOT 통합
- 영향: 다른 패키지 (action_server hpp/cpp 6 파일 + launch 4 파일) source_id 동기 변경. ACS GUI 측 source_id 직접 참조 없음 (영향 없음).

검증: `colcon build --packages-up-to trnav_motion_mux trnav_motion_action_server` + `colcon test --packages-select trnav_motion_mux` (V-01/V-02/V-04/V-05/V-06/V-07/V-08/V-10 launch_test stderr "V-XX" match 검증 통과 — 메시지 형식 (`"V-XX: Reserved id=N must have name='X'"`) 보존).

관련 SSOT: `docs/abstraction/motion_source_id_contract.md` (신규).
관련 이슈: `docs/issues_fixes/issues_and_fixes.md` [2026-05-16 source_id 재할당].

---

2026-04-29 / HH:MM - (pending commit) / 추가: pure_pursuit(7) source 활성화 + V-11 가드
- `config/trnav_motion_mux.yaml`:
  - `source_ids: [0, 1, 2, 4, 5, 6, 9]` → `[0, 1, 2, 4, 5, 6, 7, 9]` (pure_pursuit 활성화)
  - `source_7` block 신규 정의 — name="pure_pursuit", topic="/motion/wheel_cmd/pure_pursuit", timeout_ms=200
  - 코멘트 ID 매핑 갱신: `7 = pure_pursuit` 활성 항목 추가, 후속 예약 코멘트에서 7 제거 (8=stanley 만 남김)
- `src/trnav_motion_mux_node.cpp`:
  - V-11 가드 신규 — `id=7 ⇒ name="pure_pursuit"` 강제 (V-04 다음 위치, V-03 폐지 코멘트 위)
  - 잘못된 이름으로 source_7 설정 시 FATAL + `runtime_error("V-11: id=7 must be 'pure_pursuit'")`

빌드 검증: `colcon build --base-paths src --packages-select trnav_motion_mux` PASS.
Naming disambiguation 표 (`docs/abstraction/naming_disambiguation.md`) row 7: 예약 → 활성 (2026-04-29, V-11 가드).

요청: `docs/request/2026-04-29_pure_pursuit_port.md`
플랜: `docs/plan/2026-04-29_pure_pursuit_implementation.md`

---

2026-04-28 / 12:00 - (pending commit) / 추가: yaw_control_reverse(9) source 등록
- `config/trnav_motion_mux.yaml`:
  - `source_ids: [0, 1, 2, 4, 5, 6]` → `[0, 1, 2, 4, 5, 6, 9]` (yaw_control_reverse 활성화)
  - `source_9` block 신규 정의 — name="yaw_control_reverse", topic="/motion/wheel_cmd/yaw_control_reverse", timeout_ms=200
  - 코멘트 ID 매핑 갱신: `9 = yaw_control_reverse` 활성 항목 추가
  - 후속 예약 코멘트 (7=pure_pursuit, 8=stanley) 유지
- `src/trnav_motion_mux_node.cpp`: 변경 없음 (정책상 yaml 정의만으로 등록)

빌드: `colcon build --base-paths src --packages-select trnav_motion_mux` 성공.
검증: `install/trnav_motion_mux/share/trnav_motion_mux/config/trnav_motion_mux.yaml` 에 source_9 반영 확인.

영향: amr_yaw_control_reverse_node 가 발행하는 wheel_cmd 가 mux 통과 후 `/motor/wheel_cmd` 로 라우팅 가능해짐.

이슈 기록: `docs/issues_fixes/issues_and_fixes.md` ([2026-04-28 12:00] 항목)
요청: `docs/request/2026-04-28_yaw_control_reverse.md`

---

2026-04-28 / 07:31 - (pending commit) / 추가: turn(5) + yaw_control(6) source 등록 + stanley(8) 후속 예약
- `config/trnav_motion_mux.yaml`:
  - `source_ids: [0, 1, 2, 4]` → `[0, 1, 2, 4, 5, 6]` (turn + yaw_control 활성화)
  - `source_5` block 신규 정의 — name="turn", topic="/motion/wheel_cmd/turn", timeout_ms=200
  - `source_6` block 신규 정의 — name="yaw_control", topic="/motion/wheel_cmd/yaw_control", timeout_ms=200
  - 코멘트 ID 매핑 갱신: `5 = turn`, `6 = yaw_control` 활성 항목 추가
  - 후속 예약 코멘트: `8 = stanley` (lateral control 향후 개발) 신규 항목, `7 = pure_pursuit` 유지
- `src/trnav_motion_mux_node.cpp`: 변경 없음 (정책상 yaml 정의만으로 등록 — V-XX hard-code 게이트는 추가하지 않음)

빌드: `colcon build --packages-select trnav_motion_mux` 성공 (pytest 미설치 경고만 — 무관).
검증: `install/.../config/trnav_motion_mux.yaml` 에 source_ids/source_5/source_6 반영 확인.

영향: amr_turn_node, amr_yaw_control_node 가 발행하는 wheel_cmd 가 mux 통과 후 `/motor/wheel_cmd` 로 라우팅 가능해짐.

이슈 기록: `docs/issues_fixes/issues_and_fixes.md` ([2026-04-28 07:31] 항목)
요청 출처: 사용자 인터뷰 ("yaw_control 6번, stanley 8번 배정하고 mux에 등록해주세요")

---
2026-04-27 / 10:20 - (pending commit) / 정리: V-03 dead code 제거
- `src/trnav_motion_mux_node.cpp` (L125-131): `if (false && id == 2) { RCLCPP_FATAL(...); rclcpp::shutdown(); throw ...; }` 5 줄 dead block 제거 → 단일 주석 1 줄로 폐지 사실 명시.
- 동기: id=2 영구예약 정책 폐지 후 V-04 (id=2 = translate_reverse) 로 재할당. 비활성 분기가 코드 의도 흐림 + 미래 정적 분석 잡음 (critic WARN).
- 동작 변화 없음 (`if (false && ...)` 는 항상 미실행). 빌드 회귀 검증 완료.

---
2026-04-27 / 07:43 - (pending commit) / 수정: V-02/V-04 룰 갱신 — translate_forward/reverse 분리 반영
- `src/trnav_motion_mux_node.cpp`:
  - V-02: `id=1 → name="translate"` → `name="translate_forward"`
  - V-04 신규: `id=2 → name="translate_reverse"`
- `config/trnav_motion_mux.yaml`:
  - source_ids: `[0, 1, 4]` → `[0, 1, 2, 4]`
  - source_1.name: `"translate"` → `"translate_forward"`, topic: `/motion/wheel_cmd/translate_forward`
  - source_2 신규: `name="translate_reverse"`, topic `/motion/wheel_cmd/translate_reverse`, timeout_ms=200
  - 주석 갱신: V-03 폐지, source_2 재할당 사실
- 빌드 + 런타임 검증: 4 source 등록 (joystick/translate_forward/translate_reverse/crab) 정상.
