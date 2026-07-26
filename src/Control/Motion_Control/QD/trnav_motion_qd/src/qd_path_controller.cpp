#include "trnav_motion_qd/qd_path_controller.hpp"
#include "trnav_motion_core/math_utils.hpp"

#include <algorithm>
#include <cmath>

namespace trnav::motion::qd
{

QdPathController::QdPathController(const Params &params)
    : params_(params), mode_(params.mode), e_theta_filter_(params.heading_filter_window),
      e_d_filter_(params.cte_filter_window)
{
}

void QdPathController::reset()
{
    prev_e_theta_ = 0.0;
    initialized_ = false;
    first_update_ = true;
    e_theta_filter_.reset();
    e_d_filter_.reset();
}

void QdPathController::setMode(ControlMode mode)
{
    mode_ = mode;
    prev_e_theta_ = 0.0;
    first_update_ = true;
}

void QdPathController::setGains(double Kp_heading, double Kd_heading, double K_stanley, double K_soft,
                                double max_delta_rad)
{
    params_.Kp_heading = Kp_heading;
    params_.Kd_heading = Kd_heading;
    params_.K_stanley = K_stanley;
    params_.K_soft = K_soft;
    params_.max_delta = max_delta_rad;
}

void QdPathController::setPath(double start_x, double start_y, double end_x, double end_y)
{
    start_x_ = start_x;
    start_y_ = start_y;
    end_x_ = end_x;
    end_y_ = end_y;

    theta_path_ = std::atan2(end_y - start_y, end_x - start_x);
    target_distance_ = std::hypot(end_x - start_x, end_y - start_y);
    ux_ = std::cos(theta_path_);
    uy_ = std::sin(theta_path_);

    initialized_ = true;
    first_update_ = true;
}

// ── Shared helpers ──────────────────────────────────────────────────────────

double QdPathController::computeStanleyCTE(double e_d, double vx) const
{
    if (vx <= 1e-6)
    {
        return 0.0;
    }
    return std::atan2(params_.K_stanley * e_d, params_.K_soft + vx);
}

double QdPathController::computeHeadingPD(double e_theta, double de_theta) const
{
    return -params_.Kp_heading * e_theta - params_.Kd_heading * de_theta;
}

// ── BICYCLE mode ────────────────────────────────────────────────────────────

PathControlOutput QdPathController::computeBicycle(double e_d, double e_theta, double de_theta, double vx,
                                                   TravelDirection dir)
{
    // Mode B: CTE(대칭) + heading(반대칭) 통합 제어
    double delta_stanley = computeStanleyCTE(e_d, vx);
    double delta_heading = computeHeadingPD(e_theta, de_theta);
    if (dir == TravelDirection::REVERSE)
    {
        delta_heading = -delta_heading;
    }
    double delta_f = std::clamp(delta_stanley + delta_heading, -params_.max_delta, params_.max_delta);
    double delta_r = std::clamp(delta_stanley - delta_heading, -params_.max_delta, params_.max_delta);
    return PathControlOutput{0.0, 0.0, 0.0, 0.0, 0.0, 0, delta_f, delta_r};
}

// ── Main update ─────────────────────────────────────────────────────────────

PathControlOutput QdPathController::update(double robot_x, double robot_y, double robot_yaw, double vx, double dt,
                                           TravelDirection dir)
{
    const double rx = robot_x - start_x_;
    const double ry = robot_y - start_y_;

    const double projection = rx * ux_ + ry * uy_;

    const double e_d_raw = rx * uy_ - ry * ux_;
    const double e_d = e_d_filter_.update(e_d_raw);

    const double e_theta_raw = trnav_motion_core::normalizeAngle(robot_yaw - theta_path_);
    const double e_theta = e_theta_filter_.update(e_theta_raw);

    double de_theta = 0.0;
    if (dt > 0.0 && !first_update_)
    {
        de_theta = (e_theta - prev_e_theta_) / dt;
    }

    // Wave 2: BICYCLE mode only. 후속 Wave 에서 switch 로 확장.
    PathControlOutput out = computeBicycle(e_d, e_theta, de_theta, vx, dir);

    prev_e_theta_ = e_theta;
    first_update_ = false;

    out.e_d = e_d_raw;
    out.e_theta = e_theta;
    out.projection = projection;
    out.control_stage = 0;

    return out;
}

int QdPathController::validateInitialPose(double robot_x, double robot_y, double robot_yaw) const
{
    const double rx = robot_x - start_x_;
    const double ry = robot_y - start_y_;

    const double projection = rx * ux_ + ry * uy_;
    const double e_d = rx * uy_ - ry * ux_;
    const double e_theta = trnav_motion_core::normalizeAngle(robot_yaw - theta_path_);

    if (projection >= target_distance_)
    {
        return -2;
    }

    if (std::fabs(e_theta) > params_.heading_threshold)
    {
        return -2;
    }

    if (std::fabs(e_d) > params_.max_lateral_offset)
    {
        return -2;
    }

    return 0;
}

} // namespace trnav::motion::qd
