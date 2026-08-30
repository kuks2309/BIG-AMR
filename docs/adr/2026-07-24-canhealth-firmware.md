# ADR 2026-07-24 — 판다 firmware에 per-bus CAN health(can_health) 추가

## 상태
채택(구현·검증 완료). amap-1 판다#1·amap-2 판다#2 플래시 완료.

## 맥락
2026-07-23~24 밤샘, amap-2 실 로봇(Foil_A082)에서 CAN 버스에러 다발(54022 Ack/Bit/Stuff, 4모터 동시 타임아웃).
근본원인은 **Seer 끝 120Ω 종단 누락(under-termination)** 이었고 종단 추가(60Ω)로 해소. 그러나 진단 과정에서
**판다측에는 per-bus 에러 카운터 가시성이 없어**(기존 firmware/lib에 `can_health` 부재, aggregate `can_rx_errs`만)
Seer가 잡은 에러를 판다가 못 잡는 한계가 드러남. → 판다를 Seer급 에러 검출기로 만들기 위해 per-bus 카운터 필요.

> **[2026-07-27 정정 — 위 "근본원인/해소" 서술의 유효 범위]** (원문 무변경, 이력 보존)
> 종단 누락 자체는 실재했다(Seer 끝 DB9 2·7번 **51.6kΩ 개방 실측** — `docs/issues_and_fixes/issues_and_fixes.md:82`).
> 그러나 **그 이후로도 간헐 재발한 Seer CAN 알람의 원인은 종단이 아니라 판다 부팅 기본 비트레이트 500 kbps** 였다:
> `docs/issues_and_fixes/issues_and_fixes.md:86` "250 kbps 정합만으로 52106·52111·54022 전량 소멸이 실증",
> 근거 코드 `docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md:29-33`(`board/drivers/can_common.h:164-166`
> `.can_speed = 5000U` = 500 kbps, 버스 실제 250 kbps), 실증 `동 ADR:46-48`(비트레이트만 정합 후 `errors=[]` 지속).
> ⇒ 본 문서의 "종단 추가(60Ω)로 해소" 는 **2026-07-23 배치 한정 서술**이며 CAN 에러 전반의 종결이 아니다.
> 이후 CAN 계열 알람을 종단 문제로 재귀속시키지 말 것 — 먼저 판다 비트레이트·펌웨어 버전을 확인한다
> (사용자 지시 2026-07-27, `issues_and_fixes.md:86`).

## 결정
STM32F413 bxCAN의 **ESR(Error Status Register)** 를 노출하는 control 요청 `0xc3`(can_health) 추가.

- `board/health.h`: `can_health_t`(BOFF/EPVF/EWGF/LEC/REC/TEC + raw ESR, 10바이트, packed), `CAN_HEALTH_PACKET_VERSION 1`.
- `board/usb_comms.h`: `get_can_health_pkt(dat, bus)` — `bus_config[bus].can_num_lookup`→`cans[n]->ESR` 디코드. `0xc3` 핸들러(`setup->b.wValue.w`=bus). H7(FDCAN)은 미사용이라 `#ifndef STM32H7` 가드(0 반환).
- `panda/python/__init__.py`: `CAN_HEALTH_STRUCT("<BBBBBBI")`, `can_health(bus)` 메서드.

ESR 비트: EWGF(0) EPVF(1) BOFF(2) LEC(6:4) REC(23:16) TEC(31:24).

