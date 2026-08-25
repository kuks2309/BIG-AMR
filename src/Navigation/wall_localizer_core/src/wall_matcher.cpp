#include "wall_localizer_core/wall_matcher.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

#include "wall_localizer_core/line_extractor.hpp"

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

std::vector<WallCandidateGroup> matchWallsMulti(const std::vector<PredictedWall> &predicted,
                                                const std::vector<ExtractedSegment> &segments,
                                                const std::vector<OrientedWall> &walls,
                                                const MatchParams &p)
{
    // 예측 벽별 접선축 (겹침 구간 계산용)
    struct WallAxis
    {
        double ux{0.0}, uy{0.0}, len{0.0}, ang{0.0};
        bool ok{false};
    };
    std::vector<WallAxis> axes(predicted.size());
    for (std::size_t pi = 0; pi < predicted.size(); ++pi)
    {
        const PredictedWall &pw = predicted[pi];
        const double ux0 = pw.p2.x_m - pw.p1.x_m;
        const double uy0 = pw.p2.y_m - pw.p1.y_m;
        const double ulen = std::hypot(ux0, uy0);
        if (!pw.side_valid || ulen < 1e-12)
        {
            continue;
        }
        axes[pi] = {ux0 / ulen, uy0 / ulen, ulen, std::atan2(pw.line.ny, pw.line.nx), true};
    }

    // 선분별 최적 벽 1곳 배정 (게이트는 1:1 대응과 동일) → 벽별로 구간을 모은다.
    std::vector<std::vector<std::pair<double, double>>> intervals(predicted.size());
    std::vector<std::vector<std::size_t>> members(predicted.size());
    for (std::size_t si = 0; si < segments.size(); ++si)
    {
        const ExtractedSegment &seg = segments[si];
        double best_score = std::numeric_limits<double>::infinity();
        std::size_t best_pi = predicted.size();
        std::pair<double, double> best_iv{0.0, 0.0};
        for (std::size_t pi = 0; pi < predicted.size(); ++pi)
        {
            if (!axes[pi].ok)
            {
                continue;
            }
            const PredictedWall &pw = predicted[pi];
            const double d_ang =
                std::fabs(normalizeAngle(std::atan2(seg.line.ny, seg.line.nx) - axes[pi].ang));
            if (d_ang > p.gate_angle_rad)
            {
                continue;
            }
            const double d_dist = std::fabs(seg.line.d_m - pw.line.d_m);
            if (d_dist > p.gate_dist_m)
            {
                continue;
            }
            double s1 = axes[pi].ux * (seg.p1.x_m - pw.p1.x_m) +
                        axes[pi].uy * (seg.p1.y_m - pw.p1.y_m);
            double s2 = axes[pi].ux * (seg.p2.x_m - pw.p1.x_m) +
                        axes[pi].uy * (seg.p2.y_m - pw.p1.y_m);
            if (s1 > s2)
            {
                std::swap(s1, s2);
            }
            const double lo = std::max(s1, 0.0);
            const double hi = std::min(s2, axes[pi].len);
            if (hi - lo <= 0.0)
            {
                continue;
            }
            const double score = d_ang / p.gate_angle_rad + d_dist / p.gate_dist_m +
                                 (1.0 - (hi - lo) / axes[pi].len);
            if (score < best_score)
            {
                best_score = score;
                best_pi = pi;
                best_iv = {lo, hi};
            }
        }
        if (best_pi < predicted.size())
        {
            intervals[best_pi].push_back(best_iv);
            members[best_pi].push_back(si);
        }
    }

    // 벽별 구간 합집합 겹침비로 채택 판정.
    std::vector<WallCandidateGroup> groups;
    for (std::size_t pi = 0; pi < predicted.size(); ++pi)
    {
        if (members[pi].empty())
        {
            continue;
        }
        auto &iv = intervals[pi];
        std::sort(iv.begin(), iv.end());
        double covered = 0.0;
        double cur_lo = iv[0].first;
        double cur_hi = iv[0].second;
        for (std::size_t k = 1; k < iv.size(); ++k)
        {
            if (iv[k].first > cur_hi)
            {
                covered += cur_hi - cur_lo;
                cur_lo = iv[k].first;
                cur_hi = iv[k].second;
            }
            else
            {
                cur_hi = std::max(cur_hi, iv[k].second);
            }
        }
        covered += cur_hi - cur_lo;
        const double ratio = covered / axes[pi].len;
        if (ratio < p.min_overlap_ratio)
        {
            continue;
        }
        WallCandidateGroup g;
        g.wall_idx = predicted[pi].wall_idx;
        g.ref_line_station = walls[g.wall_idx].line_station;
        g.seg_indices = members[pi];
        g.combined_overlap_ratio = ratio;
        g.s_lo = iv.front().first;
        g.s_hi = cur_hi;
        for (const auto &e : iv)
        {
            g.s_hi = std::max(g.s_hi, e.second);
        }
        std::size_t seed = members[pi][0];
        for (std::size_t si : members[pi])
        {
            if (segments[si].num_points > segments[seed].num_points)
            {
                seed = si;
            }
        }
        g.seed_line = segments[seed].line;
        groups.push_back(g);
    }
    return groups;
}

