// 원위치(RETURN_HOME) 판정 3종 단위 검증 — 정본 do_return_home 의 «판정» 부분.
//
// 이 시험이 지키는 것은 셋이고, 전부 실기에서 값비싸게 배운 것이다:
//   · **완료는 거리 단독** — 3축으로 통일하면 거리 수렴 후 v→0 이라 수평 교정 수단이 없어
//     영구 대기로 교착한다(정본 :2048~2051, FAILURES #24). 사용자 확정 규약이라 코드로 동결한다.
//   · **중단 판정 순서** — 정본은 라이다가 없으면 continue(:2040) 하므로 대기 중에는 FOV·
//     timeout 을 검사하지 않는다. 순서가 바뀌면 「대기 초과」가 「시간 초과」로 보고돼 오진한다.
//   · **주입 오차의 역변환** — :2065 는 :2047 정변환의 역함수여야 한다. 어긋나면 주입한 목표와
//     완료 로그의 달성값이 서로 다른 좌표를 말해 반복 시험 산출물을 못 읽는다.
//
// 빌드: dock_control CMakeLists 의 dock_return_home_check 타깃. ROS 불요.
#include "dock_control/dock_core.hpp"

#include <cmath>
#include <cstdio>
#include <utility>

namespace
{
int g_fail = 0;

using dock_control::HomeAbort;
using dock_control::HomeAbortInput;

const char *name(HomeAbort a)
{
    switch (a)
    {
        case HomeAbort::OK: return "OK";
        case HomeAbort::STALE: return "STALE";
        case HomeAbort::MARKER_WAIT: return "MARKER_WAIT";
        case HomeAbort::LIDAR_WAIT: return "LIDAR_WAIT";
        case HomeAbort::LIDAR_OVER: return "LIDAR_OVER";
        case HomeAbort::FOV: return "FOV";
        case HomeAbort::TIMEOUT: return "TIMEOUT";
    }
    return "?";
}

/// 정상 진행 입력 — 각 시험이 여기서 한 항목만 어긋뜨린다.
/// 값은 정본 상수: FOV 200 px(:178) · 라이다 대기 5 s(:225) · timeout 90 s(:232).
HomeAbortInput nominal()
{
    HomeAbortInput in;
    in.obs_fresh = true;
    in.has_lateral = true;
    in.has_range = true;
    in.err_px = 10.0;
    in.fov_edge_px = 200.0;
    in.marker_lost_elapsed_s = 0.0;
    in.marker_grace_s = 0.8;         // home_marker_grace_s
    in.lidar_wait_elapsed_s = 0.0;
    in.lidar_wait_limit_s = 5.0;
    in.elapsed_s = 3.0;
    in.timeout_s = 90.0;
    return in;
}

void expectAbort(const HomeAbortInput &in, HomeAbort want, const char *what)
{
    const HomeAbort got = dock_control::returnHomeAbort(in);
    if (got != want)
    {
        ++g_fail;
        std::printf("  FAIL  %-44s -> %s (기대 %s)\n", what, name(got), name(want));
    }
}

void expectDone(double e_d, double tol, bool want, const char *what)
{
    const bool got = dock_control::returnHomeDone(e_d, tol);
    if (got != want)
    {
        ++g_fail;
        std::printf("  FAIL  %-44s -> %d (기대 %d)\n", what, got, want);
    }
}
}  // namespace

