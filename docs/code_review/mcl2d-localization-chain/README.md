# mcl2d 위치추정 구동 체인 — 리뷰 타임라인

휠 오도메트리 없이 2D 라이다만으로 자세를 추정하는 경로 전체
(`icp_odometry_bringup` → `mcl2d_ros2` ← `mcl2d_map` / `Tools/mcl2d_standalone`)를 대상으로 한다.

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| [2026-08-07](2026-08-07.md) | `8462c75` (main) | REQUEST CHANGES | High 2 — `base_link` 부모 2개(TF 트리 충돌)·`map_path` 미지정 시 원점 무단 발행 |

## 인접 리뷰

- [mcl2d-motion-model/2026-07-31](../mcl2d-motion-model/2026-07-31.md) — `mcl2d_core` 모션모델
  재작성분과 그 소비자. 본 리뷰의 범위 밖인 코어는 그쪽을 cross-ref 한다.
- [trnav-icp-odometry/2026-07-28](../trnav-icp-odometry/2026-07-28.md) — 이식 원본(TR_Nav)의
  `icp_odometry` 설정 리뷰. 본 체인의 `icp_odometry_bringup` 이 그 결과물이다.

## 패키지 병기 생략 사유

리뷰 대상이 **4패키지 횡단**(`src/Navigation/` 3개 + `Tools/` 1개)이라 단일 패키지 루트를
특정할 수 없다. SOP §기록 위치의 "패키지 루트를 특정할 수 없을 때 → 루트 정본만 기록(병기 생략)"
을 적용했다.

## 관련 자산

- 흐름도: [2026-08-07-flow.drawio](2026-08-07-flow.drawio) (박스 7 / 화살표 8)
- 설계 근거: [docs/adr/2026-07-28-icp-odometry-bringup.md](../../adr/2026-07-28-icp-odometry-bringup.md)
