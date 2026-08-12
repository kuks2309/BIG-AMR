#ifndef AMR_MOTION_ACTION_SERVER__TRANSLATE_REVERSE__TRANSLATE_REVERSE_ACTION_SERVER_HPP_
#define AMR_MOTION_ACTION_SERVER__TRANSLATE_REVERSE__TRANSLATE_REVERSE_ACTION_SERVER_HPP_

#include <atomic>
#include <chrono>
#include <memory>
#include <mutex>

#include "trnav_2ws_interfaces/action/amr_motion_translate_reverse.hpp"
#include "trnav_msgs/msg/wheel_motor.hpp"
#include "trnav_msgs/srv/select_motion_source.hpp"
#include "nav_msgs/msg/path.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"

#include "trnav_2ws_core/action_mutex.hpp"
#include "trnav_2ws_motion/qd_action_server_base.hpp"
#include "trnav_2ws_kinematics/qd_bicycle_model.hpp"
#include "trnav_2ws_core/localization_monitor.hpp"
#include "trnav_2ws_core/motion_profile.hpp"
#include "trnav_2ws_motion/qd_path_controller.hpp"
#include "trnav_2ws_core/transient_guard.hpp"

namespace trnav_2ws_action_server::translate_reverse
{

// 후진 전용 노드. Forward 와 차이:
// 1. lookupMapToBase 후 robot_yaw = normalizeAngle(yaw + π) 보정 (effective_yaw)
// 2. wheel velocity 출력 부호 반전 (vel_f, vel_r *= -1)
// 3. feedback current_vx 부호 음수
// 4. (Step 6 후) PathController 호출 시 TravelDirection::REVERSE 명시
//    → BICYCLE heading PD 부호 자동 반전 → 비정렬 시 e_theta 수렴
class TranslateReverseActionServer
    : public trnav::motion::two_ws::TwoWsActionServerBase<trnav_2ws_interfaces::action::AMRMotionTranslateReverse>
{
  public:
    using Translate = trnav_2ws_interfaces::action::AMRMotionTranslateReverse;

    explicit TranslateReverseActionServer(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex);

  protected:
    bool validateGoal(std::shared_ptr<const Translate::Goal> goal) override;
    void execute(std::shared_ptr<GoalHandle> goal_handle) override;

    void wheelStateCallback(const trnav_msgs::msg::WheelMotor::SharedPtr msg) override;

  private:
    rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_viz_pub_;
    rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr debug_pub_;

    std::unique_ptr<trnav::motion::two_ws::TwoWsBicycleModel> bicycle_model_;
    std::unique_ptr<trnav::motion::two_ws::TwoWsPathController> path_ctrl_;
    std::unique_ptr<trnav_2ws_core::TransientGuard> guard_;
    std::unique_ptr<trnav_2ws_core::LocalizationMonitor> loc_monitor_;

    std::mutex wheel_state_time_mutex_;
    std::chrono::steady_clock::time_point last_wheel_state_time_;
    std::atomic<bool> wheel_state_received_{false};

    std::atomic<double> max_cmd_speed_{0.0};

    // mux active source 전환 — execute() 진입 시 호출. action server 가 자기 source_id 책임 (정공법).
    // 부팅 시 supervisor 가 forward 로만 set 하므로, reverse 진입 시 자체 전환 안 하면 mux 가 drop.
    rclcpp::Client<trnav_msgs::srv::SelectMotionSource>::SharedPtr select_source_client_;
    int motion_source_id_{2};  // translate_reverse = 2 (trnav_motion_mux.yaml source_2)

    // Control parameters (yaml — forward 와 같은 translate_* 키)
    double min_vx_{0.02};
    double behind_start_speed_{0.2};
    double vy_ramp_time_{1.0};
    double goal_reach_threshold_{0.05};
    double max_timeout_sec_{60.0};
    bool enable_localization_watchdog_{true};
    double steer_rate_static_{0.140};
    double steer_rate_dynamic_{0.350};
    double steer_rate_vx_threshold_{0.05};
    double walk_accel_limit_{0.5};
    double walk_decel_limit_{1.0};

    trnav::motion::two_ws::ControlMode default_mode_{trnav::motion::two_ws::ControlMode::BICYCLE};
    double wheelbase_{0.66};
    double max_delta_{M_PI / 4.0};
    double steer_converge_err_low_deg_{3.0};
    double steer_converge_err_high_deg_{30.0};
    double steer_converge_min_scale_{0.3};

    // Hot-reloadable PathController gains (cached snapshot, forward 와 동일 패턴).
    double Kp_heading_{1.0};
    double Kd_heading_{0.3};
    double K_stanley_{2.0};
    double K_soft_{1.0};

    rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr params_cb_handle_;
};

} // namespace trnav_2ws_action_server::translate_reverse

#endif // AMR_MOTION_ACTION_SERVER__TRANSLATE_REVERSE__TRANSLATE_REVERSE_ACTION_SERVER_HPP_
