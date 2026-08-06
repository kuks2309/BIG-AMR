---
id: 2026-08-06-003
type: rule-violation
category: verify-skip
status: closed
reflected_assets:
  - docs/code_review/can_relay_ui/2026-08-06.md
  - docs/code_review/can_relay_ui/README.md
---

# 2026-08-06 18:40 (KST) — 함수표 read/갱신 생략 재발 (외부 세션의 GUI 기체선택 작업)

## 무엇을 했는가

LGIT 개발 PC 세션(sess:02319e57, 원격 이식 작업)이 `can_relay/ui/backend_direct.py` 에 기체
선택(`CAN_RELAY_MACHINE`)·주행 스케일 YAML화(`_load_drive_scale`)를 구현하고
`Tools/can_relay_gui/` 런처·`config/machine/lgit_moma_qd.yaml` 을 신설하면서, 기존 함수표
정본(`docs/code_review/can_relay_ui/2026-08-04.md` §3, 전수 115개)을 **읽지 않고** 코드부터
썼으며, 작업 후 표 갱신도 하지 않았다.

## 무엇이 잘못이었나

- coding SOP §2 (`docs/claude_guideline/coding/coding.md:50` "계획 전 함수표·전역변수표를 읽는다")
  — 표 정본이 존재하는데 미독.
- coding SOP §6 (`coding.md:82` 상태-미러형 표 이중 기록 갱신) — 신규 2함수·변경 1함수·전역 3종
  미반영 상태로 작업 종료 선언.
- **동일 지적의 재발**: 2026-08-04 사용자 지적("코딩 규칙에는 … 함수 변수 테이블을 읽고 수정하고
  다시 … 수정하게 되어있지요?")이 `2026-08-04.md:22-24` 에 정직 고지로 박제되어 있었는데도 반복.

## 사용자 지적

2026-08-06 18:34 "코딩 규칙에 따라서 코드 분석후에 함수 변수 테이블을 만들고 읽고 수정하고 다시
업데이트 하나요?" — 질문 형태의 재지적.

## 원인 분석

가시성·강제력 점검: ① 본 저장소 CLAUDE.md·coding SOP 는 인지 상태였으나(같은 번들 계열),
**외부 세션이 원격 저장소를 수정할 때 그 저장소의 code_review 산출물(함수표 정본) 존재를
사전조사 후보에 넣지 않았다** — ADR·config·코드 정독으로 사전조사를 갈음했다. ② 08-04 재발
경고가 리뷰 문서와 타임라인 README 에 있었으나 해당 문서를 열지 않으면 보이지 않는 위치였다.
③ 강제 장치는 본 저장소에 미설치(CLAUDE.md 상단 고지) — ⟦권고⟧ 상태라 수동 규율만 존재.

## 재발 방지

- 함수표 델타 문서 신설·타임라인 갱신(reflected_assets, 루트 정본+패키지 병기 이중 기록) 완료.
- 수동 규율 명문화(본 entry): **외부 세션이 이 저장소를 수정할 때도 대상 패키지의
  `docs/code_review/<주제>/` 함수표 정본 조회를 §2 사전조사 1단계로 포함**한다 — ADR·config
  정독은 표 read 의 대체물이 아니다.
- 작성 세션 측(LGIT) 메모리에도 동형 규칙 반영: 타 저장소 원격 작업 시 그 저장소 SOP·표 자산
  우선 조회.
