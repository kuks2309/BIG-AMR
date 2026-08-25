# ADR 2026-08-24 — 노드(경유점) 정의와 노드 간 주행 실행기

- **Status**: Accepted — 2026-08-24 (사용자: "도킹 전에 주행이 진행되어야 합니다.
  translate 는 이미 검증했지만, node 를 정의하고 그 node 간의 주행은 아직 — 진행")

## Context (사전조사 실측)

- **노드는 이미 정의돼 있다** — Seer smap `advancedPointList` 에 LocationMark 4개
  (LM1(−15.93, 2.41)·LM2(−15.93, 15.57)·LM3(−11.71, 15.57)·LM4(−11.99, 2.41, dir=π)) +
  `advancedCurveList` 에 StraightPath 간선 6개. RViz 의 SmapNodes(오렌지 구)가 이것.
- **주행 부품은 검증된 액션으로 존재** — `AMRMotionSpin`(상대각 제자리 회전)·
  `AMRMotionCrabLinear`(map 프레임 start→end 직선 closed-loop + target_yaw 유지).
- **자세 브리지도 존재** — 액션들은 `/robot_pose`(PoseStamped)를 소비하는데 mcl2d 는
  `/mcl_pose`(PoseWithCovarianceStamped)만 발행. `src/Sim/sil_pose_adapter` 가 정확히
  그 타입 변환기이며 입력 토픽 리맵(`/rtabmap/localization_pose:=/mcl_pose`)으로 재사용
  가능(debt-068 의 실기 `/robot_pose` 발행자 공백을 이 조합이 메운다).
- SIL 자산: `sil_spin.launch.py`·`sil_crab_linear.launch.py` + 공유 플랜트
  (`translate_sim_odom`+`sil_pose_adapter`) — 무모터 검증 가능.

## Decision

**신규는 경로 실행기 1개** — `Tools/waypoint_nav/run_route.py` (rclpy, python3 직접 실행):

1. **노드 소스**: smap `advancedPointList` 파싱(기본) 또는 `--nodes-yaml` 오버라이드.
2. **레그 실행**(노드마다): 현재 `/robot_pose` → ① 진행 헤딩과의 차가 `spin_tol`(기본 5°)
   초과면 `AMRMotionSpin`(상대각) ② `AMRMotionCrabLinear`(start=현재, end=노드,
   target_yaw=진행 헤딩) ③ 마지막 노드는 옵션으로 노드 `dir` 로 최종 spin 정렬.
3. **실패 규약**: 액션 status ≠ 0 이면 경로 중단(다음 레그 진행 금지), 결과 요약 출력.
4. `--dry-run`: 액션 전송 없이 레그 계획(회전각·거리·헤딩)만 출력.
5. 검증: SIL(공유 플랜트 + spin·crab 서버 동시 기동 + 가상 노드 3개 경로) → 실기
   (mcl2d + sil_pose_adapter 리맵 브리지, **실모터는 사용자 승인 후**).

도킹과의 결합(후속): 경로 마지막 노드 = 도킹 스테이션 진입점 → `AMRMotionDockApproach`
호출이 이어지는 시퀀스 — 노드 주행 실기 검증 후 별도 단계로.

## Consequences

- 이득: 신규 제어 코드 0 — 검증된 액션의 조립. 노드 정의는 현장 smap 재사용.
- 비용: 실행기 1본 + 기록. mcl2d 기반 주행 정밀도는 cm 급(측위 한계) — 도킹 진입점
  허용오차는 wall_localizer 초기 게이트(±0.3 m/±10°) 안이면 충분하므로 성립.
- 남는 위험: ① spin 의 실기 검증 이력은 turn 대비 얕음 — HIL 저속 확인 ② smap 노드
  좌표는 Seer 맵 기준 — mcl2d 도 같은 맵을 쓰므로 정합하나, 맵 갱신 시 재확인.

## Rollback

N/A (가역) — 도구 1본 추가, 기존 코드 무변경.
