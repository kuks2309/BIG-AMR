# ADR 2026-09-04 — 제어권 반환 시 펌웨어 핸드오버 복원 시퀀서

- **Status**: Accepted · 최종 이미지 md5 `bdac6012…`(32,280 B, 보드 이름 기능 동반) · 실기 검증 (a)(b)(c)(e)(f) PASS
- **작성**: 2026-09-04 · 세션 67ed5a48
- **대상**: `Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h`(추적), `board/usb_comms.h`(추적),
  `board/main.c`(미추적 — 변경 원문은 본 ADR §Design 에 보존)
- **선행**: ADR 2026-09-03-disengage-handover-restore(미구현), debt-129/130 해결(2026-09-04)

## Context

반환(`~/engage false` → `0xe8=0`·`0xe9=0`·SILENT)은 조향이 어디에 있든 그 자리에서 passthrough 로 넘긴다.
노드의 `backend.shutdown()` 은 구동 0 과 조향 목표 재송신 중단만 한다. 조향 90° 에서 반환하면 Seer 가
자기 목표(0°)로 되돌리는 동작이 Seer 제어로 일어나고, following error·재init 위험이 있다.
오늘 검증(분석 §9·§10)은 호스트 스크립트가 반환 전에 조향을 0° 로 되돌렸기 때문에 깨끗했다.
사용자 결정: 이 복원은 **펌웨어가** 소유한다 — 호스트가 죽어도 성립하고, 사용자는 반환만 요청하면 된다.

## Decision

펌웨어에 **핸드오버 복원 시퀀서**를 둔다(8 Hz `tick_handler`, `seer_homing_tick` 옆).

1. 트리거: `0xe8=0` 또는 `0xe9=0`(둘 다 `pc_authority` 가 켜져 있을 때), heartbeat 상실(fail-safe).
2. RESTORE: 구동륜 `0x60FF=0`(×3) → 조향 node3·4 에 `0x607A = seer_last_target[n]`(Seer 의 마지막 목표,
   engage 시 frozen pos 로 초기화) + `0x6040=0x3F`. 1 s 마다 재송신. 캐시 `0x6064`(Seer 폴 포워딩으로
   갱신)로 잔차 확인, |잔차| ≤ 5,734 counts(0.1°) 이면 도달. 8 s 타임아웃, 목표 미보유면 즉시 통과.
3. SETTLE 0.5 s 뒤 FINISH: `pc_authority=false`, frozen 해제, 전환 cover arm, fail-safe 발 트리거면
   `relay_off_latched`, 보류된 SILENT(`0xdc`) 또는 fail-safe·heartbeat 상실이면 `set_safety_mode(SILENT)`.
4. 시퀀서 진행 중에는 emulate 가 계속 Seer 를 가린다(`pc_authority` 유지), 릴레이는 절체 유지,
   USB `0xdc SILENT` 는 보류 플래그로 받는다. 호밍 진행 중이면 먼저 취소한다.
5. 진단: USB `0xec` → `[state, source, result, pending_silent, ticks, pc_authority]`.
6. 재engage(`0xe9=1`)가 시퀀서 진행 중에 오면 **복원을 끝까지 수행한 뒤** 권한을 유지한 채 끝낸다(보류 SILENT 폐기). 사용자 요구(21:1x): 반납은 복원 완료를 보고 한다.

호스트 변경 없음. 기존 순서(`0xe8=0 → 0xe9=0 → SILENT`, 또는 `0xe9=0 → 0xe8=0 → SILENT`) 그대로 동작하며
반환 완료는 최대 8.5 s 지연될 수 있다(health `safety_mode` 가 0 이 되면 완료).

## Design (main.c 변경 원문 — 미추적 파일, 재적용용)

### 1) `tick_handler()` — 8 Hz tick 에 시퀀서 추가
```c
    seer_homing_tick();
    seer_handover_tick();
```

### 2) heartbeat fail-safe 블록 — 변경 전
```c
          if ((current_safety_mode == SAFETY_SEER_GATE) && pc_authority) {
            seer_stop_drives();  // relay off 전 구동륜을 목표속도 0 으로 감속 정지
          }

          if (current_safety_mode != SAFETY_SILENT) {
            set_safety_mode(SAFETY_SILENT, 0U);
          }

          set_intercept_relay(false);
          pc_authority = false;
          relay_off_latched = true;  // 안전 off 래치 — 재engage 차단

          if (power_save_status != POWER_SAVE_STATUS_ENABLED) {
            set_power_save_state(POWER_SAVE_STATUS_ENABLED);
          }
```

