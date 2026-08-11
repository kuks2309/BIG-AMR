#include "trnav_2ws_kinematics/qd_inverse_kinematics.hpp"

namespace trnav::motion::two_ws
{

TwoWsDualSteerIK::TwoWsDualSteerIK(std::vector<WheelPosition> wheels, double wheel_radius, double gear_walk)
    : wheels_(std::move(wheels)), wheel_radius_(wheel_radius), gear_walk_(gear_walk)
{
}

IKResult TwoWsDualSteerIK::compute(const VelocityCommand &cmd) const
{
    // Ported from dual_steer_engine.py::compute(cmd, constrained=False)
    // Lines 89-102: Free mode — each wheel steers independently
    //
    // v_i = V_body + ω × r_i
    //   vx_i = vx - omega * y_i
    //   vy_i = vy + omega * x_i

    IKResult result;
    result.wheels.reserve(wheels_.size());

    for (const auto &wp : wheels_)
    {
        double vx_i = cmd.vx - cmd.omega * wp.y;
        double vy_i = cmd.vy + cmd.omega * wp.x;
        result.wheels.push_back(computeWheel(vx_i, vy_i));
    }

    return result;
}

IKResult TwoWsDualSteerIK::computeSpin(double omega) const
{
    // 인라인 배치(y=0)에서 제자리 회전 자세는 **풀 대상이 아니다** — 근거·사고 이력은 헤더 참조.
    //   v_i = ω × r_i = (0, ω·x_i)  ⇒  조향 ±90°(부호는 x_i), 속도 |ω·x_i|
    IKResult result;
    result.wheels.reserve(wheels_.size());

    for (const auto &wp : wheels_)
    {
        WheelOutput out{};
        const double v = omega * wp.x;   // 바퀴 접점의 횡방향 속도 성분

        if (std::abs(v) < 1e-6)
        {
            // ω≈0 이거나 바퀴가 회전축 위에 있다 — 자세를 주장하지 않는다(compute() 와 같은 규약).
            out.steer_rad = 0.0;
            out.wheel_speed = 0.0;
            out.direction = 0;
            out.drive_rpm = 0.0;
        }
        else
        {
            // ⚠ 강제. atan2 를 거치지 않으므로 기하가 어긋나도 자세가 흔들리지 않는다.
            out.steer_rad = std::copysign(M_PI / 2.0, v);
            out.wheel_speed = std::abs(v);
            out.direction = 1;
            out.drive_rpm = (out.wheel_speed / wheel_radius_) * 60.0 / (2.0 * M_PI) * gear_walk_;
        }
        result.wheels.push_back(out);
    }

    return result;
}

bool TwoWsDualSteerIK::isInline(double tol_m) const
{
    for (const auto &wp : wheels_)
    {
        if (std::abs(wp.y) > tol_m)
        {
            return false;
        }
    }
    return !wheels_.empty();
}

WheelOutput TwoWsDualSteerIK::computeWheel(double vx, double vy) const
{
    WheelOutput out{};

    double spd = std::hypot(vx, vy);
    if (spd < 1e-6)
    {
        out.steer_rad = 0.0;
        out.wheel_speed = 0.0;
        out.direction = 0;
        out.drive_rpm = 0.0;
        return out;
    }

    double angle = std::atan2(vy, vx);
    int direction = 1; // FWD by default (same as _make_free: direction=1)

    // ±90° normalization — 의도: 유일해(canonical) 확정. 한 바퀴 속도벡터는 항상 등가 2해
    // (θ,+v) ≡ (θ∓180°,−v) 를 갖는데, [-90°,+90°](반원, 180° 폭)로 정규화하면 방향↔각도가
    // 1:1(전단사)이 되어 정확히 한 해만 남고 항상 최소 조향각을 고른다. atan2 분기·입력 이력에
    // 무관한 결정론적 출력 → 상위 heading/CTE 폐루프가 요구하는 연속·유일 조향 목표 보장.
    // Seer(±140°, chassis_kinematics.py:56)는 접기범위 280°>반원이라 90~140°에서 2해가 공존(비유일).
    // Big-AMR 조향 한계 > 90° 이므로 ±90° 정규화는 항상 물리범위 내(한계초과 위험 0).
    // 상세: docs/adr/2026-07-26-qd-ik-pm90-unique-solution.md
    double steer = normalizeAngle(angle, direction);

    // RPM for feedback display
    //   rpm = (spd / wheel_radius) * 60 / (2π)
    //   motor_rpm = rpm * gear_ratio
    double wheel_rpm = (spd / wheel_radius_) * 60.0 / (2.0 * M_PI);

    out.steer_rad = steer;
    out.wheel_speed = spd;
    out.direction = direction;
    out.drive_rpm = wheel_rpm * gear_walk_;

    return out;
}

double TwoWsDualSteerIK::normalizeAngle(double angle_rad, int &direction)
{
    if (angle_rad > M_PI / 2.0)
    {
        angle_rad -= M_PI;
        direction = -direction;
    }
    else if (angle_rad < -M_PI / 2.0)
    {
        angle_rad += M_PI;
        direction = -direction;
    }

    return angle_rad;
}

} // namespace trnav::motion::two_ws
