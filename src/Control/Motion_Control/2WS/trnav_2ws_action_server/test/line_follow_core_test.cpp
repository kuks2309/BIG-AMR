// line_follow 제어 코어 단위테스트 — ROS 없이 순수 수학·상태기계만 검증한다.

#include <gtest/gtest.h>

#include "trnav_2ws_action_server/line_follow/line_follow_core.hpp"
#include "trnav_2ws_kinematics/qd_crab_inverse_kinematics.hpp"

using trnav_2ws_action_server::line_follow::clampAbs;
using trnav_2ws_action_server::line_follow::computeSteer;
using trnav_2ws_action_server::line_follow::correctCurveBias;
using trnav_2ws_action_server::line_follow::Gains;
using trnav_2ws_action_server::line_follow::headingErrorFollowLine;
using trnav_2ws_action_server::line_follow::HeadingMode;
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
    g.k_curve_heading = 1.2;
    g.kp_heading = 1.0;
    g.kd_heading = 0.1;
    g.max_steer_rad = 25.0 * M_PI / 180.0;
    g.slow_gain = 0.7;
    g.curve_bias_gain = 0.0;
    return g;
}

// 인자 순서를 매번 쓰지 않도록 — (offset, rate, angle, h_err, h_rate, v, gains)
trnav_2ws_action_server::line_follow::SteerInputs steer(double offset, double angle,
                                                       double h_err = 0.0,
                                                       Gains g = defaultGains(), double rate = 0.0,
                                                       HeadingMode mode = HeadingMode::FOLLOW_LINE)
{
    return computeSteer(offset, rate, angle, h_err, 0.0, 0.5, mode, g);
}
} // namespace

// ── 공통분: 진행 방향 회전 ──
// offset(+) = 라인이 진행방향 오른쪽 → 진행 방향을 오른쪽(음의 CCW)으로 돌린다.

TEST(LineFollowCore, RightOffsetTurnsTravelRight)
{
    EXPECT_LT(steer(0.3, 0.0).delta_cte, 0.0);
}

TEST(LineFollowCore, LeftOffsetTurnsTravelLeft)
{
    EXPECT_GT(steer(-0.3, 0.0).delta_cte, 0.0);
}

TEST(LineFollowCore, ControlIsDirectionFree)
{
    // 세 입력 모두 진행 방향에 의존하지 않는다 — 방향은 IK 의 vx 부호와 「진행 기준 뒷바퀴」
    // 지정이 담당한다. 그 계약은 아래 CrabIkYawRateSign 시험이 건다.
    const auto s = steer(0.3, 0.2, 0.1);
    EXPECT_LT(s.delta_cte, 0.0);
    EXPECT_LT(s.theta_body, 0.0);
    EXPECT_GT(s.delta_heading, 0.0);
}

TEST(LineFollowCore, AngleAlignsTravelWithTangent)
{
    // angle(+) = 먼 쪽이 오른쪽 기움 → 진행 방향도 오른쪽으로
    EXPECT_LT(steer(0.0, 0.3).theta_body, 0.0);
    EXPECT_GT(steer(0.0, -0.3).theta_body, 0.0);
}

TEST(LineFollowCore, AngleTermMatchesGeometricGain)
{
    // 기하 정답 kp_angle = L/(2·lookahead). L=1.2·d=1.0 이면 0.6 이고,
    // 그때 theta_body 는 필요 조향(≈ atan(κL/2))과 일치해야 한다.
    Gains g = defaultGains();
    g.kp_angle = 0.6;
    const double kappa = 1.0 / 5.0;      // R = 5 m
    const double angle = -kappa * 1.0;   // angle ≈ -κ·d
    const double expected = std::atan(kappa * 1.2 / 2.0);
    EXPECT_NEAR(steer(0.0, angle, 0.0, g).theta_body, expected, 0.002);
}

TEST(LineFollowCore, DerivativeOpposesGrowingError)
{
    const auto steady = steer(0.2, 0.0, 0.0, defaultGains(), 0.0);
    const auto growing = steer(0.2, 0.0, 0.0, defaultGains(), 1.0);
    EXPECT_LT(growing.delta_cte, steady.delta_cte);
}

// ── 곡선 편향 보상 ──

TEST(LineFollowCore, ZeroBiasGainLeavesOffsetUntouched)
{
    EXPECT_NEAR(correctCurveBias(0.4, -0.3, 0.0), 0.4, 1e-12);
}

