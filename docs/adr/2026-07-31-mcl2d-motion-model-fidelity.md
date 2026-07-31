# ADR 2026-07-31 — mcl2d 모션모델을 원본(libMCLoc) 구조와 동일하게 재작성

## Status

Accepted (2026-07-31). 구현·회귀시험 완료, 최종 verdict 는 외부 리뷰 몫(coding SOP §5 never-self-approve).

## Context

`src/Navigation/mcl2d_core` 는 Seer `libMCLoc.so`(rbk 3.4.5.20) 2D 위치추정의 재구현이다.
리버스 엔지니어링(Reverse Engineering) 제1원칙은 **"재구현 입출력은 원본과 100% 동일, 비슷함은 실패"**
([principle.md §0](../claude_guideline/reverse_engineering/principle.md)).

2026-07-31 원본 바이너리를 직접 디스어셈블한 결과(근거 전문:
[docs/comparison/seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md](../comparison/seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md),
1차 산출물 `references/seer/libMCLoc/*.asm`), 기존 이식본의 모션모델은 원본과 **구조가 달랐다**:

| 항목 | 원본 (실측) | 이식본(기존) |
| --- | --- | --- |
| 예측(`kMove`) | 결정론적 오도 적용. 노이즈 스케일이 `supplyControlVar` 2번째 인자 `d` 에 비례하는데 **호출지 2곳 다 `d=0.0`** → 노이즈 항 소멸 | 예측 안에 등방 디스크 산포 혼입 |
| 산포 | **별도 액션 `kExtraMove`**(`doExtraMove`) — x·y 독립 균등 + θ 균등 | 별도 액션 없음 |
| 산포 크기 | 매 스캔 주기 **6개 모드**로 재선택(이동량·회전량·**신뢰도** 3축) | 고정 `move_radius`·`extra_move_angle` |
| 난수 | `RangeRandom(−1000,1000)/2000` = 정수 균등 `U(−0.5,+0.5)` | `U(0,1)` 반경 + `U(0,2π)` 방향 |
| 실행 주기 | 2-rate: 예측은 odom 콜백(`DoMoveAction`), 산포+보정은 스캔 주기(`DoNormalUpdateAction`) | 단일 경로 |
| 정지 | `cv.is_stop` 이면 `kMove` 자체를 건너뜀(`DoMoveAction` @0x3d7d13) | `is_stop` 미배선 |

기존 구조는 근거였던 분석 문서 `deep-dive §6.5②` 의 "디스크 산포" 서술을 따른 것인데,
그 서술 자체가 원문 대조에서 반증됐다(두 난수는 반지름·방향이 아니라 병진·회전 노이즈였고,
그나마 `d=0` 으로 죽어 있다).

## Decision

모션모델을 원본의 **함수 분해와 실행 순서 그대로** 재작성한다.

1. `supplyControlVar(prev, cur)` — 오도 증분을 로봇좌표로 분해해 `{trans, direction, dtheta}` 반환
   (원본 멤버 `m[0x98]`·`m[0xa0]`·`m[0x90]`).
2. `doParticleMove(p, c)` — **결정론**. `R=c.trans`, `Φ=p.θ+c.direction`, `x+=R·cosΦ`, `y+=R·sinΦ`,
   `θ=normalize(θ+c.dtheta)`. 노이즈 없음(`d=0` 실측).
3. `doExtraMove(p, e, rng)` — 산포. x·y 에 **각각 독립** `U(−0.5,+0.5)·e.radius`, θ 에 `U(−0.5,+0.5)·e.angle`.
   난수는 원본과 같은 이산 균등(`uniform_int_distribution(−1000,1000)/2000.0`).
4. `selectExtraMove(trans, dtheta, likelihood, params)` — 원본 `DoNormalUpdateAction` 의 6모드 결정 트리.
5. `ParticleFilter2D` 에 `extraMove()` 추가, `predict()` 는 결정론 전용으로 축소, `applyScan`/`likelihoodAt` 공개
   (모드 판정이 **새 스캔 기준 우도**를 요구하므로 — 원본과 같은 순서).
6. `Mcl2dLocalizer::update()` 가 원본 `MCLoc` 역할로 순서를 조립:
   `스캔 적용 → 직전 추정 자세의 우도 w → 모드 선택 → predict(kMove, is_stop 이면 생략) → extraMove → 우도갱신 → 추정 → 리샘플`.
7. 기존 `applyMotion()` 은 **삭제**한다(원본에 대응물이 없는 합성 함수).

파라미터는 원본 배포값(robot.param 실측)으로 `Mcl2dParams` 에 추가:
`extra_move_dist_threshold`(20 mm) · `extra_move_angle_threshold`(1°) · `best_particle_tolerant_threshold`(0.8) ·
`low_speed_move_radius`(10 mm) · `low_speed_move_angle`(1°) · `force_extra_move`(false) ·
`force_extra_move_dist`(10 mm) · `force_extra_move_angle`(2°).

## Consequences

- **이득**: 산포가 이동량·회전량·신뢰도에 따라 적응한다(원본 동작). 정지 중 무의미한 확산이 사라진다.
  이후 원본 대조 오라클을 붙일 때 함수 경계가 1:1 이라 비교 단위가 생긴다.
- **비용**: 공개 표면 변경 — `applyMotion` 삭제, `predict` 의미 변경, 파라미터 8개 추가.
  `mcl2d_core`·`Tools/mcl2d_standalone`(파사드·데모)·`mcl2d_ros2` 노드가 동반 수정된다.
- **남는 위험**: 모드 판정에 쓰는 `w`(우도)의 스케일이 원본과 같은지는 미검증 —
  원본은 `getParticleLikelihood`(0~1 정규화 여부 미확인), 우리는 `ObservationField::getPostProb`.
  임계 `0.8` 이 우리 스케일에서 같은 의미인지는 실기 데이터로 재확인 필요 → 부채로 등록.
- 모드 6(`m[0x19e0]/m[0x19e8]` 오버라이드)은 원본에서도 writer 가 0 이라 미발동 — 포팅하지 않는다(주석으로 명시).

## Rollback

가역. `git revert` 로 되돌린다(영속 상태·스키마·펌웨어 변경 없음).
되돌릴 경우 `motion_model.{hpp,cpp}`·`particle_filter.{hpp,cpp}`·`types.hpp`·
`Tools/mcl2d_standalone/{include,src}/mcl2d_localizer.*`·`test_mcl2d.cpp` 가 이전 커밋 상태로 복귀하며,
빌드·테스트는 변경 전 상태에서 그대로 통과한다(외부 자산 의존 없음).
