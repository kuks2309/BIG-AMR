#include "mcl2d_core/skid_detector.hpp"

#include <cmath>

namespace mcl2d
{

LocReportState SkidDetector::update(double trans_odo, double dtheta_odo, double trans_state, double dtheta_state,
                                    bool stopped, double dt)
{
    if (skidding_)
    {
        // 복구는 **정지 상태 누적**으로만 한다 — 미끄러지는 중에는 어떤 값도 신뢰할 수 없으므로
        //   움직이는 동안에는 판정을 재개하지 않고, 멈춰 있는 시간이 recover_time 을 넘겨야 푼다.
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

    // 병진 불일치는 **큰 이동일 때만** 본다 — 미세 이동에서는 두 값의 비율이 잡음으로 쉽게 튄다.  comment-check: ignore
    const double r = params_.skid_mismatch_ratio;
    const bool big_move = (trans_odo > params_.skid_check_distance) || (trans_state > params_.skid_check_distance);
    const bool trans_mismatch = big_move && ((trans_state > r * trans_odo) || (trans_odo > r * trans_state));

    // 회전은 비율이 아니라 차로 본다. 부호를 버리고 크기만 비교하므로 회전 **방향** 반전은 잡지 못한다.
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
