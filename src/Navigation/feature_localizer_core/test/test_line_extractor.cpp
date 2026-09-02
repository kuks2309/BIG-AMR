// line_extractor 단위검증 — 합성 스캔에서 직선 추출의 개수·법선·거리·게이트 동작.

#include <cmath>
#include <cstdio>

#include "sim_scan.hpp"
#include "feature_localizer_core/line_extractor.hpp"

using namespace feature_localizer_core;
using feature_localizer_test::simulateScan;

namespace
{

constexpr int kBeams = 720;
constexpr double kAngleMin = -M_PI;
constexpr double kAngleInc = 2.0 * M_PI / kBeams;

std::vector<ExtractedSegment> extractFromWalls(const std::vector<FeatureRef> &features,
                                               const ExtractParams &p)
{
    const Pose2D lidar_at_origin{0.0, 0.0, 0.0};
    const std::vector<float> scan =
        simulateScan(features, lidar_at_origin, kAngleMin, kAngleInc, kBeams, 10.0, 0.0, nullptr);
    return extractSegments(scanToPoints(scan, kAngleMin, kAngleInc, p), p);
}

}  // namespace

int main()
{
    ExtractParams p;

    // 1) 직교 2벽 → 선분 2개, 법선·거리 정확.
    {
        const std::vector<FeatureRef> features = {{"front", {1.0, -1.0}, {1.0, 1.0}},
                                            {"left", {-1.0, 1.0}, {1.0, 1.0}}};
        const auto segs = extractFromWalls(features, p);
        CHECK(segs.size() == 2);
        int n_front = 0;
        int n_left = 0;
        for (const auto &s : segs)
        {
            CHECK(s.rms_m < 1e-6);  // 무잡음 — 적합 잔차 0
            if (std::fabs(s.line.nx) > 0.9)
            {
                ++n_front;
                CHECK_NEAR(s.line.nx, 1.0, 1e-6);
                CHECK_NEAR(s.line.d_m, 1.0, 1e-6);
            }
            else
            {
                ++n_left;
                CHECK_NEAR(s.line.ny, 1.0, 1e-6);
                CHECK_NEAR(s.line.d_m, 1.0, 1e-6);
            }
        }
        CHECK(n_front == 1 && n_left == 1);
    }

    // 2) 최소 길이 게이트 — 0.3 m 벽은 min_length_m(0.4) 미만이라 버려진다.
    {
        const std::vector<FeatureRef> features = {{"short", {1.0, -0.15}, {1.0, 0.15}}};
        const auto segs = extractFromWalls(features, p);
        CHECK(segs.empty());
    }

    // 3) 간격 분리 — 동일 직선 위 두 토막(간격 0.6 m > max_point_gap_m)은 병합되지 않는다.
    {
        const std::vector<FeatureRef> features = {{"a", {1.0, -1.0}, {1.0, -0.3}},
                                            {"b", {1.0, 0.3}, {1.0, 1.0}}};
        const auto segs = extractFromWalls(features, p);
        CHECK(segs.size() == 2);
    }

    // 4) 잡음 하 단일 벽 — 토막나지 않고 한 선분으로 남는다 (병합 경로 검증).
    {
        const std::vector<FeatureRef> features = {{"front", {2.0, -1.5}, {2.0, 1.5}}};
        std::mt19937 rng(7);
        const std::vector<float> scan = simulateScan(features, {0.0, 0.0, 0.0}, kAngleMin,
                                                     kAngleInc, kBeams, 10.0, 0.005, &rng);
        const auto segs = extractSegments(scanToPoints(scan, kAngleMin, kAngleInc, p), p);
        CHECK(segs.size() == 1);
        CHECK_NEAR(segs[0].line.nx, 1.0, 0.01);
        CHECK_NEAR(segs[0].line.d_m, 2.0, 0.01);
    }

    std::printf("test_line_extractor: PASS\n");
    return 0;
}
