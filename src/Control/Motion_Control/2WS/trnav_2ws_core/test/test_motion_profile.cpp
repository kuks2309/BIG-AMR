// TrapezoidalProfile · math_utils 회귀.
//
// 왜 필요한가: `turn` 의 Stage 1(coarse)이 이 프로파일 위에 서 있고, `turn`·`yaw_control`
// 의 두 가드가 `normalizeAngle*` 로 각도 오차를 잰다. 프로파일이 조용히 바뀌면 감속이
// 어긋나고, 각도 정규화가 어긋나면 ±180° 부근에서 가드가 반대로 판정한다.
//
// 단위는 일반적이다 — 각도(deg, deg/s, deg/s²)와 거리(m, m/s, m/s²) 양쪽에 같은 코드가 쓰인다.
// 여기서는 각도 단위로 검사하지만 성질은 단위와 무관하다.

#include <gtest/gtest.h>

#include <cmath>

#include "trnav_2ws_core/math_utils.hpp"
#include "trnav_2ws_core/motion_profile.hpp"

using trnav_2ws_core::normalizeAngle;
using trnav_2ws_core::normalizeAngleDeg;
using trnav_2ws_core::ProfilePhase;
using trnav_2ws_core::TrapezoidalProfile;

// ── 사다리꼴 프로파일 ─────────────────────────────────────────────────────
TEST(TrapezoidalProfile, StartsAtEntrySpeedAndEndsAtExitSpeed)
{
    TrapezoidalProfile p(90.0, 10.0, 5.0);   // 90° · 최대 10 dps · 5 dps²
    EXPECT_NEAR(p.getSpeed(0.0).speed, 0.0, 1e-9) << "기본 entry_speed 는 0 이다";
    EXPECT_NEAR(p.getSpeed(90.0).speed, 0.0, 1e-9) << "기본 exit_speed 는 0 이다";
}

TEST(TrapezoidalProfile, ReachesCruiseWhenDistanceIsLongEnough)
{
    TrapezoidalProfile p(90.0, 10.0, 5.0);
    auto mid = p.getSpeed(45.0);
    EXPECT_NEAR(mid.speed, 10.0, 1e-6) << "충분히 긴 구간인데 최대속도에 못 닿았다";
    EXPECT_EQ(mid.phase, ProfilePhase::CRUISE);
}

TEST(TrapezoidalProfile, SpeedNeverExceedsMaxSpeed)
{
    TrapezoidalProfile p(90.0, 10.0, 5.0);
    for (double s = 0.0; s <= 90.0; s += 0.5)
        EXPECT_LE(p.getSpeed(s).speed, 10.0 + 1e-9) << "위치 " << s << " 에서 상한 초과";
}

TEST(TrapezoidalProfile, PhaseOrderIsAccelThenCruiseThenDecel)
{
    TrapezoidalProfile p(90.0, 10.0, 5.0);
    EXPECT_EQ(p.getSpeed(1.0).phase, ProfilePhase::ACCEL);
    EXPECT_EQ(p.getSpeed(45.0).phase, ProfilePhase::CRUISE);
    EXPECT_EQ(p.getSpeed(89.0).phase, ProfilePhase::DECEL);
}

TEST(TrapezoidalProfile, TriangularWhenDistanceTooShortForCruise)
{
    // accel 거리 = v²/(2a) = 100/10 = 10°. 목표 10° 는 2×10 보다 짧다 → 삼각형.
    TrapezoidalProfile p(10.0, 10.0, 5.0);
    for (double s = 0.0; s <= 10.0; s += 0.25)
        EXPECT_NE(p.getSpeed(s).phase, ProfilePhase::CRUISE)
            << "짧은 구간인데 순항 국면이 나왔다 (위치 " << s << ")";
    EXPECT_LT(p.getSpeed(5.0).speed, 10.0) << "삼각형인데 최대속도까지 올라갔다";
}

TEST(TrapezoidalProfile, SpeedIsSymmetricAboutMidpointForTriangular)
{
    TrapezoidalProfile p(10.0, 10.0, 5.0);
    for (double d = 0.5; d <= 4.5; d += 0.5)
        EXPECT_NEAR(p.getSpeed(5.0 - d).speed, p.getSpeed(5.0 + d).speed, 1e-6)
            << "삼각형 프로파일이 중점 대칭이 아니다 (오프셋 " << d << ")";
}

