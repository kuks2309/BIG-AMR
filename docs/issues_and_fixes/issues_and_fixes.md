# 이슈 및 수정 기록 (Issues and Fixes)

---

## 2026-07-29

### [Fix] 크랩 주행에서 조향만 되고 구동이 취소됨 — 제어권 재획득 시 구동축이 떨어져 있다

- **문제**: 크랩(좌/우 90°)·전진 조그에서 **조향은 되는데 구동이 안 됐다.** 앞선 수정으로
  들어간 가드가 사유를 남겼다 — `⚠ 구동 취소 — 구동축이 운전 가능 상태가 아닙니다
  (operation enabled {1: False, 2: True}, fault {1: False, 2: False})`.
- **원인**: **제어권을 Seer 에게 반환했다 되찾으면 앞 구동축(node1)이 `Switch On Disabled`
  로 떨어져 있다.** GUI 로그 시각으로 확정:
  - `13:24:32` 구동 `raw=-1222` 정상 주행 → `13:24:35` **제어권 반환**
  - 9 분 뒤 `13:33:54` **제어권 재획득** → `13:34:02` 부터 구동 취소 반복
  - node2 는 `True` 를 유지해 **node1 만의 현상**이고, `fault=False` 라 과부하 재발이 아니다.
  `TongyiCan.take(True)` 는 릴레이·폴링만 세우고 **구동축 운전 상태를 확인하지 않았다**
  (`Tools/amr_test_gui/tongyi_can.py`).
- **해결**: `ensure_drives_enabled()` 신설, `take(True)` 끝에서 호출.
  상태워드가 들어올 틈(0.8 s)을 준 뒤 운전 불가 축이 있으면 `enable_drives()` 를 돌린다.
  **fault 가 서 있으면 자동으로 켜지 않고** 사유를 로그에 남긴다 — 원인을 모른 채
  재기동하면 과부하가 재발하거나 모터를 상하게 하므로, 그때는 운전자가 `구동축 활성화`
  버튼으로 확인을 거쳐 켠다.
- **파일**: `Tools/amr_test_gui/tongyi_can.py` ·
  `Tools/amr_test_gui/test/test_drive_enable.py`(회귀 3건 추가, 120 → 123 passed)
- **상태**: 완료 — 실기 확인
  - 상태 복구(내 계측): 제어권 획득 시 `n1 0x8050 enabled=0` → 자동 활성화 →
    `n1 0x8037 enabled=1`, 양축 운전 가능
  - **주행 확인(사용자 관측, 13:49 "지금은 잘됨")** — 크랩 주행 정상. 이 시점 GUI 는
    사용자가 `can_relay` 로 띄운 인스턴스(pid 1690086)라 로그가 내 쪽에 없다.
    구동 여부의 근거는 **사용자 관측**이고, 상태 복구만 내가 계측했다.
- **범위**: 이전 마스터가 왜 구동축을 내려 두는지는 **규명 대상이 아니다.** 제어권을 잡는
  쪽이 필요한 상태를 갖추는 것이 정상 책임 분담이고, 획득 시 점검·enable 로 충분하다
  (사용자 판정 2026-07-29). debt-022 는 그에 따라 **해결**로 닫는다.

---

## 2026-07-29

### [Fix] 구동 지령을 넣어도 바퀴가 안 돎 — 구동축이 운전 가능 상태가 아니었다

- **문제**: 조그를 눌러도 구동륜이 돌지 않았다. GUI 로그는 정상으로 보였다
  (`조향 정착 — 구동 raw=-1222`). 사용자는 "뒷바퀴 구동이 안 된다"·"구 GUI 는 문제
  없었다" 고 보고했고, 펌웨어인지 UI 인지 판정이 필요했다.
- **원인**: 지령이 아니라 **드라이브 상태**였다.
  - `0x60FF=-1222` 를 3 초 넣었으나 **엔코더가 1 count 도 안 변함**
    (node1 `-516,397` 고정 / node2 `222,376` 고정). GUI 를 거치지 않은 맨 스크립트도 동일 →
    **UI 배제**. `_drive(u)` 프레임은 리팩터 전후 전건 동일 → **리팩터 배제**.
    드라이브가 **자기 상태워드로** 보고 → **판다 펌웨어 배제**.
  - 양 구동축 **`operation enabled`(상태워드 bit2) = 0**, node1 은
    **`0x603F = 0x0080` Motor overload alarm**(Handbook §6.6.4 p.7614).
    Seer 알람 `Motor Error:FrontWalk-0x80` 이 독립 경로로 동일 확인(12:53:18).
  - **GUI 에 복구 수단이 없었다** — `Tools/amr_test_gui/tongyi_can.py` `TongyiCan.drive()`
    는 `0x60FF` 만 보내고 조향(`steer_axis`)처럼 `0x6040` 을 동반하지 않는다.
    그동안은 Seer 가 켜 둔 상태를 물려받아 동작했을 뿐이다.
- **해결**: `TongyiCan` 에 CiA402 상태 복구 경로를 신설(Handbook §6.6.1 명령표 근거).
  - `drives_ready()` · `drive_faults()` — 상태워드 bit2/bit3 판정
  - `enable_drives()` — Fault Reset(bit7 **상승엣지**) → **fault 가 걷힐 때까지 대기**
    → Shutdown `0x06` → Switch On `0x07` → Enable Operation `0x0F`
  - `_jog_run` 이 구동 직전 운전 가능 여부를 확인하고, 아니면 **사유를 남기고 취소**한다
    (전에는 지령만 나가고 조용히 실패해 원인을 가렸다)
  - GUI 에 `구동축 활성화 (FAULT 해제)` 버튼 + 과부하 재발 경고 확인 대화상자
  - ⚠ **대기 단계는 실기가 가르쳐 준 것** — 첫 시도에서 리셋 직후 50 ms 간격으로
    전이를 몰아 보냈더니 node1 이 fault 만 걷히고 `Switch On Disabled(0x8050)` 에 멈췄다.
- **파일**: `Tools/amr_test_gui/tongyi_can.py` · `Tools/amr_test_gui/gui.py` ·
  `Tools/amr_test_gui/test/test_drive_enable.py`(신규 10건, 110 → 120 passed)
- **상태**: 완료 — 실기 복구·주행 확인
  - 상태 복구: n1 `0x8018`→`0x8037` / n2 `0x8050`→`0x8037` (양축 operation enabled=1 · fault=0)
  - **주행 확인 (13:16:37~13:17:07)**: 전진 `raw=-1222` 로 19 초 주행, 후진 `raw=+1222` 정상.
    사용자 확인 "문제 해결". 신설한 운전가능 가드가 **한 번도 발동하지 않았다** —
    운전 불가였다면 `⚠ 구동 취소 — 구동축이 운전 가능 상태가 아닙니다` 가 찍혔을 것이다.
