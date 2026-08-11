#ifndef TRNAV_2WS_MOTION__QD_WHEEL_SET_PACKER_HPP_
#define TRNAV_2WS_MOTION__QD_WHEEL_SET_PACKER_HPP_

#include "trnav_2ws_core/robot_geometry.hpp"
#include "trnav_msgs/msg/wheel_set_array.hpp"

namespace trnav::motion::two_ws
{

// QD-diagonal platform packer: converts legacy (vel_f, ang_f, vel_r, ang_r) tuple
// into trnav_msgs/WheelSetArray for QD_DIAGONAL platform.
// wheels[0] = W1 (앞), wheels[1] = W2 (뒤).
//
// Note: For non-QD platforms (DD, FWS, Ackermann) a separate packer would live in
// trnav_motion_dd / future packages — neither is present in this repository. This is
// intentionally QD-only after the 2026-05-21 QD/DD layer separation (ADR-012; that
// decision is recorded upstream, its in-repo trace is
// trnav_2ws_core/docs/amr_motion_core_code_updates.md).
class TwoWsWheelSetPacker
{
  public:
    explicit TwoWsWheelSetPacker(const trnav_2ws_core::RobotGeometry &geom);

    trnav_msgs::msg::WheelSetArray pack(double velocity_front, double angle_front, double velocity_rear,
                                        double angle_rear) const;

    const trnav_2ws_core::RobotGeometry &geometry() const
    {
        return geom_;
    }

  private:
    trnav_2ws_core::RobotGeometry geom_;
};

} // namespace trnav::motion::two_ws

#endif // TRNAV_2WS_MOTION__QD_WHEEL_SET_PACKER_HPP_
