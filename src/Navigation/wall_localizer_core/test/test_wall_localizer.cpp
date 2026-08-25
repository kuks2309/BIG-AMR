// WallLocalizer 파사드 통합검증 — 합성 스캔 E2E 정밀도·퇴화·점프 게이트·복귀.

#include <cmath>
#include <cstdio>

#include "sim_scan.hpp"
#include "wall_localizer_core/wall_localizer.hpp"

using namespace wall_localizer_core;
using wall_localizer_test::simulateScan;

namespace
{

constexpr int kBeams = 720;
constexpr double kAngleMin = -M_PI;
constexpr double kAngleInc = 2.0 * M_PI / kBeams;
constexpr double kRangeMax = 10.0;

// U자 스테이션: 전방 벽 + 좌·우 벽 (스테이션 프레임, m)
const std::vector<WallRef> kStationWalls = {{"front", {2.0, -1.5}, {2.0, 1.5}},
                                            {"left", {0.0, 1.5}, {2.0, 1.5}},
                                            {"right", {0.0, -1.5}, {2.0, -1.5}}};

const Pose2D kLaserInBase{0.3, 0.0, 0.0};      // base_link 내 라이다 장착 자세
const Pose2D kInitialGuess{0.4, 0.0, 0.0};     // 스테이션 진입 초기 추정

std::vector<float> scanAt(const std::vector<WallRef> &walls, const Pose2D &T_station_base,
                          double sigma_m, std::mt19937 *rng)
{
    return simulateScan(walls, compose(T_station_base, kLaserInBase), kAngleMin, kAngleInc,
                        kBeams, kRangeMax, sigma_m, rng);
}

}  // namespace