- **미해결**: 과부하(`0x0080`)의 **물리적 원인은 규명되지 않았다.** Handbook §6.6.4 는
  "부하가 정격을 넘는지 확인" 을 요구한다. 상태만 되돌렸으므로 원인이 남아 있으면 재발한다.
  정지 중 node2 가 −16.07 A 를 먹던 관측도 미해명이다.

---

## 2026-07-28

### [Fix] 조향 슬라이더가 먹통 — 실측 되먹임 + 78×20 px 크기

- **문제**: `앞뒤 바퀴 조정` 슬라이더를 움직여도 눈금이 제자리로 돌아오고 조향 지령이
  나가지 않았다. 같은 세션에서 조그 구동(`0x60FF`)은 정상 동작해 조향만 안 되는 비대칭이었다.
- **원인**: 두 결함이 겹쳤다.
  - ① **실측 되먹임** — `_redraw_wheel` 이 실측 각도를 슬라이더에 되썼다
    (`Tools/amr_test_gui/gui.py` 구 `_sync_sliders`). 폴링이 약 5 Hz 라 손을 뗀 뒤 0.2 초 안에
    눈금이 원위치로 튕겼다. 슬라이더는 사용자가 **목표를 넣는 명령 입력**인데 거기에 실측을
    되먹여 방금 넣은 값을 지웠다. 또 마우스 드래그가 아닌 조작(키보드·홈 클릭)은
    `sliderReleased` 가 오지 않아 **지령이 아예 나가지 않았다**.
  - ② **크기** (실제 원인) — 슬라이더가 **78×20 px** 이었다. 범위 ±90°(181 단계)이므로
    **1 px = 2.3°**, 핸들은 10 px 남짓이라 잡을 수 없었다. `앞뒤 바퀴 조정` 그룹 348 px 중
    이름 라벨 108 px · 값 라벨 144 px 가 차지하고 슬라이더에 78 px 만 남는 배치였다.
    실측 병기를 넣으며 값 라벨 폭을 46 → 120 으로 올린 것이 결정타였으나, 근본은
    **이름·슬라이더·값을 한 줄에 나란히 놓은 배치**다.
- **해결**:
  - `_sync_sliders` 삭제(20 줄). `_redraw_wheel` 은 그림만 그린다. 목표·실측은
    `_update_wheel_labels` 가 `+30°  (실측 +12.3°)` 로 나란히 보여준다.
  - 슬라이더 배선을 축별로 분리 — 드래그는 `sliderReleased` 로 1 회, 키보드·홈 클릭은
    `valueChanged` 에서 즉시 송신(`_on_wheel_changed` → `_send_steer`).
  - 레이아웃 재구성 — 슬라이더가 **자기 줄을 통째로** 쓴다. 이름·값은 위 줄에 좌우 배치.
    결과 **324×30 px**(1 px = 0.56°), `pageStep=5`.
  - 진단 계측 — `log()` 를 stdout 에도 흘리고, 버리던 SDO abort(`0x80`) 응답을 사유와 함께
    로그에 남긴다. **CAN 송신은 한 줄도 추가하지 않았다.**
- **파일**: `Tools/amr_test_gui/gui.py` · `Tools/amr_test_gui/test/test_slider.py`(신설 12건)
- **상태**: 완료 — 실기 검증(2026-07-28 21:06). 로그 `조향 지령 N4 → -34°` · `N3 → +19°`,
  판다 직독 실측 `3 F.S +18.9°` · `4 R.S -34.0°` 로 추종 확인. 테스트 88 건 통과.

## 2026-07-28

### [Fix] CCTV 뷰어·탐지기 조용한 결함 3건 (적대적 설계 검토 파생)

- **문제**: ① 뷰어에서 프레임이 끊겨도 헤더가 **마지막 FPS 를 영원히 표시**하고 `_pixmap` 도 지워지지
  않아 **정지 화면이 라이브처럼 보였다**(감시 기능의 조용한 실패). ② 레이아웃 변경 후 **정지 경고가
  영구히 나가지 않았다**. ③ 탐지기가 주석 영상 구독자가 **0인데도** 프레임당 약 2.8 MB 를 두 번
  복사해 27 Hz 로 발행하며 추론 예산을 깎았다.
- **원인**:
  - ① `_fps` 는 `update_frame` 안에서만 갱신되고 **0 으로 감쇠하는 경로가 없다** —
    `vision_guard/main_window.py:94,131-133`.
  - ② 새 셀은 `_frames_rendered = 0` 으로 시작(`main_window.py:97`)하는데 `_last_report_frames` 는
    초기화되지 않아(`:174`) `delta = 0 - 이전누적` 이 **음수**가 되고, `delta == 0` 정지 검사(`:233`)를
    통과하지 못했다.
  - ③ `publish_annotated` 는 기동 파라미터일 뿐 구독자 유무를 보지 않았다 —
    `yolo_detector/detector_node.py` 주석 발행 블록.
- **해결**:
  - ① `_STALE_AFTER_S = 2.0` + `CameraCell.check_stale()` 추가, `_pump()` 이 매 틱 호출. 강등 시
    `_fps = 0.0` + 헤더 `신호 없음`. 프레임 복귀 시 자동 해제. (약 30줄 추가)
  - ② `_apply_layout()` 에서 `_last_report_frames.clear()`. (1줄 + 주석)
  - ③ 발행 조건에 `get_subscription_count() > 0` 추가 — 파라미터는 유지하고 비용만 제거. (1줄 + 주석)
- **파일**: `src/Sensors/Camera/USB/ui/vision_guard/vision_guard/main_window.py`,
  `src/Sensors/Camera/USB/ui/vision_guard/test/test_stale_detection.py`(신규 12 테스트),
  `src/AI/yolo_detector/yolo_detector/detector_node.py`
- **상태**: 완료 — vision_guard 25 passed(기존 13 + 신규 12), yolo_detector 23 passed.
  ③ 은 실행 검증: 구독자 0 → 주석 발행 없음(`Subscription count: 0`, 박스 토픽은 4.36 Hz 정상),
  구독자 부착 → 4.85 Hz 로 즉시 재개. 근거·경위는
  [ADR 2026-07-28-cctv-ai-overlay-toggle](../adr/2026-07-28-cctv-ai-overlay-toggle.md) §2 (F6/F9/F8).

### [Fix] 호밍 기록의 잘못된 서술 정정 + 정오표 수립 (2회 적대적 검증)

- **문제**: 2026-07-27 호밍 조사에서 생성된 기록 다수가 (a) `0x6041` bit15 **전이 시각**을 폴 상한값으로
  확정형 서술 (b) `Tool/`(단수) 경로 인용 (c) `0x6040` 반복률 「~50 Hz」 (d) 호밍 중 write 정지 범위를
  조향축으로 과소 서술 — 로 부정확했다. 더해 **정정하려고 만든 정오표(v1) 자체가 신규 오류 7건을 심었다**
  (정확한 Handbook 인용을 「오진」으로 규정 등).
