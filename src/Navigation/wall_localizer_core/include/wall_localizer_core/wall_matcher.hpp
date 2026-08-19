#ifndef WALL_LOCALIZER_CORE__WALL_MATCHER_HPP_
#define WALL_LOCALIZER_CORE__WALL_MATCHER_HPP_

#include <cstddef>
#include <vector>

#include "wall_localizer_core/types.hpp"

namespace wall_localizer_core
{

// 정향 고정된 기준 벽. line_station 의 법선은 로봇 기준 위치 쪽에서 본 예측 거리가
// 양수가 되도록 1회 고정된다 — 로봇이 스테이션 작업 중 벽 반대편으로 넘어가지 않는
// 전제(스테이션 국소 운용)에서 π 모호성이 사라진다.
struct OrientedWall
{
    WallRef ref;
    LineNormalForm line_station;
};

// 라이다 프레임으로 투영된 기준 벽 (대응 게이트의 기준).
struct PredictedWall
{
    std::size_t wall_idx{0};
    LineNormalForm line;  // 라이다 프레임. side_valid 일 때 d ≥ 0
    Point2D p1;           // 라이다 프레임 끝점
    Point2D p2;
    bool side_valid{true};  // false = 로봇이 정향 당시의 반대편(대응 제외)
};

// 기준 벽 ↔ 추출 선분 대응 쌍.
struct WallMatch
{
    std::size_t wall_idx{0};
    LineNormalForm ref_line_station;  // 정향 고정본 (스테이션 프레임)
    ExtractedSegment seg;             // 라이다 프레임
};

// 벽 끝점 → 법선형. 법선은 robot_pos_station(스테이션 프레임) 쪽 거리가 양수가 되도록 정향.
OrientedWall orientWall(const WallRef &w, const Point2D &robot_pos_station);

// 기준 벽들을 라이다 프레임으로 투영. T_station_lidar = 스테이션 내 라이다 자세.
std::vector<PredictedWall> predictWallsInLidar(const std::vector<OrientedWall> &walls,
                                               const Pose2D &T_station_lidar);

// 각도차·수직거리차·구간 겹침 게이트를 모두 통과한 쌍을 점수(작을수록 좋음)순
// 탐욕으로 1:1 배정한다. 결정론적. walls 는 predicted 와 같은 인덱스의 정향 벽 목록
// (반환 매치의 ref_line_station 을 채우는 데 쓴다).
std::vector<WallMatch> matchWalls(const std::vector<PredictedWall> &predicted,
                                  const std::vector<ExtractedSegment> &segments,
                                  const std::vector<OrientedWall> &walls, const MatchParams &p);

}  // namespace wall_localizer_core

#endif  // WALL_LOCALIZER_CORE__WALL_MATCHER_HPP_
