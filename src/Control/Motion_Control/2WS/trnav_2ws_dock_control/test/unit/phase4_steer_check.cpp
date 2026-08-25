// phase4Steer 단위 검증 — 조향 합성의 **부호**를 물리 규칙으로 못박는다.
//
// 왜 이 시험이 있는가: 정본 기체는 **좌측 접근(as=+1)** 뿐이라 `as·π/2 − δ` 와 `as·(π/2 − δ)`
// 가 같은 값을 낸다. 차이는 우측 접근에서만 드러나고, 틀리면 δ 가 오차를 **키우는** 방향으로
// 붙어 마커가 시야 밖으로 나간다.
//
// 물리 규칙(본 기체 실측 — Docking_Control/docs 의 「3축 부호·응답 실측」 §수평축):
//   **+x 전진 → err_px 증가.**
//   ⇒ err_px < 0 이면 오차를 줄이려면 +x 성분(cos(steer) > 0)이 필요하고,
//     err_px > 0 이면 −x 성분(cos(steer) < 0)이 필요하다.
//
// 빌드: dock_control CMakeLists 의 dock_phase4_steer_check 타깃. ROS 불요.
#include "dock_control/dock_core.hpp"

#include <algorithm>
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

/// 정본 식(:1844) 그대로 — 좌측 접근에서 우리 식과 같아야 한다.
double canonSteer(double as, double delta, double dmax)
{
    const double s = as * (kPi / 2.0) - delta;
    const double slim = kPi / 2.0 + dmax;
    return std::max(-slim, std::min(slim, s));
}
}  // namespace

