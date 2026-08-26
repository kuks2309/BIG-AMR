---
id: 2026-08-26-001
type: rule-violation
category: verify-skip
status: closed
reflected_assets:
  - docs/claude-mistake/INDEX.md#메타-패턴
  - Tools/find_experiment_data.sh
---

# 2026-08-26 22:24 (KST) — rosbag 부재를 얕은 find 로 단정 — 일곱 번째 「없다」 계열

## 무엇을 했는가

사용자가 "rosbag 어제 실험 파일 잇는지요?" 라고 물었을 때
`find /home/nvidia -maxdepth 5 -name 'metadata.yaml' -newermt '2026-08-24'` (0건) 과
`find /home/nvidia -maxdepth 4 -type d -name '*bag*'` (구 워크스페이스만) 두 번의
**깊이 제한 검색**만으로 "어제 실험의 rosbag 은 없습니다 — 기록물은 jsonl 3건과
리포트가 전부" 라고 단정 보고했다.

## 무엇이 잘못이었나

세션 시작 주입(INDEX §메타 패턴, 2026-08-25-001 확장 교훈)의 명시 규칙 위반:
「**「없다/미검증/위험」 단정 전부, 쓰기 전에 그 식별자로 저장소 전수 grep 1회.
안전 사유도 면제 없음**」 — 전수 조사 없이 부재를 선언했다.
실재: `Log/dock_precision_0825/` 4개 + `Log/drive_0825/` 1개, 합 5개 bag(≈1.7 GB).
metadata.yaml 은 depth 7 이라 maxdepth 5 에 걸리지 않았고, 디렉토리는 depth 5 라
maxdepth 4 에 걸리지 않았다 — **한 단계 차이로 두 번 다 빗나간 검색을 "전수"로 취급**했다.

## 사용자 지적

같은 질문을 재차 물었다("어제 실험 rosbagv파일 잇는지?") — 재질문이 재검토를
유발했고, 깊이 무제한 전수 검색(`find / -name '*.db3' -o -name '*.mcap'`) 30초로
5개 전부 나왔다.

## 원인 분석

규칙은 이 세션에 **주입돼 있었다**(SessionStart hook 의 INDEX §메타 패턴 — "여섯
번째"까지 축적된 동일 계열). 그런데도 어겼다: ① maxdepth 는 속도를 위한 임의
제한이었는데 0건 결과를 "부재 증명"으로 승격시켰고, ② 검색이 빗나갈 수 있다는
신호(어제 세션이 bag 을 남겼을 개연성 — 같은 세션 작업이고 Log/ 에 jsonl 이
실재)를 대조하지 않았다. 강제 장치 관점: 부재 단정 직전에 "전수였는가"를 묻는
기계 게이트는 없다 — 수동 준수 영역이며, 이번엔 그 수동 준수가 무너졌다.

## 재발 방지

- **실행 게이트 신설**: `Tools/find_experiment_data.sh` — 날짜(YYMMDD)를 받아
  저장소 Log/ 와 홈 전체를 **깊이 무제한**으로 bag(.db3/.mcap/metadata.yaml)·
  jsonl·리포트까지 훑는 표준 검색기. "실험 데이터 있나" 질문에는 이 스크립트
  실행이 1순위이고, 부재 보고는 이 스크립트 0건 출력 첨부 시에만 허용.
- INDEX §메타 패턴에 일곱 번째 변형(깊이 제한 find 를 전수로 승격)을 추기 —
  교훈 정밀화: **전수 grep 의 "전수"에는 깊이·경로 제한이 없어야 하며, 제한을
  둔 검색의 0건은 부재의 근거가 될 수 없다.**
