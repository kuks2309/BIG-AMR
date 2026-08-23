// reachableSteer 단위 검증 — **±180° 를 후보로 삼지 않는다**를 못박는다.
//
// 왜 이 시험이 있는가 (실기 bag `acs2-0816-083709` 실측):
//   후보에 `tgt ± 180°` 가 있던 판은 코어가 앞뒤 같은 값(−110°)을 냈는데도 축마다 **다른
//   표현**을 채택했다 — 앞축은 현재 +70° 라 `−110+180 = +70` 이, 뒤축은 −110° 가 나갔다.
//   그 상태에서 관측이 끊겨 정지 유지로 빠지자 앞바퀴에 −110° 가 나가 **반 바퀴를 쓸며**
//   조향 한계에 박혔다(실측 궤적 +65 → +45 → +18 → −7.9 → −35 → −63 → −89 → −106).
//   덧붙여 ±180° 는 「같은 직선, 구동 부호 반대」라 각도만 뒤집으면 그 바퀴가 반대로 민다.
//
// 그래서 여기서 보는 것은 셋이다:
//   ① 같은 목표를 주면 현재각이 달라도 **같은 값**이 나온다 (축이 갈리지 않는다)
//   ② 구간 밖 목표는 «없음» 이다 (반대 표현으로 우회하지 않는다)
//   ③ 현재각이 이미 구간 밖이면 «없음» 이다 (그 자리는 사람이 호밍해야 한다)
//
// 빌드: dock_control CMakeLists 의 dock_reachable_steer_check 타깃. ROS 불요.
#include "dock_control/dock_core.hpp"

#include <cmath>
#include <cstdio>
#include <string>

namespace
{
constexpr double kPi = 3.14159265358979323846;
constexpr double kRad = kPi / 180.0;
int g_fail = 0;

void check(bool ok, const std::string &what)
{
    if (!ok)
    {
        ++g_fail;
        std::printf("  FAIL %s\n", what.c_str());
    }
}

bool nearDeg(double rad, double deg) { return std::abs(rad / kRad - deg) < 1e-6; }

/// 실기 조향 구간과 같은 값(`steer_cmd_limit_deg` 기본 115°).
constexpr double kLim = 115.0 * kRad;

}  // namespace

int main()
{
    using dock_control::reachableSteer;

    // ① 축이 갈리지 않는다 — 같은 목표는 현재각과 무관하게 같은 값.
    //    이것이 실기에서 깨졌던 바로 그 조건이다(앞 +70° · 뒤 −110°, 목표 둘 다 −110°).
    {
        const auto f = reachableSteer(+70.0 * kRad, -110.0 * kRad, kLim);
        const auto r = reachableSteer(-110.0 * kRad, -110.0 * kRad, kLim);
        check(f.has_value && r.has_value, "앞뒤 모두 보낼 각이 있다");
        check(f.has_value && nearDeg(f.value, -110.0), "앞축도 −110° — 반대 표현(+70°)을 고르지 않는다");
        check(r.has_value && nearDeg(r.value, -110.0), "뒤축 −110°");
        check(f.has_value && r.has_value && std::abs(f.value - r.value) < 1e-12,
              "같은 목표는 현재각과 무관하게 같은 값 (축이 갈리지 않는다)");
    }

    // ② 구간 밖 목표는 «없음». ±180° 로 우회해 구간 안으로 들어오게 만들지 않는다.
    {
        const auto a = reachableSteer(0.0, 130.0 * kRad, kLim);
        check(!a.has_value, "목표 +130° 는 구간 밖 — 보낼 각 없음 (−50° 로 바꿔 내지 않는다)");
        const auto b = reachableSteer(0.0, -130.0 * kRad, kLim);
        check(!b.has_value, "목표 −130° 도 마찬가지");
    }

    // ③ 현재각이 구간 밖이면 «없음» — 원점이 어긋난 상태를 지령으로 덮지 않는다.
    //    실기의 +137.26°(조향 드라이브 원점 소실)가 이 자리다. 호밍이 처방이다.
    {
        const auto a = reachableSteer(137.26 * kRad, 0.0, kLim);
        check(!a.has_value, "현재 +137.26° 면 보낼 각 없음 — 사람이 호밍해야 한다");
    }

    // 정상 범위는 그대로 통과한다.
    {
        const auto a = reachableSteer(0.0, 90.0 * kRad, kLim);
        check(a.has_value && nearDeg(a.value, 90.0), "정상 목표 +90° 는 그대로");
        const auto b = reachableSteer(-90.0 * kRad, -110.0 * kRad, kLim);
        check(b.has_value && nearDeg(b.value, -110.0), "정상 목표 −110° 는 그대로");
    }

    // ±360° 는 같은 각이므로 구간 안으로 접힌다 — 표현이 달라도 판정이 흔들리지 않는다.
    {
        const auto a = reachableSteer(0.0, 90.0 * kRad - 2.0 * kPi, kLim);
        check(a.has_value && nearDeg(a.value, 90.0), "−270° 로 들어와도 +90° 로 낸다");
    }

    // 비유한 입력은 «없음».
    {
        check(!reachableSteer(0.0, std::nan(""), kLim).has_value, "NaN 목표는 보내지 않는다");
        check(!reachableSteer(std::nan(""), 0.0, kLim).has_value, "NaN 현재각도 마찬가지");
    }

    if (g_fail == 0)
    {
        std::printf("reachable_steer_check: 전 케이스 PASS\n");
        return 0;
    }
    std::printf("reachable_steer_check: %d 건 FAIL\n", g_fail);
    return 1;
}
