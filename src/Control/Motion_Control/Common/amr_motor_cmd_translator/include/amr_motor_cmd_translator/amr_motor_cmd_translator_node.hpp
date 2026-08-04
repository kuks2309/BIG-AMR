#pragma once

#include "trnav_msgs/msg/motor_cmd_array.hpp"
#include "trnav_msgs/msg/motor_state_array.hpp"
#include "trnav_msgs/msg/wheel_motor.hpp"
#include "trnav_msgs/msg/wheel_motor_state.hpp"
#include "trnav_msgs/msg/wheel_set_array.hpp"
#include <rclcpp/rclcpp.hpp>

namespace amr_motor_cmd_translator
{

class MotorCmdTranslator : public rclcpp::Node
{
  public:
    explicit MotorCmdTranslator();

  private:
    void onWheelCmd(trnav_msgs::msg::WheelSetArray::SharedPtr msg);
    void onLowState(trnav_msgs::msg::MotorStateArray::SharedPtr msg);

    // parameters (cached copies)
    double radius_;
    double gear_walk_;
    double gear_steer_;
    double pulses_per_rev_;

    int walk_front_id_;
    int walk_rear_id_;
    int steer_front_id_;
    int steer_rear_id_;

    int dir_walk_front_;
    int dir_walk_rear_;
    int dir_steer_front_;
    int dir_steer_rear_;
    // 조향 영점 오프셋 (rad) = 엔코더 raw 가 0 일 때의 **실제 물리 조향각**.
    // 지령: raw_target = cmd − offset  /  피드백: reported = raw + offset
    // 측정: experiments/2026-07-13_steer_zero_calib (개루프 같은방향 leg, 캐스터 플립 배제)
    double steer_offset_front_;
    double steer_offset_rear_;

    int32_t steer_profile_vel_;

    int wheel_index_front_;
    int wheel_index_rear_;

    bool publish_legacy_wms_;
    bool publish_legacy_wms_detailed_;

    // publishers
    rclcpp::Publisher<trnav_msgs::msg::MotorCmdArray>::SharedPtr low_cmd_pub_;
    rclcpp::Publisher<trnav_msgs::msg::WheelMotor>::SharedPtr wheel_motor_state_pub_;
    rclcpp::Publisher<trnav_msgs::msg::WheelMotorState>::SharedPtr wheel_motor_state_detailed_pub_;

    // subscribers
    rclcpp::Subscription<trnav_msgs::msg::WheelSetArray>::SharedPtr wheel_cmd_sub_;
    rclcpp::Subscription<trnav_msgs::msg::MotorStateArray>::SharedPtr low_state_sub_;
};

} // namespace amr_motor_cmd_translator
