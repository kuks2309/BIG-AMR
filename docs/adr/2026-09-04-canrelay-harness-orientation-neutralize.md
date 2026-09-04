# ADR 2026-09-04 — CAN relay 보드 하네스 방향 판정 무력화 (NC 고정)

- **Status**: Accepted (빌드 완료, 실기 플래시·검증 대기)
- **작성**: 2026-09-04 · 세션 67ed5a48
- **대상**: `Tools/Can_Relay/panda-firmware/board/boards/black.h` (git 미추적 파일 — 변경 내용은 본 ADR 과
  `docs/can_relay/debt-129-rehoming-cause-analysis-2026-09-04.md` §7 에 보존)
- **부채**: debt-130 (`docs/debt/registry.md`)

## Context

comma 블랙판다 펌웨어는 부팅 시 `harness_init()` 이 SBU1/SBU2(PC0/PC3) ADC 로 하네스 방향을 판정한다.
자작 보드(CAN RELAY R01/R02)에는 하네스가 없고 PC0 은 `CAN3_EN` 넷, PC3 은 미연결이라 판정이 부팅마다
NORMAL(1)/FLIPPED(2) 로 흔들린다. FLIPPED 이면
1. `black_init()` 이 `can_flip_buses(0,2)` 로 논리 bus0↔bus2 를 바꿔 emulate 응답이 모터측으로 나가고,
2. `set_intercept_relay()` 가 릴레이핀 PC10 을 `!intercept` 로 구동해 `set_safety_mode()` 의 push-pull
   제어와 반대로 움직인다(engage 시 릴레이 OFF, SILENT 복귀 시 릴레이 ON=절체 잔류).
2026-09-04 15:26 E1 실측: FLIPPED 부팅에서 engage 는 브리징 루프 폭주(node4 EMCY 0x8110 ≈1000 f/s)로
깨지고, SILENT 뒤 로봇이 Seer 와 분리된 채 남았다(52111 Motor[1][2][3][4]).

## Decision

`black_init()` 에서 `harness_init()` 호출을 제거하고 `car_harness_status = HARNESS_STATUS_NC` 로 고정한다.
FLIPPED 전용 `can_flip_buses(0,2)` 블록을 삭제하고 `black_harness_config.has_harness = false` 로 둔다.
릴레이(PC10)는 `set_safety_mode()` 의 push-pull 구동(SEER_GATE=HIGH 절체, SILENT=LOW 통과)만이 제어한다.
NC 에서 `set_intercept_relay()`·`harness_check_ignition()` 은 no-op/false 다.

## Consequences

- 릴레이·버스 매핑이 부팅과 무관하게 결정적이 된다(NORMAL 부팅과 동일 동작).
- `ignition_line` 이 항상 0 → heartbeat fail-safe 임계가 `HEARTBEAT_IGNITION_CNT_OFF`=2 s 로 고정된다.
  호스트 heartbeat 주기는 ROS2 0.2 s·Rig 0.4 s 라 여유 5~10배.
- `harness_init()` 의 1 s 부팅 지연·SBU 핀 MODE_INPUT 전환이 사라진다(PC0/PC3 은 analog 유지, 전기적으로 동일 hi-Z).
- `usb_comms.h` 0xe8 의 `set_intercept_relay()` 호출과 `main.c` SILENT 분기의 호출은 no-op 이 된다(코드는 유지).

## Rollback

- 코드: `black.h` 에서 `car_harness_status = HARNESS_STATUS_NC;` 를 `harness_init();` 로 되돌리고
  FLIPPED 분기 `if (car_harness_status == HARNESS_STATUS_FLIPPED) { can_flip_buses(0, 2); }` 와
  `.has_harness = true` 를 복원한 뒤 `scons -u -j4`.
- 실기: 직전 이미지 `Tools/Can_Relay/fw_backups/panda-903a9b3-pushpull-flipped_2026-09-04.bin.signed`
  (md5 `8aa53270cf61bda726efdf646e068d7a`, 31,184 B)를 `board/obj/panda.bin.signed` 에 복사 후
  `flash_dfu_direct.py` 로 DFU 재플래시. 단 그 이미지는 FLIPPED 부팅에서 본 ADR 의 문제를 그대로 가진다.

## Verification

1. 플래시 후 health `car_harness_status == 0`, `safety_mode == 0`.
2. SILENT idle 에서 양 버스 수동 캡처에 Seer 요청과 모터 응답이 함께 보인다(passthrough), Seer 52111 소멸.
3. take(4 s)→release 1사이클: engage 중 bus2 에 모터 응답만, bus0 에 Seer 요청만(루프 없음, EMCY 0);
   release 뒤 passthrough 복귀. 재호밍 여부는 debt-129 잔여(별도).
4. 위 1~3 을 판다 리셋 3회 반복해 부팅 무관성을 확인한다.
