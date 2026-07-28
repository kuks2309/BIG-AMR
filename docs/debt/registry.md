# 부채 registry (Debt Registry)

기술·이해·의도 부채의 등록·추적. **항목은 append, 해결도 기록(덮어쓰기 금지).** 코드 마커는 여기 `id` 를 참조한다 (`# TODO(debt-001): ...`).

> ⚠ **[2026-07-27 감사] 위 문장("코드 마커는 여기 `id` 를 참조한다")은 현재 성립하지 않는다 — id 공간이 충돌 상태다.**
> 저장소 안에서 최소 3개 번호대가 서로 독립적으로 `debt-00N` 을 쓰고 있으며, 여기 표의 id 와 일치하지 않는다.
> 마커를 보고 이 표를 찾아가면 **무관한 항목에 도달한다.** 문장 자체는 이력 보존을 위해 지우지 않는다.
> 아래 「id 충돌 목록」과 각 항목의 정정 표기를 먼저 읽을 것. 번호 재배정·마커 수정은 각 소유 영역의 별도 작업으로 남긴다(여기서 id·값을 바꾸지 않는다).

| id | 유형 | 위치 | 사유 | 식별일 | 상태 | 상환계획 |
| --- | --- | --- | --- | --- | --- | --- |
| debt-001 | 기술 | (예시) src/foo.py:42 | 임시 하드코딩 상수 | 2026-01-01 | 미해결 | 설정 파일로 이전 |
| debt-008 | 이해 | `References/Tongyi-Motor-Controller/manuals/IxLII-IxLs-IxH_Servo_Driver_Handbook_V7.0.pdf` 인쇄쪽 197(PDF 199) ↔ 인쇄쪽 116 | **1차 source 내부 충돌** — Appendix I `0x6000` 은 `Bit0-Bit3 = DI0-DI3 input status, default value (0xBF)` 라 하고, §4.6 Home 1/2 설명은 드라이브가 `the limit input (**DI4/DI2**)` 를 원점으로 취급한다고 한다. 즉 `0x6000` 비트가 가리키는 DI 번호와 리밋 배선 DI 번호가 문서상 불일치. 우리 결론(bit3=−Limit)은 실측으로 뒷받침되나 **왜 그런지는 미설명** | 2026-07-28 | 미해결 | 벤더 문의 또는 DI 배선 실측(각 DI 핀에 신호 주입 후 `0x6000` sub1 비트 변화 관측)으로 매핑 확정. 그 전까지 DI 번호 기반 서술 금지 |
| debt-009 | 이해 | `Log/homing_capture_220350.jsonl` · `docs/debt/registry.md:111-112` | **캡처 출처·연속성 미확정** — (1) `t=5.1558`~`17.7762` 의 **12.62 초 슬레이브 전면 무응답 구간**이 있는데 기존 기록은 180 초 연속 관측으로 읽힌다. 그 구간 마스터는 node1/2 에 `0x6040=0x86`(Bit7 Fault Reset rising edge)을 ≈120 ms 주기로 반복 발행. (2) `phase` 필드가 253,510 프레임 **전건 `baseline`** 이고 파일명이 `orin_homing_capture.py` 의 epoch 규칙과 달라 **그 스크립트 산출물이 아닐 수 있다**. 공백이 의도적 CAN2 단절인지 드라이브 침묵인지 원자료로는 판정 불가 | 2026-07-28 | 미해결 | 동일 조건 재캡처(스크립트 경로·인자·`phase` 라벨 보존)로 공백 재현 여부 확인. 재현되면 원인 규명, 아니면 본 캡처를 '출처 불명 1회 관측'으로 격하 표기. 관련 §E-9 `docs/verified_facts/2026-07-28-errata.md` |
| debt-002 | 기술 | src/Sensors/IMU/iahrs_driver_ros2/iahrs_driver/launch/iahrs_driver.py:44 → **⚠ 2026-07-27 정정: :40(마커)·:45(값)**. `:44` 는 `name='static_tf_base_to_imu',` 줄이고, 코드측 마커는 `:40` `# TODO(debt-002): (-0.37, 0, 0.29) 는 TR-AMR 실측값 — Big-AMR 실장착 위치로 재측정·수정 필요.`, 부채 대상 값은 `:45` `arguments=['--x', '-0.37', '--y', '0', '--z', '0.29',` 이다(값 변경 없음, 위치 표기만 정정) | base_link→imu_link static TF 마운트값 (-0.37, 0, 0.29)이 TR-AMR 실측값 — Big-AMR 차체와 다름. 이식 시 원본 그대로 가져옴(bit-identical) | 2026-07-26 | 미해결 | Big-AMR 실제 IMU 장착 위치 실측 후 arguments(--x/--y/--z, 필요시 회전) 갱신. 사용자 나중에 입력 예정 |
| debt-003 | 이해 | src/Actuators/motor_control/motor_control/backend.py:272-300 | freewheel servo-off(0x6040=0x05)를 1회만 assert하고 Node Guarding RTR은 계속 폴링 — 드라이브가 guarding 활동으로 서보를 조용히 재-enable/재기동하지 않는다는 가정이 코드로 확인 불가(HW/펌웨어 거동). ADR은 실측 §8 "무재초기화 재개" 인용하나 벤치 미확인 | 2026-07-26 | 미해결 | 실 Tongyi 드라이브 벤치: freewheel 유지 동안 서보가 Switch-On-Disabled 유지·노드 alive 확인. 조용히 재-enable되면 `fw_active` 중 주기적 `CW_DISABLE` 재-assert 추가 |
| debt-004 | 이해 | src/Actuators/motor_control/config/tongyi_amr.yaml:15 `kin_steer_sign: 1  # ⚠ 가정` | 조향 counts 증가가 물리적으로 CCW(+θ)인지 CW(−θ)인지 미확정. 두 실측(홈 raw음수=전진 / +90°counts+raw양수=좌)은 **CW 일 때 정합**하므로 `kin_steer_sign=-1` 이 시사되나 직접 관측으로 확인되지 않았다. 영향 범위는 `driver_node` 의 twist→모듈 변환·오도메트리 경로이며, raw 언어로 직접 지령하는 `Tools/amr_test_gui` 는 무관 | 2026-07-27 | 미해결 | 잭업 상태에서 조향 +90° counts 지령 후 바퀴 회전방향을 육안 확인(CCW/CW) → `kin_steer_sign` 확정하고 config 주석의 `⚠ 가정` 해제. 확정 전까지 `driver_node` 의 crab/스핀 twist 사용 금지 |
| debt-005 | 기술 | Tools/amr_test_gui/amr_test_gui/panda_can_bus.py | `TongyiSdoBackend` + `PandaCanBus` 통합 경로가 relay 경유 실구동으로 검증된 적 없음(어댑터 작성만). backend 브링업(선판독·init 시퀀스)이 intercept 중 판다 read 로 정상 완주하는지 미확인 | 2026-07-27 | 미해결 | ADR 검증계단 ①dry-run → ②잭업 조향만 순서로 실행하고 결과를 docs/issues_and_fixes/issues_and_fixes.md 에 기록. 브링업 실패 시 선판독 재시도/타임아웃 파라미터 조정 |
| debt-006 | 이해 | Tools/amr_test_gui/amr_test_gui/panda_can_bus.py:send | 판다는 RTR 송신 불가라 backend 의 Node Guarding RTR(20 Hz)을 skip 한다. intercept 중 Seer 의 guard RTR 이 게이트로 forward 되어 모터의 GuardTime(500 ms)×LifeFactor(1) 감시를 대신 만족시킨다는 가정이 코드로 확인 불가 | 2026-07-27 | 미해결 | 잭업 상태에서 intercept 유지 5분 이상 구동하며 노드 HALT 미발생·`snapshot()` last_seen 갱신 지속 확인. HALT 발생 시 펌웨어에 PC-요청 guard RTR 생성 경로 추가 검토 |
| debt-007 | 이해 | src/Actuators/motor_control/config/tongyi_amr.yaml:79-91 (`steer_home_counts: [7871815, 7840086]`) | **미판정 모순 — 조향 홈 counts 의 기준계.** 원문 인용(`tongyi_amr.yaml:79-88`): 「⚠ 미해소 모순 (2026-07-27 관측, debt-007) … 설계 근거(design-inputs.md 「부팅 시 0x6064≈0 이 정상」·「매 기동 시 +137.3° 스윙 필요」)대로면 아래 값은 **절대 목표**다. 그런데 2026-07-27 21:1x 관측에서, Seer 가 이미 기동·호밍을 마치고(1040 position≈0·calib=True) 육안으로도 바퀴가 직진인 상태인데 **판다 read 0x6064 는 ≈0** 이었다. 설계대로라면 그 시점 raw 는 ≈7.87M 이어야 한다. → 둘 중 하나가 틀렸다: **(a)** 판다의 조향 0x6064 read 가 오염됐다 **(b)** 호밍 후 드라이브가 위치 기준을 0 으로 재설정한다(= 아래 값은 기동 전에만 유효). 같은 시점 구동 노드는 판다 read 와 Seer 1040 이 절댓값 일치했다(조향만 어긋남). 미판정 상태이므로 어느 쪽으로도 값을 고치지 않는다」. **본 registry 는 (a)/(b) 어느 쪽도 판정하지 않는다.** → ⚠ **정정 (2026-07-27, 실기 검증)**: 이 문장은 이력 보존을 위해 남기되 더 이상 현재 상태가 아니다 — `Log/homing_capture_220350.jsonl` 로 **(b) 는 「기준이 0 으로 남는다」형태로 반증**, **신규 가설 (c)**(호밍 진행 중 `0x6041` bit15=0 구간에서 `0x6064` 가 정확히 0 고정, 3,080/3,080 샘플) **실증**, **(a) 는 미반증**. 상세는 아래 「[2026-07-27 실기 검증] debt-007 부분 판정」 §①. 안전 직결(조향 홈)이며 다수 코드가 이 id 를 안전 게이트로 참조 중: `src/Actuators/motor_control/motor_control/backend.py:43,235,244,248` · `driver_node.py:75-76` · `Tools/amr_test_gui/amr_test_gui/constants.py:18-19,48` · `controller.py:60,77` · `modes.py:93-94,102` · `Tools/docking_field_kit/docking_drive.py:73` · `amap2_monitor.py:73`. 참조는 2026-07-27 이전부터 있었으나 **본 표에는 미등록**이었다(`docs/code_review/motor_control-can-consistency/2026-07-26.md:55`, `src/Actuators/motor_control/docs/code_review/motor_control-can-consistency/2026-07-26.md:50` 이 "미등록·등록 필요"로 지적) — 2026-07-27 감사에서 등록 | 2026-07-27 | 미해결(미판정) → **⚠ 2026-07-27 실기 검증: 부분 판정**(가설 (c) 신규 확정 · (b) 「기준이 0 으로 남는다」형태 반증 · (a) 미반증). 원 상태 표기는 이력 보존, 상세는 아래 「[2026-07-27 실기 검증] debt-007 부분 판정」 절 | ① Seer 호밍 완료·바퀴 육안 직진 상태에서 조향 노드 `0x6064` 를 (i) 판다 read 와 (ii) Seer 1040 position 으로 **동시 취득**해 절댓값 일치 여부 확인(구동 노드는 이미 일치 관측됨 — `tongyi_amr.yaml:87`). ② 조향 **임의 자세에서 전원 재투입** 후 `0x6064` 재현성 확인(`docs/ros2_driver/2026-07-09-design-inputs.md:139` 이 「0 기준점이 절대 엔코더 기준인지 미확인 — 2회 전원 사이클 관측뿐」으로 남겨둔 항목). ③ 판정 결과를 본 행에 append(값은 실측 없이 변경 금지). **판정 전까지 `allow_homing_motion` 게이트를 끄지 말 것**(`tongyi_amr.yaml:89-90`). ④ ⚠ **2026-07-27 실기 검증 append** — 상환계획 ①②의 핵심 측정이 `Log/homing_capture_220350.jsonl`(Seer 주도 호밍 180 s 수동청취, 253,510 프레임)로 **부분 수행**됐다. 결과·잔여 과제·게이트 근거 정정은 아래 「[2026-07-27 실기 검증] debt-007 부분 판정」 절 참조. **게이트를 끄지 말라는 지시 자체는 계속 유효하나, 그 근거 서술은 정정됐다**(⇒ 같은 절 ③). ⚠ 줄번호: 인용된 `tongyi_amr.yaml:89-90`(사용 규칙)은 2026-07-27 정정 append 로 현재 **`:107-108`** 이며 `allow_homing_motion` 키 자체는 **`:33`** 이다(값 변화 없음). 같은 이유로 위 위치·인용의 `tongyi_amr.yaml:79-91`/`:79-88`(원문 모순 블록)은 현재 **`:97-129`**, `steer_home_counts` 키는 **`:130`** 이다. 인용이 어긋나면 키 문자열로 찾을 것. |

