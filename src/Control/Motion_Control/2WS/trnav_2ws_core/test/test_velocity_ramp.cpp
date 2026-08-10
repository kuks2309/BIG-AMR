// rampToward 회귀 — 후진 구간에서 가·감속 한계가 뒤바뀌지 않는지 고정한다.
//
// 왜 필요한가: `yaw_control`(전진판)의 지역 람다는 **부호 있는 비교**를 써서, 후진
// goal(`vx_max < 0`, 액션이 정식 허용)에서 가속에 감속한계를, 제동에 가속한계를 썼다.
// `accel=0.5 · decel=1.0` 이면 설계값의 2배로 가속하고 절반으로 제동한다 — 제동거리 2배.
// 후진판에는 크기 비교 + 부호교차 분기가 있었고 전진판만 빠져 있었다.

#include <gtest/gtest.h>

#include <cmath>

#include "trnav_2ws_core/velocity_ramp.hpp"

using trnav_2ws_core::rampToward;

namespace
{
constexpr double kAccel = 0.5;   // 한 주기 가속 한계
constexpr double kDecel = 1.0;   // 한 주기 감속 한계
} // namespace

// ── 전진: 가속은 가속한계, 감속은 감속한계 ───────────────────────────────
TEST(RampToward, ForwardAccelUsesAccelLimit)
{
    EXPECT_NEAR(rampToward(0.10, 5.0, kAccel, kDecel), 0.60, 1e-12);
}

TEST(RampToward, ForwardDecelUsesDecelLimit)
{
    EXPECT_NEAR(rampToward(5.00, 1.0, kAccel, kDecel), 4.00, 1e-12);
}

// ── 후진: **같은 한계가 같은 역할로** 쓰여야 한다 ────────────────────────
TEST(RampToward, ReverseAccelUsesAccelLimitNotDecel)
{
    // 크기가 커지는 것이 가속이다. 부호 있는 비교라면 `tgt < cur` 이라 감속한계(1.0)를
    // 써서 -1.10 이 나온다 — **설계값의 2배로 가속**한다.
    EXPECT_NEAR(rampToward(-0.60, -5.0, kAccel, kDecel), -1.10, 1e-12)
        << "후진 가속에 감속한계가 쓰였다 — 지령보다 빠르게 가속한다";
}

TEST(RampToward, ReverseDecelUsesDecelLimitNotAccel)
{
    // 크기가 작아지는 것이 감속이다. 부호 있는 비교라면 `tgt > cur` 이라 가속한계(0.5)를
    // 써서 -4.50 이 나온다 — **제동거리가 2배**가 된다.
    EXPECT_NEAR(rampToward(-5.00, -1.0, kAccel, kDecel), -4.00, 1e-12)
        << "후진 제동에 가속한계가 쓰였다 — 제동거리가 늘어난다";
}

TEST(RampToward, ForwardAndReverseAreMirrorImages)
{
    // 전·후진의 램프 거동은 부호를 빼면 같아야 한다. 이것이 깨지면 같은 goal 이
    // 방향에 따라 다른 동특성을 갖는다.
    for (double cur : {0.0, 0.3, 1.0, 4.0})
    {
        for (double tgt : {0.5, 2.0, 5.0})
        {
            const double fwd = rampToward(cur, tgt, kAccel, kDecel);
            const double rev = rampToward(-cur, -tgt, kAccel, kDecel);
            EXPECT_NEAR(fwd, -rev, 1e-12)
                << "cur=" << cur << " tgt=" << tgt << " 에서 전·후진이 대칭이 아니다";
        }
    }
}

// ── 목표 0 · 부호 교차 ───────────────────────────────────────────────────
TEST(RampToward, ZeroTargetDecelsToZeroFromBothSigns)
{
    EXPECT_NEAR(rampToward(3.0, 0.0, kAccel, kDecel), 2.0, 1e-12);
    EXPECT_NEAR(rampToward(-3.0, 0.0, kAccel, kDecel), -2.0, 1e-12);
    EXPECT_NEAR(rampToward(0.5, 0.0, kAccel, kDecel), 0.0, 1e-12) << "한 스텝 안이면 0 으로 붙는다";
}

TEST(RampToward, SignCrossingPassesThroughZeroFirst)
{
    // 정지 없이 방향을 뒤집으면 구동축이 급반전한다. 반드시 0 을 지나야 한다.
    double v = 3.0;
    const double tgt = -3.0;
    bool touched_zero = false;
    for (int i = 0; i < 50; ++i)
    {
        const double next = rampToward(v, tgt, kAccel, kDecel);
        EXPECT_LE(next, v + 1e-12) << "부호 교차 중에 크기가 늘었다";
        if (std::fabs(next) < 1e-12)
            touched_zero = true;
        if (touched_zero && next < 0.0)
            break;
        v = next;
        if (touched_zero)
            v = next;
    }
    EXPECT_TRUE(touched_zero) << "부호를 0 을 지나지 않고 뒤집었다";
}

TEST(RampToward, SettlesExactlyOnTargetWithoutOvershoot)
{
    // 스텝의 배수가 아닌 목표에서도 정확히 정착해야 한다(진동하면 지령이 떨린다).
    for (double tgt : {2.35, -2.35})
    {
        double v = 0.0;
        for (int i = 0; i < 100; ++i)
            v = rampToward(v, tgt, kAccel, kDecel);
        EXPECT_NEAR(v, tgt, 1e-12) << "목표 " << tgt << " 에 정착하지 못했다";
    }
}

TEST(RampToward, NeverExceedsLimitsPerStep)
{
    for (double cur : {-4.0, -1.0, 0.0, 1.0, 4.0})
    {
        for (double tgt : {-5.0, -0.5, 0.5, 5.0})
        {
            const double next = rampToward(cur, tgt, kAccel, kDecel);
            EXPECT_LE(std::fabs(next - cur), std::max(kAccel, kDecel) + 1e-12)
                << "cur=" << cur << " tgt=" << tgt << " 에서 한 주기 변화가 한계를 넘었다";
        }
    }
}
