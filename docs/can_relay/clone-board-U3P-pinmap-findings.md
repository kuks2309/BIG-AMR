# 클론 보드(U3P-3.2) CAN 핀맵 통전 조사 — 2026-07-20 (최종 확정판)

> 실물 클론 블랙판다(각인 `U3P-3.2`, 2024)는 **comma 표준 핀아웃과 다름.** 통전(멀티미터) 실측 기록.
> **최종 결론: 도킹 릴레이 벤치의 CAN2 장시간 불통은 = 배선 오류(핀맵 상이).** 펌웨어·릴레이·트랜시버·종단 모두 정상이었고,
> comma 표준 핀(pin22=CAN2_H)을 믿고 PCAN can1을 pin22(死핀)에 연결한 것이 원인. CANH를 pin23으로 옮기니 즉시 전항 PASS.

## 1. 확정 핀맵 (통전 ✅ — 실측 최종)

| 신호 | 26핀 커넥터 | 판다 칩 | 비고 |
| --- | --- | --- | --- |
| **CAN2_H** | **pin23** | U9 CANH(pin7) | ⚠ comma 표준(pin22) **아님** |
| **CAN2_L** | **pin24** | U9 CANL(pin6) | |
| (미사용) | **pin22** | — | **死핀** (아무 회로 미연결) — 여기 연결이 오류였음 |
| **CAN0_H** | **pin4** | U11 CANH(pin7) | ✅ 확정 |
| **CAN0_L** | **pin5·pin6** | U11 CANL(pin6) | pin5=pin6=U11 CANL 동일넷 |

## 2. 릴레이 (Panasonic TX2, 2 Form C) 통전

- **극1 COM = pin4 (CAN0_H)**, **극2 COM = pin24 (CAN2_L)**
- **미전원(passthrough/NC) 시 연결**: **pin4 ↔ pin23** (H), **pin5 ↔ pin24** (L)
  → 릴레이 off 시 CAN0↔CAN2 브릿지 = 올바른 passthrough 배선.
- ✅ **fail-safe passthrough 실측 확인 (2026-07-20)**: 판다 **미전원** + PCAN 올바른 연결에서
  **can0↔can1 양방향 통신 성공** (can1 berr tx0 rx0 클린).
  ⚠ 판다 **켜진 SILENT 상태에선 트랜시버 간섭으로 passthrough 브릿지 불통** — 그러나 fail-safe 시나리오는
  판다 死 상태이므로 무관(미전원 시 정상 동작이 핵심).
  - > **⚠ 2026-07-27 반증 — 위 "켜진 SILENT 상태 불통"은 원인 진단이 틀렸고 현상도 재현되지 않는다.** (원문은 이력 보존을 위해 유지)
    > **(1) 전원 인가 SILENT 판다로 passthrough 가 정상 동작한다** — `docs/can_relay/field-record-orin-nx-2026-07-25.md:19-20` "판다 safety_mode 0 = SILENT/passthrough. Seer↔모터 하드웨어 중계 상시 가동. 라이브 트래픽 ~3200fps … **bus0·bus2 per-bus 에러 0, esr=0x0**(수시간 무재발)".
    > **(2) 원인은 "트랜시버 간섭"이 아니라 비트레이트 불일치였다** — `docs/issues_and_fixes/issues_and_fixes.md:11` "`board/drivers/can_common.h:164-166` `.can_speed = 5000U` = **500 kbps**(버스는 250 kbps) ⇒ 250k 버스에 500k 로 붙은 live 노드가 전 프레임을 오독해 에러 프레임을 방출, 버스 파괴". 250 kbps 정정 후 "Seer `errors=[]` 21초+ 유지 · `rx_errs=0 faults=0`"(동 줄). 소스에도 반영됨 — `Tools/Can_Relay/panda-firmware/board/drivers/can_common.h:162-171` 주석. `Tools/docking_field_kit/RUNBOOK.md:38` 동일("잔류 오류의 정체는 판다 부팅 비트레이트 500 kbps 였고 펌웨어에서 250 kbps 로 정정됨").
    > → **이 줄을 근거로 "전원 인가 시 passthrough 불가"로 판단하지 말 것.** 비트레이트가 버스와 정합(250 kbps)이면 전원 인가 상태에서도 브릿지가 성립한다.

