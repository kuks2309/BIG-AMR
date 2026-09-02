---
id: 2026-09-02-002
kind: B
detector: none (특정 발화의 진위는 코드 패턴으로 잡을 지점이 없음 — 판단·소통 실패)
status: closed
---

# 2026-09-02 21:32 (KST) — 펌웨어 버전 대조 없이 "현장 킷은 release 계열" 이라 단정

## 무엇을 했는가
"왜 전에는 없던 문제가 지금 나나?" 에 답하며, **확인 전에** 후보 원인으로
"새 보드는 DEBUG 빌드(`DEV-cc5e0491-DEBUG`)이고 **검증된 현장 킷 동작은 release 계열이었음**"
이라고 단정 제시했다. 직후 스스로 `board/obj/version` 과 field-record 를 대조하니 정반대였다 —
`docs/can_relay/field-record-orin-nx-2026-07-25.md:12` 의 **2026-08-03 호밍 10회 연속(클린)이
바로 이 `DEV-cc5e0491-DEBUG`** 였고, 저장소엔 release 빌드가 **아예 존재하지 않는다**
(`board/SConscript:68-72` — RELEASE 는 comma.ai 개인 `CERT` 파일 필수: `assert cert_fn is not None`).
사용자가 "왜 이렇게???" 로 지적했다.

## 무엇이 잘못이었나
CLAUDE.md reverse_engineering §6(배포자산 대조 전 "동작" 확정 금지)·mistake 반복 지적(근거 없는
단정 금지) 위반. "release 계열" 은 대조로 반증됐을 뿐 아니라 **개인 서명 인증서가 없으면 만들 수도
없는 빌드**라, 존재 불가능한 것을 사실로 제시한 환각이었다.

## 원인 분석
"DEBUG 라서 문제" 라는 가설을 세우면서 그 대비항("전엔 release 였다")을 **확인 없이 채워 넣었다.**
대조 근거(`board/obj/version` 실판독·field-record grep)는 바로 다음 스텝에 있었는데 단정을 먼저 뱉었다
— 순서가 뒤집혔다(확인→확정 대신 확정→확인). 세션 내내 반복된 같은 실패의 재발이다.

## 재발 방지
B(검출 불가): 발화의 진위는 코드 패턴으로 못 잡는다. 전달 — 판다 펌웨어 버전/빌드 특성
(`flash_new_board.py`·`panda.bin.signed`·`DEV-cc5e0491-DEBUG`)을 다룰 때 `mistake-relevance` 가
이 처방을 띄운다: **펌웨어 버전·빌드 종류를 주장하기 전 `board/obj/version` 을 실판독하고
field-record 와 대조**한 근거를 먼저 남긴다. "전엔 X 였다" 류 대비 주장은 그 X 를 실측/기록으로
확인하기 전엔 쓰지 않는다.
