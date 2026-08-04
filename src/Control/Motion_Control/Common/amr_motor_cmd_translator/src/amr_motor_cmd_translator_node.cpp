#include "amr_motor_cmd_translator/amr_motor_cmd_translator_node.hpp"
#include <cmath>

namespace amr_motor_cmd_translator
{

using trnav_msgs::msg::MotorCmd;
using trnav_msgs::msg::MotorCmdArray;
using trnav_msgs::msg::MotorStateArray;
using trnav_msgs::msg::WheelMotor;
using trnav_msgs::msg::WheelMotorState;
using trnav_msgs::msg::WheelSetArray;

MotorCmdTranslator::MotorCmdTranslator() : Node("amr_motor_cmd_translator")
{
    // Declare and get parameters
    this->declare_parameter<double>("wheel_radius_m", 0.08);
    this->declare_parameter<double>("gear_walk", 20.0);
    this->declare_parameter<double>("gear_steer", 265.5);
    this->declare_parameter<double>("pulses_per_rev", 65536.0);

    this->declare_parameter<int>("motor_id_walk_front", 1);
    this->declare_parameter<int>("motor_id_walk_rear", 2);
    this->declare_parameter<int>("motor_id_steer_front", 3);
    this->declare_parameter<int>("motor_id_steer_rear", 4);

    this->declare_parameter<int>("direction_walk_front", -1);
    this->declare_parameter<int>("direction_walk_rear", -1);
    this->declare_parameter<int>("direction_steer_front", -1);
    this->declare_parameter<int>("direction_steer_rear", -1);
    // 조향 영점 오프셋 (deg) — 엔코더 raw 0 일 때의 실제 물리 조향각. 0 = 보정 없음(기존 동작).
    // 실측: experiments/2026-07-13_steer_zero_calib (개루프 같은방향 leg, 캐스터 플립 배제)
    this->declare_parameter<double>("steer_offset_front_deg", 0.0);
    this->declare_parameter<double>("steer_offset_rear_deg", 0.0);

    this->declare_parameter<int>("steer_profile_velocity", 30000);

    this->declare_parameter<int>("wheel_index_front", 0);
    this->declare_parameter<int>("wheel_index_rear", 1);

    this->declare_parameter<bool>("publish_legacy_wheel_motor_state", true);
    this->declare_parameter<bool>("publish_legacy_wheel_motor_state_detailed", true);

    radius_ = this->get_parameter("wheel_radius_m").as_double();
    gear_walk_ = this->get_parameter("gear_walk").as_double();
    gear_steer_ = this->get_parameter("gear_steer").as_double();
    pulses_per_rev_ = this->get_parameter("pulses_per_rev").as_double();

    walk_front_id_ = this->get_parameter("motor_id_walk_front").as_int();
    walk_rear_id_ = this->get_parameter("motor_id_walk_rear").as_int();
    steer_front_id_ = this->get_parameter("motor_id_steer_front").as_int();
    steer_rear_id_ = this->get_parameter("motor_id_steer_rear").as_int();

    dir_walk_front_ = this->get_parameter("direction_walk_front").as_int();
    dir_walk_rear_ = this->get_parameter("direction_walk_rear").as_int();
    dir_steer_front_ = this->get_parameter("direction_steer_front").as_int();
    dir_steer_rear_ = this->get_parameter("direction_steer_rear").as_int();

    steer_offset_front_ =
        this->get_parameter("steer_offset_front_deg").as_double() * M_PI / 180.0;
    steer_offset_rear_ =
        this->get_parameter("steer_offset_rear_deg").as_double() * M_PI / 180.0;

    steer_profile_vel_ = static_cast<int32_t>(this->get_parameter("steer_profile_velocity").as_int());

    wheel_index_front_ = this->get_parameter("wheel_index_front").as_int();
    wheel_index_rear_ = this->get_parameter("wheel_index_rear").as_int();

    publish_legacy_wms_ = this->get_parameter("publish_legacy_wheel_motor_state").as_bool();
    publish_legacy_wms_detailed_ = this->get_parameter("publish_legacy_wheel_motor_state_detailed").as_bool();

    // QoS: RELIABLE, KeepLast(10), VOLATILE
    auto qos = rclcpp::QoS(rclcpp::KeepLast(10)).reliable().durability_volatile();

    // Publishers
    low_cmd_pub_ = this->create_publisher<MotorCmdArray>("/motor/low_cmd", qos);

    if (publish_legacy_wms_)
    {
        wheel_motor_state_pub_ = this->create_publisher<WheelMotor>("wheel_motor_state", qos);
    }
    if (publish_legacy_wms_detailed_)
    {
        wheel_motor_state_detailed_pub_ = this->create_publisher<WheelMotorState>("wheel_motor_state_detailed", qos);
    }

    // Subscribers
    wheel_cmd_sub_ = this->create_subscription<WheelSetArray>(
        "/motor/wheel_cmd", qos, std::bind(&MotorCmdTranslator::onWheelCmd, this, std::placeholders::_1));

    low_state_sub_ = this->create_subscription<MotorStateArray>(
        "/motor/low_state", qos, std::bind(&MotorCmdTranslator::onLowState, this, std::placeholders::_1));

    RCLCPP_INFO(this->get_logger(),
                "amr_motor_cmd_translator started. radius=%.4f gear_walk=%.1f gear_steer=%.1f ppr=%.0f", radius_,
                gear_walk_, gear_steer_, pulses_per_rev_);
}

void MotorCmdTranslator::onWheelCmd(WheelSetArray::SharedPtr msg)
{
    const size_t n = msg->wheels.size();
    if (n < 2)
    {
        RCLCPP_WARN(this->get_logger(), "QD: expect 2 wheels, got %zu — dropping", n);
        return;
    }

    const int fi = wheel_index_front_;
    const int ri = wheel_index_rear_;
    if (fi < 0 || static_cast<size_t>(fi) >= n || ri < 0 || static_cast<size_t>(ri) >= n)
    {
        RCLCPP_WARN(this->get_logger(), "wheel_index out of range (front=%d rear=%d size=%zu) — dropping", fi, ri, n);
        return;
    }

    const double v_front = msg->wheels[fi].velocity;
    const double s_front = msg->wheels[fi].steering;
    const double v_rear = msg->wheels[ri].velocity;
    const double s_rear = msg->wheels[ri].steering;

    MotorCmdArray cmd;
    cmd.header.stamp = this->now();
    cmd.motors.resize(4);

    // walk_front (id=1, velocity mode)
    cmd.motors[0].motor_id = static_cast<uint8_t>(walk_front_id_);
    cmd.motors[0].mode = MotorCmd::MODE_VELOCITY;
    cmd.motors[0].target_vel =
        static_cast<int32_t>(v_front * 60.0 * gear_walk_ * 10.0 / (radius_ * 2.0 * M_PI) * dir_walk_front_);

    // walk_rear (id=2, velocity mode)
    cmd.motors[1].motor_id = static_cast<uint8_t>(walk_rear_id_);
    cmd.motors[1].mode = MotorCmd::MODE_VELOCITY;
    cmd.motors[1].target_vel =
        static_cast<int32_t>(v_rear * 60.0 * gear_walk_ * 10.0 / (radius_ * 2.0 * M_PI) * dir_walk_rear_);

    // steer_front (id=3, position mode)
    // 조향 영점 보정: raw_target = cmd − offset (offset = raw 0 일 때의 실제 물리각).
    // → cmd 0° 지령 시 raw 를 −offset 으로 보내 물리 0° 를 만든다.
    cmd.motors[2].motor_id = static_cast<uint8_t>(steer_front_id_);
    cmd.motors[2].mode = MotorCmd::MODE_POSITION;
    cmd.motors[2].target_pos = static_cast<int32_t>((s_front - steer_offset_front_) * pulses_per_rev_ *
                                                    gear_steer_ / (2.0 * M_PI) * dir_steer_front_);
    cmd.motors[2].profile_vel = steer_profile_vel_;

    // steer_rear (id=4, position mode)
    cmd.motors[3].motor_id = static_cast<uint8_t>(steer_rear_id_);
    cmd.motors[3].mode = MotorCmd::MODE_POSITION;
    cmd.motors[3].target_pos = static_cast<int32_t>((s_rear - steer_offset_rear_) * pulses_per_rev_ *
                                                    gear_steer_ / (2.0 * M_PI) * dir_steer_rear_);
    cmd.motors[3].profile_vel = steer_profile_vel_;

    low_cmd_pub_->publish(cmd);
}

void MotorCmdTranslator::onLowState(MotorStateArray::SharedPtr msg)
{
    WheelMotor wm;
    WheelMotorState wms;
    wms.header.stamp = this->now();
    wms.header.frame_id = "base_link";

    for (const auto &m : msg->motors)
    {
        if (m.motor_id == static_cast<uint8_t>(walk_front_id_))
        {
            wm.velocity_front =
                static_cast<double>(m.fb_vel) * (radius_ * 2.0 * M_PI) / (60.0 * gear_walk_ * 10.0) * dir_walk_front_;
            wms.velocity_front = wm.velocity_front;
            wms.encoder_walk_front = m.fb_pos;
        }
        else if (m.motor_id == static_cast<uint8_t>(walk_rear_id_))
        {
            wm.velocity_rear =
                static_cast<double>(m.fb_vel) * (radius_ * 2.0 * M_PI) / (60.0 * gear_walk_ * 10.0) * dir_walk_rear_;
            wms.velocity_rear = wm.velocity_rear;
            wms.encoder_walk_rear = m.fb_pos;
        }
        else if (m.motor_id == static_cast<uint8_t>(steer_front_id_))
        {
            // 조향 영점 보정: reported = raw + offset → 보고값이 실제 물리각과 일치.
            wm.angle_front =
                static_cast<double>(m.fb_pos) * (2.0 * M_PI) / (pulses_per_rev_ * gear_steer_) * dir_steer_front_ +
                steer_offset_front_;
            wms.angle_front = wm.angle_front;
            wms.encoder_steer_front = m.fb_pos;   // raw pulse (보정 전) — 원본 유지
        }
        else if (m.motor_id == static_cast<uint8_t>(steer_rear_id_))
        {
            wm.angle_rear =
                static_cast<double>(m.fb_pos) * (2.0 * M_PI) / (pulses_per_rev_ * gear_steer_) * dir_steer_rear_ +
                steer_offset_rear_;
            wms.angle_rear = wm.angle_rear;
            wms.encoder_steer_rear = m.fb_pos;    // raw pulse (보정 전) — 원본 유지
        }
    }

    // motor_ready: true if no non-zero error_code in any motor
    wms.motor_ready = true;
    for (const auto &m : msg->motors)
    {
        if (m.error_code != 0)
        {
            wms.motor_ready = false;
            break;
        }
    }
    wms.error_code = 0;

    if (publish_legacy_wms_)
    {
        wheel_motor_state_pub_->publish(wm);
    }
    if (publish_legacy_wms_detailed_)
    {
        wheel_motor_state_detailed_pub_->publish(wms);
    }
}

} // namespace amr_motor_cmd_translator
