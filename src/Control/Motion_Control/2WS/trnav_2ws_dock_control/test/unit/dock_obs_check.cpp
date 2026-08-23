// dock_obs 단위 검증 — 관측 변환의 축 분해·프레임 회전·부호·wrap 을 못박는다.
//
// 물리 규칙: e_d > 0 = 접근축 앞에 목표가 남음(전진 필요), e_lat > 0 = 접근축의
// 좌수 +90° 방향에 목표. 이 부호가 뒤집히면 제어가 목표에서 멀어지는 쪽으로 민다.
#include "dock_control/dock_obs.hpp"

#include <cmath>
#include <cstdio>
#include <limits>
#include <string>

namespace
{
constexpr double kPi = 3.14159265358979323846;
int g_fail = 0;

void check(bool ok, const std::string &what)
{
    if (!ok)
    {
        ++g_fail;
        std::printf("  FAIL  %s\n", what.c_str());
    }
}

bool near(double a, double b, double eps = 1e-12)
{
    return std::fabs(a - b) < eps;
}

}  // namespace

int main()
{
    using dock_control::DockTargetPose;
    using dock_control::StationPose;
    using dock_control::wallPoseToDockObs;

    // 1) 항등 — 목표 위에 있으면 전 축 0
    {
        const auto o = wallPoseToDockObs({1.0, 2.0, 0.3}, {1.0, 2.0, 0.3}, 0.0);
        check(o.valid && near(o.e_d_m, 0.0) && near(o.e_lat_m, 0.0) && near(o.e_yaw_deg, 0.0),
              "identity → all zero");
    }

    // 2) 전방 접근축(0): 목표가 +x 앞 0.5 m → e_d=+0.5, e_lat=0
    {
        const auto o = wallPoseToDockObs({0.0, 0.0, 0.0}, {0.5, 0.0, 0.0}, 0.0);
        check(near(o.e_d_m, 0.5) && near(o.e_lat_m, 0.0), "forward offset → e_d only");
    }

    // 3) 수평: 목표가 +y 0.2 → e_lat=+0.2 (접근축 0 의 좌수 +90° = +y)
    {
        const auto o = wallPoseToDockObs({0.0, 0.0, 0.0}, {0.0, 0.2, 0.0}, 0.0);
        check(near(o.e_d_m, 0.0) && near(o.e_lat_m, 0.2), "lateral offset → e_lat only");
    }

    // 4) 로봇이 +90° 돌아 있으면 스테이션 +y 목표가 base +x — 접근축 0 기준 e_d 로 잡힌다
    {
        const auto o = wallPoseToDockObs({0.0, 0.0, kPi / 2}, {0.0, 0.4, kPi / 2}, 0.0);
        check(near(o.e_d_m, 0.4) && near(o.e_lat_m, 0.0) && near(o.e_yaw_deg, 0.0),
              "robot rotated +90 → station +y maps to e_d");
    }

    // 5) 접근축 +90°(좌측 접근): base +y 목표가 e_d, base +x 목표가 e_lat=−(+x)…
    //    u=+y, n=u 의 +90° = −x ⇒ 목표 +x 0.3 → e_lat = −0.3
    {
        const auto oy = wallPoseToDockObs({0.0, 0.0, 0.0}, {0.0, 0.6, 0.0}, kPi / 2);
        check(near(oy.e_d_m, 0.6) && near(oy.e_lat_m, 0.0), "axis +90: +y → e_d");
        const auto ox = wallPoseToDockObs({0.0, 0.0, 0.0}, {0.3, 0.0, 0.0}, kPi / 2);
        check(near(ox.e_d_m, 0.0) && near(ox.e_lat_m, -0.3), "axis +90: +x → e_lat = -0.3");
    }

    // 6) 목표를 지나쳤으면 e_d < 0 (재접근 방향)
    {
        const auto o = wallPoseToDockObs({1.0, 0.0, 0.0}, {0.7, 0.0, 0.0}, 0.0);
        check(near(o.e_d_m, -0.3), "past target → e_d negative");
    }

    // 7) yaw wrap — 179° vs −179° 차이는 +2° 로 나와야 한다(358° 아님)
    {
        const auto o = wallPoseToDockObs({0.0, 0.0, 179.0 * kPi / 180.0},
                                         {0.0, 0.0, -179.0 * kPi / 180.0}, 0.0);
        check(near(o.e_yaw_deg, 2.0, 1e-9), "yaw wrap across ±180");
    }

    // 8) 비유한 입력 → valid=false (축값 소비 금지)
    {
        const auto o = wallPoseToDockObs({std::numeric_limits<double>::quiet_NaN(), 0.0, 0.0},
                                         {0.0, 0.0, 0.0}, 0.0);
        check(!o.valid, "NaN input → invalid");
    }

    if (g_fail == 0)
    {
        std::printf("dock_obs_check: PASS\n");
    }
    return g_fail == 0 ? 0 : 1;
}
