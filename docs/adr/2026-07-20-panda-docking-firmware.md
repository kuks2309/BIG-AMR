# ADR 2026-07-20 — 블랙판다 도킹 릴레이 펌웨어 (RTR 패치 + 릴레이 분리 + Seer 게이트)

Status: Accepted (사용자 지시 2026-07-20 "설계완료후에 펌웨어 작성해서 테스트" + "나머지 진행")

## 배경 (Context)

블랙판다(STM32, `commaai/panda 26524538`)에 도킹용 릴레이 펌웨어를 구현한다. 설계는
[relay-separation-design.md](../can_relay/relay-separation-design.md) + [SW 구조](../sw_structure/panda-relay-firmware/2026-07-20.md).
목표: 평시 passthrough(Seer 직결), 도킹 시 intercept + Seer 게이트(쓰기차단·가짜ack) + PC 직접구동.

## 결정 (Decision)

3개 변경을 의존성 순서로 구현한다. 대상 저장소: amap-1 `~/T-Robotics/CAN_Relay/panda` (기존 07-18 테스트 패치 위).

### #1 RTR 지원 (선행 — 없으면 Node Guarding 깨짐)
- `board/can_definitions.h`: `CANPacket_t.reserved:1` → `rtr:1` (와이어 포맷 무변경 — 예약 비트 재사용)
- `board/drivers/bxcan.h` TX(:149): `TIR |= (to_send.rtr << 1)` (bxCAN RTR = TIR bit1)
- `board/drivers/bxcan.h` RX(:180): `to_push.rtr = (RIR >> 1) & 0x1U`
- `board/drivers/bxcan.h` fwd(:195): `to_send.rtr = to_push.rtr`
- ~~`python/__init__.py` pack/unpack~~ **보류(2026-07-20)**: guard RTR 은 도킹 릴레이 경로에서 Seer↔모터를
  **펌웨어 C 코드가 중계**(RX→fwd→TX)하므로 PC 가 RTR 을 송신할 일이 없음. python API 튜플 `(addr,_,dat,bus)`
  확장은 침습적이라 릴레이 경로 밖(PC 원발 RTR·모니터 정밀 디코드) 필요 시로 보류.

**빌드 검증 (2026-07-20)**: `scons -j4 board` PASS (`-Werror` 엄격), `board/obj/panda.bin.signed` 47440 bytes,
hash `a812afd9909468bc62656fa5f4da5e3132de3634`. 백업: `/tmp/{can_definitions.h,bxcan.h,pyinit}.bak`.

### #2 릴레이 분리 (relay ⊥ safety_mode)
- `board/main.c:396-397`: `heartbeat_disabled=true` + `set_intercept_relay(true)` 삭제 → 부팅 passthrough + hb fail-safe 복원
  - **[조건 누락 / 2026-07-27 보강]** "hb fail-safe 복원" 은 **무조건이 아니었다**. heartbeat 상실 경로가 릴레이를 되돌리는 것은
    **현재 safety_mode 가 SILENT 가 아닐 때** 에 한정됐다 — `Tools/Can_Relay/panda-firmware/board/main.c:248-250`
    `if (current_safety_mode != SAFETY_SILENT) { set_safety_mode(SAFETY_SILENT, 0U); }` 이고,
    릴레이 해제(`set_intercept_relay(false)`)는 **`SAFETY_SILENT` case 안에만** 있었다(`board/main.c:88-89`).
    그런데 본 ADR §#2 가 릴레이를 safety_mode 와 분리했으므로(`board/usb_comms.h:406-408` `case 0xe8: set_intercept_relay(...)` — **모드 가드 없음**),
    **이미 SILENT 인 채 `0xe8` 로 intercept 된 릴레이는 heartbeat 상실로 해제되지 않았고**,
    `pc_authority`(`board/usb_comms.h:410-412` `case 0xe9`) 도 해제되지 않았다.
    이 공백을 메우는 코드는 **2026-07-27 에야 추가**됐다 — `board/main.c:252-258`
    ("CAN-Relay fail-open: 이상 상태에서는 릴레이를 intercept 로 두지 않는다 … ADR: docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md"
    + `set_intercept_relay(false); pc_authority = false;`), 목적은 `docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md:71`
    "어떤 이상 상태에서도 릴레이가 intercept 로 걸린 채 남지 않고 항상 물리 통과로 복귀한다(fail-open)".
    ⇒ 본 줄은 **2026-07-27 보강 이전 기간에 대해서는 조건부 서술로 읽어야 한다.**
