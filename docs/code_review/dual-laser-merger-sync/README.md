# dual_laser_merger 쌍 동기화 — 리뷰 타임라인

정본: `docs/code_review/dual-laser-merger-sync/` · 병기: `src/Sensors/Lidar/2D/dual_laser_merger/docs/code_review/dual-laser-merger-sync/`

대상: `src/Sensors/Lidar/2D/dual_laser_merger/` — 두 SICK 2D 라이다를 `ApproximateTime` 으로
짝지어 `/scan_merged` 로 내는 composable 노드. 본 리뷰의 초점은 **쌍의 시각 어긋남(skew)** 이다.

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| [2026-08-08](2026-08-08.md) | `4dfb626` + uncommitted (수정 후 `dual_laser_merger.cpp` md5 `48c90146`) | REQUEST CHANGES → 수정 완료 | **최초 리뷰.** High 3(검증 사문화 · `/cloud_merged` frame_id 불일치 · 진단 침묵/허위) 전부 해결, Medium 8 중 4 해결. 실기 재검증 통과 |

- 병행 리뷰(검사 도구): `docs/code_review/lidar-merger-sync-check/`
- 배경·실측: `docs/issues_and_fixes/issues_and_fixes.md` 2026-08-08 항목
- 실기 실측 요약: skew 는 `0.48 ms ↔ 14.21 ms` 를 **주기 260 s** 로 왕복(자유구동 두 스캐너의 맥놀이),
  역위상 정점에서 `pairs/s` 34.05 → 29.47

⚠ **`APPROVE` 는 아직 없다** — SOP 룰 11(작성자 self-APPROVE 금지). 수정본을 별도 lane 이 확인해야 한다.
