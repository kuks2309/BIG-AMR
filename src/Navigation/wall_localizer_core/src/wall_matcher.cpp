#include "wall_localizer_core/wall_matcher.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace wall_localizer_core
{

OrientedWall orientWall(const WallRef &w, const Point2D &robot_pos_station)
{
    OrientedWall ow;
    ow.ref = w;
    const double vx = w.p2.x_m - w.p1.x_m;
    const double vy = w.p2.y_m - w.p1.y_m;
    const double len = std::hypot(vx, vy);
    // 길이 0 벽은 YAML 검증에서 걸러야 한다 — 여기서는 0 나눗셈만 방어한다.
    const double inv = (len > 1e-12) ? 1.0 / len : 0.0;
    ow.line_station.nx = -vy * inv;
    ow.line_station.ny = vx * inv;
    ow.line_station.d_m = ow.line_station.nx * w.p1.x_m + ow.line_station.ny * w.p1.y_m;
    // 로봇 쪽 예측 거리 d − n·t 가 양수가 되도록: n·robot < d 를 만족시키는 부호 선택.
    if (ow.line_station.nx * robot_pos_station.x_m + ow.line_station.ny * robot_pos_station.y_m >
        ow.line_station.d_m)
    {
        ow.line_station.nx = -ow.line_station.nx;
        ow.line_station.ny = -ow.line_station.ny;
        ow.line_station.d_m = -ow.line_station.d_m;
    }
    return ow;
}

std::vector<PredictedWall> predictWallsInLidar(const std::vector<OrientedWall> &walls,
                                               const Pose2D &T_station_lidar)
{
    const Pose2D T_lidar_station = inverse(T_station_lidar);
    const double c = std::cos(T_station_lidar.yaw_rad);
    const double s = std::sin(T_station_lidar.yaw_rad);

    std::vector<PredictedWall> out;
    out.reserve(walls.size());
    for (std::size_t i = 0; i < walls.size(); ++i)
    {
        const LineNormalForm &ls = walls[i].line_station;
        PredictedWall pw;
        pw.wall_idx = i;
        // n_lidar = Rᵀ·n_station (수동 회전), d_lidar = d − n·t
        pw.line.nx = c * ls.nx + s * ls.ny;
        pw.line.ny = -s * ls.nx + c * ls.ny;
        pw.line.d_m = ls.d_m - (ls.nx * T_station_lidar.x_m + ls.ny * T_station_lidar.y_m);
        pw.p1 = transformPoint(T_lidar_station, walls[i].ref.p1);
        pw.p2 = transformPoint(T_lidar_station, walls[i].ref.p2);
        pw.side_valid = pw.line.d_m > 0.0;
        out.push_back(pw);
    }
    return out;
}

std::vector<WallMatch> matchWalls(const std::vector<PredictedWall> &predicted,
                                  const std::vector<ExtractedSegment> &segments,
                                  const std::vector<OrientedWall> &walls, const MatchParams &p)
{
    struct Candidate
    {
        double score;
        std::size_t pred_idx;
        std::size_t seg_idx;
    };
    std::vector<Candidate> candidates;

    for (std::size_t pi = 0; pi < predicted.size(); ++pi)
    {
        const PredictedWall &pw = predicted[pi];
        if (!pw.side_valid)
        {
            continue;
        }
        const double pred_ang = std::atan2(pw.line.ny, pw.line.nx);
        // 예측 벽 접선축 (겹침 판정용)
        const double ux0 = pw.p2.x_m - pw.p1.x_m;
        const double uy0 = pw.p2.y_m - pw.p1.y_m;
        const double ulen = std::hypot(ux0, uy0);
        if (ulen < 1e-12)
        {
            continue;
        }
        const double ux = ux0 / ulen;
        const double uy = uy0 / ulen;

        for (std::size_t si = 0; si < segments.size(); ++si)
        {
            const ExtractedSegment &seg = segments[si];
            const double d_ang = std::fabs(
                normalizeAngle(std::atan2(seg.line.ny, seg.line.nx) - pred_ang));
            if (d_ang > p.gate_angle_rad)
            {
                continue;
            }
            const double d_dist = std::fabs(seg.line.d_m - pw.line.d_m);
            if (d_dist > p.gate_dist_m)
            {
                continue;
            }
            // 겹침: 선분 끝점을 예측 벽 접선축에 사영한 구간 ∩ [0, ulen]
            double s1 = ux * (seg.p1.x_m - pw.p1.x_m) + uy * (seg.p1.y_m - pw.p1.y_m);
            double s2 = ux * (seg.p2.x_m - pw.p1.x_m) + uy * (seg.p2.y_m - pw.p1.y_m);
            if (s1 > s2)
            {
                std::swap(s1, s2);
            }
            const double overlap = std::max(0.0, std::min(s2, ulen) - std::max(s1, 0.0));
            const double ratio = overlap / ulen;  // 예측 벽 구간 대비 (MatchParams 주석 참조)
            if (ratio < p.min_overlap_ratio)
            {
                continue;
            }
            const double score =
                d_ang / p.gate_angle_rad + d_dist / p.gate_dist_m + (1.0 - ratio);
            candidates.push_back({score, pi, si});
        }
    }

    std::sort(candidates.begin(), candidates.end(),
              [](const Candidate &a, const Candidate &b) { return a.score < b.score; });

    std::vector<WallMatch> matches;
    std::vector<bool> pred_used(predicted.size(), false);
    std::vector<bool> seg_used(segments.size(), false);
    for (const Candidate &c : candidates)
    {
        if (pred_used[c.pred_idx] || seg_used[c.seg_idx])
        {
            continue;
        }
        pred_used[c.pred_idx] = true;
        seg_used[c.seg_idx] = true;
        WallMatch m;
        m.wall_idx = predicted[c.pred_idx].wall_idx;
        m.ref_line_station = walls[m.wall_idx].line_station;
        m.seg = segments[c.seg_idx];
        matches.push_back(m);
    }
    return matches;
}

}  // namespace wall_localizer_core
