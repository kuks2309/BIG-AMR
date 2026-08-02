#include "mcl2d_core/likelihood_grid.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace mcl2d
{

void LikelihoodGrid::build(const std::vector<std::pair<double, double>> &obstacles, double resolution, double sigma,
                           double max_dist)
{
    resolution_ = resolution;
    if (obstacles.empty())
    {
        data_.clear();
        width_ = height_ = 0;
        return;
    }

    // 경계 박스 (max_dist 만큼 여유)
    double min_x = std::numeric_limits<double>::max();
    double min_y = std::numeric_limits<double>::max();
    double max_x = std::numeric_limits<double>::lowest();
    double max_y = std::numeric_limits<double>::lowest();
    for (const auto &o : obstacles)
    {
        min_x = std::min(min_x, o.first);
        min_y = std::min(min_y, o.second);
        max_x = std::max(max_x, o.first);
        max_y = std::max(max_y, o.second);
    }
    origin_x_ = min_x - max_dist;
    origin_y_ = min_y - max_dist;
    width_ = static_cast<int>((max_x + max_dist - origin_x_) / resolution_) + 1;
    height_ = static_cast<int>((max_y + max_dist - origin_y_) / resolution_) + 1;

    // 거리 변환: 각 셀에서 가장 가까운 장애물까지 거리.
    // (브루트포스 — 맵 빌드는 1회성. 대형맵은 추후 kd-tree/BFS 로 최적화 = 구현 부채 후보.)
    const double inf = std::numeric_limits<double>::max();
    std::vector<double> dist(static_cast<std::size_t>(width_) * height_, inf);
    for (const auto &o : obstacles)
    {
        int ox = static_cast<int>((o.first - origin_x_) / resolution_);
        int oy = static_cast<int>((o.second - origin_y_) / resolution_);
        int reach = static_cast<int>(max_dist / resolution_) + 1;
        for (int gy = std::max(0, oy - reach); gy <= std::min(height_ - 1, oy + reach); ++gy)
        {
            for (int gx = std::max(0, ox - reach); gx <= std::min(width_ - 1, ox + reach); ++gx)
            {
                double cx = origin_x_ + (gx + 0.5) * resolution_;
                double cy = origin_y_ + (gy + 0.5) * resolution_;
                double d = std::hypot(cx - o.first, cy - o.second);
                double &cell = dist[static_cast<std::size_t>(gy) * width_ + gx];
                if (d < cell)
                    cell = d;
            }
        }
    }

    // 거리 → 가우시안 PDF → 0~255 양자화. (peak=255 at d=0)
    data_.assign(static_cast<std::size_t>(width_) * height_, 0);
    const double inv2s2 = 1.0 / (2.0 * sigma * sigma);
    for (std::size_t i = 0; i < dist.size(); ++i)
    {
        if (dist[i] == inf)
            continue;
        double p = std::exp(-(dist[i] * dist[i]) * inv2s2); // 0..1
        data_[i] = static_cast<std::uint8_t>(std::lround(p * 255.0));
    }
}

std::uint8_t LikelihoodGrid::probAt(double x, double y) const
{
    int gx, gy;
    if (data_.empty() || !worldToGrid(x, y, gx, gy))
        return 0;
    return data_[static_cast<std::size_t>(gy) * width_ + gx];
}

} // namespace mcl2d