- **원인**: ① 폴링 관측값을 이벤트 시각으로 취급(직전 폴 간격 미확인) — `Log/homing_capture_220350.jsonl`
  node3 `0x6041` 최대 폴 간격 12.818 s ② 한 노드 결과를 전 노드로 일반화 ③ v1 작성 시 원문 재대조 없이
  기억·요약에 의존해 **정확한 인용을 틀렸다고 판정**(자기 표와 모순).
- **해결**: 원문(`pdftotext -f N -l N`) 재대조로 쪽 사실을 확정하고 v2 정오표로 전면 개정.
  저장소 잔여 서술 11건 정정(전이 시각 → 「0 최초 관측」 + 확정 구간 병기, `Tool/`→`Tools/`),
  `docs/debt/registry.md:146` 의 `0x6040=0x86` 「enable」 오라벨을 「fault reset(+enable voltage)」로 정정
  (Bit7 rising edge = Fault Reset, `Enable Operation`(0x0F) 아님).
  미해결 항목은 **debt-008**(Handbook 1차 source 내부 DI 번호 충돌)·**debt-009**(캡처 출처·12.62 s
  무응답 구간 미확정)로 등록.
- **검증**: 40 에이전트 적대적 재검증(wf_83c55976-efe) → v1 작성 → **10 에이전트가 v1 을 공격**
  (wf_ea102b6e-a7c, 비-CONFIRMED 51건·신규오류 7건 검출) → v2. 각 레인이 캡처를 직접 재파싱하고
  PDF 를 각자 재추출. 이전 실패 레인(`cap-digital-in`) 재수행 완료.
- **파일**: `docs/verified_facts/2026-07-28-errata.md`(신규 v2), `docs/debt/registry.md`,
  `docs/verified_facts/2026-07-27.md`, `docs/ros2_driver/2026-07-09-design-inputs.md`,
  `References/Tongyi-Motor-Controller/docs/tongyi-motor-protocol-tables.md`,
  `References/Tongyi-Motor-Controller/docs/tongyi-canopen-protocol-reference.md`,
  `Tools/docking_field_kit/amap2_monitor.py`, `Tools/docking_field_kit/HANDOFF-amap2.md`
- **상태**: 완료 (미해결분은 debt-008·debt-009 로 이관)

---

## 2026-07-27

### [Fix] 로봇 단독 전원 인가 시 Seer CAN/모터 알람 지속 — 판다 부팅 기본 비트레이트 500 kbps

- **문제**: 호스트 소프트웨어를 **하나도 실행하지 않은 채** 전원만 인가하면 Seer 가 `52106 odo data lost` + `52111 motor driver connection error` + `54022 CAN1 Bit Recessive error`(10 초마다 타임스탬프 갱신 = 진행 중) + `54301 Motor is calibrating` 을 지속 발생. 판다 health 는 `safety_mode=0`·`power_save=1`·`car_harness_status=1`·`faults=0`.
- **원인**: 세 가지가 겹침 — ① `Tools/Can_Relay/panda-firmware/board/drivers/harness.h:91` `set_intercept_relay(false)`("keep busses connected by default")로 **릴레이가 버스를 물리 연결**(Seer↔모터 직결, 펌웨어 포워딩 무관) ② `board/main.c:405-406` `can_silent = ALL_CAN_LIVE` + 루프마다 `enable_can_transceivers(true)` 로 **판다가 그 버스에 live 로 부착** ③ `board/drivers/can_common.h:164-166` `.can_speed = 5000U` = **500 kbps**(버스는 250 kbps). 단위 근거: `usb_comms.h:322` 가 `wIndex` 를 그대로 저장, `panda/python/__init__.py:550` 이 `speed*10` 송신. ⇒ 250k 버스에 500k 로 붙은 live 노드가 전 프레임을 오독해 에러 프레임을 방출, 버스 파괴. **호스트 도구가 take() 에서 `set_can_speed_kbps(b,250)` 을 부르기 때문에 지금까지 가려져 있었다**(= PC 가 붙어야만 버스가 성립하는 구조).
- **해결**: `bus_config[]` 의 bus0/1/2 `can_speed` `5000U`→`2500U`(250 kbps). 함께 ① heartbeat 상실 블록(`main.c`)에 `set_intercept_relay(false)` + `pc_authority = false` 추가 — 이상 상태에서 릴레이가 intercept 로 남지 않도록(fail-open, 사용자 요구) ② `safety/safety_seer_gate.h` freeze 집합에 `0x6041` 추가(Seer SDO 폴 12초 실측으로 확정: `0x6064` 2718~2920회·`0x6041` 66~312회·`0x6078` 66회, **`0x606C` 0회 = 미폴**). 총 3 파일 소수 라인.
- **파일**: `Tools/Can_Relay/panda-firmware/board/drivers/can_common.h`, `.../board/main.c`, `.../board/safety/safety_seer_gate.h`, `docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md`(신규)
- **상태**: 완료 — 빌드 `-Werror` 0 error → 플래시 → **비트레이트 미설정 상태로** 8초 29,625 프레임 수신(부팅 기본 250 kbps 확정) · Seer `errors=[]` 21초+ 유지 · `rx_errs=0 faults=0` · 현장 육안 확인("오류 안남"). ⚠ 펌웨어 version 문자열은 상위 레포 HEAD 에서 오므로(`panda-firmware` 자체 .git 없음) 커밋 전 빌드는 신구 구분 불가 — 현재 플래시본은 `DEV-d98bc1a5-DEBUG` 표기이나 내용은 본 수정 반영본이다.

