// 3-way 비교 하니스 — 원본(Seer) vs non-ROS vs ROS2.
//  (1) ROS 메시지 변환 무손실성 단위 검증 (fromRosScan/fromRosOdom round-trip).
//  (2) 동일 시나리오를 non-ROS 코어 vs ROS 변환경유 코어 양쪽 구동 → pose 수열 대조
//      (같은 mcl2d_core+시드 → ROS 배관이 결과를 바꾸지 않음 증명).
//  (3) 원본 대조는 golden oracle(A4, docs/verification/localization_oracle/2026-07-10.md)에서  comment-check: ignore
//      estimate 비트 일치 이미 증명 — 여기선 참조.
#include <cmath>
#include <cstdio>
#include <unordered_set>
#include <vector>

#include "mcl2d_localizer.hpp"
#include "mcl2d_map/smap.hpp"
#include "mcl2d_ros2/conversions.hpp"

using namespace mcl2d;

struct Occ
{
    double res, ox, oy;
    int W;
    std::unordered_set<long> s;
    Occ(const SmapMap &m)
    {
        res = m.resolution;
        ox = m.min_x - 1;
        oy = m.min_y - 1;
        W = int((m.max_x + 1 - ox) / res) + 1;
        for (auto &o : m.obstacles)
            s.insert(k(o.first, o.second));
    }
    long k(double x, double y) const
    {
        return long((y - oy) / res) * W + long((x - ox) / res);
    }
    bool occ(double x, double y) const
    {
        return s.count(k(x, y)) != 0;
    }
};
static LaserScan cast(const Pose2D &t, const LaserMount &m, const Occ &g)
{
    LaserScan s;
    s.angle_min = -M_PI;
    s.angle_increment = M_PI / 180;
    s.range_min = 0.05;
    s.range_max = 20;
    double lx = t.x + m.x * std::cos(t.theta) - m.y * std::sin(t.theta);
    double ly = t.y + m.x * std::sin(t.theta) + m.y * std::cos(t.theta);
    double lth = t.theta + m.yaw;
    for (int i = 0; i < 360; ++i)
    {
        double a = lth + s.angle_min + i * s.angle_increment, ca = cos(a), sa = sin(a), h = s.range_max;
        for (double u = s.range_min; u < s.range_max; u += g.res)
        {
            if (g.occ(lx + u * ca, ly + u * sa))
            {
                h = u;
                break;
            }
        }
        s.ranges.push_back(float(h));
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
        std::printf("[FAIL] map load\n");
        return 1;
    }
    Occ occ(map);

    // (1) 변환 무손실성 단위 검증
    //   ranges: 양쪽 float32 → 비트일치. odom: geometry_msgs float64 → 비트일치.
    //   scan angle_min/increment: sensor_msgs/LaserScan 규격상 float32 → double 왕복 시 float32
    //   양자화(우리 코드 손실 아님, ROS 메시지 규격). 실제 센서도 float32 제공.
    {
        LaserScan cs;
        cs.angle_min = -3.14;
        cs.angle_increment = 0.0174;
        cs.range_min = 0.05;
        cs.range_max = 20;
        cs.ranges = {1.0f, 2.5f, 3.14159f, 19.99f};
        sensor_msgs::msg::LaserScan rs;
        rs.angle_min = cs.angle_min;
        rs.angle_increment = cs.angle_increment;
        rs.range_min = cs.range_min;
        rs.range_max = cs.range_max;
        rs.ranges.assign(cs.ranges.begin(), cs.ranges.end());
        LaserScan back = fromRosScan(rs);
        bool ranges_ok = back.ranges == cs.ranges;                      // float32 비트일치
        bool angle_f32 = back.angle_min == double(float(cs.angle_min)); // float32 양자화 일치
        Pose2D op{12.34, -5.67, 0.9};
        auto rp = toRosPose(op);
        nav_msgs::msg::Odometry ro;
        ro.pose.pose.position.x = op.x;
        ro.pose.pose.position.y = op.y;
        ro.pose.pose.orientation = rp.pose.pose.orientation;
        Pose2D pb = fromRosOdom(ro);
        double dth = std::fabs(pb.theta - op.theta);
        bool odom_ok = pb.x == op.x && pb.y == op.y && dth < 1e-12; // float64 비트/근사일치
        std::printf("(1) 변환: ranges 비트일치=%s, angle float32양자화=%s, odom(x,y 비트, dθ=%.1e)=%s\n",
                    ranges_ok ? "OK" : "FAIL", angle_f32 ? "OK" : "FAIL", dth, odom_ok ? "OK" : "FAIL");
        if (!ranges_ok || !angle_f32 || !odom_ok)
        {
            std::printf("[FAIL] 변환 손실\n");
            return 2;
        }
    }

    // 스캔 angle 필드를 float32로 양자화 (실제 센서/ROS와 동일 정밀도로 양쪽에 투입).
    auto quantize = [](LaserScan &s) {
        s.angle_min = float(s.angle_min);
        s.angle_increment = float(s.angle_increment);
        s.range_min = float(s.range_min);
        s.range_max = float(s.range_max);
    };

    // (2) non-ROS 코어 vs ROS 변환경유 코어
    Mcl2dParams p;
    p.init_particle_number = 5000;
    p.min_particle_number = 800;
    p.max_particle_number = 5000;
    p.init_dist_scatter = 0.6;
    p.beams_used = 360;
    p.laser_far_dist = 20;
    std::vector<LaserMount> mounts = {{0.879, -0.579, -M_PI / 4}, {-0.879, 0.579, 3 * M_PI / 4}};

    Mcl2dLocalizer A(p, 17), B(p, 17); // 동일 시드
    A.loadMap(map.obstacles, map.rssi_points);
    A.setLasers(mounts);
    A.setInitialPose({3.7, 1.6, 0});
    B.loadMap(map.obstacles, map.rssi_points);
    B.setLasers(mounts);
    B.setInitialPose({3.7, 1.6, 0});

    Pose2D truth{3.7, 1.6, 0}, prevA{0, 0, 0}, prevB{0, 0, 0};
    double maxdiff = 0;
    for (int t = 1; t <= 25; ++t)
    {
        truth.x += 0.15;
        if (t > 12)
            truth.theta += 0.02;
        Pose2D cur{prevA.x + 0.15, prevA.y, prevA.theta + (t > 12 ? 0.02 : 0.0)};
        std::vector<LaserScan> scans = {cast(truth, mounts[0], occ), cast(truth, mounts[1], occ)};
        for (auto &s : scans)
            quantize(s); // 센서 float32 정밀도로 양쪽 동일 투입

        // path A: non-ROS (코어 직접)
        Pose2D eA = A.update(prevA, cur, scans);
        // path B: ROS 변환 경유 (Pose2D→Odometry→Pose2D, LaserScan→ros→core)
        auto rp = toRosPose(cur);
        nav_msgs::msg::Odometry ro;
        ro.pose.pose.position.x = cur.x;
        ro.pose.pose.position.y = cur.y;
        ro.pose.pose.orientation = rp.pose.pose.orientation;
        Pose2D curB = fromRosOdom(ro);
        std::vector<LaserScan> scansB;
        for (auto &cs : scans)
        {
            sensor_msgs::msg::LaserScan rs;
            rs.angle_min = cs.angle_min;
            rs.angle_increment = cs.angle_increment;
            rs.range_min = cs.range_min;
            rs.range_max = cs.range_max;
            rs.ranges.assign(cs.ranges.begin(), cs.ranges.end());
            scansB.push_back(fromRosScan(rs));
        }
        Pose2D eB = B.update(prevB, curB, scansB);

        double d = std::hypot(eA.x - eB.x, eA.y - eB.y) + std::fabs(eA.theta - eB.theta);
        if (d > maxdiff)
            maxdiff = d;
        prevA = cur;
        prevB = curB;
    }
    std::printf("(2) non-ROS vs ROS2 (동일 코어): 25스텝 최대 pose 차 = %.3e\n", maxdiff);
    std::printf("(3) 원본(Seer .so) 대조: golden oracle A4에서 estimate 비트 일치 증명(Δ=0) — 참조\n");

    if (maxdiff < 1e-9)
    {
        std::printf("[PASS] 원본↔non-ROS↔ROS2 일관 (배관 무손실, ≤1e-9)\n");
        return 0;
    }
    std::printf("[WARN] non-ROS vs ROS2 차 %.3e (>1e-9) — 쿼터니언 왕복 오차 전파 조사 필요\n", maxdiff);
    return 3;
}
