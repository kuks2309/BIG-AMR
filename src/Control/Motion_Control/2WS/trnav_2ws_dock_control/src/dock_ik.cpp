#include "dock_control/dock_ik.hpp"

#include <cmath>

namespace dock_control
{

SteerHoldIk::SteerHoldIk(const DockGeometry &geom, double hold_below)
    : geom_(geom),
      ik_({{geom.w1_x, geom.w1_y}, {geom.w2_x, geom.w2_y}},
          geom.wheel_radius_m, geom.gear_walk),
      hold_below_(hold_below)
{
}

void SteerHoldIk::resetHold()
{
    have_last_ = false;
    last_af_ = 0.0;
    last_ar_ = 0.0;
}

bool SteerHoldIk::lastSteer(double &af, double &ar) const
{
    af = last_af_;
    ar = last_ar_;
    return have_last_;
}

DockWheelCommand SteerHoldIk::compute(double vx, double vy, double omega)
{
    const auto res = ik_.compute({vx, vy, omega});

    DockWheelCommand cmd;
    // QdDualSteerIK 는 speed(>=0) + direction 으로 내고 정본은 부호 포함 속도를 쓴다.
    cmd.vf = res.wheels[0].wheel_speed * static_cast<double>(res.wheels[0].direction);
    cmd.af = res.wheels[0].steer_rad;
    cmd.vr = res.wheels[1].wheel_speed * static_cast<double>(res.wheels[1].direction);
    cmd.ar = res.wheels[1].steer_rad;

    // steer-hold — **바퀴별로** 판정한다. 공전 중 ICR 에 가까운 한쪽만 임계 아래로 떨어지는
    // 경우가 실재하므로 그 바퀴만 조향을 유지하고 속도는 IK 결과(0)를 그대로 쓴다.
    // 바퀴 속도 크기는 IK 와 같은 식으로 다시 구한다(qd_inverse_kinematics.cpp:25-26).
    const double spd_f = std::hypot(vx - omega * geom_.w1_y, vy + omega * geom_.w1_x);
    const double spd_r = std::hypot(vx - omega * geom_.w2_y, vy + omega * geom_.w2_x);
    if (have_last_)
    {
        if (spd_f < hold_below_) { cmd.af = last_af_; }
        if (spd_r < hold_below_) { cmd.ar = last_ar_; }
    }

    last_af_ = cmd.af;
    last_ar_ = cmd.ar;
    have_last_ = true;
    return cmd;
}

DockWheelCommand SteerHoldIk::orbit(double cx, double cy, double omega)
{
    // 정본 :281-282 — ICR=C 조건에서 body 속도.
    return compute(cy * omega, -cx * omega, omega);
}

DockWheelCommand SteerHoldIk::forward(double vx)
{
    return compute(vx, 0.0, 0.0);
}

}  // namespace dock_control