> ### ⚠ [2026-07-27 감사 부기] 위 entry 의 미검증·미판정 표시 (원문 무변경 · 값/코드 무변경)
>
> **(1) "상태: 완료" 를 변경 단위로 분리** — 이 entry 의 변경은 3건인데(① `can_speed` 5000U→2500U · ② heartbeat fail-open · ③ `0x6041` freeze 추가) 인용된 증거는 전부 ① 에 대한 것뿐이다.
> - **① 비트레이트 정합 = 실측 검증 완료** (증거 상동: 비트레이트 미설정 상태 8초 29,625 프레임 · Seer `errors=[]` 21초+ · `rx_errs=0 faults=0`). 코드 반영 확인: `Tools/Can_Relay/panda-firmware/board/drivers/can_common.h:174-176`(`.can_speed = 2500U` ×3).
> - **② heartbeat fail-open = 미검증** — heartbeat 를 실제로 끊어본 시험 기록이 본 문서·ADR 어디에도 없다. 코드 반영 자체는 확인됨(`.../board/main.c:257-258`).
> - **③ `0x6041` freeze = 미검증** — `docs/can_relay/test-process.md:14` 가 요구하는 실로봇 판정(구동 중 **신규** 52111/52106/52954/54301 + 55602 = 0) 미실시. 코드 반영 자체는 확인됨(`.../board/safety/safety_seer_gate.h:170-172` `seer_is_motion_obj()` 에 `0x6041U` 포함).
>
> **(2) "fail-open → Seer 가 모터를 직접 보게 한다" = 미판정 모순** (어느 쪽으로도 고치지 않음)
> - *이쪽 기록*: heartbeat 상실 시 `set_intercept_relay(false)` + `pc_authority = false` 로 물리 통과 복귀 → Seer 직결 (`Tools/Can_Relay/panda-firmware/board/main.c:252-258` 주석·코드).
> - *어긋나는 기록*: `Tools/docking_field_kit/PINMAP.md:80` 은 "passthrough(fail-safe)는 **판다 미전원 시** 기계적 브릿지로 확실히 동작(검증됨)"이라 적고, 뒤이어 "판다 켜진 SILENT 는 트랜시버 간섭으로 불통"을 (현재 취소선 + `PINMAP.md:82-103` 의 **미판정 모순** 부기 상태로) 기록한다. heartbeat 상실 경로는 **판다가 전원 ON 인 채 SILENT 로 전환**되고(`main.c:248-250` → `main.c:88-93` `set_intercept_relay(false)` + `can_silent = ALL_CAN_SILENT`) 메인 루프가 매 회전 `enable_can_transceivers(true)` 로 트랜시버를 계속 켜 두는(`main.c:421`) 상태 — 즉 PINMAP 이 "불통"이라 적은 바로 그 조건이다.
> - ⇒ "Seer 가 모터를 직접 보게 된다"는 **아직 실증되지 않았다**. (릴레이가 물리적으로 붙는다는 점은 별개로 확인돼 있다 — `PINMAP.md:87-90`.)
> - **판정에 필요한 측정**: 250 kbps 정합 펌웨어에서 heartbeat 를 5초 이상 끊은 뒤(판다 전원 ON · SILENT · relay OFF) ⓐ Seer↔모터 SDO 왕복(요청/응답 쌍) 프레임 수 ⓑ per-bus `can_health` 에러 카운터 ⓒ Seer 알람(52111/52106/54022) 을 동시 실측. **값·코드는 변경하지 말 것.**
>
> **(3) SDO 폴 "12초 실측으로 확정" 은 창 조건 미기재** — 관측은 **12초 단일 창** 기준이며 그 창의 로봇 상태(정차/구동 · `pc_authority` engage 여부 · 호밍 진행 여부)가 기록돼 있지 않다. 특히 `0x606C`(실속도)는 정차 창에서 0회여도 구동/호밍 중에는 폴될 수 있으며 이를 배제한 측정이 없다 ⇒ **"`0x606C` 0회 = 미폴" 은 재측정 전까지 잠정**. 같은 전제가 펌웨어 주석 `.../board/safety/safety_seer_gate.h:138`("0회(Seer 미폴) → 현재 죽은 분기")에도 전파돼 있다(단 `:171-172` 가 `0x606C` 를 freeze 집합에 유지하므로 현재 동작 위험은 낮다). **판정에 필요한 측정**: 구동 중·재호밍 중 각 60초 이상 SDO 폴 카운트 재수집. **freeze 집합·값은 변경하지 말 것.**

### [Fix] vision_guard 6대 표시가 16fps로 저하 — 프레임 변환의 BGR→RGB 복사(9.2ms/대)가 렌더 병목

- **문제**: 퍼블리셔 캡처는 29.7fps인데 뷰어 표시는 16~20fps. 6대 동시 표시 시에만 발현.
- **원인**: [실측] 구간 분리 측정 결과 병목 2개. **(주)** `main_window.bgr_to_qimage` 가 `np.ascontiguousarray(frame[:, :, ::-1])`(비연속 스트라이드 복사) + `QImage.copy()` 로 2.76MB 프레임을 **두 번 복사** → 오프스크린 실측 **9.2ms/대**(변환 12.0ms/대 중 76%). 6대×30Hz면 한 틱 72ms 로 30Hz 예산(33ms) 초과 → **렌더 상한 13.9fps**. 실측 CPU도 일치: 프로세스 145%, GUI 메인 스레드 단독 83%. **(부)** raw bgr8 전송 자체 손실 — 아무 것도 안 하는 카운트 전용 구독자(CPU 55%)도 24Hz만 수신(6대 합계 166MB/s, best-effort/depth=1).
- **해결**: Qt 가 BGR 을 직접 읽는 `QImage.Format_BGR888` 로 채널 스왑 복사를 제거하고, numpy 버퍼 수명이 살아있는 함수 내부에서 `QPixmap.fromImage` 로 소유권을 옮기도록 `bgr_to_qimage` → `bgr_to_pixmap` 교체(호출부 `_pump`·`CameraCell.update_frame` 포함 3곳). 대안 비교 실측: 현재 14.3ms → **BGR888 무복사 1.1ms**(12.6배) / cv2 선축소 0.9~2.2ms.
- **파일**: `src/Sensors/Camera/USB/ui/vision_guard/vision_guard/main_window.py`, `.../test/test_frame_convert.py`(신규 — 채널 순서·크기·원본 해제 후 생존·비연속 입력 7 케이스)
- **상태**: 완료. 테스트 **14 passed**(기존 7 + 신규 7), 빌드 클린. 실측: 표시 **20.7~24.1 fps**(6/6), 뷰어 CPU **145% → 85%**. 남은 상한은 (부)의 전송 손실(~24Hz)이며 compressed transport 도입은 미적용(별건).

### [Diag] 뷰어를 kill -9 로 강제 종료하면 퍼블리셔 쓰기가 막혀 일부 카메라가 영구 "No Signal"

- **문제**: 진단 중 뷰어를 `kill -9` 로 수차례 종료한 뒤, 재기동한 뷰어에서 cam0·cam1·cam2·cam5 가 **콜백 0회**("No Signal", 에러 로그 없음). 동시에 해당 4대의 퍼블리셔 캡처 FPS 가 29.7 → 18(순간 0.8까지) 로 동반 저하. cam3·cam4 만 정상.
- **원인**: [증거] 독립 구독자(`rate_probe.py`)는 같은 시각 6토픽 모두 정상 수신 → 발행 자체는 살아있음. 즉 SIGKILL 로 정리 없이 사라진 리더의 FastDDS 공유메모리(`/dev/shm/fastrtps_*`, 40→50개로 증가) 상태가 남아 해당 라이터의 전달·쓰기가 지연된 것. 퍼블리셔는 캡처 스레드에서 `grab → convert → publish` 를 직렬 수행(`usb_cam_publisher_node.cpp:168,192`)하므로 **쓰기 지연이 곧 캡처 FPS 저하**로 나타남.
- **해결**: 퍼블리셔 재기동으로 즉시 정상화(6/6 표시, 캡처 전 카메라 29.7 복귀). 운용 규칙: 뷰어는 **Ctrl+C / SIGTERM 으로 종료**(SIGKILL 금지), 부득이 SIGKILL 한 경우 퍼블리셔도 함께 재기동.
- **파일**: (코드 변경 없음) 관련: `src/Sensors/Camera/USB/usb_cam_publisher/src/usb_cam_publisher_node.cpp`
- **상태**: 원인·회복 절차 확인 완료. ⚠ 미해결: 퍼블리셔의 publish 블로킹이 캡처 루프를 멈추는 구조(캡처·발행 스레드 미분리)는 그대로 — 재발 시 같은 증상 가능.