## 3. 검증 상태

| 항목 | 상태 |
| --- | --- |
| **도킹 게이트 (intercept, T1~T6)** | ✅ **6/6 PASS** — CAN2_H를 pin23으로 이동 후 (올바른 배선에서 재확인까지) ⚠ **2026-07-25 재시행에서 T6 미확정 — 아래 §3 정정 블록 참조** |
| **릴레이 passthrough (fail-safe)** | ✅ **확인** — 판다 미전원/전원투입(부팅 passthrough) 모두 can0↔can1 브릿지 통신 성공 |
| **도킹 속임수 시나리오 (양방향)** | ✅ **6/6 PASS** — PC가 CAN2로 모터 구동 + Seer(CAN0)가 모터 살아있다 인식 유지 + PC명령 은폐 |

**도킹 벤치 종합 검증 항목 (2026-07-20):**
- 게이트 T1~T6: passthrough·쓰기차단·가짜ack·읽기통과·guard RTR·PC직접구동
- 속임수 A1·A2(모터→Seer 응답/guard 전달) · B1·B2(PC구동+에코차단) · C1·C2(Seer폴링→모터+guard)
→ **개념 전체가 PCAN 벤치에서 실증됨.** 남은 것 = 실 Seer + 실 모터 실차 검증.

> **⚠ 2026-07-25 미판정 모순 — 위 §3 :31 "T1~T6 6/6 PASS" 와 :38 "개념 전체 실증"을 현재 상태로 인용하지 말 것.** (원문은 이력 보존을 위해 유지)
> **기록 A(본 문서, 2026-07-20)**: 게이트 T1~T6 **6/6 PASS**.
> **기록 B(2026-07-25 재시행)**: `docs/can_relay/field-record-orin-nx-2026-07-25.md:97` "**amap-1 PCAN 벤치**(가짜 Seer/모터): `seer_gate_bench.py` **T1~T5 PASS**(passthrough·쓰기차단·가짜ack·읽기통과·guard RTR). T6(PC구동)·`hb_compare` 는 **벤치 판다(#1) 불안정**(LIBUSB_BUSY 지속 + BAD SEND MANY)로 미확정."
> **어느 쪽이 현재 상태인지 문서만으로 판정 불가.** 위 6/6 은 **2026-07-20 시점 기록**이다.
> **판정에 필요한 측정**: 안정된 벤치 판다(#2, 또는 USB 재점유 해소 후 #1)로 **T6(PC 직접구동) + `hb_compare` 재실행** → 결과와 실행 일시·판다 시리얼을 여기에 병기.

## 4. 실차 이관 시 주의

1. **핀맵 준수(가장 중요)**: CAN2_H=**pin23**(pin22 死핀 아님), CAN2_L=pin24, CAN0_H=pin4, CAN0_L=**pin5**(=pin6 동일넷).
   - **pin5 안내**: CAN0_L이며 **릴레이 passthrough(fail-safe) L 브릿지 지점(pin5↔pin24)**. Seer L은 pin5 연결 권장.
2. **PCAN/모터/Seer 케이블은 실측 핀맵대로** — comma 표준 가정 금지(이번 장시간 삽질의 원인).
3. passthrough(fail-safe)는 릴레이 OFF 시 정상 — 도킹은 게이트(intercept)로 동작.
4. 전원: 12VIN(핀12/14)+GND(핀1/26).

## 5. 교훈

- **클론 보드는 comma 표준 핀아웃을 신뢰하지 말 것.** CAN2_H가 pin22→pin23 이동, pin22 死핀. CAN0도 재배치 의심.
- 실측(통전) 기반 핀맵을 먼저 확정한 뒤 배선할 것.
