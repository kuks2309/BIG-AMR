#ifndef TRNAV_QD_KINEMATICS__QD_CRAB_INVERSE_KINEMATICS_HPP_
#define TRNAV_QD_KINEMATICS__QD_CRAB_INVERSE_KINEMATICS_HPP_

#include <cstddef>

#include "trnav_qd_kinematics/qd_inverse_kinematics.hpp"

namespace trnav::motion::qd
{

// QdCrabIK — CRAB linear 전용 IK (rear-steer heading 보정 지원).
//
// 표준 DualSteerIK 는 atan2(vy,vx) + ±90° normalize 를 사용. CRAB sideways
// (|theta_body| ≈ 90°) 영역에서는 작은 δ_cte 변화가 normalize edge 를 넘어
// wheel steer 가 +88° ↔ -88° 점프하고 walk direction 부호가 반전됨.
//
// 본 클래스는 (theta_body + delta_cte) 를 base steer 로 사용하여 atan2 없이
// 직접 출력. 또한 rear wheel 만 delta_heading 만큼 추가 offset 하여 robot 의
// yaw 능동 보정을 만든다 (bicycle-like rear-steer).
//
// 가정:
//  - num_wheels = 2, wheels[0]=W1 (front-left, w1_x>0), wheels[1]=W2 (rear-right, w2_x<0)
//  - dir>0 (정방향): rear = W2 (wheels[1])
//  - dir<0 (역방향): rear = W1 (wheels[0])  — walk 진행 방향 기준 뒤
//  - rear_steer_offset = -dir × delta_heading  (시뮬레이션으로 부호 검증)
//  - walk direction 은 vx_path 부호 (+ wrap 시 wheel 별 flip 가능)
//  - wheel speed 양 휠 동일 |vx_path|
class QdCrabIK
{
  public:
    QdCrabIK(std::size_t num_wheels, double wheel_radius, double gear_walk);

    // Phase 0 (alignment) 끝나는 시점에 1회 호출 — Phase 0 의 wheel steer 결정값 +
    // walk direction 결정값을 state 로 저장. 이후 compute() 가 본 state 기준 ±25°
    // 안에서만 변화하고 walk dir 은 고정.
    //
    // 1단계 (Phase 0): ±π/2 strict wrap (DualSteerIK) 으로 부호 결정. setInitial 호출.
    // 2단계 (Phase 1-3 cruise): compute() 가 state 기준 clamp + dir 고정.
    void setInitial(double initial_base_steer, int initial_walk_dir);

    // initial 미설정 시 false. cruise 진입 전 setInitial 호출 권장.
    bool isInitialized() const { return initialized_; }

    // vx_path        : path 진행 속도 (m/s, + forward / - reverse)
    // theta_body     : path_yaw - robot_yaw (rad)
    // delta_cte      : CTE 보정 각 (rad). 호출자가 적절히 saturate.
    // delta_heading  : heading 보정 각 (rad) — rear wheel offset 용. 호출자가 saturate.
    //
    // initialized 시: base_raw = theta_body + delta_cte 를 [initial-25°, initial+25°] clamp.
    //   walk dir 은 initial_walk_dir 고정 (wrap 없음). rear wheel offset 적용 후 clamp 동일.
    // 미초기화 시: 기존 wrap (±π/2 + 25°) 동작 (legacy fallback).
    IKResult compute(double vx_path, double theta_body, double delta_cte,
                     double delta_heading = 0.0) const;

  private:
    std::size_t num_wheels_;
    double wheel_radius_;
    double gear_walk_;

    // Phase 0 결정 state (cruise 기준)
    double initial_base_steer_{0.0};  // wrap 후 wheel steer (DualSteerIK 결과, ±π/2)
    int initial_walk_dir_{1};         // wrap 후 walk dir (±1)
    bool initialized_{false};
};

} // namespace trnav::motion::qd

#endif // TRNAV_QD_KINEMATICS__QD_CRAB_INVERSE_KINEMATICS_HPP_