> ⚠ **[2026-07-27 감사 부기 — 기전은 미검증 가설]** (원문 무변경)
> 위 "원인" 절의 "SIGKILL 로 사라진 리더의 FastDDS 공유메모리 상태가 남아 해당 라이터의 전달·쓰기가 지연된 것" 은 **"…지연됐을 가능성이 크다(미검증 가설)"** 로 읽어야 한다. 제시된 근거는 (a) 독립 구독자 정상 수신 (b) `/dev/shm/fastrtps_*` 40→50 개 증가 두 정황뿐이고, 인과를 확인한 재현 시험이 없다. 실제 해결도 원인 제거가 아닌 **퍼블리셔 재기동**이었고(위 "해결" 절), 같은 entry 의 "상태" 절도 구조적 원인이 남아 있음을 스스로 적고 있다.
> 따라서 "해결" 절의 **SIGKILL 금지 운용 규칙은 "기전 미확정 — 예방적 규칙"** 으로 병기한다(규칙 자체는 유지: 비용이 낮고 회복 절차가 확인돼 있음).
> **판정에 필요한 측정**: ① SIGTERM 종료 N회 vs SIGKILL 종료 N회 후 뷰어 콜백 수신 여부 대조 ② SIGKILL 후 잔존 `/dev/shm/fastrtps_*` **정리만으로** 회복하는지(퍼블리셔 재기동 없이) 확인.

### [Fix] vision_guard 기동 즉시 abort — opencv-python 이 Qt 플랫폼 플러그인 경로를 오염

- **문제**: `ros2 launch vision_guard vision_guard.launch.py` 실행 시 `qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in ".../cv2/qt/plugins" even though it was found` 후 프로세스 abort(exit -6). 6대 카메라 퍼블리셔는 정상(29.7fps)인데 뷰어만 뜨지 않음.
- **원인**: pip 설치본 `opencv-python 4.10.0`(`~/.local/lib/python3.10/site-packages/cv2`)이 **import 시점에 `QT_QPA_PLATFORM_PLUGIN_PATH` 를 자기 번들 경로로 덮어씀**(실측: import 전 `None` → import 후 `.../cv2/qt/plugins`). 그 번들 `libqxcb.so` 는 cv2 자체 Qt 에 링크돼 시스템 PyQt5(`/usr/lib/aarch64-linux-gnu/qt5/plugins/platforms`)와 호환되지 않아 플랫폼 플러그인 초기화 실패. 발현 경로: `app.py:17` 의 `from .ros_worker import ...` → `ros_worker.py:21` `import cv2` 가 `app.py:23` `QApplication()` 보다 먼저 실행. **외부 환경변수 지정으로는 못 고침** — cv2 가 import 시 다시 덮어쓰는 것을 실측 확인.
- **해결**: `app.py` import 직후·`QApplication` 생성 전에 `os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)` 추가(주석 5줄 + `import os` + pop 1줄). 재현 스크립트로 `platform = xcb` 정상 기동 선검증 후 적용.
- **파일**: `src/Sensors/Camera/USB/ui/vision_guard/vision_guard/app.py`
- **상태**: 완료 (colcon build 성공, 6대 뷰어 `6/6 cameras shown` 실측 확인)

### [Change] USB CCTV 카메라 로스터 6대로 확장 (cam5 = AY4EC5401BT)

- **문제**: 6대 장착 상태인데 roster 에 5대만 등록돼 뷰어에 5분할만 표시.
- **원인**: `config/camera/camera_common.yaml` 로스터 미갱신 — 6번째 시리얼 `AY4EC5401BT`(/dev/video2, usb 1-3.3) 누락.
- **해결**: cam5 항목 추가 + 버스 공유 주석(cam4·cam5 는 둘 다 Bus 001). 6대 동시 구동 실측: 전 카메라 **29.7fps, grab_failures=0** — 기존 문서의 "RGB 최대 4대" 제약(tr-orin-22 단일 USB2.0 컨트롤러 기준)은 이 Tegra 호스트에 미적용임을 재확인.
- **파일**: `config/camera/camera_common.yaml`
- **상태**: 완료

> ⚠ **[2026-07-27 감사 부기 — 6대 무손실 주장은 조건부]** (원문 무변경 · 로스터 값 무변경)
> 위 "해결" 절의 "6대 동시 구동 실측 29.7fps · grab_failures=0 ⇒ 'RGB 최대 4대' 제약 미적용 재확인" 은 다음 두 이유로 **조건부**로 읽어야 한다.
> - 이 entry 가 수정한 바로 그 파일이 상반된 문구를 **미정정 상태로 유지**한다: `config/camera/camera_common.yaml:22` "HARDWARE LIMIT: 단일 USB 2.0 컨트롤러라 RGB 최대 4대", `:23` "이 호스트에 실제 연결된 Gemini E **4대**" — 실제 로스터는 `:26-38` 의 cam0~cam5 **6대**. (어느 쪽이 옳은지는 여기서 판정하지 않는다. 값·주석은 해당 파일 담당 범위.)
> - 같은 파일 `:39-40` 은 "**5대** 실측 검증", `:41-42` 는 "cam4·cam5 는 둘 다 Bus 001 공유이므로 **6대 동시 구동 시 이 두 대의 FPS/grab 실패를 우선 관찰할 것**" 이라 적어 6대 조건을 **열린 관찰 대상**으로 남겨둔다.
> - 또 본 entry 의 6대 측정에는 **조건이 기재돼 있지 않다**(해상도·픽셀포맷·측정 지속시간·동시 뷰어 유무).
> **판정에 필요한 측정**: 6대 동시 구동을 해상도·픽셀포맷(`camera_common.yaml:14-17` 기준)·지속시간을 명기해 재측정하고, cam4/cam5(Bus 001 공유)의 FPS·`grab_failures` 를 별도로 기록.

### [Fix] vision_guard(USB_CCTV 뷰어) 메모리 누수 → OOM kill (프레임별 queued signal 무한 적재)