<!-- 새 부채는 위 표에 행 추가. 유형: 기술 / 이해 / 의도. 상태: 미해결 / 해결(해결일·커밋 병기). -->

## [2026-07-27 감사] id 충돌 목록 (append — 삭제 금지)

아래는 **본 표의 id 와 다른 대상을 가리키는** `debt-00N` 마커·인용이다. 최소 3개 번호대가 독립적으로 쓰인다:
(A) 본 registry, (B) CAN-Relay 계열(`Tools/Can_Relay`, `Tools/firmware`, `Tools/docking_field_kit`, `docs/can_relay`),
(C) 카메라 캘리브 계열(`Tools/CameraCalibration`). **여기서 번호를 재배정하지 않는다**(각 소유 영역의 별도 작업).

⚠ 줄번호 주의: 다른 문서·주석들은 본 표를 `registry.md:8`(debt-002)·`:9`(debt-003)·`:10`(debt-004) 로 인용하지만,
2026-07-27 감사에서 머리말 경고를 append 하면서 각각 **`:13`·`:14`·`:15`** 로 이동했다(내용 변화 없음). 인용이 어긋나면 id 문자열로 찾을 것.

| id | 본 registry 의 뜻 | 충돌하는 다른 용법 (파일:줄) |
| --- | --- | --- |
| debt-002 | IMU base_link→imu_link static TF 마운트값 (본 표 `:13` 행) | (B) `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:1,4,7` = intercept **전환 커버** · `Tools/firmware/cover/safety_seer_gate.h:1,4,7` (동일) · `docs/can_relay/field-record-orin-nx-2026-07-25.md:92,103,113` = **전환 글리치** · `Tools/docking_field_kit/orin_hold_intercept.py:2`·`orin_debt002_char.py:2`·`orin_termcheck.py:2` (동일 계열) / (C) `Tools/CameraCalibration/calib_intrinsics.py:158` `TODO(debt-002)` = 캘리브 **dropped=0 오도 보고** |
| debt-003 | backend.py freewheel servo-off 가정 (본 표 `:14` 행) | (B) `docs/can_relay/field-record-orin-nx-2026-07-25.md:92,105` = **게이트 누출 원인** · `Tools/docking_field_kit/docking_drive.py:88-89` 및 `amap2_monitor.py:155,176,193-197,312` (해당 파일들은 이미 「원 주석의 debt-003 은 원 프로젝트(CAN-Relay) 번호이며 본 저장소 registry.md:9 와 다른 항목」이라고 자체 정정 표기함) / (C) `Tools/CameraCalibration/calib_intrinsics.py:205` `TODO(debt-003)` = **부트스트랩 이중 수행** |
| debt-004 | `kin_steer_sign` 미확정 (본 표 `:15` 행) | (B) `docs/can_relay/field-record-orin-nx-2026-07-25.md:109` 「debt-004 신규」 = docking_drive **heartbeat USB 경합**(같은 줄이 「이 저장소 registry.md:10 의 debt-004 와 다른 항목」이라 자체 정정) / (C) `Tools/CameraCalibration/test_calib_intrinsics.py:296` `TODO(debt-004)` = **과적합 벌점 미입증** |

