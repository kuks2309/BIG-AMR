#include "feature_localizer_core/pose_solver.hpp"

#include <cmath>

namespace feature_localizer_core
{

SolveResult solvePose(const std::vector<FeatureMatch> &matches, const SolveParams &p)
{
    SolveResult r;
    if (matches.size() < 2)
    {
        // 벽 1면은 그 벽의 법선 방향 1자유도만 구속한다 — 병진 2자유도를 못 푼다.
        r.reason = "insufficient_matches";
        return r;
    }

    // yaw: θ_i = angle(n_station) − angle(n_lidar) 의 가중 원형 평균.
    double sum_w = 0.0;
    double sum_sin = 0.0;
    double sum_cos = 0.0;
    for (const FeatureMatch &m : matches)
    {
        const double w = static_cast<double>(m.seg.num_points);
        const double theta_i =
            std::atan2(m.ref_line_station.ny, m.ref_line_station.nx) -
            std::atan2(m.seg.line.ny, m.seg.line.nx);
        sum_w += w;
        sum_sin += w * std::sin(theta_i);
        sum_cos += w * std::cos(theta_i);
    }
    const double yaw = std::atan2(sum_sin, sum_cos);

    // 병진: n_station·t = d_station − d_lidar 의 가중 정규방정식 A·t = b.
    double axx = 0.0;
    double axy = 0.0;
    double ayy = 0.0;
    double bx = 0.0;
    double by = 0.0;
    for (const FeatureMatch &m : matches)
    {
        const double w = static_cast<double>(m.seg.num_points);
        const double nx = m.ref_line_station.nx;
        const double ny = m.ref_line_station.ny;
        const double rhs = m.ref_line_station.d_m - m.seg.line.d_m;
        axx += w * nx * nx;
        axy += w * nx * ny;
        ayy += w * ny * ny;
        bx += w * nx * rhs;
        by += w * ny * rhs;
    }
    axx /= sum_w;
    axy /= sum_w;
    ayy /= sum_w;
    bx /= sum_w;
    by /= sum_w;

    // 가관측성: A 는 대칭·trace 1 — 최소고유값 = (1 − √((axx−ayy)² + 4axy²)) / 2.
    const double diff = std::sqrt((axx - ayy) * (axx - ayy) + 4.0 * axy * axy);
    r.normal_spread = 0.5 * (1.0 - diff);
    if (r.normal_spread < p.min_normal_spread)
    {
        // 법선이 사실상 한 방향(평행 벽뿐) — 접선 방향 병진이 미관측이라 해가 무의미하다.
        r.reason = "degenerate_normals";
        return r;
    }

    const double det = axx * ayy - axy * axy;
    r.T_station_lidar.x_m = (ayy * bx - axy * by) / det;
    r.T_station_lidar.y_m = (axx * by - axy * bx) / det;
    r.T_station_lidar.yaw_rad = normalizeAngle(yaw);
    r.ok = true;
    return r;
}

}  // namespace feature_localizer_core