- **문제**: CCTV 5-카메라 내구 테스트 중 GUI `vision_guard` 가 시작 ~1시간 만에 강제 종료(exit code -9=SIGKILL). 동시에 20:32~20:49 5대 publisher FPS 가 0.5~28 로 요동. `journalctl -k`: `20:49:59 Out of memory: Killed process 1195045 (vision_guard) total-vm:24.9GB anon-rss:11.2GB` — vision_guard 가 11.2GB 까지 성장해 OOM killer 가 kill, 그 메모리·스왑 압박 여파로 publisher 캡처 FPS 동반 하락(카메라/USB 결함 아님 — grab_failures=0·stall=0, GUI 사망 후 9시간+ 29.7 FPS 안정).
- **원인**: [실측·증거] `main_window.py:37` `frame_ready = pyqtSignal(str, object)` 를 ROS 스핀 스레드에서 프레임마다 emit(`ros_worker.py:102·125`), GUI 스레드 `_on_frame`(`main_window.py:189`)에 **cross-thread queued connection**(`main_window.py:154`)으로 연결. GUI 렌더(bgr_to_qimage copy+scale+setPixmap)가 유입률(5대×30=150fps, 각 ~2.7MB)을 못 따라가면 **Qt 이벤트 큐에 프레임이 무한 적재**(드롭·백프레셔 없음) → 11GB/1h → OOM. ROS 구독 QoS 는 KEEP_LAST depth=1 로 정상(ROS 큐 누수 아님). 원본 tr-orin-22 는 2대라 누수가 느려 미노출, 5대에서 발현.
- **해결**: 유입률과 렌더율 **분리**. `FrameSignals`(queued signal) → `LatestFrameStore`(스레드 안전 dict, `put`=카메라별 최신 프레임 덮어쓰기·`drain`=GUI가 당겨 비움)로 교체. ros_worker 는 `_store.put(topic, frame)`, GUI 는 `QTimer(30Hz)`로 `_pump` 드레인 렌더. 메모리 상한 = 카메라수×1프레임(구버전 무한 큐 제거). (main_window.py: 클래스 교체+QTimer+_pump, ros_worker.py: emit→put 2곳+docstring, app.py: wiring)
- **파일**: `src/Sensors/Camera/USB/ui/vision_guard/vision_guard/{main_window.py, ros_worker.py, app.py}` (원본 병기: `tr-orin-22:~/Project/Ford_CATL_AMR/src/Sensors/Camera/USB/ui/vision_guard/` 동일 3파일)
- **상태**: 양쪽 완료·검증. **tegra**: 빌드 클린·테스트 7 passed(flake8·pep257 포함)·GUI RSS **268.6MB 80초 완전 평탄(Δ=0)** 실측(구 11GB→OOM 대비 상한 고정)·5대 렌더·소크 무영향. **tr-orin-22(원본)**: 수정 3파일 rsync 전파·빌드 클린·테스트 7 passed(코드 tegra와 동일). ⚠ tr-orin-22 런타임 RSS 미실측(동일 코드라 동작 동일 판단). launch 의 카메라 하드코딩은 누수 무관이라 이번 범위 외.

---

## 2026-07-26

### [Fix] motor_control 리뷰 지적 4건 수정 (E-stop 안전 2 · 브링업 누수 1 · 테스트 레이스 1)

- **문제**: 이식된 `src/Actuators/motor_control/` 코드 리뷰([docs/code_review/motor_control/2026-07-26.md](../code_review/motor_control/2026-07-26.md), Verdict REQUEST CHANGES) High 1·Medium 3. ① `test_cold_bringup_allowed_with_permission` 이 이 Jetson(ARM)에서 8/8 결정적 실패(x86 원격은 통과). ② E-stop 중 조향축이 계속 지령받아 정지 상태에서 물리 스윙 가능. ③ 브링업 예외 시 CAN 버스·rclpy 컨텍스트 누수. ④ E-stop 중 도착한 cmd_vel 이 해제 직후 급발진.
- **원인**: ① `_tx_loop`(backend.py:258)이 생성하는 조향 write 를 tx 데몬 스레드 기동 전에 테스트가 단언 — 스케줄링 레이스(`test_backend.py:126`). ② `_tx_loop`(backend.py:257-259)가 조향 setpoint 를 `_estop` 무관하게 무조건 송신. ③ `main`(driver_node.py:206)의 `node = MotorControlNode()` 가 try/finally 밖 + `__init__` 이 버스 개방(72) 후 `start()`(83) 예외 시 정리 없음. ④ `set_command`(backend.py:131)이 `_estop` 미확인.
- **해결**: ① 테스트를 tx 첫 write 폴링 대기(≤1s)로 견고화(+회귀 테스트 2건 추가). ② `_tx_loop` 에 `estopped` 캡처 후 E-stop 시 조향 setpoint 송신 `continue`(현 위치 hold, 설계문서 §5-4 step-cut 정렬). ③ `__init__` start() 를 try 로 감싸 실패 시 `backend.shutdown()`(버스 close) 재-raise + `main()` 노드 생성 실패 시 `rclpy.shutdown()`. ④ `set_command` 진입부 `if self._estop: return`. (backend.py +5줄, driver_node.py +8줄, test_backend.py +42줄)
- **파일**: `src/Actuators/motor_control/motor_control/backend.py`, `.../motor_control/driver_node.py`, `.../test/test_backend.py` (병기: `src/Actuators/motor_control/docs/code_review/motor_control/2026-07-26.md` findings 상태 [해결])
- **상태**: 로컬 완료 · 원본 반영 **부분(검증 보류)** — 로컬 **31 passed**(원본 29 + 신규 2), 레이스 테스트 8/8 PASS(Jetson), AST 정상. ⚠ 원본과 바이트 동일했던 코드에 **의도적 divergence**. 원본 `amap@amap-2:.../T-Driver-Analysis/src/Motor_Control/` 에 3파일 **rsync 전송 성공**(backend.py·driver_node.py·test_backend.py)했으나, 직후 amap-2 **SSH 도달 불가(오프라인)** 로 원격 pytest 검증·원격 doc 기록·git commit **미완**. 재개 시: (1) 원격 `python3 -m pytest test -q` 31 passed 확인, (2) 원격 docs/issues_and_fixes 동일 기록, (3) 협업 모드 확인 후 commit.

### [Diag] emulate 내구 중 Seer 52954(zeroing/재호밍 timeout) 1회 — zeroDI 하드웨어 아님, 기동 전환 트랜지언트로 추정