`docs/can_relay/field-record-orin-nx-2026-07-25.md:95-96` 도 같은 충돌을 이미 기록한다 —
「본 §11·§12(:104 "debt-004 신규")의 id 로 이 저장소를 추적하면 **무관한 항목에 도달한다.**
이 기록이 다른 저장소(CAN-Relay)의 registry 를 지칭했을 가능성이 높다」.
(⚠ 그 줄이 인용한 `:104` 는 현재 파일에서 `:109` 다 — 줄번호가 이동했으므로 문자열로 찾을 것.)

### 미등록 사항 (id 미배정 — 소유 영역에서 등록 필요)

- `module_x` 전/후 배정이 실측과 반대라는 🔴HIGH 지적: `docs/code_review/motor_control-can-consistency/2026-07-26.md:59`
  (「🔴 HIGH — 모듈 전/후(module_x) 노드 배정 반전 (실측 데이터와 정면 모순)」, 권고 :68, 미적용 사유 :116)
  및 `src/Actuators/motor_control/config/tongyi_amr.yaml:75-77`(「판정 측정 … 부채 registry.md 에 module_x 항목
  미등록 — 등록 필요」). 본 감사에서는 **id 를 새로 배정하지 않았다**(어느 번호가 안전한지 위 충돌 상태에서
  단정할 수 없음). 등록 시 위 충돌 목록을 먼저 해소할 것.

