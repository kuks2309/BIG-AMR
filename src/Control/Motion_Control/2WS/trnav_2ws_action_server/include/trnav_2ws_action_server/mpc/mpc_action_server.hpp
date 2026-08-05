#ifndef AMR_MOTION_ACTION_SERVER__MPC__MPC_ACTION_SERVER_HPP_
#define AMR_MOTION_ACTION_SERVER__MPC__MPC_ACTION_SERVER_HPP_

#include <atomic>
#include <chrono>
#include <memory>
#include <mutex>

#include "trnav_2ws_interfaces/action/amr_motion_mpc.hpp"
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
#include "trnav_2ws_motion/qd_mpc_controller.hpp"
#include "trnav_2ws_core/transient_guard.hpp"

namespace trnav_2ws_action_server::mpc
{

class MpcActionServer
    : public trnav::motion::two_ws::TwoWsActionServerBase<trnav_2ws_interfaces::action::AMRMotionMpc>
{
  public:
    using Mpc = trnav_2ws_interfaces::action::AMRMotionMpc;

    explicit MpcActionServer(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex);

  protected:
    bool validateGoal(std::shared_ptr<const Mpc::Goal> goal) override;
    void execute(std::shared_ptr<GoalHandle> goal_handle) override;

    // Override: wheel-state timestamp tracking (actual-steer-based speed)
    void wheelStateCallback(const trnav_msgs::msg::WheelMotor::SharedPtr msg) override;

  private:
    // Extra publishers (path viz, debug array)
    rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_viz_pub_;
    rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr debug_pub_;

    // Modules
    std::unique_ptr<trnav::motion::two_ws::TwoWsBicycleModel> bicycle_model_;
    std::unique_ptr<trnav::motion::two_ws::TwoWsMpcController> pp_ctrl_;
    std::unique_ptr<trnav_2ws_core::TransientGuard> guard_;
    std::unique_ptr<trnav_2ws_core::LocalizationMonitor> loc_monitor_;

    // Wheel feedback freshness tracking
    std::mutex wheel_state_time_mutex_;
    std::chrono::steady_clock::time_point last_wheel_state_time_;
    std::atomic<bool> wheel_state_received_{false};

    // Localization speed limit (for jump detection in LocalizationMonitor)
    std::atomic<double> max_cmd_speed_{0.0};

    // mux active source 전환 — execute() 진입 시 호출. action server 가 자기 source_id 책임 (정공법).
    rclcpp::Client<trnav_msgs::srv::SelectMotionSource>::SharedPtr select_source_client_;
    int motion_source_id_{8};  // mpc = 8 (2026-05-16 7→8, docs/abstraction/motion_source_id_contract.md)

    // Control parameters (from YAML)
    double lookahead_distance_{0.6};
    double goal_reach_threshold_{0.05};
    double min_vx_{0.02};
    double behind_start_speed_{0.2};
    double max_timeout_sec_{60.0};
    bool enable_localization_watchdog_{true};
    double steer_rate_static_{0.140};
    double steer_rate_dynamic_{0.350};
    double steer_rate_vx_threshold_{0.05};
    double walk_accel_limit_{0.5};
    double walk_decel_limit_{1.0};
    double wheelbase_{0.66};
    double max_delta_{M_PI / 4.0};
    double steer_converge_err_low_deg_{3.0};
    double steer_converge_err_high_deg_{30.0};
    double steer_converge_min_scale_{0.3};

    // ros2 param set 핫 리로드 콜백 (mpc_lookahead_distance / mpc_max_delta_deg).
    rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr params_cb_handle_;
};

} // namespace trnav_2ws_action_server::mpc

#endif // AMR_MOTION_ACTION_SERVER__MPC__MPC_ACTION_SERVER_HPP_
