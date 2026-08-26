---
id: 2026-08-26-003
type: mistake
category: context-missing
status: closed
reflected_assets:
  - code_updates/2026-08-26-drive-test-ui.md
  - /home/nvidia/.claude/projects/-home-nvidia-Project-Ford-CATL-AMR-Big-AMR/memory/biguamr-experiment-set-names.md
---

# 2026-08-26 22:37 (KST) — 왕복 실험 UI 를 어제 실기 방식 기록을 안 보고 설계

## 무엇을 했는가

왕복 주행 실험 UI 의 실험 루프를 translate 후진→전진 복귀만으로 설계·실행했다.
도착 판정도 translate 정지 지점의 PGV 순간값이었다.

## 무엇이 잘못이었나

어제(2026-08-25) ±3 mm 실기 33회의 확정 방식 — 후퇴 → 고속 직진 레그 →
게이트(타깃 앞 0.25 m) 정지 → **/wall_pose 기반 정밀 도킹 전환** → 도킹 완료 후
PGV 10샘플 평균 — 이 저장소에 기록돼 있었는데(리포트 §3 시험 방법, bag 2본)
참조하지 않았다. 그 결과 wall_localizer·dock_approach 서버가 스택에서 빠졌고
복귀 오차가 65 mm 급으로 나왔다(도킹 없인 당연한 수치).

## 사용자 지적

"지금 오늘 구성한 gui 는 어제 실험 방식이랑 많이 다르네요. 기록 안보고 또 구성한
것 같습니다. 정밀 도킹을 위해서 wall detection이 빠져있네요" — 이어 "어제 실험에서
matrix 위치가 기록 되어 있음 / 그것으로 사용하면 되지 않는지?" 로 목표 출처까지
교정.

## 원인 분석

context-missing — 실험 절차를 설계하는 작업인데 같은 절차의 전날 확정 기록
(리포트 §시험 방법·rosbag)을 수집 단계에 넣지 않았다. "왕복 주행"이라는 새 이름에
끌려 별개 실험으로 취급했지만, 사용자의 목적은 어제 방식의 왕복 반복이었다.
도킹 목표도 어제 bag 의 /wall_pose 정착 구간에 이미 있었다(추출 결과 σ 1.1 mm).

## 재발 방지

실험 도구·절차를 설계하기 전, 같은 계열 실험의 **직전 확정 기록(리포트 §시험
방법 + bag 토픽 구성)을 먼저 Read** 하고 그 절차·계측 방식(필드명까지)을 그대로
계승한다 — code_updates/2026-08-26-drive-test-ui.md "어제 실기 방식으로 왕복 실험
재구성" 절에 계승 내역을 기록했고, 집합 명칭·원자료 대조 원칙은 메모리
biguamr-experiment-set-names 에 이미 등재돼 있어 이번 사건의 절차 항목을 함께
적용한다.
