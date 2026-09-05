#include "slam_karto_core/seer_mapper_config.hpp"

#include <open_karto/Mapper.h>

namespace slam_karto_core
{

void applySeerParams(karto::Mapper *mapper, const SeerMapperParams &p)
{
    if (mapper == nullptr)
    {
        return;
    }

    // 노드 추가 게이트
    mapper->setParamMinimumTravelDistance(p.minimum_travel_distance);
    mapper->setParamMinimumTravelHeading(p.minimum_travel_heading);
    mapper->setParamMinimumTimeInterval(p.minimum_time_interval);

    // ★ Seer 튜닝 5개 — 거동 재현의 핵심
    mapper->setParamScanBufferSize(p.scan_buffer_size);
    mapper->setParamLoopSearchMaximumDistance(p.loop_search_maximum_distance);
    mapper->setParamLoopMatchMinimumResponseCoarse(p.loop_match_minimum_response_coarse);
    mapper->setParamLoopMatchMinimumResponseFine(p.loop_match_minimum_response_fine);
    mapper->setParamLoopSearchSpaceDimension(p.loop_search_space_dimension);

    // 나머지 — 상류 기본값과 같아도 전량 명시 설정한다(벤더링 판본 드리프트 차단)
    mapper->setParamScanBufferMaximumScanDistance(p.scan_buffer_maximum_scan_distance);
    mapper->setParamLoopMatchMinimumChainSize(p.loop_match_minimum_chain_size);
    mapper->setParamLoopMatchMaximumVarianceCoarse(p.loop_match_maximum_variance_coarse);
    mapper->setParamCorrelationSearchSpaceDimension(p.correlation_search_space_dimension);
    mapper->setParamCorrelationSearchSpaceResolution(p.correlation_search_space_resolution);
    mapper->setParamCorrelationSearchSpaceSmearDeviation(p.correlation_search_space_smear_deviation);
    mapper->setParamLinkMatchMinimumResponseFine(p.link_match_minimum_response_fine);
    mapper->setParamLinkScanMaximumDistance(p.link_scan_maximum_distance);
    mapper->setParamDistanceVariancePenalty(p.distance_variance_penalty);
    mapper->setParamAngleVariancePenalty(p.angle_variance_penalty);
    mapper->setParamCoarseSearchAngleOffset(p.coarse_search_angle_offset);
    mapper->setParamCoarseAngleResolution(p.coarse_angle_resolution);
    mapper->setParamFineSearchAngleOffset(p.fine_search_angle_offset);
    mapper->setParamLoopSearchSpaceResolution(p.loop_search_space_resolution);
    mapper->setParamLoopSearchSpaceSmearDeviation(p.loop_search_space_smear_deviation);
    mapper->setParamMinimumAnglePenalty(p.minimum_angle_penalty);
    mapper->setParamMinimumDistancePenalty(p.minimum_distance_penalty);
    mapper->setParamDoLoopClosing(p.do_loop_closing);
    mapper->setParamUseScanMatching(p.use_scan_matching);
    mapper->setParamUseScanBarycenter(p.use_scan_barycenter);
    mapper->setParamUseResponseExpansion(p.use_response_expansion);
}

} // namespace slam_karto_core