int main()
{
    const double dmax = 25.0 / kDeg;
    const double kp = 0.015;                 // pid_lateral_kp — 부호만 보므로 크기는 무관
    std::printf("phase4Steer 단위 검증 (delta 상한 %.1f deg)\n", dmax * kDeg);

    // ── 1. 좌측 접근은 정본과 **완전히 같아야 한다** ────────────────────────
    for (double d_deg = -25.0; d_deg <= 25.0 + 1e-9; d_deg += 2.5)
    {
        const double d = d_deg / kDeg;
        const double ours = dock_control::phase4Steer(+1.0, d, dmax);
        const double canon = canonSteer(+1.0, d, dmax);
        check(std::abs(ours - canon) < 1e-12,
              "좌측 접근이 정본과 다르다: delta=" + std::to_string(d_deg));
    }
    std::printf("  [1] 좌측 접근(as=+1) = 정본 식 — 21점 일치\n");

    // ── 2. 우측 접근은 좌측의 거울상이어야 한다 ─────────────────────────────
    for (double d_deg = -25.0; d_deg <= 25.0 + 1e-9; d_deg += 2.5)
    {
        const double d = d_deg / kDeg;
        check(std::abs(dock_control::phase4Steer(-1.0, d, dmax) +
                       dock_control::phase4Steer(+1.0, d, dmax)) < 1e-12,
              "우측이 좌측의 거울상이 아니다: delta=" + std::to_string(d_deg));
    }
    std::printf("  [2] 우측 접근(as=-1) = 좌측의 부호 반전 — 21점 일치\n");

    // ── 3. **오차를 줄이는 방향인가** ───────────────────────────────────────
    // 실측 규칙(+x 전진 → err_px 증가)은 **우측 카메라인 본 기체의 사실**이다.
    // 좌측 접근 기체는 카메라가 거울상이라 규칙도 뒤집히므로 여기서 함께 단정하지 않는다
    // — 좌측은 [1](정본 식 동일)·[2](거울상)로 이미 묶여 있다.
    // e_px = travel·as·err_px, delta = kp·e_px (포화 전). travel=+1(전진 구간) 고정.
    int n3 = 0;
    {
        const double as = -1.0;                          // 본 기체: 우측 접근
        for (double err = -200.0; err <= 200.0 + 1e-9; err += 20.0)
        {
            if (std::abs(err) < 1e-9) { continue; }
            const double e_px = 1.0 * as * err;
            const double d = std::max(-dmax, std::min(dmax, kp * e_px));
            const double steer = dock_control::phase4Steer(as, d, dmax);
            const double x_comp = std::cos(steer);       // 진행 방향의 x 성분
            const bool want_forward = err < 0.0;         // err_px<0 → +x 로 키워야 0 에 간다
            check(want_forward == (x_comp > 0.0),
                  "as=-1 err_px=" + std::to_string(err) +
                      " → steer=" + std::to_string(steer * kDeg) +
                      " x=" + std::to_string(x_comp));
            ++n3;
        }
    }
    std::printf("  [3] 오차 감소 방향 (본 기체 as=-1) — %d점\n", n3);

    // ── 4. 실기에서 실제로 났던 조건 ────────────────────────────────────────
    {
        const double err = -110.8, as = -1.0;
        const double d = std::max(-dmax, std::min(dmax, kp * (1.0 * as * err)));
        const double steer = dock_control::phase4Steer(as, d, dmax) * kDeg;
        check(std::abs(steer + 65.0) < 0.5,
              "실기 조건 재현 실패: err_px -110.8 · as=-1 → " + std::to_string(steer));
        std::printf("  [4] 실기 조건 err_px -110.8 → 조향 %+.1f deg (종전 식 -115.0)\n", steer);
    }

    // ── 5. 클램프 ───────────────────────────────────────────────────────────
    {
        const double slim = (kPi / 2.0 + dmax) * kDeg;
        check(std::abs(dock_control::phase4Steer(+1.0, -10.0, dmax) * kDeg - slim) < 1e-9,
              "상한 클램프 실패");
        check(std::abs(dock_control::phase4Steer(-1.0, -10.0, dmax) * kDeg + slim) < 1e-9,
              "하한 클램프 실패");
        std::printf("  [5] 클램프 +-%.1f deg\n", slim);
    }

    // ── 6. 정렬선 오차의 **픽셀 환산은 접근측에 종속**이다 ──────────────────
    // 실측 2점이 `base_link x = as · err_px · z / fx` 로 일치한다:
    //   · RIGHT(as=-1) `err_px +196.0` ↔ `cte_x -0.3101`
    //   · LEFT (as=+1) `err_px  -93.6` ↔ `cte_x -0.0961`
    // 그리고 로봇은 **오차와 같은 부호로** 움직여야 마커가 정렬선에 온다(3-2 실측: LEFT 에서
    // err_px>0 에 전진(+x)이 오차를 줄였고, RIGHT 는 그 거울상이라 후진이 줄였다).
    // 진입각은 `atan(ex/e_d)` 이므로 아래는 「진입 구간의 x 성분이 오차와 같은 부호인가」다.
    {
        const double z = 1.0, fx = 607.66943359375, e_d = 0.35, bias = 3.0 / kDeg;
        int n6 = 0;
        for (const double as : {-1.0, +1.0})
        {
            for (double err = -200.0; err <= 200.0 + 1e-9; err += 20.0)
            {
                if (std::abs(err) < 1e-9) { continue; }
                const double ex = as * err * z / fx;                 // 접근측 반영 환산
                const double d = dock_control::geomEntryDeltaBiased(ex, e_d, dmax, bias);
                const double x_comp = std::cos(dock_control::phase4Steer(as, d, dmax));
                check((ex > 0.0) == (x_comp > 0.0),
                      "진입 x 성분이 오차 부호와 다르다: as=" + std::to_string(as) +
                          " err_px=" + std::to_string(err));
                ++n6;
            }
        }
        std::printf("  [6] 진입 x 성분 = 오차 부호 (as=+-1 양쪽) — %d점\n", n6);

        // red 고정 — 접근측을 뺀 **고정 부호** 환산(종전 `lineErrX`)은 as=+1 에서 반대로 간다.
        // 이 단정이 깨지면 「고쳐도 아무것도 달라지지 않는 시험」이 된 것이다.
        const double err = 100.0, as = +1.0;
        const double ex_fixed = -err * z / fx;                       // 종전 규약
        const double d_fixed = dock_control::geomEntryDeltaBiased(ex_fixed, e_d, dmax, bias);
        const double x_fixed = std::cos(dock_control::phase4Steer(as, d_fixed, dmax));
        const double ex_true = as * err * z / fx;
        check((ex_true > 0.0) != (x_fixed > 0.0),
              "고정 부호 환산이 as=+1 에서 오차를 줄인다 — red 시험이 무효해졌다");
        std::printf("  [6-red] 고정 부호 환산은 as=+1 에서 오차를 키운다 (확인)\n");
    }

    if (g_fail == 0)
    {
        std::printf("OK: phase4Steer 단위 검증 통과\n");
        return 0;
    }
    std::printf("FAIL: %d 건\n", g_fail);
    return 1;
}
