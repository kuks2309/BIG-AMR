#ifndef WALL_LOCALIZER_CORE__WALL_MATCHER_HPP_
#define WALL_LOCALIZER_CORE__WALL_MATCHER_HPP_

#include <cstddef>
#include <vector>

#include "feature_localizer_core/types.hpp"

namespace feature_localizer_core
{

// 정향 고정된 기준 특징면. line_station 의 법선은 로봇 기준 위치 쪽에서 본 예측 거리가
// 양수가 되도록 1회 고정된다 — 로봇이 스테이션 작업 중 벽 반대편으로 넘어가지 않는
// 전제(스테이션 국소 운용)에서 π 모호성이 사라진다.
struct OrientedWall
{
    FeatureRef ref;
    LineNormalForm line_station;
};

// 라이다 프레임으로 투영된 기준 특징면 (대응 게이트의 기준).
struct PredictedWall
{
    std::size_t feature_idx{0};
    LineNormalForm line;  // 라이다 프레임. side_valid 일 때 d ≥ 0
    Point2D p1;           // 라이다 프레임 끝점
    Point2D p2;
    bool side_valid{true};  // false = 로봇이 정향 당시의 반대편(대응 제외)
};

// 기준 특징면 ↔ 추출 선분 대응 쌍.
struct FeatureMatch
{
    std::size_t feature_idx{0};
    LineNormalForm ref_line_station;  // 정향 고정본 (스테이션 프레임)
    ExtractedSegment seg;             // 라이다 프레임
};

// 벽 끝점 → 법선형. 법선은 robot_pos_station(스테이션 프레임) 쪽 거리가 양수가 되도록 정향.
OrientedWall orientWall(const FeatureRef &w, const Point2D &robot_pos_station);

// 기준 특징면들을 라이다 프레임으로 투영. T_station_lidar = 스테이션 내 라이다 자세.
std::vector<PredictedWall> predictWallsInLidar(const std::vector<OrientedWall> &features,
                                               const Pose2D &T_station_lidar);

// 각도차·수직거리차·구간 겹침 게이트를 모두 통과한 쌍을 점수(작을수록 좋음)순
// 탐욕으로 1:1 배정한다. 결정론적. features 는 predicted 와 같은 인덱스의 정향 벽 목록
// (반환 매치의 ref_line_station 을 채우는 데 쓴다).
std::vector<FeatureMatch> matchWalls(const std::vector<PredictedWall> &predicted,
                                  const std::vector<ExtractedSegment> &segments,
                                  const std::vector<OrientedWall> &features, const MatchParams &p);

// 벽 하나에 귀속된 후보 선분 묶음 (1:N 대응 — 토막화 대비).
struct FeatureCandidateGroup
{
    std::size_t feature_idx{0};
    LineNormalForm ref_line_station;
    std::vector<std::size_t> seg_indices;
    double combined_overlap_ratio{0.0};  // 귀속 선분들의 구간 합집합 / 예측 벽 길이
    LineNormalForm seed_line;  // 점수 최대 귀속 선분의 직선 — 재적합 회랑의 초기 중심
    double s_lo{0.0};          // 귀속 선분들이 실제로 본 구간 (예측 벽 접선축 좌표)
    double s_hi{0.0};
};

// 게이트 통과 선분을 벽당 여러 개 귀속한다(선분은 최적 점수 벽 1곳에만). 벽은
// 구간 합집합 겹침비가 min_overlap_ratio 이상일 때만 채택. 결정론적.
std::vector<FeatureCandidateGroup> matchWallsMulti(const std::vector<PredictedWall> &predicted,
                                                const std::vector<ExtractedSegment> &segments,
                                                const std::vector<OrientedWall> &features,
                                                const MatchParams &p);

// 귀속 선분들이 본 구간(group.s_lo~s_hi ± margin) 안에서, 관측 시드선(group.seed_line)
// 중심 회랑(±corridor)의 원시 점 전체를 총최소자승 재적합해 그 벽의 측정으로 만든다 —
// 토막은 대응 근거, 측정은 점이 담당. 회랑 중심이 예측선이 아니라 시드선인 이유:
// 초기 추정 오차는 대응 게이트(수십 cm)까지 허용되는데 회랑 반폭은 수 cm 라, 예측선
// 기준으로는 벽 점이 회랑 밖에 있다. 1패스 적합 후 그 결과선으로 재중심화해 한 번 더
// 적합한다(시드 토막의 기울기 오차 제거). 점 부족이거나 결과가 예측과 gate_angle 이상
// 벌어지면 false.
bool refitWallFromPoints(const std::vector<Point2D> &points_lidar, const PredictedWall &pred,
                         const FeatureCandidateGroup &group, const MatchParams &p, int min_points,
                         double gate_angle_rad, ExtractedSegment *out);

}  // namespace feature_localizer_core

#endif  // WALL_LOCALIZER_CORE__WALL_MATCHER_HPP_