- ⚠ **[2026-07-27 실기 검증 추가] 브링업이 조건 없이 전 범위 재호밍을 개시한다.**
  `backend._write_init_sequence`(`src/Actuators/motor_control/motor_control/backend.py:362`, `:368`)가
  `0x6099=2500`(HOMING_SPEED) 과 `0x60FB.4=1`(RstStart, 호밍 개시 트리거 [Handbook V7.0 §6.9, page 171])을
  **조향 위치·게이트와 무관하게 무조건** 송신한다. 따라서 조향이 홈에 정확히 있는 상태로 기동해도
  매번 −리밋 탐색(≈31.1 s) + 조향 0° 복귀(≈3.2 s) 전 범위 재호밍이 일어난다.
  `_gate_homing_motion`(`backend.py:283`, 판정 `:305`)은 `0x6064` ↔ `steer_home_counts` **이탈만** 보므로
  이 경로를 덮지 못한다. 근거: `Log/homing_capture_220350.jsonl` t=17.9252/17.9257 `0x60FB.4=1`
  (본 감사 전수 디코드로 재확인 — 캡처 180 s 중 해당 write 는 이 2 건뿐).
  본 감사는 **id 를 배정하지 않았다**(위 충돌 상태). 등록 시 위 충돌 목록을 먼저 해소할 것.
  ※ 이 항목은 **동작 결함 주장이 아니다** — 재호밍 자체는 설계된 동작이다(아래 §③).
    등록 대상은 「게이트 문구가 이 경로를 막는 것처럼 읽힌다」는 서술·설계 부채다.

