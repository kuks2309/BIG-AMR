#ifndef WALL_LOCALIZER_CORE__LINE_EXTRACTOR_HPP_
#define WALL_LOCALIZER_CORE__LINE_EXTRACTOR_HPP_

#include <cstddef>
#include <vector>

#include "feature_localizer_core/types.hpp"

namespace feature_localizer_core
{

// LaserScan 원시 거리 배열 → 게이트(거리·섹터) 통과 2D 점군 (라이다 프레임).
// ranges_m[i] 의 빔각 = angle_min_rad + i·angle_inc_rad. 비유한(NaN/Inf) 표본은 폐기.
std::vector<Point2D> scanToPoints(const std::vector<float> &ranges_m, double angle_min_rad,
                                  double angle_inc_rad, const ExtractParams &p);

// 점군(스캔 각도순 정렬 가정) → 직선 선분 목록.
// 인접 간격 클러스터링 → split-and-merge(점-현 수직거리 분할, 공선 병합) →
// 총최소자승 적합 → 점수·길이 게이트. 결정론적 — 난수 없음.
// 반환 선분의 법선은 라이다 원점 정향(types.hpp 서두 규칙).
std::vector<ExtractedSegment> extractSegments(const std::vector<Point2D> &points_lidar,
                                              const ExtractParams &p);

// [i0, i1] 구간(양끝 포함, i0 < i1) 점들의 총최소자승(주성분) 직선 적합.
// 법선은 원점 정향(d ≥ 0). rms_m 이 널이 아니면 점-직선 수직거리 RMS 를 채운다.
LineNormalForm fitLineTLS(const std::vector<Point2D> &points, std::size_t i0, std::size_t i1,
                          double *rms_m);

}  // namespace feature_localizer_core

#endif  // WALL_LOCALIZER_CORE__LINE_EXTRACTOR_HPP_
