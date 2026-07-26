#ifndef TRNAV_MOTION_QD__QD_WHEEL_SET_PACKER_HPP_
#define TRNAV_MOTION_QD__QD_WHEEL_SET_PACKER_HPP_

#include "trnav_motion_core/robot_geometry.hpp"
#include "trnav_msgs/msg/wheel_set_array.hpp"

namespace trnav::motion::qd
{

// QD-diagonal platform packer: converts legacy (vel_f, ang_f, vel_r, ang_r) tuple
// into trnav_msgs/WheelSetArray for QD_DIAGONAL platform.
// wheels[0] = W1 (전-좌), wheels[1] = W2 (후-우).
//
// Note: For non-QD platforms (DD, FWS, Ackermann) a separate packer lives in
// trnav_motion_dd / future packages — this is intentionally QD-only after the
// 2026-05-21 QD/DD layer separation (ADR-012).
class QdWheelSetPacker
{
  public:
    explicit QdWheelSetPacker(const trnav_motion_core::RobotGeometry &geom);

    trnav_msgs::msg::WheelSetArray pack(double velocity_front, double angle_front, double velocity_rear,
                                        double angle_rear) const;

    const trnav_motion_core::RobotGeometry &geometry() const
    {
        return geom_;
    }

  private:
    trnav_motion_core::RobotGeometry geom_;
};

} // namespace trnav::motion::qd

#endif // TRNAV_MOTION_QD__QD_WHEEL_SET_PACKER_HPP_
