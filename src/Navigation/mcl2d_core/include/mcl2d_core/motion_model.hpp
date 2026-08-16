// 모션모델 — Seer libMCLoc 의 MCLMotionModel2D 재구현.
//
// 원본은 "결정론적 이동"과 "산포"를 서로 다른 액션으로 분리하고 파티클마다 **택일** 실행한다
// (ParticleFilter2D::Whats2Run 의 kMove / kExtraMove).  comment-check: ignore
//   kMove      — 오도 증분만 적용. 원본의 노이즈 항은 supplyControlVar 2번째 인자 d 에 비례하는데
//                호출지가 전부 d=0.0 이라 소멸한다. 그래서 여기서는 노이즈 항 자체를 두지 않는다.
//   kExtraMove — x·y 각각 독립 균등 + theta 균등. 원형이 아니라 **정사각형** 산포다.
//
// 좌표·단위: 자세는 map 프레임 (x, y) 미터 · theta 라디안. 원본 내부는 mm 이지만 여기 식은
//   순수 기하라 단위에 불변이며, 우도장·파라미터가 모두 미터라 미터로 통일한다.
#ifndef MCL2D_CORE_MOTION_MODEL_HPP
#define MCL2D_CORE_MOTION_MODEL_HPP

#include <random>

#include "mcl2d_core/types.hpp"

namespace mcl2d
{

// 오도 두 시점 → 로봇좌표 증분 (원본 supplyControlVar @0x33ce70).
//   Δx_b = Δx·cosθ_prev + Δy·sinθ_prev  (로봇 전방 성분)
//   Δy_b = Δy·cosθ_prev − Δx·sinθ_prev  (로봇 좌측 성분)
//   → trans = hypot(Δx_b, Δy_b) [m] · direction = atan2(Δy_b, Δx_b) [rad, 직전 헤딩 기준 상대각]
//     dtheta = normalizeAngle(Δθ) [rad]
// 오도의 **절대 자세는 쓰지 않는다** — 차분만 취하므로 오도 드리프트가 추정 자세로 전파되지 않는다.
ControlIncrement2D supplyControlVar(const Pose2D &prev_odom, const Pose2D &cur_odom);

// kMove — 결정론적 이동. 이동 방향을 파티클 자신의 헤딩 기준으로 재투영해 적용한다.
//   난수를 쓰지 않으므로 같은 입력이면 항상 같은 결과다.
void doParticleMove(Particle &p, const ControlIncrement2D &c);

// kExtraMove — 산포. x·y 는 같은 반폭의 **독립** 난수, theta 는 별도 반폭.
//   e.radius·e.angle 은 1σ 가 아니라 **반폭**이다 — 난수가 U(−0.5, +0.5) 이므로 실제 범위는 ±e/2.
void doExtraMove(Particle &p, const ExtraMoveParams &e, std::mt19937 &rng);

// 산포 크기 선택 (원본 MCLoc::DoNormalUpdateAction 의 모드 결정 트리).  comment-check: ignore
//   trans [m] · dtheta [rad] = **직전 산포 판정 이후 누적** 이동량 (주기당 증분이 아니다 —
//     스캔이 오도보다 느릴 때 이동량이 과소평가돼 최소 산포로 치우치는 것을 막는다).
//   likelihood = 새 스캔 기준 현재 추정 자세의 관측 우도.
// 많이 움직였는데 신뢰도가 낮으면 넓게, 신뢰도가 높거나 거의 안 움직였으면 좁게 뿌린다 —
//   오도 증분이 클수록 그 주기의 오차 가능성도 크므로 관측이 교정할 여지를 그만큼 연다.
// 원본의 모드 6(멤버 오버라이드)은 원본에도 writer 가 없어 발동하지 않으므로 이식하지 않는다.
ExtraMoveParams selectExtraMove(double trans, double dtheta, double likelihood, const Mcl2dParams &params);

// 각도 정규화 → [−π, π). 원본 libfoundation 의 Normalize 와 같은 while 루프 방식이다
//   (floor 기반 환산은 경계에서 1 ulp 어긋난다).
double normalizeAngle(double a);

} // namespace mcl2d

#endif // MCL2D_CORE_MOTION_MODEL_HPP
