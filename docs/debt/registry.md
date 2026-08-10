# 부채 registry (Debt Registry)

> ⚠ **조향 홈 관련 서술 정정 — 정본은 아래 한 곳이다. 원문은 이력으로 보존한다.**
> **정본: `docs/homing/2026-08-03-can-relay-homing-assets.md` §0** (호밍 **10회 연속 실측**, 2026-08-03 15:33~15:40)
> (값 정본은 `src/Comm/CAN/can_relay/config/machine/foil_a082.yaml` 의 `steer_home_counts`)
>
> - 조향 0° = **`[7871815, 7840086]`** — ⚠ **Seer 좌표계 기준**이며 **물리적 직진은 미확인**이다.
> - **`7882020 / 7859062` 는 0° 가 아니다** — 「**호밍 후 정착값**」이며 0° 에서
>   **+0.178° / +0.331°** 벗어나 있다. 호밍 10회 실측 정착값은 node3 **7,882,021**(σ≈2.8c) ·
>   node4 **7,859,065**(σ≈3.2c) 로 σ≈3 counts 에 재현된다 ⇒ **결함이 아니라 설계 동작**이다.
> - `counts/°` = **57,344**(지령각→CAN 기울기 실측 1.000000) · `0x6098` 호밍 방식 = **1**(−리밋) ·
>   리밋 스위치 **실재** · 호밍 성공률 **10/10**, 소요 **35.0 s**.
>
> **❌ 2026-08-02 판정(`docs/verified_facts/2026-08-02-steer-home-closed.md`)은 폐기됐다 — 인용 금지:**
> - ~~홈 = `[7871810, 7839894]`~~ → **틀렸다.** node4 가 193c 어긋난 raw 판독값이었다.
> - ~~구값 `7871815 / 7840086` 은 「출처 없는 값」~~ → **반증됐다.** 출처는 **Seer 가 실시간으로 내는
>   `0x607A` 조향 목표**이며, 그 값이 1 count 이내로 맞았다.
> - ~~「CAN ↔ Seer 독립 교차확인」~~ → **성립하지 않는다.** Seer 1040 은 판다가 엿듣는 **바로 그
>   `0x6064` 의 아핀 변환**이다(기울기 ×57,344 = **1.000001**). 같은 프레임을 두 번 읽은 것이라
>   역산 `0° = CAN + Seer°×57344` 는 **항등식**이고 자세와 무관하게 같은 값을 낸다.
>   그 측정이 확정한 것은 **Seer 내부 조향 영점**이지 물리적 0° 가 아니다.
> - `debt-007` 은 종결이나, **홈 상수 부채 id 는 계보마다 다르다** — `origin/main` 이 정본:
>   홈 상수 하드코딩 = **debt-026** · can_relay 이름 충돌 = **debt-025** · 구동축 브링업 = **debt-027**.

> ❌ **정정 2026-08-03: 위 배너의 값·판정 2건이 실측으로 뒤집혔다.** 원문은 이력으로 보존한다.
> 정본: `docs/homing/2026-08-03-can-relay-homing-assets.md` §10 (실측 2026-08-03 11:44,
> `orin_steer_crosscheck.py` · 판다 SILENT·passthrough · 송신 0건 · 사용자 확인 「Seer 표시 앞바퀴 2축 0°」 · 2회 동일)
>
> - **홈(0°) = `[7871815, 7840086]`** 이다. 위 배너의 `[7871810, 7839894]` 은 **0° 가 아니라 raw 판독값**이었다 —
>   0° 는 같은 배너 마지막 줄의 역산식으로 구해야 하는데 채택값에 적용되지 않았다.
>   실측 0° 는 node3 **7,871,816** / node4 **7,840,087**, 구값은 **양 노드 1 count(0.000017°) 이내**,
>   위 배너 값은 node4 에서 **193 counts = 0.0034°** 어긋난다.
> - 「구값은 **출처 없는 값**」도 반증 — **출처는 Seer 의 실시간 `0x607A` 조향 목표**다.
> - ⚠ **과장 금지**: 0.0034° 는 **거동상 무의미**하다. 안전 문제가 아니라 정본 정확성 문제다.
> - ⚠ `7882020 / 7859062` 가 **0° 가 아니라 호밍 후 정착값**이라는 위 배너 서술은 **그대로 유효**하다
>   (펌웨어 `SEER_HOME_ZERO_N3/N4` — 이름이 「ZERO」인 것 자체가 부채 → **debt-034**).
> - 영향 항목: **debt-007**(종결 유지, 결론값 재정정) · **debt-016**(해결 유지, 갱신값 재정정) ·
>   **debt-022**(인용한 구값이 이제 정본).

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
| debt-005 | 기술 | ~~Tools/amr_test_gui/amr_test_gui/panda_can_bus.py~~ **(2026-07-28 삭제 — docs/adr/2026-07-28-old-gui-removal.md)** | `TongyiSdoBackend` + `PandaCanBus` 통합 경로가 relay 경유 실구동으로 검증된 적 없음(어댑터 작성만). backend 브링업(선판독·init 시퀀스)이 intercept 중 판다 read 로 정상 완주하는지 미확인 | 2026-07-27 | **무효화 (2026-07-28)** — 대상 파일이 구 GUI 폐기와 함께 삭제됐다. 신 `gui.py` 는 정본 backend 를 경유하지 않고 `_sdo_write` 로 판다에 직접 송신하므로 'TongyiSdoBackend+PandaCanBus 통합 경로' 자체가 존재하지 않는다 | 상환 불요. 단 **정본 backend 경유 경로를 다시 만들 경우 본 항목을 재등록할 것**. 신 GUI 의 판다 직접 송신 경로에 대한 미검증 항목은 debt-012 로 분리 등록 |
| debt-006 | 이해 | Tools/amr_test_gui/amr_test_gui/panda_can_bus.py:send | 판다는 RTR 송신 불가라 backend 의 Node Guarding RTR(20 Hz)을 skip 한다. intercept 중 Seer 의 guard RTR 이 게이트로 forward 되어 모터의 GuardTime(500 ms)×LifeFactor(1) 감시를 대신 만족시킨다는 가정이 코드로 확인 불가 | 2026-07-27 | 미해결 | 잭업 상태에서 intercept 유지 5분 이상 구동하며 노드 HALT 미발생·`snapshot()` last_seen 갱신 지속 확인. HALT 발생 시 펌웨어에 PC-요청 guard RTR 생성 경로 추가 검토 · ⚠ **2026-07-28 이관** — 인용 위치 `panda_can_bus.py:send` 는 구 GUI 폐기로 삭제됐다(docs/adr/2026-07-28-old-gui-removal.md). **질문 자체는 신 `Tools/amr_test_gui/gui.py` `_sdo_write` 경로에 그대로 유효**하며 debt-012 로 재등록했다. 본 행은 이력으로 남긴다 |
| debt-007 | 이해 | src/Actuators/motor_control/config/tongyi_amr.yaml:79-91 (`steer_home_counts: [7871815, 7840086]`) | **미판정 모순 — 조향 홈 counts 의 기준계.** 원문 인용(`tongyi_amr.yaml:79-88`): 「⚠ 미해소 모순 (2026-07-27 관측, debt-007) … 설계 근거(design-inputs.md 「부팅 시 0x6064≈0 이 정상」·「매 기동 시 +137.3° 스윙 필요」)대로면 아래 값은 **절대 목표**다. 그런데 2026-07-27 21:1x 관측에서, Seer 가 이미 기동·호밍을 마치고(1040 position≈0·calib=True) 육안으로도 바퀴가 직진인 상태인데 **판다 read 0x6064 는 ≈0** 이었다. 설계대로라면 그 시점 raw 는 ≈7.87M 이어야 한다. → 둘 중 하나가 틀렸다: **(a)** 판다의 조향 0x6064 read 가 오염됐다 **(b)** 호밍 후 드라이브가 위치 기준을 0 으로 재설정한다(= 아래 값은 기동 전에만 유효). 같은 시점 구동 노드는 판다 read 와 Seer 1040 이 절댓값 일치했다(조향만 어긋남). 미판정 상태이므로 어느 쪽으로도 값을 고치지 않는다」. **본 registry 는 (a)/(b) 어느 쪽도 판정하지 않는다.** → ⚠ **정정 (2026-07-27, 실기 검증)**: 이 문장은 이력 보존을 위해 남기되 더 이상 현재 상태가 아니다 — `Log/homing_capture_220350.jsonl` 로 **(b) 는 「기준이 0 으로 남는다」형태로 반증**, **신규 가설 (c)**(호밍 진행 중 `0x6041` bit15=0 구간에서 `0x6064` 가 정확히 0 고정, 3,080/3,080 샘플) **실증**, **(a) 는 미반증**. 상세는 아래 「[2026-07-27 실기 검증] debt-007 부분 판정」 §①. 안전 직결(조향 홈)이며 다수 코드가 이 id 를 안전 게이트로 참조 중: `src/Actuators/motor_control/motor_control/backend.py:43,235,244,248` · `driver_node.py:75-76` · ~~`Tools/amr_test_gui/amr_test_gui/constants.py:18-19,48` · `controller.py:60,77` · `modes.py:93-94,102`~~ **(2026-07-28 삭제 — docs/adr/2026-07-28-old-gui-removal.md; 신 `Tools/amr_test_gui/gui.py:35` `STEER_HOME` 이 같은 값을 계승)** · `Tools/docking_field_kit/docking_drive.py:73` · `amap2_monitor.py:73`. 참조는 2026-07-27 이전부터 있었으나 **본 표에는 미등록**이었다(`docs/code_review/motor_control-can-consistency/2026-07-26.md:55`, `src/Actuators/motor_control/docs/code_review/motor_control-can-consistency/2026-07-26.md:50` 이 "미등록·등록 필요"로 지적) — 2026-07-27 감사에서 등록 | 2026-07-27 | **✅ 2026-08-02 종결 (유지)** — ❌ **단, 결론값은 2026-08-03 재정정**: 종결이 채택한 `[7871810, 7839894]` 은 **0° 가 아니라 raw 판독값**이었다(역산식 `0° = CAN + Seer°×57344` 미적용). 실측 0° 는 node3 **7,871,816** / node4 **7,840,087** 이고 **정본은 `[7871815, 7840086]`**(양 노드 1c 이내). 구값 폐기 판정(「출처 없는 값」)도 반증 — 출처는 Seer 실시간 `0x607A`. 차이 193c = **0.0034°, 거동상 무의미**(안전 아님, 정본 정확성). **종결 자체(기준계 판정·정본 일원화)는 취소되지 않는다.** 근거 `docs/homing/2026-08-03-can-relay-homing-assets.md` §10 · 아래 「[2026-08-03 실측 재정정]」 절. (아래 「[2026-08-02 실측 확정] debt-007 종결」 절) ← 미해결(미판정) → **⚠ 2026-07-27 실기 검증: 부분 판정**(가설 (c) 신규 확정 · (b) 「기준이 0 으로 남는다」형태 반증 · (a) 미반증). 원 상태 표기는 이력 보존, 상세는 아래 「[2026-07-27 실기 검증] debt-007 부분 판정」 절 | ① Seer 호밍 완료·바퀴 육안 직진 상태에서 조향 노드 `0x6064` 를 (i) 판다 read 와 (ii) Seer 1040 position 으로 **동시 취득**해 절댓값 일치 여부 확인(구동 노드는 이미 일치 관측됨 — `tongyi_amr.yaml:87`). ② 조향 **임의 자세에서 전원 재투입** 후 `0x6064` 재현성 확인(`docs/ros2_driver/2026-07-09-design-inputs.md:139` 이 「0 기준점이 절대 엔코더 기준인지 미확인 — 2회 전원 사이클 관측뿐」으로 남겨둔 항목). ③ 판정 결과를 본 행에 append(값은 실측 없이 변경 금지). **판정 전까지 `allow_homing_motion` 게이트를 끄지 말 것**(`tongyi_amr.yaml:89-90`). ④ ⚠ **2026-07-27 실기 검증 append** — 상환계획 ①②의 핵심 측정이 `Log/homing_capture_220350.jsonl`(Seer 주도 호밍 180 s 수동청취, 253,510 프레임)로 **부분 수행**됐다. 결과·잔여 과제·게이트 근거 정정은 아래 「[2026-07-27 실기 검증] debt-007 부분 판정」 절 참조. **게이트를 끄지 말라는 지시 자체는 계속 유효하나, 그 근거 서술은 정정됐다**(⇒ 같은 절 ③). ⚠ 줄번호: 인용된 `tongyi_amr.yaml:89-90`(사용 규칙)은 2026-07-27 정정 append 로 현재 **`:107-108`** 이며 `allow_homing_motion` 키 자체는 **`:33`** 이다(값 변화 없음). 같은 이유로 위 위치·인용의 `tongyi_amr.yaml:79-91`/`:79-88`(원문 모순 블록)은 현재 **`:97-129`**, `steer_home_counts` 키는 **`:130`** 이다. 인용이 어긋나면 키 문자열로 찾을 것. |
| debt-010 | 기술 | Tools/amr_test_gui/gui.py `_wait_settle`·`_jog_run` | **조향 추종 실패 시 FAULT 래치가 없다.** 구 GUI 의 `ramp.py` 는 미추종 시 래치를 걸어 이후 지령을 봉쇄했으나, 구 GUI 폐기로 그 자산이 사라졌다(docs/adr/2026-07-28-old-gui-removal.md). 현재는 정착 대기 timeout 후 **그 회차의 구동만 취소**하고 끝나므로, 운전자가 같은 버튼을 다시 눌러 실패 지령을 반복할 수 있다 | 2026-07-28 | 미해결 | 정착 실패를 상태로 보존하고(래치), 해제 전까지 조그·슬라이더 지령을 거부. 해제는 명시적 조작으로만. 회귀 테스트 동반 |
| debt-011 | 기술 | Tools/amr_test_gui/gui.py | **테스트 0건.** 구 GUI 테스트 84건이 패키지와 함께 삭제됐다(docs/adr/2026-07-28-old-gui-removal.md). 신 GUI 는 실기 동작만 확인됐고(2026-07-28 15:20 사용자 확인) 자동 회귀가 없다 | 2026-07-28 | **부분 상환 (2026-07-28)** — 순수 환산 회귀 37건 신설(`Tools/amr_test_gui/test/test_gui_math.py`, `QT_QPA_PLATFORM=offscreen python3 -m pytest test/ -q` → 37 passed). 환산부는 `steer_counts`·`drive_units` 모듈 함수로 분리해 Qt 무의존으로 만들었다. **잔여: CAN 송신 프레임 대조·UI 상호작용 미검증** | 하드웨어 없이 검증 가능한 순수 함수부터 고정 — ±90° 클램프, counts 환산(`STEER_HOME`+deg×`COUNTS_PER_DEG`), 속도 환산·상한, `_wait_settle` 양축 판정, `_redraw_wheel` 출처 우선순위. CAN 송신은 `_sdo_write` 를 가짜 객체로 대체해 프레임 수준 대조 |
| debt-012 | 이해 | Tools/amr_test_gui/gui.py `_sdo_write` (구 debt-006 이관) | 판다는 RTR 송신 불가라 PC 측이 Node Guarding RTR(20 Hz)을 보내지 못한다. intercept 중 Seer 의 guard RTR 이 게이트로 forward 되어 모터의 GuardTime(500 ms)×LifeFactor(1) 감시를 대신 만족시킨다는 가정이 코드로 확인되지 않는다 | 2026-07-28 | 미해결 | 잭업 상태에서 제어권 유지 5분 이상 구동하며 노드 HALT 미발생 확인. HALT 발생 시 펌웨어에 PC-요청 guard RTR 생성 경로 추가 검토 |
| debt-014 | 이해 | `Tools/amr_test_gui/gui.py:1058` (세션 8bfbdf1d 소유 — 본 세션은 진단만) | **호밍 중 조향각 표시 경로 미확정.** GUI 는 호밍 중 `0x6064` 를 읽지만 `not self._homing` 가드로 폐기한다(각도 미표시). `0x6064` 는 호밍 중(0x6041 bit15=0) 정확히 0 이 맞다(debt-007 §①, 3,080/3,080 샘플) — 따라서 0x6064 로는 호밍 중 각도 불가. TR_Nav 는 UI 로 호밍 중 각도를 표시(다른 드라이브, 벤더 PDO `0x2106`). **2026-07-29 실기 시험 결과(내가 CAN 으로 닿은 범위)**: 호밍 WAIT(t=0.3~31.6s) 동안 CAN 위치객체 `0x6064`·`0x60FB.2`·`0x60FB.3`(slAbsAngle) **전부 0 리셋**(GOZERO 후에만 복원). 원시 엔코더 내부변수 `0x42FD`(sMotor.slAbsAngle)·`0x5A3E`/`0x5A3F` 는 **CAN SDO 미노출(ABORT 0x06020000)** — EasyDRIVE 내부 모니터 변수. ⚠ **"경로 없음"은 내가 시험한 CAN 객체 범위에 한한 것이며 확정 아님** — 사용자가 "엔코더 읽으면 된다"고 확신, **읽는 방법을 나중에 제공 예정**(객체 인덱스 / 드라이버 파라미터 / 별도 링크 중 무엇인지 대기) | 2026-07-29 | 미해결(사용자 입력 대기) | 사용자 제공 방법으로 호밍 중 위치 판독 → 유효하면 gui.py 가드를 그 경로로 교체. 미제공 잠정안: (a) 속도 적분 추정 + "추정" 라벨 (b) 호밍 중 상태만 표시. 관련 mistake `2026-07-29-001` |
| debt-013 | 기술 | `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h` `seer_stop_drives` + `board/main.c` heartbeat 상실 블록 | **S4(정지 명령) 검증 미완.** 저속 후진 실기(2026-07-28)에서 heartbeat 상실 ~2s 후 node2 가 감속→정지(t≈5.0s, 램프)함을 관측했으나 **분리·재현이 미흡**: (1) 정지 순간 S4 의 `0x60FF=0` 발행과 relay off 후 Seer 인수가 같은 시점이라 **S4 단독 기여를 분리 못 함** — pre-S4 펌웨어(`12dd1138`)와 대조 미수행. (2) node1 은 거의 안 움직여(~3,000 counts) 감속 곡선 확보 실패, 비대칭 원인 미상. (3) 판다 발원 정지 프레임이 에코로는 node1 1건만 잡혀 node2 전달을 버스로 직접 확증 못 함 | 2026-07-28 | 미해결 | 내일 재검증: ① pre-S4(`12dd1138`) vs S4(`fd9f728b`) 동일 후진 조건 대조로 "PC 사망 후 주행 거리" 차이 측정 ② 양 구동륜 유의 속도 확보 후 0x6064 시계열로 양측 감속 확인 ③ 정지 프레임 전달을 드라이브 SDO 응답으로 확증 |