int main()
{
    std::printf("원위치 판정 단위 검증\n");

    // ── 1. 완료 게이트 = 거리 단독 ─────────────────────────────────────────
    const double tol = 0.03;   // 정본 :229 RETURN_TOL_D
    std::printf("\n[1] returnHomeDone — 거리 단독\n");
    expectDone(0.0, tol, true, "e_d 0");
    expectDone(0.029, tol, true, "e_d +29 mm (안쪽)");
    expectDone(-0.029, tol, true, "e_d -29 mm (안쪽, 후퇴측)");
    expectDone(tol, tol, true, "e_d = tol (경계 포함 — 정본은 <=)");
    expectDone(0.031, tol, false, "e_d +31 mm (밖)");
    expectDone(-0.031, tol, false, "e_d -31 mm (밖)");
    // 시그니처가 (e_d, tol) 뿐이라는 사실 자체가 «거리 단독» 의 강제다 — 축을 끼워넣는
    // 개정이 오면 이 호출부가 컴파일되지 않아 드러난다. 그것이 함수로 떼어낸 이유다.
    expectDone(0.005, tol, true, "수평·자세와 무관하게 거리만 (e_d 5 mm)");

    // ── 2. 중단 판정 — 정본 제어흐름 순서 ──────────────────────────────────
    std::printf("\n[2] returnHomeAbort — 사유와 순서\n");
    expectAbort(nominal(), HomeAbort::OK, "정상 진행");

    {   // 관측 자체가 낡으면 유예 없이 즉시 STALE — 값이 못 믿을 것이다
        HomeAbortInput in = nominal();
        in.obs_fresh = false;
        expectAbort(in, HomeAbort::STALE, "관측 낡음 (유예 대상 아님)");
    }

    {   // marker 결손은 **유예** 안에서는 대기다 — 정본은 즉시 중단이나, 관측 미수신을
        // 0.5 s 견디면서 「못 봤다」는 보고에 즉사하는 것은 앞뒤가 맞지 않는다.
        // 실기 실측: 결손 5.1%, 연속 최대 0.49 s → 1프레임 규칙으로는 복귀가 완주 불가.
        HomeAbortInput in = nominal();
        in.has_lateral = false;
        in.marker_lost_elapsed_s = 0.0;
        expectAbort(in, HomeAbort::MARKER_WAIT, "marker 결손 직후 = 대기");
        in.marker_lost_elapsed_s = 0.49;
        expectAbort(in, HomeAbort::MARKER_WAIT, "결손 0.49s (실측 최대 버스트) = 대기");
        in.marker_lost_elapsed_s = 0.8;
        expectAbort(in, HomeAbort::MARKER_WAIT, "결손 = 유예 (정본은 > 로 중단)");
        in.marker_lost_elapsed_s = 0.81;
        expectAbort(in, HomeAbort::STALE, "결손 0.81s (유예 초과) = 종료");
    }

    {   // 유예 중에는 라이다·FOV·timeout 을 보지 않는다 — 눈이 감긴 동안의 값이다
        HomeAbortInput in = nominal();
        in.has_lateral = false;
        in.has_range = false;
        in.err_px = 500.0;
        in.elapsed_s = 120.0;
        expectAbort(in, HomeAbort::MARKER_WAIT, "marker 결손이 라이다·FOV·timeout 을 이긴다");
    }

    {   // 라이다 결측은 **중단이 아니라 대기**. 한도를 넘어야 중단 (정본 :2032~2040)
        HomeAbortInput in = nominal();
        in.has_range = false;
        expectAbort(in, HomeAbort::LIDAR_WAIT, "라이다 결측 직후 = 대기");
        in.lidar_wait_elapsed_s = 4.9;
        expectAbort(in, HomeAbort::LIDAR_WAIT, "대기 4.9 s (한도 안)");
        in.lidar_wait_elapsed_s = 5.0;
        expectAbort(in, HomeAbort::LIDAR_WAIT, "대기 = 한도 (정본은 > 로 중단)");
        in.lidar_wait_elapsed_s = 5.1;
        expectAbort(in, HomeAbort::LIDAR_OVER, "대기 5.1 s (한도 초과)");
    }

    {
        HomeAbortInput in = nominal();
        in.err_px = 200.1;
        expectAbort(in, HomeAbort::FOV, "err_px +200.1 px");
        in.err_px = -200.1;
        expectAbort(in, HomeAbort::FOV, "err_px -200.1 px (부호 무관)");
        in.err_px = 200.0;
        expectAbort(in, HomeAbort::OK, "err_px = 경계 (정본은 > 로 중단)");
    }
    {
        HomeAbortInput in = nominal();
        in.elapsed_s = 90.1;
        expectAbort(in, HomeAbort::TIMEOUT, "경과 90.1 s");
        in.elapsed_s = 90.0;
        expectAbort(in, HomeAbort::OK, "경과 = 경계 (정본은 > 로 중단)");
    }

    // **순서**가 이 함수의 계약이다. 아래 셋이 뒤집히면 사유가 원인을 가리키지 못한다.
    {   // 라이다 대기 중 timeout 이 지나도 «대기» 여야 한다 (정본 :2040 continue)
        HomeAbortInput in = nominal();
        in.has_range = false;
        in.lidar_wait_elapsed_s = 1.0;
        in.elapsed_s = 120.0;
        expectAbort(in, HomeAbort::LIDAR_WAIT, "라이다 대기 중 timeout 경과 -> 대기 우선");
    }
    {   // 관측이 낡으면 err_px 자체가 못 믿을 값이라 STALE 이 FOV 보다 먼저다
        HomeAbortInput in = nominal();
        in.obs_fresh = false;
        in.err_px = 500.0;
        expectAbort(in, HomeAbort::STALE, "관측 낡음 + FOV 초과 -> STALE 우선");
    }
    {
        HomeAbortInput in = nominal();
        in.has_range = false;
        in.err_px = 500.0;
        expectAbort(in, HomeAbort::LIDAR_WAIT, "라이다 결측 + FOV 초과 -> 대기 우선");
    }

    // ── 3. 주입 오차 역변환 ────────────────────────────────────────────────
    // 정본 :2047 정변환: x_mm      = err_px * z_cam / fx * 1000
    // 정본 :2065 역변환: err_px_tgt = dx_mm  * fx    / (z_cam * 1000)
    std::printf("\n[3] homeErrPxTarget — :2047 정변환의 역함수\n");
    {
        const double z = 1.2, fx = 615.0;
        for (const double dx_mm : {-150.0, -37.5, 0.0, 12.0, 150.0})
        {
            const double px = dock_control::homeErrPxTarget(dx_mm, z, fx);
            const double back = px * z / fx * 1000.0;      // 정본 :2047 정변환
            if (std::abs(back - dx_mm) > 1e-9)
            {
                ++g_fail;
                std::printf("  FAIL  dx %.1f mm -> %.4f px -> %.6f mm (왕복 불일치)\n",
                            dx_mm, px, back);
            }
        }
        // 무주입은 정확히 0 이어야 한다 — 아니면 «주입 없음» 시행에 편향이 섞인다.
        if (dock_control::homeErrPxTarget(0.0, z, fx) != 0.0)
        {
            ++g_fail;
            std::printf("  FAIL  dx 0 mm 이 0 px 가 아니다\n");
        }
        // 변환 불가 관측 — 0(무주입)이어야 한다. inf/NaN 이 나가면 δ 가 통째로 오염된다.
        const std::pair<double, double> bad[] = {{0.0, fx}, {z, 0.0}, {0.0, 0.0}};
        for (const auto &c : bad)
        {
            const double px = dock_control::homeErrPxTarget(150.0, c.first, c.second);
            if (px != 0.0 || !std::isfinite(px))
            {
                ++g_fail;
                std::printf("  FAIL  z=%.1f fx=%.1f -> %.4f (0 이어야 한다)\n",
                            c.first, c.second, px);
            }
        }
    }

    std::printf("\n%s — 실패 %d건\n", g_fail == 0 ? "PASS" : "FAIL", g_fail);
    return g_fail == 0 ? 0 : 1;
}
