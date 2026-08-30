# system_health — 코드 리뷰 타임라인

대상: `src/Safety/system_health/` (AMR 본체 PC 자원·SW 건강 감시, Phase 1 ROS 무의존)

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| [2026-08-09](2026-08-09.md) | sha256 `86477744…` (조치 후) · ADR `2026-08-09-system-health-review-followup` | COMMENT (외부 lane 대기) | 2026-08-07 권고 **15건 전부 [해결]** · 함수표 108행 전수 재도출(현행 앵커 권위본) · 테스트 183 → 220 |
| [2026-08-07](2026-08-07.md) | 리뷰 시점 `origin/main` `757056d` 내용 동일(sha256 `0a3142d8…`) → 주석 정정 21건 후 sha256 `2d4a9af1…` (현재 브랜치 미추적) | REQUEST CHANGES | High 1(임계값 값 미검증 → 재시작 루프) · Medium 5(`--interval` 경계 2 · `--since` 성장률 과대 · 완독 2회 · 절대경로 하드코딩) · 부록 A: 주석 정정 21건(ADR 오귀속 2·미지정 10·근거 누락 1·주석 규율 2·S6 게이트 6) |

- 병기본: `src/Safety/system_health/docs/code_review/system_health/` (동일 내용)
- 동반 흐름도: `2026-08-07-flow-modules.drawio` · `-flow-sampler.drawio` · `-flow-report.drawio` · `-flow-webview.drawio`
- staleness: 리뷰 시점 이후 `src/Safety/system_health/` 변경이 생기면 delta 리뷰로 갱신할 것.
