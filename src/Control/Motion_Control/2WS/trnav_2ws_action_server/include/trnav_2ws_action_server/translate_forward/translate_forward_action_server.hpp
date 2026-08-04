#ifndef AMR_MOTION_ACTION_SERVER__TRANSLATE_FORWARD__TRANSLATE_FORWARD_ACTION_SERVER_HPP_
#define AMR_MOTION_ACTION_SERVER__TRANSLATE_FORWARD__TRANSLATE_FORWARD_ACTION_SERVER_HPP_

#include <atomic>
#include <chrono>
#include <memory>
#include <mutex>

#include "trnav_2ws_interfaces/action/amr_motion_translate_forward.hpp"
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

namespace trnav_2ws_action_server::translate_forward
{

class TranslateForwardActionServer
    : public trnav::motion::two_ws::TwoWsActionServerBase<trnav_2ws_interfaces::action::AMRMotionTranslateForward>
{
  public:
    using Translate = trnav_2ws_interfaces::action::AMRMotionTranslateForward;

    explicit TranslateForwardActionServer(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex);

  protected:
    bool validateGoal(std::shared_ptr<const Translate::Goal> goal) override;
    void execute(std::shared_ptr<GoalHandle> goal_handle) override;

    // Override: wheel-state timestamp tracking (actual-steer-based speed)
    void wheelStateCallback(const trnav_msgs::msg::WheelMotor::SharedPtr msg) override;

  private:
    // Extra publishers (path viz, debug array)
    rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_viz_pub_;
    rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr debug_pub_;

    // Modules
    std::unique_ptr<trnav::motion::two_ws::TwoWsBicycleModel> bicycle_model_;
    std::unique_ptr<trnav::motion::two_ws::TwoWsPathController> path_ctrl_;
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
    int motion_source_id_{1};  // translate_forward = 1

    // Control parameters (from YAML)
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

    // 종단 fine-positioning (exit_speed<=0 최종 정지 한정 closed-loop creep)
    double fine_enter_dist_{0.08};
    double fine_tol_pos_{0.02};
    double fine_kp_{0.5};
    double fine_v_max_{0.04};
    double fine_v_min_{0.015};
    double fine_timeout_{5.0};

    // BICYCLE 고정. Mode 2+ 는 후속 Wave.
    trnav::motion::two_ws::ControlMode default_mode_{trnav::motion::two_ws::ControlMode::BICYCLE};
    double wheelbase_{0.66};
    double max_delta_{M_PI / 4.0};
    double steer_converge_err_low_deg_{3.0};
    double steer_converge_err_high_deg_{30.0};
    double steer_converge_min_scale_{0.3};

    // Hot-reloadable PathController gains (cached snapshot, callback 이 부분 갱신 시
    // 5 개 모두 path_ctrl_->setGains 에 전달).
    double Kp_heading_{1.0};
    double Kd_heading_{0.3};
    double K_stanley_{2.0};
    double K_soft_{1.0};

    // heading yaw 소스: 0=robot_pose(기본) / 1=IMU(시작 RMA10 offset 후 고정). x,y(CTE)는 항상 pose.
    int heading_source_{0};

    // ros2 param set 핫 리로드 콜백 핸들 (PathController 5 게인 한정).
    rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr params_cb_handle_;
};

} // namespace trnav_2ws_action_server::translate_forward

#endif // AMR_MOTION_ACTION_SERVER__TRANSLATE_FORWARD__TRANSLATE_FORWARD_ACTION_SERVER_HPP_
