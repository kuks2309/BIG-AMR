// 슬립(skid) 감지 — 원본 CheckWheelSkid 재구현.
// 휠 오도 이동량과 위치추정(레이저) 이동량이 어긋나면 바퀴가 미끄러진 것으로 본다.
//
// ⚠ 전제: /odom 이 **휠 오도** 여야 의미가 있다. 레이저 정합 오도(icp_odometry)를 /odom 으로 쓰면
//   레이저↔레이저 비교가 되어 두 값이 같은 원인으로 함께 틀리므로 미끄러짐을 검출하지 못한다.
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

    // 한 주기 갱신.
    //   trans_odo [m] · dtheta_odo [rad]     — 휠 오도가 말하는 이동량
    //   trans_state [m] · dtheta_state [rad] — 위치추정 자세가 말하는 이동량
    //   stopped — 정지 여부(복구 판정에만 쓰인다) · dt [s] — 직전 갱신 이후 경과
    // 반환 = 이번 주기 보고 상태. 한번 Skidding 이 되면 정지 상태로 recover_time 이 지나야 풀린다.
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
