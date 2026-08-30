---
id: 2026-07-28-003
type: mistake
category: intent-guess
status: closed
reflected_assets:
  - /home/nvidia/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-system-health-monitor.md
---

# 2026-07-28 16:05 (KST) — "gui 실행해서 테스트" 의 지시대상을 CAN relay GUI 로 오해

## 무엇을 했는가

세션 주제는 **PC(Personal Computer) 자원 모니터링**(`src/Safety/system_health`)이었다. 사용자가
"커밋 하고 gui 실행해서 테스트 해봅시다" 라고 했을 때, 직전 작업이 `Tools/amr_test_gui`(CAN relay
GUI)의 종료 해제 이식이었다는 이유로 "gui" 를 그 GUI 로 해석했다. 그리고:

1. `DISPLAY=:0` 에 `Tools/amr_test_gui/gui.py` 를 띄웠다.
2. 내 인스턴스가 예상과 달리 즉시 종료되자, **원인을 캐려고 프로세스·창 목록·USB fd 를 두 차례
   더 조사**했다(다른 세션 인스턴스 PID 411588 판별 포함).
3. 사용자가 "pC 모니터링 테스트 실행하는데 왜 can relay gui를 실행할까??" 로 지적한 뒤에도, 곧바로
   모니터링으로 넘어가지 않고 GUI 프로세스 정리 상태를 한 번 더 확인했다.
4. 이어서 실행한 모니터링 명령은 출력 포맷 f-string 문법 오류로 실패해, 사용자 화면에는 여전히
   "다른 것을 하고 있는" 것으로 보였다.

## 무엇이 잘못이었나

- 세션의 주제(PC 모니터링)와 직전 작업(CAN relay GUI)이 **다른 대상**인 상황에서 "gui" 라는
  모호어를 질문 없이 한쪽으로 확정했다. `system_health` 에는 GUI 가 없으므로 "gui 실행" 이
  모니터링을 가리킬 수 없다고 단정할 근거도 없었다 — 사용자는 모니터링 실행 자체를 뜻했다.
- 지적을 받은 직후에도 **직전 오답의 뒷정리**(프로세스 조사)를 우선했다. 지적의 요구는 "즉시
  올바른 대상으로 전환" 이었다.
- 결과적으로 세 번의 도구 호출을 요청과 무관한 일에 썼다.

## 사용자 지적

> "pC 모니터링 테스트 실행하는데 왜 can relay gui를 실행할까??"

> "지금 뭘 자꾸 실행하는 것인지? pc모니터링 이잖아 그걸 테스트해야 하느데 왜 자꾸 다른것을 하는지?"

> "정신 못 차려?"

## 원인 분석

`intent-guess` — 모호어를 질문 없이 추측했다. 본 저장소에 "모호어 사전 질문" 명시 규칙이
설치돼 있지 않으므로(`docs/claude_guideline/` 에 iteration_anti_pattern·모호어 규칙 부재 확인)
`mistake.md` §판정 기준의 상대성에 따라 `rule-violation` 이 아니라 `mistake` 로 분류한다.

추측이 한쪽으로 쏠린 이유는 **최근성 편향**이다. 직전 30분을 `amr_test_gui` 에 썼기 때문에
"gui" 의 지시대상 후보로 그것만 떠올랐고, "이 세션이 무엇을 하는 세션인가" 를 되짚지 않았다.
지시대상 후보가 2개 이상일 때 최근 작업을 기본값으로 삼는 것은 근거가 없다 — 사용자의 관심은
세션 주제에 걸려 있다.

부수 요인: 두 대상이 **같은 저장소에 공존**하고 이름이 겹치지 않아(`system_health` vs
`amr_test_gui`) 혼동 여지가 없어 보였으나, "gui" 라는 **일반명사**로 지칭되면 구분이 사라진다.

## 재발 방지

지식 자산 보강 — 두 대상의 관계와 "gui" 의 모호성을 메모리에 고정했다:

- `memory/biguamr-system-health-monitor.md` — `system_health` 는 **GUI 가 없는 비-ROS 상주
  샘플러**이고, `Tools/amr_test_gui` 는 **별개 주제인 CAN relay 제어 GUI** 임을 명시. 세션 주제가
  모니터링일 때 "gui" 는 자동으로 `amr_test_gui` 를 뜻하지 않으며, 대상이 갈리면 **1줄로
  되물어야** 한다고 기록.

판단 규칙(다음 세션에 적용): 지시대상 후보가 2개 이상이면 최근 작업을 기본값으로 삼지 않고,
**세션 주제**를 기준으로 고르거나 1줄 질문한다. 지적을 받으면 뒷정리보다 **전환**을 먼저 한다.