- ⚠ **[2026-07-28 이관] `drive_sign: -1` 라벨 상충 — 미판정.**
  실측 확정 주장: `docs/ros2_driver/2026-07-09-design-inputs.md` §3 「부호 관례(실측): **전진 = N1·N2 모두 음(−)**」 ·
  `Tools/docking_field_kit/docking_drive.py` `self._vel = {1: -s, 2: -s}   # 전진=음(실측)` ·
  `docs/claude-mistake/2026-07-27-003_sign-contradiction-false-claim.md:21,38`(확정 방향을 "미검증"으로 격하한 것이 실수라고 closed).
  미검증 표기 쪽: `docs/code_review/motor_control/2026-07-26.md:188` 「| drive_sign / kin_steer_sign | int | -1 / 1 ⚠ | 부호(미검증) |」.
  ⇒ **어느 쪽으로도 단정 금지**('미검증'으로의 격하도 단정이다).
  판정 측정: 잭업 또는 ≤0.05 m/s 에서 조향 홈 고정 후 raw 음수 지령 → 차체 이동방향(+x 여부) 1회 관측·기록.

- ⚠ **[2026-07-28 이관] `track_width: 1.2` 는 좌우 트랙폭이 아니라 휠베이스다** (값 변경 금지).
  근거: `module_x` 합 0.5961+0.6039 = 1.200 이고 `module_y` 는 두 바퀴 동일 ⇒ 좌우 이격 0(인라인 센터라인) ·
  `robot_geometry_2ws.yaml:55` 「wheelbase = 0.6039 + 0.5961 = 1.200 m (tongyi_amr.yaml track_width: 1.2)」 ·
  `trnav_2ws_kinematics/docs/trnav_qd_kinematics_code_updates.md:8` 「실물 Foil_A082 = inline 센터라인 2 조향휠」.
  그런데 `kinematics.py` 의 `DiffDriveKinematics` 는 이 값을 좌우 이격으로 쓴다 —
  `twist_to_modules` 의 `vl = vx - wz * self.track_width / 2.0` / `vr = vx + wz * self.track_width / 2.0`,
  `modules_to_twist` 의 `return ((vl + vr) / 2.0, 0.0, (vr - vl) / self.track_width)` 이고
  `DiffDriveKinematics(drive_nodes[0], drive_nodes[1], ...)` 로 좌/우를 배정한다(노드 1·2 는 좌/우가 아니라 전/후).
  ⇒ `kinematics: "diff_drive"` 로 전환하면 인라인 차체에 좌우 차동 모델이 적용된다. **검증 전 사용 금지.**

