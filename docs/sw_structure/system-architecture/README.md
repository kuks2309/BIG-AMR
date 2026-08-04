# system-architecture — 타임라인 인덱스

CATL-Ford CAN-Relay 전체 시스템 아키텍처 (하드웨어+소프트웨어) 버전 이력.

| 날짜 | 문서 | 요지 |
|------|------|------|
| 2026-06-27 | [2026-06-27.md](2026-06-27.md) | 초판 재설계 — 레거시 리트로핏 + Black Panda(CAN relay) 인라인 삽입, 권한=PLC, fail-safe=릴레이 HW. ~~미해결 Q1~Q5.~~ → ⚠ **2026-07-27 감사 정정**: 표 기준 잔여는 **Q3b·Q3c·Q4·Q5·Q8** (Q1/Q1′/Q2/Q3 은 같은 문서 `:45-50` 에서 종결, Q3b 는 본 감사에서 '종결'→'미판정' 하향). |

## ⚠ 2026-07-27 감사 — 본 문서를 읽기 전 알아야 할 정정 (2026-06-27.md)

- **§7.6 서두 D13 「PLC↔Panda 직결 없음」은 철회됨** → D14(06:18) 로 대체(여유 CAN 직결 있음). 근거: 2026-06-27.md `:27,:32,:377,:421`.
- **「heartbeat 소실 → fail-safe passthrough 복귀」서술은 부정확** — 실제는 `SAFETY_SILENT` 진입이며, 그 결과로 릴레이가 OFF 된다. 근거: `Tools/Can_Relay/panda-firmware/board/main.c:236-238,248-249,88-89` + `docs/verified_facts/2026-07-27.md:133`(§A-5). 별개로 `heartbeat_engaged`↔`controls_allowed` **불일치** 경로(`main.c:222-228`)는 `controls_allowed=0` 만 하고 **릴레이를 건드리지 않는다**.
- **「PASSTHROUGH = 무전원 기본값」의 인용 근거 2건은 확인 불가**(`References/Black-Panda/02-can-architecture.md` 부재, `black.h:92-104` 는 GPS 분기). 부팅 기본 passthrough 의 실재 근거는 `board/drivers/harness.h:90-91`. **'무전원 시' 는 미검증 HW 가정**(전원 차단 후 도통 확인 필요).
- **Q3b(NRU USB2 무경합)는 미판정** — 확보 근거는 USB3.2 포트 대역뿐이며 같은 문서 `:282` 는 아직 확인 필요라고 적는다.