> **[2026-07-27 정정 — 위 줄의 REC/TEC 라벨은 반대다]** (원문 무변경, 이력 보존)
> ST 벤더 CMSIS 디바이스 헤더(1차 source)가 정반대를 규정한다:
> `Tools/Can_Relay/panda-firmware/board/stm32fx/inc/stm32f413xx.h:2022` `#define CAN_ESR_TEC_Pos (16U)`
> (/*!< Least significant byte of the 9-bit Transmit Error Counter */),
> `:2025` `#define CAN_ESR_REC_Pos (24U)` (/*!< Receive Error Counter */).
> ⇒ **23:16 = TEC, 31:24 = REC** 이다. 본 ADR 서술은 REC↔TEC 가 뒤바뀌었다.
> 펌웨어 구현도 같은 뒤바뀜을 따른다(필드 이름만 뒤바뀜, 비트 오프셋 자체는 헤더와 일치):
> `board/health.h:35-36`(`receive_error_cnt // ESR REC[7:0] (bits 23:16)`, `transmit_error_cnt // (bits 31:24)`),
> `board/usb_comms.h:70-71`(`receive_error_cnt = (esr >> 16)`, `transmit_error_cnt = (esr >> 24)`).
> 같은 문서 §근거·검증(아래)의 실측도 이를 뒷받침한다 — "미연결 bus1로 송신→ACK에러 유발" 은 송신 전용 시나리오라
> CAN 규칙상 송신 에러 카운터만 증가하는데 기록은 "REC=128" 이다(= 실제로는 TEC=128).
> **판정 전 주의**: 정정 전까지 `can_health` 의 REC/TEC 판독으로 "수신측 문제/종단" 을 추정하지 말 것.
> **별건 등록 대상**: `health.h:35-36` / `usb_comms.h:70-71` 의 필드 라벨 뒤바뀜(값·비트 오프셋 변경은 본 감사 범위 밖 —
> 필드 이름을 바꾸면 `panda/python/__init__.py` 의 `CAN_HEALTH_STRUCT` 소비측과 함께 고쳐야 하므로 별도 작업으로 진행).

## 근거·검증
- amap-1(PCAN 벤치): 유휴=전부0. 미연결 bus1로 송신→ACK에러 유발 시 **error_passive=1, error_warning=1, LEC=3(ack), REC=128** 포착 → 실제 에러 추적 입증. LEC=3는 Seer 로그 "Acknowledgement error"와 동일 클래스.
- amap-2(실 로봇, 종단 수리 후): 라이브 3,444fps 하에서 양 버스 **REC/TEC=0, error 플래그 0** → 종단 수리 하드웨어 레벨 확증.
  - **[조건 누락 정정 2026-07-27]** 위 "확증" 은 무조건이 아니라 **호스트가 붙어 비트레이트를 250 kbps 로 고쳐 놓은 조건에서 확인**된 것이다.
    측정 도구 `Tools/docking_field_kit/amap2_canhealth.py:19-21` 이 `p.set_safety_mode(0, 0)` 직후
    `for b in (0, 2): p.set_can_speed_kbps(b, 250); p.set_can_enable(b, True)` 를 실행한 뒤 `:24` 에서 `can_health` 를 읽는다.
    판다 **부팅 기본값은 500 kbps** 이며(`docs/adr/2026-07-27-panda-boot-bitrate-and-failsafe.md:29-33`),
    같은 ADR `:39` "모든 호스트 도구가 제어권 획득 시퀀스에서 `set_can_speed_kbps(bus, 250)` 을 호출한다 …
    PC 소프트웨어가 붙어야만 버스가 성립하는 구조", `:87` 호스트 미실행 전원 사이클이 이번 사건의 재현 조건.
    ⇒ 표현을 **"종단 수리 하드웨어 레벨 확증" → "호스트 접속·250 kbps 설정 조건에서 확인"** 으로 읽을 것.
    호스트 미접속(판다 기본 500 kbps) 조건에서는 재현되지 않았다. 측정치·수치는 무변경.

## 기각안
- `health()` aggregate(`can_rx_errs`)만 사용 | per-bus·에러종류(LEC) 식별 불가, 수동 리스너에선 거의 안 오름 → 재발 진단 부적합.
- 판다 lib만 신규 버전으로 교체 | firmware 패킷버전 불일치 위험. 대신 현 firmware(26524538)에 최소 추가가 안전.

## 영향·주의
- Scope: control 요청 1개 추가(읽기 전용, 부작용 없음). 기존 health(0xd2) struct·버전 불변(HEALTH_PACKET_VERSION 7 유지).
- 재플래시 필요: 두 판다 모두 완료. udev 규칙이 bootstub(`ddee`) 미포함이면 플래시 불가 → amap-2에서 `idVendor=="bbaa"` 전 모드 0666 규칙으로 수정(교훈).
- Confidence: high. Not-tested: FDCAN(H7) 경로(미사용, 0 반환).
