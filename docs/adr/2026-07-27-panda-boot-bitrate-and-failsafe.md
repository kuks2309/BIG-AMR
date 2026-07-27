# ADR 2026-07-27 — 판다 릴레이 부팅 기본 비트레이트 정정 + 이상상태 릴레이 강제 해제 + freeze 집합 실측 정정

Status: Proposed (사용자 지시 sess:56a709a5 2026-07-27: "펌웨어 수정(근본 해결)" · "모든 이상상태가 되면 relay 를 연결하면 안됨" · "부채0로 진행할 것" · "기술 부채가 있는 제안은 절대 금지")

## Context (배경) — 관측과 근본 원인

### 증상 (실측)

로봇 전원 인가 후 **호스트 소프트웨어를 하나도 실행하지 않은 상태**에서 Seer 알람이 지속 발생했다(API 1050 폴링, 읽기 전용):

| 레벨 | 코드 | 내용 |
| --- | --- | --- |
| errors | 52106 | `odo data lost` |
| errors | 52111 | `motor driver connection error` |
| warnings | 54022 | `CAN1 new error:0x40, count:136, Bit Recessive error` — **10 초마다 타임스탬프 갱신(진행 중)** |
| warnings | 54301 | `Motor is calibrating` |

### 근본 원인 (코드 근거)

전원 인가 시 판다가 하는 일이 세 가지 겹친다:

1. **릴레이가 버스를 물리적으로 연결한다** — `board/drivers/harness.h:91`
   ```c
   // keep busses connected by default
   set_intercept_relay(false);
   ```
   health 실측 `car_harness_status=1`(HARNESS_STATUS_NORMAL) 로 하네스 감지 확인. 즉 **Seer↔모터는 하드웨어로 직결**이며 펌웨어 포워딩은 관여하지 않는다. (관측 뒷받침: 동일 프레임이 bus0/bus2 에 같은 카운트로 잡힘 — `0x603`: 2615/2615.)
2. **판다 트랜시버가 그 버스에 live 로 붙는다** — `board/main.c:405-406` `can_silent = ALL_CAN_LIVE; can_init_all();` + 메인 루프 매 회 `current_board->enable_can_transceivers(true)`.
3. **그 CAN 주변장치가 500 kbps 로 초기화된다** — `board/drivers/can_common.h:164-166`
   ```c
   { .bus_lookup = 0U, ..., .can_speed = 5000U, ... },   // 5000U = 500 kbps
   ```
   단위 확정: `usb_comms.h:322` 가 `wIndex` 를 그대로 `can_speed` 에 저장하고, `panda/python/__init__.py:550` 이 `int(speed*10)` 을 보낸다 ⇒ 5000U = 500 kbps. **버스 실제 속도는 250 kbps.**

⇒ **250 kbps 버스에 500 kbps 로 설정된 live CAN 노드가 물리 직결로 붙어 있다.** 이 노드는 모든 프레임을 오독해 에러 프레임(dominant 6 비트)을 방출하고 버스를 파괴한다. Seer 가 보고한 `Bit Recessive error` 누적 + 모터 통신 상실이 그 결과다.

### 왜 지금까지 드러나지 않았나

모든 호스트 도구가 제어권 획득 시퀀스에서 `set_can_speed_kbps(bus, 250)` 을 호출한다(`docking_drive.py:75-76`, `Tool/amr_test_gui/amr_test_gui/panda_can_bus.py:_take`). 즉 **PC 소프트웨어가 붙어야만 버스가 성립하는 구조**였고, 로봇 단독 전원 인가로는 정상 동작할 수 없었다.

### 검증 (제안 전 실증)

비트레이트만 정합시키고(`set_can_speed_kbps(0,250)`·`(2,250)`) 나머지는 일절 건드리지 않은 상태 — safety_mode 0 유지, 릴레이 불변, `pc_authority` 미설정, 모터 지령 0 건:

```
[t+18s] errors=[]  54022=
[t+24s] errors=[]  54022=
[t+30s] errors=[]  54022=
```

**Seer 알람 전량 소멸.** 가설이 실증됐다. 단 이 설정은 판다 RAM 상태라 전원 재인가 시 500 kbps 로 되돌아간다 → 펌웨어 기본값 수정이 필요한 이유.

### freeze 집합 불일치 (같은 플래시에서 함께 해소)

`safety_seer_gate.h:84` 의 모션 노출 객체 집합이 운영 기록과 달랐다. **Seer 의 실제 폴 집합을 12 초 스니핑으로 실측**해 확정했다:

| index | 12 초 폴 횟수 | 모션 노출 | 소스 포함? |
| --- | --- | --- | --- |
| `0x6064` 위치 | 2718~2920 (노드별) | 예 | 예 |
| `0x6041` statusword | node3/4 300여, node1/2 66 | 예 | **아니오 (누락)** |
| `0x6078` 전류 | 66 | 예 | 예 |
| `0x606C` 실속도 | **0 — 폴하지 않음** | 예 | 예 (죽은 분기) |
| `0x603F` error code | 68 | 아니오(실 고장은 보여야 함) | 아니오 |
| `0x6000` digital in | 66~68 | 아니오 | 아니오 |