bool refitWallFromPoints(const std::vector<Point2D> &points_lidar, const PredictedWall &pred,
                         const WallCandidateGroup &group, const MatchParams &p, int min_points,
                         double gate_angle_rad, ExtractedSegment *out)
{
    const double ux0 = pred.p2.x_m - pred.p1.x_m;
    const double uy0 = pred.p2.y_m - pred.p1.y_m;
    const double ulen = std::hypot(ux0, uy0);
    if (ulen < 1e-12 || out == nullptr)
    {
        return false;
    }
    const double ux = ux0 / ulen;
    const double uy = uy0 / ulen;
    // 접선 구간 = (토막들이 실제 본 구간) ∪ (예측 벽 전장) + 여유 — 토막 커버리지가
    // 낮아도 벽 전장의 점을 회수하고, 예측이 틀린 초기 반복에서는 토막 구간이 보증한다.
    const double s_min = std::min(group.s_lo, 0.0) - p.refit_margin_m;
    const double s_max = std::max(group.s_hi, ulen) + p.refit_margin_m;

    // 1패스: 시드선 중심 회랑 → 적합. 2패스: 그 결과선으로 재중심화해 다시 적합
    // (시드 토막의 기울기 오차가 벽 끝단에서 만드는 이탈을 제거).
    LineNormalForm center = group.seed_line;
    std::vector<Point2D> sel;
    double rms = 0.0;
    LineNormalForm l;
    for (int pass = 0; pass < 2; ++pass)
    {
        sel.clear();
        for (const Point2D &q : points_lidar)
        {
            const double e = center.nx * q.x_m + center.ny * q.y_m - center.d_m;
            if (std::fabs(e) > p.refit_corridor_m)
            {
                continue;
            }
            const double s = ux * (q.x_m - pred.p1.x_m) + uy * (q.y_m - pred.p1.y_m);
            if (s < s_min || s > s_max)
            {
                continue;
            }
            sel.push_back(q);
        }
        if (sel.size() < static_cast<std::size_t>(min_points))
        {
            return false;
        }
        l = fitLineTLS(sel, 0, sel.size() - 1, &rms);
        center = l;
    }
    // 이상치 트림 — 혼합 화소·에지 반사가 회랑 안에 간헐 유입되면 소수 점이 적합을
    // mm 단위로 끌고 간다(실기 한쪽 꼬리 분포로 확인). 척도는 MAD — rms 는 오염만큼
    // 부풀어 3σ 트림이 오염을 통과시킨다.
    for (int pass = 0; pass < 2; ++pass)
    {
        std::vector<double> res(sel.size());
        std::vector<double> abs_dev(sel.size());
        for (std::size_t i = 0; i < sel.size(); ++i)
        {
            res[i] = l.nx * sel[i].x_m + l.ny * sel[i].y_m - l.d_m;
        }
        std::vector<double> tmp = res;
        std::nth_element(tmp.begin(), tmp.begin() + tmp.size() / 2, tmp.end());
        const double med = tmp[tmp.size() / 2];
        for (std::size_t i = 0; i < sel.size(); ++i)
        {
            abs_dev[i] = std::fabs(res[i] - med);
        }
        tmp = abs_dev;
        std::nth_element(tmp.begin(), tmp.begin() + tmp.size() / 2, tmp.end());
        const double scale = std::max(1.4826 * tmp[tmp.size() / 2], 2e-3);
        std::vector<Point2D> kept;
        kept.reserve(sel.size());
        for (std::size_t i = 0; i < sel.size(); ++i)
        {
            if (abs_dev[i] <= 3.0 * scale)
            {
                kept.push_back(sel[i]);
            }
        }
        if (kept.size() == sel.size() || kept.size() < static_cast<std::size_t>(min_points))
        {
            break;
        }
        sel.swap(kept);
        l = fitLineTLS(sel, 0, sel.size() - 1, &rms);
    }
    // 재적합이 예측과 크게 벌어지면 회랑에 잡물이 섞였거나 예측이 틀린 것 — 기각.
    const double d_ang = std::fabs(normalizeAngle(
        std::atan2(l.ny, l.nx) - std::atan2(pred.line.ny, pred.line.nx)));
    if (d_ang > gate_angle_rad)
    {
        return false;
    }

    const double tx = -l.ny;  // 재적합 직선의 접선
    const double ty = l.nx;
    std::size_t i_min = 0;
    std::size_t i_max = 0;
    double t_min = std::numeric_limits<double>::infinity();
    double t_max = -std::numeric_limits<double>::infinity();
    for (std::size_t i = 0; i < sel.size(); ++i)
    {
        const double t = tx * sel[i].x_m + ty * sel[i].y_m;
        if (t < t_min)
        {
            t_min = t;
            i_min = i;
        }
        if (t > t_max)
        {
            t_max = t;
            i_max = i;
        }
    }
    const auto project = [&l](const Point2D &q) -> Point2D {
        const double e = l.nx * q.x_m + l.ny * q.y_m - l.d_m;
        return {q.x_m - e * l.nx, q.y_m - e * l.ny};
    };
    out->line = l;
    out->p1 = project(sel[i_min]);
    out->p2 = project(sel[i_max]);
    out->num_points = static_cast<int>(sel.size());
    out->length_m = std::hypot(out->p2.x_m - out->p1.x_m, out->p2.y_m - out->p1.y_m);
    out->rms_m = rms;
    return true;
}

}  // namespace wall_localizer_core