TEST(LineFollowCore, BiasGainRemovesCurveInducedOffset)
{
    // 완벽 추종 곡선: offset = angle · d/(2·hw). 보상 후 0 이어야 한다.
    const double bias_gain = 1.0 / (2.0 * 0.6); // d=1.0, hw=0.6
    const double angle = -0.2;
    const double offset = angle * bias_gain;
    EXPECT_NEAR(correctCurveBias(offset, angle, bias_gain), 0.0, 1e-12);
}

TEST(LineFollowCore, BiasCompensationRemovesOversteer)
{
    // 보상이 없으면 곡선 편향까지 횡오차로 보고 과조향한다.
    Gains g = defaultGains();
    const double angle = -0.464;                 // R = 2 m 완벽 추종
    const double offset = -0.393;
    const auto raw = steer(offset, angle, 0.0, g);
    g.curve_bias_gain = 1.0 / (2.0 * 0.6);
    const auto fixed = steer(offset, angle, 0.0, g);
    EXPECT_GT(std::abs(raw.delta_cte), std::abs(fixed.delta_cte));
    EXPECT_NEAR(fixed.delta_cte, 0.0, 0.02);     // 편향만 있고 실제 횡오차는 없다
    EXPECT_NEAR(fixed.offset_used, 0.0, 0.02);
}

TEST(LineFollowCore, BiasCompensationKeepsRealErrorIntact)
{
    // 곡선 편향 위에 진짜 횡오차 0.2 가 얹힌 경우 — 보상 후 그 0.2 만 남아야 한다.
    Gains g = defaultGains();
    g.curve_bias_gain = 1.0 / (2.0 * 0.6);
    const double angle = -0.2;
    const double bias = angle * g.curve_bias_gain;
    EXPECT_NEAR(steer(bias + 0.2, angle, 0.0, g).offset_used, 0.2, 1e-12);
}

// ── 차이분: heading ──

TEST(LineFollowCore, HeadingErrorRotatesBodyCcwWhenPositive)
{
    EXPECT_GT(steer(0.0, 0.0, 0.3).delta_heading, 0.0);
}

TEST(LineFollowCore, CurveFeedforwardMatchesRequiredCounterSteer)
{
    // 곡선을 완벽히 타고 있을 때 필요한 앞뒤 차는 2·atan(κL/2) 다.
    // FOLLOW_LINE 의 feedforward (L/d)·(−angle) 이 그 값과 맞아야 한다.
    Gains g = defaultGains();
    for (double radius : {20.0, 10.0, 5.0, 3.0, 2.0})
    {
        const double kappa = 1.0 / radius;
        const double angle = -kappa * 1.0; // angle = -κ·d, d = 1.0
        const double required = 2.0 * std::atan(kappa * 1.2 / 2.0);
        const auto s = steer(0.0, angle, headingErrorFollowLine(angle), g);
        EXPECT_NEAR(s.delta_heading, required, 0.03) << "radius=" << radius;
    }
}

TEST(LineFollowCore, CurveFeedforwardIsTwiceTheCommonPart)
{
    // 기하 정답 kp_angle = L/2d 와 k_curve_heading = L/d 는 정확히 2배 관계다.
    // 그래야 곡선에서 crab 성분 0 (= 순수 counter-steer) 이 된다:
    //   front = theta_body,  rear = theta_body - 2·theta_body = -theta_body
    const double angle = -0.3;
    const auto s = steer(0.0, angle, headingErrorFollowLine(angle));
    EXPECT_NEAR(s.delta_heading, 2.0 * s.theta_body, 1e-12);
    const double front = s.theta_body + s.delta_cte;
    const double rear = front - s.delta_heading;
    EXPECT_NEAR(front, -rear, 1e-12);
}

TEST(LineFollowCore, HoldModeUsesFeedbackGainsNotCurveFeedforward)
{
    // HOLD·ABSOLUTE 의 오차는 진짜 yaw 편차다 — feedforward 계수가 아니라 PD 를 쓴다.
    Gains g = defaultGains();
    g.k_curve_heading = 1.2;
    g.kp_heading = 1.0;
    g.kd_heading = 0.0;
    const double err = 0.2;
    const auto hold = computeSteer(0.0, 0.0, 0.0, err, 0.0, 0.5, HeadingMode::HOLD, g);
    const auto follow = computeSteer(0.0, 0.0, 0.0, err, 0.0, 0.5, HeadingMode::FOLLOW_LINE, g);
    EXPECT_NEAR(hold.delta_heading, g.kp_heading * err, 1e-12);
    EXPECT_NEAR(follow.delta_heading, g.k_curve_heading * err, 1e-12);
}

