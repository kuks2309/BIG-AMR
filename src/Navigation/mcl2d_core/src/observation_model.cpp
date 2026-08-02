#include "mcl2d_core/observation_model.hpp"

#include <algorithm>
#include <cmath>

namespace mcl2d
{
namespace
{

// 한 라이다의 빔을 맵에 투영해 PDF 합·유효빔수를 누적(정규화 전).
void accumulateLaser(const Pose2D &pose, const LaserScan &scan, const LaserMount &mount, const LikelihoodGrid &grid,
                     const Mcl2dParams &params, double &pdf_sum, int &valid)
{
    if (scan.ranges.empty())
        return;
    const double ct = std::cos(pose.theta);
    const double st = std::sin(pose.theta);
    const double lx = pose.x + mount.x * ct - mount.y * st;
    const double ly = pose.y + mount.x * st + mount.y * ct;
    const double ltheta = pose.theta + mount.yaw;

    const int n = static_cast<int>(scan.ranges.size());
    const int target = std::max(1, std::min(params.beams_used, n));
    const int stride = std::max(1, n / target);

    for (int i = 0; i < n; i += stride)
    {
        const double r = scan.ranges[static_cast<std::size_t>(i)];
        if (!(r >= params.laser_close_dist && r <= params.laser_far_dist))
            continue;
        if (scan.range_max > 0.0 && r >= scan.range_max)
            continue;
        const double a = ltheta + scan.angle_min + i * scan.angle_increment;
        pdf_sum += static_cast<double>(grid.probAt(lx + r * std::cos(a), ly + r * std::sin(a)));
        ++valid;
    }
}

} // namespace

double computeLikelihood(const Pose2D &pose, const LaserScan &scan, const LaserMount &mount, const LikelihoodGrid &grid,
                         const Mcl2dParams &params)
{
    if (grid.empty())
        return 0.0;
    double pdf_sum = 0.0;
    int valid = 0;
    accumulateLaser(pose, scan, mount, grid, params, pdf_sum, valid);
    if (valid == 0)
        return 0.0;
    return pdf_sum / static_cast<double>(valid) / params.pdf_max; // Seer 실측 정규화
}

double computeLikelihoodMulti(const Pose2D &pose, const std::vector<LaserScan> &scans,
                              const std::vector<LaserMount> &mounts, const LikelihoodGrid &grid,
                              const Mcl2dParams &params)
{
    if (grid.empty())
        return 0.0;
    const std::size_t k = std::min(scans.size(), mounts.size());
    double pdf_sum = 0.0;
    int valid = 0;
    for (std::size_t i = 0; i < k; ++i)
    {
        accumulateLaser(pose, scans[i], mounts[i], grid, params, pdf_sum, valid);
    }
    if (valid == 0)
        return 0.0;
    // 전 라이다 빔을 합산 후 총 유효빔수로 정규화 (Seer 듀얼 라이다 동일).
    return pdf_sum / static_cast<double>(valid) / params.pdf_max;
}

} // namespace mcl2d