TEST(TrapezoidalProfile, IsCompleteOnlyAtOrPastTarget)
{
    TrapezoidalProfile p(90.0, 10.0, 5.0);
    EXPECT_FALSE(p.isComplete(0.0));
    EXPECT_FALSE(p.isComplete(89.999));
    EXPECT_TRUE(p.isComplete(90.0));
    EXPECT_TRUE(p.isComplete(120.0)) << "목표를 지나쳤는데 미완료로 나왔다";
}

TEST(TrapezoidalProfile, SpeedIsNonNegativeEverywhereIncludingOutOfRange)
{
    TrapezoidalProfile p(90.0, 10.0, 5.0);
    for (double s : {-10.0, -0.1, 0.0, 45.0, 90.0, 200.0})
        EXPECT_GE(p.getSpeed(s).speed, 0.0) << "위치 " << s << " 에서 음수 속도";
}

TEST(TrapezoidalProfile, ExitSpeedIsHonored)
{
    TrapezoidalProfile p(90.0, 10.0, 5.0, /*exit_speed=*/3.0);
    EXPECT_NEAR(p.getSpeed(90.0).speed, 3.0, 1e-6)
        << "exit_speed 를 줬는데 0 으로 끝났다 — 연속 기동에서 급정지가 된다";
}

// ── 각도 정규화 ───────────────────────────────────────────────────────────
TEST(MathUtils, NormalizeAngleStaysWithinPlusMinusPi)
{
    EXPECT_NEAR(normalizeAngle(0.0), 0.0, 1e-12);
    EXPECT_NEAR(normalizeAngle(M_PI / 2), M_PI / 2, 1e-12);
    for (double a : {-100.0, -7.0, -1.0, 0.0, 1.0, 7.0, 100.0})
        EXPECT_LE(std::fabs(normalizeAngle(a)), M_PI + 1e-12) << "입력 " << a;
}

TEST(MathUtils, NormalizeAngleDegStaysWithinPlusMinus180)
{
    EXPECT_NEAR(normalizeAngleDeg(0.0), 0.0, 1e-12);
    EXPECT_NEAR(normalizeAngleDeg(90.0), 90.0, 1e-12);
    EXPECT_NEAR(normalizeAngleDeg(270.0), -90.0, 1e-9);
    EXPECT_NEAR(normalizeAngleDeg(-270.0), 90.0, 1e-9);
    for (double d : {-1000.0, -181.0, 0.0, 181.0, 1000.0})
        EXPECT_LE(std::fabs(normalizeAngleDeg(d)), 180.0 + 1e-9) << "입력 " << d;
}

TEST(MathUtils, TieBreakAtBoundaryIsRoundHalfEven)
{
    // ⚠ **함정이므로 못 박는다.** 구현은 `std::remainder` 이고 그 타이브레이크는
    //   round-half-even 이다. 몫이 정확히 x.5 인 입력(±180 의 홀수배)은 **짝수 쪽으로**
    //   접히므로 부호가 직관과 다를 수 있다:
    //     540 / 360 = 1.5 → 2 로 반올림 → 540 − 720 = **−180**
    //   즉 `+180` 이 나올 것이라 가정하면 ±180° 경계에서 판정이 뒤집힌다.
    //   헤더 주석도 「±π 를 한 부호로 뭉개지 않는다」고 명시한다 — 방향이 필요한 호출자는
    //   스스로 처리해야 한다.
    EXPECT_NEAR(normalizeAngleDeg(540.0), -180.0, 1e-9);
    EXPECT_NEAR(normalizeAngleDeg(180.0), 180.0, 1e-9);
    EXPECT_NEAR(normalizeAngleDeg(-180.0), -180.0, 1e-9);
    EXPECT_NEAR(normalizeAngle(3 * M_PI), -M_PI, 1e-9);
    EXPECT_NEAR(normalizeAngle(M_PI), M_PI, 1e-9);
}

TEST(MathUtils, NormalizeIsIdempotent)
{
    for (double d : {-359.9, -181.0, -1.0, 0.0, 1.0, 181.0, 359.9, 720.0})
        EXPECT_NEAR(normalizeAngleDeg(normalizeAngleDeg(d)), normalizeAngleDeg(d), 1e-12)
            << "두 번 정규화하면 값이 달라진다 (입력 " << d << ")";
}

TEST(MathUtils, DifferenceAcrossWrapBoundaryIsSmall)
{
    // 가드가 ±180° 부근에서 반대로 판정하지 않는지 — 179° 와 −179° 의 차이는 2° 다.
    EXPECT_NEAR(std::fabs(normalizeAngleDeg(179.0 - (-179.0))), 2.0, 1e-9);
    EXPECT_NEAR(std::fabs(normalizeAngleDeg(-179.0 - 179.0)), 2.0, 1e-9);
}
