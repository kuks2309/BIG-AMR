// 2-rate 구조 회귀 — ADR 2026-08-08-mcl2d-two-rate-pose (debt-044 상환).
//   원본은 오도 주기와 스캔 주기가 하는 일이 다르다:
//     오도 주기 DoMoveAction        : kMove + moveRobotAccordingToMotion(발행 자세 전진) + 발행
//     스캔 주기 DoNormalUpdateAction: 산포 + 우도갱신 + 추정 + 리샘플 (발행 자세는 추정으로 재설정)
//   여기서는 파사드의 두 진입점이 각자의 일만 하는지, 그리고 스캔 없이도 자세가 전진하는지 확인한다.
// NDEBUG 와 무관하게 실패할 수 있도록 자체 CHECK 매크로를 쓴다.
#include <cmath>
#include <cstdio>
#include <utility>
#include <vector>

#include "mcl2d_localizer.hpp"

using namespace mcl2d;

static int g_fail = 0;
#define CHECK(cond, msg)                                                                                               \
    do                                                                                                                 \
    {                                                                                                                  \
        if (!(cond))                                                                                                   \
        {                                                                                                              \
            std::printf("[FAIL] %s  (%s:%d)\n", (msg), __FILE__, __LINE__);                                            \
            ++g_fail;                                                                                                  \
        }                                                                                                              \
    } while (0)

static const double kW = 10.0, kH = 6.0;

static std::vector<std::pair<double, double>> makeRoom()
{
    std::vector<std::pair<double, double>> obs;
    for (double x = 0; x <= kW; x += 0.05)
    {
        obs.emplace_back(x, 0.0);
        obs.emplace_back(x, kH);
    }
    for (double y = 0; y <= kH; y += 0.05)
    {
        obs.emplace_back(0.0, y);
        obs.emplace_back(kW, y);
    }
    return obs;
}

static LaserScan simulateScan(const Pose2D &truth)
{
    LaserScan s;
    s.angle_min = -M_PI;
    s.angle_increment = M_PI / 180.0;
    s.range_min = 0.05;
    s.range_max = 30.0;
    for (int i = 0; i < 360; ++i)
    {
        const double a = truth.theta + s.angle_min + i * s.angle_increment;
        const double ca = std::cos(a), sa = std::sin(a);
        double best = s.range_max;
        if (ca > 1e-9)
            best = std::min(best, (kW - truth.x) / ca);
        if (ca < -1e-9)
            best = std::min(best, (0.0 - truth.x) / ca);
        if (sa > 1e-9)
            best = std::min(best, (kH - truth.y) / sa);
        if (sa < -1e-9)
            best = std::min(best, (0.0 - truth.y) / sa);
        s.ranges.push_back(static_cast<float>(best));
    }
    return s;
}

static Mcl2dParams makeParams()
{
    Mcl2dParams p;
    p.init_particle_number = 800;
    p.init_dist_scatter = 0.05;
    p.init_angle_scatter = 0.02;
    p.beams_used = 360;
    return p;
}

static void setup(Mcl2dLocalizer &loc, const Pose2D &init)
{
    loc.loadMap(makeRoom(), {});
    loc.setLasers({LaserMount{}});
    loc.setInitialPose(init);
}

