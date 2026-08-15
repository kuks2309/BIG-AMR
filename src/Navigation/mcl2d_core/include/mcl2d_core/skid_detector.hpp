// 슬립(skid) 감지 — Seer CheckWheelSkid / skidDetect.cpp 재구현.
// 휠 오도(odometry) 이동량과 위치추정(레이저) 이동량의 불일치로 미끄러짐 판정.
// 근거: References/seer/libMCLoc/2026-06-24-localization-deep-dive.md §6.6 ③ (confirmed 2/2).
#ifndef MCL2D_CORE_SKID_DETECTOR_HPP
#define MCL2D_CORE_SKID_DETECTOR_HPP

#include "mcl2d_core/types.hpp"

namespace mcl2d
{

class SkidDetector
{
  public:
    explicit SkidDetector(const Mcl2dParams &params) : params_(params)
    {
    }

    // 한 주기 갱신. d_odo = 휠오도 이동(병진 m, 회전 rad), d_state = 위치추정 이동.
    //  stopped = 로봇 정지 여부, dt = 경과 시간(s). 반환 = 이번 주기 보고 상태.
    LocReportState update(double trans_odo, double dtheta_odo, double trans_state, double dtheta_state, bool stopped,
                          double dt);

    bool skidding() const
    {
        return skidding_;
    }
    void reset()
    {
        skidding_ = false;
        stopped_elapsed_ = 0.0;
    }

  private:
    const Mcl2dParams &params_;
    bool skidding_ = false;
    double stopped_elapsed_ = 0.0; // 정지 후 누적 경과(s) — 복구 판정용
};

} // namespace mcl2d

#endif // MCL2D_CORE_SKID_DETECTOR_HPP
