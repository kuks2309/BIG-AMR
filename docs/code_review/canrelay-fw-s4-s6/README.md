# CAN Relay 펌웨어 S4·S6 — 리뷰 타임라인

대상: `Tools/Can_Relay/panda-firmware/board/` S4(구동륜 감속 정지)·S6(재engage 차단 래치) 추가분.

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| [2026-07-29](2026-07-29.md) | 서명 `015f4373` (git 미추적) | COMMENT | Medium 2(정지프레임 TX 재init 레이스·S4 실효성 미검증) / Low 2 / Info 1. 적대적 감사 17에이전트 fw-s4·fw-s6 SUPPORTED |

> 패키지 병기본: `Tools/Can_Relay/panda-firmware/docs/code_review/canrelay-fw-s4-s6/` (동일 내용, 미추적 펌웨어 트리와 함께 위치).
