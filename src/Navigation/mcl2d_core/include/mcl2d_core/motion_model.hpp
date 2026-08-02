// 모션모델 — Seer MCLMotionModel2D 재구현 (원본 디스어셈블 대조, 2026-07-31).
//
// 원본은 "결정론적 이동"과 "산포"를 **서로 다른 액션**으로 분리한다
// (ParticleFilter2D::Whats2Run 의 kMove / kExtraMove — ThreadFunc1/2 가 switch 로 택일):
//   - kMove      : doParticleMoveAction @0x33cb70 — 오도 증분만 적용. 노이즈 스케일이
//                  supplyControlVar 2번째 인자 d 에 비례하는데 호출지 2곳 다 d=0.0 이라 노이즈 소멸.
//   - kExtraMove : doExtraMove @0x33cca0 — x·y 각각 독립 균등 + theta 균등(정사각형 산포).
// 근거: docs/comparison/seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md §1.1~§1.1.2,
//       ADR docs/adr/2026-07-31-mcl2d-motion-model-fidelity.md
#ifndef MCL2D_CORE_MOTION_MODEL_HPP
#define MCL2D_CORE_MOTION_MODEL_HPP

#include <random>

#include "mcl2d_core/types.hpp"

namespace mcl2d
{

// 오도 두 시점 → 로봇좌표 증분 (Seer supplyControlVar @0x33ce70).
//   Δx_b = Δx·cosθ_prev + Δy·sinθ_prev, Δy_b = Δy·cosθ_prev − Δx·sinθ_prev 로 분해한 뒤
//   trans=hypot, direction=atan2(Δy_b, Δx_b), dtheta=normalize(Δθ).
ControlIncrement2D supplyControlVar(const Pose2D &prev_odom, const Pose2D &cur_odom);

// kMove — 결정론적 이동 (Seer doParticleMoveAction). 노이즈 없음(원본 d=0 실측).
void doParticleMove(Particle &p, const ControlIncrement2D &c);

// kExtraMove — 산포 (Seer doExtraMove). x·y 는 같은 반폭의 **독립** 난수, theta 는 별도 반폭.
//   난수는 원본과 동일한 이산 균등: RangeRandom(-1000,1000) / 2000.0 = U{-0.5 .. +0.5}.
void doExtraMove(Particle &p, const ExtraMoveParams &e, std::mt19937 &rng);

// 산포 크기 선택 (Seer MCLoc::DoNormalUpdateAction 의 모드 결정 트리, CFG 추적으로 복원).
//   trans/dtheta = 직전 산포 시점 이후 이동량·회전량, likelihood = 새 스캔 기준 현재 추정 자세의 우도.
//   모드 6(멤버 오버라이드)은 원본에서도 writer 가 없어 미발동이므로 이식하지 않는다.
ExtraMoveParams selectExtraMove(double trans, double dtheta, double likelihood, const Mcl2dParams &params);

// 각도 정규화 [-pi, pi)
double normalizeAngle(double a);

} // namespace mcl2d

#endif // MCL2D_CORE_MOTION_MODEL_HPP
