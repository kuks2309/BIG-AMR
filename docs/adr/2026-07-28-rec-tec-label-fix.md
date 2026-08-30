# ADR 2026-07-28 — `can_health` 의 REC/TEC 라벨 반전 수정

## 상태

**Accepted — 2026-07-28 실기 플래시·재현 검증 완료.** 서명 md5 `12dd11387c6d68c0`.

## 맥락

`0xc3`(`can_health`)이 STM32 bxCAN 의 ESR(Error Status Register)에서 뽑는 두 카운터의 **이름이 서로 뒤바뀌어** 있었다.

**1차 source — 벤더 CMSIS(Cortex Microcontroller Software Interface Standard) 헤더**
`board/stm32fx/inc/stm32f413xx.h:2022,2025`

```
#define CAN_ESR_TEC_Pos  (16U)   /* Transmit Error Counter */
#define CAN_ESR_REC_Pos  (24U)   /* Receive  Error Counter */
```

**수정 전 코드** (`board/usb_comms.h:67-68`)

```c
can_health->receive_error_cnt  = (uint8_t)((esr >> 16) & 0xFFU);   /* 실제 TEC */
can_health->transmit_error_cnt = (uint8_t)((esr >> 24) & 0xFFU);   /* 실제 REC */
```

비트 오프셋은 헤더와 일치하므로 **값은 정확했고 이름표만 반대**였다. 크래시나 오동작은 없고, 사람이 읽고 내리는 진단 판단만 뒤집힌다 — TEC 상승은 "상대가 ACK(Acknowledgement) 안 함"(노드 부재·비트레이트 불일치)을, REC 상승은 "내가 못 읽음"(내 쪽 배선·노이즈)을 뜻해 점검 방향이 정반대다.

## 실기 실증 (추론 아님)

미연결 bus1(CAN2)로만 송신하면 ACK 부재로 **물리적으로 TEC만** 오른다. 사전에 bus1 수신 0(3초 수동청취, bus0·bus2 는 각 4,780프레임)으로 격리를 확인했다.

| | `receive_error_cnt` | `transmit_error_cnt` | `esr_reg` |
|---|---|---|---|
| **수정 전** | **128** ← 수신 0건인데 상승 | 0 | `0x00800033` |
| **수정 후** | 0 | **128** | `0x00800033` (동일) |

`LEC=3`(ACK error)·`error_passive=1` 도 양쪽 동일. **ESR 원값이 같고 라벨만 바로잡혔다.**

## 결정

**대입 대상만 맞바꾼다.** 구조체 필드 순서·와이어 포맷·호스트 코드는 건드리지 않는다.

```c
can_health->transmit_error_cnt = (uint8_t)((esr >> 16) & 0xFFU);   /* TEC bits 23:16 */
can_health->receive_error_cnt  = (uint8_t)((esr >> 24) & 0xFFU);   /* REC bits 31:24 */
```

`can_health_t` 는 offset4=`receive_error_cnt` / offset5=`transmit_error_cnt` 이고 호스트도 그 순서로 언팩하므로, **오프셋에 들어가는 값만 바꾸면 필드명·호스트 키가 자동으로 맞는다.** 펌웨어 2줄, 호스트 변경 0.

> 당초 "펌웨어 2줄 + 호스트 2줄" 로 추정했으나(이름을 바꾸는 방식 가정), 대입을 바꾸는 편이 더 작고 안전하다.

## ⚠ 과거 기록의 소급 해석

**과거 로그·문서의 숫자는 정확하다. 이름만 반대로 읽으면 된다.**

| 기록 | 원문 | 올바른 해석 |
|---|---|---|
| `docs/adr/2026-07-24-canhealth-firmware.md` 벤치 실측 | "REC=128" | **TEC=128** (송신 전용 시나리오와 정합) |
| `docs/can_relay/field-record-orin-nx-2026-07-25.md` | "bus2 RX 수신에러(REC 100~237)" | **TEC 100~237** (engage 시 미ACK 송신과 정합) |

⇒ **2026-07-28 이전 기록에서 `receive_error_cnt`/REC 는 TEC 로, `transmit_error_cnt`/TEC 는 REC 로 읽을 것.**
이 경계는 서명 md5 로 판별한다 — `12dd1138…` 이후가 수정본이다.

기록자·실험자의 잘못이 아니었다. 기록은 화면 값을 정확히 옮겼고, 오류는 펌웨어 라벨 한 곳에 있었다.

## Rollback Plan

| 항목 | 내용 |
|---|---|
| 직전 실기 이미지 | `Tools/Can_Relay/fw_backups/panda.bin.signed.coverfix_2026-07-28_d341d5d8` (30,204 B) |
| 현재(수정본) | `…/panda.bin.signed.rectecfix_2026-07-28_12dd1138` (30,204 B) |
| 되돌리는 법 | `flash_panda.py <직전 이미지>` 후 `0xd3`+`0xd4` 서명 md5 확인 |
| 되돌림 판단 | 없음 — 라벨 정정이라 기능 회귀 요인이 없다. 되돌리면 오히려 진단이 다시 뒤집힌다 |
| 체인 전체 | `Tools/Can_Relay/fw_backups/README-2026-07-28.md` |

## 검증

- [x] 1차 source 대조 (벤더 헤더 `:2022`,`:2025`)
- [x] 빌드 통과(`-Werror`), 30,204 B / 한도 49,152 B
- [x] 실기 실증 — 수정 전 `receive=128`, 수정 후 `transmit=128`, ESR 원값 동일
- [x] 플래시 + 서명 md5 대조
- [x] 호스트 무변경 확인 (구조체 오프셋·언팩 순서 불변)

## 참조

- 리뷰 결함 **[H14]**: `docs/code_review/can_relay_firmware/2026-07-28.md` §High
- 최초 발견: `docs/adr/2026-07-24-canhealth-firmware.md` 의 2026-07-27 정정 블록 — 문서에만 반영되고 코드는 미수정 상태로 남아 있었다