| debt-015 | 의도 | `src/Comm/CAN/can_relay/package.xml` (패키지명 `can_relay`) | **이름 충돌 — 알고 감수한 것.** 저장소에서 `can_relay` 는 지금까지 판다 펌웨어 프로젝트를 뜻해 왔다(`Tools/Can_Relay/`, `docs/can_relay/`, `docs/code_review/can_relay_firmware/`, `README.md:1` "CATL-Ford CAN-Relay"). 신설 ROS2 드라이버가 같은 이름을 쓰면 세 번째 맥락이 생긴다. 10인 감사의 리뷰어 8·변호인 D1 이 **둘 다 개명을 권고**했고, 근거는 이 저장소에서 이름 공유로 **debt id 오참조가 실제 발생한 기록**(본 registry `id 충돌 목록`)이다. 사용자가 원안(이름 유지)을 명시 선택했으므로 진행하되 위험을 등록한다 | 2026-07-29 | 미해결(의도적 수용) | 완화책 유지: `package.xml` `<description>` 첫 단락이 펌웨어와의 구분을 명시하고, 문서·주석 인용 시 **어느 `can_relay` 인지 반드시 병기**한다. 오참조가 1건이라도 실제 발생하면 개명을 재상신한다(후보: `seer_relay_bridge`). 근거 ADR `docs/adr/2026-07-29-can-relay-ros2-package.md` §Decision 2 |
| debt-016 | 이해 | `src/Comm/CAN/can_relay/config/can_relay.yaml` `steer_home_counts` · `can_relay/safety.py` `DEFAULT_STEER_HOME` | **조향 홈 상수 하드코딩 계승 (debt-007 파생).** `Log/homing_capture_220350.jsonl` 전수 디코드 결과, Seer 가 유지한 0° 목표는 `7882020`(node3)/`7859062`(node4) 이고 config 값 `7871815`/`7840086` 과 `+10,205`/`+18,976` counts(= **+0.178°**/**+0.331°**) 다르다. 두 값 모두 `homing_tol` 5°·`settle_tol` 3° 어느 게이트로도 검출되지 않는 **영구 미검출 오프셋**이다. ⚠ **재정정 2026-08-03 17:00 (E7) — 충돌 명시**: 2026-08-03 15:40 에 debt-034 와 `docs/homing/2026-08-03-can-relay-homing-assets.md` §0-2 가 **같은 +0.178° / +0.331°** 를 「**결함이 아니라 설계 동작**」이라고 적었는데, 이는 본 행의 「**영구 미검출 오프셋**」 등록과 **정면 충돌**한다. 17:00 재정정으로 그 표현은 **과잉 확정으로 판정돼 「재현되는 정착 동작(상수 적정성은 별건)」으로 완화**됐다 — 실측이 보증하는 것은 「축이 `SEER_HOME_ZERO_N3/N4`(`safety_seer_gate.h:212-213`)에 1~3 counts 로 재현성 있게 정착한다」까지이고, **그 상수의 적정성은 실측에서 나오지 않는다**. ⇒ **본 행의 「영구 미검출 오프셋」 등록은 유효하며, 「설계 동작이라 문제없다」를 근거로 본 행을 닫지 말 것.** 근거 `docs/homing/2026-08-03-can-relay-homing-assets.md` §0-0-3. 또한 `7871815` 계열은 캡처에서 `0x6041=0x9450`(Operation enabled 아님) 구간에만 나타나 **드라이브가 수행한 적 없는 목표**로 보인다. debt-007 상환계획 ③("실측 없이 값 변경 금지") 때문에 값을 바꾸지 않고 계승했다 | 2026-07-29 | **✅ 2026-08-02 해결(대안 경로)** — 상환계획의 「런타임 취득」 대신 **정본 일원화 + 코드 기본값 제거**로 닫았다. `steer_home_counts` 정본은 `config/machine/foil_a082.yaml` 하나이고 `safety.DEFAULT_STEER_HOME = {}` 이라 미설정 시 조향을 거부한다. 값도 실측값 `[7871810, 7839894]` 으로 갱신(구값과 5c/192c 차). 상세는 「[2026-08-02 실측 확정] debt-007 종결」 절. → ❌ **정정 2026-08-03 (해결 판정은 유지, 갱신값만 재정정)**: 그때 넣은 `[7871810, 7839894]` 은 **0° 가 아니라 raw 판독값**이었다. 실측 0° 는 node3 7,871,816 / node4 7,840,087 이고 **정본은 `[7871815, 7840086]`** — 즉 이 항목이 「구값 → 실측값」으로 바꾼 방향이 node4 에서 **193c(0.0034°) 만큼 반대로** 갔다. **본 항목의 실질(정본 일원화 + 코드 기본값 제거)은 값과 무관하게 유효**하므로 해결 판정은 유지한다. 거동 영향 없음. 근거 `docs/homing/2026-08-03-can-relay-homing-assets.md` §10. **잔여: 런타임 취득은 구현하지 않았다** — 절대 엔코더가 4일·전원사이클을 넘어 8c/190c 로 재현됨이 실측돼 상시 취득의 필요가 낮아졌다 | 근본 해법은 하드코딩 폐기 — 호밍 완료(`0x6041` bit15 0→1) 직후 드라이브가 정착한 `0x6064` 를 **런타임에 취득**해 홈으로 삼는다. 그러면 상수 소유자가 사라지고 debt-007·debt-016 이 함께 상환된다. 그 전까지 파라미터로만 노출하고 기본값을 바꾸지 않는다 |
| debt-017 | 기술 | `src/Comm/CAN/can_relay/can_relay/protocol.py` `drive_init_frames`·`steer_init_frames` (`allow_bringup` 기본 false) | **구동축 브링업 시퀀스에 실기 검증 이력이 0 이다.** 실기 구동이 확인된 유일한 코드 `Tools/amr_test_gui/gui.py` 에는 이 시퀀스가 **없다** — 그 코드는 `0x6060`·`0x100C`/`0x100D`·`0x6081/83/84` 를 한 번도 쓰지 않고, Seer 가 이미 브링업·enable 해 둔 축에 intercept 로 올라타 `0x60FF`/`0x607A` 만 덮어쓴다(확인: `grep -n "0x6060\|0x100C\|0x6081" Tools/amr_test_gui/gui.py` → 0건). 본 패키지의 브링업 프레임은 실측 캡처(Seer init, t=17.883~17.904 / t=49.012~49.133)와 **바이트 동일**함이 확인됐으나, 그것을 **우리가 보냈을 때** 드라이브가 어떻게 반응하는지는 미관측이다 | 2026-07-29 | 미해결 | 잭업(바퀴 공중) + 하드웨어 E-STOP 상비 상태에서 `allow_bringup: true` 로 1회 수행하고 `0x6041`·`0x603F`·SDO abort 를 전수 기록. abort 0건·상태 전이 정상 확인 후에만 지면 사용. 확인 전까지 기본값 false 유지 |
| debt-018 | 기술 | `src/Comm/CAN/can_relay` ↔ `src/Actuators/motor_control` (배타 장치 부재) | **모터 구동 ROS2 패키지가 둘이고 동시 기동을 막는 장치가 없다.** 두 패키지는 전제가 배타적이다(can_relay=Seer 공존·판다 경유 / motor_control=Seer 분리·socketcan 직결). 동시에 뜨면 같은 드라이브에 서로 다른 안전 모델로 쓰기가 들어간다. 확인: `grep -rniE 'flock\|lockfile\|pidfile\|singleton' src/Comm/CAN/can_relay src/Actuators/motor_control --include=*.py` → 0건. 나아가 **어느 패키지도 타 마스터(Seer 포함) 트래픽을 검출하지 않는다** | 2026-07-29 | 미해결 | 최소안: 버스 배타 파일 락 + 브링업 전 수동 청취로 타 마스터 SDO(`0x600±`)·guard(`0x700±`) 검출 시 기동 거부. 정공법: `motor_control` 을 판다 게이트 뒤로 옮기거나 한쪽을 deprecate. 그 전까지 **운전자 수동 준수**(동시 launch 금지) |
| debt-019 | 기술 | `Tools/amr_test_gui/gui.py` `_wait_settle`·`_meas_deg` (**타 세션 소유 — 본 세션은 진단만 등록**) | **피드백 신선도 게이트가 대체 없이 사라졌다.** 구 GUI 는 `FEEDBACK_STALE_S = 0.5` 로 오래된 실측을 무효화했고 그 주석이 "이 게이트가 없으면 램프가 영원히 SETTLED·구동 허용으로 남는다"고 적었다(`Tools/amr_test_gui/docs/sw_structure/amr-test-gui/2026-07-27.md:254-256`). 구 GUI 폐기(`docs/adr/2026-07-28-old-gui-removal.md`)로 삭제됐고 **그 ADR 의 「폐기 자산과 대체」 표에도 debt 에도 등록되지 않았다**. 현재 `gui.py` 에 신선도 판정이 없다(확인: `grep -c "stale\|last_seen" Tools/amr_test_gui/gui.py` → 0). 결과: RX 가 죽어도 `_wait_settle` 이 굳은 값으로 즉시 True 를 반환해, 조향이 실제로 안 돌아간 상태에서 crab 구동이 시작될 수 있다 | 2026-07-29 | 미해결 | 소유 세션이 상환: 실측에 수신 시각을 달고 TTL 초과 시 `None` 처리 → `_wait_settle` 은 결측을 정착으로 치지 않는다. 참고 구현 `src/Comm/CAN/can_relay/can_relay/backend.py` `NodeState.fresh()`·`steer_angles_deg()` (같은 문제를 TTL 로 해결, 회귀 시험 `test_backend.py::test_steer_angle_none_when_feedback_expired`) |

| debt-020 | 의도 | `docs/claude_guideline/code_review/review.md` (다중 에이전트 감사 절차) · 관련 `docs/claude-mistake/2026-07-29-003` §재발 방지 3 | **적대적 반대심문이 절차가 아니라 「사용자 지시」에 걸려 있다.** 2026-07-29 10인 병렬 감사에서 나온 결론 **5건이 반대심문 3인에게 뒤집혔다**(브링업 부재=거짓 / 조향 홈 기준계=논리 반증 / NaN 방향=미입증 / guard forward 조건=누락 / 「중복이니 확장」=반박). 그 라운드가 돈 이유는 사용자가 "적대적 토론 진행"을 명시 지시했기 때문이고, **지시가 없었으면 5건이 정본으로 남아 그 위에 코드를 지었을 것**이다. 특히 「중복이니 motor_control 을 확장하라」를 따랐다면 그 패키지의 유일한 문서보증 정지수단(guard RTR 중단)이 판다 경유에서 무력화된 코드가 나왔다. 같은 구멍이 `docs/claude-mistake/INDEX.md` §메타 패턴의 2026-07-28-011·012·013 에도 기록돼 있다 — 그때도 사용자 지시("10명이 재검토", "적대적 검증을 해야 합니다")가 결정적이었다. 2026-07-29 S6 lint 추가로 *부정형 단정* 쪽 구멍은 닫혔으나 **반대심문 자체의 기동 조건은 닫히지 않았다**(사용자가 이번엔 미채택 결정) | 2026-07-29 | 미해결(사용자 미채택 — 위험만 등록) | 채택 시: `review.md` 에 "다중 에이전트 감사는 반대심문 라운드를 거친다"를 명문화하고, 1차 결론 대비 뒤집힌 건수를 리뷰 산출물에 의무 기록(오늘 `docs/code_review/can_relay_ros2/2026-07-29.md` §적대적 반대심문… 절이 그 형식의 선례). 미채택 유지 시: 다중 에이전트 감사 결과를 **1차 결론 그대로 사용자에게 보고하지 말고** 최소한 「미심문」 라벨을 붙인다 |
| debt-021 | 기술 | `src/Control/Motion_Control/{QD,2WS}` ↔ `src/Comm/CAN/can_relay` (체인 상류 2노드 부재) | **모션 스택과 모터 드라이버 사이의 중간 2노드가 저장소에 없다.** 상류 원본 `kuks2309/TR_Nav_ros2_ws`(HEAD `ad75209`, 2026-07-31 대조)의 체인은 `action server ─WheelSetArray→ trnav_motion_mux ─/motor/wheel_cmd→ amr_motor_cmd_translator ─MotorCmdArray→ amr_canopen_motor_driver` 인데, 본 저장소에는 **액션 서버(9종)와 can_relay 만 있고 mux·translator 가 없다**(확인: `find src -type d \( -iname '*mux*' -o -iname '*translator*' -o -iname '*canopen*' -o -iname '*arbitration*' \)` → 0건). 저장소의 `sil_*.launch.py` 들은 `trnav_motion_mux`·`trnav_motion_supervisor`·`translate_sim_odom` 을 참조하지만 그 패키지들이 트리에 없어 **현 상태로는 launch 가 성립하지 않는다.** 결과: can_relay 를 모터 계층으로 내려도(ADR `docs/adr/2026-07-31-can-relay-cpp-motor-layer.md`) `/motor/low_cmd` 를 발행하는 노드가 없어 체인이 이어지지 않는다 | 2026-07-31 | **해결(2026-07-31)** — 상환계획 (a) 채택. `trnav_motion_mux`·`amr_motor_cmd_translator` 를 TR_Nav(HEAD `ad75209`)에서 `src/Control/Motion_Control/Common/` 으로 이식. 리네임 0건(메시지 패키지 통합으로 사본 불요). ADR `docs/adr/2026-07-31-motion-motor-chain-mux-translator-port.md`. 검증: colcon 13/13 error 0·stderr 0, 두 노드 기동 후 `/motor/wheel_cmd` pub 1/sub 1 연결·`/motor/low_cmd` pub 1 확인, 이식본 회귀 12 tests 0 failures. **잔여**: `trnav_motion_supervisor`·`translate_sim_odom` 은 여전히 부재해 `sil_*.launch.py` 는 아직 성립하지 않음(→ debt-026). 실기 구동 0 | (해결됨) |
| debt-022 | 이해 | `src/Comm/CAN/can_relay/can_relay/safety.py` `steer_deg_to_counts`·`DEFAULT_STEER_HOME` ↔ TR_Nav `amr_motor_cmd_translator` (환산 책임 경계) | **조향 환산 보정이 이중 적용될 수 있으나 책임 경계가 미확정이다.** 상류 `amr_motor_cmd_translator_qd.yaml` 은 이미 `direction_steer_front/rear: -1`, `steer_offset_front/rear_deg: -1.676`(2026-07-13 개루프 실측), `gear_steer: 265.5`, `pulses_per_rev: 65536` 을 적용해 raw pulse 를 만든다. 본 패키지의 `steer_home_counts`(`[7871815, 7840086]`)·`COUNTS_PER_DEG`(57344.0)가 같은 보정을 다시 걸면 **이중 적용**된다. 어느 계층이 환산을 소유하는지가 문서로 확정된 적이 없다. 값 자체도 부호·기준계가 다르다 — TR_Nav `amr_canopen_motor_driver.yaml` 의 `steer_home_offset_front/rear: -6500000` 대 본 패키지 `+7871815`/`+7840086`. 선행 부채와 얽힘: debt-007(호밍 후 영구 오프셋 미판정), debt-016(홈 상수 하드코딩 계승) → ⚠ **정정 2026-08-03 (인용값 상태 갱신 — 부채 자체는 미해결 유지)**: 본 행이 인용한 `steer_home_counts` `[7871815, 7840086]` 은 **2026-08-02 에 폐기 선언됐다가 2026-08-03 실측으로 정본으로 확정**됐다(실측 0° node3 7,871,816 / node4 7,840,087 대비 양 노드 1c 이내). 따라서 **본 행의 값 인용은 현재도 유효**하며, 2026-08-02~08-03 사이에 잠시 `[7871810, 7839894]` 이던 것으로 읽지 말 것. **「이중 적용 위험」 지적은 값의 옳고 그름과 무관하므로 그대로 유효하다** — 쟁점은 어느 계층이 환산을 소유하느냐이지 상수값이 아니다. 부호·기준계 상충(TR_Nav `steer_home_offset_front/rear: -6500000` 대 본 패키지 `+7871815`/`+7840086`)도 미해소 그대로다. 근거 `docs/homing/2026-08-03-can-relay-homing-assets.md` §10 | 2026-07-31 | **부분 해결 (2026-08-05)** — ①(소유 계층) **확정**, ②(잭업 실측 대조) 미이행 → 항목 유지. 상세는 아래 「[2026-08-05 판정]」 절. ⚠ 아래 ① 의 「권장」은 **반대 방향으로 판정**됐다 — 그 문장을 근거로 코드를 되돌리지 말 것 | ① 환산 소유 계층을 문서로 확정(권장: translator 가 SI→raw 를 단독 소유, can_relay 는 **안전 클램프 판정용으로만** counts↔deg 환산 — 지령 값을 재보정하지 않는다). ② 확정 후 잭업 상태에서 상류가 만든 raw 를 그대로 흘려 실측 조향각과 대조. ③ debt-007 상환계획 ③("실측 없이 값 변경 금지")을 그대로 적용 — 대조 전까지 어느 쪽 값도 바꾸지 않는다 |
| debt-027 | 기술 | `src/Comm/CAN/can_relay/can_relay/protocol.py` `drive_init_frames`·`steer_init_frames` (`allow_bringup` 기본 false) | **구동축 브링업 시퀀스에 실기 검증 이력이 0 이다.** 실기 구동이 확인된 유일한 코드 `Tools/amr_test_gui/gui.py` 에는 이 시퀀스가 **없다** — 그 코드는 `0x6060`·`0x100C`/`0x100D`·`0x6081/83/84` 를 한 번도 쓰지 않고, Seer 가 이미 브링업·enable 해 둔 축에 intercept 로 올라타 `0x60FF`/`0x607A` 만 덮어쓴다(확인: `grep -n "0x6060\|0x100C\|0x6081" Tools/amr_test_gui/gui.py` → 0건). 본 패키지의 브링업 프레임은 실측 캡처(Seer init, t=17.883~17.904 / t=49.012~49.133)와 **바이트 동일**함이 확인됐으나, 그것을 **우리가 보냈을 때** 드라이브가 어떻게 반응하는지는 미관측이다 | 2026-07-29 | 미해결 | 잭업(바퀴 공중) + 하드웨어 E-STOP 상비 상태에서 `allow_bringup: true` 로 1회 수행하고 `0x6041`·`0x603F`·SDO abort 를 전수 기록. abort 0건·상태 전이 정상 확인 후에만 지면 사용. 확인 전까지 기본값 false 유지 |
| debt-028 | 기술 | `src/Comm/CAN/can_relay` ↔ `src/Actuators/motor_control` (배타 장치 부재) | **모터 구동 ROS2 패키지가 둘이고 동시 기동을 막는 장치가 없다.** 두 패키지는 전제가 배타적이다(can_relay=Seer 공존·판다 경유 / motor_control=Seer 분리·socketcan 직결). 동시에 뜨면 같은 드라이브에 서로 다른 안전 모델로 쓰기가 들어간다. 확인: `grep -rniE 'flock\|lockfile\|pidfile\|singleton' src/Comm/CAN/can_relay src/Actuators/motor_control --include=*.py` → 0건. 나아가 **어느 패키지도 타 마스터(Seer 포함) 트래픽을 검출하지 않는다** | 2026-07-29 | 미해결 | 최소안: 버스 배타 파일 락 + 브링업 전 수동 청취로 타 마스터 SDO(`0x600±`)·guard(`0x700±`) 검출 시 기동 거부. 정공법: `motor_control` 을 판다 게이트 뒤로 옮기거나 한쪽을 deprecate. 그 전까지 **운전자 수동 준수**(동시 launch 금지) |
| debt-029 | 기술 | `Tools/amr_test_gui/gui.py` `_wait_settle`·`_meas_deg` (**타 세션 소유 — 본 세션은 진단만 등록**) | **피드백 신선도 게이트가 대체 없이 사라졌다.** 구 GUI 는 `FEEDBACK_STALE_S = 0.5` 로 오래된 실측을 무효화했고 그 주석이 "이 게이트가 없으면 램프가 영원히 SETTLED·구동 허용으로 남는다"고 적었다(`Tools/amr_test_gui/docs/sw_structure/amr-test-gui/2026-07-27.md:254-256`). 구 GUI 폐기(`docs/adr/2026-07-28-old-gui-removal.md`)로 삭제됐고 **그 ADR 의 「폐기 자산과 대체」 표에도 debt 에도 등록되지 않았다**. 현재 `gui.py` 에 신선도 판정이 없다(확인: `grep -c "stale\|last_seen" Tools/amr_test_gui/gui.py` → 0). 결과: RX 가 죽어도 `_wait_settle` 이 굳은 값으로 즉시 True 를 반환해, 조향이 실제로 안 돌아간 상태에서 crab 구동이 시작될 수 있다 | 2026-07-29 | 미해결 | 소유 세션이 상환: 실측에 수신 시각을 달고 TTL 초과 시 `None` 처리 → `_wait_settle` 은 결측을 정착으로 치지 않는다. 참고 구현 `src/Comm/CAN/can_relay/can_relay/backend.py` `NodeState.fresh()`·`steer_angles_deg()` (같은 문제를 TTL 로 해결, 회귀 시험 `test_backend.py::test_steer_angle_none_when_feedback_expired`) |
| debt-030 | 의도 | `docs/claude_guideline/code_review/review.md` (다중 에이전트 감사 절차) · 관련 `docs/claude-mistake/2026-07-29-003` §재발 방지 3 | **적대적 반대심문이 절차가 아니라 「사용자 지시」에 걸려 있다.** 2026-07-29 10인 병렬 감사에서 나온 결론 **5건이 반대심문 3인에게 뒤집혔다**(브링업 부재=거짓 / 조향 홈 기준계=논리 반증 / NaN 방향=미입증 / guard forward 조건=누락 / 「중복이니 확장」=반박). 그 라운드가 돈 이유는 사용자가 "적대적 토론 진행"을 명시 지시했기 때문이고, **지시가 없었으면 5건이 정본으로 남아 그 위에 코드를 지었을 것**이다. 특히 「중복이니 motor_control 을 확장하라」를 따랐다면 그 패키지의 유일한 문서보증 정지수단(guard RTR 중단)이 판다 경유에서 무력화된 코드가 나왔다. 같은 구멍이 `docs/claude-mistake/INDEX.md` §메타 패턴의 2026-07-28-011·012·013 에도 기록돼 있다 — 그때도 사용자 지시("10명이 재검토", "적대적 검증을 해야 합니다")가 결정적이었다. 2026-07-29 S6 lint 추가로 *부정형 단정* 쪽 구멍은 닫혔으나 **반대심문 자체의 기동 조건은 닫히지 않았다**(사용자가 이번엔 미채택 결정) | 2026-07-29 | 미해결(사용자 미채택 — 위험만 등록) | 채택 시: `review.md` 에 "다중 에이전트 감사는 반대심문 라운드를 거친다"를 명문화하고, 1차 결론 대비 뒤집힌 건수를 리뷰 산출물에 의무 기록(오늘 `docs/code_review/can_relay_ros2/2026-07-29.md` §적대적 반대심문… 절이 그 형식의 선례). 미채택 유지 시: 다중 에이전트 감사 결과를 **1차 결론 그대로 사용자에게 보고하지 말고** 최소한 「미심문」 라벨을 붙인다 |
| debt-022 | 이해 | `src/Comm/CAN/can_relay/can_relay/safety.py` `steer_deg_to_counts`·`DEFAULT_STEER_HOME` ↔ TR_Nav `amr_motor_cmd_translator` (환산 책임 경계) | **조향 환산 보정이 이중 적용될 수 있으나 책임 경계가 미확정이다.** 상류 `amr_motor_cmd_translator_qd.yaml` 은 이미 `direction_steer_front/rear: -1`, `steer_offset_front/rear_deg: -1.676`(2026-07-13 개루프 실측), `gear_steer: 265.5`, `pulses_per_rev: 65536` 을 적용해 raw pulse 를 만든다. 본 패키지의 `steer_home_counts`(`[7871815, 7840086]`)·`COUNTS_PER_DEG`(57344.0)가 같은 보정을 다시 걸면 **이중 적용**된다. 어느 계층이 환산을 소유하는지가 문서로 확정된 적이 없다. 값 자체도 부호·기준계가 다르다 — TR_Nav `amr_canopen_motor_driver.yaml` 의 `steer_home_offset_front/rear: -6500000` 대 본 패키지 `+7871815`/`+7840086`. 선행 부채와 얽힘: debt-007(호밍 후 영구 오프셋 미판정), debt-016(홈 상수 하드코딩 계승) → ⚠ **정정 2026-08-03 (인용값 상태 갱신 — 부채 자체는 미해결 유지)**: 본 행이 인용한 `steer_home_counts` `[7871815, 7840086]` 은 **2026-08-02 에 폐기 선언됐다가 2026-08-03 실측으로 정본으로 확정**됐다(실측 0° node3 7,871,816 / node4 7,840,087 대비 양 노드 1c 이내). 따라서 **본 행의 값 인용은 현재도 유효**하며, 2026-08-02~08-03 사이에 잠시 `[7871810, 7839894]` 이던 것으로 읽지 말 것. **「이중 적용 위험」 지적은 값의 옳고 그름과 무관하므로 그대로 유효하다** — 쟁점은 어느 계층이 환산을 소유하느냐이지 상수값이 아니다. 부호·기준계 상충(TR_Nav `steer_home_offset_front/rear: -6500000` 대 본 패키지 `+7871815`/`+7840086`)도 미해소 그대로다. 근거 `docs/homing/2026-08-03-can-relay-homing-assets.md` §10 | 2026-07-31 | 미해결 | ① 환산 소유 계층을 문서로 확정(권장: translator 가 SI→raw 를 단독 소유, can_relay 는 **안전 클램프 판정용으로만** counts↔deg 환산 — 지령 값을 재보정하지 않는다). ② 확정 후 잭업 상태에서 상류가 만든 raw 를 그대로 흘려 실측 조향각과 대조. ③ debt-007 상환계획 ③("실측 없이 값 변경 금지")을 그대로 적용 — 대조 전까지 어느 쪽 값도 바꾸지 않는다 |
| debt-031 | 이해 | `src/Navigation/mcl2d_core/src/motion_model.cpp` `selectExtraMove()` ↔ `types.hpp` `best_particle_tolerant_threshold` | **산포 모드 판정에 쓰는 우도 스케일이 원본과 같은지 미검증이다.** 2026-07-31 원본 대조로 모드 결정 트리를 이식했는데(ADR `docs/adr/2026-07-31-mcl2d-motion-model-fidelity.md`), 판정 입력 `w` 를 원본은 `getParticleLikelihood`(정규화 여부 미확인)로, 우리는 `ObservationField::getPostProb` 로 구한다. 임계 `0.8`(BestParticleTolerantThreshold, robot.param 실측 배포값)이 우리 스케일에서 같은 의미인지 확인된 적이 없다. 참고로 `types.hpp` 의 다른 우도 임계들은 이미 스케일 차이로 재조정된 이력이 있다(`reloc_success_threshold` 0.5→0.1, `stop_confidence` 0.3→0.02 — 「가우시안 근사 시절 스케일」 주석). **현재 데모 수렴 시 우도가 0.07 수준**이라 실측대로면 모드 5(신뢰 높음, w≥0.8)는 사실상 발동하지 않는다 | 2026-07-31 | 미해결 | ① 원본 `getParticleLikelihood` 반환 스케일을 오라클(`test_obs_field_oracle` 계열)로 확인 — 분석 장비 `amap@amap-1` 의 원본 하드 필요. ② 같은 스캔·자세에서 양쪽 값을 대조해 임계를 우리 스케일로 환산. ③ 환산 전까지 `best_particle_tolerant_threshold` 값을 **임의로 바꾸지 않는다**(원본 배포값 그대로 둠). ④ **2026-07-31 착수** — 값 대신 **진단을 노출**했다: `Mcl2dLocalizer::lastModeLikelihood()`·`lastExtraMove()` + ROS2 노드 5초 throttle 로그(`mode/radius/angle/w/BPTT/stopped`). 현재까지 관측된 w 는 **0.076**(비-ROS 데모 수렴)·**0.376**(합성 방 단위시험, `test_localizer_stopped`)로 둘 다 임계 0.8 미달 — 실기 로그가 쌓이면 그 분포로 환산한다 |
| debt-024 | 기술 | `src/Control/Motion_Control/{QD,2WS}` (동일 토픽·동일 타입, 배타 장치 부재) | **메시지 패키지 통합의 부작용 — QD·2WS 동시 기동 시 지령이 조용히 섞인다.** 두 스택은 토픽명(`/motor/wheel_cmd`, `/motor/low_cmd`, `/motion/wheel_cmd/<action>`)과 서비스명(`/select_motion_source`)이 동일하고 액션 노드 실행파일명도 같다(`amr_mpc_node` 등, 패키지 한정 실행으로 구분). **통합 전에는 타입 불일치(`trnav_msgs` vs `trnav_2ws_msgs`)가 우연한 안전장치로 작동해 연결 자체가 안 됐으나, 2026-07-31 통합(ADR `docs/adr/2026-07-31-motion-motor-chain-mux-translator-port.md`)으로 그 장벽이 사라졌다** — 이제 두 스택을 함께 띄우면 같은 토픽에 발행자가 둘 붙어 섞인 지령이 모터로 내려간다. 확인: 이식·통합 후 `ros2 topic list -t` 전 토픽이 `trnav_msgs/*` 단일 타입. 배타 장치는 없다(mux 의 `/select_motion_source` 는 **한 스택 내부**의 소스 중재이지 스택 간 중재가 아니다). debt-018(모터 구동 ROS2 패키지 2개 동시 기동 방지 장치 부재)과 같은 부류이며, 그쪽은 CAN 계층·이쪽은 모션 계층이다 | 2026-07-31 | 미해결 | 최소안: 두 스택 launch 에 상호배타 파일 락 또는 기동 시 `/motor/wheel_cmd` 기존 발행자 수 조회 후 1 이상이면 기동 거부. 정공법: 플랫폼을 **런타임 파라미터 1개**로 고르게 하고(스택을 둘로 두지 않음) `trnav_2ws_*` 를 QD 스택의 geometry/kinematics 선택지로 흡수 — 그러면 debt-024 와 「2WS 6패키지 사본」이 함께 해소된다. 그 전까지 **운전자 수동 준수**(동시 launch 금지) |
| debt-025 | 이해 | `src/Control/Motion_Control/Common/amr_motor_cmd_translator/config/amr_motor_cmd_translator_qd.yaml` ↔ `src/Control/Motion_Control/2WS/trnav_2ws_core/config/robot_geometry_2ws.yaml` | **이식한 translator 의 환산 파라미터가 상류 QD 플랫폼 실측값이라 본 저장소 2WS 기하와 다르다.** translator YAML: `wheel_radius_m: 0.08`, `gear_walk: 20.0`. 2WS geometry YAML: `wheel_radius = 0.125`, `gear_walk = 32.0`. 이 값들은 `target_vel = v * 60 * gear_walk * 10 / (radius * 2π) * dir` 에 직접 들어가므로 **구동 속도 환산이 실제와 어긋난다**(비율로 보면 `0.08·20` 대 `0.125·32` — 2배 이상 차이). 조향 쪽 `gear_steer: 265.5`·`pulses_per_rev: 65536`·`steer_offset_*_deg: -1.676`(상류 2026-07-13 개루프 실측) 역시 본 로봇 실측으로 확인된 적이 없다. 2026-07-31 이식은 **로직·값 무변경 원칙**으로 원본을 그대로 옮겼고 정렬을 수행하지 않았다 | 2026-07-31 | 미해결 | ① 본 로봇 실측으로 `wheel_radius_m`·`gear_walk`·`gear_steer`·`pulses_per_rev` 를 확정하고 2WS 전용 params 파일을 별도로 만든다(원본 QD YAML 은 대조용으로 보존). ② `steer_offset_*_deg` 는 상류와 같은 방식(개루프 같은방향 leg, 캐스터 플립 배제)으로 재측정. ③ 확정 전까지 **실기에서 translator 를 통해 구동하지 않는다** — debt-007 상환계획 ③("실측 없이 값 변경 금지") 준용이며, 여기서는 "실측 없이 값을 **쓰지도** 않는다" 로 강화 적용한다 |
| debt-026 | 기술 | `src/Control/Motion_Control/{QD,2WS}/*/launch/sil_*.launch.py` (참조 패키지 2종 부재) | **SIL launch 가 여전히 성립하지 않는다.** debt-021 해소로 `trnav_motion_mux` 는 실재하게 됐으나, 같은 launch 들이 참조하는 `trnav_motion_supervisor`(상류 `src/Control/AMR-Arbitration/`)와 `translate_sim_odom`(상류 `src/SIL/`)은 **아직 이식되지 않았다**(확인 2026-07-31: `find src -type d -iname '*supervisor*' -o -iname '*sim_odom*'` → 0건). 예: `2WS/trnav_2ws_action_server/launch/sil_mpc_reverse.launch.py:23,41` 이 두 패키지를 `package=` 로 지목한다. 결과: SIL 회귀를 돌릴 수 없어 이식 체인의 **런타임 동작 검증이 배선 확인 수준에 머문다**(ADR Verification §5 참조) | 2026-07-31 | 미해결 | ① 두 패키지의 의존 폐포를 먼저 조사한다(mux·translator 는 `rclcpp`+`trnav_msgs` 뿐이었으나 supervisor 는 상류에서 더 넓은 의존을 가질 수 있다). ② 폐포가 닫히면 같은 방식으로 `Common/` 에 이식하고 SIL launch 1종을 실제로 돌려 mux→translator→(sim) 흐름을 관측. ③ 그때까지 체인 검증 주장은 **「배선 확인」까지로만 표기**하고 「동작 검증」이라 쓰지 않는다 |
| debt-032 | 기술 | `src/Actuators/motor_control/motor_control/driver_node.py` `steer_home_counts` 기본값 · `backend.py:38` `steer_home: int = 0` | **조향 홈 미로드가 조용한 오판이 된다(motor_control 측).** YAML 이 안 실리면 `backend.WheelModule.steer_home` 이 기본값 **0** 으로 남고, 그 0 이 그대로 `0x607A` 목표로 나간다 — 실측 홈이 ≈7.87M counts 이므로 바퀴가 **≈−137°** 로 돈다. 「값이 없다」와 「값이 0 이다」가 구분되지 않는 것이 핵심이며, 3톤 차체에서 무해한 오차가 아니다. 같은 문제를 `can_relay` 는 2026-08-02 에 **「값 없으면 거부」**로 닫았다(`safety.DEFAULT_STEER_HOME = {}` + `driver_node` 기동 거부, 회귀 3건: `test_code_has_no_builtin_steer_home` · `test_steer_refused_when_home_not_configured` · `test_steer_refused_when_home_is_none_and_no_default`). `motor_control` 은 **타 세션 소유**라 본 세션은 값 갱신(구값 → 실측값)과 주석 정정까지만 하고 거동은 바꾸지 않았다 | 2026-08-02 | 미해결(타 세션 소유 — 진단·값 갱신만 수행) | 소유 세션이 상환: `can_relay` 와 같은 형태로 ① 코드 기본값 제거(빈 배열 = 미설정) ② 미설정 시 기동 거부 ③ 회귀 시험 동반. rclpy 함정 주의 — 빈 배열 기본값은 `BYTE_ARRAY` 로 추론돼 YAML 의 정수 배열 로드를 거부한다. `ParameterDescriptor(dynamic_typing=True)` 가 필요하며 `descriptor.type` 지정만으로는 안 된다(Humble 이 기본값 타입으로 덮어씀 — 2026-08-02 실기 기동 실패로 확인) |
| debt-034 | 기술 | `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:212-213` (`SEER_HOME_ZERO_N3 7882020` / `SEER_HOME_ZERO_N4 7859062`) · `:217` (`SEER_HOME_ZERO_TOL 57344`) | **이름이 「ZERO」인 상수가 0° 아닌 정착값을 담고 있고, 허용오차가 커서 펌웨어가 스스로 검출하지 못한다.** `SEER_HOME_ZERO_N3/N4` 는 실제로는 **호밍 후 정착 목표**(Seer 가 `0x607A` 로 지령하는 값, 2026-07-27 캡처 t=49.14 관측)이며 실측 0°(node3 **7,871,816** / node4 **7,840,087**, 2026-08-03)에서 **+10,204 / +18,975 counts = +0.178° / +0.331°** 떨어져 있다. 그런데 도달 판정 허용오차 `SEER_HOME_ZERO_TOL = 57344` 은 **정확히 1.0°**(57,344 counts/°)라 이 편차보다 3~5배 크다 ⇒ **펌웨어는 「0° 가 아니다」를 원리적으로 검출할 수 없다.** 이름이 사실과 어긋나는 것이 실질 피해다 — 이 두 값을 「조향 홈(0°)」으로 부른 것이 4주간 재실험 반복의 원인이었고(2026-08-02 종결 §), 2026-08-03 조사에서도 다시 0° 후보로 거론됐다. ⚠ **동작 결함 주장이 아니다** — 정착값을 목표로 두는 것 자체는 Seer 실측 거동과 일치한다. 등록 대상은 **이름·허용오차가 오인을 막지 못한다**는 점이다. 근거 `docs/homing/2026-08-03-can-relay-homing-assets.md` §2 · §10-5 · **§0-2** ⟵ **❌ 재정정 2026-08-03 17:00 (E6·E7)**: 아래 15:40 보강의 ① **σ 표기에 기준이 없다** — 원자료(`Log/home_experiment_260803_153319_summary.json` `runs[*].post` 10건) 재계산 결과 σ 2.8 / 3.2 는 **모표준편차(population) 기준**(정확히는 **2.80 / 3.21**)이고, **표본표준편차는 2.95 / 3.38** 이다. 관측 원값은 node3 `7,882,021` ×8 · `7,882,014` ×2(중앙 7,882,021 / 평균 7,882,019.6), node4 `7,859,065` ×8 · `7,859,058` ×2(중앙 7,859,065 / 평균 7,859,062.9). ② **「결함이 아니라 설계 동작이다」는 과잉 확정이다** — 실측이 보증하는 것은 「축이 펌웨어 상수 `SEER_HOME_ZERO_N3/N4`(`Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:212-213` = 7,882,020 / 7,859,062)에 **node3 +1 c · node4 +3 c 로 재현성 있게 정착한다**」까지이며, **그 상수가 옳다는 것은 실측에서 나오지 않는다**(우리가 써 넣은 값이다). ⚠ **그리고 이 표현은 debt-016 과 정면 충돌한다** — debt-016(본 표 위쪽 행) 및 「[2026-07-27 실기 검증] debt-007 부분 판정」 절은 **같은 +0.178° / +0.331°** 를 「`homing_tol` 5°·`settle_tol` 3° 어느 게이트로도 검출되지 않는 **영구 미검출 오프셋**」으로 등록해 두었다. ⇒ 표현을 **「재현되는 정착 동작(상수 적정성은 별건 — debt-016)」**으로 완화하고, **「결함이 아니다」로 인용하지 않는다.** 본 항목(debt-034)의 **등록 사유·미해결 상태는 그대로 유지**된다. 근거 `docs/homing/2026-08-03-can-relay-homing-assets.md` **§0-0-3**. — 이하 15:40 원문 이력 보존 — ⟵ **✅ 보강 2026-08-03 15:40 (판정 불변, 근거만 굳음)**: 호밍 **10회 연속** 실측에서 정착값이 node3 **7,882,021**(σ 2.8 c) · node4 **7,859,065**(σ 3.2 c) 로 **10회 재현**됐다 — σ ≈ 3 counts ≈ **0.00005°**. 조향 0°(`[7871815, 7840086]`) 대비 편차 **+0.178° / +0.331°** 가 계산이 아니라 **반복 실측**으로 확정됐고, 펌웨어 상수 `SEER_HOME_ZERO_N3/N4`(7882020 / 7859062)와 **1~3 counts 로 일치**한다. ⇒ 「호밍은 조향을 0° 가 아니라 이 지점에 놓는다」는 **결함이 아니라 설계 동작**이며, 본 항목의 등록 사유(이름이 사실과 어긋남 · 허용오차 1.0° 가 이 편차를 검출 못 함)는 **그대로 유지**된다. 산출 `Log/home_experiment_260803_153319.jsonl` · `_summary.json` | 2026-08-03 | 미해결 | ① 상수명을 사실대로 개명(`SEER_HOME_SETTLE_N3/N4` 등)하고 「0° 가 아니다 · 실측 0° 는 `[7871815, 7840086]`」 주석을 인접 배치 — 펌웨어 재빌드·플래시 동반이므로 다른 펌웨어 변경과 묶어 1회로 처리. ② 정착 도달 판정 허용오차와 **0° 검증**을 분리한다 — 도달 판정은 현행 1.0° 유지, 0° 대조는 별도 진단으로 노출(정착값 − 실측 0° 를 로그로 남김). ③ 개명 전까지 문서·주석에서 이 상수를 **「홈」·「0°」로 인용 금지**(반드시 「호밍 후 정착값」 병기) |
| debt-035 | 기술 | `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:219` (`SEER_HOME_CW_ENABLE 0x86`) · `:360-364` · **`:391-402`(WAIT 하강에지 검출)** · `SEER_HOME_ATHOME_S`·`seer_home_athome_mask` | **❌ 정정 2026-08-03 15:40 (최종) — 사유를 「원인 미상」으로 되돌리고 우선순위를 낮춘다.** 오늘 사유가 두 번 교체됐고 **둘 다 반증**됐다: ① 「CiA402 `Switch on disabled` 라 막힌다」(→ 14:19 반증) ② 「축이 이미 홈이라 무동작 즉시 완료 → 에지 미발생 → 타임아웃」(→ 15:25 반증, 아래 15:40 확정). **호밍 10회 연속 실측(15:33~15:40)에서 10/10 성공 · 소요 35.0 s(편차 0.17 s) · 리밋 도달 10회 모두 DI `0x01`→`0x09`** — 즉 **호밍은 정상 동작한다.** 09:58 의 `ERR_TIMEOUT` 1회가 **유일한 실패**이고 이후 **12회 연속 성공**(본 10회 + 14:46 · 15:25 · 15:33 기준선) — **재현되지 않는다.** ⟵ **❌ 재정정 2026-08-03 17:00 (E1·E4)**: 「**12회 연속**」은 **거짓이며 12회 연속**이 맞다. 「15:33 기준선」은 호밍이 아니라 **레지스터 스냅샷**이기 때문이다 — `Tools/docking_field_kit/orin_home_experiment.py:390` `base = snapshot(rig, "baseline")` 이고 `snapshot()`(`:259-275`)은 `pos_median()`·`sdo_read()` 만 호출하는 **판독 전용** 함수다. 원자료 재확인 결과 **오늘 호밍 시도 13 / 성공 12 / 실패 1**(09:19 `…_091956_summary.json` `repeat=0`·`runs=[]` → 호밍 0회 / 09:58 `…_095815_summary.json` `final_state=6` → 실패 1 / 14:46 `homing_edge_260803_144602.json` `final_state=5`·`elapsed=37.0` → 성공 1 / 15:25 `homing_edge_260803_152520.json` `final_state=5`·`elapsed=34.91` → 성공 1 / 15:33 `…_153319_summary.json` 10건 전부 `final_state=5` → 성공 10 / 나머지 `homing_edge` 6건은 `fsm_trace=[]` 이고 `accepted`·`elapsed` 키가 없어 **호밍 미개시**). **「10회 연속 10/10」 자체는 유효**하다. 또한 「소요 35.0 s」는 **평균 35.07 s · 중앙 35.05 s**(범위 34.99~35.16, 폭 0.17 s)가 정확하다. **본 항목의 판정(사유 「원인 미상」 환원)은 이 정정으로 바뀌지 않는다.** 근거 `docs/homing/2026-08-03-can-relay-homing-assets.md` §0-0-1. ⇒ **09:58 실패의 원인은 현재 미상**이며, 그 1회를 설명하는 확정된 기전은 없다. ⚠ **운영상 이슈가 아니다** — `ERR_TIMEOUT` 은 깔끔한 terminal 이라 **재시도로 충분**하다. 따라서 본 항목은 **미해결 유지 · 우선순위 낮음**으로 둔다. 펌웨어에 추가된 「이미 홈」 종료 조건(`SEER_HOME_ATHOME_S` · `seer_home_athome_mask`)은 **무해함이 실증**됐으나(10회 정상 경로 그대로 동작) **필요성은 미확인**이다 — 10회 실측에서 **발동조차 하지 않았다**. **보험으로 존치하되 「09:58 실패를 고쳤다」고 주장하지 않는다.** 근거 `docs/homing/2026-08-03-can-relay-homing-assets.md` §0-1 · §0-4 · §0-5, 산출 `Log/home_experiment_260803_153319.jsonl` · `_summary.json`. — 이하 원문 이력 보존 — **❌ 정정 2026-08-03 14:19 — 아래 원래 사유(CiA402 차단)는 반증됐다. 대체 사유는 「에지-온리 완료 판정」이다(§신규 절 참조).** 원 사유(이력 보존): **호밍 시퀀서가 「드라이브가 이미 `Operation enabled` 이다」를 암묵 전제하며, 그 전제는 코드·문서 어디에도 기재돼 있지 않다.** ENABLE 단계가 `0x6040 = 0x86` **한 발**로 끝난다. `0x86` 은 `0x06`(Shutdown) + **bit7(Fault reset)=1** 이라 Fault reset 이 우선 해석되어 **Shutdown 이 성립하지 않는다** ⇒ CiA402 `Switch on disabled`(statusword bit6=1)를 벗어나지 못한다. 표준 천이는 `0x06`(Shutdown) → `0x07`(Switch on) → `0x0F`(Enable operation)이며 각 단계 statusword 확인이 필요하다. **2026-08-03 실기 실측**: 서보 off 상태(node3·4 `0x9450`, node1·2 `0x8050` — 4축 전부 `Switch on disabled`)에서 호밍 실행 시 프레임은 설계대로 정확히 발행됐으나(`0x6040=0x86` → `0x6099=2500` → `0x60FB:04=1`, t=1.048 s) **125초 내내 statusword 변화 0건 · SDO ABORT 0건 · `0x6064` 불변 · `done_mask` 전 구간 `0x00`** 으로 **120초 소모 후 `ERR_TIMEOUT`**. 캡처 `Log/home_experiment_260803_095815.jsonl`(66,614 프레임). Seer 도 같은 구간 `0x3F` 만 96회 보내 마찬가지로 막혀 있다 ⇒ **버스상 누구도 `0x06` 을 보내지 않는다.** ⚠ 펌웨어 WAIT 로직(`0x6041` bit15 0→1 전이만 완료로 인정)은 **정확히 동작했다** — 결함은 그 앞단이다. 근거 `docs/homing/2026-08-03-can-relay-homing-assets.md` §8-2 · §8-3 · §9-5 | 2026-08-03 | **미해결 (우선순위 낮음 — 2026-08-03 15:40 하향)** | **❌ 정정 2026-08-03 15:40 — 상환계획 최신본**: ① 추가 조치 **없음**. 호밍이 10/10 정상 동작하므로 **관찰만 한다** — `ERR_TIMEOUT` 이 다시 나오면 그때 `0x6041` 전체·`0x6000:01`·`0x603F`·`0x6064` 를 **동시 취득**해 기록한다(재현 자료 확보가 유일한 진전 경로). ② 「이미 홈」 종료 조건은 **되돌리지 않고 보험으로 존치**하되, 문서·주석·커밋 메시지에서 **「실패를 고쳤다」로 인용 금지**(필요성 미확인). ③ 「드라이브 상태 전제」 명문화(아래 원 계획 ③)는 **그대로 유효**하다 — 무기재 자체가 부채다. ④ **「호밍이 안 되는 이유」를 단정하지 않는다** — 오늘 세 번 틀렸다(Switch on disabled / 0x6098=0 / 이미 홈). — 이하 원문 이력 보존 — ⚠ **수정 순서 주의 — 펌웨어부터 고치면 안 된다.** ① **현장 조치 선행**: 로봇을 서보 on(운전 준비) 상태로 만든 뒤 호밍 1회차 재시도 → 원인이 「시스템 상태」인지 「펌웨어」인지 먼저 가른다(펌웨어 변경 0). ② 가른 뒤 필요하면 ENABLE 단계를 CiA402 표준 천이(`0x06`→`0x07`→`0x0F`, 각 단계 statusword 확인 후 진행)로 교체. **①을 건너뛰고 ②를 하면 「의도된 서보 off(대기)」 상태의 3톤 로봇을 임의로 기동시키는 기능**이 된다. ③ 어느 쪽이든 「드라이브 상태 전제」를 코드 주석·문서에 명문화한다(현재 무기재가 부채의 핵심) |
| debt-036 | 이해 | **❌ 재정정 2026-08-03 17:00 — 아래 15:40 정정의 「1회 관측 · 재현 안 됨」은 거짓이므로 하향 근거를 철회한다(E2).** 원자료 재파싱(SDO upload `0x583`/`0x584`, index `0x6064` sub 0) 결과 `0x6064`=0 은 **최소 3개 캡처에서 재현**된다: 09:19 `Log/home_experiment_260803_091956.jsonl` node3 **50/50 · node4 50/50 (100 %)** · 09:58 `Log/home_experiment_260803_095815.jsonl` **12,220/12,220 · 12,211/12,211 (100 %)** · 10:08 `Log/seer_homing_260803_100813.jsonl` **10,327/10,327 · 10,327/10,327 (100 %)** — 세 캡처 모두 `0x6041` = 37968(`0x9450`) bit15=1 전량이고 **구동축 node1·2 의 zero 는 0건**이다. 11:38 판다 리부팅 **이후**인 14:43 `Log/homing_edge_260803_144305_can.jsonl` 에도 node3 **2/74** · node4 **2/68**, 같은 파일 `before` 스냅샷의 **node4 `pos=0`, `sw=37968`, `bit15=1`**. ⇒ **「09:58 단 1회 관측이라 근거가 약하다」는 판단은 사실 오인 위에 서 있었다 — 하향 근거를 철회한다.** ⚠ **다만 인과는 여전히 미판정이며, 양쪽 다 미판정이다** — `0x6064`=0 이 관측되던 조건에서도 오늘 호밍이 **12회 성공**했으므로 「이것이 호밍을 막는다」도 성립하지 않는다(15:25 의 승격 철회는 그대로 유지). ⚠ **구분 필수**: 15:33 성공 10회 캡처에도 node3 zero 32,801 건이 있으나 **전부 호밍 진행 창(run pre~post) 안**이고 **창 밖 zero 는 0건**이다 — 호밍 중 0 고정은 알려진 정상 동작이므로 위 **정지 상태 100 % zero** 와 같은 것으로 세지 말 것. **우선순위 재판정은 사용자 결정 사안으로 남긴다(본 재정정은 근거만 정정한다).** 근거 `docs/homing/2026-08-03-can-relay-homing-assets.md` **§0-0-2**. — 이하 15:40 원문 이력 보존 — **❌ 정정 2026-08-03 15:40 — 우선순위 하향 · 「호밍을 막는다」 단정 철회.** 15:25 에 본 항목을 「호밍 실패의 실질 원인 후보」로 **승격**했으나, 15:33~15:40 **호밍 10회 연속 성공(10/10, 35.0 s)** 으로 그 근거가 약해졌다. `0x6064`=0 (bit15=1 동반) 은 **09:58 단 1회 관측**이고 **재현되지 않았다** — 관측 2점의 상관을 원인으로 승격한 것이 성급했다. ⇒ 「`0x6064`=0 래치 상태에서는 호밍이 걸리지 않는다」는 **단정을 철회**한다(래치→호밍 불능인지, 공통 원인의 두 증상인지, 무관한 우연인지 **전부 미판정**). 본 항목은 **미해결 유지 · 추적 우선순위 낮음**이다 — 재현 자료가 없으면 진전이 없고, 호밍이 정상 동작하므로 운영상 급하지 않다. 운용 보호는 이미 있음(`safety.position_trustworthy()`). 근거 `docs/homing/2026-08-03-can-relay-homing-assets.md` §0-1 · §0-5, 산출 `Log/home_experiment_260803_153319.jsonl`. — 이하 원문 이력 보존 — **❌ 정정 2026-08-03 — 「전원 사이클로만 풀린다」는 반증됐다(§신규 절).** 조향 드라이브(node3·4) `0x6064` 보고 동작 — 저장소 코드 아님(하드웨어/드라이브 펌웨어). 관측 기록 `Log/home_experiment_260803_095815.jsonl` · `Log/seer_homing_260803_100813.jsonl` · `docs/homing/2026-08-03-can-relay-homing-assets.md` §9-3 | **조향축이 어떤 조건에서 위치를 0 으로 보고하는 「래치」에 빠지고, 전원 사이클로만 풀린다 — 조건·원인 미판정.** 2026-08-03 실측: **리부팅 전후 statusword 가 동일 `0x9450` 인데 `0x6064` 만 0 → 실값(7,871,823 / 7,840,052)으로 바뀌었다.** 즉 이 현상은 statusword 로 설명되지 않는다 — 기존 후보였던 「호밍 중(`0x6041` bit15=0)」도, 「미-enable」도 아니다. 미-enable 가설은 같은 회차가 직접 반증했다: **같은 `Switch on disabled` 인데 구동축(node1·2 `0x8050`)은 실위치(−655,844 / −650,517)를 반환**하고 조향축(`0x9450`)만 0 이었다. 바뀐 것은 **전원 재투입뿐**이다(구동축 증분 카운터가 −655,844/−650,517 → 380/−380 으로 리셋된 것이 전원 사이클의 증거). 부수 확정: 조향축은 **절대 엔코더**(전원 사이클을 넘어 7.87 M 유지), 구동축은 증분. ⚠ 본 항목은 debt-007 을 낳은 관측군(「부팅 직후 `0x6064`≈0」·「호밍 중 0 고정」·「판다 read −1,517」)의 **공통 원인 후보**이나 **미검증**이다 — debt-007 종결(기준계 판정)을 되돌리는 것이 아니라, 그 종결이 「유력 후보이지 확정이 아니다」로 남겨둔 잔여를 승계한다 | 2026-08-03 | **미해결 (우선순위 낮음 — 2026-08-03 15:40 하향)**  — ⇒ **✅ 2026-08-03 19:45 종결 (원인 규명)**. 아래 상환계획 말미의 「종결」 절 참조. 상태 이력은 덮어쓰지 않고 append 한다(debt SOP 룰 4).| **❌ 정정 2026-08-03 15:40**: 15:25 의 「우선순위 상향」은 **취소**한다(호밍 10/10 성공으로 근거 약화). 계획 자체는 유지하되 **기회 관측**으로 격하 — `0x6064`=0 이 다시 관측될 때 아래 ①을 수행한다. 재현 없이는 진전 불가이며, **재현되지 않는 1회 관측을 원인으로 인용하지 않는다.** — 이하 원 계획 유지 — ① **래치 진입 조건 재현** — 현재 실값을 보고하는 상태에서 시작해, 어느 조작(제어권 취득 / 호밍 시도 / CAN 단절 / 서보 off↔on)이 0 래치를 만드는지 1변수씩 바꿔가며 관측. 매 관측에 **`0x6041` 전체 · `0x6000.1` · `0x603F` 를 동시 취득**(bit15 만 보면 구분 불가 — debt-007 §① 결론). ② 재현되면 드라이브 벤더 매뉴얼에서 대응 동작을 찾고(`Handbook V7.0` 위치 오브젝트 절), 없으면 벤더 문의. ③ **36초 CAN 단절로는 재현되지 않았다**(2026-08-03 실측, statusword·`0x6064` 변화 0건) — 이 반례는 재현 시나리오에서 제외. ④ 판정 전까지 **`0x6064`=0 을 「호밍 중」의 증거로 인용하지 않는다**. 운용상 보호는 이미 있음 — `can_relay` 의 `safety.position_trustworthy()` 가 bit15=0 구간의 `0x6064` 를 상위로 흘리지 않는다(회귀 `test_position_untrusted_while_homing`)  ‖ **✅ 종결 2026-08-03 19:45 — 원인은 「아침에 드라이브가 죽어 있었다」였다.** 사용자 진술: 「아침에는 드라이버가 죽었다고」·「그래서 내가 기존 기록 다 있는데도 다시 실험한 거잖아」. ⇒ 2026-08-03 오전 캡처의 `0x6064`=0 은 **정상 동작 중인 드라이브의 이상 보고가 아니라, 죽어 있던(재기동 중) 드라이브가 낸 값**이다. 「전원 사이클 래치」·「emulate 동결」 가설은 **둘 다 불필요**했다. **뒷받침 관측**: ① `Log/home_experiment_260803_095815.jsonl` 에 **node1 `BOOTUP`(0x701, 데이터 0x00) 1건** — 그 시각 드라이브가 재기동 중이었다는 직접 증거. 오후 정상 캡처(`…_153319.jsonl`)에는 `BOOTUP` 이 **0건**이다. ② 오전 3개 캡처 모두 SDO abort **0건**이라 통신은 살아 있었다 — 전원은 들어왔으나 축이 살아있지 않은 상태와 정합. ③ **재현 시험 실패(= 정상)**: `Tools/docking_field_kit/orin_frozen_readback.py` (2026-08-03 19:05, 읽기 전용·무동작)로 제어권 미취득/취득/반환 3구간을 각 7회 판독 → **0 발생 0/7 × 3구간 × 2노드** (node3 7,871,810 · node4 7,840,084~91). 산출 `Log/frozen_readback_260803_190509.json`. ④ 같은 날 18:55 `orin_steer_crosscheck.py` 에서 CAN·Seer 1040·1005 **세 값 모두 정합**(Seer 0.000°). ⚠ **폐기(인용 금지)**: 「전원 사이클로만 풀리는 래치」 · 「제어권 취득 시 emulate 동결값이 0 을 만든다」 · 「운용 보호는 이미 있음(`safety.position_trustworthy()`)」 — **셋 다 거짓**이다. 특히 마지막은 내가 2026-08-03 15:40 에 쓴 거짓 서술로, 그 함수는 `bit15=1` 이면 값을 그대로 신뢰하므로 **이 현상을 전혀 걸러내지 못한다**(`safety.py:126-133`, 시험 `test_safety.py:100` 이 `0x9450`→True 를 고정). ⇒ **잔여 조치는 debt-037**(값 범위 가드)로 분리 등록한다.|
| debt-033 | 기술 | `src/MES/csm/csm/runtime/tasks/equipment_monitor.py` · `csm/adapters/base.py` `get_station_status()` | **The equipment monitor samples a level; the received specification is edge-triggered.** A machine requests a robot by *changing* a value — the request is the transition itself, and the machine clears the signal once it believes it was heard. `EquipmentMonitorTask` polls at 1 Hz and reads state. A change that occurs and reverts between two samples is **missed entirely, while the machine believes the call succeeded** — a silently dropped transport job with no error anywhere. **Why this is not a tuning problem**: polling faster narrows the window without closing it, and the whole `EquipmentAdapter` interface is poll-shaped (`get_station_status(id)` returns a value, not an event), so there is nowhere for a transition to be reported. Correct against `MockEquipment`, known-incomplete against the real protocol | 2026-08-04 | 미해결 | ① Add a push path to `EquipmentAdapter` — a callback or queue the adapter fills on transition, which the FSM drains. Keep the FSM protocol-free (the point of the adapter). ② Implement it with **OPC-UA subscriptions** for the machine-tool link; confirm the equivalent for the S7 pack-line link, which may genuinely have to poll. ③ If any link must poll, latch the transition **inside the adapter** so it survives until read, rather than exposing the sampling race upward. ④ Do **not** close this by reducing the poll period — that hides it. ⑤ Test: drive a mock that raises and clears a request between two ticks and assert the job is still created. **⚠ 2026-08-04 정정 — ①②는 무효.** 회의에서 직접 질의·응답으로 확인된 바, 설비 인터페이스는 **이벤트 방식이 아니다.** 양측이 비트를 세워 서로를 호출하는 공유메모리식 구조이며, CSM 은 **일정 간격으로 계속 스캔**해야 한다("계속 스캔을 하고 있어야 돼요"). 따라서 구독(subscription) 전환은 해법이 아니고 **폴링이 정본 설계**다. 남는 문제는 폴링 자체가 아니라 **주기**다 — 요청이 전이(transition)이고 설비가 수신됐다고 판단하면 신호를 내리므로, **폴링 주기가 안전여유 전부**다. 재설정된 상환계획: ⓐ 설비의 **최소 신호 유지 시간**을 확인한다(현재 미확보) — 그 값이 최대 허용 폴링 주기를 정한다. ⓑ 1 Hz 는 근거 없는 기본값이므로 그 수치가 나오기 전까지 신뢰하지 않는다. ⓒ 어댑터 내부에서 전이를 **래치**해, 상위가 읽어갈 때까지 유지하여 샘플링 경합을 위로 노출하지 않는다. ⓓ 위 ⑤ 시험은 그대로 유효 |
| debt-034 | 기술 | `src/MES/csm/csm/adapters/base.py` `EquipmentAdapter.send_station_command()` → `bool` | **명령에 대한 acknowledgement 가 프로토콜에 존재하지 않는데 인터페이스는 있는 것처럼 되어 있다.** 2026-08-04 회의 직접 질의 확인: "아크 없어요… 샌드에 대한 아크널리지가 없어요. 얘는 TCP 통신이 아니에요, 메모리 공유 방식이거든요." 한쪽이 비트를 세우면 상대가 응답 비트를 세우는 **공유메모리식 핸드셰이크**가 프로토콜의 전부이며, 전송 계층 확인 응답이 없다. 현재 `send_station_command()` 는 `bool` 을 돌려주고 `Done.on_enter` 는 그 값을 "수락됨"으로 읽어 경고를 남긴다 — 실제 프로토콜에서는 그 참/거짓을 **알 수 없다.** | 2026-08-04 | 미해결 | ① 명령의 성공 판정을 **기대 상태 변화의 읽기 확인(read-back)** 으로 재정의하고 타임아웃을 붙인다. ② 인터페이스 반환형을 즉시 판정(`bool`)에서 미결·확인·타임아웃을 표현할 수 있는 형태로 바꾼다. ③ Mock 을 실제 프로토콜처럼 **무응답 가능**하게 만들어 현재 코드가 거짓 성공을 보고하는지 시험으로 드러낸다. ④ 확인 전까지 "설비가 명령을 수락했다"는 서술을 문서·로그에서 쓰지 않는다 |
| debt-035 | 의도 | CSM 전반 — `job.py`, `job_store.py`, 영속성 없음 | **숙성(curing) 시간 관리 요구사항이 설계에 전혀 없다.** 2026-08-04 회의에서 신규 확인: 일부 자재는 다음 공정 투입 전 **6시간 또는 10시간** 숙성해야 하며, CSM 이 자재별 경과 시간을 관리해 시간이 찬 것만 내보내야 한다. 랙 포트는 `비어있음 / 예약됨 / 보유중 + 경과시간` 상태를 보고하고, **정전 후 복전 시에도 경과 시간이 보존**되어야 한다(서버가 기억할지 랙 PLC 가 기억할지 미정). 또한 목적지 랙이 만실이면 다른 구역으로 보내 그쪽에서 숙성시키되 **이중 숙성은 금지**다. 현재 job 은 분 단위·메모리 전용이며 재시작하면 전부 소실된다 — 시간 단위 영속 상태를 담을 그릇이 없다 | 2026-08-04 | 미해결 | ① 숙성을 job 이 아닌 **자재(item) 의 속성**으로 모델링한다 — job 은 이동이고 숙성은 체류다. ② 경과 시간의 **정본 보유자**를 결정한다(랙 PLC vs 서버). 회의에서 미결. ③ 영속성을 도입한다 — 재시작·정전 후 복구 시험을 회귀로 포함한다. ④ 이중 숙성 방지 규칙을 명시적 상태로 표현한다(숙성 완료 플래그가 자재를 따라다니게). ⑤ 숙성 불요 공정도 있으므로 공정별로 켜고 끌 수 있어야 한다 |
| debt-038 | 기술 | `src/Comm/CAN/can_relay/can_relay/backend.py:277-292` (`RelayBackend.set_motor_cmds` 의 `profile_vel` 처리) | **상류가 보낸 `profile_vel` 을 반영하지 않는다 — 지금은 고지만 한다.** `/motor/low_cmd`(`trnav_msgs/MotorCmdArray`)의 다섯째 필드 `profile_vel` 을 백엔드가 받아 놓고 CAN 으로 내보내지 않는다. 조향은 PP(Profile Position) 모드라 실제 이동 속도는 드라이브에 **마지막으로 기록된 `0x6081`** 이 결정한다 — 브링업 `steer_init_frames` 의 30000 또는 호밍의 `home_profile_vel` 2500 이 그대로 남아 있다. 즉 상류가 프로파일 속도를 낮춰 보내도 축은 이전 속도로 움직인다. 2026-08-03 리뷰(M1) 전에는 **아무 흔적 없이** 버려졌고, 지금은 값이 바뀔 때 로그 1줄을 남긴다(에지 트리거 — `rejected_commands` 에는 세지 않는다. 정상 지령이 거부로 집계되면 그 지표가 죽는다). 반영 자체를 미루는 이유는 **매 지령마다 `0x6081` 을 덧붙이는 것이 실기 미검증 변경**이기 때문이다 — 20~50 Hz 로 SDO 가 늘고, 브링업 경로는 이미 실기 검증 이력 0 이다(debt-017). 회귀: `test/test_backend_method35.py::test_profile_vel_notice_is_logged_not_counted_as_rejection` · `::test_profile_vel_notice_is_edge_triggered` | 2026-08-03 | 미해결 | ① 잭업 상태 HIL 게이트에서 `0x6081` 동반 송신을 켜고 상류 지령값 ↔ 실측 조향 속도를 대조한다. ② 대조 통과 시 **값이 바뀔 때만** `0x6081` 을 보내는 에지 송신으로 구현(매 틱 송신 금지 — 프레임 예산). ③ 그 전까지 문서·주석에서 「상류 profile_vel 이 반영된다」로 인용 금지. ④ ✅ **2026-08-05 확인 완료 — 상류는 고정값을 보낸다.** `amr_motor_cmd_translator_node.cpp:64` 가 `steer_profile_velocity`(기본 **30000**)를 **기동 시 1회** 읽어 `steer_profile_vel_` 에 담고, :144·:151 에서 조향 2축에 그대로 싣는다. 재대입 지점 없음 · 파라미터 콜백 없음(`add_on_set_parameters_callback` 0건) · 구동축엔 넣지 않는다. ⇒ **매 지령 `0x6081` 동반 송신은 불필요하다.** 본 부채는 「지령마다 반영」이 아니라 **「런치 상수를 1회 반영」** 으로 축소된다 — SDO 부하 우려(20~50 Hz 증가)가 사라지므로 ①의 잭업 HIL 전제도 불필요하다. 남는 검증은 **제자리 조향 소요시간 대조**뿐이다(2500 ↔ 30000 은 12배라 로그로 바로 갈린다). ⚠ 다만 **어느 값이 현재 드라이브에 남아 있는지**는 여전히 미확인이다 — 브링업은 비활성(`allow_bringup: false`)이고 호밍은 `home_profile_vel` 2500 을 쓴다 |
| debt-039 | 기술 | `Tools/amr_test_gui/gui.py` ↔ `src/Comm/CAN/can_relay/can_relay/ui/gui_node.py` (같은 화면 2벌) | **시험 GUI 가 두 벌 공존한다 — 실기 동등성이 확인될 때까지 의도된 중복이다.** ROS2 이식본을 넣으면서 원본을 지우지 않았다(ADR `docs/adr/2026-08-03-amr-test-gui-ros2-port.md` §Decision ⑤) — 같은 조작에 대해 두 구현이 같은 CAN 프레임을 내는지 **잭업 실기 대조**가 끝나기 전에 원본을 없애면 비교 대상이 사라지기 때문이다. 중복 실체: `WheelView`(바퀴 렌더 ~60줄)·`_toggle`·모터 표 생성·`JOG` 방향표·Seer 폴링 루프가 양쪽에 각각 있다. ⚠ **값 중복은 아니다** — 이식본은 `STEER_HOME`·`COUNTS_PER_DEG`·`VEL_PER_MMPS` 를 갖지 않고 도(°)·mm/s 로만 지령해 counts 환산을 드라이버에 맡긴다(원본 리뷰 Medium G4 의 사본 문제는 이식본에 없다). 남는 위험은 **한쪽만 고치는 것** — 예: 2026-08-03 에 고친 heartbeat 락 결함의 GUI 판(`gui.py:1026`)은 원본에 **그대로 남아 있다**(리뷰 High, `docs/code_review/amr-test-gui/2026-08-03.md`) | 2026-08-03 | 미해결 | ① 잭업 실기에서 ADR §Verification 게이트 4(두 구현의 CAN 프레임 바이트 대조)를 수행한다. ② 통과하면 원본을 폐기하고 본 부채를 종결한다 — 폐기 시점은 사용자 결정. ③ 폐기 전까지 **원본을 고칠 때 이식본도 함께 보는 것**을 규칙으로 한다(특히 조그 방향표 `JOG` 와 호밍 절차). ④ 원본 잔존 기간에는 원본의 High 4건(신선도·heartbeat 락·단발 송신·취소 부재)을 「알려진 제약」으로 취급하고, 새 시험은 이식본으로 한다 |
| debt-040 | 이해 | `src/Comm/CAN/can_relay/can_relay/backend.py` `halt_steer` (현재 위치를 조향 목표로 써 넣는 지점) ↔ 제어권 획득 직후의 `0x6064` 판독 | **제어권 획득 직후 첫 조향 판독이 26 ms 뒤 판독과 1.29° / 1.41° 달랐고, 그 첫 값이 정지 경로에서 조향 목표로 송신됐다 — 어느 쪽이 그 시각의 참인지 미판정.** **기준값(2026-08-03 오후 확정, 본 항목이 인용하는 정본)**: 실측 0° = node3 **7,871,816** / node4 **7,840,087** (11:44 `orin_steer_crosscheck.py`, Seer 0.000°, 2회 독립 실행 counts 일치, `docs/homing/2026-08-03-can-relay-homing-assets.md` §10-3) · 호밍 후 정착 = node3 **7,882,021**(σ 2.8 c) / node4 **7,859,065**(σ 3.2 c) (15:33~15:40 10회, 0° 대비 +0.178° / +0.331°, debt-034). **관측 A (22:29 실기, 드라이버 로그)**: engage 0.17 s 뒤 `~/stop` → `halt_steer` 가 **N3 7,871,810 / N4 7,840,091** 을 목표로 송신 — 오후 확정 0° 와 **6 c / 4 c 차**(≈0.000°). **26 ms 뒤** 종료 경로가 **N3 7,798,142 / N4 7,759,482** 를 읽어 목표로 송신. **관측 B (22:31 수동 판독, 송신 0건 20 s, CAN 2,109 샘플)**: node3 중앙 **7,798,136**(σ 24) · node4 **7,759,482**(σ 23) → 오후 확정 0° 대비 **−73,680 c / −80,605 c = 1.2849° / 1.4056°**, Seer 1040 **+1.285° / +1.406°** 와 부호 반전 정합. 같은 시각 Seer 1005 **r_steer(지령) 1.2605° / 1.4324°** — 즉 **Seer 가 그 각을 능동 지령 중**이라 바퀴가 거기 있는 것은 이상이 아니다. 산출 `Log/steer_xcheck_port_check.jsonl`. ⚠ **미판정 부분을 분명히 한다** — 22:29 시점의 독립 측정이 없다. 「첫 판독이 틀렸다」는 **추론**이며, 근거는 ① 26 ms 안에 1.3° 물리 이동은 비현실적 ② intercept 직전까지 Seer 가 1.26° 를 지령하고 있었다 두 가지뿐이다. **관측 B 는 22:31 의 상태를 말할 뿐 22:29 를 말하지 않는다.** ⚠ 역산식 `0° = CAN + Seer°×57,344` 로 0° 를 재도출하지 말 것 — **항등식이라 자세와 무관하게 같은 값**이 나온다(`docs/homing/…-homing-assets.md`:186-187, 도구 자체도 경고를 출력한다). ⚠ **실질 위험**: `halt_steer` 는 「현재 위치를 새 목표로 준다」로 축을 세우는데, 판독이 틀리면 **정지 명령이 축을 1.3° 움직이라는 지령**이 된다. 신선도 게이트(`NodeState.fresh`)는 못 걸른다 — 값은 방금 도착했고(신선) **내용만 옛것**이기 때문이다. 가설 2개(① 판다 freeze/emulate 캐시가 이전 값을 첫 응답으로 냄 ② 전환 순간 잔류 응답 파싱)는 **둘 다 미검증** — 인용 시 「가설」로 표기할 것. 관련 debt-036(같은 객체 `0x6064` 의 별건 이상) | 2026-08-03 | **종결 2026-08-05 — 전제 소멸** ✅ 위험 통로였던 「현재 위치를 조향 목표로 써 넣기」 자체를 제거했다(`docs/claude-mistake/2026-08-05-001`). 정지 경로는 이제 조향축에 프레임을 보내지 않으므로 **첫 판독이 틀려도 조향 목표가 되지 않는다.** 오전에 넣었던 bit15 게이트는 그 방식을 안전하게 만드는 것이었고 방식이 사라져 함께 제거됐다. 재현 자체는 완료했다 — engage 후 t=35 ms pos=0(sw=0x1050) → t=168 ms 참값(sw=0x9450), 차 +69.3°, `Log/first_read_260805_141539.json`. | ✅ ① **재현 완료 2026-08-05 14:15** — engage 후 t=35 ms 판독 pos=0(sw=0x1050, bit15=0), t=168 ms 참값 3,971,954(sw=0x9450). 차 **+69.3°**. `Log/first_read_260805_141539.json`. ✅ ② **게이트 추가** — `hold_steer_at_measured` 가 `S.position_trustworthy`(bit15)로 목표 후보를 거른다. 기존 방어 2종(시각 신선도·`stationary`)이 왜 못 막았는지는 `docs/verified_facts/2026-08-04-amr-test-gui-field-run.md` §debt-040 참조. 회귀 2건 + 돌연변이 검출 확인. ⚠ **게이트가 실기에서 발동하는 장면은 아직 못 봤다** — bit15=0 창이 간헐적이다(14:15 132 ms · 14:20 0 ms, 조건 미상). ③ 그 전까지 engage 직후 즉시 `~/stop` 금지(최소 0.5 s 대기)는 게이트가 생겨 **완화**되나 여전히 권고다. ④ 옛 계획: ① **재현 먼저** — `Tools/docking_field_kit/orin_first_read_check.py` **작성 완료·미실행**(실기 조작이라 사용자 승인 필요). ⚠ 2026-08-05 10:49 1차 시도는 **무효**다 — 다른 곳에서 로봇을 제어 중이어서 USB 송신이 36회 연속 실패했고, 그 상태의 판독(`pos=0`)과 종료 시 조향 목표 0 counts 는 경합의 산물이다(`Log/first_read_260805_104954.INVALID-contended.README.md`). 재시도 전에 **다른 제어 주체 부재를 먼저 확인**하고, USB 송신 실패가 나면 즉시 중단해 판독을 채택하지 않는다. engage 직후 `0x6064` 를 시간순으로 남겨 첫 판독↔안정 판독 차와 안정까지의 시간을 본다. 판정은 **오후 확정 0°·정착값 기준**으로 한다. ② 재현되면 `halt_steer` 에 **내용 신선도** 게이트 — 서로 다른 폴 주기 2회 이상 같은 값일 때만 목표 채택, 또는 engage 후 첫 N ms 판독 폐기. ③ 그 전까지 engage 직후 즉시 `~/stop`·`~/engage false` 를 호출하지 않는다(최소 0.5 s 대기). ④ 실기 구동 시험의 「조향 0° 전제」는 드라이버 판독으로 검사하지 말고 **송신 0건 수동 판독**으로 대조한다 |
| debt-041 | 기술 | `src/Comm/CAN/can_relay/can_relay/backend.py` `halt_steer` (이름) | **❌ 재분류 2026-08-03 23:00 — 이 항목의 알맹이는 부채가 아니라 실수였다.** 최초 등록(22:50)은 「도입 ADR 부재」·「이동 중 정지 미검증」을 부채로 적었으나, 둘 다 **명시 규칙 위반**(coding SOP §3 사전승인 · §5 검증 · 2026-07-27-002 §재발 방지 ④ 「단일 read 를 물리상태 진실로 신뢰 금지」)이다. 부채는 **알고서 미루기로 한 것**이고, 검증 없이 하드웨어 정지 경로에 지령을 넣은 것은 **검증 실패**다 — 지위가 다르다. ⇒ 그 두 건은 **`docs/claude-mistake/2026-08-03-003_halt-steer-inserted-without-verification.md`(rule-violation / verify-skip, status: open)** 로 이관했다. 사용자 지적: 「부채인가요? 실수인가요?」. **본 행에 남는 것은 이름 하나뿐이다** — `halt_steer` 인데 벤더가 정의한 Halt(controlword bit8)를 쓰지 않는다(마스터 Seer 도 Halt 를 안 쓰므로 **동작 선택 자체는 옳다**, 실측 `Log/homing_capture_220350.jsonl` 12,928회 중 bit8 **0회**). 이름만 사실과 어긋나 오해를 부른다. ⚠ 「우회 기법·근거 없음」이라는 22:50 서술은 **거짓이며 철회**됐다(경위 `docs/claude-mistake/2026-08-03-002`) | 2026-08-03 | **종결 2026-08-05 — 함수 자체 제거** | ✅ ① 이름을 `hold_steer_at_measured` 로 바꿨고, 이어서 **함수가 하던 조향 프레임 송신을 통째로 제거**했다(`release_steer_target` 은 재송신 중단만 한다). 이름 문제의 원인이던 「Halt 를 쓰지 않으면서 Halt 처럼 읽히는 함수」 자체가 없어졌다. 옛 기록: 정의부 docstring 에 「Halt(bit8)를 쓰지 않는다 · 마스터도 안 쓴다(캡처 12,928회 중 0회) · 옛 이름 halt_steer」를 명시. 호출부 9곳·시험 4건 갱신, **381 passed**. ⚠ 과거 문서(실수 기록·날짜 붙은 리뷰·당시 실행한 grep 명령)의 `halt_steer` 표기는 그 시점 사실이므로 **고치지 않았다**. ② 옛 계획: **실측을 기다릴 이유가 없다** (❌ 정정 2026-08-03 23:05: 종전 계획은 「이동 중 거동 실측 후에」였는데, 그 실측은 정당화의 전제조건이 아니다 — 이동 중 목표 변경은 Handbook V7.0:9049-9050 이 보증한다. 사용자 지적 「근거가 없는데 왜 실측하니?」). ② 그 전까지 docstring·문서에서 「Halt 를 쓴다」로 읽히지 않게 표기한다 |
| debt-043 | 이해 | `src/Navigation/mcl2d_core/src/motion_model.cpp` `supplyControlVar()` | **원본 대조 잔여 1 ulp — 300표본 중 1표본의 `trans`·`direction` 2값.** 2026-08-07 에 주 원인이던 dθ 는 **해소**됐다: 원본은 `Normalize(cur.angle − prev.angle)` 결과를 `atan2(sin, cos)` 에 **한 번 더** 통과시킨다(`33d91c` → `33dca3`). 원본 `Normalize` 를 dlopen 해 직접 대조한 결과 **while 루프와 비트 동일**(2000/2000)이었고(어제 적은 floor 재현 1801/2000 은 내 오독), 그 조합으로 dθ 불일치 **17 → 0**, 전체 **17 → 2 / 1800**. 잔여 2값은 같은 표본에서 나오며 `dx_b`·`dy_b` 파생이다. 같은 수치를 **하드코딩해 단독 실행하면 원본과 4/4 비트 일치**하고, 하네스 안에서는 **하네스가 직접 계산한 값도 우리 함수와 같다**(둘 다 원본과 1 ulp 차) — 즉 식의 문제가 아니라 그 표본에서 원본이 다른 경로를 타는 것으로 보이나 미확정 | 2026-08-06 | 미해결(축소) | ① 실패 표본의 입력을 hex(`%a`)로 고정해 단독 재현 → 원본 `dx_b`(0xf0)·`dy_b`(0xf8)부터 다시 대조. ② 원본이 그 입력에서 타는 분기(`33d93c` 조건, dt 비교 상수 `0x59ce38`)를 확인. ③ 현재 상태는 「1,798/1,800 비트 일치」로 표기한다 — 「완전 일치」라고 쓰지 않는다 |
| debt-044 | 기술 | `src/Navigation/mcl2d_ros2` · `Tools/mcl2d_standalone` (원본 `MCLoc::DoMoveAction` 대비) | **원본이 오도 콜백마다 수행하는 `moveRobotAccordingToMotion` 을 이식하지 않았다.** 원본은 파티클과 **별개로** 로봇 추정 자세(StateVar2D)를 같은 결정론 식으로 전진시키고(`0x33f4b0`, `DoMoveAction` @0x3d7d39), 파티클 평균은 스캔 갱신 주기에만 반영한다. 우리는 매 오도 콜백에 전체 필터를 돌려 파티클 평균만 낸다 — 출력 자세의 시간 특성이 다를 수 있다(특히 스캔이 오도보다 느릴 때). 같은 계열로 `doOffsetMove`/`setLaserMoveOffset`(라이다 장착 오프셋 보정, 조건부 경로)·`moveAccordingToMotion`·`getRealControlVar` 도 미이식 | 2026-08-06 | 미해결 | ① 원본에서 이 자세가 어디로 나가는지(발행 메시지) 확인 → 우리 `/mcl_pose` 와 같은 소비자인지 판정. ② 같은 소비자면 이식, 아니면 「의도적 미이식」으로 ADR 에 못박고 본 항목 종결 |
| debt-045 | 이해 | Tongyi 구동축 node1(FrontWalk) 하드웨어 | **구동축 과부하 알람의 물리적 원인 미규명.** node1 이 `0x603F=0x0080` Motor overload alarm 으로 떨어져 양 구동축이 `operation enabled=0` 이 됐다(Seer 알람 `Motor Error:FrontWalk-0x80` 로 독립 확인). Handbook §6.6.4 는 '부하가 정격을 넘는지 확인하고 과부하 보호 시간 설정을 조정' 을 대처로 든다. **상태는 `_enable_drives()` 로 복구했고 주행도 확인됐으나 왜 과부하가 났는지는 모른다.** 정지 중 node2 가 −16.07 A 를 먹던 관측도 미해명 | 2026-08-09 | 미해결(현상 재발 시 대응 — 사용자 판단) | 재발하면 그 시점의 `0x603F`·`0x6078`(전류)·부하 조건을 함께 기록한다. 반복되면 기구 물림·정격 초과를 점검하고 필요 시 과부하 보호 시간 설정을 검토. 복구 수단(`구동축 활성화` 버튼·제어권 획득 시 자동 복구)이 있으므로 운용을 막지 않는다 |
| debt-046 | 기술 | Tools/amr_test_gui/mutation_check.py · test/{test_drive_resend,test_medium_fixes,test_usb_serialization}.py | **돌연변이 검사의 「검출」 판정이 신뢰할 수 없다 — 선재 실패가 검출로 계상된다.** 무변조 상태에서 `test_drive_command_is_resent_by_poll_loop`·`test_zero_is_also_resent`·`test_watchdog_zeroes_drive_when_bus_goes_silent` 3건이 이미 실패한다(전체 6 failed / 125 passed). `mutation_check.py` 는 변조 후 실패한 시험 이름을 검출 근거로 기록하는데, **12개 돌연변이 전부가 이 3건만을 근거로 「✅ 검출」 판정**을 받았다 — 어떤 변조를 넣든 무조건 실패하므로 실제 검출력과 무관하다. 이는 mutation_check 를 만든 취지(claude-mistake 2026-08-04-001 「시험을 추가한 것과 시험이 검출하는 것을 같게 취급」)를 정면으로 무력화한다 | 2026-08-09 | 미해결 | ① 선재 실패 6건을 먼저 고치거나 격리한다 ② `mutation_check.py` 가 **기준선(무변조) 실패 집합을 먼저 수집**하고, 변조 후 **새로 실패한 시험만** 검출 근거로 계상하도록 고친다(현재는 실패 전량을 근거로 씀). ②만으로도 거짓 양성은 사라진다 |
| debt-060 | 의도 | `src/Comm/TCP_IP/seer_api/` (broker 노드 부재) · `api.py:63-81` (`SeerApi.transport` 의 `allow_guarded` 우회구) | **Seer 지령 포트(19205 제어 · 19206 내비 · 19207 설정 · 19210 DO)의 단일 소유 broker 를 만들지 않았다 — 지금은 「명시하면 열린다」로만 막혀 있다.** ADR `docs/adr/2026-08-07-seer-api-tcp-hal.md` §Decision 3 은 broker 단일 소유를 정했으나 **본 작업 범위 밖으로 미뤘다** — 이관한 소비자 2건이 둘 다 19204 조회여서 broker 없이도 정책 위반이 없기 때문이다. 남는 구멍은 `SeerApi(..., allow_guarded=True)` 로, 단발 도구를 위해 열어 둔 것이지만 **두 도구가 동시에 켜지면 그대로 동시 지령**이다. ❌ **등록 사유 2건이 2026-08-10 실측으로 반증돼 정정한다**(원문은 이력으로 보존): ① ~~「이 네 포트는 동시연결 1 이라 선점되면 RoboShop 을 포함한 타 클라이언트가 거부된다」~~ → **틀렸다.** 한도는 **5** 이고(19204·19301 은 10), 초과 시 거동은 **거부형**이다 — 신규만 거부되고 **기존 연결은 살아남는다** (19204 실측: 9번째부터 `type=19204 / ret_code=61001 / "reach the maximum of status api connection limitation"`, 직후 기존 #1 정상 응답). 따라서 **선점 사고 위험은 존재하지 않는다.** broker 의 근거는 소켓 희소성이 아니라 **지령 중재**(두 주체 동시 지령)로 옮겨갔다. ② ~~「실기 프로토콜 판본 미확인 → 보수적으로 v1.2.1 값 채택」~~ → **질문 자체가 틀렸다.** 한도는 판본이 정하는 상수가 아니라 로봇의 **런타임 파라미터**(`Robot<카테고리>APITCPServerMaxConnections`, `uint32`, `minValue` 1 ~ `maxValue` 20, `advanced`)이며 API 1400 으로 직접 조회된다. 근거 2경로 일치 — 실기(192.168.44.82) 6건 + 원본 하드 `robot.param` SQLite `NetProtocol` 테이블(amap-server `sdb2`; 그 하드의 `rbk/product.version.h` = `3.4.5.22` 로 **실기와 동일 버전**). 조회기 `Tools/seer_re/seer_param.sh` 신설(양쪽 동시 조회). 경위: `docs/claude-mistake/2026-08-07-002` | 2026-08-07 | **미해결(축소)** — ②는 해소, ①은 근거 교체 후 존치 | ① 지령 포트를 쓰는 실사용(제어·내비·설정 자동화)이 생기는 시점에 broker 노드를 만든다 — 소켓은 노드가 소유하고 타 노드는 ROS 서비스로 요청. **판정 기준이 바뀌었다**: 「연결이 부족한가」가 아니라 「두 주체가 동시에 지령할 수 있는가」로 본다. ② 그 전까지 `allow_guarded=True` 는 **단발 CLI 도구에서만** 쓰고 상주 노드에 넣지 않는다. ③ ✅ **해소** — 한도는 상수로 신뢰하지 않고 `SeerApi.get_max_connections()` 가 로봇에 묻는다(돌연변이 `A13` 이 상수 우회를 차단). `ports.OBSERVED_MAX_CONNECTIONS` 는 참고값임을 스스로 선언한다. ④ 게이트 집합을 한도에서 파생하지 않는다 — 한도가 5 라 `n<=1` 파생은 빈 집합이 되어 게이트가 조용히 사라진다(돌연변이 `P2` 가 고정) |
| debt-061 | 이해 | HAL 경계 메시지 계약 (토픽·서비스·액션 목록 부재) · `docs/adr/2026-08-07-seer-api-tcp-hal.md` §Decision 2 | **HAL 경계를 「ROS 인터페이스에 둔다」고 위치만 정하고 그 목록을 정하지 않았다.** ADR 은 Seer 교체 가능성을 위해 상위 알고리즘 패키지가 `seer_api` 를 직접 import 하지 않는다고 정했으나, **그 대신 무엇을 쓰는지**(`/odom` 을 Seer 1004 로 채울지 우리 MCL(`src/Navigation/mcl2d_*`)로 채울지, 배터리·알람 토픽의 이름과 메시지 타입, nav 를 action 으로 감쌀지 service 로 둘지, 맵 배포 경로 4011 → `mcl2d_map` 를 어떻게 이을지)가 미정이다. 계약이 없으면 다음 소비자가 각자 편한 이름을 만들고, 그 시점에 경계가 사실상 사라진다 — `seer_api` 를 직접 import 하는 상위 노드가 하나라도 생기면 「디렉토리 하나만 지우면 된다」는 ADR 의 이득이 무효가 된다. 현재 소비자 2건은 TF 발행이라 이 문제를 건드리지 않는다 | 2026-08-07 | 미해결 | ① 세 번째 소비자(Seer 상태를 ROS 로 흘리는 첫 노드)가 생기기 **전에** 토픽·서비스 목록을 ADR 로 확정한다 — 그 노드가 사실상 계약을 정해버리기 때문이다. ② 확정 시 기존 상류(`trnav_msgs` 계열)와 타입을 맞춘다(메시지 재정의 금지 — `trnav_2ws_msgs` 중복 폐기 선례). ③ 그 전까지 `seer_api` 를 import 하는 곳이 늘면 이 행에 추가 기록한다(현재 2곳: `seer_lidar_tf_node.py`, `seer_read_lidar_install.py` — 둘 다 조회 전용) |

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
  반대편(node1=Front): `References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md` §1 canID config · `design-inputs.md` §1 버스·노드 표 · ~~`Tools/amr_test_gui/amr_test_gui/constants.py:62-64`~~ **(2026-07-28 삭제 — docs/adr/2026-07-28-old-gui-removal.md)**.
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

## [2026-08-02 실측 확정] debt-007 종결 — 조향 홈 기준계

> ❌ **정정 2026-08-03 — 본 절의 채택값과 「출처 없는 값」 판정은 반증됐다. 종결 자체는 유지된다.**
> 아래 원문은 이력으로 보존한다. 상세는 파일 말미 「[2026-08-03 실측 재정정] 조향 0° 정본」 절.
>
> - **정본은 `[7871815, 7840086]`** 이다. 아래가 채택한 `[7871810, 7839894]` 은 **0° 가 아니라 raw 판독값**이었다 —
>   아래 §4-2 의 역산식 `0° = CAN + Seer°×57344` 를 채택값에 적용하지 않은 것이 원인이다.
> - 「출처가 없었다」도 반증 — **출처는 Seer 의 실시간 `0x607A` 조향 목표**다.
> - 차이는 node4 **193c = 0.0034°**, **거동상 무의미**. 안전 문제가 아니라 정본 정확성 문제다.
> - ✅ **유지되는 것**: 기준계 판정(§B-1 (a) 기각 · (c) 유력 후보) · 정본 일원화 · 코드 기본값 제거
>   (`DEFAULT_STEER_HOME = {}`) · 「`7882020/7859062` 는 홈이 아니라 호밍 후 정착값」.

**판정: 기존 config 값 `[7871815, 7840086]` 은 옳았다. 다만 출처가 없었다.**
**❌ 이 절이 채택했던 `[7871810, 7839894]` 은 2026-08-03 호밍 10회 실측으로 반증됐다.**
정본은 **`[7871815, 7840086]`**(Seer 좌표계 기준, 물리 직진 미확인)이며 근거는
`docs/homing/2026-08-03-can-relay-homing-assets.md` §0 이다. 이 절이 든 「CAN↔Seer 독립
교차확인」은 성립하지 않는다 — Seer 1040 은 판다가 읽는 바로 그 `0x6064` 의 아핀 변환이라
역산식이 **항등식**이었다(자세와 무관하게 같은 값을 낸다).

### 근거 — 같은 자세(육안 직진)를 intercept off 로 읽은 **세 경로가 일치**한다

| 경로 | node3 | node4 | 취득 |
| --- | --- | --- | --- |
| 판다 수동청취 콜드부팅 캡처 `0x6064` | **7,871,818** | **7,840,084** | 2026-07-27 22:03, 노드당 16,811 샘플 (`verified_facts/2026-07-27.md` §A-8) |
| 판다 **SILENT** 수동청취 `0x6064` | **7,871,810** | **7,839,894** | 2026-08-01, 설정 호출 0건·제어권 미취득 |
| Seer API 1040 `motor_info.position` | **+0.0001°** | **+0.0035°** | 2026-08-01, 위와 동시각 |

4일·전원 인가 실험·펌웨어 플래시 8회를 사이에 두고 편차가 node3 **8c(0.00014°)** · node4 **190c(0.0033°)**
에 머물렀다 → **절대 엔코더는 전원 사이클을 넘어 재현된다.**

### §B-1 모순의 반대편(판다 read ≈0)에 대한 판정

- 원인 후보 **(a) 「제어권 보유 중 판다 read 오염」 → 기각.**
  `emulate`(`= cover \|\| pc_authority`)는 **bus 라우팅만** 바꾼다 — bus0 의 Seer SDO 요청을 캐시 응답으로
  대신하고(`0x601~0x604`), bus2 의 `0x600~0x604`·`0x581~0x584`·`0x701~0x704` 를 드롭해 Seer 에게
  숨긴다. **PC 자신의 수신 경로는 건드리지 않는다.**
  근거: `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:164-193` 직접 확인(2026-08-02).
- 남는 유력 후보는 **(c) `0x6041` bit15=0 구간에서 `0x6064` 가 0 으로 고정**되는 동작이다
  (2026-07-27 캡처에서 3,080/3,080 샘플로 실증). 다만 **21:11~21:18 당시 statusword 로그가 없어
  그 시점이 bit15=0 이었는지는 확정할 수 없다** — 따라서 (c) 는 *유력 후보*이지 확정이 아니다.
- 실무상 이 잔여 불확실성은 이미 닫혀 있다: `can_relay` 는 `safety.position_trustworthy()` 로
  bit15=0 구간의 `0x6064` 를 상위에 흘리지 않는다(회귀 `test_position_untrusted_while_homing`).

### 정본 일원화 (본 종결의 실질)

`steer_home_counts` 의 **정본은 `src/Comm/CAN/can_relay/config/machine/foil_a082.yaml` 하나**다.
코드 기본값은 제거했다(`safety.DEFAULT_STEER_HOME = {}`) — 값이 없으면 조향 지령을 **거부**한다.
구값이 실행 자산 7곳에 흩어져 있던 것을 실측값으로 갱신했다(아래). 이것이 debt-016 의 상환이기도 하다.

`Tools/amr_test_gui/gui.py:46` · `Tools/docking_field_kit/amap2_monitor.py:115` ·
`Tools/docking_field_kit/docking_drive.py:78` · `Tools/Kinematics/chassis_kinematics.py:79` ·
`src/Actuators/motor_control/config/tongyi_amr.yaml:40` ·
`src/Actuators/motor_control/motor_control/driver_node.py:71` ·
`src/Actuators/motor_control/motor_control/backend.py:44`(주석만)
(줄번호는 2026-08-02 갱신 직후 값이다. 어긋나면 `steer_home`/`STEER_HOME` 문자열로 찾을 것.)

### 남은 것 (종결에 포함되지 않음)

- ❌ ~~**「Seer 의 0°」와 물리적 직진이 같은지는 육안 미확인이다.**~~ Seer 도 자기 캘리브레이션을 거친 값을 준다.
  스티어링 중립 산출은 **사용자가 별도 진행**(2026-08-02 지시).
  > ❌ **재정정 2026-08-03 17:30: 「육안 미확인」은 사실이 아니다.**
  > 사용자가 **바퀴 직진 상태에서 Seer 앞바퀴 2축 0° 를 육안 확인**했다(2026-08-02 · 2026-08-03,
  > `can_relay` GUI 표시로도 동일 확인). 「Seer 도 자기 캘리브레이션을 거친 값」이라는 서술은
  > 맞지만 그것은 EasyDRIVE `steerOffset` 으로 **교정된** 조향각이라는 뜻이므로 앵커를 무효화하지 않는다.
  > ⇒ **물리 직진 앵커는 실재한다.** 남는 것은 **정밀도**뿐 — 육안 한계 **≈±1°(±57,344 counts)** 로,
  > 다툰 **193 counts(0.0034°)** 의 약 297배라 **counts 정본의 소수 자리를 분해하지 못한다.**
- 호밍 후 정착값(7,882,020 / 7,859,062)은 실측 0° 에서 **+0.178° / +0.331°** 떨어져 있다 —
  **호밍은 0° 에 정확히 놓지 않는다.** 이는 결함이 아니라 관측된 사실이며 그대로 둔다.
- `motor_control` 의 「미설정 = 0」 문제는 별건으로 등록했다 → **debt-032**.

## [2026-08-03 실측 재정정] 조향 0° 정본 (append — 삭제 금지)

**위 「[2026-08-02 실측 확정] debt-007 종결」 절의 채택값을 정정한다. 종결 판정 자체는 취소하지 않는다.**

### 정정 대상과 결론

| 항목 | 2026-08-02 채택 | **2026-08-03 실측 확정** |
| --- | --- | --- |
| 조향 0° node3 | 7,871,810 | **7,871,816** (구값 `7871815` 와 **−1 c**) |
| 조향 0° node4 | 7,839,894 | **7,840,087** (구값 `7840086` 과 **−1 c**) |
| 정본 `steer_home_counts` | `[7871810, 7839894]` | **`[7871815, 7840086]`** |
| 구값 판정 | 「틀린 값이 아니라 **출처 없는 값**」 | **철회** — 출처도 있고 값도 맞다 |

### 왜 틀렸나 — 역산식을 적어 놓고 채택값에 적용하지 않았다

0° 는 raw CAN 판독값이 아니라 Seer 각도로 역산해야 한다: **`0° = CAN_0x6064 + Seer_deg × 57344`**.
2026-08-02 종결 문서(`docs/verified_facts/2026-08-02-steer-home-closed.md`)는 이 식을 **§4-2 에 제시해 놓고
§1 채택값에는 적용하지 않고 raw 판독값을 그대로 0° 로 박았다.**
node3 은 그 시점 Seer 각도가 작아 오차가 **6 c** 에 그쳐 드러나지 않았고, **node4 에서 193 c 로 드러났다.**
20인 감사가 이미 「종결 문서 자신의 공식대로면 node4 0° = 7,840,095 이고 폐기 선언된 구값 7,840,086 이
오히려 9 c 로 더 가깝다」고 **내부 모순으로 지적**했었다 — 본 실측이 그 지적을 확정한다.

### 측정 조건 (교차검증 성립 조건 전부 충족)

- 2026-08-03 **11:44**, 도구 `Tools/docking_field_kit/orin_steer_crosscheck.py`
- ❌ **정정 2026-08-06**: Seer 1005·1040 은 판다가 엿듣는 **바로 그 `0x6064` 의 아핀 변환**이다(1040 기울기 ×57,344 = **1.000001** · 1005 = **1.000130**). 따라서 「독립 경로」·「사용자 확인 Seer 표시 0°」·「2회 독립 실행 동일」은 **근거가 되지 못한다**(인용 금지) — 역산식이 **항등식**이라 자세와 무관하게 같은 값을 낸다. 유효한 근거는 **「송신 0건(AST)」** 뿐이고, 값의 지위는 물리 0° 실측이 아니라 **「Seer 좌표계의 조향 영점 + 공학적 채택」**이다. 현행 정본: `docs/homing/2026-08-03-can-relay-homing-assets.md` §0.
- ~~판다 **SAFETY_SILENT · passthrough** — **제어권 미취득** ⇒ CAN 과 Seer 가 **독립 경로**~~
  (제어권을 쥐면 `emulate` 로 Seer 가 판다 캐시를 보게 되어 교차검증이 무의미해진다)
- **송신 0건** — AST 구문트리 검사로 확인
- **사용자 확인: Seer 표시 앞바퀴 2축 모두 0°** 자세에서 측정
- **2회 독립 실행이 counts 단위까지 동일** — node3 7,871,823 c(σ=3, n=3,110) + Seer **−0.000°**,
  node4 7,840,052 c(σ=2, n=3,110) + Seer **+0.001°**
- 산출물 `Log/steer_xcheck_reboot_0deg.jsonl` · `Log/steer_xcheck_reboot_0deg_confirm.jsonl`
- 상세 `docs/homing/2026-08-03-can-relay-homing-assets.md` §10

### 유보 사항 (과대 해석 방지 — 반드시 병기할 것)

- 차이 193 c = **0.0034°** 로 **거동상 무의미**하다. **안전 문제가 아니라 정본 정확성 문제**다.
- 본 측정은 **호밍을 하지 않은 현재 자세**의 값이다. 「호밍이 축을 여기로 데려온다」는 주장이 **아니다.**
- **`7882020 / 7859062` 는 0° 가 아니다** — 펌웨어 GOZERO 상수(`SEER_HOME_ZERO_N3/N4`, 호밍 후 정착 목표)이며
  **별개 사안**이다. 실측 0° 대비 편차 **+0.178° / +0.331°** 도 그대로 유효하다(→ **debt-034**).
- Seer 1040 각도의 절대 정확도(로봇 기구 정렬 포함)는 본 측정의 범위 밖이다. 확정한 것은
  **「Seer 가 0° 라 부르는 자세 ↔ CAN counts」의 대응**뿐이다.

### 반영 범위

- 코드·설정: 정본 `src/Comm/CAN/can_relay/config/machine/foil_a082.yaml` + 사본 6곳
  (`src/Actuators/motor_control/config/tongyi_amr.yaml` · `motor_control/motor_control/driver_node.py` ·
  `Tools/amr_test_gui/gui.py` · `Tools/Kinematics/chassis_kinematics.py` ·
  `Tools/docking_field_kit/docking_drive.py` · `Tools/docking_field_kit/amap2_monitor.py`) + 테스트 픽스처.
  회귀 **319건 통과**(can_relay 177 · motor_control 35 · amr_test_gui 88 · Kinematics 19).
- 부채: **debt-007**(종결 유지 · 결론값 재정정) · **debt-016**(해결 유지 · 갱신값 재정정) ·
  **debt-022**(인용한 구값이 이제 정본 — 「이중 적용 위험」 지적은 그대로 유효).
- 신규 등록: **debt-034**(펌웨어 `SEER_HOME_ZERO_*` 이름·허용오차) ·
  **debt-035**(호밍 시퀀서의 `Operation enabled` 암묵 전제) · **debt-036**(`0x6064`=0 래치, 원인 미판정).
  > ❌ **정정 2026-08-03 15:40**: 여기 적힌 debt-035 의 등록 사유(`Operation enabled` 암묵 전제)는
  > 14:19 에 반증됐고, 대체 사유(「이미 홈」)도 15:25 에 반증됐다. 최종 사유는 **「원인 미상 · 우선순위 낮음」**
  > 이다(호밍 10/10 성공). debt-036 의 「래치」도 **재현되지 않은 1회 관측**이다.
  > 최종 판정은 맨 아래 **[2026-08-03 15:40 확정]** 절.
  >
  > ❌ **재정정 2026-08-03 17:00 (E2)**: 바로 위 「debt-036 의 「래치」도 **재현되지 않은 1회 관측**이다」는
  > **거짓**이다. 원자료 재파싱 결과 `0x6064`=0 은 09:19(node3 **50/50**) · 09:58(**12,220/12,220**) ·
  > 10:08(**10,327/10,327**) 세 캡처에서 **정지 상태 100 %** 로 재현되고, 11:38 리부팅 후 14:43 에도 **2/74** 있다.
  > **debt-036 의 하향 근거는 철회**한다. 단 **인과는 양쪽 다 미판정**이다(그 조건에서도 호밍은 12회 성공).
  > 최종 판정은 맨 아래 **[2026-08-03 15:40 확정] 절의 「❌ 17:00 재정정」 소절**.
- 이슈 로그: `docs/issues_and_fixes/issues_and_fixes.md` 2026-08-03 `[Fix]` entry.



---

## [2026-08-03 14:19 판독] debt-035 · debt-036 전제 반증

읽기 전용 판독(`Tools/docking_field_kit/orin_homing_diag.py`, 쓰기 0건)과
10인 적대적 검증 결과로 두 부채의 **등록 사유가 무너졌다.** 항목은 유지하되 사유를 교체한다.
근거: `docs/homing/2026-08-03-can-relay-homing-assets.md` §11-2 · §15 · 산출 `Log/homing_diag_260803_141949.json`

### debt-035 — 사유 교체 (항목은 유지)

**반증된 원 사유**: 「`0x6040=0x86` 이 CiA402 `Switch on disabled` 를 벗어나지 못해 호밍이 실패했다」
- **반례 ①**: `Log/homing_capture_220350.jsonl`(2026-07-27 **성공** 런)이 **동일한 `0x86` → `0x6099` → `0x60FB:04=1`**
  시퀀스를 **동일한 `0x?050`(Switch on disabled)** statusword 에서 실행해 **호밍에 성공**했다
  (bit15 1→0→1, 위치 7,871,818 → 7,882,021).
- **반례 ②**: Handbook §4.6 은 호밍을 벤더 오브젝트(`RstMode`/`RstStart`/`RstStarSpd`)로만 규정하고
  **controlword·상태머신을 한 번도 언급하지 않는다.** 요구 조건은 *"the driver needs to run in the PP mode"* 뿐이며,
  2026-08-03 판독에서 **`0x6060`/`0x6061` = 1(PP(Profile Position))** 로 그 조건은 충족돼 있다.
- **반례 ③**: 같은 판독에서 `0x6098`=**1**(호밍 활성) · `0x603F`=**0**(오류 없음) ·
  `0x6000:01`=**0x01**(리밋 미접촉) · `0x60FB:04`=**0**(RstStart 미고착) — **막을 요인이 없다.**
⇒ 「서보 on 을 먼저 하라」는 상환계획 ①도 근거를 잃었다.

**교체 사유 — 에지-온리 완료 판정**: WAIT 단계(`safety_seer_gate.h:391-402`)는 `0x6041` bit15 의
**하강→상승 에지**로만 완료를 인정한다(`seen_active` 가 서야 `done_mask` 가 선다).
그런데 Handbook §4.6 은 *"When the motor is **already in the resetting position** … the driver
**directly outputs the resetting end signal**"* 라고 규정한다 ⇒ **축이 이미 홈이면 무동작 즉시 완료**되어
bit15 가 떨어지지 않고, 검출기는 영구 대기하다 120 s 타임아웃한다.
2026-08-03 09:58 실패 시점의 `0x6064` 는 홈에서 **0.0006° 이내**였다.
⚠ 에지 검출 자체는 「개시 전 bit15=1 을 완료로 오독하지 않는다」는 **올바른 목적**을 갖는다 —
단순 제거는 답이 아니고 **별도 종료 조건**이 필요하다.

**교체 상환계획**: ① **검증 선행** — 조향을 홈에서 충분히 떼어놓고 호밍 1회. 성공하면 본 사유 확정,
또 타임아웃이면 재탐색. 이때 `0x6041` 을 **고속 연속 폴링**한다(09:58 회차는 125 s 에 788 샘플 ≈6 Hz 라
짧은 에지를 놓칠 수 있다). ② 확정 시 「이미 홈」 종료 조건 추가 — 예: START 후 N tick 내 bit15 하강이
없고 `0x6064` 가 목표 허용오차 이내면 완료로 인정. ③ 「드라이브가 즉시 완료를 낼 수 있다」는 전제를
코드 주석에 명문화.

### debt-036 — 사유 축소 (항목은 유지)

**반증된 원 사유**: 「`0x6064`=0 은 전원 사이클로만 풀리는 래치이며 statusword 로 설명되지 않는다」
- **반례**: 2026-07-27 **성공 런 한 캡처 안에서** `0x6064`=0 이 **3,115회** 나타났다 — **전원 사이클 없이.**
  같은 캡처 16,811 표본에서 **`0x6064`==0 ⟺ bit15==0 이 99.9% 대응**한다
  (`0x1050`/`0x1450`(bit15=0) → pos=0 이 3,102/3,102 · `0x9050`/`0x9450`(bit15=1) → pos≠0 이 13,678/13,691).
⇒ 「호밍 중(bit15=0)이 원인이 아니다」라던 내 서술은 **틀렸다.** `0x6064`=0 은 대체로 bit15=0 과 함께 온다.

**축소된 잔여 사유**: 2026-08-03 관측은 그 99.9% 의 **바깥(0.1% 코너)** 이다 —
**bit15=1 인데 `0x6064`=0**. 이 조합이 왜 생기는지는 **여전히 미판정**이다.
Handbook §4.6 의 `uwHomeSet`(현위치를 홈으로 설정) 계열 동작이 후보이나 미검증.
⚠ 「전원 사이클로만 풀린다」는 **인용 금지** — 반증됐다.

**교체 상환계획**: ① 재현 시 **bit15 와 `0x6064` 를 같은 판독에서** 취득해 0.1% 코너인지 확인.
② `0x20F1`~`0x20F5`(벤더 `SelfSofRst.*`)는 **ABORT 라 판독 불가**가 확인됐다(2026-08-03) —
이 경로에 의존하는 계획은 폐기. ③ 기존 ③(36초 CAN 단절 반례)도 **철회** —
그 침묵은 판다 재부팅 구간과 시각이 일치해(uptime 145,627 s → 5,346 s) **CAN 단절이었는지 미판정**이다.

### 부수 — 폐기된 측정 계획

적대적 검증이 **최우선**으로 제안한 「`0x4490 uwRstEnd` · `0x4491 uwRstErr` 판독」은 **불가능**하다.
Handbook 의 `0x448E`/`0x4490`/`0x4491` 은 **내부 레지스터 주소이지 CANopen 인덱스가 아니고**,
EDS(Electronic Data Sheet) 에서 이름으로 역인덱싱한 `0x20F1`~`0x20F5` 는 **드라이브가 전부 ABORT** 를 낸다.
⇒ 드라이브의 호밍 종료/오류 플래그는 **CANopen SDO 로 볼 수 없다.** 다른 관측 수단이 필요하다.


---

## [2026-08-03 14:46 실기 검증] debt-035 교체 사유 **확정** · debt-034 근거 실측

> ❌ **정정 2026-08-03 15:40: 본 절의 「확정」은 무효다.** 여기서 확정했다고 적은 debt-035 사유
> (「이미 홈이라 무동작 즉시 완료」)는 15:25 에 반증됐고, 15:40 의 호밍 **10/10 성공**으로
> 「호밍이 실패한다」는 전제 자체가 사라졌다 — 최종 판정은 맨 아래 **[2026-08-03 15:40 확정]** 절이다.
> ✅ 다만 본 절의 **debt-034 근거 실측**(`+0.178°` / `+0.331°`)과 **DI `0x01`→`0x09` 리밋 실재**는
> 15:40 의 10회 실측으로 **재현되어 그대로 유효**하다. 아래 원문은 이력으로 보존한다.

`Tools/docking_field_kit/orin_homing_edge_test.py` 실행. 산출 `Log/homing_edge_260803_144602.json`.
전문 근거: `docs/homing/2026-08-03-can-relay-homing-assets.md` §16

### debt-035 — 교체 사유 확정 (미해결 유지, 원인은 확정)

조향을 홈에서 **+10°** 떼어놓고 호밍하니 **정상 동작(DONE, 37.0 s)** 했다.
`0x6041` 을 노드당 **≈110 Hz** 로 폴링해 **`bit15` 하강 에지 2건(t=0.271/0.282 s)** 을 직접 포착했다
(09:58 실패 회차는 ≈6 Hz 라 놓칠 우려가 있었는데, 그 우려를 제거한 관측이다).

⇒ **원인 확정**: 「축이 이미 홈 → 드라이브가 무동작 즉시 완료 → `bit15` 하강 에지 미발생 →
WAIT 의 에지 검출기(`safety_seer_gate.h:391-402`)가 영구 대기 → 120 s 타임아웃」.
Handbook §4.6 *"already in the resetting position … directly outputs the resetting end signal"* 과 정합.

**상환계획 갱신**: ①(검증 선행)은 **완료**. 남은 것은 ② 펌웨어 WAIT 에 **「이미 홈」 종료 조건** 추가 —
예: START 후 N tick 내 `bit15` 하강이 없고 `0x6064` 가 목표 허용오차 이내면 완료로 인정.
에지 검출은 「개시 전 `bit15`=1 을 완료로 오독하지 않는다」는 올바른 목적이 있으므로 **제거가 아니라 보강**한다.
③ 「드라이브가 즉시 완료를 낼 수 있다」는 전제를 코드 주석에 명문화. ⚠ 재현 1회 권장(현재 1회 관측).

### debt-034 — 근거 실측 확보 (미해결 유지)

같은 회차에서 호밍 완료 직후 위치가 **node3 `+0.178°` · node4 `+0.331°`** 로 관측됐다.
그동안 계산으로만 주장하던 GOZERO 편차가 **실측으로 확인**됐고, 재계산값 **`+0.331°` 가 정확히 맞았다**
(폐기된 `+0.334°` 는 구 0° 기준 잔재). ⇒ 「`SEER_HOME_ZERO_*` 가 0° 가 아니다」가 실측 근거를 얻었다.

### 부수 — 기준선#4 재현

리밋 도달 순간 DI(Digital Input) 3·4 가 `0x01` → **`0x09`**(bit3 = −Limit). 리밋 스위치 실재가 이번 회차로 재현됐다.

### 신규 부채 후보 — 판독 경로 (미등록, 이미 수정함)

`sdo_read()` 가 요청 전 수신 버퍼를 비우지 않아 **제어권 보유 중 Seer 폴 응답을 자기 응답으로 간헐 오인**했다
(실측: dry-run 이 `0x1050`/`pos≈19` 를 읽었으나 같은 시각 45 s 수동 청취 4,589 샘플은 `0x9450`/홈 고정).
2026-08-03 수정 완료 — 요청 직전 버퍼 flush + `snap()` 다중 샘플 중앙값.
⚠ **그 이전 단발 `sdo_read` 인용은 이 오염 가능성을 안고 있다.**

---

## [2026-08-03 15:25 실기] debt-035 사유 **재반증** · debt-036 이 실질 원인으로 승격

> ❌ **정정 2026-08-03 15:40: 본 절의 「debt-036 승격」은 철회한다.** 호밍 **10회 연속 성공**으로
> 「호밍 실패」 자체가 재현되지 않아, 관측 2점(09:58 실패 / 15:25 성공)의 상관을 실질 원인으로
> 승격한 근거가 사라졌다. 아래 표의 대조는 관측 사실이므로 남기되, **「`0x6064`=0 래치 상태에서는
> 호밍이 걸리지 않는다」는 단정은 무효**다.
> ❌ **재정정 2026-08-03 17:00 (E2)**: 위 「승격 철회」와 「단정 무효」는 **그대로 유효**하나,
> 15:40 이 그 뒤에 덧붙인 「`0x6064`=0 은 **1회 관측이라 재현되지 않는다**」는 **거짓**이다 —
> 09:19 · 09:58 · 10:08 세 캡처에서 **정지 상태 100 %** 로 재현된다(→ [15:40 확정] 절 「❌ 17:00 재정정」 E2).
> ⇒ **debt-036 의 「우선순위 낮음」 하향 근거만 철회**되고, 인과는 **양쪽 다 미판정**으로 남는다.
> ✅ 본 절의 **debt-035 재반증**(「이미 홈이라 즉시 완료」가 틀렸다)과 **오귀속 기전 분석**
> (10° 오프셋과 리부팅이 동시에 바뀐 상태에서 오프셋만 원인으로 귀속)은 **그대로 유효**하다.

펌웨어 수정본 플래시 후 **홈 상태에서 호밍**을 걸었더니 **정상 동작(DONE 34.9 s)** 했다 —
`bit15` 하강 에지 t=0.307 s 발생, 31.3 s 에 −리밋 도달(DI `0x09`), 축이 실제로 주행했다.
산출 `Log/homing_edge_260803_152520.json` · 전문 `docs/homing/2026-08-03-can-relay-homing-assets.md` §17

### debt-035 — 「이미 홈이라 즉시 완료」 사유도 **반증**됨 (항목 유지, 사유 재교체)

14:46 에 확정했다고 적은 사유가 **틀렸다.** 홈에 있어도 드라이브는 무동작 즉시 완료하지 않고
정상적으로 리밋을 탐색한다. Handbook §4.6 의 해당 문구는 이 드라이브의 이 조건에서 발현하지 않는다.

**오귀속의 기전**: 14:46 실험은 「10° 오프셋」과 「11:38 리부팅으로 `0x6064` 래치 해제」가
**동시에 바뀐 상태**였는데 오프셋만 원인으로 귀속했다. `--offset 0` 대조군을 함께 돌렸으면 바로 갈렸다.
⇒ INDEX §메타 패턴의 「하나를 보고 단정」 재발.

**현재 지위**: 펌웨어에 추가한 「이미 홈」 종료 조건(`SEER_HOME_ATHOME_S` · `seer_home_athome_mask`,
`safety_seer_gate.h`)은 **무해함이 실증**됐으나(정상 경로 그대로 동작) **필요성은 미확인**이다
— 이번 회차에서 발동조차 하지 않았다. **되돌리지 않되, 「09:58 실패를 고쳤다」고 주장하지 않는다.**

**상환계획 갱신**: ① 「드라이브가 무동작 즉시 완료」 상황이 실재하는지 별도 관측 —
없으면 이 방어 코드는 보험으로만 남는다. ② 실질 원인은 **debt-036** 이므로 그쪽을 먼저 푼다.

### debt-036 — 실질 원인 후보로 **승격** (미해결, 우선순위 상향)

09:58 실패와 15:25 성공의 **유일한 차이가 `0x6064` 보고값**이다:

| | 09:58 (ERR_TIMEOUT) | 15:25 (DONE) |
|---|---|---|
| statusword · 호밍방식 · 위치 · CiA402 상태 | `0x9450` · 1 · 홈 · Switch on disabled | **전부 동일** |
| **`0x6064`** | **0 (래치)** | **실값 7,871,815** |

⇒ **`0x6064`=0 래치 상태에서는 호밍이 걸리지 않는다.** 이것이 호밍 실패의 실질 원인 후보다.
(⚠ 「래치가 호밍을 막는다」는 인과 방향도 아직 **미확정**이다 — 래치와 호밍 불능이 **공통 원인**의
두 증상일 수도 있다. 관측 2점에서 나온 상관이다.)

**상환계획(유지·강화)**: ① 래치 진입 조건을 **1변수씩** 재현 — 제어권 취득 / 호밍 시도 /
CAN 단절 / 서보 off↔on. 매 관측에 `0x6041` 전체 · `0x6000:01` · `0x603F` · `0x6064` **동시 취득**.
② 재현되면 그 상태에서 호밍을 걸어 **인과 방향**을 가른다(래치→불능인지, 공통원인인지).
③ 벤더 `0x20F1`~`0x20F5` 경로는 **ABORT 로 판독 불가** 확인됨(2026-08-03) — 이 경로 의존 계획 폐기.
④ 판정 전까지 **「호밍이 안 되는 이유」를 단정하지 않는다** — 오늘 두 번 틀렸다.


---

## ★ [2026-08-03 15:40 확정] 호밍 10회 연속 실측 — 본 절이 오늘의 호밍 관련 서술에 우선한다

**이 절이 debt-034 · debt-035 · debt-036 에 대한 오늘의 최종 판정이다.**
위 [14:19] · [14:46] · [15:25] 절과 어긋나는 서술은 무효이며, 원문은 이력으로 보존한다.

> ❌ **재정정 2026-08-03 17:00 — 본 절에 오류 7건(E1~E7)이 있다. 아래 「17:00 재정정」 소절이 본 절에 우선한다.**
> 15:40 원문은 이력으로 그대로 두고, 각 오류 지점에 `❌ 재정정 17:00` 표시를 인접 배치했다.
> 정본은 `docs/homing/2026-08-03-can-relay-homing-assets.md` **§0-0**.

### ❌ 17:00 재정정 — 원자료 재계산 (본 절의 15:40 서술에 우선)

아래는 전부 `Log/**` 원자료·소스 파일을 **직접 파싱/재계산**한 값이다(문서를 근거로 삼지 않았다).

| # | 15:40 판 (틀림) | ❌ 재정정 17:00 | 원자료 |
|---|---|---|---|
| **E1** | 「이후 **12회 연속 성공**」 | **12회 연속.** 오늘 시도 **13** / 성공 **12** / 실패 **1**. 「15:33 기준선」은 호밍이 아니라 **레지스터 스냅샷**(`orin_home_experiment.py:390` `base = snapshot(rig,"baseline")`, `snapshot()` `:259-275` 는 판독 전용). **「10회 연속 10/10」 자체는 유효** | `…_091956_summary.json`(`repeat=0`·`runs=[]`) · `…_095815_summary.json`(`final_state=6`) · `homing_edge_…144602.json`(`5`, 37.0 s) · `homing_edge_…152520.json`(`5`, 34.91 s) · `…_153319_summary.json`(10건 `5`) · 나머지 edge 6건 `fsm_trace=[]` |
| **E2** | debt-036 「`0x6064`=0 은 09:58 **1회 관측 · 재현 없음**」 | **재현된다** — 09:19 node3 **50/50**, 09:58 **12,220/12,220**, 10:08 **10,327/10,327**(전부 100 %, `0x6041`=37968=`0x9450` bit15=1 전량). 11:38 리부팅 후 14:43 에도 node3 **2/74**. ⇒ **하향 근거 철회.** 단 **인과는 양쪽 다 미판정** | `home_experiment_260803_091956.jsonl` · `…_095815.jsonl` · `seer_homing_260803_100813.jsonl` · `homing_edge_260803_144305_can.jsonl` |
| **E3** | 「WAIT **31.7 s**」 | **WAIT(state 4) 체류 = 평균 31.30 s**(31.21~31.38, 중앙 31.295). **31.687 s 는 개시 t=0 → state 8 관측까지의 절대 시각**(state 4 진입이 t=0.33~0.44) ⇒ 0.4 s 과대 라벨 | `…_153319_summary.json` `runs[*].transitions` |
| **E4** | 「**35.0 s**」 | **평균 35.07 s · 중앙 35.05 s**(범위 34.99~35.16, 폭 0.17 — 이 둘은 정확) | 〃 `runs[*].elapsed` |
| **E5** | 「counts/° **57,344**」 단일값 | **node3 57,344.00 / node4 57,344.28**(node4 누락이었음). ×57344 = 1.0000000 / 1.0000049. 설정값 `steer_counts_per_deg: 57344.0`(`foil_a082.yaml:20`)은 그대로 유효 | `Log/steer_two_phase_260803_131305.jsonl` A국면 −5~+5° 5점 최소제곱 |
| **E6** | 「σ **2.8 c** / **3.2 c**」(기준 무표기) | **모표준편차(population) 기준 2.80 / 3.21.** 표본표준편차는 **2.95 / 3.38**. 원값 node3 7,882,021 ×8 · 7,882,014 ×2 / node4 7,859,065 ×8 · 7,859,058 ×2 | `…_153319_summary.json` `runs[*].post` |
| **E7** | 「정착 편차는 **결함이 아니라 설계 동작이다**」 | **과잉 확정.** 실측 보증은 「축이 `SEER_HOME_ZERO_N3/N4`(`safety_seer_gate.h:212-213`)에 **node3 +1 c · node4 +3 c 로 재현성 있게 정착**」까지. **상수 적정성은 실측 밖**이며 **debt-016 의 「영구 미검출 오프셋」 등록과 충돌**한다 ⇒ **「재현되는 정착 동작(상수 적정성은 별건, debt-016)」**으로 완화 | 〃 + `safety_seer_gate.h` 직접 확인 |

**미확인으로 남긴 것**: E2 의 **인과 방향**(래치→호밍 불능 / 공통 원인의 두 증상 / 무관) — **전부 미판정**.
E7 의 **상수 적정성**(`SEER_HOME_ZERO_N3/N4` 가 옳은 목표인지) — 실측 범위 밖, debt-016·debt-034 소관.

- 실행: `orin_home_experiment.py --repeat 10`, 2026-08-03 **15:33~15:40**, 접지 상태,
  펌웨어 `DEV-cc5e0491-DEBUG`, 호밍속도 2500
- 산출: `Log/home_experiment_260803_153319.jsonl` · `Log/home_experiment_260803_153319_summary.json`
- 정본: `docs/homing/2026-08-03-can-relay-homing-assets.md` **§0**

### 실측 사실 (관측만 — 가설 없음)

| 항목 | 결과 |
|---|---|
| 성공률 | **10 / 10** (전부 `DONE`) |
| 소요 | **35.0 s** (34.99~35.16, 편차 **0.17 s**) |
| 단계 | ENABLE → SET_SPEED → START → WAIT(**31.7 s**, −리밋 탐색) → RESTORE → GOZERO → GOZERO_W → DONE |
| 리밋 도달 | **10회 모두** DI(Digital Input) `0x01` → `0x09` (bit3 = −Limit) |
| 정착값 node3 | **7,882,021** (σ 2.8 c) → 조향 0° 대비 **+0.178°** |
| 정착값 node4 | **7,859,065** (σ 3.2 c) → 조향 0° 대비 **+0.331°** |
| 조향 0° (Seer 좌표계) | **`[7871815, 7840086]`** — ~~물리 직진 여부는 **미확인**~~ → **재정정 17:30**: 물리 직진 앵커는 **실재**(Seer 교정 조향각 + 사용자 육안 확인)하나 **정밀도 ≈±1°(±57,344 c)** 라 counts 소수 자리(193 c = 0.0034°)는 분해 못 함 |
| counts/° | **57,344** (지령각→CAN 기울기 실측 1.000000) |
| `0x6098` | **1** (Home 1, −리밋) — 리밋 스위치 **실재** |

> ❌ **재정정 17:00**(위 표): 「소요 **35.0 s**」 → **평균 35.07 / 중앙 35.05**(E4) · 「WAIT **31.7 s**」 →
> **WAIT 체류 31.30 s, 31.687 s 는 개시~state 8 절대 시각**(E3) · 「σ 2.8 / 3.2」 → **모표준편차 기준 2.80 / 3.21,
> 표본 2.95 / 3.38**(E6) · 「counts/° **57,344**」 → **node3 57,344.00 / node4 57,344.28**(E5) ·
> 「조향 0° `[7871815, 7840086]`」 → **값은 유지하되 근거는 「공학적 채택값(Seer 좌표계 정합)」이며 「실측 확정」 아님**(E8).
> 「**10 / 10**」·「리밋 도달 10회 모두」·「`0x6098`=1」은 **유효**하다.

### 판정

1. **호밍은 정상 동작한다.** 09:58 의 `ERR_TIMEOUT` **1회가 유일한 실패**이고 이후 **12회 연속 성공**
   (본 10회 + 14:46 · 15:25 · 15:33 기준선). **재현되지 않는다.**
   실패해도 `ERR_TIMEOUT` 은 깔끔한 terminal 이라 **재시도로 충분** — **운영상 이슈가 아니다.**
   > ❌ **재정정 17:00 (E1)**: 「**12회 연속**」은 **거짓 — 12회 연속**이다(15:33 기준선은 호밍이 아니라
   > 레지스터 스냅샷). 오늘 **시도 13 / 성공 12 / 실패 1**. 「호밍이 정상 동작한다」는 판정 자체는 유효하다.
2. **정착 편차(+0.178° / +0.331°)는 결함이 아니라 설계 동작이다.** σ ≈ 3 counts ≈ **0.00005°** 로
   매번 같은 자리에 서고, 펌웨어 상수 `SEER_HOME_ZERO_N3/N4` 와 1~3 counts 로 일치한다.
   > ❌ **재정정 17:00 (E7)**: 「**결함이 아니라 설계 동작이다**」는 **과잉 확정**이다. 실측이 보증하는 것은
   > 「축이 펌웨어 상수 `SEER_HOME_ZERO_N3/N4`(`safety_seer_gate.h:212-213`)에 **1~3 counts 로 재현성 있게
   > 정착한다**」까지이고, **그 상수가 옳다는 것은 실측에서 나오지 않는다**(우리가 써 넣은 값이다).
   > **debt-016 은 같은 +0.178° / +0.331° 를 「영구 미검출 오프셋」으로 등록**해 두었으므로 이 표현은 그 등록과
   > **충돌**한다 ⇒ **「재현되는 정착 동작(상수 적정성은 별건, debt-016)」**으로 읽을 것.
3. **Seer 1005 · 1040 은 둘 다 `0x6064` 유래**다 — 독립 앵커가 아니며, 이 둘의 일치를 교차검증으로
   인용하지 않는다. ~~**물리 직진 앵커는 여전히 부재**하다(非-Seer 계측 필요).~~
   > ❌ **재정정 2026-08-03 17:30 — 뒷문장은 거짓이므로 폐기한다.**
   > 앞문장(**두 Seer 채널이 서로 독립 교차검증이 아니다**)은 **유효하며 유지**한다.
   > 그러나 **물리 직진 앵커는 실재한다** — Seer 의 **교정된**(EasyDRIVE `steerOffset`) 조향각 +
   > 사용자 육안 확인(바퀴 직진 상태에서 Seer 앞바퀴 2축 0°, 2026-08-02 · 2026-08-03,
   > `can_relay` GUI 동일). 한계는 **정밀도 ≈±1°(±57,344 c)** 로 다툰 **193 c(0.0034°)** 의 약 297배다.
   > ⇒ 「非-Seer 계측 필요」는 **「counts 소수 자리까지 판정하려면」**이라는 조건에서만 참이다.

### 부채 반영

| 항목 | 조치 |
|---|---|
| **debt-034** | **근거 굳음 (판정 불변, 미해결 유지)** — 편차 +0.178°/+0.331° 가 **10회 재현**. 「이름이 「ZERO」인데 0° 가 아니다 · 허용오차 1.0° 로는 검출 불가」라는 등록 사유가 반복 실측으로 뒷받침됨 |
| **debt-035** | **사유를 「원인 미상」으로 환원 + 우선순위 낮춤** — 오늘 사유가 두 번 교체됐고 **둘 다 반증**(① Switch on disabled ② 이미 홈). 호밍이 정상 동작하므로 급하지 않다. 펌웨어 「이미 홈」 종료 조건(`SEER_HOME_ATHOME_S`·`seer_home_athome_mask`)은 **무해함 실증 · 필요성 미확인**(10회에서 발동 0) ⇒ **보험으로 존치, 「실패를 고쳤다」 주장 금지** |
| **debt-036** | **우선순위 하향 + 「호밍을 막는다」 단정 철회** — 15:25 의 「실질 원인 후보 승격」 취소. `0x6064`=0 은 09:58 **1회 관측 · 재현 없음**. 인과 방향 미판정 ⟵ ❌ **재정정 17:00 (E2)**: 「**1회 관측 · 재현 없음**」은 **거짓** — 09:19 **50/50**, 09:58 **12,220/12,220**, 10:08 **10,327/10,327**(전부 100 %) + 14:43 **2/74** 로 **재현된다**. ⇒ **하향 근거 철회.** 「단정 철회」·「인과 방향 미판정」은 유효(호밍이 12회 성공했으므로 **양쪽 다 미판정**) |

### 폐기된 주장 (인용 금지 — `docs/homing/2026-08-03-can-relay-homing-assets.md` §0-4)

| 폐기된 주장 | 반증 |
|---|---|
| 「`Switch on disabled` 라 호밍이 막힌다」 | 07-27 성공 로그가 같은 statusword 로 성공 |
| 「`0x6098`=0 이라 호밍 비활성」 | 실측 **1** |
| 「RstStart 가 1 로 고착돼 에지 불가」 | 실측 **0** |
| 「`0x6064`=0 은 전원 사이클로만 풀리는 래치」 | 07-27 캡처가 사이클 없이 3,115회 관측 |
| 「축이 이미 홈이면 무동작 즉시 완료 → 타임아웃」 | 홈 상태 호밍이 정상 동작 (15:25 · 15:40) |
| 「CAN 과 Seer 가 독립 경로라 교차검증 성립」 | 1005·1040 둘 다 `0x6064` 의 아핀 변환 |
| 「회귀 319건 통과로 값이 검증됨」 | 변이 시험에서 값을 바꿔도 전부 통과 |

### 남은 것

- **`0x6064`=0 (bit15=1 동반)** — 09:58 1회, 재현 없음 (debt-036, 우선순위 낮음)
  > ❌ **재정정 17:00 (E2)**: 「09:58 1회, 재현 없음」은 **거짓**이다 — 09:19(50/50) · 09:58(12,220/12,220) ·
  > 10:08(10,327/10,327) 세 캡처에서 **정지 상태 100 %** 로 관측되고, 11:38 리부팅 후 14:43 에도 소수 샘플(2/74)이 있다.
  > **debt-036 의 「우선순위 낮음」 하향 근거는 철회**한다. **인과는 양쪽 다 미판정**(호밍은 그 조건에서도 12회 성공).
- ❌ ~~**물리 직진 앵커 부재** — Seer 좌표계 기준까지만 확정~~ → **재정정 2026-08-03 17:30**:
  **물리 직진 앵커는 실재한다**(Seer 의 EasyDRIVE `steerOffset` 교정 조향각 + 사용자 육안 확인 —
  바퀴 직진 상태에서 Seer 앞바퀴 2축 0°, 2026-08-02 · 2026-08-03, `can_relay` GUI 동일).
  남은 것은 **앵커 정밀도**다 — 육안 한계 **≈±1°(±57,344 c)** 로 **counts 정본의 소수 자리
  (193 c = 0.0034°, 약 297배)를 분해하지 못한다.** 그 자리를 판정하려면 非-Seer 계측
  (휠 평면 직접 계측 0.052° / iAHRS yaw 0.012°)이 필요하다 — **그 조건에서만** 필요하다.
  (debt-004 · debt-022 와 인접)
- **펌웨어 「이미 홈」 종료 조건의 필요성** — 미확인, 보험 존치 (debt-035)

---

## [2026-08-05 판정] debt-022 — 환산 소유 계층 확정 (① 종결, ② 잔존)

> 사용자 지시로 확정했다: 「0도의 위치를 config 에서 저장하고 사용하지」·
> 「조향 원점 부분은 전체 모션에서 중요한 수정할 것」. 반영 커밋 `3d53cfc`.

### 확정된 경계

| 항목 | 소유 계층 | 근거 |
| --- | --- | --- |
| 기계 **원점**(홈 counts) | **can_relay**(드라이버 계층) | 홈 정본이 `config/machine/<기체>.yaml` 하나다. 상류에 복제하면 정본이 둘이 된다 |
| 스케일·부호·영점 미세보정 | **translator** | `gear_steer`·`pulses_per_rev`·`direction_steer_*`·`steer_offset_*_deg` |

계약: `/motor/low_cmd` 의 `target_pos` 와 `/motor/low_state` 의 조향 `fb_pos` 는
**홈 기준 상대 counts**. 절대 counts 변환은 can_relay 안에서만 일어난다.

### ⚠ 상환계획 ① 의 「권장」과 반대 방향이다

① 은 「can_relay 는 **안전 클램프 판정용으로만** 환산 — **지령 값을 재보정하지 않는다**」를
권장했다. 확정은 그 반대다(can_relay 가 `home + tpos` 로 재보정한다). 뒤집은 근거:

- **상류 선례가 드라이버 계층이다** — 본 행 본문이 인용한 TR_Nav
  `amr_canopen_motor_driver.yaml` 의 `steer_home_offset_front/rear: -6500000` 은
  translator 가 아니라 **드라이버** config 에 있다. ① 의 권장은 그 인용과 어긋나 있었다.
- **실기 검증된 경로가 이미 그렇게 한다** — `set_steer_deg` → `steer_deg_to_counts`
  (`safety.py:85` `home[node] + applied × counts_per_deg`). raw 경로만 그 원점을 지나지
  않아 갈라져 있었다(진입점 2개, 한쪽만 검증됨).
- **원점을 상류가 더하면 홈 정본이 둘이 된다** — 기체 교체 시 한쪽만 갱신되면 그 오차가
  그대로 바퀴로 나간다.

### 「이중 적용」 우려는 해소됐다

본 행이 지적한 이중 적용은 **성립하지 않는다** — translator 의 `steer_offset_*_deg`(−1.676°,
조향 영점 미세보정)와 can_relay 의 `steer_home_counts`(기계 원점)는 **다른 보정**이다.
같은 보정을 두 번 거는 구조가 아니다.

### 확정 전 상태가 실제로 무엇이었나 (반영 근거)

원점을 아무도 더하지 않아 **0°(직진) 지령이 −81,005 counts 로 내려가 클램프 하한
2,710,855c(홈−90°)로 잘린 채 지령**됐다. 피드백도 대칭으로 깨져 있었다 — 절대 counts 를
그대로 올려 상류가 직진을 **137.27°** 로 읽었다.

### 검증

- 회귀 `src/Comm/CAN/can_relay/test/test_steer_origin.py` 19건.
  기존 시험은 픽스처 홈이 0 이라 원점을 지워도 통과한다(`test_backend.py:496`) — 그 눈먼
  구간을 실기 값 `[7871815, 7840086]` 으로 덮었다.
- 돌연변이: 지령 원점 제거 → 11 failed · 피드백 원점 제거 → 3 failed · 복원 → 19 passed.
- **Seer 독립 대조**(로봇 무동작, SILENT passthrough 캡처):
  node3 차 `0.000016°` · node4 차 `0.000012°`. 원점·스케일(57,344)·조향 부호(−1)를
  동시에 확인한다. 상설화: `Tools/motion_chain_check/check_chain_contract.py --seer-capture`.

### 잔존 — ② 잭업 실측 대조

확정한 것은 **정지 자세에서 보고각이 Seer 와 일치한다**까지다. **움직이는 지령을 실기에
낸 적이 없다.** ② (잭업 상태에서 상류가 만든 raw 를 흘려 실측 조향각과 대조)는 그대로
미이행이므로 본 항목은 닫지 않는다.

---

## [2026-08-08 판정] debt-017 · debt-027 — 구동축 한정 **부분 상환** (커밋 `a7420a6`)

두 항목은 같은 대상(`drive_init_frames`·`steer_init_frames`, `allow_bringup` 기본 false)을
가리키는 중복 등록이다. 아래 판정은 둘 다에 적용한다.

### 상환된 부분 — 구동축 시퀀스가 실기에서 동작함이 관측됐다

「실기 검증 이력 0」은 더 이상 사실이 아니다. 2026-08-08 실기에서 can_relay **프로세스
재시작** 뒤 `node1 walk_front` 가 `0x60FF` 를 받고도 안 도는 고장이 재현됐고, 구동축
브링업(`0x6040=0x86` · `0x60FF=0` · `0x100C`/`0x100D` · `0x6060=3` PV) 송신으로 복구됐다.

```
브링업 전   node1 +0.0009 m   node2 +0.0896 m
브링업 후   node1 +0.0830 m   node2 +0.0794 m   (차 3.6 mm)
            node1 −0.0888 m   node2 −0.0893 m   (차 0.5 mm)
```

조치: `_write_bringup()` 을 **구동축 전용**으로 좁히고 배포 설정
`config/can_relay.yaml` 을 `allow_bringup: true` 로 전환.
**코드 기본값 `RelayConfig.allow_bringup` 은 여전히 False** — 활성화는 배포 yaml 에서만 일어난다.

### 잔존 — 상환계획이 요구한 검증 조건 3개가 **전부 미이행**

등록 당시 상환계획은 「잭업(바퀴 공중) + 하드웨어 E-STOP 상비 상태에서 1회 수행하고
`0x6041`·`0x603F`·SDO abort 를 전수 기록. abort 0건·상태 전이 정상 확인 후에만 지면 사용」
이었다. 실제로 수행한 것은 **지면 주행에서의 구동 복귀 관측**뿐이다.

```
① 잭업(바퀴 공중)                        미이행 — 지면 상태로 수행
② 하드웨어 E-STOP 상비                    미이행
③ 0x6041 · 0x603F · SDO abort 전수 기록   미이행 — 기록 0건
```

⇒ **본 항목은 닫지 않는다.** 지면 사용 중이므로 위 3개를 갖춘 재검증이 남아 있다.

### 조향축 브링업은 **영구 제외 후보** — 별도 판정 필요

같은 날 조향축까지 브링업을 보냈더니 fault reset(`0x6040=0x86`)이 조향 위치 카운터를
지워 **조향 0° 기준이 무효**가 됐고(판독이 −(홈) 으로 떨어짐), 그 상태의 「0° 로 가라」
지령에 전륜이 실제로 움직였다. `~/home` 재호밍으로 복구(정착값 node3 +0.18° · node4 +0.33°,
정본 기록과 일치). ⇒ `steer_init_frames` 는 **브링업 경로에서 제외**했으며, 이 제외를
영구화할지는 미판정으로 남긴다.

---

## [2026-08-08 등록] 신규 부채 3건 — 브링업 수정에서 파생

| id | 유형 | 위치 | 사유 | 식별일 | 상태 | 상환계획 |
| --- | --- | --- | --- | --- | --- | --- |
| **debt-045** | 기술 | `src/Comm/CAN/can_relay/can_relay/ui/backend_direct.py` `DirectBackend.set_engaged` | 브링업 수정이 `RelayBackend` 한쪽에만 들어갔다. UI 직결 백엔드는 여전히 구동축 브링업을 보내지 않으므로 **같은 고장이 그 경로에서 재현**된다(2026-08-08 실측: node1 0.1 rpm / node2 78.2 rpm). 기록에 「PC 경로 전부 고쳤다」로 읽힐 서술이 있었다 | 2026-08-08 | **상환 완료(2026-08-10)** — 브링업 추가 + 회귀 4건(돌연변이 2건 검출 확인) | `DirectBackend` 제어권 획득 경로에 동일한 **구동축 전용** 브링업을 추가하고, 같은 재현 절차(프로세스 재시작 → 구동 시험)로 확인 |
| **debt-046** | 이해 | `src/Comm/CAN/can_relay/can_relay/backend.py` `_write_bringup` 주변 | **왜 `node1` 만 상태를 잃고 `node2` 는 멀쩡했는지 미규명.** 「프로세스 재시작이 축 브링업 상태를 지운다」는 관측이며 기전은 확정되지 않았다. 기전을 모르면 다른 축·다른 기체에서 재발해도 같은 시간을 다시 태운다 | 2026-08-08 | 미해결 | 재시작 전후로 `0x6060`(modes) · `0x6041`(statusword) · `0x603F`(error code)를 축별로 폴링해 무엇이 달라지는지 대조. 판다 Seer 게이트의 재개방 동작도 후보 |
| **debt-047** | 기술 | `src/Comm/CAN/can_relay/test/` | 2026-08-08 의 두 수정(조향 게이트 `homed_effective` 통일 · 구동축 브링업)을 **덮는 회귀 시험이 0건**이다. 통과 숫자(364 passed)는 커버리지 근거가 아니다 — 두 변경을 되돌려도 시험은 전부 통과한다 | 2026-08-08 | **상환 완료(2026-08-10)** — 조향 게이트는 기존 시험이 이미 검출, 브링업은 회귀 5건 신설(돌연변이 3건 검출 확인) | 각 수정을 수정 전으로 되돌리면 실패하는 시험을 추가하고, `Tools/amr_test_gui/mutation_check.py` 방식의 돌연변이 확인으로 검출됨을 증명 |

---

## [2026-08-09 등록] `turn` 계열 각도 계상 — 90° 실기 검증에서 파생

| id | 유형 | 위치 | 사유 | 식별일 | 상태 | 상환계획 |
| --- | --- | --- | --- | --- | --- | --- |
| **debt-048** | 기술 | `trnav_2ws_action_server/src/turn/turn_action_server.cpp:259-260 · 314-315 · 387-388` 및 `src/turn_reverse/turn_reverse_action_server.cpp:262 · 317 · 393` | **`turn` 계열에는 오차 피드백이 없다** — 각속도 지령은 `profile.getSpeed(accumulated_angle)`(`turn_action_server.cpp:204`)의 표 조회일 뿐이고 「목표 대비 벗어난 양」을 되먹이는 항이 없다. 닫혀 있는 것은 **종료 판정 하나뿐**이라 누적기가 틀리면 잡아 줄 두 번째 기구가 없다(Phase 3.5 미세보정도 같은 누적기를 본다). 그 위에, `turn` 계열이 IMU **델타 누적**으로 회전각을 계상하면서 누적기에 **0 클램프**를 둔다 — 음의 델타가 0 아래로 끌면 잘라 버려 그 음수가 영구히 사라지므로 **과대계상 방향으로만** 편향될 수 있다. 2026-08-09 90° 실기에서 액션 자기보고(−90.22 / +90.69°)가 맵 절대 측위(−90.53 / +91.19°)보다 **양쪽 다리 모두 작게** 나왔다. 기동 자체는 양호하나(왕복 폐합 14 mm / 0.64°) **자기보고를 신뢰해 종료 판정·후속 보정을 하는 상위 로직이 있으면 그만큼 어긋난다** | 2026-08-09 | **상환 완료(2026-08-10)** | `spin` 이 이미 쓰는 **절대 목표 yaw** 방식으로 옮긴다(`spin_action_server.cpp:263 target_imu_yaw` + `normalizeAngle(target − cur)`) — 델타 누적 자체가 없어져 클램프·드리프트가 원천 소거된다. `turn` 소스 주석 `:253-256` 이 이미 이 방식을 권하며 「별건(구조 변경)」으로 미뤄 둔 것이다. 착수 전 **래칫이 실제로 발화하는지** 를 누적기 로그로 먼저 확인할 것 — 현재 관측은 n = 2 의 방향 일치일 뿐 **기전 미확정**이다. 두 파일 모두 고쳐야 한다(ADR 2026-08-09 가 수용한 중복 비용) |

---

## [2026-08-09 갱신] debt-048 부분 상환 + 신규 debt-049

**debt-048 — 상환 완료(2026-08-10). 단 등록 당시의 원인 지목은 오진이었다.**

정정: 등록 사유였던 「자기보고가 맵 절대 측위보다 작다」의 원인은 **0 클램프 래칫이 아니었다.**
2026-08-10 실측으로 갈렸다 — ① 외부 계측이 정지 후 3초를 기다려 잡은 **AHRS 기동 후 완화**
(mcl2d 는 평평한데 IMU 만 0.8° 기어감) ② `turn` 시험 당시 **mcl2d 미수렴**(노드 재기동 후
`/initialpose` 재시딩 누락). 정지 순간 기준으로는 자기보고와 IMU 가 +0.056° 로 맞는다.
**구조 변경 자체는 유효하고 완료됐다**(오차 피드백 도입 + 델타 누적 제거) — 다만 그것을
정당화한 증상은 다른 원인이었다. 전말: `issues_and_fixes.md` 2026-08-10 `[Closed]`.

종전 서술: `turn`·`turn_reverse` 의 IMU 델타 누적과 0 클램프 3곳을
**절대 목표 yaw** 방식으로 교체해 원인을 제거했다(ADR `2026-08-09-turn-error-feedback` D1).
SIL 에서 「자기보고 − 지상진값」 괴리가 **−0.001°** 로 사라졌고, 오차가 각도에 무관해졌다
(10°·90° 모두 −0.262°). **다만 실기 재측정 전까지 닫지 않는다** — 실기 관측(0.3~0.5° 괴리)이
정말 이 원인이었는지는 재측정이 판별시험이다.

| id | 유형 | 위치 | 사유 | 식별일 | 상태 | 상환계획 |
| --- | --- | --- | --- | --- | --- | --- |
| **debt-049** | 기술 | `src/Control/Motion_Control/2WS/` **5개 패키지 전부** | ⚠ 2026-08-10 범위 정정: `trnav_2ws_action_server` 뿐 아니라 **2WS 5개 패키지 전부**가 시험 인프라 0이다(`test/` 0 · CMake 등록 0). **부분 상환(2026-08-10)**: 2개 패키지에 gtest 를 도입했다 — `trnav_2ws_core` 의 `TransientGuard` 10건(돌연변이 2건 검출: 주행 중 임계 오용 5 failures · 클램프 제거 2 failures)과 `trnav_2ws_kinematics` 의 `TwoWsDualSteerIK` 14건(돌연변이 2건 검출: `computeSpin` 을 범용 IK 로 되돌림 2 failures · `isInline` 항상 true 3 failures). 합계 **50건**(core 36 + kinematics 14)이며 `trnav_2ws_core` 의 **순수 자산은 전부 덮였다**(`TransientGuard`·`TrapezoidalProfile`·`math_utils`·`robot_geometry`·`RecursiveMovingAverage`·`ActionMutex`)이며 스택 최초의 자동 시험이다. core 쪽에는 `TrapezoidalProfile`·`math_utils` 도 포함되며(돌연변이 3건 검출: fmod 치환 5 · 삼각형 분기 무력화 2 · isComplete 경계 2), `std::remainder` 의 round-half-even 타이브레이크 규약을 명시적으로 고정했다. **남는 것**: 액션서버 4개의 제어 루프는 여전히 시험이 없다 — `execute()` 가 거대한 단일 함수라 리팩터 없이는 단위시험이 불가하고, 억지로 붙이면 거짓 안심만 남는다. 종전 사유: **이 패키지에는 자동 시험이 0건이다** — `test/` 디렉터리도, `CMakeLists.txt` 의 시험 등록도 없다. 2026-08-09 의 구조 변경(델타 누적 → 절대 목표 yaw, bang-bang → PD)은 두 파일의 제어 루프를 통째로 갈았는데 **되돌려도 실패할 시험이 하나도 없다.** 검증은 전부 수동 SIL 프로브에 의존하며, 그 프로브조차 전진판 전용이라 후진은 이번에 즉석 변환본을 썼다(재현 불가) | 2026-08-09 | 미해결 | ① `turn_residual_probe.py` 에 `--action forward\|reverse` 를 넣어 후진을 정식 지원 ② 각 액션의 종료 오차·조향 부동(不動)·ICR 보존을 SIL 로 검사하는 회귀를 `test/` 에 추가 ③ `Tools/amr_test_gui/mutation_check.py` 방식의 돌연변이 확인으로 **검출됨을 증명**(통과 숫자는 커버리지 근거가 아니다 — mistake 2026-08-04-001 · 2026-08-08-002) |


---

## [2026-08-10 등록] debt-050 — `yaw_control_reverse` 의 pose 토픽

| id | 유형 | 위치 | 사유 | 식별일 | 상태 | 상환계획 |
| --- | --- | --- | --- | --- | --- | --- |
| **debt-050** | 기술 | `trnav_2ws_action_server/config/yaw_control_reverse_params.yaml:48` | ⚠ **2026-08-10 오진 정정.** 「pose 를 못 받는다」는 **틀렸다** — `yaw_control_reverse_pose_topic` 은 **읽는 코드가 0건인 죽은 키**였고, `LocalizationMonitor::Params::pose_topic` 기본값이 `/robot_pose`(`localization_monitor.hpp:27`)라 실제로는 **정상 수신**했다(실행 확인: `/robot_pose` 구독자 1→2, `/rtabmap/localization_pose` 는 토픽 자체 부재). yaml 만 보고 코드를 확인하지 않아 없는 결함을 등록했다. 남은 실질 문제는 **죽은 키가 실재하지 않는 토픽을 가리켜 오독을 유발한 것**이다. | 2026-08-10 | **상환 완료(2026-08-10)** | ① 죽은 키를 살렸다 — 코드에 `lm_params.pose_topic = safeParam("yaw_control_reverse_pose_topic", "/robot_pose")` 추가, yaml 값도 `/robot_pose` 로 정정. ② `−7`(헤딩 발산)·`−8`(조향 미도달) 가드를 전진판과 같은 규약으로 이식. ③ **첫 실기 검증 통과** — 헤딩 유지 0.4 m, `status 0`, 최종 헤딩오차 +0.020°, 가드 오탐 0. ⚠ 「`yaw_control` 이 양방향을 덮으므로 폐기」안은 채택하지 않았다 — 두 액션은 `vx_max` 의미(부호 포함 대 magnitude)와 mux 소스 id 가 다르고, 저장소의 방향쌍 패턴을 따른다 |


---

## [2026-08-10 등록] 조향축 비응답 · IMU 추종 실패 — 실기에서 파생

| id | 유형 | 위치 | 사유 | 식별일 | 상태 | 상환계획 |
| --- | --- | --- | --- | --- | --- | --- |
| **debt-051** | 기술 | `can_relay` 조향 경로 (또는 그 이하) | **조향축이 비응답 상태로 빠진다.** 지령이 `/motor/low_cmd` 까지 정상값으로 내려가는데(node3 target_pos = 지령각과 일치) 모터가 안 움직인다. `yaw_control`·`turn` 양쪽에서 동일 재현. **제어권 반납→재획득으로 회복.** `debt-046`(재시작이 축 상태를 지운다)·타 세션 `4aea32d`(구동축 CiA402 운전 상태 복구)와 같은 계열로 보인다 | 2026-08-10 | 미해결 | 비응답 상태에서 `0x6041`(statusword)·`0x6060`(modes)·`0x603F`(error code)를 조향축별로 읽어 무엇이 달라졌는지 확정. 회복 조건(engage 사이클)이 무엇을 다시 쓰는지 `backend.py` 에서 대조 |
| **debt-052** | 기술 | `trnav_2ws_action_server` 전 액션 (조향 도달 판정) | **`yaw_control` 이 조향 미도달을 진단 없이 60초 대기한다.** ⚠ 2026-08-10 정정: 종전 서술 「`turn` 은 Phase 0 타임아웃 경고만 남기고 넘어간다」는 **틀렸다** — 소스 확인 결과 `turn`·`turn_reverse`·`spin` **셋 다** Phase 0 타임아웃에서 `status −3` + `abort()` 로 동일하게 처리한다(각 `:162` · `:165` · `:219`). 경고만 내는 것은 **Phase 4**(기동 완료 후 조향 복귀)이며 셋 다 `non-critical` 라벨이고 그 판단은 타당하다. 실제 결함은 `yaw_control` 고유다 — Phase 0 목표가 δ=0 이라 대개 이미 충족돼 즉시 통과하고, 조향 목표는 **주행 중 계속 바뀌므로** Phase 0 에서 잡히지 않는다. 그 뒤 주 루프의 `TransientGuard` 가 조향 미도달로 `gate_blocked` 를 걸어 구동을 0 으로 묶는데, **가드가 막고 있다는 사실을 보고하는 경로가 없어** 전역 타임아웃(60 s)까지 조용히 대기한 뒤 `status −3` 만 낸다(2026-08-10 실측: 지령 −20.2°, 실제 0.00°, 거리 0.001 m) | 2026-08-10 | **상환 완료(2026-08-10)** — status −8 감시 추가, 실기 2건 확인 | `yaw_control` 주 루프에 **가드 차단 지속 감시**를 넣는다 — `gate_blocked` 가 N 초 연속이면 전용 오류코드로 abort 하고 「조향이 지령에 도달하지 못한다」를 로그에 남긴다. 전역 타임아웃까지 기다리지 않는다. ⚠ `turn`·`spin` 은 손댈 것이 없다(이미 Phase 0 에서 abort) |
| **debt-053** | 기술 | `yaw_control_action_server.cpp:184` 및 주행 루프 | **조대(粗大) 고장 탐지기가 없다.** IMU 가 회전을 못 읽은 2026-08-10 시험에서 **25° 틀어진 채 `status 0`(성공)** 을 반환했다. localization watchdog 은 pose 두절·점프만 본다. ⚠ **「오프셋 1회 + IMU 추종」구조 자체는 결함이 아니다**(사용자 정정) — 현재 측위는 heading 정밀도를 보정해 줄 만큼 정확하지 않아, 미세 제어를 측위로 닫으면 오히려 나빠진다. 측위가 절대 기준을 1회 주고 정밀한 IMU 가 추종하는 현 구조가 맞다. 빠진 것은 **제어 보정이 아니라 고장 탐지**다 | 2026-08-10 | **상환 완료(2026-08-10)** — status −7 탐지기 추가, 실기 2건 확인 | 주행 루프에 `\|보정 yaw − 맵 yaw\| > 임계` 가 N cycle 연속이면 전용 오류코드로 abort. **제어 소스는 IMU 그대로 두고 탐지만 추가한다.** 임계는 **맵 heading 잡음보다 훨씬 크게**(수 도 급) 잡아 오탐을 피하고, 25° 급 고장만 잡는 것이 목적이다 — 정밀도에는 관여하지 않는다. 임계·N 은 주행 중 맵-IMU 괴리 분포를 실측해 정한다 |
| **debt-054** | 이해 | IMU(iahrs) 회전 추종 | **저속 회전(약 0.5 °/s)에서 IMU 가 실제 회전을 거의 읽지 못했다**(실제 +24.7° → IMU +1.7°). 정지 시 드리프트는 정상(10초 0.023°, gyro_z −0.004 °/s)이라 고장은 아니다. 같은 날 제자리 spin 대조(10 dps·2.8 dps)에서는 일치했다 — **회전율 의존인지 병진 동반 여부인지 미확정.** ⚠ **검증 완료된 `turn`·`spin` 은 이 구간이 아니다** — 오늘 실기는 전부 ω ≥ 2.8 °/s 였고(`spin` 10·2.8 dps 비 0.991·1.015, `turn` R=1.0·v=0.05 → ω=2.86 °/s, n=8 왕복 폐합 확인) 거기서 IMU 는 정확했다. **위험 구간은 ω ≲ 1 °/s 로, `turn` 에서는 큰 반경(v=0.05 기준 R ≳ 3 m)에 해당하며 미검증이다** | 2026-08-10 | **규명 완료(2026-08-10) — 유효 구간 확정, 기전은 미확정** | 제자리 spin 을 0.3 / 0.5 / 1.0 / 2.8 dps 로 돌려 IMU 대 맵 비율을 회전율의 함수로 측정. 병진 동반 여부를 가르려면 같은 회전율의 turn 과 대조. 드라이버 설정(바이어스 추정 시상수·ZRU)도 조사 대상 |


---

## [2026-08-10] debt-054 규명 결과

**IMU 회전 추종의 유효 구간을 실측으로 확정했다.** 도구 `Tools/imu_rate_check/`, 전문은
`docs/issues_and_fixes/issues_and_fixes.md` 2026-08-10 `[Closed]`.

```
0.280 °/s → 0.013      0.564 → 0.049·0.065     1.130 → 0.363·0.539
2.84  °/s → 0.988~0.995 (n=4)                  5.69  → 0.988·0.994
⇒ ω ≥ 2.8 °/s 신뢰 가능 · ω ≲ 1 °/s 금지
```

⚠ **닫지 않는 부분**: 원인(기전)은 미확정이다. AHRS 바이어스 추정의 흡수가 유력하나
드라이버 설정(시상수·zero-rate update)을 확인하지 않았다. 유효 구간만 답했다.


---

## [2026-08-10 등록] debt-055 · debt-056

| id | 유형 | 위치 | 사유 | 식별일 | 상태 | 상환계획 |
| --- | --- | --- | --- | --- | --- | --- |
| **debt-055** | 기술 | `trnav_2ws_action_server/src/yaw_control/yaw_control_action_server.cpp` | **파라미터 콜백이 없어 전 파라미터가 생성자 전용**이다. `ros2 param set` 이 `Set parameter successful` 을 반환하면서 **거동은 바뀌지 않는다**(2026-08-10 실측). 현장에서 값을 조정했다고 믿고 시험하면 결과를 오독한다. `spin` 은 콜백이 있어(`spin_action_server.cpp:38`) 일부 키가 hot-reload 된다 | 2026-08-10 | **상환 완료(2026-08-10)** — 콜백 신설 + 비-화이트리스트 명시 거부 + 죽은 키 5개 삭제, 검증 4종 | `spin` 과 같은 형태로 `add_on_set_parameters_callback` + 화이트리스트 + 범위 검증 추가. 화이트리스트에 넣지 않을 키는 **선언 자체를 read-only 로** 두어 set 이 실패하게 만든다 — 거짓 성공이 가장 나쁘다 |
| **debt-056** | 기술 | `trnav_2ws_action_server/launch/` | **`yaw_control` 만 SIL 런치가 없다.** 다른 8개 기동(`turn`·`turn_reverse`·`spin`·`crab_linear`·`translate_*`·`mpc*`)에는 `sil_*.launch.py` 가 있는데 `yaw_control`·`yaw_control_reverse` 는 없어 **SIL 검증 이력이 0**이다. 2026-08-10 의 탐지기 검증도 실기에서만 했다 | 2026-08-10 | **상환 완료(2026-08-10)** — sil_yaw_control(_reverse).launch.py 신설, 정상 주행·콜백·−7 재현 확인 | `sil_turn.launch.py` 를 본떠 `sil_yaw_control.launch.py` 신설. `/robot_pose` 공급원(SIL 플랜트 → 어댑터)을 어떻게 채울지가 관건이며, 그것이 정해지면 발산 탐지기의 (b) 시험도 SIL 로 옮길 수 있다 |


---

## [2026-08-10 등록] debt-057 — pytest 수집 중단

| id | 유형 | 위치 | 사유 | 식별일 | 상태 | 상환계획 |
| --- | --- | --- | --- | --- | --- | --- |
| **debt-057** | 기술 | `src/Comm/CAN/can_relay/test/test_master_frame_match.py:31` | **모듈 레벨 skip 이 전체 수집을 중단시킨다.** 캡처 파일(`Log/homing_capture_220350.jsonl`)이 없으면 `pytest test/` 가 `collected 0 items / 1 skipped` 로 끝난다 — 알파벳 순서상 앞선 6개 파일도 수집되지 않는다(pytest 6.2.5). 출력이 `1 skipped` 뿐이라 **「돌릴 게 없다/문제 없다」로 읽히고 실패가 보이지 않는다.** 캡처가 있는 환경에서는 정상 수집되므로 **환경에 따라 조용히 달라진다** | 2026-08-10 | **상환 완료(2026-08-10)** — fixture 로 전환, `pytest test/` 가 393 passed / 8 skipped (exit 0) | 모듈 레벨 skip 대신 **테스트 함수 단위 skip**(`@pytest.mark.skipif`)으로 바꿔 수집이 계속되게 한다. 또는 캡처 부재 시 fixture 에서 skip. 고친 뒤 `pytest test/` 가 393+ 를 수집하는지로 검증 |


---

## [2026-08-10 등록] debt-058 — 전량 실행 종료 시 간헐 segfault

| id | 유형 | 이해 | 위치 | 사유 | 식별일 | 상태 | 상환계획 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **debt-058** | 이해 | — | `src/Comm/CAN/can_relay/test/` 전량 실행 | ⚠ **2026-08-10 정정: 「종료 시점」이 아니다.** faulthandler 로 지점을 특정했다 — `test_gui_node.py:66` 의 `rig` 픽스처가 `driver_node.py:218` 에서 `rclpy` `create_service` 를 부르는 **실행 중**(약 53% 지점)에 죽는다. 종전 서술(「모두 통과 뒤 종료 시점」)은 요약줄만 보고 추정한 것이었고 틀렸다. **간헐적**이다 — 같은 명령이 통과하기도 한다. 분리 실행하면 양쪽 다 정상이다: `test_gui_node.py` 단독 15 passed(exit 0), 나머지 전량 383 passed·8 skipped(exit 0). 한 프로세스에 PyQt5 와 rclpy 가 함께 적재되는 것이 배경으로 보이나 **기전 미확정**. ⚠ 요약줄이 정상으로 보이는 실행도 있으므로 **종료코드를 봐야 안다** | 2026-08-10 | **상환 완료(2026-08-10)** — 스핀 스레드 join 추가. A/B 실측 미수정 2/12 실패 · 수정 0/12, 전량 4회 연속 exit 0 | 크래시 지점은 특정됐다(`test_gui_node.py` 의 rclpy 노드·서비스 생성). 남은 것은 **왜 간헐적인가** — 같은 프로세스에서 앞선 시험이 남긴 rclpy 컨텍스트·PyQt5 적재와의 상호작용을 좁힌다. 실무 회피는 **파일 그룹 분리 실행**(`test_gui_node.py` 를 따로) 또는 `pytest-forked`. **먼저 CI 에서 종료코드를 보는지 확인할 것** — 안 보면 이 크래시는 영원히 조용하다 |


| debt-059 | ~~이해~~ **상환(2026-08-10)** | `yaw_control*` + `localization_monitor.cpp` | 감사 지적: `lookupMapToBase` 에 stamp 신선도 검사가 없고 `setMaxCmdSpeed` 를 yaw 계열이 **한 번도 호출하지 않아**(`grep` 0건) `max_cmd_speed_=0` → `checkLocalizationHealth` 가 조기 반환, **−4·−5·−6 이 전부 발화 불가**. 사실이면 −7 가드의 전제(`map_yaw_fresh`)가 성립하지 않고 pose 두절 시 시한까지 주행한다 | **상환** | 확인 결과 **사실이었다**. `setMaxCmdSpeed` 배선 + `map_yaw_fresh` 0.3 s 신선도 판정. SIL `yaw_loc` 케이스로 고정(배선 제거 시 −3, 배선 시 −4) |
| debt-060 | ~~기술~~ **상환(2026-08-10)** | `yaw_control*` 파라미터 콜백 | 감사 지적: 검증 통과 즉시 멤버를 써서 **뒤 파라미터가 거부되면 앞은 이미 반영**된 채 노드 저장소와 영구 불일치. 검증/커밋 2단계 분리 필요 | **상환** | 검증/반영 2단계 분리(`commits` 지연 실행) + 타입 가드 |
| debt-061 | ~~기술~~ **상환(2026-08-10)** | `yaw_control*` 멤버 | 감사 지적: 콜백이 쓰는 멤버가 비-atomic 인데 detached execute 스레드가 동시에 읽는다. 베이스는 같은 이유로 `std::atomic` 을 쓴다(`qd_action_server_base.hpp:195`) | **상환** | 멤버 10개 `std::atomic` 화(hot-reload 의미는 유지). 로그 인자 8곳 `.load()` |
| debt-062 | ~~기술~~ **상환(2026-08-10)** | `turn*` ±180° 경계 | 감사 지적: `spin` 이 가진 경계 결정화(`kBoundaryEpsDeg`, antipode 고정)가 turn 에 없다 — `target_angle` 180.0 vs 180.001 에서 회전 **방향이 반대**가 될 수 있다 | **상환** | 경계 결정화 + antipode 고정 이식 |
| debt-063 | ~~기술~~ **상환(2026-08-10)** | `DirectBackend` 워치독 | 감사 지적: 지령 워치독이 없어(RelayBackend 는 0.3 s TTL) UI 가 멈춰도 마지막 구동 지령이 무한 재송신. RX 워치독도 `_rx_at=0.0` 초기값이 falsy 라 **응답을 한 번도 못 받으면 영원히 무장되지 않는다** | **상환** | `CMD_TTL_S=0.5` 지령 워치독 + engage 시 `_rx_at` 무장. 회귀 2건(돌연변이 검출 확인) |
| debt-064 | ~~기술~~ **상환(2026-08-10)** | 신규 gtest 커버리지 | 감사가 돌연변이로 실증한 잔여 구멍: 사다리꼴의 **감속 개시점·가속 종료점이 전혀 고정되지 않음**(어디서 밟아도 통과) · `exit_speed` 가 DONE 분기만 밟아 감속 램프 미검사 · `entry_speed` 실현가능성 가드 삭제해도 통과. 배포 yaml 값도 무보증 | **상환** | 전이점(10·80)·경계 연속성·감속 램프 중간점 고정. 돌연변이 3건 검출 확인 |

| debt-065 | 이해 | `trnav_2ws_core/src/motion_profile.cpp` 생성자 | `entry_speed` 실현가능성 가드가 `getSpeed` 를 통해 **관측 불가능**하다(5개 조합 전 구간 차이 0). 가드 발동 조건이 곧 `accel_dist_=0` 이라 ACCEL 분기가 실행되지 않고, DECEL 식은 `entry_speed` 를 쓰지 않는다. 방어적 대수로 남길지 죽은 코드로 제거할지 판단 필요 | 미판단 | 연속 기동(`crab_linear`)에서 `entry_speed` 가 실제로 어떤 값으로 들어오는지 확인 후 결정. 등가성은 시험으로 고정해 뒀다 |

| debt-066 | ~~기술~~ **상환(2026-08-10)** | `translate_forward` · `translate_reverse` · `crab_linear` · `mpc` · `mpc_reverse` 의 지역 `velProfile` | `yaw_control` 전진판에서 발견한 **부호 있는 비교로 인한 가·감속 한계 뒤바뀜**이 다른 서버 사본에도 있는지 미확인. 후진을 허용하는 서버라면 같은 결함(제동거리 2배)이다. 공용 `trnav_2ws_core::rampToward` 는 이미 있다 | **상환** | 전수 조사: 후진판 2개는 정상, `crab_linear`·`translate_forward`·`mpc` 가 부호 비교였다. `crab_linear` 은 **후방 크랩**(θ 90~270°, `direction=−1`)에서 실제 도달. 전진 전용 2개는 양수 구간 차이 0 임을 증명 후 치환. 지역 사본 0 |

| debt-067 | 이해 | `yaw_control*` 의 −7·−8 | 이번에 바꾼 두 가드의 **실기 확인이 남았다**. −8 진전 기반 로직은 즉응 플랜트라 SIL 로 발화시킬 수 없고, −7 의 pose 샘플 디바운스는 SIL(50 Hz)에서 종전과 구분되지 않는다(실차는 10 Hz) | 미확인 | 실기에서 ① `max_steer_deg=90` goal 1회(−8 오탐 없음 확인) ② `/robot_pose` 를 10 Hz 로 둔 선회 1회(−7 오탐 없음 확인) |

| debt-068 | 이해 | 실차 `/robot_pose` **정본 발행자** | **⚠ 2026-08-10 정정 2회.** ① 「배선 불일치」가 아니다 — 분리는 의도된 설계(`pose_node.py:20-31`). ② 「발행자가 누구인지 미확인」도 아니다 — **2026-08-06 실측 기록이 이미 있다** (`issues_and_fixes.md`: `yaw_control` 발행자 1 / `/rtabmap/localization_pose` 발행자 0, `trnav_pose_publisher` 는 저장소 부재, 「실차 경로 정상」은 확인 불가로 자기정정됨). **진짜 미결은 하나** — 실차 정본 발행자(PC 측위)를 무엇으로 세울 것인가: Seer 를 정본으로 쓸지(`seer_pose.launch.py pose_topic:=/robot_pose`), mcl2d 를 `PoseStamped`/`/robot_pose` 로 잇는 어댑터를 둘지. 조회한 기록: `issues_and_fixes.md`(`robot_pose`), `docs/code_review/pose-topic-wiring/2026-08-10.md`. 경위: `docs/claude-mistake/2026-08-10-004` | 미결(설계 결정) | 사용자 결정 사항. 결정 전까지 실기 기동은 `pose_topic:=` 을 **명령줄에 명시**해 결속을 남긴다 |