- ⚠ **[2026-07-28 이관] `can_channel` 관련 2건.**
  ① '단독 마스터' 는 채널의 성질이 아니라 **매 기동 전 운전자 전제**다 — ⓐ Seer 마스터 분리 ⓑ 동일 버스상 다른 live CAN 노드(판다 relay 등) 부재 확인.
  근거: `src/Actuators/motor_control/README.md` §⚠ 안전 절차 1항 · `design-inputs.md` §6 ROS2 아키텍처 마지막 불릿.
  ② 버스는 250 kbps 고정(`design-inputs.md` §1 버스·노드 표)이나 **본 config 는 비트레이트를 설정하지 않는다** — OS `ip link` 의존
  (`docs/code_review/motor_control-can-consistency/2026-07-26.md:88-91` 🟡LOW).
  위험 실례: `docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md:52`(250 kbps 버스에 500 kbps live 노드 직결 → 버스 파괴. 같은 ADR :3,:9-10 에 `can_speed = 2500U` 로 수정·플래시 완료 기록).

- ⚠ **[2026-07-28 정정] 위 「브링업이 조건 없이 전 범위 재호밍을 개시한다」 항목은 미판정으로 격하한다.**
  `_write_init_sequence()` 안의 해당 write 는 2026-07-27 편집에서 **주석 처리**됐다 —
  「종전: `P.sdo_write(n, P.OBJ_VENDOR_60FB, 1, size=1, sub=0x04)`」, `grep -n OBJ_VENDOR_60FB backend.py` 는 주석만 반환(실행 코드 0건).
  반면 같은 파일의 `_gate_homing_motion()` docstring·운전자 예외 메시지는 여전히 「조건 없이 송신」이라 적는다. **어느 쪽으로도 단정 금지.**
  판정 측정: 잭업 상태에서 브링업 1회 실행 후 can1 candump 에 `0x60FB sub4` write 프레임이 실재하는지 확인.

- ⚠ **[2026-07-28 이관] `module_x` 항목 보강**(위 🔴HIGH 지적과 동일 대상).
  하류 기록끼리도 불일치라 **미판정**이다 — 현재 배열과 같은 편: `robot_geometry_2ws.yaml:37,39`(w1_x 0.6039=Front=node2 / w2_x −0.5961=Rear=node1, 단 같은 파일 :36 이 스스로 「미판정 모순」 표기) ·
  `Tools/Kinematics/chassis_kinematics.py:50` `KIN_NODE_XY = {1: (-0.5961, -0.0014), 2: (+0.6039, -0.0014)}`(단 :33 이 「노드 매핑은 SPIN 부호 정합에서 도출한 **가정**」이라 밝힘).
  반대편(node1=Front): `References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md` §1 canID config · `design-inputs.md` §1 버스·노드 표 · `Tools/amr_test_gui/amr_test_gui/constants.py:62-64`.
  영향 경로: `driver_node` 의 `self.node_xy` → `DualSteerKinematics` 모멘트암 → 스핀/크랩/오도메트리 yaw 부호(직진 등속에서는 미노출).
  **확정 전까지 스핀/크랩 twist 사용 금지.** 판정 측정: ① 잭업 또는 ≤0.05 m/s 에서 wz>0 스핀 지령 후 IMU yaw 부호와 전/후 모듈 실제 이동방향 관측 ② node1/node3 이 물리적으로 차체 앞쪽인지 육안·배선 확인.

- ⚠ **[2026-07-28 이관] `steer_home_counts` 동일 기본값이 `driver_node.py` 의 `declare_parameters` 에도 하드코딩**돼 있다
  (`("steer_home_counts", [7871815, 7840086]),`) — 값 변경 시 함께 다뤄야 한다. 값 자체의 판정은 debt-007 · `docs/verified_facts/2026-07-27.md` §B-1 참조.
  덧붙임: config 값과 호밍 후 정착 목표의 차(node3 +10,205 = +0.178° / node4 +18,976 = +0.331° @57,344 counts/°)는
  `homing_tol_deg` 5°(286,720 counts)·`steer_settle_tol_deg` 3°(172,032 counts) 어느 게이트도 검출하지 못하는 **영구 미검출 오프셋**이다.

## [2026-07-27 실기 검증] debt-007 부분 판정 (append — 삭제 금지)

위 표 debt-007 행의 「미해결(미판정)」·상환계획 ①②에 대한 **부분 판정**이다.
행의 counts 값·상태 원문은 이력 보존을 위해 그대로 두고 결과만 여기에 append 한다.
**본 절은 값을 바꾸지 않는다**(값 변경은 실차 재측정·승인 사안).

