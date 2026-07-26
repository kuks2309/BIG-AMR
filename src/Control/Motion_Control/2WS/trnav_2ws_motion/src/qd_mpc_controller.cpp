#include "trnav_2ws_motion/qd_mpc_controller.hpp"

#include "trnav_2ws_core/math_utils.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <nlopt.hpp>

namespace trnav::motion::two_ws
{

namespace
{
inline double normalize_pi(double a)
{
    while (a > M_PI) a -= 2.0 * M_PI;
    while (a < -M_PI) a += 2.0 * M_PI;
    return a;
}
}  // namespace

TwoWsMpcController::TwoWsMpcController(const Params &params) : params_(params) {}

void TwoWsMpcController::reset()
{
    initialized_ = false;
    wp_.clear();
    seg_len_.clear();
    seg_cum_.clear();
    total_length_ = 0.0;
    warm_start_.assign(params_.N, 0.0);
}

bool TwoWsMpcController::setPath(const std::vector<MpcPose> &poses)
{
    if (poses.size() < 2)
    {
        initialized_ = false;
        return false;
    }
    wp_ = poses;
    seg_len_.clear();
    seg_cum_.clear();
    seg_len_.reserve(wp_.size() - 1);
    seg_cum_.reserve(wp_.size());
    seg_cum_.push_back(0.0);
    for (std::size_t i = 0; i + 1 < wp_.size(); ++i)
    {
        double dx = wp_[i + 1].x - wp_[i].x;
        double dy = wp_[i + 1].y - wp_[i].y;
        double len = std::hypot(dx, dy);
        seg_len_.push_back(len);
        seg_cum_.push_back(seg_cum_.back() + len);
    }
    total_length_ = seg_cum_.back();
    if (total_length_ < 1e-6)
    {
        initialized_ = false;
        return false;
    }
    warm_start_.assign(params_.N, 0.0);
    initialized_ = true;
    return true;
}

void TwoWsMpcController::closestSegmentError(double rx, double ry, double ryaw,
                                           double &lat_err, double &hdg_err) const
{
    std::size_t best_i = 0;
    double best_d2 = std::numeric_limits<double>::infinity();
    for (std::size_t i = 0; i + 1 < wp_.size(); ++i)
    {
        double ax = wp_[i].x;
        double ay = wp_[i].y;
        double dx = wp_[i + 1].x - ax;
        double dy = wp_[i + 1].y - ay;
        double seg = seg_len_[i];
        if (seg < 1e-9) continue;
        double t = ((rx - ax) * dx + (ry - ay) * dy) / (seg * seg);
        if (t < 0.0) t = 0.0;
        if (t > 1.0) t = 1.0;
        double cx = ax + t * dx;
        double cy = ay + t * dy;
        double d2 = (rx - cx) * (rx - cx) + (ry - cy) * (ry - cy);
        if (d2 < best_d2)
        {
            best_d2 = d2;
            best_i = i;
        }
    }
    // tangent = path orientation (Phase A 정공법 — atan2 재계산 폐기)
    const double tangent = wp_[best_i].yaw;
    const double ax = wp_[best_i].x;
    const double ay = wp_[best_i].y;
    const double nx = -std::sin(tangent);
    const double ny = std::cos(tangent);
    lat_err = (rx - ax) * nx + (ry - ay) * ny;
    hdg_err = normalize_pi(tangent - ryaw);
}

double TwoWsMpcController::computeCost(const std::vector<double> &deltas,
                                     double rx0, double ry0, double ryaw0) const
{
    const double gx = wp_.back().x;
    const double gy = wp_.back().y;
    double x = rx0, y = ry0, yaw = ryaw0;
    double cost = 0.0;
    double prev_d = 0.0;
    for (int k = 0; k < params_.N; ++k)
    {
        // bicycle FK step
        x += params_.v_const * std::cos(yaw) * params_.dt_mpc;
        y += params_.v_const * std::sin(yaw) * params_.dt_mpc;
        yaw += params_.v_const * std::tan(deltas[k]) / params_.wheelbase * params_.dt_mpc;

        double lat = 0.0, hdg = 0.0;
        closestSegmentError(x, y, yaw, lat, hdg);
        cost += params_.w_lat * lat * lat + params_.w_hdg * hdg * hdg;
        cost += params_.w_du * (deltas[k] - prev_d) * (deltas[k] - prev_d);

        double goal_dx = x - gx;
        double goal_dy = y - gy;
        cost += params_.w_goal * (goal_dx * goal_dx + goal_dy * goal_dy);

        prev_d = deltas[k];
    }
    return cost;
}

// NLopt 의 objective callback. data = struct {this, robot pose}.
struct NloptUserData
{
    const TwoWsMpcController *self;
    double rx, ry, ryaw;
};

double TwoWsMpcController::nloptObjective(unsigned n, const double *x, double *grad, void *data)
{
    auto *ud = static_cast<NloptUserData *>(data);
    std::vector<double> deltas(x, x + n);
    const double f = ud->self->computeCost(deltas, ud->rx, ud->ry, ud->ryaw);

    if (grad != nullptr)
    {
        // finite difference gradient (central)
        const double eps = 1e-4;
        std::vector<double> deltas_p = deltas;
        std::vector<double> deltas_m = deltas;
        for (unsigned i = 0; i < n; ++i)
        {
            deltas_p[i] = deltas[i] + eps;
            deltas_m[i] = deltas[i] - eps;
            const double f_p = ud->self->computeCost(deltas_p, ud->rx, ud->ry, ud->ryaw);
            const double f_m = ud->self->computeCost(deltas_m, ud->rx, ud->ry, ud->ryaw);
            grad[i] = (f_p - f_m) / (2.0 * eps);
            deltas_p[i] = deltas[i];
            deltas_m[i] = deltas[i];
        }
    }
    return f;
}

MpcOutput TwoWsMpcController::update(double rx, double ry, double ryaw,
                                   double /*current_speed*/, double /*dt*/)
{
    MpcOutput out{};
    if (!initialized_) return out;

    // 1) lat/hdg err (debug)
    closestSegmentError(rx, ry, ryaw, out.e_d, out.e_theta);
    {
        const auto &g = wp_.back();
        out.remaining_to_goal = std::hypot(g.x - rx, g.y - ry);
    }

    // 2) NLopt SLSQP optimize
    nlopt::opt opt(nlopt::LD_SLSQP, params_.N);
    NloptUserData ud{this, rx, ry, ryaw};
    opt.set_min_objective(TwoWsMpcController::nloptObjective, &ud);
    std::vector<double> lb(params_.N, -params_.max_delta_rad);
    std::vector<double> ub(params_.N, params_.max_delta_rad);
    opt.set_lower_bounds(lb);
    opt.set_upper_bounds(ub);
    opt.set_ftol_rel(params_.ftol_rel);
    opt.set_maxeval(params_.max_iter);

    // warm start (이전 sol shift + 마지막 element 복제)
    std::vector<double> x_init = warm_start_;
    if (static_cast<int>(x_init.size()) != params_.N)
    {
        x_init.assign(params_.N, 0.0);
    }
    // shift: x_init[k] = warm_start_[k+1] (1 step 전진)
    for (int k = 0; k + 1 < params_.N; ++k)
    {
        x_init[k] = warm_start_[k + 1];
    }
    x_init[params_.N - 1] = warm_start_.back();

    double minf = 0.0;
    try
    {
        nlopt::result res = opt.optimize(x_init, minf);
        out.valid = (res >= 0);
        out.cost = minf;
        out.n_iter = opt.get_numevals();
        out.delta_f = x_init.front();
        // clamp
        out.delta_f = std::clamp(out.delta_f, -params_.max_delta_rad, params_.max_delta_rad);
        // warm start 갱신
        warm_start_ = x_init;
    }
    catch (const std::exception &)
    {
        out.valid = false;
        out.delta_f = 0.0;
    }
    return out;
}

int TwoWsMpcController::validateInitialPose(double rx, double ry, double /*ryaw*/) const
{
    if (!initialized_) return -2;
    double lat = 0.0, hdg = 0.0;
    closestSegmentError(rx, ry, 0.0, lat, hdg);
    if (std::fabs(lat) > params_.max_lateral_offset) return -2;
    return 0;
}

} // namespace trnav::motion::two_ws
