// SteerHoldIk(2WS) 단위 검증 — 저속 임계에서 조향이 0 으로 복귀하지 않고 유지되는가.
//
// 근거: trnav_2ws_kinematics 의 IK 는 |v| < 1e-6 에서 조향을 0 으로 되돌린다.
// 속도가 0 을 관통하는 순간(재접근 반전·완료 직전) 조향 0 복귀는 접지 마찰로 차체를
// 민다 — 정본이 금지한 동작. 어댑터가 바퀴별로 직전 조향을 유지해야 한다.
#include "dock_control/dock_ik.hpp"

#include <cmath>
#include <cstdio>
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

// 2WS 인라인 실측 기하 (docs/adr — trnav_2ws 기하 정본)
dock_control::DockGeometry inlineGeom()
{
    dock_control::DockGeometry g;
    g.w1_x = 0.6039;
    g.w1_y = 0.0;
    g.w2_x = -0.6039;
    g.w2_y = 0.0;
    g.wheel_radius_m = 0.08;
    g.gear_walk = 20.0;
    return g;
}

}  // namespace

int main()
{
    using dock_control::SteerHoldIk;

    // 1) 정상 속도에서 crab 45° 지령 → 두 축 모두 45°
    {
        SteerHoldIk ik(inlineGeom(), 1e-6);
        const auto c = ik.compute(0.1, 0.1, 0.0);
        check(std::fabs(c.af - kPi / 4) < 1e-9 && std::fabs(c.ar - kPi / 4) < 1e-9,
              "crab 45deg both axles");
        check(c.vf > 0.0 && c.vr > 0.0, "positive speeds");
    }

    // 2) 속도 0 관통 — 직전 조향(45°)이 유지돼야 한다 (IK 원값은 0° 복귀)
    {
        SteerHoldIk ik(inlineGeom(), 1e-6);
        ik.compute(0.1, 0.1, 0.0);            // 45° 각인
        const auto c = ik.compute(0.0, 0.0, 0.0);  // 정지
        check(std::fabs(c.af - kPi / 4) < 1e-9 && std::fabs(c.ar - kPi / 4) < 1e-9,
              "steer held at 45deg through zero speed");
        check(std::fabs(c.vf) < 1e-12 && std::fabs(c.vr) < 1e-12, "speeds zero while holding");
    }

    // 3) resetHold — 유지 이력이 지워지면 정지 지령은 IK 원값(0°)을 낸다
    {
        SteerHoldIk ik(inlineGeom(), 1e-6);
        ik.compute(0.1, 0.1, 0.0);
        ik.resetHold();
        const auto c = ik.compute(0.0, 0.0, 0.0);
        check(std::fabs(c.af) < 1e-12 && std::fabs(c.ar) < 1e-12,
              "after resetHold zero-speed steer is IK raw (0)");
    }

    // 4) 바퀴별 판정 — 순수 공전(vx=vy=0, ω≠0)은 인라인 기하에서 양 바퀴 속도가 살아
    //    있으므로 ±90° 강제 없이도 유지 경로를 타지 않는다(속도 = |ω·x_i| > 임계)
    {
        SteerHoldIk ik(inlineGeom(), 1e-6);
        const auto c = ik.compute(0.0, 0.0, 0.5);
        check(std::fabs(std::fabs(c.af) - kPi / 2) < 1e-9 &&
                  std::fabs(std::fabs(c.ar) - kPi / 2) < 1e-9,
              "spin via free IK gives +-90 on inline geometry");
        // 자유 IK 의 회전 표현: 조향 부호가 반대(전 +90°/후 −90°)이고 속도는 양수 —
        // 「같은 조향, 속도 반대」와 물리적으로 동일한 다른 표현이다.
        check(c.af * c.ar < 0.0, "spin steer signs opposite");
        check(c.vf > 0.0 && c.vr > 0.0, "spin speeds positive in free-IK representation");
    }

    // 5) lastSteer 조회 — 유지 중 값 반환
    {
        SteerHoldIk ik(inlineGeom(), 1e-6);
        double af = 0.0, ar = 0.0;
        check(!ik.lastSteer(af, ar), "no last steer before first compute");
        ik.compute(0.1, 0.0, 0.0);
        check(ik.lastSteer(af, ar) && std::fabs(af) < 1e-12, "last steer recorded");
    }

    if (g_fail == 0)
    {
        std::printf("steer_hold_check: PASS\n");
    }
    return g_fail == 0 ? 0 : 1;
}
