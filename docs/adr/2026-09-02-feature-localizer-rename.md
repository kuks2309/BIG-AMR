# ADR: wall_localizer → feature_localizer 전면 개명

- 날짜: 2026-09-02
- 상태: 채택 (사용자 지시 "feature_localizer 로 정해서")
- 관련: docs/adr/2026-08-18-wall3-precision-localizer.md (원 설계)

## 배경

wall_localizer 는 "벽 3면" 기준 측위로 출발했지만 실운용의 기준면은 벽이
아니었다 — 2026-08-27~28 실기에서 정본 티치는 사용자가 RViz 에서 지정한
임의 직선 특징점(윗벽 구간 + 도킹 구조물 면, σ 0.5 mm)이었고, 티치 도구도
임의 ROI(Region of Interest)의 직선 피처를 추출한다. 이름이 실체(직선 특징
기반 측위)보다 좁고, 반사판 등 피처 확장 여지도 이름이 막는다.

## 결정

패키지·노드·토픽·파라미터 키·도구·티치 자산을 feature_* 로 전면 개명한다.

| 구 이름 | 새 이름 |
| --- | --- |
| `wall_localizer_core` / `wall_localizer_ros2` (패키지) | `feature_localizer_core` / `feature_localizer_ros2` |
| `wall_localizer_node` (노드 `wall_localizer`) | `feature_localizer_node` (노드 `feature_localizer`) |
| `/wall_pose` · `/wall_localizer/diagnostics` | `/feature_pose` · `/feature_localizer/diagnostics` |
| `wall_names` · `walls.<name>` (파라미터) | `feature_names` · `features.<name>` |
| 코어 심볼 `WallLocalizer`·`WallMatch`·`WallRef`·`WallFit` 등 | `Feature*` 동형 |
| `Tools/wall_teach/teach_walls.py` · `walls_lm1*.yaml` | `Tools/feature_teach/teach_features.py` · `features_lm1*.yaml` |
| `Tools/wall_localizer_sim` · `Tools/dock_sil/walls_sil.yaml` | `Tools/feature_localizer_sim` · `features_sil.yaml` |
| dock 적응층 `wallPoseToDockObs` (dock_obs) | `featurePoseToDockObs` |

## 경계 (바꾸지 않는 것)

- **trnav_2ws_dock_control 의 이식 코어(dock_core.\*)와 golden 자산** — LGIT
  무수정 이식 W1 규약 유지. dock_obs 는 본 저장소 작성 적응층이라 개명 대상.
- **과거 문서의 wall 표기** — 특정 시점 기록 인용은 역사적 사실로 보존
  (저장소 규약). 현행 참조 문서(패키지 내 docs·함수표)만 동반 갱신.
- `station_frame` 개념·티치 좌표계·알고리즘 — 이름만 바뀌고 동작 불변.

## 검증

- 전역 잔존 식별자 0건(grep, golden 제외) 확인 후 빌드·단위시험 전량 통과를
  머지 조건으로 한다. 실기 스모크(왕복 1회)는 로봇 워크스페이스 pull 후 수행.

## 파급

- 로봇 라이브 워크스페이스(공유 트리)는 pull + colcon build 전까지 구 이름으로
  동작한다. UI 스택·teach 정본 경로가 함께 바뀌므로 부분 pull 금지(일괄 갱신).
