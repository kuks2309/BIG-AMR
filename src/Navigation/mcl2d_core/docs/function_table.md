# mcl2d_core 함수표 — 모션모델 (모듈 로컬 권위본)

> 대상: 2026-07-31 원본 충실 재작성분(ADR `docs/adr/2026-07-31-mcl2d-motion-model-fidelity.md`).
> 범위는 `motion_model.*` 와 그 소비자(`particle_filter`·파사드)로 한정한다 — 코어 전체 인벤토리는
> `code_review` SOP 소관의 별도 작업이며 아직 없다(coding SOP §2 의 "표 부재" 상태를 이 파일이 부분 해소).

## 공개 함수 (motion_model.hpp)

| 함수 | 입력 | 출력 | 원본 대응 | 부작용 |
| --- | --- | --- | --- | --- |
| `supplyControlVar(prev_odom, cur_odom)` | 오도 절대 자세 2시점(m·rad) | `ControlIncrement2D{trans, direction, dtheta}` | `MCLMotionModel2D::supplyControlVar` @0x33ce70 | 없음(순수) |
| `doParticleMove(p, c)` | 파티클, 증분 | — (`p` 갱신) | `doParticleMoveAction` @0x33cb70 | `p.pose` 변경. **결정론** |
| `doExtraMove(p, e, rng)` | 파티클, 산포크기, 난수원 | — (`p` 갱신) | `doExtraMove` @0x33cca0 | `p.pose` 변경, `rng` 상태 소비(3회) |
| `selectExtraMove(trans, dtheta, likelihood, params)` | 이동량·회전량·우도·파라미터 | `ExtraMoveParams{radius, angle, mode}` | `MCLoc::DoNormalUpdateAction` 모드 트리 | 없음(순수) |
| `normalizeAngle(a)` | rad | rad ∈ [−π, π) | `rbk::foundation::utils::Normalize` | 없음(순수) |

### `selectExtraMove` 결정 트리 (원본 배포값 기준)

| 조건 | mode | radius | angle |
| --- | --- | --- | --- |
| `trans>20mm` · `\|dθ\|>1°` · `w<0.8` | 1 | `extra_move_radius` 40mm | `extra_move_angle` 3° |
| `trans>20mm` · `\|dθ\|≤1°` | 2 | `extra_move_radius` 40mm | 고정 2° |
| `trans≤20mm` · `\|dθ\|>1°` · `w<0.8` | 3 | `move_radius` 10mm | `extra_move_angle` 3° |
| `trans≤20mm` · `\|dθ\|≤1°` | 4 | `low_speed_move_radius` 10mm | `low_speed_move_angle` 1° |
| `\|dθ\|>1°` · `w≥0.8` (거리 무관) | 5 | `force_extra_move` ? `force_extra_move_dist` : 고정 10mm | `force_extra_move_angle` 2° |

원본 모드 6(멤버 오버라이드)은 원본에서도 writer 가 없어 미발동 — 이식하지 않음.
`w`(우도) 스케일 정합은 미검증 → `docs/debt/registry.md` **debt-031**.

## 변경된 소비자

| 위치 | 변경 | 비고 |
| --- | --- | --- |
| `ParticleFilter2D::predict` | 산포 제거, `supplyControlVar`+`doParticleMove` 로 결정론화 | 시그니처 불변 |
| `ParticleFilter2D::extraMove` | **신규** — 전 파티클에 `doExtraMove` | — |
| `ParticleFilter2D::applyScan`·`likelihoodAt` | private → **public** | 모드 판정이 새 스캔 기준 우도를 요구(원본 순서) |
| `ParticleFilter2D::step` | 순서 교체: 스캔적용 → 우도 → 모드선택 → predict → extraMove → 우도갱신 → 추정 → 리샘플 | — |
| `Mcl2dLocalizer::update` | 위 순서를 조립. `stopped` 면 `predict` 생략 | 원본 `DoMoveAction` @0x3d7d13 의 `is_stop` 분기 |
| `Mcl2dLocalizer::lastExtraMove()` | **신규** 접근자 | 진단용(원본 `MCLocUpdateMode` 로그 대응) |

## 삭제된 함수

| 함수 | 사유 |
| --- | --- |
| `applyMotion(p, prev, cur, params, rng)` | 원본에 대응물이 없는 합성 함수(예측+산포 혼합). 호출처는 `ParticleFilter2D::predict` 1곳뿐이었다 |

## 전역변수

없음(모듈 전역 0). 난수 상태는 `ParticleFilter2D::rng_` 인스턴스 멤버.
