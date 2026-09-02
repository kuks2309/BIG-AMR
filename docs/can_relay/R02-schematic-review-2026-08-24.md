# CAN RELAY R02 회로도 검토 — 2026-08-24 (v2)

> **정정 이력 v1→v2 (2026-08-24)**: v1 은 CN4/bus1 을 "예비" 로 서술했으나, 기존 기록
> [fw_backups/README-2026-08-23.md §R02 배선 확정](../../Tools/Can_Relay/fw_backups/README-2026-08-23.md)
> (L75-87)에 **CN4 = IMU(Inertial Measurement Unit) 용도 확정**이 이미 있었다(사용자 지적으로 발견,
> 실수 기록 [2026-08-24-002](../claude-mistake/2026-08-24-002_r02-decision-record-not-swept.md)).
> v2 는 CN4 역할을 IMU 로 정정하고, 확정 기록 대비 정합 검증과 IMU 후속 확인 3건을 추가했다.
> 치명 결함 판정(커넥터 라벨 3건)은 변동 없음.

> 대상: [CAN RELAY R02.pdf, page 1](../../Tools/Can_Relay/R02/CAN%20RELAY%20R02.pdf) (A3 1장, 표제란 날짜 2026-08-24)
> 비교 기준: [CAN RELAY R01.pdf, page 1](../../Tools/Can_Relay/R01/CAN%20RELAY%20R01.pdf) (2026-07-27) ·
> **R02 배선 확정 기록**(2026-08-23, [fw_backups/README-2026-08-23.md](../../Tools/Can_Relay/fw_backups/README-2026-08-23.md) L75-87
> — Seer=CN2/CAN1/bus0/PB8·9, 모터=CN3/CAN3/bus2/PA8·15, **IMU=CN4(+5V)/CAN2/bus1/PB5·6**) ·
> R01 실기 분석(2026-08-23 engage 실패 → 근본 원인 = 커넥터 용도 배정 오류 + bus2 트랜시버 미실장)
> 검증 방법: PDF 텍스트 객체 좌표 추출(pdftotext -bbox)로 넷 라벨↔심볼 핀 인접성 판독(라벨 y = 핀명 y − 2.7pt 오프셋 일정, PA0·PA2·PA11 등 무모호 라벨로 캘리브레이션) + 펌웨어 소스 대조. OCR(Optical Character Recognition) 아님 — PDF 자체 텍스트라 철자 오독 없음.

## 결론

**MCU·트랜시버·EN·릴레이 쪽 재배선(R02 의 목적)은 정확히 달성됐다. 그러나 커넥터 쪽 넷 라벨 3개가
R01 그대로 남아 있어, 그린 대로 만들면 Seer 커넥터(CN2)가 완전 부유(open)가 되고 모터는 예비 버스에
붙는다 — 발주 전 라벨 3건 정정 필수.**

## 1. 정합 확인 (✓ = 1차 source 직접 확인)

펌웨어(black-panda, hw_type 0x03) 요구 위상과 R02 배선 대조:

| 항목 | R02 회로도 | 펌웨어 요구 | 판정 |
| --- | --- | --- | --- |
| U2 (net CAN3) | TXD/RXD → PB9/PB8 | STM32 CAN1 = **bus0(Seer 슬롯)** — [stm32fx/peripherals.h:30-34](../../Tools/Can_Relay/panda-firmware/board/stm32fx/peripherals.h#L30-L34) PB8/9=AF CAN1 | ✓ |
| U2 STB | net CAN3_EN → **PC1** | EN#1=PC1 — [black.h:4-5](../../Tools/Can_Relay/panda-firmware/board/boards/black.h#L4-L5) | ✓ |
| U3 (net CAN1) | TXD/RXD → PA15/PA8 | STM32 CAN3 = **bus2(모터 슬롯)** — [black.h:133-134](../../Tools/Can_Relay/panda-firmware/board/boards/black.h#L133-L134) PA8/15=AF11 CAN3 | ✓ |
| U3 STB | net CAN1_EN → **PA0** | EN#3=PA0 — [black.h:10-11](../../Tools/Can_Relay/panda-firmware/board/boards/black.h#L10-L11) | ✓ |
| U4 (net CAN2) | TXD/RXD → PB6/PB5 | STM32 CAN2 normal 쌍 = **bus1(IMU 슬롯)** — [black.h:108-109](../../Tools/Can_Relay/panda-firmware/board/boards/black.h#L108-L109) + 확정 기록 L80 | ✓ |
| U4 STB | net CAN2_EN → **PC13** | EN#2=PC13 — [black.h:7-8](../../Tools/Can_Relay/panda-firmware/board/boards/black.h#L7-L8) | ✓ |
| 릴레이 K1 | net CAN1↔CAN3 브리지(120Ω R22/R32 포함, R01 과 동일 구조) | fail-safe 는 Seer↔모터 직결이어야 함 = bus0 넷↔bus2 넷 | ✓ (넷 차원) |
| RELAY 구동 | **PC10** (Q31 베이스) | pin_relay_SBU1=PC10 — [black.h:141-145,179](../../Tools/Can_Relay/panda-firmware/board/boards/black.h#L141-L145) | ✓ |
| V_SENSE | **PC2** (R53/R54 분압) | 전압 ADC ch12=PC2 (R01 과 동일 유지) | ✓ |
| LED | BLUE=PC6·GRN=PC7·RED=PC9 | [black.h:33-47](../../Tools/Can_Relay/panda-firmware/board/boards/black.h#L33-L47) | ✓ |

펌웨어 버스 용도: Seer 응답·포워딩 원점 = bus0([safety_seer_gate.h:25-28](../../Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h#L25-L28)),
모터 방향 = bus2([safety_seer_gate.h:166-192,270-273](../../Tools/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h#L166-L192)). ✓

즉 R01 의 근본 결함(Seer·모터가 STM32 CAN2 뮤텍스 쌍 PB12/13·PB5/6 에 동거 + bus2 트랜시버 부재)은
R02 에서 해소됐다. R21(구 U2 STB 풀업)은 삭제되고 3개 트랜시버 STB 전부 MCU 제어로 바뀐 것도 정합.

**확정 기록 대비**: MCU 쪽 3행(Seer/모터/IMU 의 STM32·버스·핀)이 2026-08-23 확정표와 **전부 일치** ✓.
CN4 의 +5V 유지도 IMU 전원 공급 목적과 부합(우연 아님).

## 2. 치명 결함 — 커넥터 넷 라벨 미갱신 (✓ 좌표 판독)

커넥터 쪽 라벨이 R01 그대로다:

| 커넥터 | 현재 라벨 (R02 그대로) | 결과 | 연결 요건 (같은 넷이 돼야 할 상대) |
| --- | --- | --- | --- |
| **CN2 (Seer)** | `CAN0_H/L` | net CAN0 은 R02 전체에서 여기 **한 곳뿐** → CN2 는 Z21(ESD)만 붙은 **완전 부유** | U2 CANH/CANL (bus0) — 현 도면 명명으로는 `CAN3_H/L` |
| **CN3 (모터)** | `CAN2_H/L` | 모터가 **bus1(IMU 슬롯)** 에 붙음 → 펌웨어는 bus2 로 포워딩하므로 불통 | U3 CANH/CANL (bus2) — 현 도면 명명으로는 `CAN1_H/L` |
| **CN4 (IMU, +5V)** | `CAN3_H/L` | IMU 커넥터가 **bus0(Seer 슬롯)** 를 차지 | U4 CANH/CANL (bus1) — 현 도면 명명으로는 `CAN2_H/L` |

> **라벨 명칭은 사용자 결정 사항** — 본 검토의 요구는 위 **연결 관계**뿐이다. 어떤 이름을 쓰든
> 각 커넥터와 해당 트랜시버 출력(그리고 릴레이 K1 은 CN2 넷↔CN3 넷)이 **동일 철자 라벨로 한 넷**이
> 되면 충족한다. 넷 이름 전면 개명(예: SEER/MOTOR/IMU 계열, 또는 **연결 장비 번호 기반 CAN 번호**
> — 하네스 관례처럼 Seer 버스=CAN0 등)도 무방 — 단 개명 시 트랜시버·릴레이 쪽 라벨도 함께 바꿔
> 짝을 유지할 것. 장비 번호 기반 명명을 쓰면 넷 이름과 STM32 주변장치 번호(CAN1/2/3)가 서로
> 달라지는데, 이는 R01 오배정의 발단이었던 혼동 지점이므로(넷 이름을 따라 커넥터를 배정),
> 도면 여백에 **넷 이름 ↔ STM32 CAN ↔ 펌웨어 bus 대응표 1줄**을 남겨 두면 재발을 막는다.

파급: net CAN1(bus2, 모터 슬롯)은 **어느 커넥터에도 도달하지 않고**(U3 + K1 뿐), 릴레이 fail-safe
브리지는 커넥터 기준 "무연결 넷 ↔ CN4(IMU)" 를 스위칭하는 상태다 — 전원상실 시 Seer↔모터 직결이라는
안전규칙 S1·S2 가 그린 대로는 성립하지 않는다. **커넥터 쪽 라벨 3곳의 연결만 맞추면 전부 동시에
해소된다** (명명은 사용자 결정, 트랜시버·MCU·릴레이 쪽은 손댈 것 없음).

증거(좌표): CN2 핀열(x≈1082, y 354–385) 옆 라벨 `CAN0_H`(943.9, 360.7)·`CAN0_L`(943.9, 367.9);
`CAN0_*` 출현 횟수 전 도면 1회씩. `CAN1_H/L` 출현 = 릴레이(x 440.6)·U3(x 881) 2곳뿐, 커넥터 열(x 944) 없음.

## 3. 경미 지적

1. **표제란이 여전히 "CAN RELAY R01"** (날짜만 2026-08-24 로 갱신, Rev 칸 공백) → "CAN RELAY R02" 로 정정.
2. **J1(SWD(Serial Wire Debug) 헤더, SWDIO/SWCLK=PA13/14) 삭제됨** — 플래시는 USB DFU(BOOT0, 신설 S3 스위치)로 가능하므로
   치명은 아니나, 벽돌 복구·저수준 디버그 수단이 DFU 하나로 준다. 의도 여부 확인 요망.
3. **PB12/13(STM32 CAN2 OBD 쌍)은 트랜시버 없음** — 호스트가 `CAN_MODE_OBD_CAN2` 를 요청하면 bus1 이
   죽는다([black.h:110-117](../../Tools/Can_Relay/panda-firmware/board/boards/black.h#L110-L117)).
   **bus1 = IMU 버스이므로 OBD(On-Board Diagnostics) 모드 요청 시 IMU 판독이 끊긴다** — 운용상 OBD 모드 금지 준수 필요.
4. PC0/PC3(하네스 SBU 감지 ADC)은 R01 과 동일하게 미연결 — 기존 검증 보드들과 같은 조건이라 신규 위험 아님.

## 3.1 IMU(bus1) 후속 확인 — 확정 기록의 미결 3건 (회로도 밖, 브링업 시 검증)

확정 기록 L84-87 이 명시한 항목으로, 회로도가 아닌 펌웨어·운용 검증 사항:

1. IMU 가 250 kbps(bus1 비트레이트)와 정합하는지 — IMU 모델 확정 후
2. 판다가 전 버스 RX 를 USB 로 호스트 전달하므로 Jetson 의 bus1 IMU 판독 가능 — 실기 확인
3. IMU 폴링/설정에 TX 필요 시 SILENT/게이트 모드에서 bus1 호스트 TX 허용 여부 확인

## 4. 판정 요약

- 재배선 목적(동시 2버스 MITM 위상 + fail-safe 브리지) 달성: **✓** (넷·핀 차원)
- 발주 가능 여부: **아니오 — §2 라벨 3건 정정 후 가능.**
- 정정 후 재검토 항목: 커넥터 열 라벨 3개 + 표제란. 그 외 변경 불요.
