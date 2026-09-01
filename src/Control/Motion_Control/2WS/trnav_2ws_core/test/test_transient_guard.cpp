// TransientGuard 회귀 — 2WS 스택 최초의 자동 시험.
//
// 왜 여기부터인가: `yaw_control` 의 조향 미도달 감시(status −8)가 이 클래스의
// `gate_blocked` 위에 서 있다. 게이트 판정이 조용히 바뀌면 그 가드가 발화하지 않거나
// 반대로 정상 주행을 막는다 — 어느 쪽도 현장에서야 드러난다.
//
// 게이트 임계가 **국면마다 다르다**는 사실이 특히 중요하다. Phase 0 은
// `steer_gate_threshold`(3°), 주행 중은 `runtime_gate_threshold`(15°)를 쓴다.
// 이것을 모르면 「주행 중 조향 오차가 3° 를 넘으면 막힌다」로 오해하게 되는데,
// 실제로는 15° 를 넘어야 막히므로 정상 주행에서는 `gate_blocked` 가 참이 되지 않는다.

#include <gtest/gtest.h>

#include "trnav_2ws_core/transient_guard.hpp"

using trnav_2ws_core::TransientGuard;

namespace
{

TransientGuard::Params defaults()
{
    return TransientGuard::Params{};  // 3.0 / 15.0 / 10.0 …
}

TransientGuard::GuardInput in(double steer_err_deg, bool phase0)
{
    TransientGuard::GuardInput i{};
    i.vy_cmd = 0.0;
    i.omega_cmd = 0.0;
    i.steer_error_deg = steer_err_deg;
    i.is_phase0 = phase0;
    return i;
}

} // namespace

// ── 게이트 임계가 국면마다 다르다 ─────────────────────────────────────────
TEST(TransientGuard, Phase0UsesSteerGateThreshold)
{
    TransientGuard g(defaults());
    EXPECT_FALSE(g.apply(in(2.9, true)).gate_blocked) << "3.0° 미만인데 막혔다";
    EXPECT_TRUE(g.apply(in(3.1, true)).gate_blocked) << "3.0° 초과인데 안 막혔다";
}

TEST(TransientGuard, RuntimeUsesRuntimeGateThreshold)
{
    TransientGuard g(defaults());
    // Phase 0 이면 막혔을 값(3.1°)이 주행 중에는 막히지 않아야 한다.
    EXPECT_FALSE(g.apply(in(3.1, false)).gate_blocked)
        << "주행 중 임계는 15° 인데 3.1° 에서 막혔다";
    EXPECT_FALSE(g.apply(in(14.9, false)).gate_blocked);
    EXPECT_TRUE(g.apply(in(15.1, false)).gate_blocked) << "15° 초과인데 안 막혔다";
}

TEST(TransientGuard, PhaseThresholdsAreNotTheSame)
{
    // 두 임계를 하나로 합치는 변경을 잡는다 — 합치면 Phase 0 이 헐거워지거나
    // 주행 중이 과민해진다. 어느 쪽이든 −8 가드의 의미가 달라진다.
    TransientGuard g(defaults());
    const double between = 8.0;  // 3° 와 15° 사이
    EXPECT_TRUE(g.apply(in(between, true)).gate_blocked);
    EXPECT_FALSE(g.apply(in(between, false)).gate_blocked);
}

// ── 비례 감속 ─────────────────────────────────────────────────────────────
TEST(TransientGuard, ProportionalDecelScalesWithSteerError)
{
    TransientGuard g(defaults());
    EXPECT_DOUBLE_EQ(g.apply(in(0.0, false)).drive_scale, 1.0);
    EXPECT_NEAR(g.apply(in(5.0, false)).drive_scale, 0.5, 1e-9);  // 1 − 5/10
    EXPECT_DOUBLE_EQ(g.apply(in(10.0, false)).drive_scale, 0.0);
}

TEST(TransientGuard, DriveScaleIsClampedToUnitRange)
{
    TransientGuard g(defaults());
    EXPECT_GE(g.apply(in(-5.0, false)).drive_scale, 0.0);
    EXPECT_LE(g.apply(in(-5.0, false)).drive_scale, 1.0);
    EXPECT_DOUBLE_EQ(g.apply(in(999.0, false)).drive_scale, 0.0);
}

TEST(TransientGuard, ProportionalDecelCanBeDisabled)
{
    auto p = defaults();
    p.enable_proportional_decel = false;
    TransientGuard g(p);
    EXPECT_DOUBLE_EQ(g.apply(in(5.0, false)).drive_scale, 1.0)
        << "비활성인데 감속 스케일이 걸렸다";
}