int main()
{
    const WallLocalizerParams params;  // 전 기본값

    // 1) 무잡음 — OK, 오차 < 1 mm · 0.05°.
    {
        WallLocalizer loc(kStationWalls, params, kLaserInBase, kInitialGuess);
        const Pose2D truth{0.5, 0.1, 2.0 * M_PI / 180.0};
        const LocalizeResult r =
            loc.update(scanAt(kStationWalls, truth, 0.0, nullptr), kAngleMin, kAngleInc);
        CHECK(r.status == Status::OK);
        CHECK_NEAR(r.T_station_base.x_m, truth.x_m, 1e-3);
        CHECK_NEAR(r.T_station_base.y_m, truth.y_m, 1e-3);
        CHECK_NEAR(r.T_station_base.yaw_rad, truth.yaw_rad, 0.05 * M_PI / 180.0);
        for (const auto &f : r.wall_fits)
        {
            CHECK(f.matched);
        }
    }

    // 2) 잡음 σ=10 mm (시드 고정) — LOST 아님, 오차 < 5 mm · 0.3°.
    {
        WallLocalizer loc(kStationWalls, params, kLaserInBase, kInitialGuess);
        const Pose2D truth{0.5, 0.1, 2.0 * M_PI / 180.0};
        std::mt19937 rng(42);
        const LocalizeResult r =
            loc.update(scanAt(kStationWalls, truth, 0.010, &rng), kAngleMin, kAngleInc);
        CHECK(r.status != Status::LOST);
        CHECK_NEAR(r.T_station_base.x_m, truth.x_m, 5e-3);
        CHECK_NEAR(r.T_station_base.y_m, truth.y_m, 5e-3);
        CHECK_NEAR(r.T_station_base.yaw_rad, truth.yaw_rad, 0.3 * M_PI / 180.0);
    }

    // 3) 좌측 벽 가림 — DEGRADED 로 강등되지만 자세는 유지 (전방+우측이 3자유도 구속).
    {
        WallLocalizer loc(kStationWalls, params, kLaserInBase, kInitialGuess);
        const Pose2D truth{0.5, 0.1, 2.0 * M_PI / 180.0};
        const std::vector<WallRef> visible = {kStationWalls[0], kStationWalls[2]};
        const LocalizeResult r =
            loc.update(scanAt(visible, truth, 0.0, nullptr), kAngleMin, kAngleInc);
        CHECK(r.status == Status::DEGRADED);
        CHECK_NEAR(r.T_station_base.x_m, truth.x_m, 1e-3);
        CHECK_NEAR(r.T_station_base.y_m, truth.y_m, 1e-3);
    }

    // 4) 전방 벽만 보임 — 대응 부족으로 LOST, 자세 출력 없음.
    {
        WallLocalizer loc(kStationWalls, params, kLaserInBase, kInitialGuess);
        const Pose2D truth{0.5, 0.1, 0.0};
        const std::vector<WallRef> visible = {kStationWalls[0]};
        const LocalizeResult r =
            loc.update(scanAt(visible, truth, 0.0, nullptr), kAngleMin, kAngleInc);
        CHECK(r.status == Status::LOST);
        CHECK(r.reason == "insufficient_matches");
    }

    // 5) 평행 벽만 기준으로 구성 — 가관측성 검사로 LOST (쓰레기 자세 금지).
    {
        const std::vector<WallRef> parallel_only = {kStationWalls[1], kStationWalls[2]};
        WallLocalizer loc(parallel_only, params, kLaserInBase, kInitialGuess);
        const Pose2D truth{0.5, 0.0, 0.0};
        const LocalizeResult r =
            loc.update(scanAt(kStationWalls, truth, 0.0, nullptr), kAngleMin, kAngleInc);
        CHECK(r.status == Status::LOST);
        CHECK(r.reason == "degenerate_normals");
    }

    // 6) 점프 게이트 + 연속 기각 복귀.
    {
        WallLocalizer loc(kStationWalls, params, kLaserInBase, kInitialGuess);
        const Pose2D pose_a{0.5, 0.1, 2.0 * M_PI / 180.0};
        CHECK(loc.update(scanAt(kStationWalls, pose_a, 0.0, nullptr), kAngleMin, kAngleInc)
                  .status == Status::OK);
        // 한 스캔 만에 0.19 m 이동한 것으로 보이는 해 — 오대응 신호로 기각돼야 한다.
        const Pose2D pose_b{0.65, -0.02, 2.0 * M_PI / 180.0};
        const LocalizeResult rj =
            loc.update(scanAt(kStationWalls, pose_b, 0.0, nullptr), kAngleMin, kAngleInc);
        CHECK(rj.status == Status::LOST);
        CHECK(rj.reason == "jump_gate");
        // 같은 장면이 계속되면 max_consecutive_rejects 초과 후 추적을 버리고 재수렴한다.
        LocalizeResult rr;
        for (int i = 0; i < params.quality.max_consecutive_rejects + 2; ++i)
        {
            rr = loc.update(scanAt(kStationWalls, pose_b, 0.0, nullptr), kAngleMin, kAngleInc);
        }
        CHECK(rr.status == Status::OK);
        CHECK_NEAR(rr.T_station_base.x_m, pose_b.x_m, 1e-3);
        CHECK_NEAR(rr.T_station_base.y_m, pose_b.y_m, 1e-3);
    }

    // 7) 추종 시나리오 — 스테이션으로 전진하는 연속 자세를 연속 추적.
    {
        WallLocalizer loc(kStationWalls, params, kLaserInBase, kInitialGuess);
        std::mt19937 rng(7);
        for (int k = 0; k <= 20; ++k)
        {
            const Pose2D truth{0.4 + 0.02 * k, 0.1 - 0.004 * k, 0.001 * k};
            const LocalizeResult r =
                loc.update(scanAt(kStationWalls, truth, 0.005, &rng), kAngleMin, kAngleInc);
            CHECK(r.status != Status::LOST);
            CHECK_NEAR(r.T_station_base.x_m, truth.x_m, 5e-3);
            CHECK_NEAR(r.T_station_base.y_m, truth.y_m, 5e-3);
        }
    }

    // 8) 고잡음 σ=25mm — 토막화 면역: 회랑 재적합이 벽 점수를 회복해 정밀도를 지킨다.
    //    (거리 임계는 3σ 규칙대로 조정 — 임계 < 1.5σ 의 극한 붕괴는 본 수정의 범위 밖)
    {
        WallLocalizerParams hp;
        hp.extract.split_dist_m = 0.075;
        hp.extract.merge_dist_m = 0.075;
        hp.match.refit_corridor_m = 0.075;
        hp.quality.max_dist_residual_m = 0.075;
        WallLocalizer loc(kStationWalls, hp, kLaserInBase, kInitialGuess);
        const Pose2D truth{0.5, 0.1, 2.0 * M_PI / 180.0};
        std::mt19937 rng(11);
        int n_fix = 0;
        double worst = 0.0;
        int min_front_points = 1 << 30;
        for (int k = 0; k < 40; ++k)
        {
            const LocalizeResult r =
                loc.update(scanAt(kStationWalls, truth, 0.025, &rng), kAngleMin, kAngleInc);
            if (r.status == Status::LOST)
            {
                continue;
            }
            ++n_fix;
            worst = std::max(worst, std::hypot(r.T_station_base.x_m - truth.x_m,
                                               r.T_station_base.y_m - truth.y_m));
            for (const auto &f : r.wall_fits)
            {
                if (f.name == "front" && f.matched)
                {
                    min_front_points = std::min(min_front_points, f.seg_points);
                }
            }
        }
        CHECK(n_fix >= 36);              // 해율 ≥ 90%
        CHECK(worst < 0.012);            // 단발 최악 < 12mm (종전 σ=20 에서 49mm)
        CHECK(min_front_points >= 140);  // 재적합이 전방 벽 점수를 토막과 무관하게 회복
    }

    std::printf("test_wall_localizer: PASS\n");
    return 0;
}
