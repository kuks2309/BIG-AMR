# panda-relay-firmware — SW 구조 분석 타임라인

블랙판다(STM32) 도킹 릴레이 펌웨어의 SW(Software) 구조 분석 인덱스.

| 날짜 | 문서 | 범위 | 비고 |
|---|---|---|---|
| 2026-07-20 | [2026-07-20.md](2026-07-20.md) | 기존 판다 펌웨어(`26524538`) CAN 릴레이 경로 + 신규 제안 모듈 | 최초 구조 제시. 게이트 삽입점(`safety_hooks.fwd`) 확인, 보완 필요 4건 도출 |

## 관련 문서

- 프로토콜: [docs/can_relay/usb-can-mapping-table.md](../../can_relay/usb-can-mapping-table.md)
- 릴레이 실증: [References/Black-Panda/CAN-relay-test-resolution.md](../../../References/Black-Panda/CAN-relay-test-resolution.md)
