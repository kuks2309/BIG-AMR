#include "trnav_motion_qd/qd_wheel_set_packer.hpp"

namespace trnav::motion::qd
{

QdWheelSetPacker::QdWheelSetPacker(const trnav_motion_core::RobotGeometry &geom) : geom_(geom)
{
}

trnav_msgs::msg::WheelSetArray QdWheelSetPacker::pack(double velocity_front, double angle_front,
                                                     double velocity_rear, double angle_rear) const
{
    trnav_msgs::msg::WheelSetArray msg;

    switch (geom_.platform)
    {
    case trnav_motion_core::Platform::QD_DIAGONAL: {
        msg.wheels.resize(2);
        // wheels[0] = W1 (전-좌)
        msg.wheels[0].velocity = velocity_front;
        msg.wheels[0].steering = angle_front;
        // wheels[1] = W2 (후-우)
        msg.wheels[1].velocity = velocity_rear;
        msg.wheels[1].steering = angle_rear;
        break;
    }
    case trnav_motion_core::Platform::DD:
    case trnav_motion_core::Platform::FWS_INDEPENDENT:
    case trnav_motion_core::Platform::ACKERMANN:
        // Non-QD platforms must use sibling packers (trnav_motion_dd, etc.).
        // After ADR-012 (2026-05-21) QD/DD layer separation, mixing platforms
        // in one packer is rejected as an architectural violation. We fall
        // through to QD packing to avoid silent empty output if config is
        // misconfigured for this binary; the caller should construct with
        // QD_DIAGONAL geometry only.
        msg.wheels.resize(2);
        msg.wheels[0].velocity = velocity_front;
        msg.wheels[0].steering = angle_front;
        msg.wheels[1].velocity = velocity_rear;
        msg.wheels[1].steering = angle_rear;
        break;
    }

    return msg;
}

} // namespace trnav::motion::qd
