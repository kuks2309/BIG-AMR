// 기하 진입 단위 검증 — 이득 없는 직선 진입이 «경유점에서 수평 0» 을 만드는지,
// 그리고 조향 한계 밖을 제대로 걸러 내는지 못박는다.
//
// 근거 관계식(순수 crab, ω=0): d(cte_x)/dD = tan δ.
//   δ = atan(cte_x/e_d) 를 유지하면 d(cte_x)/d(e_d) = cte_x/e_d 이므로 cte_x ∝ e_d 이고,
//   e_d → 0 에서 cte_x → 0 이다. [4] 가 이 적분을 수치로 확인한다.
//
// 빌드: dock_control CMakeLists 의 dock_geom_entry_check 타깃. ROS 불요.
#include "dock_control/dock_core.hpp"

#include <cmath>
#include <cstdio>
#include <string>

namespace
{
constexpr double kPi = 3.14159265358979323846;
constexpr double kDeg = 180.0 / kPi;
int g_fail = 0;

void check(bool ok, const std::string &what)
{
    if (!ok)
    {
        ++g_fail;
        std::printf("  FAIL  %s\n", what.c_str());
    }
}
}  // namespace

int main()
{
    const double dmax = 25.0 / kDeg;
    std::printf("기하 진입 단위 검증 (delta 상한 %.1f deg)\n", dmax * kDeg);

    // ── 1. 한계 안에서는 **정확히 아크탄젠트** ──────────────────────────────
    {
        int n = 0;
        for (double e_d = 0.30; e_d <= 2.00 + 1e-9; e_d += 0.10)
        {
            for (double c = -0.10; c <= 0.10 + 1e-9; c += 0.02)
            {
                const double want = std::atan2(c, e_d);
                if (std::abs(want) > dmax) { continue; }
                check(std::abs(dock_control::geomEntryDelta(c, e_d, dmax) - want) < 1e-12,
                      "아크탄젠트 불일치: cte_x=" + std::to_string(c) +
                          " e_d=" + std::to_string(e_d));
                ++n;
            }
        }
        std::printf("  [1] 한계 안 = atan(cte_x/e_d) — %d점\n", n);
    }

    // ── 2. 한계 밖은 클램프되고, 그때 필요 횡이동량이 양수로 나온다 ─────────
    {
        const double c = -0.324, e_d = 0.30;          // |c|/e_d = 1.08 > tan25° = 0.466
        const double d = dock_control::geomEntryDelta(c, e_d, dmax);
        check(std::abs(d + dmax) < 1e-12, "클램프 실패: " + std::to_string(d * kDeg));
        const double need = dock_control::geomEntryTranslateNeed(c, e_d, dmax, 0.0);
        const double want = std::abs(c) - std::tan(dmax) * e_d;
        check(std::abs(need - want) < 1e-12, "필요 횡이동량 불일치: " + std::to_string(need));
        check(need > 0.0, "한계 밖인데 필요량이 0");
        std::printf("  [2] 한계 밖 → 클램프 %+.1f° · 필요 횡이동 %.3fm\n", d * kDeg, need);
    }

    // ── 3. 실기 시작 조건은 **가능** 해야 한다 ──────────────────────────────
    // D 1.62 · cte_x −0.324 · 경유점 0.90 → e_d 0.72 → δ* −24.2° (한계 25° 안)
    {
        const double c = -0.324, e_d = 1.62 - 0.90;
        const double d = dock_control::geomEntryDelta(c, e_d, dmax) * kDeg;
        check(std::abs(d + 24.2) < 0.2, "실기 조건 각도: " + std::to_string(d));
        check(dock_control::geomEntryTranslateNeed(c, e_d, dmax, 0.0) == 0.0,
              "실기 조건이 불가로 판정됐다");
        // 같은 조건에서 경유점을 1.00 으로 올리면 불가여야 한다(δ* −27.6°)
        check(dock_control::geomEntryTranslateNeed(c, 1.62 - 1.00, dmax, 0.0) > 0.0,
              "경유점 1.00m 가 가능으로 판정됐다");
        std::printf("  [3] 실기 시작조건 δ* %+.1f° — 경유점 0.90 가능 · 1.00 불가\n", d);
    }

    // ── 3b. **경유점 안쪽** — 남은 거리가 없어도 허용치 안이면 진입은 성립한다 ──
    // 실기(LM3003): 도크 1.096 m · 경유점 1.13 m → e_d −0.034 m. 3-2 가 수평을 3.2 mm 까지
    // 줄였는데도 종전 식은 그 값을 통째로 「부족분」으로 돌려줘 재시도 2 회를 소진하고 실패했다.
    // 그 자리는 필요 진입각이 0(순수 크랩 ±90°)이라 그대로 들어가면 된다.
    {
        const double e_d = 1.096 - 1.13;             // −0.034 (경유점 안쪽)
        const double tol = 0.004;                    // converge_tol_center_mm 4 mm
        check(dock_control::geomEntryTranslateNeed(0.0032, e_d, dmax, tol) == 0.0,
              "경유점 안쪽 + 허용치 안(3.2mm)인데 진입 불가로 판정됐다");
        // 허용치를 넘으면 **초과분만** 요구한다 — 「전부 없애라」가 아니다.
        const double over = dock_control::geomEntryTranslateNeed(0.030, e_d, dmax, tol);
        check(std::abs(over - 0.026) < 1e-12, "초과분 계산 불일치: " + std::to_string(over));
        // red 고정 — 허용치 0(종전 거동)이면 3.2 mm 도 불가로 남는다. 이 단정이 깨지면
        // 「고쳐도 아무것도 달라지지 않는 시험」이 된 것이다.
        check(dock_control::geomEntryTranslateNeed(0.0032, e_d, dmax, 0.0) > 0.0,
              "허용치 0 에서도 통과한다 — red 시험이 무효해졌다");
        std::printf("  [3b] 경유점 안쪽(e_d %+.3fm): 3.2mm 가능 · 30mm 는 %.3fm 필요\n", e_d, over);
    }

    // ── 4. **적분 검증** — 이 각을 유지하면 경유점에서 수평이 0 이 된다 ──────
    // dD 씩 접근하며 cte_x += tan δ · dD 를 적분한다. 모형 그대로다.
    {
        double c = -0.30, D = 1.60;
        const double Dw = 0.90, dD = -1e-4;
        int steps = 0;
        while (D > Dw + 1e-6 && steps < 200000)
        {
            const double d = dock_control::geomEntryDelta(c, D - Dw, dmax);
            c += std::tan(d) * dD;
            D += dD;
            ++steps;
        }
        check(std::abs(c) < 1e-3, "경유점에서 수평이 0 이 아니다: " + std::to_string(c));
        std::printf("  [4] 적분: cte_x -0.300 (D 1.60) → %+.5f (D %.2f)\n", c, D);
    }

    // ── 5. 경유점을 지난 뒤에는 0 을 낸다 — 부호 뒤집힌 각을 내면 안 된다 ────
    {
        check(dock_control::geomEntryDelta(-0.05, -0.10, dmax) == 0.0, "경유점 통과 후 비영");
        check(dock_control::geomEntryDelta(-0.05, 0.0, dmax) == 0.0, "e_d=0 에서 비영");
        std::printf("  [5] 경유점 통과 후 δ = 0\n");
    }

    // ── 6. 과조향 바이어스 ──────────────────────────────────────────────────
    // 오차 방향으로만 키운다 · 상한에서 클램프 · 기하각 0 이면 바이어스도 0.
    {
        const double bias = 3.0 / kDeg;
        const double e_d = 0.50;
        for (double c = -0.10; c <= 0.10 + 1e-9; c += 0.02)
        {
            const double base = dock_control::geomEntryDelta(c, e_d, dmax);
            const double b = dock_control::geomEntryDeltaBiased(c, e_d, dmax, bias);
            if (std::abs(base) < 1e-12)
            {
                // 비례 제한이라 결과는 최대 2배 — 0 이면 0 으로 남는다는 뜻이지
                // 비트 단위로 같다는 뜻이 아니다.
                check(std::abs(b) < 1e-11, "기하각 0 인데 바이어스가 붙었다");
                continue;
            }
            check(std::abs(b) > std::abs(base), "바이어스가 크기를 키우지 않았다");
            check(b * base > 0.0, "바이어스가 부호를 바꿨다");
            // 얹는 양은 min(bias, |기하각|) — 기하각이 작으면 그만큼만 얹는다(최대 2배).
            const double applied = std::min(bias, std::abs(base));
            check(std::abs(std::abs(b) - std::abs(base) - applied) < 1e-12,
                  "바이어스 크기가 다르다");
            check(std::abs(b) <= 2.0 * std::abs(base) + 1e-12, "기하각의 2배를 넘었다");
        }
        // 상한 클램프 — 이미 포화면 더 커지지 않는다
        const double sat = dock_control::geomEntryDeltaBiased(-0.50, 0.30, dmax, bias);
        check(std::abs(sat + dmax) < 1e-12, "포화 상태에서 상한을 넘었다");
        // 경유점 통과 후에는 기하각이 0 이므로 바이어스도 0
        check(dock_control::geomEntryDeltaBiased(-0.05, -0.1, dmax, bias) == 0.0,
              "경유점 통과 후 바이어스가 붙었다");
        std::printf("  [6] 과조향 바이어스 — 방향 유지 · min(bias,|δ*|) · 클램프 · 0 보존\n");
    }

    if (g_fail == 0)
    {
    // ── §3c 가변 경유점 — 조향이 지울 수 있는 만큼이 곧 경유점이다 ────────────────
    //
    // `dock_ros_node::waypointD` 가 쓰는 관계를 코어 함수로 고정한다:
    //   경유점 = target_d + |cte_x| / tan(δ_eff)  ⇔  그 지점의 `need` 가 정확히 0 이다.
    // 종전 고정 경유점(target + 0.60)이 만들던 «오차가 작아도 안쪽» 자리가 사라졌음을 본다.
    {
        const double dmax = 17.0 / kDeg;          // δ_eff = δmax 20 − 과조향 3
        const double target = 0.530;
        for (const double cte : {0.003, 0.030, 0.095, 0.150})
        {
            const double wp = target + std::abs(cte) / std::tan(dmax);
            // 경유점에 정확히 서면 남은 거리 0 — 허용치 0 에서도 «더 지울 것 없음» 이어야 한다.
            check(dock_control::geomEntryTranslateNeed(cte, 0.0, dmax, std::abs(cte)) == 0.0,
                  "§3c 경유점 위: 허용치가 오차만큼이면 need 0");
            // 경유점 **밖**(여유 1 mm)이면 굴러가며 지울 수 있다.
            check(dock_control::geomEntryTranslateNeed(cte, 0.001, dmax, 0.0) < std::abs(cte),
                  "§3c 경유점 밖: 남은 거리가 오차를 줄인다");
            // 실기 조건 — LM3003 정차 1.10 m. 고정 경유점(1.13)이면 안쪽이지만 가변이면 밖이다.
            if (std::abs(cte - 0.095) < 1e-9)
            {
                check(wp < 1.10, "§3c LM3003 조건에서 가변 경유점은 정차 거리보다 앞이다");
                check(target + 0.60 > 1.10, "§3c 같은 조건에서 고정 경유점은 뒤였다(회귀 표식)");
            }
        }
        // 정말 못 지우는 조건은 경유점이 밖으로 밀려 가드가 발동한다.
        const double wp_far = 0.530 + 0.300 / std::tan(dmax);
        check(wp_far > 1.10, "§3c 큰 오차(300 mm)면 경유점이 정차 거리 밖 — translate 가드");
    }

        std::printf("OK: 기하 진입 단위 검증 통과\n");
        return 0;
    }
    std::printf("FAIL: %d 건\n", g_fail);
    return 1;
}
