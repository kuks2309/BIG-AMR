#include "trnav_motion_core/transient_guard.hpp"

#include <algorithm>
#include <cmath>

namespace trnav_motion_core
{

TransientGuard::TransientGuard(const Params &params) : params_(params), prev_vy_(0.0), prev_omega_(0.0)
{
}

void TransientGuard::reset()
{
    prev_vy_ = 0.0;
    prev_omega_ = 0.0;
}

// static
double TransientGuard::clamp(double val, double lo, double hi)
{
    return std::max(lo, std::min(val, hi));
}

// static
double TransientGuard::rateLimitStep(double current, double target, double max_change)
{
    double diff = target - current;
    if (std::fabs(diff) <= max_change)
    {
        return target;
    }
    return current + std::copysign(max_change, diff);
}

TransientGuard::GuardOutput TransientGuard::apply(const GuardInput &input)
{
    GuardOutput out{};

    // 1. Rate limit
    out.vy_limited = rateLimitStep(prev_vy_, input.vy_cmd, params_.vy_rate_limit);
    out.omega_limited = rateLimitStep(prev_omega_, input.omega_cmd, params_.omega_rate_limit);
    prev_vy_ = out.vy_limited;
    prev_omega_ = out.omega_limited;

    // 2. Gate
    if (input.is_phase0)
    {
        out.gate_blocked = (input.steer_error_deg > params_.steer_gate_threshold);
    }
    else
    {
        out.gate_blocked = (input.steer_error_deg > params_.runtime_gate_threshold);
    }

    // 3. Proportional decel
    if (params_.enable_proportional_decel)
    {
        out.drive_scale = clamp(1.0 - input.steer_error_deg / params_.steer_error_max, 0.0, 1.0);
    }
    else
    {
        out.drive_scale = 1.0;
    }

    // Gate overrides scale
    if (out.gate_blocked)
    {
        out.drive_scale = 0.0;
    }

    return out;
}

} // namespace trnav_motion_core
