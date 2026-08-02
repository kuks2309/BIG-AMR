// mcl2d_core 통합 검증: 합성 사각형 방 맵에서 시뮬레이션 로봇이 직진할 때
// 파티클필터가 실제 자세로 수렴하는지 확인 (외부 테스트 프레임워크 없이 assert).
#include <cassert>
#include <cmath>
#include <cstdio>
#include <random>
#include <vector>

#include "mcl2d_core/particle_filter.hpp"

using namespace mcl2d;

// 10m x 6m 사각형 방의 벽 점군 생성
static std::vector<std::pair<double, double>> makeRoom()
{
    std::vector<std::pair<double, double>> obs;
    const double W = 10.0, H = 6.0, step = 0.05;
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

// 진짜 자세에서 360도 레이저 스캔을 방 벽에 레이캐스트로 합성
static LaserScan simulateScan(const Pose2D &truth, const LaserMount &mount)
{
    LaserScan s;
    s.angle_min = -M_PI;
    s.angle_increment = M_PI / 180.0; // 1도
    s.range_min = 0.05;
    s.range_max = 30.0;
    const double W = 10.0, H = 6.0;
    const double lx = truth.x + mount.x * std::cos(truth.theta) - mount.y * std::sin(truth.theta);
    const double ly = truth.y + mount.x * std::sin(truth.theta) + mount.y * std::cos(truth.theta);
    const double lth = truth.theta + mount.yaw;
    for (int i = 0; i < 360; ++i)
    {
        const double a = lth + s.angle_min + i * s.angle_increment;
        // 사각형 [0,W]x[0,H] 경계까지 거리 레이캐스트
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
    // 관측 우도장 구축 (Seer 충실 ObservationField, 반사판 없음)
    ObservationField field;
    field.build(makeRoom(), {});
    assert(!field.empty());

    Mcl2dParams params;
    params.init_particle_number = 4000;
    params.min_particle_number = 500;
    params.max_particle_number = 4000;
    params.init_dist_scatter = 1.0;  // 초기 불확실 ±1m
    params.init_angle_scatter = 0.5; // ±0.5rad
    params.move_radius = 0.02;
    params.beams_used = 360;

    LaserMount mount; // 로봇 중심 레이저

    ParticleFilter2D pf(params, std::move(field), mount, /*seed=*/7);

    // 진짜 자세: 방 중앙 근처, x로 직진
    Pose2D truth{3.0, 3.0, 0.0};
    pf.initialize(truth); // 초기 추정(±1m 산포)

    Pose2D prev_odom{0, 0, 0};
    Pose2D est;
    for (int t = 0; t < 40; ++t)
    {
        // 진짜 로봇 0.1m/step 직진
        truth.x += 0.1;
        Pose2D cur_odom{prev_odom.x + 0.1, prev_odom.y, 0.0};
        LaserScan scan = simulateScan(truth, mount);
        est = pf.step(prev_odom, cur_odom, scan);
        prev_odom = cur_odom;
    }

    const double ex = std::fabs(est.x - truth.x);
    const double ey = std::fabs(est.y - truth.y);
    std::printf("truth=(%.3f,%.3f) est=(%.3f,%.3f) err=(%.3f,%.3f) meanW=%.4f n=%d\n", truth.x, truth.y, est.x, est.y,
                ex, ey, pf.meanWeight(), static_cast<int>(pf.particles().size()));

    // 수렴 검증: 40스텝 후 추정 오차 < 0.3m
    assert(ex < 0.3 && "x 추정 수렴 실패");
    assert(ey < 0.3 && "y 추정 수렴 실패");
    std::printf("[PASS] mcl2d_core 파티클필터 수렴 검증 통과\n");
    return 0;
}
