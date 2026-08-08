# ADR 2026-08-08 — mcl2d 를 원본과 같은 2-rate 구조로 분리 (오도 전진 ↔ 스캔 보정)

## Status

Accepted (2026-08-08). 구현·회귀시험 완료, 최종 verdict 는 외부 리뷰 몫(coding SOP §5 never-self-approve).
debt-044 상환.

## Context

`debt-044` 는 원본 `MCLMotionModel2D::moveRobotAccordingToMotion`(0x33f4b0) 미이식을 추적해 왔다.
상환계획 ①("원본에서 이 자세가 어디로 나가는지 확인 → 우리 `/mcl_pose` 와 같은 소비자인지 판정")을
2026-08-08 에 원본에서 확인했다.

**원본은 2-rate 구조다** — 주기가 다른 두 경로가 각각 다른 일을 한다:

| 경로 | 진입점 | 하는 일 |
| --- | --- | --- |
| **오도 주기** | `MCLoc::PublishLoc(Message_Odometer)` → `DoMoveAction` / `OdometerMoveAction` | `supplyControlValue(cv, 0.0)` → **`moveRobotAccordingToMotion`(자세를 오도 증분으로 전진)** → `ParticlesAction(kMove)` → `Message_Localization` **발행** |
| **스캔 주기** | `MCLoc::DoNormalUpdateAction()` | 우도 → 모드 선택 → `setExtraMoveParams` → `ParticlesAction(kExtraMove)` → 가중치 갱신 → 추정 → 리샘플 |

근거(실측): `PublishLoc`(0x20b9e0–0x20ce10)이 `Message_Localization` 을 만들어 발행하며
`OdometerMoveAction`·`DoOdoDataProcess` 를 각 1회 호출한다. `kMove` 는 `DoMoveAction` 에만,
`kExtraMove`·`kOffset` 은 `DoNormalUpdateAction` 에만 나타난다(2026-07-31 vtable·호출지 전수 확인).

**우리 이식본은 단일 경로였다** — `/odom` 콜백 하나가 예측·산포·우도갱신·추정·리샘플을 매번 수행하고
파티클 평균을 발행했다. 스캔은 "최신값 캐시"를 재사용하므로 **스캔이 오도보다 느리면 같은 스캔으로
반복 가중**되어(코드리뷰 2026-07-31 D2) 관측 정보가 실제보다 여러 번 반영된다.

## Decision

파사드(`Mcl2dLocalizer`)를 원본과 같은 두 진입점으로 분리하고, ROS2 노드가 그에 맞춰 배선한다.

1. **`advanceWithOdom(prev_odom, cur_odom, stopped)`** — 원본 `DoMoveAction` 대응.
   `stopped` 가 아니면 `predict`(kMove) + **발행 자세(`pose_`)를 같은 결정론 식으로 전진**
   (`doParticleMove` 를 자세 1개에 적용 = 원본 `moveRobotAccordingToMotion`). 스캔을 쓰지 않는다.
2. **`updateWithScan(scans, stopped, dt)`** — 원본 `DoNormalUpdateAction` 대응.
   스캔 적용 → 직전 자세의 우도 → 모드 선택(누적 기준점) → `extraMove` → `updateWeights` →
   `estimate` → `resample`, 그리고 **발행 자세를 파티클 평균으로 재설정**. 슬립·신뢰도 판정도 여기서.
3. 기존 `update(...)` 는 **두 함수를 순서대로 부르는 얇은 래퍼**로 남긴다(하위 호환·단일 구현).
4. ROS2 노드: `/odom` 콜백 → ①만 수행하고 발행. `/scan_front`·`/scan_rear` 콜백에서
   **양쪽 스캔이 새로 갱신됐을 때만** ②를 수행하고 발행. 스캔 재사용이 사라진다.

## Consequences

- **이득**: 같은 스캔이 반복 가중되지 않는다(D2 해소). 발행 주기가 오도 주기를 따라가므로 자세 출력이
  스캔 주기에 묶이지 않는다 — 원본과 같은 시간 특성.
- **비용**: 공개 표면 확장(파사드 메서드 2개 추가), 노드 콜백 구조 변경. 스캔 신선도 플래그 도입.
- **남는 위험**: 스캔이 오래 끊기면 오도만으로 자세가 흘러간다(원본도 동일). 원본은 `ScanLostTimeThresh`
  300 ms 로 게이트하는데 **우리는 그 타임아웃을 이식하지 않았다** — 별도 부채로 등록한다.
- `update(...)` 를 쓰는 기존 호출부(데모·테스트)는 동작이 바뀌지 않는다(두 단계를 연속 수행).

## Rollback

가역. `git revert` 로 되돌린다(영속 상태·스키마·펌웨어 변경 없음).
되돌리면 파사드는 단일 `update()` 경로로, 노드는 `/odom` 콜백 단일 구동으로 복귀하며
빌드·테스트는 변경 전 상태에서 그대로 통과한다(외부 자산 의존 없음).
