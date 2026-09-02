#ifndef WALL_LOCALIZER_CORE__POSE_SOLVER_HPP_
#define WALL_LOCALIZER_CORE__POSE_SOLVER_HPP_

#include <string>
#include <vector>

#include "feature_localizer_core/feature_matcher.hpp"

namespace feature_localizer_core
{

struct SolveResult
{
    Pose2D T_station_lidar;   // ok 일 때만 유효
    bool ok{false};
    std::string reason;       // 실패 사유 코드: insufficient_matches | degenerate_normals
    double normal_spread{0.0};  // Σw·nnᵀ/Σw 의 최소고유값 (가관측성 지표, [0, 0.5])
};

// 대응 쌍으로 SE(2) 를 푼다 — 가중치는 선분 표본 수.
// yaw = 각도 잔차의 가중 원형 평균, 병진 = n_station·t = d_station − d_lidar 의
// 2×2 가중 정규방정식. 대응 < 2 또는 법선 방향 다양성 부족이면 해를 내지 않는다.
SolveResult solvePose(const std::vector<FeatureMatch> &matches, const SolveParams &p);

}  // namespace feature_localizer_core

#endif  // WALL_LOCALIZER_CORE__POSE_SOLVER_HPP_