**근거**: `Log/homing_capture_220350.jsonl` — 2026-07-27 22:03, Seer 주도 호밍을 판다로 **수동청취만** 한
180 s 캡처(253,510 프레임, 판다는 송신 없음). 아래 수치는 본 감사에서 SDO 응답을 전수 디코드해 재확인했다.

### ① `0x6064 = 0` 의 정체 — 가설 (c) 신규 확정, (b) 부분 반증

원문 인용(위 행): 「→ 둘 중 하나가 틀렸다: **(a)** 판다의 조향 0x6064 read 가 오염됐다
**(b)** 호밍 후 드라이브가 위치 기준을 0 으로 재설정한다(= 아래 값은 기동 전에만 유효)」.

⚠ **정정 (2026-07-27): 이 이지선다는 불완전하다. 후보는 셋이다.**

- **(c) 〈신규·실증〉 호밍 진행 중(`0x6041` bit15 = 0)에는 드라이브가 `0x6064` 를 정확히 0 으로 보고한다.**
  - `0x6041` bit15 = 0 **최초 관측**: t=17.9562(node3) / 17.9567(node4). ⚠ 전이 시각이 아니다 — 직전 폴이
    t=5.1383/5.1387 이고 그 사이 폴 0건이라 1→0 은 구간 (5.138, 17.956] 안에서만 확정된다.
    0→1 복귀: t=49.0795(node3) / 48.9993(node4).
  - `0x6064` = 0 구간: node3 t=17.9302~49.1781 / node4 t=17.9308~49.1781, 각 **3,115 샘플**.
    구간 내부(t=18.0~48.9) **3,080 샘플 전수 0, nonzero 0 건**(양 노드 동일).
  - 같은 구간에 축은 물리적으로 이동 중이었다 — 음(−) 리밋 물림 `0x6000.1` bit3 0→1 @ t=47.0249(node3)/47.0254(node4).
  - ⇒ 21:1x 의 「Seer 호밍 완료·육안 직진인데 판다 read ≈0」 관측은 **판다 오염을 가정하지 않고도** 설명된다.
- **(b) 는 「기준이 0 으로 남는다」는 형태로는 반증됐다.** 호밍 완료 후 `0x6064` 는 0 에 머물지 않고
  t≈49.18~52.4 에 램프한 뒤 t=180 까지 유지된다 — 실측 정착 **node3 7,882,001~7,882,008 /
  node4 7,859,058~7,859,065**(t≥100 구간 min/max). 캡처 시작 시점 baseline 은 이미 홈 부근이었다:
  t=0.0343 `0x6064` = node3 **7,871,818** / node4 **7,840,084**(= 본 표 `steer_home_counts` 와 정합).
  ⇒ 「부팅 시 `0x6064`≈0 이 정상」이라는 전제도 이 캡처에서는 성립하지 않는다.
- **(a) 는 미반증.** 본 캡처는 수동청취라 판다 자신의 SDO read 응답을 검사하지 못한다.
  21:1x 의 intercept **보유** 상태는 재현되지 않았다.

⇒ **판정 절차 필수 추가: `0x6064` 를 읽을 때 같은 시각의 `0x6041` bit15 를 반드시 함께 취득할 것.**
bit15 를 보지 않으면 (c) 와 (a)/(b) 를 원리적으로 구분할 수 없다.

### ② 호밍 트리거·완료 조건 (상환계획 ①의 전제 확정)

Seer 실측 개시 시퀀스(조향 node3/4 에만 송신, 구동 node1/2 에는 **호밍 프레임 없음**):