- **문제**: `emulate_endurance.py` 내구(2026-07-26 09:05~13:00, emulate firmware, engage180s/diseng5s) 중 Seer API 1050 알람에 **52954 "Motor calibration/zeroing timeout"(ERROR) 1회**(desc 09:29:19). 재호밍(원점복귀) 타임아웃.
- **원인**: [실측·증거 — ⚠ 2026-07-27 감사: 인과사슬 후반부는 **[가설]** 로 하향, 아래 부기 참조] appendix 002 매뉴얼의 일반원인(zeroDI 원점스위치 손상/오설치)은 **이 런 증거로 미지지**. 실제 인과사슬 = **첫 engage 전환(09:08) 순간 emulate 인수 전 수초 모터 통신 순단** → Seer가 모터침묵 감지(동시각 52111 motor timeout·52106 odo lost·54022 stuff, `seermon_endur.log` 09:08:42~43) → 자동 재호밍(54301 calibrating) 시작 → **emulate 경로가 실 원점센서(zeroDI) 피드백 미제공** → 시작+약20분 뒤 zeroing 카운트다운 만료로 52954(09:29). 09:29 시점 판다측 모터응답 정상(endur cyc7/8 급감0)=신규 통신갭 아님=09:08 zeroing의 종착점. 이후 59사이클 급감0·무재발. 근거모델: `docs/can_relay/field-record-orin-nx-2026-07-25.md:47,137`(모터응답/guard 상실=재호밍 방아쇠).
- **해결**: [미확정·검증대기] 코드 변경 없음. zeroDI 하드웨어 고장 가설 배제 위해 **실로봇 전원사이클 재현**(emulate 없이 실 Seer 재기동 → zeroing 정상완료=52954 미발생 확인) 예정. 정상완료 시 "emulate 기동 전환 트랜지언트"로 확정, 재발 시 실 zeroDI 점검. ⚠안전: Seer 전원복구=조향 물리 재호밍 동반(field-record §5-4), 가동범위 주변 클리어 후 수행.
- **파일**: (분석) `~/docking_reliability/seermon_endur.log`, `~/docking_reliability/endur_out.log`, `T-Robot_seer_gui/references/seer/robokit-api/appendix/002-alarm-code.md:183`; (재현도구) `~/Project/CAN-Relay/docking_field_kit/seer_powercycle_repro.py`(신규 작성·검증)
- **상태**: 진단 완료 · **재현검증 미실시(다음 세션 재개 필요)**. 내구는 76사이클 완주 PASS(모터급감 0, `endur_out.log` 13:00:12 종료요약). 전원사이클 재현 모니터 2회 기동(13:01·14:52, 각 10분 창)했으나 **양 창 모두 실 전원 OFF→ON 미수행**으로 zeroDI 하드웨어 가설 확정/배제 못함. **재개 절차**: (안전-조향 재호밍 물리이동 주변 클리어) → `python3 ~/Project/CAN-Relay/docking_field_kit/seer_powercycle_repro.py 192.168.44.82 600` 실행 후 Seer 전원 OFF→수초→ON → 판정(zeroing 완료=배제 / 52954 재발=하드웨어).

> ⚠ **[2026-07-27 감사 부기 — "emulate 경로가 실 원점센서(zeroDI) 피드백 미제공" 은 코드 근거 없음]** (원문 무변경 · 값/코드 무변경)
> 본 entry 는 제목이 "…**추정**", 상태가 "[미확정·검증대기]" 인데 원인 절만 `[실측·증거]` 라벨 + "**실제 인과사슬 =**" 단정형이었다. 인과사슬 중 **09:08 통신 순단 → Seer 재호밍 개시** 까지는 로그 인용이 있으나(`seermon_endur.log` 09:08:42~43), 그 뒤의 "**zeroDI 피드백 미제공**" 은 이를 뒷받침하는 로그·캡처 인용이 없고 펌웨어 코드는 오히려 반대 방향을 가리킨다.
> - 디지털 입력 `0x6000` 은 **모션 객체가 아니어서 freeze 대상이 아니다**(`Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h:139` "0x603F error·0x6000 digital in 은 폴되나 모션 아님 → **freeze 금지**", 모션객체 정의 `:170-172`, freeze 적용 조건 `:203`).
>   - ⚠ **정정 (2026-07-27)** — 위 「모션 객체가 아니어서」라는 **근거 서술은 부정확**하다(원문 보존. freeze 금지라는 운영 결정 자체를 뒤집는 것은 아니며, 값·코드 변경 없음).
>     `0x6000` 은 **배열 오브젝트**이고 실제 입력값은 **sub 1** 이다(sub 0 = 항목 수 = 2). sub 1 의 비트는 **bit0 = Servo Enable, bit1 = Positive Limit, bit2 = Alarm, bit3 = Negative Limit** [Handbook V7.0 Appendix I(Object Dictionary), printed page 197]. 그리고 조향축에는 리밋 스위치가 실재하며 호밍 방식은 **Home 1(음(−)의 리밋 트리거)** 이다(전 노드 `0x6098 = 1` 실기 파라미터 판독; Handbook 기본 RstMode 도 1 [§4.6, page 116]). 즉 `0x6000` sub 1 은 위치·속도는 아니어도 **호밍 진행/완료를 간접 노출**한다.
>     실측: 조향 노드만 `0x01 → 0x09`(bit3 = −Limit 셋) t=47.0249(node3)/47.0254(node4), `0x09 → 0x01` t=49.4223/49.4227, **구동 노드(1·2)는 180 s 전 구간 `0x01` 무변화** [`Log/homing_capture_220350.jsonl`]. 구동축은 호밍하지 않으므로 예상과 정합한다.
>     ⇒ freeze 제외의 근거는 「모션 객체가 아님」이 아니라 「**위치·속도 등 연속 모션량을 노출하지 않아 현 단계에서 은닉 필요성이 낮음**」으로 정정해 읽는다. 호밍 상태 은닉이 요구되는 시나리오(PC 가 조향을 리밋까지 몰 수 있는 경우 포함)가 생기면 재검토 대상이다.
> - emulate 중 Seer 의 SDO **읽기**(cmd `0x40`)는 캐시로 즉답되면서 **모터로도 forward**(`:286-288` `bus_fwd = 2`) 되어 캐시가 갱신되므로, 비-모션 객체의 실값은 (1폴 지연으로) Seer 에 전달되는 구조다. 단 캐시에 항목이 없으면 무응답이 될 수 있다는 한계는 별도로 기록돼 있다(`:182-194`, `:212`).
> ⇒ **정정**: "emulate 경로가 zeroing 을 완료시키지 못한 기전은 **미확정**" 으로 읽는다. 후보 —
> **(a)** SDO **쓰기**가 가짜 ack 후 모터로 전달되지 않아 호밍 지령이 모터에 미도달(`safety_seer_gate.h:289-291` `seer_fake_ack()` + `bus_fwd = -1` "모터로 안 보냄"), **(b)** `pc_authority` 중 모션객체(`0x6064` 등)를 engage 스냅샷(정지값)으로 고정해 위치가 불변으로 보임(`:179-180`, `:203-211`). 둘 다 **미검증**이다.
> **판정에 필요한 측정**: 재현 시 emulate 중 bus2(모터) 방향으로 나가는 호밍 관련 SDO **쓰기** 프레임 유무를 스니핑하고, 같은 창에서 `0x6000`(digital in) 응답값 변화와 `0x6064` 실위치 변화를 동시 기록. (기존 "실로봇 전원사이클 재현" 절차는 그대로 유효.)

---

## 2026-07-24

### [Fix] amap-2 현장 CAN 버스 단절오류 다발 — Seer 끝 종단저항(120Ω) 누락