### 2) heartbeat fail-safe 블록 — 변경 후
```c
          if ((current_safety_mode == SAFETY_SEER_GATE) && pc_authority) {
            // 구동 0 + 조향을 Seer 목표로 복원한 뒤 시퀀서가 SILENT·래치까지 처리한다
            seer_handover_request(SEER_HO_SRC_FAILSAFE);
          } else if (seer_handover_active()) {
            // 복원 진행 중(최대 8.5 s) — power-save 가 트랜시버를 끄므로 완료를 기다린다
          } else {
            if (current_safety_mode != SAFETY_SILENT) {
              set_safety_mode(SAFETY_SILENT, 0U);
            }

            set_intercept_relay(false);
            pc_authority = false;
            relay_off_latched = true;  // 안전 off 래치 — 재engage 차단

            if (power_save_status != POWER_SAVE_STATUS_ENABLED) {
              set_power_save_state(POWER_SAVE_STATUS_ENABLED);
            }
          }
```

추적 파일(`safety_seer_gate.h`·`usb_comms.h`)의 변경은 git diff 가 원문이다.

## Consequences

- 반환이 조향 위치와 무관하게 Seer 기대 상태(마지막 목표)에서 일어난다. 호스트 사망 시에도 동일.
- fail-safe 의 SILENT 전환이 최대 8.5 s 늦어진다. 그동안 구동륜은 즉시 0, 조향은 Seer 목표로 복귀 중.
- `0xe9=1` 재engage 가 시퀀서 진행 중에 오면 복원이 끝난 뒤 권한이 유지된다(조향은 Seer 목표 위치).

## Rollback

- 코드: 세 파일의 본 변경 revert(`git checkout -- safety_seer_gate.h usb_comms.h`, main.c 는 본 ADR §Design 역적용).
- 실기: `Tools/Can_Relay/fw_backups/panda-8dcca835-harness-nc_2026-09-04.bin.signed`(본 변경 직전 이미지, 31,172 B, md5 `1f9fe50b348c346d3925818e725ace65`)를 `board/obj/panda.bin.signed` 로 복사 후 `python3 Tools/Can_Relay/flash_dfu_direct.py` 로 DFU 재플래시. 이 이미지는 하네스 NC 고정까지 포함한다(복원 시퀀서만 제거).

### Rollback 드릴 (2026-09-04 18:4x 실기 검증)
1. 최종 이미지를 `fw_backups/panda-0eee6d66-handover-restore_2026-09-04.bin.signed` 로 백업(md5 `0eee6d66…`).
2. 롤백 이미지(md5 `1f9fe50b…`)를 `board/obj/panda.bin.signed` 로 복사 → `flash_dfu_direct.py` → 서명 검증 OK → 부팅 harness=0·safety=0, passthrough 요청·응답 정상, Seer 오류 0, `0xec` 미지원(빈 응답)으로 구버전 확인.
3. 최종 이미지 복사 → 재플래시 → 서명 검증 OK → `0xec` 응답 복귀, passthrough 정상, hold 1사이클 PASS.
⇒ 롤백·복귀 모두 약 1분 안에 성립. 현재 보드 = 최종 이미지.

## Verification (2026-09-04 실측)

1. 빌드(-Werror) PASS — 31,764 B, md5 `639b4654a7b25346f4b90a21e9746e71`, 4e002c DFU 플래시 서명 검증 OK.
2. 노드 경로: engage → 조향 +30°(m3/m4 1,720,335/1,720,332 counts) → `~/engage false` → 0xec: RESTORE(src=1, SILENT 보류) → 2.0 s 도달(res=1) → SETTLE → IDLE·auth 0·safety 0. 수동 판독 조향 raw 7,871,817/7,840,091 = 홈 +0.000°. Seer 알람 0·재호밍 0.
3. fail-safe 경로: Rig engage → 조향 변위(node4 +4.8° 확인) → heartbeat 중단, release 미호출 → 1.2 s 뒤 시퀀서 요청(src=2) → 1.4 s 도달 → SETTLE → SILENT·auth 0. 조향 홈 +0.000°. Seer 알람 0.
4. 회귀: hold 4 s 10사이클 10/10 PASS(재init 0·EMCY 0·알람 0, 매 사이클 passthrough 복귀).
5. 재engage 의미 변경(21:1x): 복원 중 재engage 는 중단이 아니라 완료 후 권한 유지. 중단 시험은 사용자 지적으로 철회(`docs/claude-mistake/2026-09-04-001`).
6. 회귀 3사이클 3/3 PASS(최종 이미지).
7. 최종 이미지(bdac6012…): 조향 +30° 반환 복원 1.1 s 도달·홈 +0.000°, hold 3/3 PASS.
