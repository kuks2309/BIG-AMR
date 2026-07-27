---
id: 2026-07-27-001
type: rule-violation
category: verify-skip
status: open
reflected_assets:
  - docs/claude-mistake/2026-07-27-001_freeze-object-list-guessed.md (data-grounding 원칙 재확인)
  - Tool/Can_Relay/panda-firmware/board/safety/safety_seer_gate.h (문서기반 freeze 객체로 정정 예정)
---

# 2026-07-27 12:14 (KST) — freeze 대상 객체를 문서 아닌 추측으로 작성

## 무엇을 했는가
Seer 게이트 surgical freeze 펌웨어에서, PC 구동을 Seer에게 숨길 "모션 노출 객체"
목록을 `{0x6064, 0x606C, 0x6078}` 로 코딩했다. 이를 authoritative 캡처데이터
(`tongyi-motor-protocol-tables.md` §10 / `tongyi-canopen-protocol-reference.md` §4의
Seer 실측 읽기객체 집합)와 **먼저 대조하지 않고** 일반 CANopen 지식으로 선정했다.

## 무엇이 잘못이었나
- `docs/claude_guideline/coding/coding.md` §2(사전조사, :L38-40) 위반 — "코딩 계획 전에
  함수표·전역표(=여기선 캡처된 프로토콜 실측표)를 먼저 읽는다"인데, freeze 객체 선정 전에
  Tongyi 문서 §10/§4를 읽지 않고 추정으로 코딩.
- `docs/claude_guideline/reverse_engineering/principle.md` §6 위반 — 실측근거 없는 [동작]
  가정을 코드에 반영. 결과:
  - **0x606C(속도) 오포함** — 문서 §10에서 Seer 미read(굵게 아님), §4 부재. 불필요.
  - **0x6041(statusword) 누락** — 문서 §10 Seer 실측 read객체, §8 bit10(Target reached)
    이동 중 토글 = 모션 누설 소지인데 freeze 안 함.

## 사용자 지적
- "왜 분석 데이터를 활용하지 않고 마음대로 명령을 만들어서 보내는지 이해가 안됨"
- "그것을 기반으로 작성해야 하는데... 지금 무슨 데이터로 작성했는지?"
- "지금 심각한 실수를 하는 것입니다. 코딩은 추측에 의해서 하면 되는 것이 아닌데"

## 원인 분석
규칙(coding §2 사전조사, reverse_engineering §6)은 설치·인지돼 있었으나 advisory라
"코드의 각 상수/객체가 실측·1차문서에 근거하는가"를 기계 차단하는 게이트가 없었다.
Tongyi 문서(§10 RO 실측표)를 **끝까지 읽기 전에** 코드를 먼저 썼고, 일반 CANopen 지식으로
빈칸을 메운 과신이 직접 원인. 2026-07-26-001(검증 없이 완료선언)과 동일 뿌리 =
**데이터 그라운딩 없이 진행하는 반복 패턴**(meta-pattern).

## 재발 방지
- **원칙(강화)**: 펌웨어/프로토콜 코드의 **모든 객체 인덱스·상수는 캡처데이터 또는 1차문서
  라인 인용을 코드 주석에 병기**한다. 인용 없는 값은 코드에 넣지 않는다.
- **정정**: freeze 객체를 문서 §10/§4 실측 read집합 기반 **{0x6064, 0x6078, 0x6041}**
  (0x606C 제거·0x6041 추가)로 수정 예정. 각 객체에 문서 라인 인용 주석.
- **선행 검증**: 코딩 전 라이브 캡처로 Seer 실제 폴 객체집합·현재 인코더값을 실측해 STEER_HOME
  등 상수를 재도출(추정 금지).
- (강제 gap) "값에 실측/문서 인용 필수" hook 미설치 — 후속 과제.

**owner**: claude
