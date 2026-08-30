// non-ROS 실제 맵 데모 — Seer .smap(실 Roll_A084 맵)을 로드해 위치추정 end-to-end 실증.
// 실 맵 점군으로 점유셋을 만들고, 듀얼 라이다 스캔을 레이캐스트로 합성해 로봇 궤적을 추종한다.
//   usage: real_map_demo <map.smap>
#include <cmath>
#include <cstdio>
#include <unordered_set>
#include <vector>

#include "mcl2d_core/motion_model.hpp" // normalizeAngle
#include "mcl2d_localizer.hpp"
#include "mcl2d_map/smap.hpp"

using namespace mcl2d;

// 실 맵 점군 → 점유 셀 집합(스캔 레이캐스트용). 셀 키 = gy*W + gx.
struct OccGrid
{
    double res, ox, oy;
    int W;
    std::unordered_set<long> occ;
    OccGrid(const SmapMap &m)
    {
        res = m.resolution;
        ox = m.min_x - 1.0;
        oy = m.min_y - 1.0;
        W = static_cast<int>((m.max_x + 1.0 - ox) / res) + 1;
        occ.reserve(m.obstacles.size() * 2);
        for (auto &o : m.obstacles)
            occ.insert(key(o.first, o.second));
    }
    long key(double x, double y) const
    {
        long gx = static_cast<long>((x - ox) / res);
        long gy = static_cast<long>((y - oy) / res);
        return gy * W + gx;
    }
    bool occupied(double x, double y) const
    {
        return occ.count(key(x, y)) != 0;
    }
};

// 실 맵 점유셋에 레이캐스트해 한 라이다 스캔 합성.
static LaserScan castScan(const Pose2D &truth, const LaserMount &m, const OccGrid &g)
{
    LaserScan s;
    s.angle_min = -M_PI;
    s.angle_increment = M_PI / 180.0; // 1도, 360빔
    s.range_min = 0.05;
    s.range_max = 20.0;
    const double lx = truth.x + m.x * std::cos(truth.theta) - m.y * std::sin(truth.theta);
    const double ly = truth.y + m.x * std::sin(truth.theta) + m.y * std::cos(truth.theta);
    const double lth = truth.theta + m.yaw;
    for (int i = 0; i < 360; ++i)
    {
        const double a = lth + s.angle_min + i * s.angle_increment;
        const double ca = std::cos(a), sa = std::sin(a);
        double hit = s.range_max;
        for (double t = s.range_min; t < s.range_max; t += g.res)
        {
            if (g.occupied(lx + t * ca, ly + t * sa))
            {
                hit = t;
                break;
            }
        }
        s.ranges.push_back(static_cast<float>(hit));
    }
    return s;
}

int main(int argc, char **argv)
{
    if (argc < 2)
    {
        std::fprintf(stderr, "usage: %s <map.smap>\n", argv[0]);
        return 64;
    }

    SmapMap map = loadSmap(argv[1]);
    if (!map.valid)
    {
        std::printf("[FAIL] .smap 로드 실패: %s\n", argv[1]);
        return 1;
    }
    std::printf("맵: %s | 장애물 %zu | 해상도 %.3f | 명명점 %zu\n", map.map_name.c_str(), map.obstacles.size(),
                map.resolution, map.named_points.size());

    OccGrid occ(map);

    // 위치추정 파라미터 (실 맵 스케일)
    Mcl2dParams p;
    p.init_particle_number = 6000;
    p.min_particle_number = 800;
    p.max_particle_number = 6000;
    p.init_dist_scatter = 0.6;
    p.init_angle_scatter = 0.4;
    p.move_radius = 0.02;
    p.beams_used = 360;
    p.laser_far_dist = 20.0;

    Mcl2dLocalizer loc(p, /*seed=*/17);
    loc.loadMap(map.obstacles, map.rssi_points);

    // Roll_A084 듀얼 라이다
    std::vector<LaserMount> mounts = {{0.879, -0.579, -M_PI / 4}, {-0.879, 0.579, 3 * M_PI / 4}};
    loc.setLasers(mounts);

    // 시작 자세 = 특징 풍부한 명명 위치 부근(LM1002 ≈ (3.7,1.6))
    Pose2D truth{3.7, 1.6, 0.0};
    loc.setInitialPose(truth);

    Pose2D prev_odom{0, 0, 0}, est;
    std::printf("\nstep  truth(x,y,th)         est(x,y,th)          err(m)  conf  state\n");
    const char *stname[] = {"Normal", "Skidding", "LowConf"};
    for (int t = 1; t <= 30; ++t)
    {
        truth.x += 0.15; // 실 맵 자유공간 직진
        if (t > 15)
            truth.theta += 0.02; // 후반 완만한 회전
        Pose2D cur_odom{prev_odom.x + 0.15, prev_odom.y, normalizeAngle(prev_odom.theta + (t > 15 ? 0.02 : 0.0))};

        std::vector<LaserScan> scans = {castScan(truth, mounts[0], occ), castScan(truth, mounts[1], occ)};
        est = loc.update(prev_odom, cur_odom, scans);
        prev_odom = cur_odom;

        if (t % 5 == 0 || t == 1)
        {
            const double err = std::hypot(est.x - truth.x, est.y - truth.y);
            std::printf("%3d   (%.2f,%.2f,%.2f)    (%.2f,%.2f,%.2f)    %.3f   %.2f  %s\n", t, truth.x, truth.y,
                        truth.theta, est.x, est.y, est.theta, err, loc.confidence(),
                        stname[static_cast<int>(loc.reportState())]);
        }
    }
    const double ferr = std::hypot(est.x - truth.x, est.y - truth.y);
    std::printf("\n최종 오차 %.3f m, 신뢰도 %.2f\n", ferr, loc.confidence());
    if (ferr < 0.5)
    {
        std::printf("[PASS] 실제 Roll_A084 맵 위치추정 추종\n");
        return 0;
    }
    std::printf("[FAIL] 추종 실패\n");
    return 2;
}
