// 관측모델: 빔별 맵좌표 변환 → 우도장 PDF 룩업·합 → weight = pdf_sum / valid_beam / 255.
// Seer 실측(getPostProbBase): movzbl PDF + /255 정규화 (OpenCL 커널과 동일). 근거 doc 6.5절 ③.
// 다중 라이다(Roll_A084 전+후) 융합: 전 라이다의 빔을 합산해 단일 우도로 정규화(Seer 듀얼 라이다 동일).
#ifndef MCL2D_CORE_OBSERVATION_MODEL_HPP
#define MCL2D_CORE_OBSERVATION_MODEL_HPP

#include <vector>

#include "mcl2d_core/likelihood_grid.hpp"
#include "mcl2d_core/types.hpp"

namespace mcl2d
{

// 단일 라이다 우도(0~1).
double computeLikelihood(const Pose2D &pose, const LaserScan &scan, const LaserMount &mount, const LikelihoodGrid &grid,
                         const Mcl2dParams &params);

// 다중 라이다 융합 우도(0~1): 전 라이다 빔을 합산 후 valid_beam 으로 정규화.
// scans[i] 는 mounts[i] 장착. 크기 불일치 시 min(size) 만큼만 사용.
double computeLikelihoodMulti(const Pose2D &pose, const std::vector<LaserScan> &scans,
                              const std::vector<LaserMount> &mounts, const LikelihoodGrid &grid,
                              const Mcl2dParams &params);

} // namespace mcl2d

#endif // MCL2D_CORE_OBSERVATION_MODEL_HPP