- `board/main.c` safety switch: 신규 `SAFETY_SEER_GATE` case (릴레이 미개입, can_silent=LIVE)
- `board/usb_comms.h`: `0xe8` RELAY_SET, `0xe9` AUTH_SET 추가
- SILENT/NOOUTPUT case 의 `set_intercept_relay(false)` 는 **유지**(fail-safe 비대칭)

### #C Seer 게이트
- `board/safety/safety_seer_gate.h` (신규): `seer_gate_fwd_hook` — pc_authority 시 Seer 쓰기(0x601~604, 0x23/2B/2F) drop + can_send 가짜 ack(0x580+N) + 읽기·guard 통과

## 구현·빌드 상태 (2026-07-20)

- **#1 RTR + #2 릴레이분리 + #C 게이트 3변경 전부 구현·컴파일 완료.**
  `scons -j4 board` PASS (`-Werror`), `board/obj/panda.bin.signed` **47672 bytes**, hash `1cd43c68a41c304801a278d0a017f7814ef79264`.
- 변경 파일(amap-1): `can_definitions.h`(rtr) · `bxcan.h`(rtr TX/RX/fwd) · `safety_declarations.h`(can_send proto) ·
  `safety/safety_seer_gate.h`(신규 게이트 훅) · `safety.h`(define·include·registry) · `main.c`(SEER_GATE case·init 강제제거) ·
  `usb_comms.h`(0xe8 RELAY_SET·0xe9 AUTH_SET).
- 빌드 함정 교훈: seer_gate include 를 `#ifdef CANFD` 밖(무조건 영역)에 둬야 STM32F4 빌드 포함됨.
- ⚠ **미검증(빌드는 통과, 동작 아님)**: 게이트 `can_send` 가짜ack 의 인터럽트 재진입 안전성 — PCAN 벤치 필수.
  - **[사후 상호참조 2026-07-27]** → 이 항목은 아래 **§검증 게이트 3(PCAN 벤치, ✅ 6/6 PASS 2026-07-20)** 에서
    "가짜ack `can_send` 인터럽트 재진입 안전성 **실기 확인**" 으로 기록됐다. 즉 본 줄의 "미검증" 은 **작성 시점 기준**이며 이후 갱신되지 않았다.
    (원문 무변경 — 이력 보존.)

## 검증 게이트 (PCAN 벤치 → 실차, 사용자 확정 순서)

1. **컴파일** — ✅ PASS (위)
2. **플래시 + USB 스모크** — ✅ PASS (2026-07-20). `panda.bin.signed` 플래시 성공, 재연결 OK.
   - 부팅 기본 safety_mode **0(SILENT)/passthrough** 확인 → #2 init 강제제거 실기 검증 (이전엔 17/intercept 강제).
   - `0xdc`→`SEER_GATE(30)` 모드 설정 sticks(레지스트리 OK) · `0xe9` AUTH_SET · `0xe8` RELAY_SET 전송 크래시 없음 · 원복 OK.
   - voltage 12052mV(12V 정상). 판다는 클린 상태(SILENT/passthrough)로 종료.
   - ⚠ 미검증: 게이트 실동작(가짜ack·쓰기차단·guard RTR 중계)은 CAN 트래픽 필요 → 3단계.
