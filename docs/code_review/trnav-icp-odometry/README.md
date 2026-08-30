# TR_Nav ICP 오도메트리 스택 — 리뷰 타임라인

Big-AMR 이식 관점에서 외부 저장소 `kuks2309/TR_Nav_ros2_ws` 의 `icp_odometry`(ICP, Iterative Closest Point) 구성을 리뷰한 기록.

| 날짜 | 코드 버전 | Verdict | 핵심 |
| --- | --- | --- | --- |
| [2026-07-28](2026-07-28.md) | `ad7520981d50` (TR_Nav_ros2_ws main, 2026-07-13) | REQUEST CHANGES | High 4 — use_sim_time 기본값 역전(TF 미발행)·Force3DoF 부재(평면에 6DoF ICP)·모션 prior 미적용·ResetCountdown 부재 |

## 대상 코드가 외부 저장소인 점

리뷰 대상 파일은 본 저장소에 없다(다른 워크스페이스의 launch). SOP §기록 위치의 "패키지 루트를
특정할 수 없을 때 → 루트 정본만 기록(병기 생략)" 에 따라 **패키지 병기본은 만들지 않았다.**
이식이 실제로 진행되어 Big-AMR 에 패키지가 생기면, 그 시점의 리뷰부터 해당 패키지에 병기한다.

## 관련 자산

- 흐름도: [2026-07-28-flow.drawio](2026-07-28-flow.drawio) (박스 8 / 화살표 9)
- 원저자 근거 문서: TR_Nav_ros2_ws `docs/plan/2026-07-13_icp_motion_prior.md`, `docs/issues_fixes/issues_and_fixes.md`
- 소비 예정처: [src/Navigation](../../../src/Navigation) 의 `mcl2d_localization_node` (`/odom` 입력)
