// 파사드(Mcl2dLocalizer) 정지 경로 검증 — 코드리뷰 2026-07-31 M3.
//   원본 DoMoveAction @0x3d7d13 은 cv.is_stop 이면 kMove(결정론 이동)를 건너뛴다.
//   그 분기가 실제로 동작하는지, 그리고 산포 모드 진단 접근자가 값을 채우는지 확인한다.
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

// 사각형 방 경계까지 레이캐스트한 360빔 스캔 (로봇 중심 라이다)
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

// 같은 입력에 stopped 만 다르게 준 뒤 추정 자세의 이동량을 돌려준다.
static double runOnce(bool stopped, const Pose2D &init, const Pose2D &cur_odom, const std::vector<LaserScan> &scans,
                      ExtraMoveParams *mode_out, double *w_out)
{
    Mcl2dParams params;
    params.init_particle_number = 800;
    params.init_dist_scatter = 0.05; // 초기 불확실 작게 → 이동 여부가 또렷하게 보인다
    params.init_angle_scatter = 0.02;
    params.beams_used = 360;

    Mcl2dLocalizer loc(params, /*seed=*/11);
    loc.loadMap(makeRoom(), {});
    loc.setLasers({LaserMount{}});
    loc.setInitialPose(init);

    const Pose2D est = loc.update({0, 0, 0}, cur_odom, scans, stopped, /*dt=*/0.1);
    if (mode_out)
        *mode_out = loc.lastExtraMove();
    if (w_out)
        *w_out = loc.lastModeLikelihood();
    return std::hypot(est.x - init.x, est.y - init.y);
}

int main()
{
    const Pose2D init{3.0, 3.0, 0.0};
    const std::vector<LaserScan> scans = {simulateScan(init)}; // 초기 자세에서 본 스캔

    // 오도는 1m 전진을 보고한다 — 이 증분이 파티클에 적용되는지가 관건.
    const Pose2D cur_odom{1.0, 0.0, 0.0};

    ExtraMoveParams mode_moving{}, mode_stopped{};
    double w_moving = 0.0, w_stopped = 0.0;
    const double moved = runOnce(/*stopped=*/false, init, cur_odom, scans, &mode_moving, &w_moving);
    const double held = runOnce(/*stopped=*/true, init, cur_odom, scans, &mode_stopped, &w_stopped);

    std::printf("stopped=false 이동 %.3f m · stopped=true 이동 %.3f m (mode %d/%d, w %.4f/%.4f)\n", moved, held,
                mode_moving.mode, mode_stopped.mode, w_moving, w_stopped);

    // 1) 정지가 아니면 오도 증분이 반영돼 추정이 크게 움직인다.
    CHECK(moved > 0.5, "stopped=false 인데 오도 증분이 반영되지 않았다");
    // 2) 정지면 kMove 를 건너뛰므로 추정이 거의 제자리다(남는 것은 ExtraMove 산포뿐, 반폭 ≤ 20mm).
    CHECK(held < 0.05, "stopped=true 인데 파티클이 전진했다");
    // 3) 두 경로의 차이가 분명해야 회귀에서 잡힌다.
    CHECK(moved > held * 5.0, "정지/이동 경로 차이가 불충분");

    // 4) 진단 접근자(H2 노출용)가 실제로 채워진다.
    CHECK(mode_moving.mode >= 1 && mode_moving.mode <= 5, "모드 번호 범위");
    CHECK(mode_moving.radius > 0.0 && mode_moving.angle > 0.0, "산포 크기 미설정");
    CHECK(w_moving >= 0.0, "모드 판정 우도 미설정");

    if (g_fail == 0)
        std::printf("[PASS] 파사드 정지 경로(kMove 생략) + 산포 모드 진단 검증 통과\n");
    else
        std::printf("[FAIL] %d 건 실패\n", g_fail);
    return g_fail == 0 ? 0 : 1;
}
