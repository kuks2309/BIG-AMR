#include "feature_localizer_core/line_extractor.hpp"

#include <algorithm>
#include <cmath>
#include <utility>

namespace feature_localizer_core
{

namespace
{

// 점 q 와 현(a→b) 사이 수직거리. 현 길이가 0 이면 점-점 거리로 대체.
double pointToChordDist(const Point2D &a, const Point2D &b, const Point2D &q)
{
    const double vx = b.x_m - a.x_m;
    const double vy = b.y_m - a.y_m;
    const double len = std::hypot(vx, vy);
    if (len < 1e-12)
    {
        return std::hypot(q.x_m - a.x_m, q.y_m - a.y_m);
    }
    return std::fabs(vx * (q.y_m - a.y_m) - vy * (q.x_m - a.x_m)) / len;
}

// 재귀 분할: [i0, i1] 을 현 기준 최대 이탈점에서 쪼갠다. min_points 미만 구간은 버린다.
void splitRecursive(const std::vector<Point2D> &pts, std::size_t i0, std::size_t i1,
                    const ExtractParams &p,
                    std::vector<std::pair<std::size_t, std::size_t>> &out)
{
    if (i1 - i0 + 1 < static_cast<std::size_t>(p.min_points))
    {
        return;
    }
    std::size_t k = i0;
    double max_d = -1.0;
    for (std::size_t i = i0 + 1; i < i1; ++i)
    {
        const double d = pointToChordDist(pts[i0], pts[i1], pts[i]);
        if (d > max_d)
        {
            max_d = d;
            k = i;
        }
    }
    if (max_d > p.split_dist_m)
    {
        splitRecursive(pts, i0, k, p, out);
        splitRecursive(pts, k, i1, p, out);
        return;
    }
    out.push_back({i0, i1});
}

// 직선 위로 점을 사영.
Point2D projectOntoLine(const LineNormalForm &l, const Point2D &q)
{
    const double e = l.nx * q.x_m + l.ny * q.y_m - l.d_m;
    return {q.x_m - e * l.nx, q.y_m - e * l.ny};
}

// [i0, i1] 구간을 적합해 선분으로 만든다.
ExtractedSegment makeSegment(const std::vector<Point2D> &pts, std::size_t i0, std::size_t i1)
{
    ExtractedSegment seg;
    seg.line = fitLineTLS(pts, i0, i1, &seg.rms_m);
    seg.p1 = projectOntoLine(seg.line, pts[i0]);
    seg.p2 = projectOntoLine(seg.line, pts[i1]);
    seg.num_points = static_cast<int>(i1 - i0 + 1);
    seg.length_m = std::hypot(seg.p2.x_m - seg.p1.x_m, seg.p2.y_m - seg.p1.y_m);
    return seg;
}

}  // namespace

std::vector<Point2D> scanToPoints(const std::vector<float> &ranges_m, double angle_min_rad,
                                  double angle_inc_rad, const ExtractParams &p)
{
    std::vector<Point2D> pts;
    pts.reserve(ranges_m.size());
    for (std::size_t i = 0; i < ranges_m.size(); ++i)
    {
        const double r = static_cast<double>(ranges_m[i]);
        if (!std::isfinite(r) || r < p.range_min_m || r > p.range_max_m)
        {
            continue;
        }
        const double a = angle_min_rad + static_cast<double>(i) * angle_inc_rad;
        if (a < p.angle_min_rad || a > p.angle_max_rad)
        {
            continue;
        }
        pts.push_back({r * std::cos(a), r * std::sin(a)});
    }
    return pts;
}

LineNormalForm fitLineTLS(const std::vector<Point2D> &points, std::size_t i0, std::size_t i1,
                          double *rms_m)
{
    const double n = static_cast<double>(i1 - i0 + 1);
    double cx = 0.0;
    double cy = 0.0;
    for (std::size_t i = i0; i <= i1; ++i)
    {
        cx += points[i].x_m;
        cy += points[i].y_m;
    }
    cx /= n;
    cy /= n;

    double sxx = 0.0;
    double sxy = 0.0;
    double syy = 0.0;
    for (std::size_t i = i0; i <= i1; ++i)
    {
        const double dx = points[i].x_m - cx;
        const double dy = points[i].y_m - cy;
        sxx += dx * dx;
        sxy += dx * dy;
        syy += dy * dy;
    }

    // 주성분(최대 분산) 방향각 = 0.5·atan2(2Sxy, Sxx−Syy). 법선은 그 수직.
    const double dir = 0.5 * std::atan2(2.0 * sxy, sxx - syy);
    LineNormalForm l;
    l.nx = -std::sin(dir);
    l.ny = std::cos(dir);
    l.d_m = l.nx * cx + l.ny * cy;
    if (l.d_m < 0.0)
    {
        // 원점 정향 규칙: d ≥ 0 (types.hpp 서두)
        l.nx = -l.nx;
        l.ny = -l.ny;
        l.d_m = -l.d_m;
    }

    if (rms_m != nullptr)
    {
        double ss = 0.0;
        for (std::size_t i = i0; i <= i1; ++i)
        {
            const double e = l.nx * points[i].x_m + l.ny * points[i].y_m - l.d_m;
            ss += e * e;
        }
        *rms_m = std::sqrt(ss / n);
    }
    return l;
}

std::vector<ExtractedSegment> extractSegments(const std::vector<Point2D> &points_lidar,
                                              const ExtractParams &p)
{
    std::vector<ExtractedSegment> segments;
    if (points_lidar.size() < static_cast<std::size_t>(p.min_points))
    {
        return segments;
    }

    // 1) 인접 간격 클러스터링 — 가림·물체 경계에서 끊는다.
    std::vector<std::pair<std::size_t, std::size_t>> clusters;
    std::size_t start = 0;
    for (std::size_t i = 1; i < points_lidar.size(); ++i)
    {
        const double gap = std::hypot(points_lidar[i].x_m - points_lidar[i - 1].x_m,
                                      points_lidar[i].y_m - points_lidar[i - 1].y_m);
        if (gap > p.max_point_gap_m)
        {
            if (i - start >= static_cast<std::size_t>(p.min_points))
            {
                clusters.push_back({start, i - 1});
            }
            start = i;
        }
    }
    if (points_lidar.size() - start >= static_cast<std::size_t>(p.min_points))
    {
        clusters.push_back({start, points_lidar.size() - 1});
    }

    // 2) 클러스터별 split → 공선 병합 → 게이트.
    for (const auto &cl : clusters)
    {
        std::vector<std::pair<std::size_t, std::size_t>> intervals;
        splitRecursive(points_lidar, cl.first, cl.second, p, intervals);

        // 인접 구간 공선 병합 — 같은 벽이 여러 토막으로 나뉘는 것을 붙인다
        // (ANT 도 "short features must be merged into a unique long wall" 을 요구한다).
        std::vector<std::pair<std::size_t, std::size_t>> merged;
        for (const auto &iv : intervals)
        {
            if (!merged.empty())
            {
                const auto &prev = merged.back();
                double rms_prev = 0.0;
                double rms_cur = 0.0;
                const LineNormalForm a = fitLineTLS(points_lidar, prev.first, prev.second, &rms_prev);
                const LineNormalForm b = fitLineTLS(points_lidar, iv.first, iv.second, &rms_cur);
                const double d_ang = std::fabs(
                    normalizeAngle(std::atan2(a.ny, a.nx) - std::atan2(b.ny, b.nx)));
                const Point2D mid_b = {
                    0.5 * (points_lidar[iv.first].x_m + points_lidar[iv.second].x_m),
                    0.5 * (points_lidar[iv.first].y_m + points_lidar[iv.second].y_m)};
                const double d_line = std::fabs(a.nx * mid_b.x_m + a.ny * mid_b.y_m - a.d_m);
                if (d_ang < p.merge_angle_rad && d_line < p.merge_dist_m)
                {
                    merged.back().second = iv.second;
                    continue;
                }
            }
            merged.push_back(iv);
        }

        for (const auto &iv : merged)
        {
            ExtractedSegment seg = makeSegment(points_lidar, iv.first, iv.second);
            if (seg.num_points >= p.min_points && seg.length_m >= p.min_length_m)
            {
                segments.push_back(seg);
            }
        }
    }
    return segments;
}

}  // namespace feature_localizer_core
