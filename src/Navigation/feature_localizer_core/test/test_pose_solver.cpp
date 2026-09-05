// pose_solver + 기하 유틸 단위검증 — 정확 대응 왕복 복원·퇴화 거부·변환 항등.

#include <cmath>
#include <cstdio>

#include "sim_scan.hpp"
#include "feature_localizer_core/pose_solver.hpp"

using namespace feature_localizer_core;

namespace
{

// 참 자세로부터 정확한 측정 직선을 만들어 대응 쌍을 구성한다.
FeatureMatch exactMatch(const OrientedWall &w, const Pose2D &T_station_lidar, int num_points)
{
    const double c = std::cos(T_station_lidar.yaw_rad);
    const double s = std::sin(T_station_lidar.yaw_rad);
    FeatureMatch m;
    m.feature_idx = 0;
    m.ref_line_station = w.line_station;
    m.seg.line.nx = c * w.line_station.nx + s * w.line_station.ny;
    m.seg.line.ny = -s * w.line_station.nx + c * w.line_station.ny;
    m.seg.line.d_m = w.line_station.d_m - (w.line_station.nx * T_station_lidar.x_m +
                                           w.line_station.ny * T_station_lidar.y_m);
    m.seg.num_points = num_points;
    m.seg.length_m = 1.0;
    return m;
}

}  // namespace

int main()
{
    SolveParams sp;
    const Point2D robot_guess{0.5, 0.0};
    const OrientedWall front = orientWall({"front", {2.0, -1.5}, {2.0, 1.5}}, robot_guess);
    const OrientedWall left = orientWall({"left", {0.0, 1.5}, {2.0, 1.5}}, robot_guess);
    const OrientedWall right = orientWall({"right", {0.0, -1.5}, {2.0, -1.5}}, robot_guess);

    // 정향 규칙 확인 — 로봇 쪽 예측 거리가 양수가 되는 방향.
    CHECK_NEAR(front.line_station.nx, 1.0, 1e-12);
    CHECK_NEAR(front.line_station.d_m, 2.0, 1e-12);
    CHECK_NEAR(left.line_station.ny, 1.0, 1e-12);
    CHECK_NEAR(right.line_station.ny, -1.0, 1e-12);
    CHECK_NEAR(right.line_station.d_m, 1.5, 1e-12);

    // 1) 벽 3면 정확 대응 → 참 자세 복원 (해석해 수준 오차).
    {
        const Pose2D truth{0.8, 0.1, 3.0 * M_PI / 180.0};
        const std::vector<FeatureMatch> matches = {exactMatch(front, truth, 120),
                                                exactMatch(left, truth, 80),
                                                exactMatch(right, truth, 90)};
        const SolveResult r = solvePose(matches, sp);
        CHECK(r.ok);
        CHECK_NEAR(r.T_station_lidar.x_m, truth.x_m, 1e-9);
        CHECK_NEAR(r.T_station_lidar.y_m, truth.y_m, 1e-9);
        CHECK_NEAR(r.T_station_lidar.yaw_rad, truth.yaw_rad, 1e-9);
    }

    // 2) 비평행 2면으로도 해석 가능.
    {
        const Pose2D truth{0.6, -0.05, -2.0 * M_PI / 180.0};
        const std::vector<FeatureMatch> matches = {exactMatch(front, truth, 100),
                                                exactMatch(right, truth, 100)};
        const SolveResult r = solvePose(matches, sp);
        CHECK(r.ok);
        CHECK_NEAR(r.T_station_lidar.x_m, truth.x_m, 1e-9);
        CHECK_NEAR(r.T_station_lidar.y_m, truth.y_m, 1e-9);
    }

    // 3) 평행 벽만(좌·우) → 접선 방향 미관측, 해를 내지 않는다.
    {
        const Pose2D truth{0.6, 0.0, 0.0};
        const std::vector<FeatureMatch> matches = {exactMatch(left, truth, 100),
                                                exactMatch(right, truth, 100)};
        const SolveResult r = solvePose(matches, sp);
        CHECK(!r.ok);
        CHECK(r.reason == "degenerate_normals");
    }

    // 4) 대응 1건 → 미결정.
    {
        const Pose2D truth{0.6, 0.0, 0.0};
        const std::vector<FeatureMatch> matches = {exactMatch(front, truth, 100)};
        const SolveResult r = solvePose(matches, sp);
        CHECK(!r.ok);
        CHECK(r.reason == "insufficient_matches");
    }

    // 5) 변환 왕복 항등 (numeric 도메인 §5 — 왕복 변환 == 항등).
    {
        const Pose2D T{1.234, -0.567, 2.345};
        const Pose2D I = compose(T, inverse(T));
        CHECK_NEAR(I.x_m, 0.0, 1e-12);
        CHECK_NEAR(I.y_m, 0.0, 1e-12);
        CHECK_NEAR(I.yaw_rad, 0.0, 1e-12);
        const Point2D q{0.3, -0.9};
        const Point2D back = transformPoint(inverse(T), transformPoint(T, q));
        CHECK_NEAR(back.x_m, q.x_m, 1e-12);
        CHECK_NEAR(back.y_m, q.y_m, 1e-12);
    }

    // 6) normalizeAngle 반개구간 [-π, π) — 경계 입력은 ±π 근방(sin/cos 반올림 한계)이면 된다.
    {
        const double a = normalizeAngle(3.0 * M_PI);
        CHECK(a >= -M_PI && a < M_PI);
        CHECK(std::fabs(std::fabs(a) - M_PI) < 1e-9);
        CHECK(normalizeAngle(M_PI) < M_PI);
        CHECK_NEAR(normalizeAngle(-M_PI), -M_PI, 1e-9);
        CHECK_NEAR(normalizeAngle(5.0), 5.0 - 2.0 * M_PI, 1e-12);
    }

    std::printf("test_pose_solver: PASS\n");
    return 0;
}
