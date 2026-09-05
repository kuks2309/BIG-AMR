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
   보류된 SILENT(`0xdc`) 또는 fail-safe·heartbeat 상실이면 `set_safety_mode(SILENT)`. (`relay_off_latched` 는 읽는 곳이 없어 09-05 에 제거.)
4. 시퀀서 진행 중에는 emulate 가 계속 Seer 를 가린다(`pc_authority` 유지), 릴레이는 절체 유지,
   USB `0xdc SILENT` 는 보류 플래그로 받는다. 호밍 진행 중이면 먼저 취소한다.
5. 진단: USB `0xec` → `[state, source, result, pending_silent, ticks, pc_authority]`.
6. **복원은 어떤 경우에도 끝까지 수행한다(사용자 요구: 반환 = 조향 복원 완료 → 제어권 해제).** 진행 중 들어온 요청은 **마지막 것이 이긴다**: 마지막이 반환(0xe8=0/0xe9=0)이면 완료 시 권한 해제·보류 SILENT 적용, 마지막이 재engage(0xe9=1)면 완료 시 권한 유지(출처 host/failsafe 무관, SILENT 폐기). 재engage 가 대기 중일 때는 Seer 목표 재송신을 멈춘다(호스트가 축을 쥠). 2026-09-05 09:1x 수정(md5 `218cfc53`).

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
          relay_off_latched = true;  // (09-05 제거 — 읽는 곳 없음)

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

            if (power_save_status != POWER_SAVE_STATUS_ENABLED) {
              set_power_save_state(POWER_SAVE_STATUS_ENABLED);
            }
          }
```

추적 파일(`safety_seer_gate.h`·`usb_comms.h`)의 변경은 git diff 가 원문이다.

## Consequences

- 반환이 조향 위치와 무관하게 Seer 기대 상태(마지막 목표)에서 일어난다. 호스트 사망 시에도 동일.
- fail-safe 의 SILENT 전환이 최대 8.5 s 늦어진다. 그동안 구동륜은 즉시 0, 조향은 Seer 목표로 복귀 중.
- `0xe9=1` 재engage 가 시퀀서 진행 중에 오면 복원이 끝난 뒤 권한이 유지된다. 그 뒤 다시 반환이 오면 복원 완료 후 해제된다(플래그 잔류 없음).

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

### 2026-09-05 재engage 의미 정정·검증 (펌웨어 md5 `218cfc53`)
사용자 지적: "반환 시 스티어링 복원 후 제어권 해제 순서로 가야 한다." 09-04 구현은 반환→복원 중 재engage→다시 반환 순서에서 재engage 플래그가 남아 완료 시 권한을 유지할 수 있었다(`docs/claude-mistake/2026-09-05-001`). 수정: request() 가 진행 중 재요청 시 재engage 플래그를 지우고(최신 요청 우선), finish() 는 출처 무관하게 대기 중 재engage 를 존중하며, 재engage 대기 중엔 목표 재송신을 멈춘다.
검증(직접 USB, 0xec 20~100 ms 폴 + 엔코더 10 Hz + 반환 뒤 Seer API):
| 순서 | 결과 |
|---|---|
| 90° 반환(재engage 없음) | RESTORE 3.4 s 도달(두 축 ≤0.1°) → SETTLE → IDLE·auth 0·safety 0. node4 첫 지령 유실을 1 s 재송신이 회복 |
| 90° 반환 → +0.25 s 0xe9=1 | 복원 완료(2.45 s) → IDLE·auth 1·safety 30(권한 유지), 엔코더 0.0°; 이후 정상 반환 → auth 0 |
| 90° 반환 → +0.25 s set_safety_mode(30)만 | 복원 완료 → auth 0·safety 0(재engage 아님) |
| 90° 반환 → +0.2 s 재engage → +0.4 s 다시 반환 | 복원 완료 후 auth 0·safety 0, Seer 조향 0.0 rad |
| 90° heartbeat 중단(fail-safe src=2) → RESTORE 감지 즉시 재engage+심박 | 복원 완료(3.2 s) → IDLE·auth 1·safety 30; 정상 반환 뒤 Seer 0.0 rad |
| hold 회귀 3사이클 | 3/3 PASS |
측정 주의: 시험 스크립트가 USB 수신 백로그를 비우지 않고 SDO 를 읽으면 옛 프레임을 집어 엉뚱한 각도를 보고한다(09-05 "82°/28°" 오보고, `docs/claude-mistake/2026-09-05-002`). 반환 뒤 최종 판정은 Seer API `steer_angles` 로 한다.

### 2026-09-05 09:3x 추가 — 0xdc 경로 보강 (펌웨어 md5 `6ffe710d…`)
15인 검토 쟁점(#2 GUI release 경로가 0xE8/0xE9 단계를 건너뛰고 SILENT 만 보낼 수 있음, #6 0xdc=30 이 보류 SILENT 를 안 지움)에 대한 펌웨어 측 대응:
- `0xdc SILENT` 가 pc_authority 중에 **0xe8/0xe9 없이** 오면 시퀀서를 요청하고 SILENT 를 보류한다 — 어떤 호스트 순서로 반환해도 "복원 완료 → 해제" 가 지켜진다.
- `0xdc` 라이브 모드(예: 30) 가 시퀀서 진행 중에 오면 보류 SILENT 를 지운다(재engage 시작).
검증: 30° 에서 `0xdc 0` 만 전송 → RESTORE 1.4 s 도달 → IDLE·auth 0·safety 0, Seer 0.0 rad; hold 회귀 3/3 PASS.

### 2026-09-05 결정 — 소프트 E-stop 래치 중 반환 (15인 검토 #17)
호스트 소프트 E-stop 이 걸린 상태에서 `~/engage false` 를 부르면 펌웨어 복원이 조향을 Seer 마지막 목표로 움직인 뒤 반환한다.
**현행 유지**(사용자 결정 2026-09-05). E-stop 은 호스트 지령 차단이 목적이고, 복원 이동은 반환 직후 Seer 가 명령할 목표로의 귀환이다. 반환을 거부하면 로봇이 호스트 권한에 묶인 채 남는다.

### 2026-09-05 내구 — 최종 이미지 c04e7b07
시퀀서·보드 이름 검증을 포함한 최종 이미지로 take 4 s→release 100사이클 **100/100 PASS**(재init 0·EMCY 0·알람 0·매 사이클 passthrough 복귀). 상세 `Tools/docking_field_kit/docs/2026-09-05-endurance-and-supervisor-e2e.md`.
