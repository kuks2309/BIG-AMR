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

// ── 전이점·연속성 (돌연변이로 실증된 구멍이었다) ─────────────────────────
TEST(TrapezoidalProfile, TransitionPointsAreAtTheComputedDistances)
{
    // ⚠ **감사가 돌연변이로 실증했다.** `accel_dist_` 를 0.5배로 줄이거나 감속 거리를 0.5배로
    //   줄여 `decel_start_` 를 80 → 85 로 미뤄도 기존 시험 14건이 전부 통과했다 — 즉
    //   「감속을 절반 늦게 시작한다(오버슈트)」와 「속도가 7.07 → 10.0 으로 계단 점프한다」를
    //   아무도 잡지 못했다. 원인은
    //   `PhaseOrderIsAccelThenCruiseThenDecel` 이 s=1/45/89 **세 점만** 봤다는 것이다.
    //   전이점 자체를 못 박는다: d_accel = v²/(2a) = 100/10 = 10, decel_start = 90 − 10 = 80.
    TrapezoidalProfile p(90.0, 10.0, 5.0);
    EXPECT_EQ(p.getSpeed(9.9).phase, ProfilePhase::ACCEL) << "가속이 너무 일찍 끝났다";
    EXPECT_EQ(p.getSpeed(10.1).phase, ProfilePhase::CRUISE) << "가속 종료점이 10 이 아니다";
    EXPECT_EQ(p.getSpeed(79.9).phase, ProfilePhase::CRUISE) << "감속이 너무 일찍 시작했다";
    EXPECT_EQ(p.getSpeed(80.1).phase, ProfilePhase::DECEL) << "감속 개시점이 80 이 아니다";
}

TEST(TrapezoidalProfile, SpeedIsContinuousAcrossPhaseBoundaries)
{
    // 전이점에서 속도가 튀면 구동 지령이 불연속이 된다 — 흡수해 줄 기제가 없다.
    TrapezoidalProfile p(90.0, 10.0, 5.0);
    for (double b : {10.0, 80.0})
    {
        const double lo = p.getSpeed(b - 0.01).speed;
        const double hi = p.getSpeed(b + 0.01).speed;
        EXPECT_NEAR(lo, hi, 0.05) << "경계 " << b << " 에서 속도가 튀었다 (" << lo << " → " << hi << ")";
    }
}

TEST(TrapezoidalProfile, ExitSpeedShapesTheDecelRampNotJustTheEndpoint)
{
    // ⚠ 기존 `ExitSpeedIsHonored` 는 `getSpeed(90.0)` 만 봤는데 그것은 DONE 분기라
    //   `exit_speed_` 를 그대로 반환한다. 감속 램프의 `v = √(v_exit² + 2a·remaining)` 에서
    //   `v_exit²` 항을 **지워도 통과**했다 — 그러면 램프가 0 으로 수렴하다 목표점에서 3.0 으로
    //   튄다. 시험 메시지가 경고하던 「연속 기동에서 급정지」가 바로 그것인데도 못 잡았다.
    TrapezoidalProfile p(90.0, 10.0, 5.0, /*exit_speed=*/3.0);
    // remaining = 0.1 → √(9 + 2·5·0.1) = √10 = 3.162
    EXPECT_NEAR(p.getSpeed(89.9).speed, std::sqrt(10.0), 1e-6)
        << "감속 램프가 exit_speed 를 반영하지 않는다 — 목표점에서 속도가 튄다";
    EXPECT_GT(p.getSpeed(89.9).speed, 3.0) << "램프 값이 exit_speed 아래로 내려갔다";
}

TEST(TrapezoidalProfile, EntrySpeedFeasibilityGuardIsObservationallyInert)
{
    // ⚠ **놀라운 사실이므로 못 박는다 — 바람직해서가 아니라 사실이라서다.**
    //   생성자의 「실현가능성 가드」(거리가 짧으면 entry_speed 를 감속 가능한 값으로 자른다)는
    //   `getSpeed` 를 통해 **관측되지 않는다.** 대수적으로:
    //     · 가드가 발동하는 조건 `D < (v_entry² − v_exit²)/(2a)` 은 곧 `accel_dist_ = 0` 을 뜻해
    //       ACCEL 분기가 한 번도 실행되지 않는다(entry_speed 를 쓰는 유일한 분기다).
    //     · DECEL 식 `√(v_exit² + 2a·remaining)` 에는 entry_speed 가 없다.
    //     · 가드가 없을 때의 `peak_speed_` 는 더 크므로 `min(·, peak)` 도 걸리지 않는다.
    //   그래서 가드를 **통째로 지워도 출력이 한 점도 달라지지 않는다**(5개 조합 전수 확인,
    //   최대 차이 0.000e+00). 감사는 이것을 「커버리지 구멍」으로 보고했으나 실제로는
    //   **검출할 차이가 없다** — 시험을 아무리 잘 써도 잡을 수 없다.
    //   이 시험은 그 등가성 자체를 고정한다. 가드가 언젠가 관측 가능해지면(예: ACCEL 분기의
    //   조건이 바뀌면) 여기가 먼저 깨져 「그때부터는 진짜 안전 계산」임을 알린다.
    //   제거 여부는 debt-065 에서 판단한다 — 방어적 대수로 남길 수도 있다.
    const double D = 0.5, vmax = 10.0, a = 5.0, vexit = 0.0;
    TrapezoidalProfile clamped(D, vmax, a, vexit, /*entry_speed=*/8.0);

    // 가드가 자른 값(√(v_exit² + 2aD) = √5)으로 직접 만든 프로파일과 같아야 한다.
    TrapezoidalProfile equivalent(D, vmax, a, vexit, /*entry_speed=*/std::sqrt(5.0));
    for (int i = 0; i <= 50; ++i)
    {
        const double pos = D * i / 50.0;
        EXPECT_NEAR(clamped.getSpeed(pos).speed, equivalent.getSpeed(pos).speed, 1e-9)
            << "위치 " << pos << " 에서 갈렸다 — 가드의 등가성 전제가 깨졌다";
    }
    // 시작점은 DECEL 식이 지배한다(ACCEL 이 실행되지 않으므로).
    EXPECT_NEAR(clamped.getSpeed(0.0).speed, std::sqrt(2.0 * a * D), 1e-9);
}

TEST(TrapezoidalProfile, EntrySpeedIsHonoredWhenFeasible)
{
    // 거리가 충분하면 진입속도가 그대로 쓰인다 — 이쪽은 **실제로 관측된다**
    // (ACCEL 분기가 살아 있어 `√(v_entry² + 2a·pos)` 가 entry 에서 출발한다).
    // 연속 기동(`crab_linear` 등 5개 서버가 `goal->entry_speed` 를 넘긴다)이 매번 0 에서
    // 다시 가속하면 그것도 결함이다.
    TrapezoidalProfile p(100.0, 10.0, 5.0, /*exit_speed=*/0.0, /*entry_speed=*/4.0);
    EXPECT_NEAR(p.getSpeed(0.0).speed, 4.0, 1e-9) << "실현 가능한 진입속도가 무시됐다";
    EXPECT_EQ(p.getSpeed(0.0).phase, ProfilePhase::ACCEL);
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
