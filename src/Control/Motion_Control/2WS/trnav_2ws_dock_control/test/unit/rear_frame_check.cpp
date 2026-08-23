// steerFrameOffset — 후방 접근에서 **명령 프레임만** 90° 도는지 고정한다.
//
// 이 시험이 지키는 명제: «알고리즘은 그대로, 방향만 바뀐다».
//   · 좌·우는 오프셋 0 이라 종전 동작이 한 치도 안 바뀐다.
//   · 후방은 3-2 가 크랩(∓90°), Phase 4 가 후진 직진(≈0°)이 된다 — 제어식·게인·수렴판정은
//     하나도 손대지 않고 조향 목표에 오프셋을 더하는 것만으로.
//
// 값이 아니라 **관계**를 시험한다. `phase4Steer` 가 나중에 바뀌어도 «접근은 거리축을 따라
// 곧게» 라는 성질이 깨지면 여기서 걸린다.
#include "dock_control/dock_core.hpp"

#include <cmath>
#include <cstdio>

namespace
{
int fails = 0;

void check(bool ok, const char *what, double got, double want)
{
    if (ok) { return; }
    std::printf("  ❌ %s — got %+.6f want %+.6f\n", what, got, want);
    ++fails;
}

void near(double got, double want, const char *what, double tol = 1e-9)
{
    check(std::abs(got - want) <= tol, what, got, want);
}
}  // namespace

int main()
{
    using namespace dock_control;
    const double HALF_PI = M_PI / 2.0;
    const double DMAX = 0.35;   // δ 상한 — 값 자체는 이 시험의 관심사가 아니다

    std::printf("== 좌·우는 오프셋 0 (종전 동작 불변) ==\n");
    near(steerFrameOffset(false, +1.0), 0.0, "LEFT  offset");
    near(steerFrameOffset(false, -1.0), 0.0, "RIGHT offset");

    std::printf("== 후방은 −as·90° ==\n");
    near(steerFrameOffset(true, +1.0), -HALF_PI, "REAR(as=+1) offset");
    near(steerFrameOffset(true, -1.0), +HALF_PI, "REAR(as=-1) offset");

    std::printf("== 3-2 수평 정렬 — 좌·우 직진 / 후방 크랩 ==\n");
    // 3-2 의 조향 목표는 «0 + 오프셋» 이다(dock_ros_node).
    near(0.0 + steerFrameOffset(false, +1.0), 0.0, "3-2 LEFT  = 직진(0°)");
    near(0.0 + steerFrameOffset(false, -1.0), 0.0, "3-2 RIGHT = 직진(0°)");
    for (double as : {+1.0, -1.0})
    {
        const double s = 0.0 + steerFrameOffset(true, as);
        check(std::abs(std::abs(s) - HALF_PI) <= 1e-9, "3-2 REAR = 크랩(±90°)",
              std::abs(s), HALF_PI);
    }

    std::printf("== Phase 4 접근 — 좌·우 크랩 / 후방 후진 직진 ==\n");
    for (double as : {+1.0, -1.0})
    {
        // δ=0(정면 진입)에서 좌·우는 ±90° 크랩
        const double side = phase4Steer(as, 0.0, DMAX) + steerFrameOffset(false, as);
        check(std::abs(std::abs(side) - HALF_PI) <= 1e-9, "P4 좌·우 = 크랩(±90°)",
              std::abs(side), HALF_PI);
        // 같은 조건에서 후방은 0° — 거리축(후방)을 따라 곧게 간다
        const double rear = phase4Steer(as, 0.0, DMAX) + steerFrameOffset(true, as);
        near(rear, 0.0, "P4 REAR = 후진 직진(0°)");
    }

    std::printf("== δ 보정은 후방에서도 같은 크기로 남는다 ==\n");
    // 진입 보정 δ 는 «크랩 기준각에서 얼마나 튼다» 는 값이다. 프레임을 돌려도 그 크기는
    // 보존돼야 한다 — 안 그러면 같은 오차에 다른 보정이 걸린다.
    for (double as : {+1.0, -1.0})
    {
        for (double delta : {0.05, 0.2, 0.35})
        {
            const double rear = phase4Steer(as, delta, DMAX) + steerFrameOffset(true, as);
            near(std::abs(rear), delta, "P4 REAR 잔여각 = δ", 1e-9);
        }
    }

    if (fails == 0) { std::printf("\n✅ rear_frame_check 통과\n"); }
    else { std::printf("\n❌ rear_frame_check 실패 %d건\n", fails); }
    return fails == 0 ? 0 : 1;
}