int main()
{
    const Pose2D init{3.0, 3.0, 0.0};
    const std::vector<LaserScan> scans = {simulateScan(init)};

    // 1) 스캔 없이 오도만으로 발행 자세가 전진한다 (moveRobotAccordingToMotion 이식분).
    //    이 검사는 스캔을 한 번도 넣지 않으므로, 자세 전진이 파티클 평균이 아니라 **자세 자체의
    //    전진**에서 온다는 것을 보장한다.
    {
        Mcl2dLocalizer loc(makeParams(), /*seed=*/11);
        setup(loc, init);
        const Pose2D p = loc.advanceWithOdom({0, 0, 0}, {0.5, 0, 0}, /*stopped=*/false);
        CHECK(std::fabs(p.x - 3.5) < 1e-9, "오도 0.5m 전진이 발행 자세에 반영되지 않았다");
        CHECK(std::fabs(p.y - 3.0) < 1e-9, "y 가 흔들렸다(결정론 이동이어야 한다)");
        CHECK(std::fabs(loc.pose().x - p.x) < 1e-12, "pose() 와 반환값이 다르다");
    }

    // 2) 오도 여러 번 → 스캔 한 번 (실제 2-rate). 전진분이 누적된다.
    {
        Mcl2dLocalizer loc(makeParams(), /*seed=*/11);
        setup(loc, init);
        Pose2D prev{0, 0, 0};
        for (int i = 1; i <= 5; ++i)
        {
            const Pose2D cur{0.1 * i, 0, 0};
            loc.advanceWithOdom(prev, cur, /*stopped=*/false);
            prev = cur;
        }
        CHECK(std::fabs(loc.pose().x - 3.5) < 1e-9, "오도 5회(0.1m씩) 누적 전진이 어긋났다");

        // 스캔 보정 후에는 발행 자세가 파티클 평균(추정)으로 재설정된다.
        const Pose2D est = loc.updateWithScan(scans, prev, /*stopped=*/false, /*dt=*/0.5);
        CHECK(std::fabs(loc.pose().x - est.x) < 1e-12 && std::fabs(loc.pose().y - est.y) < 1e-12,
              "스캔 보정 후 발행 자세가 추정으로 재설정되지 않았다");
    }

    // 3) 정지면 파티클도 발행 자세도 전진하지 않는다 (원본 DoMoveAction @0x3d7d13 의 is_stop 분기).
    {
        Mcl2dLocalizer loc(makeParams(), /*seed=*/11);
        setup(loc, init);
        const Pose2D p = loc.advanceWithOdom({0, 0, 0}, {1.0, 0, 0}, /*stopped=*/true);
        CHECK(std::fabs(p.x - init.x) < 1e-12 && std::fabs(p.y - init.y) < 1e-12,
              "stopped=true 인데 발행 자세가 전진했다");
    }

    // 4) 스캔 주기는 kMove 를 하지 않는다 — updateWithScan 만 반복해도 오도 증분만큼 끌려가지 않는다.
    //    (예전 단일 경로에서는 /odom 이 올 때마다 같은 스캔으로 예측+보정을 반복했다: 코드리뷰 D2)
    {
        Mcl2dLocalizer loc(makeParams(), /*seed=*/11);
        setup(loc, init);
        for (int i = 0; i < 3; ++i)
            loc.updateWithScan(scans, {1.0, 0, 0}, /*stopped=*/false, /*dt=*/0.1);
        const double drift = std::hypot(loc.pose().x - init.x, loc.pose().y - init.y);
        CHECK(drift < 0.2, "updateWithScan 이 오도 증분을 적용했다(kMove 는 오도 주기 소관)");
    }

    // 5) update() 래퍼 == advanceWithOdom + updateWithScan (같은 시드·같은 입력이면 동일 결과).
    {
        Mcl2dLocalizer a(makeParams(), /*seed=*/11), b(makeParams(), /*seed=*/11);
        setup(a, init);
        setup(b, init);
        const Pose2D e1 = a.update({0, 0, 0}, {0.2, 0, 0}, scans, /*stopped=*/false, /*dt=*/0.1);
        b.advanceWithOdom({0, 0, 0}, {0.2, 0, 0}, /*stopped=*/false);
        const Pose2D e2 = b.updateWithScan(scans, {0.2, 0, 0}, /*stopped=*/false, /*dt=*/0.1);
        CHECK(std::fabs(e1.x - e2.x) < 1e-12 && std::fabs(e1.y - e2.y) < 1e-12 &&
                  std::fabs(e1.theta - e2.theta) < 1e-12,
              "update() 래퍼가 두 단계 수행과 다른 결과를 냈다");
    }

    if (g_fail == 0)
        std::printf("[PASS] 2-rate 분리(오도 전진 ↔ 스캔 보정) 검증 통과\n");
    else
        std::printf("[FAIL] %d 건 실패\n", g_fail);
    return g_fail == 0 ? 0 : 1;
}
