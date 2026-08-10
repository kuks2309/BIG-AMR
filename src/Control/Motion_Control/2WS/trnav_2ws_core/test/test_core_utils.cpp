// robot_geometry · recursive_moving_average · action_mutex 회귀.
//
// `parsePlatform` 은 **모르는 이름을 조용히 `QD_DIAGONAL` 로 바꾼다.** 이 스택의 기체는
// QD 대각이 아니라 inline dual-steer 이므로, 오타 하나가 다른 플랫폼 해석으로 이어진다.
// 같은 계열의 사고가 이미 있었다 — QD 기본 기하가 흘러들어와 제자리 회전이 187 mm 병진이 됐다.
// 그 대체 동작 자체를 시험으로 못 박아, 없애거나 바꿀 때 반드시 눈에 띄게 한다.

#include <gtest/gtest.h>

#include <cmath>
#include <numeric>
#include <vector>

#include "trnav_2ws_core/action_mutex.hpp"
#include "trnav_2ws_core/recursive_moving_average.hpp"
#include "trnav_2ws_core/robot_geometry.hpp"

using trnav_2ws_core::ActionMutex;
using trnav_2ws_core::ActionMutexGuard;
using trnav_2ws_core::parsePlatform;
using trnav_2ws_core::Platform;
using trnav_2ws_core::RecursiveMovingAverage;

// ── 플랫폼 파싱 ───────────────────────────────────────────────────────────
TEST(RobotGeometry, ParsePlatformAcceptsBothCases)
{
    EXPECT_EQ(parsePlatform("QD_DIAGONAL"), Platform::QD_DIAGONAL);
    EXPECT_EQ(parsePlatform("qd_diagonal"), Platform::QD_DIAGONAL);
    EXPECT_EQ(parsePlatform("DD"), Platform::DD);
    EXPECT_EQ(parsePlatform("dd"), Platform::DD);
    EXPECT_EQ(parsePlatform("FWS_INDEPENDENT"), Platform::FWS_INDEPENDENT);
    EXPECT_EQ(parsePlatform("fws_independent"), Platform::FWS_INDEPENDENT);
    EXPECT_EQ(parsePlatform("ACKERMANN"), Platform::ACKERMANN);
    EXPECT_EQ(parsePlatform("ackermann"), Platform::ACKERMANN);
}

TEST(RobotGeometry, UnknownPlatformSilentlyFallsBackToQdDiagonal)
{
    // ⚠ **이것은 위험한 기본값이다 — 바람직해서가 아니라 사실이라서 고정한다.**
    //   오타("QD_DIAGONA")나 새 플랫폼 이름이 들어오면 예외도 경고도 없이 QD 로 해석된다.
    //   이 스택의 기체는 QD 대각이 아니므로 그 해석은 틀린 기하로 이어진다.
    //   대체를 없애거나 다른 값으로 바꾸려면 이 시험이 먼저 실패해야 한다.
    EXPECT_EQ(parsePlatform("QD_DIAGONA"), Platform::QD_DIAGONAL) << "오타";
    EXPECT_EQ(parsePlatform(""), Platform::QD_DIAGONAL) << "빈 문자열";
    EXPECT_EQ(parsePlatform("INLINE_DUAL_STEER"), Platform::QD_DIAGONAL)
        << "이 기체의 실제 배치 이름조차 QD 로 떨어진다";
    EXPECT_EQ(parsePlatform("Qd_Diagonal"), Platform::QD_DIAGONAL)
        << "혼합 대소문자는 인식 목록에 없어 대체로 떨어진다";
}

// ── 재귀 이동평균 ─────────────────────────────────────────────────────────
TEST(RecursiveMovingAverage, FillPhaseAveragesOnlyReceivedSamples)
{
    RecursiveMovingAverage rma(5);
    EXPECT_NEAR(rma.update(10.0), 10.0, 1e-12) << "첫 샘플은 그 자신이 평균이다";
    EXPECT_NEAR(rma.update(20.0), 15.0, 1e-12);
    EXPECT_NEAR(rma.update(30.0), 20.0, 1e-12);
}

TEST(RecursiveMovingAverage, MatchesTrueMeanOfLastNSamples)
{
    // 재귀 갱신(avg += (new − old)/N)이 진짜 이동평균과 어긋나는지 본다.
    const int N = 5;
    RecursiveMovingAverage rma(N);
    std::vector<double> hist;
    double last = 0.0;
    for (int i = 1; i <= 40; ++i)
    {
        const double v = std::sin(i * 0.37) * 100.0 + i;   // 부호·크기가 섞인 입력
        hist.push_back(v);
        last = rma.update(v);
        if (static_cast<int>(hist.size()) > N)
            hist.erase(hist.begin());
        const double truth = std::accumulate(hist.begin(), hist.end(), 0.0) / hist.size();
        EXPECT_NEAR(last, truth, 1e-9) << "샘플 " << i << " 에서 진짜 이동평균과 어긋났다";
    }
}

TEST(RecursiveMovingAverage, ConstantInputConvergesToThatConstant)
{
    RecursiveMovingAverage rma(4);
    for (int i = 0; i < 20; ++i)
        rma.update(7.5);
    EXPECT_NEAR(rma.update(7.5), 7.5, 1e-12);
}

TEST(RecursiveMovingAverage, ResetClearsHistory)
{
    RecursiveMovingAverage rma(3);
    rma.update(100.0);
    rma.update(100.0);
    rma.update(100.0);
    rma.reset();
    EXPECT_NEAR(rma.update(1.0), 1.0, 1e-12)
        << "reset 후에도 이전 표본이 남아 있다 — 새 기동이 옛 값에서 출발한다";
}

TEST(RecursiveMovingAverage, WindowSizeOneIsPassThrough)
{
    RecursiveMovingAverage rma(1);
    EXPECT_NEAR(rma.update(3.0), 3.0, 1e-12);
    EXPECT_NEAR(rma.update(-9.0), -9.0, 1e-12);
}

// ── 액션 상호배제 ─────────────────────────────────────────────────────────
TEST(ActionMutexGuardTest, ReleasesOnScopeExit)
{
    ActionMutex m = std::make_shared<std::atomic<bool>>(true);
    {
        ActionMutexGuard g(m);
        EXPECT_TRUE(m->load()) << "범위 안에서는 잠금이 유지돼야 한다";
    }
    EXPECT_FALSE(m->load()) << "범위를 벗어났는데 잠금이 남았다 — 다음 기동이 영원히 막힌다";
}

TEST(ActionMutexGuardTest, ReleasesOnException)
{
    ActionMutex m = std::make_shared<std::atomic<bool>>(true);
    try
    {
        ActionMutexGuard g(m);
        throw std::runtime_error("execute() 중 예외");
    }
    catch (const std::runtime_error &)
    {
    }
    EXPECT_FALSE(m->load())
        << "예외 경로에서 잠금이 풀리지 않았다 — 한 번 죽으면 이후 모든 기동이 거부된다";
}

TEST(ActionMutexGuardTest, SharedInstanceIsVisibleToAllHolders)
{
    // 모든 액션 서버가 **같은 인스턴스**를 주입받아야 교차 배제가 성립한다.
    ActionMutex m = std::make_shared<std::atomic<bool>>(false);
    ActionMutex same = m;
    m->store(true);
    EXPECT_TRUE(same->load()) << "사본이 상태를 공유하지 않는다 — 교차 배제가 깨진다";
}
