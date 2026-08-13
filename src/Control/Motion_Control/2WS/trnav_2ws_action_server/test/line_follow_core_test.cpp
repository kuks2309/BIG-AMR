// line_follow 제어 코어 단위테스트 — ROS 없이 순수 수학·상태기계만 검증한다.

#include <gtest/gtest.h>

#include "trnav_2ws_action_server/line_follow/line_follow_core.hpp"

using trnav_2ws_action_server::line_follow::computeCommand;
using trnav_2ws_action_server::line_follow::Gains;
using trnav_2ws_action_server::line_follow::LostCoastFsm;
using trnav_2ws_action_server::line_follow::Phase;
using trnav_2ws_action_server::line_follow::rampSpeed;

namespace
{
Gains defaultGains()
{
    Gains g;
    g.kp_offset = 1.2;
    g.kd_offset = 0.15;
    g.kp_angle = 0.6;
    g.max_steer_rad = 25.0 * M_PI / 180.0;
    g.slow_gain = 0.7;
    return g;
}
} // namespace

// ── 부호 규약 ──
// offset(+) = 라인이 진행방향 기준 오른쪽 → 진행방향을 오른쪽으로 돌려야 한다.
// counter-steer 자전거에서 omega = 2*vx*tan(delta)/L 이므로 전진은 delta<0, 후진은 delta>0.

TEST(LineFollowCore, ForwardRightOffsetSteersNegative)
{
    const auto cmd = computeCommand(0.3, 0.0, 0.0, 0.5, /*reverse=*/false, defaultGains());
    EXPECT_LT(cmd.steer_rad, 0.0);
}

TEST(LineFollowCore, ForwardLeftOffsetSteersPositive)
{
    const auto cmd = computeCommand(-0.3, 0.0, 0.0, 0.5, false, defaultGains());
    EXPECT_GT(cmd.steer_rad, 0.0);
}

TEST(LineFollowCore, ReverseFlipsSteerSign)
{
    const auto fwd = computeCommand(0.3, 0.0, 0.0, 0.5, false, defaultGains());
    const auto rev = computeCommand(0.3, 0.0, 0.0, 0.5, true, defaultGains());
    EXPECT_NEAR(fwd.steer_rad, -rev.steer_rad, 1e-12);
    EXPECT_GT(rev.steer_rad, 0.0);
}

TEST(LineFollowCore, AngleTermAddsInSameDirectionAsOffset)
{
    const auto only_offset = computeCommand(0.2, 0.0, 0.0, 0.5, false, defaultGains());
    const auto with_angle = computeCommand(0.2, 0.0, 0.2, 0.5, false, defaultGains());
    EXPECT_LT(with_angle.steer_rad, only_offset.steer_rad); // 더 큰 음의 조향
}

TEST(LineFollowCore, DerivativeTermOpposesGrowingError)
{
    // 오차가 커지는 중(rate>0)이면 조향이 더 세져야 한다(더 음수).
    const auto steady = computeCommand(0.2, 0.0, 0.0, 0.5, false, defaultGains());
    const auto growing = computeCommand(0.2, 1.0, 0.0, 0.5, false, defaultGains());
    EXPECT_LT(growing.steer_rad, steady.steer_rad);
}

// ── 포화 ──

TEST(LineFollowCore, SteerSaturatesAtMaxBothSigns)
{
    const auto g = defaultGains();
    const auto right = computeCommand(1.0, 10.0, 1.0, 0.5, false, g);
    const auto left = computeCommand(-1.0, -10.0, -1.0, 0.5, false, g);
    EXPECT_NEAR(right.steer_rad, -g.max_steer_rad, 1e-12);
    EXPECT_NEAR(left.steer_rad, g.max_steer_rad, 1e-12);
}

// ── 커브 감속 ──

TEST(LineFollowCore, CenteredLineKeepsFullSpeed)
{
    const auto cmd = computeCommand(0.0, 0.0, 0.0, 0.8, false, defaultGains());
    EXPECT_NEAR(cmd.v_target, 0.8, 1e-12);
}

TEST(LineFollowCore, LargeOffsetSlowsDown)
{
    const auto cmd = computeCommand(0.5, 0.0, 0.0, 0.8, false, defaultGains());
    EXPECT_NEAR(cmd.v_target, 0.8 * (1.0 - 0.7 * 0.5), 1e-12);
    EXPECT_LT(cmd.v_target, 0.8);
}

