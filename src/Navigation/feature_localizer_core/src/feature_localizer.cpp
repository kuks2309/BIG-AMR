#include "feature_localizer_core/feature_localizer.hpp"

#include <cmath>

namespace feature_localizer_core
{

FeatureLocalizer::FeatureLocalizer(const std::vector<FeatureRef> &features,
                             const FeatureLocalizerParams &params, const Pose2D &T_base_lidar,
                             const Pose2D &initial_T_station_base)
    : params_(params), T_base_lidar_(T_base_lidar),
      initial_T_station_base_(initial_T_station_base),
      last_T_station_base_(initial_T_station_base)
{
    oriented_features_.reserve(features.size());
    const Point2D robot_pos = {initial_T_station_base.x_m, initial_T_station_base.y_m};
    for (const FeatureRef &w : features)
    {
        oriented_features_.push_back(orientWall(w, robot_pos));
    }
}

void FeatureLocalizer::reset(const Pose2D &T_station_base_guess)
{
    last_T_station_base_ = T_station_base_guess;
    has_fix_ = false;
    consecutive_rejects_ = 0;
}

void FeatureLocalizer::registerReject()
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

LocalizeResult FeatureLocalizer::update(const std::vector<float> &ranges_m, double angle_min_rad,
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

    // 대응 → 재적합 → 해석 → 재대응 반복 (시드 오차로 인한 오대응을 해로 교정).
    // 대응은 추출 선분(1:N)이, 해석기에 넣는 측정은 예측 직선 회랑 안 원시 점 전체의
    // 재적합이 담당한다 — 잡음 토막화가 측정 점수·편향에 영향을 못 주게 하는 구조.
    std::vector<FeatureMatch> matches;
    SolveResult sr;
    for (int iter = 0; iter < params_.solve.max_iterations; ++iter)
    {
        res.iterations = iter + 1;
        const std::vector<PredictedWall> predicted =
            predictWallsInLidar(oriented_features_, T_station_lidar);
        const std::vector<FeatureCandidateGroup> groups =
            matchWallsMulti(predicted, segments, oriented_features_, params_.match);
        matches.clear();
        for (const FeatureCandidateGroup &g : groups)
        {
            ExtractedSegment meas;
            if (!refitWallFromPoints(points, predicted[g.feature_idx], g, params_.match,
                                     params_.extract.min_points, params_.match.gate_angle_rad,
                                     &meas))
            {
                continue;
            }
            FeatureMatch m;
            m.feature_idx = g.feature_idx;
            m.ref_line_station = g.ref_line_station;
            m.seg = meas;
            matches.push_back(m);
        }
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
    res.feature_fits.resize(oriented_features_.size());
    bool residual_ok = true;
    for (std::size_t i = 0; i < oriented_features_.size(); ++i)
    {
        res.feature_fits[i].name = oriented_features_[i].ref.name;
    }
    for (const FeatureMatch &m : matches)
    {
        FeatureFit &fit = res.feature_fits[m.feature_idx];
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
    res.status = (matches.size() == oriented_features_.size()) ? Status::OK : Status::DEGRADED;
    return res;
}

}  // namespace feature_localizer_core
