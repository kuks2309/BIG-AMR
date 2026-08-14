# 2026-08-15 — 소실된 line_follow 수정 재적용 + 즉시 커밋 (사고 기록 포함)

> 수정 이력의 기록처. 주석은 현재 코드의 사실만 담고 이력은 여기와 커밋 메시지가 담는다
> (`docs/claude_guideline/coding/conventions.md:26`, `hooks/coding-comment-gate.py`).
> 약어: CCG(Claude-Codex-Gemini) · SIL(Software In the Loop) · mux(multiplexer)

- 사용자 지시: 2026-08-15 "CCG 6건 + 주석 정정 재적용 → 빌드 → 단위테스트 / 즉시 커밋 …"
- 선행 이력: `code_updates/2026-08-14-line-follow-ccg-review-fixes.md`(무엇을·왜 바꿨는지) ·
  `code_updates/2026-08-14-line-comment-accuracy-audit.md`(주석 정정 5건)
- 커밋: `9afefce` → `origin/main` 병합 `47493c3`

## 무슨 일이 있었나 — 미커밋 변경이 지워졌다

공유 워킹트리에서 **다른 세션의 `git reset`** 으로 이 세션의 미커밋 변경이 소실됐다.
`git reflog` 에 `reset: moving to origin/main` 이 남아 있다.

소실 범위(재적용 전 `grep -c` 실측):

| 마커 | 소실 전 | 소실 후 |
| --- | --- | --- |
| `require_motion_source`·`v_body_cmd`·`wait_line_start`·`reached_goal`·`steer_hold` | 있음 | **전부 0** |
| `resetLineSnapshot` | 있음 | 2 (커밋 `dda4d75` 에 포함돼 생존) |
| 주석 정정 5건(경로 3·거짓 경고 1·종료조건 1) | 있음 | **전부 0** |

**부수 피해 — 시험 결과의 해석이 바뀐다.** 설치 바이너리에도
`line_follow_require_motion_source` 문자열이 0건이었다. 즉 2026-08-14 에 돌린 **SIL 전부가
수정 이전 코드**로 실행됐다. 특히 `steer_rate_limit` 스윕은 **미분항 수정 이전** 거동을 잰
것이므로 그 결론(무릎점 0.25 · 최적 0.5~1.2 · 0.8 권고)은 **무효**이며 재측정 대상이다.
전진·후진 수렴과 `status −8` 발화는 해당 수정 경로를 타지 않아 결론은 유지되나, 엄밀히는
구버전 결과다.

## 무엇을 했나

이력 문서 두 건을 근거로 CCG 합의 6건과 주석 정정 5건을 **전부 재적용**했다. 코드 내용은
선행 이력 문서와 동일하므로 여기서 반복하지 않는다. 재적용 검증(`grep -c`):
`require_motion_source` 4 · `v_body_cmd` 7 · `wait_line_start` 2 · `reached_goal` 4 ·
`steer_hold` 4 · `last_meas_stamp` 4, 바이너리 문자열 반영 2.

그리고 **즉시 커밋했다.** 세션 워크트리가 옛 커밋(`dda4d75`) 기준이라 폐기 후 현재 `main`
으로 재생성한 뒤, 재적용분과 함께 그때까지 미커밋으로 남아 있던 오늘 산출물
(`line_sim_sensor`·`sil_line_follow.launch.py`·`line_webview`)을 한 커밋으로 올렸다.

## 재발 방지

- **미커밋 상태로 공유 트리에 오래 두지 않는다.** 이번 손실의 직접 원인이다. 작업 단위가
  끝나면 세션 브랜치에 커밋하고 병합까지 마친다
- 이력 문서(`code_updates/`)가 복구를 가능하게 했다 — 미추적 파일이라 reset 에 지워지지
  않았고, 「무엇을·왜」가 적혀 있어 코드를 그대로 되살릴 수 있었다. 이력을 커밋 메시지에만
  두었다면 복구가 훨씬 어려웠다
- 타 세션이 `trnav_2ws_core` 헤더를 바꾼 뒤에는 의존 패키지를 **클린 재빌드**해야 한다
  (2026-08-14 의 기동 크래시가 이 경로였다)

## 검증

| 항목 | 결과 |
| --- | --- |
| colcon 빌드 | `trnav_2ws_interfaces`·`trnav_2ws_action_server`·`line_vision` 오류 0 |
| gtest | **19 passed** |
| pytest | **53 passed** (`line_vision` 17 · `line_sim_sensor` 22 · `line_webview` 14) |
| 주석 검사기 | 20파일 **불일치 0** |
| 표 갱신 | 앵커 재동기 + `require_motion_source_` 행 + status `−12`·`−13` 등재(루트 정본·패키지 병기) |

**미검증**: 재적용본 기준 SIL 재실행. 다음 작업이다 — D 항 수정이 거동을 바꾸므로
`steer_rate_limit` 스윕부터 다시 잰다.

최종 verdict 는 저자가 찍지 않는다 (`coding.md:89` never-self-approve).