TEST(LineFollowCore, CurveFeedforwardHasNoDerivativeTerm)
{
    // feedforward 는 미분할 대상이 아니다 — 변화율이 들어와도 값이 변하지 않아야 한다.
    Gains g = defaultGains();
    const auto a = computeSteer(0.0, 0.0, 0.0, 0.2, 0.0, 0.5, HeadingMode::FOLLOW_LINE, g);
    const auto b = computeSteer(0.0, 0.0, 0.0, 0.2, 5.0, 0.5, HeadingMode::FOLLOW_LINE, g);
    EXPECT_NEAR(a.delta_heading, b.delta_heading, 1e-12);
}

// 코어가 진행 방향을 안 받는 근거 — IK 가 「진행 기준 뒷바퀴」에 −delta_heading 을 주므로
// 후진에서는 그 offset 을 받는 물리 바퀴가 바뀐다. 그 결과 yaw rate 부호는 진행 방향과
// 무관하게 delta_heading 을 따른다. 여기에 방향 계수를 곱하면 후진이 양의 되먹임이 된다.
//
// omega = vx_body * (tan(delta_W1) - tan(delta_W2)) / L,  W1 이 +x 쪽 바퀴.
TEST(LineFollowCore, CrabIkYawRateSignFollowsDeltaHeadingBothDirections)
{
    using trnav::motion::two_ws::TwoWsCrabIK;
    constexpr double kWheelbase = 1.2; // w1_x 0.6039 - w2_x (-0.5961)
    constexpr double kDeltaHeading = 0.1;

    auto omega = [&](bool reverse) {
        TwoWsCrabIK ik(2, 0.125, 32.0);
        ik.setInitial(0.0, reverse ? -1 : 1);
        const double vx = reverse ? -1.0 : 1.0;
        const auto r = ik.compute(vx, 0.0, 0.0, kDeltaHeading);
        return vx * (std::tan(r.wheels[0].steer_rad) - std::tan(r.wheels[1].steer_rad)) / kWheelbase;
    };

    EXPECT_GT(omega(false), 0.0);
    EXPECT_GT(omega(true), 0.0);
    EXPECT_NEAR(omega(false), omega(true), 1e-9);
}

TEST(LineFollowCore, FollowLineHeadingErrorIsNegatedAngle)
{
    EXPECT_NEAR(headingErrorFollowLine(0.3), -0.3, 1e-12);
    EXPECT_NEAR(headingErrorFollowLine(-0.25), 0.25, 1e-12);
}

TEST(LineFollowCore, HoldHeadingProducesNoRotationWhenAligned)
{
    // heading 오차 0 이면 차체는 돌지 않는다 — 공통분만으로 라인을 따라간다(crab)
    EXPECT_NEAR(steer(0.3, 0.2, 0.0).delta_heading, 0.0, 1e-12);
}

TEST(LineFollowCore, HeadingModeValuesMatchActionContract)
{
    EXPECT_EQ(static_cast<uint8_t>(HeadingMode::FOLLOW_LINE), 0);
    EXPECT_EQ(static_cast<uint8_t>(HeadingMode::HOLD), 1);
    EXPECT_EQ(static_cast<uint8_t>(HeadingMode::ABSOLUTE), 2);
}

// ── 포화 ──

TEST(LineFollowCore, EachInputSaturatesIndependently)
{
    const auto g = defaultGains();
    const auto s = steer(1.0, 1.0, 3.0, g, 10.0);
    EXPECT_NEAR(s.delta_cte, -g.max_steer_rad, 1e-12);
    EXPECT_NEAR(s.theta_body, -g.max_steer_rad, 1e-12);
    // 차이분은 바퀴각 두 개의 차라 한계가 2배다
    EXPECT_NEAR(s.delta_heading, 2.0 * g.max_steer_rad, 1e-12);
}

