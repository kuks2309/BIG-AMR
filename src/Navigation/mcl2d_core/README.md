# mcl2d_core

Seer `libMCLoc.so`의 **2D 레이저 파티클필터 MCL(Monte Carlo Localization) 모드**를 리버스 엔지니어링으로 복원해 재구현한 **프레임워크-독립 순수 C++17 코어**(외부 의존성 0). ROS2/non-ROS2 어댑터가 이 코어를 공유한다.

> 범위 주의: 원본 다중모달 플러그인(2D PF + 3D + 반사판 + 태그 + SLAM) 전체가 아니라 **2D 레이저 파티클필터 모드만**이다.

## 알고리즘 (RE 실측 충실 재현)
- **예측(kMove)**: 결정론적 오도 증분 **적용만**. 산포 없음 — 원본 노이즈 항이 `supplyControlVar` 2번째 인자
  `d` 에 비례하는데 호출지 2곳 모두 `d=0.0` 이라 소멸한다(2026-07-31 디스어셈블 실측).
- **산포(kExtraMove)**: 별도 액션. x·y 각각 **독립** `U(−0.5,+0.5)·radius`, θ 는 `U(−0.5,+0.5)·angle`.
  크기는 매 주기 **6개 모드**로 재선택한다(이동량·회전량·신뢰도 3축 → `selectExtraMove()`).
  근거·모드표: [ADR](../../../docs/adr/2026-07-31-mcl2d-motion-model-fidelity.md) ·
  [대조 문서 §1.1](../../../docs/comparison/seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md)
- **우도(충실·비트일치)**: `ObservationField` — 원본 `QuadGridSearchMap` 관측모델 충실 포팅. mm 프레임·flat 거리장(dx²+dy²)·`gauss[100·d]=trunc(255·exp(−d))`·`weight = Σ gauss·wtab / valid_beam / 255`. **원본 getPostProb 과 비트 일치(245/245 Δ=0)**.
- **리샘플**: systematic(low-variance) — 단일 난수 u₀ + 균등 stride.
- **적응표본**: `n = (점유 (x,y,θ) bin 수) × 2.5`, clamp[min,max].
- **추정**: 가중평균(위치) + 원형평균(각).

> **관측 모델 = `ObservationField`(충실·RE 비트일치, 정본)**. `ParticleFilter2D` 가 이를 사용(2026-07-13 이관 완료 — 단일/듀얼 라이다 원본 대조 245/245·125/125 Δ=0). 레거시 `LikelihoodGrid`/`observation_model` 은 이제 `loc_verification` 오라클 스캐폴딩만 참조(코어 미사용, 제거는 별도 cleanup).

근거: [docs/reverse_engineering/libMCLoc/2026-06-24-localization-deep-dive.md](../../docs/reverse_engineering/libMCLoc/2026-06-24-localization-deep-dive.md) (§6.5 분석 백로그 해소). 설계: [docs/adr/2026-06-24-mcl2d-core.md](../../docs/adr/2026-06-24-mcl2d-core.md), [관측 우도 충실 포팅 ADR](../../docs/adr/2026-07-12-obs-likelihood-faithful-port.md).

## 빌드 / 테스트
```bash
# 정상 환경(cmake 동작 시):
cmake -S . -B build && cmake --build build && ctest --test-dir build

# 현재 호스트는 시스템 cmake 가 libssl.so.1.1 누락(debt-011) → g++ 직접 빌드:
g++ -std=c++17 -O2 -Iinclude src/*.cpp test/test_mcl2d.cpp -o test_mcl2d && ./test_mcl2d
```
검증: 합성 사각형 방에서 직진 시뮬레이션 → 추정 오차 < 0.3m (실측 ~수mm 수렴).

## 구조
- `types.hpp` — Pose2D, Particle, LaserScan, Mcl2dParams(기본값=robot.param 실측)
- `observation_field.*` — **관측 우도 충실 포팅**(원본 QuadGridSearchMap, RE 비트일치). build(맵)→setScan(스캔)→getPostProb(자세)
- `likelihood_grid.*` — 레거시 우도장(거리→가우시안 PDF 0~255, PF 행동 시뮬용 근사)
- `motion_model.*` — 균등 산포 예측
- `observation_model.*` — 빔 우도(레거시 LikelihoodGrid 기반)
- `particle_filter.*` — PF 파이프라인
- `test/test_obs_field_oracle.cpp` — RE 검증(원본 dlopen, `ObservationField` ↔ 원본 getPostProb Δ=0)

## 알려진 부채
[docs/debt/registry.md](../../docs/debt/registry.md) debt-011(cmake), debt-012(거리변환 브루트포스), debt-013(단일 레이저·PF 모드만).