- **문제**: 실 로봇 Foil_A082에서 CAN1(모터) 버스에러 다발(2026-07-23 23:13~24 01:05, 1h52m). Seer 알람 54022(Ack 250·Bit Recessive 183·Bit Dominant 104·Stuff 7 = 544회), 52111 모터 응답타임아웃(4개 동시 302회), 52106 odo lost 408회, 54301 재캘리 347회. 로봇 정지 중 발생, 수 초 내 자동복구 반복. Seer는 "check CAN router"만 지목, 원인 특정 못함. 판다측 모니터도 트래픽만 봐서 못 잡음.
- **원인**: **CAN 버스 종단이 모터(Tongyi) 끝 120Ω 하나뿐 = under-termination.** Seer 끝(DB9 2·7번=CAN_L/H) 종단 **없음**(실측 51.6kΩ 개방). 개방단 신호반사 → Bit/Ack/Stuff 에러. 판다는 온보드 종단이 없음(CAN0 pin4·5 / CAN2 pin23·24 실측 개방) — 문서 `Tools/docking_field_kit/PINMAP.md:50`의 "CAN2 온보드 120Ω 내장"은 오기였음(초기 혼선 원인).
- **해결**: **Seer 끝(DB9 2–7번)에 120Ω 종단저항 1개 추가** → 전체 60Ω(양단 120Ω) 정상화. PINMAP.md 종단 문구를 실측대로 정정(판다 종단 없음·Seer끝 120 필수·도킹시 스위칭종단 필요 명시).
- **파일**: `Tools/docking_field_kit/PINMAP.md`(정정), (하드웨어) Seer DB9 종단 120Ω 추가
- **상태**: 완료(판다측 검증) — 종단 60Ω 확인 후 라이브 트래픽 12s(33,278프레임·2,773fps)에서 판다 CAN 에러 전부 0(can_rx/send/fwd_errs Δ0, faults 0). **잔여 확증**: Seer 자체 로그 지속 무에러(수시간~밤샘 관찰) + per-bus 에러카운터(can_health) 위한 펌웨어 보강 예정.
- **[2026-07-27 종결 append]** 위 "잔여 확증" 항목을 닫는다. 그 후로도 간헐 재발하던 Seer CAN 알람의 원인은 **종단이 아니라 판다 부팅 기본 비트레이트 500 kbps** 였다(같은 날짜 상단 entry 참조). 250 kbps 정합만으로 `52106`·`52111`·`54022` 전량 소멸이 실증됐고 펌웨어 기본값을 정정했다. ⇒ **종단 문제는 종결. 이후 CAN 계열 알람에서 종단을 원인 후보로 재제기하지 않는다**(사용자 지시 2026-07-27). 먼저 판다 비트레이트·펌웨어 버전을 확인할 것.

> ⚠ **[2026-07-27 감사 부기 — 07-23 단절오류의 원인 귀속은 미판정]** (위 두 서술 모두 무변경 · 값/하드웨어 무변경)
> **양쪽 기록을 병기한다.**
> - *종단 쪽*: 위 "원인" 절은 2026-07-24 **실측**을 기록한다 — Seer 끝 DB9 2·7번 종단 없음(**51.6kΩ 개방**), 모터 끝 120Ω 하나뿐 = under-termination. `docs/adr/2026-07-24-canhealth-firmware.md:8` 은 "근본원인은 Seer 끝 120Ω 종단 누락이었고 종단 추가(60Ω)로 해소", 같은 문서 `:48` 은 "종단 수리 후 REC/TEC=0 → 종단 수리 하드웨어 레벨 확증" 이라 적는다. (해당 ADR 에는 `:12-19`·`:55` 로 2026-07-27 정정 부기가 이미 달려 있다.)
> - *비트레이트 쪽*: 위 종결 append 와 `docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md`.
> **미판정 사유**: 120Ω 종단은 **07-24 에 이미 장착**됐고(위 "해결"·"상태" 절), 07-27 검증(8초 29,625 프레임 · Seer `errors=[]`)은 **그 종단이 장착된 상태에서** 수행됐다. 두 변경(종단 추가 · 비트레이트 정합)을 **분리해 측정한 기록이 없다** — 07-27 ADR 에는 '종단/termination/120' 문자열이 0건(grep, 2026-07-27).
> ⇒ 실증된 것은 **"250 kbps 정합이 '호스트 미실행 시 잔여 알람'을 없앴다"** 까지다. **07-23 단절오류(1h52m, 54022 544회 등)의 원인 귀속(종단 vs 비트레이트, 또는 양자 복합)은 미판정.**
> **운용 지시의 유효 범위**: "종단을 원인 후보로 재제기하지 않는다"는 **원인 후보 확인 순서**(판다 비트레이트·펌웨어 버전을 **먼저** 확인)로 운용하며, **물리 종단 60Ω 상시 확인은 별개로 유지**한다(`Tools/docking_field_kit/PINMAP.md:62-71`: 판다는 온보드 종단 없음 · Seer 끝·모터 끝 각 120Ω 필요 · 도킹 intercept 시 스위칭 종단 별도 필요).
> **판정에 필요한 측정**: ① 250 kbps 정합 상태의 **현재 버스 종단 저항 실측**(60Ω 유지 여부) 기록 ② 가능하면 종단 정상·비트레이트 정합 상태에서 장시간 `can_health`(REC/TEC) + Seer 1050 알람 무에러 지속 확인.

---

## 2026-07-04

### [Fix] python 훅 전체가 한국어 Windows(cp949) 콘솔에서 UnicodeEncodeError 로 조용히 실패

- **문제**: `.claude/settings.json` 에 등록된 python reminder 훅들이 실제 런타임에서 출력 없이 실패 — 게이트 컨텍스트(user_instruction·debt·git_workflow 등)가 세션에 주입되지 않음. kuks_claude_agent_setup 업데이트(git_workflow v1.4.0) 설치 스모크 테스트 중 발견.
- **원인**: Windows 에서 stdout 이 파이프일 때 python 기본 인코딩이 cp949 — 훅 출력의 em-dash(U+2014) 등 cp949 비수록 문자가 `UnicodeEncodeError` 유발. 예: `docs/claude_guideline/git_workflow/hooks/git_workflow-reminder.py:128` 의 `print(DIRECTIVE ...)` (`[GIT-WORKFLOW SOP — 강제 게이트]` 헤더 18번째 문자). 구버전 훅에도 동일 문자 존재 → 신버전 회귀가 아닌 기존 잠재 버그. 검증: 기본 환경에서 user_instruction(exit=1)·debt(exit=1)·git_workflow(crash) 재현.
- **해결**: `.claude/settings.json` 최상위에 `"env": {"PYTHONUTF8": "1"}` 추가 (4줄 추가). 훅 파일은 저장소 원본과 동일하게 유지(diff 0) — 프로젝트 환경 레벨에서 UTF-8 모드 일괄 적용. 세션 재시작 후 발효.
- **파일**: `.claude/settings.json`
- **상태**: 완료 — 등록 훅 10종 전부 `PYTHONUTF8=1` 환경에서 exit=0 확인 (reminder 8종 + git_workflow track·stage-gate). 업스트림(kuks_claude_agent_setup) 훅에 `sys.stdout.reconfigure(encoding="utf-8")` 추가 또는 install.sh 의 settings env 등록 권고.
