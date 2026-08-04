#include "trnav_2ws_kinematics/qd_bicycle_model.hpp"

#include <algorithm>
#include <stdexcept>

namespace trnav::motion::two_ws
{

TwoWsBicycleModel::TwoWsBicycleModel(const std::vector<WheelPosition> &wheels) : wheels_(wheels), has_wheels_(true)
{
    if (wheels_.size() < 2)
    {
        throw std::runtime_error("TwoWsBicycleModel requires at least 2 wheel positions");
    }
    L_ = std::abs(wheels_[0].x - wheels_[1].x);
    if (L_ < kSpeedEpsilon)
    {
        throw std::runtime_error("TwoWsBicycleModel: computed wheelbase is too small (wheels at same X?)");
    }
}

TwoWsBicycleModel::TwoWsBicycleModel(double wheelbase_m) : L_(wheelbase_m), has_wheels_(false)
{
    if (L_ < kSpeedEpsilon)
    {
        throw std::runtime_error("TwoWsBicycleModel: wheelbase_m must be > 0");
    }
}

VelocityCommand TwoWsBicycleModel::toVelocityCommand(const BicycleCommand &cmd) const
{
    // Bicycle model forward conversion:
    //   vx = v  (longitudinal velocity maps directly)
    //   vy = 0  (bicycle model constraint: no lateral velocity)
    //   omega = v * tan(delta) / L
    double vx = cmd.v;
    double vy = 0.0;
    double omega_val;

    if (std::abs(cmd.v) < kSpeedEpsilon)
    {
        omega_val = 0.0;
    }
    else
    {
        double delta_clamped = std::clamp(cmd.delta, -kDeltaMax, kDeltaMax);
        omega_val = cmd.v * std::tan(delta_clamped) / L_;
    }

    return {vx, vy, omega_val};
}

IKResult TwoWsBicycleModel::toIKResult(const BicycleCommand &cmd, const TwoWsDualSteerIK &ik) const
{
    return ik.compute(toVelocityCommand(cmd));
}

VelocityCommand TwoWsBicycleModel::toVelocityCommand(const DualBicycleCommand &cmd) const
{
    // Dual bicycle model forward conversion (matches Python compute_from_dual_bicycle):
    //   omega = vx * (tan(delta_f) - tan(delta_r)) / L
    //   vy    = vx * (tan(delta_f) + tan(delta_r)) / 2
    if (std::abs(cmd.vx) < kSpeedEpsilon)
    {
        return {cmd.vx, 0.0, 0.0};
    }
    double df_c = std::clamp(cmd.delta_f, -kDeltaMax, kDeltaMax);
    double dr_c = std::clamp(cmd.delta_r, -kDeltaMax, kDeltaMax);
    double tan_f = std::tan(df_c);
    double tan_r = std::tan(dr_c);
    double omega_val = cmd.vx * (tan_f - tan_r) / L_;
    double vy = cmd.vx * (tan_f + tan_r) / 2.0;
    return {cmd.vx, vy, omega_val};
}

IKResult TwoWsBicycleModel::toIKResult(const DualBicycleCommand &cmd, const TwoWsDualSteerIK &ik) const
{
    return ik.compute(toVelocityCommand(cmd));
}

BicycleState TwoWsBicycleModel::fromVelocityCommand(const VelocityCommand &vel) const
{
    double v = vel.vx;
    double vy_residual = vel.vy;

    double delta = deltaFromOmega(vel.vx, vel.omega);

    double curv;
    if (std::abs(vel.vx) < kSpeedEpsilon)
    {
        curv = 0.0;
    }
    else
    {
        curv = vel.omega / vel.vx;
    }

    double turning_rad;
    if (std::abs(curv) < kSpeedEpsilon)
    {
        turning_rad = std::numeric_limits<double>::infinity();
    }
    else
    {
        turning_rad = 1.0 / std::abs(curv);
    }

    return {v, delta, curv, turning_rad, vy_residual};
}

BicycleState TwoWsBicycleModel::fromIKResult(const IKResult &result) const
{
    if (!has_wheels_)
    {
        throw std::runtime_error("TwoWsBicycleModel::fromIKResult requires wheel positions "
                                 "(use wheel-position constructor, not explicit wheelbase constructor)");
    }

    // Step 1: Reconstruct wheel velocity vectors in robot frame
    double v0_signed = result.wheels[0].wheel_speed * result.wheels[0].direction;
    double vx_1 = v0_signed * std::cos(result.wheels[0].steer_rad);
    double vy_1 = v0_signed * std::sin(result.wheels[0].steer_rad);

    double v1_signed = result.wheels[1].wheel_speed * result.wheels[1].direction;
    double vx_2 = v1_signed * std::cos(result.wheels[1].steer_rad);

    // Step 2: Solve for body velocity (vx, vy, omega) from 2-wheel constraint
    double y_1 = wheels_[0].y;
    double y_2 = wheels_[1].y;
    double x_1 = wheels_[0].x;
    double dy = y_2 - y_1;

    double omega_val, vx, vy;
    if (std::abs(dy) < kSpeedEpsilon)
    {
        omega_val = 0.0;
        vx = (vx_1 + vx_2) / 2.0;
        vy = vy_1;
    }
    else
    {
        omega_val = (vx_1 - vx_2) / dy;
        vx = vx_1 + omega_val * y_1;
        vy = vy_1 - omega_val * x_1;
    }

    return fromVelocityCommand({vx, vy, omega_val});
}

double TwoWsBicycleModel::curvature(const BicycleCommand &cmd) const
{
    double delta_clamped = std::clamp(cmd.delta, -kDeltaMax, kDeltaMax);
    return std::tan(delta_clamped) / L_;
}

double TwoWsBicycleModel::turningRadius(const BicycleCommand &cmd) const
{
    double delta_clamped = std::clamp(cmd.delta, -kDeltaMax, kDeltaMax);
    double tan_delta = std::tan(delta_clamped);
    if (std::abs(tan_delta) < kSpeedEpsilon)
    {
        return std::numeric_limits<double>::infinity();
    }
    return L_ / std::abs(tan_delta);
}

double TwoWsBicycleModel::omega(const BicycleCommand &cmd) const
{
    if (std::abs(cmd.v) < kSpeedEpsilon)
    {
        return 0.0;
    }
    double delta_clamped = std::clamp(cmd.delta, -kDeltaMax, kDeltaMax);
    return cmd.v * std::tan(delta_clamped) / L_;
}

double TwoWsBicycleModel::deltaFromOmega(double vx, double omega_val) const
{
    // CRITICAL: Use atan() NOT atan2(). atan(omega*L/vx) works because division
    // cancels the sign of vx, giving correct delta in both forward and reverse.

    if (std::abs(vx) < kSpeedEpsilon)
    {
        if (std::abs(omega_val) > kSpeedEpsilon)
        {
            return std::copysign(M_PI / 2.0, omega_val);
        }
        return 0.0;
    }

    return std::atan(omega_val * L_ / vx);
}

} // namespace trnav::motion::two_ws
