#include "trnav_qd_kinematics/qd_inverse_kinematics.hpp"

namespace trnav::motion::qd
{

QdDualSteerIK::QdDualSteerIK(std::vector<WheelPosition> wheels, double wheel_radius, double gear_walk)
    : wheels_(std::move(wheels)), wheel_radius_(wheel_radius), gear_walk_(gear_walk)
{
}

IKResult QdDualSteerIK::compute(const VelocityCommand &cmd) const
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

IKResult QdDualSteerIK::computeSpin(double omega) const
{
    return compute({0.0, 0.0, omega});
}

WheelOutput QdDualSteerIK::computeWheel(double vx, double vy) const
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

    // ±90° normalization
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

double QdDualSteerIK::normalizeAngle(double angle_rad, int &direction)
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

} // namespace trnav::motion::qd
