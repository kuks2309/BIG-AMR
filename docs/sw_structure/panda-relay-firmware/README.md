# panda-relay-firmware — SW 구조 분석 타임라인

블랙판다(STM32) 도킹 릴레이 펌웨어의 SW(Software) 구조 분석 인덱스.

| 날짜 | 문서 | 범위 | 비고 |
|---|---|---|---|
| 2026-07-20 | [2026-07-20.md](2026-07-20.md) | 기존 판다 펌웨어(`26524538`) CAN 릴레이 경로 + 신규 제안 모듈 | 최초 구조 제시. 게이트 삽입점(`safety_hooks.fwd`) 확인, 보완 필요 4건 도출 |

## 관련 문서

- 프로토콜: [docs/can_relay/usb-can-mapping-table.md](../../can_relay/usb-can-mapping-table.md)
- 릴레이 실증(외부 근거·미대조): `References/Black-Panda/CAN-relay-test-resolution.md` — 이 저장소에 부재(2026-07-27 검증, docs/can_relay/black-panda-hw-verification.md §1). 원본 저장소·커밋 해시 병기 또는 근거 문서 동반 이식 전까지 "외부 근거, 미대조"로 취급.
