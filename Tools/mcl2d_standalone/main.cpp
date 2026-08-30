// non-ROS standalone 위치추정 러너 (데모).
// Roll_A084 유사 듀얼 라이다(전+후) 구성으로 합성 방에서 궤적을 추종하며,
// ROS 없이 mcl2d_localizer 만으로 위치추정이 동작함을 입증한다.
#include <cmath>
#include <cstdio>
#include <vector>

#include "mcl2d_localizer.hpp"

using namespace mcl2d;

static std::vector<std::pair<double, double>> makeRoom(double W, double H, double step)
{
    std::vector<std::pair<double, double>> obs;
    for (double x = 0; x <= W; x += step)
    {
        obs.emplace_back(x, 0.0);
        obs.emplace_back(x, H);
    }
    for (double y = 0; y <= H; y += step)
    {
        obs.emplace_back(0.0, y);
        obs.emplace_back(W, y);
    }
    return obs;
}

// 사각형 방 [0,W]x[0,H] 에서 한 라이다의 360도 스캔 합성(레이캐스트).
static LaserScan simScan(const Pose2D &truth, const LaserMount &m, double W, double H)
{
    LaserScan s;
    s.angle_min = -M_PI;
    s.angle_increment = M_PI / 180.0;
    s.range_min = 0.05;
    s.range_max = 30.0;
    const double lx = truth.x + m.x * std::cos(truth.theta) - m.y * std::sin(truth.theta);
    const double ly = truth.y + m.x * std::sin(truth.theta) + m.y * std::cos(truth.theta);
    const double lth = truth.theta + m.yaw;
    for (int i = 0; i < 360; ++i)
    {
        const double a = lth + s.angle_min + i * s.angle_increment;
        double best = s.range_max;
        const double ca = std::cos(a), sa = std::sin(a);
        if (ca > 1e-9)
            best = std::min(best, (W - lx) / ca);
        if (ca < -1e-9)
            best = std::min(best, (0.0 - lx) / ca);
        if (sa > 1e-9)
            best = std::min(best, (H - ly) / sa);
        if (sa < -1e-9)
            best = std::min(best, (0.0 - ly) / sa);
        s.ranges.push_back(static_cast<float>(best));
    }
    return s;
}

int main()
{
    const double W = 12.0, H = 8.0;

    Mcl2dParams params;
    params.init_particle_number = 5000;
    params.min_particle_number = 500;
    params.max_particle_number = 5000;
    params.init_dist_scatter = 1.0;
    params.init_angle_scatter = 0.6;
    params.move_radius = 0.02;
    params.beams_used = 360;

    Mcl2dLocalizer loc(params, /*seed=*/11);
    if (!loc.loadMap(makeRoom(W, H, 0.05)))
    {
        std::fprintf(stderr, "map load failed\n");
        return 1;
    }

    // Roll_A084 듀얼 라이다 배치(전우측/후좌측)
    std::vector<LaserMount> mounts = {
        {0.879, -0.579, -M_PI / 4.0},      // FrontLiDAR yaw -45deg
        {-0.879, 0.579, 3.0 * M_PI / 4.0}, // RearLiDAR  yaw 135deg
    };
    loc.setLasers(mounts);

    Pose2D truth{3.0, 4.0, 0.0};
    loc.setInitialPose(truth); // 초기 추정(±1m 산포)

    Pose2D prev_odom{0, 0, 0};
    Pose2D est;
    std::printf("step  truth(x,y,th)        est(x,y,th)          err(m)  conf\n");
    for (int t = 1; t <= 50; ++t)
    {
        truth.x += 0.12; // 직진
        if (t > 25)
            truth.y += 0.04; // 후반 약간 사선
        Pose2D cur_odom{prev_odom.x + 0.12, prev_odom.y + (t > 25 ? 0.04 : 0.0), 0.0};

        std::vector<LaserScan> scans = {simScan(truth, mounts[0], W, H), simScan(truth, mounts[1], W, H)};
        est = loc.update(prev_odom, cur_odom, scans);
        prev_odom = cur_odom;

        if (t % 10 == 0 || t == 1)
        {
            const double err = std::hypot(est.x - truth.x, est.y - truth.y);
            std::printf("%3d   (%.2f,%.2f,%.2f)   (%.2f,%.2f,%.2f)   %.3f   %.3f\n", t, truth.x, truth.y, truth.theta,
                        est.x, est.y, est.theta, err, loc.confidence());
        }
    }

    const double ferr = std::hypot(est.x - truth.x, est.y - truth.y);
    std::printf("\n최종 오차 %.3f m, 신뢰도 %.3f\n", ferr, loc.confidence());
    if (ferr < 0.3)
    {
        std::printf("[PASS] non-ROS 듀얼 라이다 위치추정 수렴\n");
        return 0;
    }
    std::printf("[FAIL] 수렴 실패\n");
    return 1;
}
