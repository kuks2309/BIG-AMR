#include "mcl2d_core/skid_detector.hpp"

#include <cmath>

namespace mcl2d
{

LocReportState SkidDetector::update(double trans_odo, double dtheta_odo, double trans_state, double dtheta_state,
                                    bool stopped, double dt)
{
    if (skidding_)
    {
        // 복구 판정: 정지 상태로 recover_time 경과 → Normal 복귀 (Seer: elapsed > recoverTime*1000ms).
        if (stopped)
        {
            stopped_elapsed_ += dt;
            if (stopped_elapsed_ > params_.recover_time)
            {
                skidding_ = false;
                stopped_elapsed_ = 0.0;
            }
        }
        else
        {
            stopped_elapsed_ = 0.0;
        }
        return skidding_ ? LocReportState::Skidding : LocReportState::Normal;
    }

    // 병진 불일치 (Seer skidDetect.cpp:167,180): 큰 이동일 때만 게이트.  comment-check: ignore
    const double r = params_.skid_mismatch_ratio;
    const bool big_move = (trans_odo > params_.skid_check_distance) || (trans_state > params_.skid_check_distance);
    const bool trans_mismatch = big_move && ((trans_state > r * trans_odo) || (trans_odo > r * trans_state));

    // 회전 불일치: 휠↔레이저 각 이동량 차가 임계 초과.
    const double dtheta_diff = std::fabs(std::fabs(dtheta_odo) - std::fabs(dtheta_state));
    const bool rot_mismatch = dtheta_diff > params_.skid_check_angle;

    if (trans_mismatch || rot_mismatch)
    {
        skidding_ = true;
        stopped_elapsed_ = 0.0;
        return LocReportState::Skidding;
    }
    return LocReportState::Normal;
}

} // namespace mcl2d