TEST(LineFollowCore, SlowFactorSaturatesAtUnitOffsetAndStaysNonNegative)
{
    // |offset| 이 1 을 넘어도 감속 계수는 1 에서 멈춘다 — 속도가 음수가 되면 안 된다.
    const auto cmd = computeCommand(5.0, 0.0, 0.0, 0.8, false, defaultGains());
    EXPECT_NEAR(cmd.v_target, 0.8 * (1.0 - 0.7), 1e-12);
    EXPECT_GE(cmd.v_target, 0.0);
}

TEST(LineFollowCore, SpeedIsMagnitudeEvenInReverse)
{
    // 방향은 vx 부호가 담당한다 — 코어는 항상 크기(>=0)를 낸다.
    const auto cmd = computeCommand(0.2, 0.0, 0.0, 0.6, true, defaultGains());
    EXPECT_GT(cmd.v_target, 0.0);
}

// ── 속도 ramp ──

TEST(LineFollowCore, RampRespectsAccelLimit)
{
    EXPECT_NEAR(rampSpeed(0.0, 1.0, 0.3, 0.02), 0.006, 1e-12);
    EXPECT_NEAR(rampSpeed(1.0, 0.0, 0.3, 0.02), 0.994, 1e-12);
}

TEST(LineFollowCore, RampSnapsWhenWithinStep)
{
    EXPECT_NEAR(rampSpeed(0.999, 1.0, 0.3, 0.02), 1.0, 1e-12);
}

// ── 소실 coast 상태기계 ──

TEST(LostCoastFsmTest, StartsInWaitLineUntilGoodDetection)
{
    LostCoastFsm fsm(1.0, 0.9);
    EXPECT_EQ(fsm.update(false, 0.0, 0.0), Phase::WAIT_LINE);
    EXPECT_EQ(fsm.update(true, 0.0, 0.1), Phase::FOLLOWING);
}

TEST(LostCoastFsmTest, LossEntersCoastAndTimeoutStops)
{
    LostCoastFsm fsm(1.0, 0.9);
    fsm.update(true, 0.0, 0.0);
    EXPECT_EQ(fsm.update(false, 0.0, 0.1), Phase::LOST_COAST);
    EXPECT_EQ(fsm.update(false, 0.0, 0.9), Phase::LOST_COAST); // 아직 유예 안
    EXPECT_EQ(fsm.update(false, 0.0, 1.2), Phase::STOPPING);   // 0.1 + 1.0 초과
}

TEST(LostCoastFsmTest, GoodDetectionResumesAndFlagsOnce)
{
    LostCoastFsm fsm(1.0, 0.9);
    fsm.update(true, 0.0, 0.0);
    fsm.update(false, 0.0, 0.1);
    EXPECT_EQ(fsm.update(true, 0.1, 0.5), Phase::FOLLOWING);
    EXPECT_TRUE(fsm.resumed());
    fsm.update(true, 0.1, 0.6);
    EXPECT_FALSE(fsm.resumed()); // 1회만
}

TEST(LostCoastFsmTest, EdgeDetectionDoesNotResume)
{
    // 화면 가장자리(|offset| >= resume 임계) 검출로는 복귀하지 않는다 — 오검출 배제.
    LostCoastFsm fsm(1.0, 0.9);
    fsm.update(true, 0.0, 0.0);
    fsm.update(false, 0.0, 0.1);
    EXPECT_EQ(fsm.update(true, 0.95, 0.5), Phase::LOST_COAST);
    EXPECT_FALSE(fsm.resumed());
}

TEST(LostCoastFsmTest, StoppingIsTerminal)
{
    LostCoastFsm fsm(0.5, 0.9);
    fsm.update(true, 0.0, 0.0);
    fsm.update(false, 0.0, 0.1);
    EXPECT_EQ(fsm.update(false, 0.0, 1.0), Phase::STOPPING);
    EXPECT_EQ(fsm.update(true, 0.0, 1.1), Phase::STOPPING); // 재검출로도 안 풀린다
}

TEST(LostCoastFsmTest, WaitLineIgnoresCoastTimeout)
{
    // 시작 대기는 coast 유예와 무관하다 — wait_line_timeout 은 서버가 따로 관리한다.
    LostCoastFsm fsm(0.5, 0.9);
    EXPECT_EQ(fsm.update(false, 0.0, 10.0), Phase::WAIT_LINE);
}

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