| 단계 | 오브젝트 | 시각(node3 / node4) |
| --- | --- | --- |
| fault reset (+enable voltage) | `0x6040 = 0x86` | 17.9102 / 17.9107 |
|   ⚠ `0x86` = Bit1(Enable voltage) + Bit2(Quick stop) + Bit7(**Fault Reset**, rising edge). Bit0(Switch On)=0 · Bit3(Enable Operation)=0 이므로 **`Enable Operation`(=0x0F)이 아니다** [Handbook 인쇄쪽 150 / PDF 152 controlword 표]. 종전 'enable' 라벨은 오기 | | |
| 호밍 속도 | `0x6099 = 2500` (0.1 r/min ⇒ 250 rpm) | 17.9183 / 17.9188 |
| **호밍 개시** | `0x60FB.4 = 1` (**RstStart**, 0=Reset off / 1=Reset on) | **17.9252 / 17.9257** |
| 탐색 중 | `0x6041` bit15 = 0, `0x6064` = 0 | ≤17.956 ~ 49.0 (시작 상한만 확정) |
| −리밋 물림 | `0x6000.1` bit3 0→1 | 47.0249 / 47.0254 |
| 완료 | `0x6041` bit15 0→1 | 49.0795 / 48.9993 |
| 조향 0° 복귀 지령 | `0x607A` = **7,882,020 / 7,859,062**, `0x6040=0x3F` | 49.1402 / 49.1416 |
| 리밋 해제 | `0x6000.1` bit3 1→0 (복귀 이동 중) | 49.4223 / 49.4227 |

- `0x60FB.4` 의 의미는 더 이상 미상이 아니다 — **RstStart(호밍 개시)** [Handbook V7.0 §6.9, page 171
  "0-Reset off, 1-Reset on"]. 이 write 는 **모터를 물리적으로 움직인다.**
- `0x6098`(homing method)은 캡처 전 구간에서 **write·read 0 건**이다 → 드라이브 저장값을 쓴다.
  별도 실기 판독에서 전 조향 노드 `0x6098 = 1` = **Home 1(음의 리밋 트리거)** 로 확인됐다.
  ⇒ **조향축에 리밋 스위치가 실재한다.** 「Home 36/37 기계 하드스톱(리밋 없음)」류 서술은 오류다.
  ⚠ Home 35 를 쓰면 RstMode 가 0(호밍 꺼짐)으로 리셋되므로(§4.6 page 122) 타사 코드를 그대로 베끼지 말 것.
- **구동축(node 1·2)은 호밍하지 않는다** — 기계적 원점이 없다. 본 절의 판정은 조향 노드에 한정된다.

### ③ 「`allow_homing_motion` 게이트를 끄지 말 것」의 **근거** 정정 (지시 자체는 유효)

⚠ **정정 (2026-07-27)**: 위 행/`tongyi_amr.yaml` 의 「그 게이트가 이 불일치를 잡아내는 **방어선**」이라는
서술은 성립하지 않는다.

- 게이트(`backend._gate_homing_motion`, `backend.py:283` / 판정 `:305`)가 실제로 검출하는 것은
  `0x6064` 가 `steer_home_counts` 에서 이탈했는지뿐이다. 게이트를 **통과해도**
  `_write_init_sequence`(`backend.py:362`, `:368`)가 `0x6099` + `0x60FB.4=1` 을 조건 없이 송신하므로
  전 범위 재호밍은 그대로 일어난다(→ 위 「미등록 사항」의 신규 항목).
- 또한 게이트의 원 근거였던 **「콜드부팅 137° 조향 스윙 = 위험한 미지 거동」 전제는 반증됐다.**
  그 스윙은 호밍 완료 후 원점(음 리밋)에서 **조향 0° 로 복귀하는 설계된 이동**이며,
  목표는 node3 7,882,020 / node4 7,859,062 counts(= +137.45° / +137.05° @ 57,344 counts/°)로
  EasyDRIVE `steerOffset` node3 138.000 / node4 137.250 과 대응한다. 「원인 미상 이상 스윙」이 아니다.
  (`steerOffset` 은 축마다 다르므로 「137.3° 단일값」 서술도 오류다.)
- ⇒ **게이트는 계속 `false` 로 둔다**(위 행의 지시 유지). 다만 **「스윙을 막는 방어선」으로 인용하지 말 것.**
  게이트 존폐 판단은 별건이며 본 정정은 서술만 갱신한다(코드 동작 무변경).

### ④ 잔여 상환계획 (미해결로 남는 것)

1. **(a) 판정** — intercept **보유** 상태에서 판다가 직접 발행한 조향 `0x6064` SDO read 응답을
   Seer 1040 position 과 동시 취득해 대조(21:1x 조건 재현). 본 캡처는 수동청취라 미수행.
2. **21:1x 관측치 자체의 해석** — 그 값이 GUI 홈기준 상대각의 역산이어서 raw 로 오독됐을 가능성 미배제.
3. **상환계획 ②(임의 자세 전원 재투입 후 `0x6064` 재현성)** — 미수행.
4. 위 1~3 수행 시 **`0x6041` bit15 동시 취득 필수**(§① 결론).
