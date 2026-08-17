// 입력 두절 워치독 회귀 — 원본 MCLoc 판정식의 성질을 고정한다.
//
// 고정 대상은 넷이다: 경계(임계 이상은 정상) · 진입 1회 로그 · 회복 · 기준선 없는 무수신.
// 시각은 인자로 주므로 시계가 필요 없다. NDEBUG 와 무관하게 실패하도록 자체 CHECK 를 쓴다.
#include <cstdio>

#include "mcl2d_ros2/lost_watchdog.hpp"

using namespace mcl2d_ros2;

static int g_fail = 0;
#define CHECK(cond, msg)                                                                                               \
    do                                                                                                                 \
    {                                                                                                                  \
        if (!(cond))                                                                                                   \
        {                                                                                                              \
            std::printf("[FAIL] %s  (%s:%d)\n", (msg), __FILE__, __LINE__);                                            \
            ++g_fail;                                                                                                  \
        }                                                                                                              \
    } while (0)

static constexpr std::int64_t kMs = 1000000; // ns

int main()
{
    // 1) 기준선을 세우기 전에는 판정하지 않는다 — 활성화 전 오탐을 막는다.
    {
        LostWatchdog w;
        CHECK(!w.update(1000000000LL), "start 전인데 두절로 판정했다");
        CHECK(!w.lost(), "start 전인데 두절 상태다");
    }

    // 2) 경계 — 원본 판정식은 `임계 >= 경과` 면 정상이므로 **초과**에서만 두절이다.
    {
        LostWatchdog w(300);
        w.start(0);
        CHECK(!w.update(299 * kMs), "임계 미만인데 두절로 판정했다");
        CHECK(!w.update(300 * kMs), "임계와 같은데 두절로 판정했다 — 원본은 이 지점이 정상이다");
        CHECK(w.update(301 * kMs), "임계 초과인데 두절로 판정하지 않았다");
    }

    // 3) 진입 1회 — 원본의 정적 err_reported 플래그에 대응한다.
    {
        LostWatchdog w(300);
        w.start(0);
        w.update(400 * kMs);
        CHECK(w.justLost(), "두절 진입을 알리지 않았다");
        w.update(500 * kMs);
        CHECK(w.lost(), "두절이 유지되지 않았다");
        CHECK(!w.justLost(), "두절이 계속되는데 진입을 또 알렸다 — 로그가 매 주기 쏟아진다");
    }

    // 4) 회복 — 원본 clearError 지점에 대응한다.
    {
        LostWatchdog w(300);
        w.start(0);
        w.update(400 * kMs);
        w.markReceived(450 * kMs);
        CHECK(!w.update(500 * kMs), "수신했는데 두절이 유지됐다");
        CHECK(w.justRecovered(), "회복을 알리지 않았다");
        w.update(550 * kMs);
        CHECK(!w.justRecovered(), "회복을 두 번 알렸다");
    }

    // 5) 한 건도 오지 않은 경우도 두절로 잡힌다 — 기준선이 활성화 시각이기 때문이다.
    //    everReceived 가 「끊김」과 「처음부터 없음」을 가른다.
    {
        LostWatchdog w(300);
        w.start(0);
        CHECK(w.update(1000 * kMs), "한 건도 안 왔는데 두절로 잡지 못했다");
        CHECK(!w.everReceived(), "받은 적 없는데 수신 이력이 있다고 한다");
        w.markReceived(1100 * kMs);
        CHECK(w.everReceived(), "받았는데 수신 이력이 없다고 한다");
    }

    // 6) 임계 범위는 원본과 같이 [0, 10000] 으로 자른다.
    {
        LostWatchdog w;
        CHECK(w.thresholdMs() == kDefaultLostThreshMs, "기본 임계가 원본(300)과 다르다");
        w.setThresholdMs(-5);
        CHECK(w.thresholdMs() == kMinLostThreshMs, "하한 밖 값이 잘리지 않았다");
        w.setThresholdMs(999999);
        CHECK(w.thresholdMs() == kMaxLostThreshMs, "상한 밖 값이 잘리지 않았다");
    }

    // 7) 경과 시간 보고 — 진단에 싣는 값이다.
    {
        LostWatchdog w(300);
        w.start(0);
        CHECK(w.elapsedMs(750 * kMs) == 750, "경과 시간이 ms 로 환산되지 않았다");
    }

    // 8) 원본에서 옮겨 온 값은 **리터럴로** 못 박는다. 상수끼리 비교하면 그 상수를 바꿔도
    //    시험이 통과해 버려 아무것도 지키지 못한다.
    CHECK(kErrorScanLost == 52102, "스캔 두절 에러 번호가 원본과 다르다");
    CHECK(kErrorOdoLost == 52106, "오도 두절 에러 번호가 원본과 다르다");
    CHECK(kDefaultLostThreshMs == 300, "기본 임계가 원본 바이너리 기본값(300 ms)과 다르다");
    CHECK(kMinLostThreshMs == 0 && kMaxLostThreshMs == 10000, "임계 범위가 원본([0,10000])과 다르다");

    if (g_fail == 0)
        std::printf("[PASS] 입력 두절 워치독 회귀 통과\n");
    else
        std::printf("[FAIL] %d 건 실패\n", g_fail);
    return g_fail == 0 ? 0 : 1;
}
