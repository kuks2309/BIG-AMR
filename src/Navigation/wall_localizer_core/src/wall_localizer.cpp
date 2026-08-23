#include "wall_localizer_core/wall_localizer.hpp"

#include <cmath>

namespace wall_localizer_core
{

WallLocalizer::WallLocalizer(const std::vector<WallRef> &walls,
                             const WallLocalizerParams &params, const Pose2D &T_base_lidar,
                             const Pose2D &initial_T_station_base)
    : params_(params), T_base_lidar_(T_base_lidar),
      initial_T_station_base_(initial_T_station_base),
      last_T_station_base_(initial_T_station_base)
{
    oriented_walls_.reserve(walls.size());
    const Point2D robot_pos = {initial_T_station_base.x_m, initial_T_station_base.y_m};
    for (const WallRef &w : walls)
    {
        oriented_walls_.push_back(orientWall(w, robot_pos));
    }
}

void WallLocalizer::reset(const Pose2D &T_station_base_guess)
{
    last_T_station_base_ = T_station_base_guess;
    has_fix_ = false;
    consecutive_rejects_ = 0;
}

void WallLocalizer::registerReject()
{
    ++consecutive_rejects_;
    if (has_fix_ && consecutive_rejects_ > params_.quality.max_consecutive_rejects)
    {
        // 추적이 죽은 것으로 보고 초기 추정으로 복귀 — 스테이션 진입 지점 근방이라는
        // 운용 전제에서만 유효하다 (전역 재측위는 본 코어 범위 밖).
        has_fix_ = false;
        last_T_station_base_ = initial_T_station_base_;
        consecutive_rejects_ = 0;
    }
}

LocalizeResult WallLocalizer::update(const std::vector<float> &ranges_m, double angle_min_rad,
                                     double angle_inc_rad)
{
    LocalizeResult res;

    const std::vector<Point2D> points =
        scanToPoints(ranges_m, angle_min_rad, angle_inc_rad, params_.extract);
    const std::vector<ExtractedSegment> segments = extractSegments(points, params_.extract);
    res.num_segments = static_cast<int>(segments.size());
    if (segments.empty())
    {
        res.reason = "no_segments";
        registerReject();
        return res;
    }

    // 대응 시드: 추적 중이면 직전 해, 아니면 초기 추정.
    Pose2D T_station_lidar =
        compose(has_fix_ ? last_T_station_base_ : initial_T_station_base_, T_base_lidar_);

    // 대응 → 해석 → 재대응 반복 (시드 오차로 인한 오대응을 해로 교정).
    std::vector<WallMatch> matches;
    SolveResult sr;
    for (int iter = 0; iter < params_.solve.max_iterations; ++iter)
    {
        res.iterations = iter + 1;
        const std::vector<PredictedWall> predicted =
            predictWallsInLidar(oriented_walls_, T_station_lidar);
        matches = matchWalls(predicted, segments, oriented_walls_, params_.match);
        if (static_cast<int>(matches.size()) < params_.quality.min_walls)
        {
            res.reason = "insufficient_matches";
            registerReject();
            return res;
        }
        sr = solvePose(matches, params_.solve);
        if (!sr.ok)
        {
            res.reason = sr.reason;
            res.normal_spread = sr.normal_spread;
            registerReject();
            return res;
        }
        const double dx = sr.T_station_lidar.x_m - T_station_lidar.x_m;
        const double dy = sr.T_station_lidar.y_m - T_station_lidar.y_m;
        const double dyaw =
            normalizeAngle(sr.T_station_lidar.yaw_rad - T_station_lidar.yaw_rad);
        T_station_lidar = sr.T_station_lidar;
        if (std::hypot(dx, dy) < params_.solve.converge_eps_m &&
            std::fabs(dyaw) < params_.solve.converge_eps_rad)
        {
            break;
        }
    }
    res.normal_spread = sr.normal_spread;

    // 벽별 잔차 (최종 해 기준) + 잔차 게이트.
    res.wall_fits.resize(oriented_walls_.size());
    bool residual_ok = true;
    for (std::size_t i = 0; i < oriented_walls_.size(); ++i)
    {
        res.wall_fits[i].name = oriented_walls_[i].ref.name;
    }
    for (const WallMatch &m : matches)
    {
        WallFit &fit = res.wall_fits[m.wall_idx];
        fit.matched = true;
        fit.seg_rms_m = m.seg.rms_m;
        fit.seg_points = m.seg.num_points;
        const double d_pred = m.ref_line_station.d_m -
                              (m.ref_line_station.nx * T_station_lidar.x_m +
                               m.ref_line_station.ny * T_station_lidar.y_m);
        fit.dist_residual_m = d_pred - m.seg.line.d_m;
        fit.angle_residual_rad = normalizeAngle(
            std::atan2(m.ref_line_station.ny, m.ref_line_station.nx) -
            (T_station_lidar.yaw_rad + std::atan2(m.seg.line.ny, m.seg.line.nx)));
        if (std::fabs(fit.dist_residual_m) > params_.quality.max_dist_residual_m ||
            std::fabs(fit.angle_residual_rad) > params_.quality.max_angle_residual_rad)
        {
            residual_ok = false;
        }
    }
    if (!residual_ok)
    {
        res.reason = "residual_gate";
        registerReject();
        return res;
    }

    const Pose2D T_station_base = compose(T_station_lidar, inverse(T_base_lidar_));

    // 점프 게이트 — 추적 중 갑작스러운 해 이동은 오대응 신호다.
    if (has_fix_)
    {
        const double jump = std::hypot(T_station_base.x_m - last_T_station_base_.x_m,
                                       T_station_base.y_m - last_T_station_base_.y_m);
        const double jump_yaw =
            normalizeAngle(T_station_base.yaw_rad - last_T_station_base_.yaw_rad);
        if (jump > params_.quality.max_jump_m ||
            std::fabs(jump_yaw) > params_.quality.max_jump_rad)
        {
            res.reason = "jump_gate";
            registerReject();
            return res;
        }
    }

    has_fix_ = true;
    consecutive_rejects_ = 0;
    last_T_station_base_ = T_station_base;
    res.T_station_base = T_station_base;
    res.status = (matches.size() == oriented_walls_.size()) ? Status::OK : Status::DEGRADED;
    return res;
}

}  // namespace wall_localizer_core