⇒ 소스는 `0x6041` 을 빠뜨렸다. 이대로 PC 가 구동하면 Seer 가 **실제 statusword 변화를 보게 된다**. 운영 기록(메모리 `biguamr-motor-node4-sign-crab`)의 `{0x6064, 0x6078, 0x6041}` 이 옳았다.

## Decision (결정)

1. **부팅 기본 비트레이트 250 kbps** — `board/drivers/can_common.h` `bus_config[]` 의 bus0·bus1·bus2 `can_speed` 를 `5000U` → `2500U`. bus1 은 본 배선에서 미사용이나 기본값 일관성을 위해 함께 맞추고 주석으로 명시한다.
2. **이상상태에서 릴레이 연결 금지** (사용자 요구) — heartbeat 상실 처리(`board/main.c` 의 `set_safety_mode(SAFETY_SILENT, 0U)` 블록)에 `set_intercept_relay(false)` + `pc_authority = false` 를 추가한다. 어떤 이상 상태에서도 릴레이가 intercept 로 걸린 채 남지 않고 **항상 물리 통과로 복귀**한다(fail-open).
3. **freeze 집합 실측 정정** — `seer_is_motion_obj()` 에 `0x6041` 을 추가한다. `0x606C` 는 현재 Seer 가 폴하지 않음이 실측됐으나 모션 노출 객체가 맞으므로 유지하고, 폴 미관측 사실을 주석에 근거와 함께 남긴다.
4. **펌웨어 소스를 git 에 커밋** — `board/safety/safety_seer_gate.h` 등 현재 미추적(`??`) 파일을 추적으로 전환한다. 플래시된 바이너리의 소스가 버전관리 밖에 있는 상태를 끝낸다(이번 세션에 실제로 "소스가 git 에 없다"는 혼란을 유발했다).
5. **잘못된 문서 서술 정정** — "heartbeat 소실 시 판다가 fail-safe passthrough 로 복귀" 라는 서술은 사실과 다르다. 실제 코드는 `SAFETY_SILENT` 로 되돌린다. 다만 **릴레이가 물리 통과이므로 버스 자체는 유지**된다는 점이 본 조사로 밝혀졌다. 이 서술이 들어간 `Tool/amr_test_gui/amr_test_gui/panda_can_bus.py` docstring 과 `docs/adr/2026-07-27-amr-test-gui.md` 를 정정한다.

## Safety (안전)

- 본 변경은 **모터 지령을 생성하지 않는다.** 비트레이트·릴레이 해제·응답 치환만 다룬다.
- 변경 방향은 전부 **fail-open**(버스 유지 · intercept 해제)이다. 어떤 실패 경로에서도 Seer 가 모터를 잃지 않는 쪽으로만 움직인다.
- 플래시 중에는 판다가 리셋되며 그 동안 버스에서 이탈한다. **로봇 정지 상태에서 수행**하고, 플래시 후 전원 사이클로 검증한다.
- `ModemManager` 정지 필요(LIBUSB_BUSY 회피).

## Verification (검증 — 기록 전 필수)

1. 빌드 0 error.
2. 플래시 후 `get_version()` 이 새 빌드로 바뀐 것 확인.
3. **호스트 소프트웨어를 하나도 실행하지 않은 채 전원 사이클** → Seer 1050 폴링으로 `errors=[]` 및 `54022` 미갱신을 60 초 이상 확인. (이번 사건의 재현 조건 그대로.)
4. `health()` 에서 `car_harness_status=1`, `fault_status=0`, `rx_errs=0` 확인.
5. freeze 정정 검증: 제어권 획득 후 저속 구동 중 Seer 알람 0 확인(검증 계단 ③ 시점에 수행).

## Consequences (결과)

- (+) 로봇이 **PC 없이 단독으로 정상 동작**한다. 현재는 PC 소프트웨어가 붙어야만 버스가 성립한다.
- (+) 이상 상태에서 릴레이가 intercept 로 남지 않는다(사용자 요구 충족).
- (+) 플래시되는 펌웨어의 소스가 git 에 남아 다음 세션이 추적 가능하다.
- (−) 비트레이트가 250 kbps 로 고정되므로 다른 속도의 버스에 이 판다를 쓰려면 호스트가 명시 설정해야 한다(기존과 동일하게 `set_can_speed_kbps` 로 가능).
- (−) 플래시는 되돌림 비가역 — 아래 롤백 계획으로 완화.

## Rollback (롤백)

- **바이너리 롤백**: 플래시 전 현재 바이너리를 백업하고(`panda.bin.signed` + 기존 `panda.bin.signed.bak_0724`·`.bak_pre_emulate`), 문제 시 `flash_panda.py` 로 백업본을 재기록한다.
- **소스 롤백**: 본 변경은 3 파일의 소수 라인 수정이다 — `can_common.h` 의 `can_speed` 3 줄, `main.c` 의 2 줄 추가, `safety_seer_gate.h` 의 조건 1 줄. git 커밋 후이므로 `git revert` 로 정확히 되돌릴 수 있다.
- **런타임 우회**: 펌웨어를 되돌리지 않고도 호스트에서 `set_can_speed_kbps(bus, <원하는 값>)` 로 언제든 덮어쓸 수 있다(기본값만 바뀌는 변경이므로).
- **복구 실패 대비**: 판다는 DFU 모드 복구 경로(`recover.sh`)를 보유한다.