// ── 변화율 제한 ───────────────────────────────────────────────────────────
TEST(TransientGuard, RateLimitsAreAppliedPerCycle)
{
    auto p = defaults();
    p.vy_rate_limit = 0.1;
    p.omega_rate_limit = 0.2;
    TransientGuard g(p);

    TransientGuard::GuardInput i{};
    i.vy_cmd = 1.0;      // 한 번에 도달 불가
    i.omega_cmd = 1.0;
    i.steer_error_deg = 0.0;
    i.is_phase0 = false;

    auto o1 = g.apply(i);
    EXPECT_NEAR(o1.vy_limited, 0.1, 1e-9);
    EXPECT_NEAR(o1.omega_limited, 0.2, 1e-9);

    auto o2 = g.apply(i);   // 누적된다
    EXPECT_NEAR(o2.vy_limited, 0.2, 1e-9);
    EXPECT_NEAR(o2.omega_limited, 0.4, 1e-9);
}

TEST(TransientGuard, RateLimitSettlesExactlyOnTargetWithoutOvershoot)
{
    // ⚠ **돌연변이로 실증된 구멍이었다.** `rateLimitStep` 의 「남은 차이가 한 스텝 이하면
    //   목표를 그대로 반환한다」 분기를 **통째로 지워도** 이 파일의 시험이 전부 통과했다.
    //   지우면 지령이 목표에 정착하지 못하고 ±rate_limit 로 영구 진동한다 — 이 경로는
    //   7개 액션 서버가 전부 탄다. 원인은 기존 시험이 목표(1.0)에 **한 번도 닿지 않는**
    //   구간(0.1씩 2스텝)만 봤다는 것이다. 끝까지 돌려 정착을 확인한다.
    auto p = defaults();
    p.vy_rate_limit = 0.1;
    p.omega_rate_limit = 0.1;
    TransientGuard g(p);

    TransientGuard::GuardInput i{};
    i.vy_cmd = 0.25;          // 스텝의 배수가 아니다 — 마지막 스텝이 반드시 남는다
    i.omega_cmd = -0.25;
    i.steer_error_deg = 0.0;
    i.is_phase0 = false;

    TransientGuard::GuardOutput o{};
    for (int n = 0; n < 20; ++n)
        o = g.apply(i);

    EXPECT_DOUBLE_EQ(o.vy_limited, 0.25) << "목표에 정착하지 못했다 — 진동하고 있는가";
    EXPECT_DOUBLE_EQ(o.omega_limited, -0.25) << "음수 목표에서 정착하지 못했다";
}

TEST(TransientGuard, RateLimitIsSymmetricForNegativeTargets)
{
    auto p = defaults();
    p.vy_rate_limit = 0.1;
    TransientGuard g(p);

    TransientGuard::GuardInput i{};
    i.vy_cmd = -1.0;
    i.steer_error_deg = 0.0;
    i.is_phase0 = false;

    EXPECT_NEAR(g.apply(i).vy_limited, -0.1, 1e-9);
    EXPECT_NEAR(g.apply(i).vy_limited, -0.2, 1e-9);
}

TEST(TransientGuard, ResetClearsRateLimitState)
{
    auto p = defaults();
    p.vy_rate_limit = 0.1;
    TransientGuard g(p);

    TransientGuard::GuardInput i{};
    i.vy_cmd = 1.0;
    i.steer_error_deg = 0.0;
    i.is_phase0 = false;

    g.apply(i);
    g.apply(i);            // vy 는 0.2 까지 올라간 상태
    g.reset();
    EXPECT_NEAR(g.apply(i).vy_limited, 0.1, 1e-9)
        << "reset 후에도 이전 vy 상태가 남아 있다 — 다음 goal 이 전 goal 속도에서 출발한다";
}

TEST(TransientGuard, DeadbandSkipsNoiseLevelError)
{
    trnav_2ws_core::TransientGuard::Params p;
    p.steer_error_max = 10.0;
    p.steer_error_deadband = 2.0;
    p.enable_proportional_decel = true;
    p.runtime_gate_threshold = 90.0;
    trnav_2ws_core::TransientGuard g(p);
    trnav_2ws_core::TransientGuard::GuardInput in{};
    in.is_phase0 = false;
    in.steer_error_deg = 1.5;   // 불감대 이하 — 무감쇠
    EXPECT_DOUBLE_EQ(g.apply(in).drive_scale, 1.0);
    in.steer_error_deg = 6.0;   // 불감대~max 중간 — (6-2)/(10-2)=0.5
    EXPECT_NEAR(g.apply(in).drive_scale, 0.5, 1e-9);
    in.steer_error_deg = 10.0;  // max — 0 유지
    EXPECT_NEAR(g.apply(in).drive_scale, 0.0, 1e-9);
}
