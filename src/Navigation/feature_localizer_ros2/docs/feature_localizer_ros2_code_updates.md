# feature_localizer_ros2 code updates

## 2026-09-02 — wall_* → feature_* 전면 개명

패키지·노드·토픽·파라미터·심볼 개명(동작 불변). 결정 정본:
docs/adr/2026-09-02-feature-localizer-rename.md, 전체 매핑·검증은 루트
code_updates/2026-09-02-feature-localizer-rename.md.

## 2026-09-05 — 개명 누락분 정리 (세션 67ed5a48)

2026-09-02 전면 개명이 코드·설정에서는 완결됐으나 **마크다운이 아닌 파일**과 루트 인덱스에 옛 이름이 남아 있었다(사용자 지적).

| 대상 | 내용 |
|---|---|
| `trnav_2ws_interfaces/action/AMRMotionDockApproach.action` | 헤더·관측 설명·`target_x_m` 주석의 `/wall_pose`·`wallPoseToDockObs`·`wall_localizer` → `/feature_pose`·`featurePoseToDockObs`·`feature_localizer`. 인터페이스 정의라 이용자가 처음 읽는 문서다 |
| `trnav_2ws_dock_ros/src/dock_approach_action_server.cpp` | `arm_engage_dist_m` 주석의 "wall 관측" → "특징면 관측" |
| `docs/reports/2026-08-25-dock-precision-report.html` | 본문 4곳 |
| `docs/sw_structure/function_table.md` | 등재 2행이 존재하지 않는 `wall_localizer_*` 경로를 가리켜 **링크가 깨져 있었다** → 실제 경로로 교정, 표 전체 링크 재확인(깨짐 0) |

검증: `colcon build --packages-select trnav_2ws_interfaces` 성공(액션 정의 문법·생성 코드 유효), 링크 검사 통과.
**남긴 것**: `code_updates/`·`docs/adr/`·`docs/code_review/` 의 2026-08-19~08-27 기록과 개명 ADR 자체는 그 시점 사실이므로 고치지 않는다.