TEST(LineFollowCore, DifferentialSaturatesAtTwiceTheWheelLimit)
{
    // R=2 m 가 요구하는 33.4° 는 바퀴 한계 25° 를 넘지만, **차이**로는 정당하다.
    // 1배로 조이면 이 곡선이 낼 수 없는 값이 되어 곡선을 놓친다.
    Gains g = defaultGains();
    const double angle = -0.5; // R = 2 m
    const auto s = steer(0.0, angle, headingErrorFollowLine(angle), g);
    EXPECT_GT(std::abs(s.delta_heading), g.max_steer_rad);
    EXPECT_LE(std::abs(s.delta_heading), 2.0 * g.max_steer_rad + 1e-12);
}

// ── 커브 감속 ──

TEST(LineFollowCore, CenteredLineKeepsFullSpeed)
{
    EXPECT_NEAR(computeSteer(0.0, 0.0, 0.0, 0.0, 0.0, 0.8, HeadingMode::FOLLOW_LINE, defaultGains()).v_target, 0.8,
                1e-12);
}

TEST(LineFollowCore, LargeOffsetSlowsDown)
{
    const auto s = computeSteer(0.5, 0.0, 0.0, 0.0, 0.0, 0.8, HeadingMode::FOLLOW_LINE, defaultGains());
    EXPECT_NEAR(s.v_target, 0.8 * (1.0 - 0.7 * 0.5), 1e-12);
}

TEST(LineFollowCore, SlowdownUsesMeasuredOffsetNotCompensated)
{
    // 편향이 큰 곡선일수록 실제로 느려야 하므로 감속 판단은 **보상 전** 값으로 한다.
    Gains g = defaultGains();
    g.curve_bias_gain = 1.0 / (2.0 * 0.6);
    const double angle = -0.464, offset = -0.393;
    const auto s = computeSteer(offset, 0.0, angle, 0.0, 0.0, 0.8, HeadingMode::FOLLOW_LINE, g);
    EXPECT_NEAR(s.v_target, 0.8 * (1.0 - 0.7 * 0.393), 1e-9);
}

TEST(LineFollowCore, TargetSpeedIsAlwaysMagnitude)
{
    // 부호는 IK 의 vx 가 담당한다 — 코어는 항상 크기만 낸다.
    EXPECT_GT(computeSteer(0.2, 0.0, 0.0, 0.0, 0.0, 0.6, HeadingMode::FOLLOW_LINE, defaultGains()).v_target, 0.0);
}

TEST(LineFollowCore, SlowFactorSaturatesAndStaysNonNegative)
{
    const auto s = computeSteer(5.0, 0.0, 0.0, 0.0, 0.0, 0.8, HeadingMode::FOLLOW_LINE, defaultGains());
    EXPECT_NEAR(s.v_target, 0.8 * 0.3, 1e-12);
    EXPECT_GE(s.v_target, 0.0);
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

TEST(LineFollowCore, ClampAbsIsSymmetric)
{
    EXPECT_NEAR(clampAbs(5.0, 2.0), 2.0, 1e-12);
    EXPECT_NEAR(clampAbs(-5.0, 2.0), -2.0, 1e-12);
    EXPECT_NEAR(clampAbs(1.0, 2.0), 1.0, 1e-12);
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
    EXPECT_EQ(fsm.update(false, 0.0, 0.9), Phase::LOST_COAST);
    EXPECT_EQ(fsm.update(false, 0.0, 1.2), Phase::STOPPING);
}

TEST(LostCoastFsmTest, GoodDetectionResumesAndFlagsOnce)
{
    LostCoastFsm fsm(1.0, 0.9);
    fsm.update(true, 0.0, 0.0);
    fsm.update(false, 0.0, 0.1);
    EXPECT_EQ(fsm.update(true, 0.1, 0.5), Phase::FOLLOWING);
    EXPECT_TRUE(fsm.resumed());
    fsm.update(true, 0.1, 0.6);
    EXPECT_FALSE(fsm.resumed());
}

TEST(LostCoastFsmTest, EdgeDetectionDoesNotResume)
{
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
    EXPECT_EQ(fsm.update(true, 0.0, 1.1), Phase::STOPPING);
}

TEST(LostCoastFsmTest, WaitLineIgnoresCoastTimeout)
{
    LostCoastFsm fsm(0.5, 0.9);
    EXPECT_EQ(fsm.update(false, 0.0, 10.0), Phase::WAIT_LINE);
}

int main(int argc, char **argv)
{
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
