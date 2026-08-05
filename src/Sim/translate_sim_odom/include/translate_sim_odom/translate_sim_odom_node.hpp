#ifndef TRANSLATE_SIM_ODOM__TRANSLATE_SIM_ODOM_NODE_HPP_
#define TRANSLATE_SIM_ODOM__TRANSLATE_SIM_ODOM_NODE_HPP_

#include <atomic>
#include <memory>
#include <mutex>

#include "trnav_msgs/msg/wheel_motor.hpp"
#include "trnav_msgs/msg/wheel_set_array.hpp"
#include "geometry_msgs/msg/pose_with_covariance_stamped.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/imu.hpp"
#include "tf2_ros/transform_broadcaster.h"

namespace translate_sim_odom
{

// 폐쇄 루프 SIL 시뮬레이터 — amr_translate_node 검증용.
//
// 입력  : /motor/wheel_cmd (trnav_msgs::WheelSetArray, 2 wheels QD diagonal)
// 처리  : 2-wheel kinematic 역계산 → (vx, vy, omega) → Euler 적분 (50Hz)
// 출력  : TF map→base_link, /rtabmap/localization_pose (1Hz),
//        /imu/data (50Hz), /wheel_motor_state (50Hz, cmd echo)
//
// QD wheel layout (config):
//   w1 = (w1_x, w1_y) = (+0.330, +0.135)  ← front-left (wheels[0])
//   w2 = (w2_x, w2_y) = (-0.330, -0.135)  ← rear-right (wheels[1])
class TranslateSimOdomNode : public rclcpp::Node
{
  public:
    TranslateSimOdomNode();

  private:
    void wheelCmdCallback(const trnav_msgs::msg::WheelSetArray::SharedPtr msg);
    void integrateAndPublish();

    // ── Robot geometry ──
    double w1_x_;
    double w1_y_;
    double w2_x_;
    double w2_y_;

    // ── Initial pose ──
    double initial_x_;
    double initial_y_;
    double initial_yaw_;

    // ── IMU yaw offset (rad) ──
    // Models real-world misalignment between IMU's own yaw zero and map's yaw zero.
    // imu_published_yaw = ground_truth_yaw + imu_yaw_offset_rad_
    // → yaw_control's calibration: yaw_offset = wrap(start_yaw_map - start_yaw_imu) = -imu_yaw_offset_rad_
    // S7 SIL scenario uses non-zero value to verify offset calibration. Default 0 (legacy behavior).
    double imu_yaw_offset_rad_;

    // ── Integration state (atomic for callback safety) ──
    std::atomic<double> x_{0.0};
    std::atomic<double> y_{0.0};
    std::atomic<double> yaw_{0.0};

    // ── Latest cmd (mutex protected) ──
    std::mutex cmd_mtx_;
    double cmd_v0_{0.0}; // wheels[0] velocity (signed)
    double cmd_s0_{0.0}; // wheels[0] steering (rad)
    double cmd_v1_{0.0};
    double cmd_s1_{0.0};
    bool cmd_received_{false};

    // ── Pubs/Subs ──
    rclcpp::Subscription<trnav_msgs::msg::WheelSetArray>::SharedPtr wheel_cmd_sub_;
    rclcpp::Publisher<geometry_msgs::msg::PoseWithCovarianceStamped>::SharedPtr loc_pose_pub_;
    rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr imu_pub_;
    rclcpp::Publisher<trnav_msgs::msg::WheelMotor>::SharedPtr wheel_state_pub_;
    std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;

    // ── Timer ──
    rclcpp::TimerBase::SharedPtr integrate_timer_;
    double integrate_rate_hz_;
    rclcpp::Time last_integrate_time_;
    bool first_step_{true};
};

} // namespace translate_sim_odom

#endif // TRANSLATE_SIM_ODOM__TRANSLATE_SIM_ODOM_NODE_HPP_
