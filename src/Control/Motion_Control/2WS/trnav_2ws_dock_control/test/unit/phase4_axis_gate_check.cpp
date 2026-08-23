// phase4AxesReady 단위 검증 — 게이트가 **쓰는 축만** 요구하는지 못박는다.
//
// 두 방향으로 틀릴 수 있고 둘 다 실기 실패다:
//   · 너무 느슨 — 무효 축의 잔류값으로 지령을 만든다(정본 실패 10회의 원인).
//   · 너무 빡빡 — 지령에 기여하지도 않는 축 때문에 제어가 멈춘다(검은 배경에서 자세축
//     유효율 4.2%, 순수 crab 시행의 마지막 구간이 정지·재개를 반복).
//
// 빌드: dock_control CMakeLists 의 dock_phase4_axis_gate_check 타깃. ROS 불요.
#include "dock_control/dock_core.hpp"

#include <cstdio>

namespace
{
int g_fail = 0;

void expect(bool has_lat, bool has_rng, bool has_yaw, bool yaw_active, bool want)
{
    const bool got = dock_control::phase4AxesReady(has_lat, has_rng, has_yaw, yaw_active);
    if (got != want)
    {
        ++g_fail;
        std::printf("  FAIL  lat=%d rng=%d yaw=%d yawActive=%d -> %d (기대 %d)\n",
                    has_lat, has_rng, has_yaw, yaw_active, got, want);
    }
}
}  // namespace

int main()
{
    std::printf("phase4AxesReady 단위 검증\n");

    // ── 1. 수평·거리축은 **언제나** 필수 ────────────────────────────────────
    // δ 와 v_app, 그리고 완료 판정(x_ok·d_ok)이 이 둘을 직접 소비한다.
    for (int ya = 0; ya <= 1; ++ya)
    {
        for (int y = 0; y <= 1; ++y)
        {
            expect(false, true, y != 0, ya != 0, false);   // 수평 없음 → 불가
            expect(true, false, y != 0, ya != 0, false);   // 거리 없음 → 불가
            expect(false, false, y != 0, ya != 0, false);
        }
    }
    std::printf("  [1] 수평·거리축 무효 → 항상 차단 (12점)\n");

    // ── 2. 자세축이 살아 있으면 이득과 무관하게 통과 ────────────────────────
    expect(true, true, true, true, true);
    expect(true, true, true, false, true);
    std::printf("  [2] 3축 모두 유효 → 통과 (2점)\n");

    // ── 3. 자세축만 무효일 때 — **이득이 갈림길** ───────────────────────────
    // 이득이 살아 있으면 ω 가 그 축을 소비하므로 잔류값을 쓸 수 없다 → 차단.
    expect(true, true, false, true, false);
    // 이득이 0 이면 ω ≡ 0 이라 그 축의 기여분이 없다 → 통과(순수 crab).
    expect(true, true, false, false, true);
    std::printf("  [3] 자세축 무효: 이득 있으면 차단 · 이득 0 이면 통과 (2점)\n");

    if (g_fail == 0)
    {
        std::printf("OK: phase4AxesReady 단위 검증 통과\n");
        return 0;
    }
    std::printf("FAIL: %d 건\n", g_fail);
    return 1;
}
