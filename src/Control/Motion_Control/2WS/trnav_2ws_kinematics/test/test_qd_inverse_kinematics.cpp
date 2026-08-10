// TwoWsDualSteerIK 회귀 — 제자리 회전 자세 강제와 원호 조향 항등식을 고정한다.
//
// 왜 필요한가: `computeSpin` 은 범용 IK 를 **풀지 않고** ±90° 를 강제한다. 예전에는
// `compute({0,0,ω})` 로 풀었는데, 그 결과가 `wheels_[i].y == 0` 에 전적으로 의존해
// 기하 파라미터가 어긋나면 **조용히 다른 자세**가 나왔다 — QD 기본값(±0.330, ±0.135)이
// 흘러들어와 −67.75°(양 축 같은 부호)가 나오고 제자리 회전이 187 mm 병진이 된 사례가 있다.
// 그 강제와 `isInline` 전제 검사가 여기서 고정하는 성질이다.
//
// 원호 조향 항등식(`atan(x_i / R)`)도 함께 고정한다 — 실기에서 R=1.0 m 에
// 전륜 +31.13° / 후륜 −30.80° 로 나왔고, 그 비대칭(0.33°)이 실측 기하가 쓰이고 있다는 증거다.
// 대칭 근사로 되돌아가면 이 시험이 잡는다.

#include <gtest/gtest.h>

#include <cmath>
#include <vector>

#include "trnav_2ws_kinematics/qd_inverse_kinematics.hpp"

using trnav::motion::two_ws::IKResult;
using trnav::motion::two_ws::TwoWsDualSteerIK;
using trnav::motion::two_ws::VelocityCommand;
using trnav::motion::two_ws::WheelPosition;

namespace
{

// Foil_A082 실측 기하(정본 `trnav_2ws_core/config/robot_geometry_2ws.yaml`).
constexpr double kW1X = 0.6039;
constexpr double kW2X = -0.5961;
constexpr double kRadius = 0.125;
constexpr double kGearWalk = 32.0;

TwoWsDualSteerIK makeInline()
{
    return TwoWsDualSteerIK({{kW1X, 0.0}, {kW2X, 0.0}}, kRadius, kGearWalk);
}

// QD 대각 배치 — 이 스택의 기체가 **아니다**. 전제 검사가 잡아야 하는 값.
TwoWsDualSteerIK makeDiagonal()
{
    return TwoWsDualSteerIK({{0.330, 0.135}, {-0.330, -0.135}}, 0.080, 20.0);
}

double deg(double rad) { return rad * 180.0 / M_PI; }

} // namespace

// ── 인라인 전제 ───────────────────────────────────────────────────────────
TEST(TwoWsDualSteerIK, IsInlineTrueForCenterlineWheels)
{
    EXPECT_TRUE(makeInline().isInline());
}

TEST(TwoWsDualSteerIK, IsInlineFalseForDiagonalLayout)
{
    EXPECT_FALSE(makeDiagonal().isInline())
        << "QD 대각 배치를 인라인으로 통과시키면 computeSpin 의 ±90° 강제 근거가 무너진다";
}

TEST(TwoWsDualSteerIK, IsInlineRespectsTolerance)
{
    TwoWsDualSteerIK ik({{kW1X, 0.0005}, {kW2X, -0.0005}}, kRadius, kGearWalk);
    EXPECT_TRUE(ik.isInline(1e-3)) << "1 mm 허용 안에서 거짓이 됐다";
    EXPECT_FALSE(ik.isInline(1e-4)) << "0.1 mm 허용인데 참이 됐다";
}

// ── 제자리 회전 자세는 **강제**된다 ───────────────────────────────────────
TEST(TwoWsDualSteerIK, SpinForcesNinetyDegreesRegardlessOfMagnitude)
{
    auto ik = makeInline();
    for (double w : {0.05, 0.5, 2.0})
    {
        auto r = ik.computeSpin(w);
        ASSERT_EQ(r.wheels.size(), 2u);
        EXPECT_NEAR(std::fabs(deg(r.wheels[0].steer_rad)), 90.0, 1e-9) << "ω=" << w;
        EXPECT_NEAR(std::fabs(deg(r.wheels[1].steer_rad)), 90.0, 1e-9) << "ω=" << w;
    }
}

TEST(TwoWsDualSteerIK, SpinSteerSignsAreOppositeFrontAndRear)
{
    auto r = makeInline().computeSpin(0.5);
    EXPECT_LT(r.wheels[0].steer_rad * r.wheels[1].steer_rad, 0.0)
        << "앞뒤 조향 부호가 같다 — x_i 부호로 갈려야 한다(제자리 회전이 병진이 된다)";
}

TEST(TwoWsDualSteerIK, SpinSteerFlipsWithOmegaDirection)
{
    auto ik = makeInline();
    auto pos = ik.computeSpin(+0.5);
    auto neg = ik.computeSpin(-0.5);
    EXPECT_LT(pos.wheels[0].steer_rad * neg.wheels[0].steer_rad, 0.0)
        << "ω 부호를 뒤집었는데 같은 조향이 나왔다";
}