3. **PCAN 벤치** — `Tools/panda_bench/seer_gate_bench.py`. **✅ 6/6 PASS (2026-07-20)**:
   - ✅ T1 passthrough · ✅ **T2 Seer 쓰기 차단** · ✅ **T3 가짜 ack 합성** · ✅ T4 Seer 읽기 통과 ·
     ✅ **T5 guard RTR 통과(#1 RTR 패치 실증)** · ✅ T6 PC 직접구동.
   - **가짜ack `can_send` 인터럽트 재진입 안전성 실기 확인**(코드리뷰 결론 일치: 스톡 포워딩과 동일 패턴 + `global_critical_depth` 중첩안전).
   - 비트레이트: 실 Tongyi 250k (벤치도 250k 정합).
   - ⚠ **근본 함정(해결)**: 이 클론 보드(각인 `U3P-3.2`, 2024)는 **CAN2_H를 26핀 pin22가 아닌 pin23에 배선**(pin22 미사용/死핀).
     comma 표준 핀아웃(pin22=CAN2_H)대로 PCAN can1 CANH를 pin22에 연결해 **CANH 단선 → CAN2 전면 불통**이 장시간 지속.
     원인은 릴레이·트랜시버·펌웨어·종단 아님 — **핀맵 상이**. 사용자 통전+회로분석으로 규명, CANH를 pin23으로 이동 후 즉시 6/6 PASS.
     **교훈**: 클론 보드는 comma 표준 핀아웃을 신뢰 말고 실측 핀맵 확인(U9 CANH=pin23, CANL=pin24).
4. **실차** — 노드이동↔도킹↔반환, 저속·E-STOP 상비 (다음 단계)

## Rollback Plan (⟦CI:adr-fields⟧ — 비가역 펌웨어)

- **소스**: 모든 변경 전 `git -C panda stash` 또는 브랜치 격리. 문제 시 `git checkout -- <file>` 로 즉시 원복.
- **플래시**: 현재 동작 펌웨어(`board/obj/panda.bin.signed`, 07-18 검증본)를 **백업 보관** 후 신규 플래시.
  실패 시 `Panda().recover()` (DFU) 로 백업본 재플래시. paw 연결 시 확실.
- **하드웨어 fail-safe**: 최악의 경우 판다 무전원 → 물리 릴레이 OFF(passthrough) → Seer 직결 (기존 제어기로 복귀,
  판다 없이 동작) — 이 fail-safe 자체가 롤백 안전망.
- **플래시 승인**: 실제 플래시는 사용자 명시 승인 후에만 (컴파일까지는 무해, 플래시가 비가역 지점).

## Rejected

- 릴레이를 safety mode 에 계속 종속 | 평시 passthrough 구조적 불가 (설계 §1)
- 물리단위 USB 전송 | HAL 경계 오배치 (모터 교체 시 펌웨어 변경)
- 새 CAN 패킷 버전 도입(RTR 필드 신설) | 와이어 포맷 파괴 + 라이브러리 호환 손실 → 예약 비트 재사용 채택

## 제약 / Not-tested

- Confidence: high (모든 변경점 소스 실측 file:line 확보)
- Scope-risk: moderate (펌웨어 — 비가역, 단 하드웨어 fail-safe 안전망 有)
- Not-tested: PCAN 벤치 전 단계. 도킹 중 USB 경로 지터, heartbeat timeout 시 게이트 원복 미검증
  - **[미갱신 표시 / 문서 내 모순 2026-07-27]** 본 절의 "PCAN 벤치 **전 단계**" 는 같은 문서 **§검증 게이트 3
    ("PCAN 벤치 — ✅ 6/6 PASS (2026-07-20)", T1~T6 전항 PASS)** 와 **상충**한다.
    동일 패턴이 §구현·빌드 상태의 "⚠ 미검증 … 인터럽트 재진입 안전성" vs §검증 게이트 3 의 "실기 확인" 에도 있다.
    **어느 쪽이 최신인지 문서만으로는 확정 불가** — 갱신 누락으로 보이나 단정할 근거는 없다.
    ⇒ **미판정 모순으로 표시**한다. 판정에 필요한 것: PCAN 벤치 실행 로그/타임스탬프
    (`Tools/panda_bench/seer_gate_bench.py` 실행 산출물)와 본 절 작성 시각의 선후 확인.
    그때까지는 **§검증 게이트 기록(6/6 PASS)이 더 나중에 추가된 서술**로 읽되, 본 절 원문은 삭제하지 않는다.
  - **잔여 미검증(위 모순과 무관하게 그대로 유효)**: ① 도킹 중 USB 경로 지터,
    ② heartbeat timeout 시 게이트 원복 — ②는 §#2 의 조건 누락 주석(위) 참조:
    SILENT 상태에서 `0xe8` 로 걸린 릴레이·`pc_authority` 는 2026-07-27 `board/main.c:252-258` 추가 전까지 해제되지 않았다.
