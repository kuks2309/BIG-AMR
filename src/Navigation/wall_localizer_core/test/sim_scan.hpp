#ifndef WALL_LOCALIZER_CORE__TEST__SIM_SCAN_HPP_
#define WALL_LOCALIZER_CORE__TEST__SIM_SCAN_HPP_

// 테스트 전용 하니스 — 합성 스캔(벽 선분 레이캐스트) + CHECK 매크로.
// CHECK 는 NDEBUG 와 무관하게 실패한다 (Release 기본 빌드에서도 유효).

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <random>
#include <vector>

#include "wall_localizer_core/types.hpp"

#define CHECK(cond)                                                                          \
    do                                                                                       \
    {                                                                                        \
        if (!(cond))                                                                         \
        {                                                                                    \
            std::fprintf(stderr, "CHECK failed %s:%d: %s\n", __FILE__, __LINE__, #cond);     \
            std::exit(1);                                                                    \
        }                                                                                    \
    } while (0)

#define CHECK_NEAR(a, b, eps)                                                                \
    do                                                                                       \
    {                                                                                        \
        const double _va = (a);                                                              \
        const double _vb = (b);                                                              \
        if (!(std::fabs(_va - _vb) < (eps)))                                                 \
        {                                                                                    \
            std::fprintf(stderr, "CHECK_NEAR failed %s:%d: %s=%.9f vs %s=%.9f (eps=%g)\n",   \
                         __FILE__, __LINE__, #a, _va, #b, _vb, (double)(eps));               \
            std::exit(1);                                                                    \
        }                                                                                    \
    } while (0)

namespace wall_localizer_test
{

// T_station_lidar 자세의 라이다에서 벽 선분들을 레이캐스트한 거리 배열.
// sigma_m > 0 이면 거리 방향 가우시안 잡음(rng 필수). 미충돌 빔은 +inf.
inline std::vector<float> simulateScan(const std::vector<wall_localizer_core::WallRef> &walls,
                                       const wall_localizer_core::Pose2D &T_station_lidar,
                                       double angle_min_rad, double angle_inc_rad, int n_beams,
                                       double range_max_m, double sigma_m, std::mt19937 *rng)
{
    std::normal_distribution<double> noise(0.0, sigma_m > 0.0 ? sigma_m : 1.0);
    std::vector<float> out(static_cast<std::size_t>(n_beams),
                           std::numeric_limits<float>::infinity());
    const double cy = std::cos(T_station_lidar.yaw_rad);
    const double sy = std::sin(T_station_lidar.yaw_rad);
    for (int i = 0; i < n_beams; ++i)
    {
        const double a = angle_min_rad + i * angle_inc_rad;
        // 빔 방향 (스테이션 프레임)
        const double dx = cy * std::cos(a) - sy * std::sin(a);
        const double dy = sy * std::cos(a) + cy * std::sin(a);
        double best = std::numeric_limits<double>::infinity();
        for (const auto &w : walls)
        {
            const double vx = w.p2.x_m - w.p1.x_m;
            const double vy = w.p2.y_m - w.p1.y_m;
            const double det = vx * dy - vy * dx;
            if (std::fabs(det) < 1e-12)
            {
                continue;  // 빔과 벽이 평행
            }
            const double qx = w.p1.x_m - T_station_lidar.x_m;
            const double qy = w.p1.y_m - T_station_lidar.y_m;
            const double r = (vx * qy - vy * qx) / det;
            const double t = (dx * qy - dy * qx) / det;
            if (r > 1e-6 && t >= 0.0 && t <= 1.0 && r < best)
            {
                best = r;
            }
        }
        if (best <= range_max_m)
        {
            const double r_out = (sigma_m > 0.0 && rng != nullptr) ? best + noise(*rng) : best;
            out[static_cast<std::size_t>(i)] = static_cast<float>(r_out);
        }
    }
    return out;
}

}  // namespace wall_localizer_test

#endif  // WALL_LOCALIZER_CORE__TEST__SIM_SCAN_HPP_