TEST(TwoWsDualSteerIK, SpinWheelSpeedIsOmegaTimesLeverArm)
{
    const double w = 0.5;
    auto r = makeInline().computeSpin(w);
    EXPECT_NEAR(r.wheels[0].wheel_speed, std::fabs(w * kW1X), 1e-9);
    EXPECT_NEAR(r.wheels[1].wheel_speed, std::fabs(w * kW2X), 1e-9);
}

TEST(TwoWsDualSteerIK, SpinPostureDoesNotDependOnGeometryErrors)
{
    // 강제이므로 y 가 어긋나도 자세는 ±90° 여야 한다. 예전 방식(범용 IK)이라면
    // 여기서 다른 각이 나왔다 — 그것이 조용한 실패의 형태였다.
    TwoWsDualSteerIK skewed({{kW1X, 0.05}, {kW2X, -0.05}}, kRadius, kGearWalk);
    auto r = skewed.computeSpin(0.5);
    EXPECT_NEAR(std::fabs(deg(r.wheels[0].steer_rad)), 90.0, 1e-9);
    EXPECT_NEAR(std::fabs(deg(r.wheels[1].steer_rad)), 90.0, 1e-9);
}

// ── 원호 조향 항등식 ──────────────────────────────────────────────────────
TEST(TwoWsDualSteerIK, ArcSteerMatchesAtanOfLeverOverRadius)
{
    const double R = 1.0;
    const double omega = 0.05;      // rad/s
    const double vx = omega * R;    // 0.05 m/s
    auto r = makeInline().compute({vx, 0.0, omega});

    EXPECT_NEAR(deg(r.wheels[0].steer_rad), deg(std::atan(kW1X / R)), 1e-6);
    EXPECT_NEAR(deg(r.wheels[1].steer_rad), deg(std::atan(kW2X / R)), 1e-6);
    // 실기 실측값과의 대조(전륜 +31.13° / 후륜 −30.80°).
    EXPECT_NEAR(deg(r.wheels[0].steer_rad), 31.13, 0.01);
    EXPECT_NEAR(deg(r.wheels[1].steer_rad), -30.80, 0.01);
}

TEST(TwoWsDualSteerIK, ArcSteerIsAsymmetricBecauseGeometryIs)
{
    // 전후 레버암이 다르므로(0.6039 대 0.5961) 조향각도 대칭이 아니다.
    // 대칭 근사(|앞| == |뒤|)로 되돌아가면 이 시험이 잡는다.
    auto r = makeInline().compute({0.05, 0.0, 0.05});
    const double f = std::fabs(deg(r.wheels[0].steer_rad));
    const double b = std::fabs(deg(r.wheels[1].steer_rad));
    EXPECT_GT(f - b, 0.2) << "전후 조향각 차이가 사라졌다 — 대칭 근사로 되돌아갔는가";
    EXPECT_LT(f - b, 0.5);
}

// ── ±90° 정규화 ───────────────────────────────────────────────────────────
TEST(TwoWsDualSteerIK, SteerIsNormalizedToPlusMinusNinety)
{
    auto ik = makeInline();
    for (double vx : {-1.0, -0.1, 0.1, 1.0})
    {
        for (double vy : {-1.0, 0.0, 1.0})
        {
            auto r = ik.compute({vx, vy, 0.0});
            for (const auto &w : r.wheels)
            {
                EXPECT_LE(std::fabs(w.steer_rad), M_PI / 2.0 + 1e-9)
                    << "vx=" << vx << " vy=" << vy << " 조향이 ±90° 를 넘었다";
            }
        }
    }
}

TEST(TwoWsDualSteerIK, ReverseCommandFlipsDirectionNotSteer)
{
    auto ik = makeInline();
    auto fwd = ik.compute({0.2, 0.0, 0.0});
    auto rev = ik.compute({-0.2, 0.0, 0.0});
    for (size_t i = 0; i < 2; ++i)
    {
        EXPECT_NEAR(fwd.wheels[i].steer_rad, rev.wheels[i].steer_rad, 1e-9)
            << "직진 후진에서 조향이 달라졌다 — 방향은 direction 이 담아야 한다";
        EXPECT_EQ(fwd.wheels[i].direction, -rev.wheels[i].direction);
        EXPECT_NEAR(fwd.wheels[i].wheel_speed, rev.wheels[i].wheel_speed, 1e-9);
    }
}

TEST(TwoWsDualSteerIK, WheelSpeedIsNonNegative)
{
    auto ik = makeInline();
    for (double vx : {-0.5, 0.0, 0.5})
    {
        auto r = ik.compute({vx, 0.0, 0.3});
        for (const auto &w : r.wheels)
            EXPECT_GE(w.wheel_speed, 0.0) << "속도는 크기이며 부호는 direction 이 담는다";
    }
}
