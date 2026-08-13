#ifndef TRNAV_2WS_ACTION_SERVER__LINE_FOLLOW__LINE_FOLLOW_ACTION_SERVER_HPP_
#define TRNAV_2WS_ACTION_SERVER__LINE_FOLLOW__LINE_FOLLOW_ACTION_SERVER_HPP_

#include <memory>
#include <mutex>
#include <string>

#include "ai_msgs/msg/line_error.hpp"
#include "trnav_2ws_interfaces/action/amr_motion_line_follow.hpp"
#include "trnav_msgs/srv/select_motion_source.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"

#include "trnav_2ws_action_server/line_follow/line_follow_core.hpp"
#include "trnav_2ws_core/action_mutex.hpp"
#include "trnav_2ws_core/localization_monitor.hpp"
#include "trnav_2ws_core/transient_guard.hpp"
#include "trnav_2ws_kinematics/qd_bicycle_model.hpp"
#include "trnav_2ws_motion/qd_action_server_base.hpp"

namespace trnav_2ws_action_server::line_follow
{

class LineFollowActionServer
    : public trnav::motion::two_ws::TwoWsActionServerBase<trnav_2ws_interfaces::action::AMRMotionLineFollow>
{
  public:
    using LineFollow = trnav_2ws_interfaces::action::AMRMotionLineFollow;

    explicit LineFollowActionServer(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex);

  protected:
    bool validateGoal(std::shared_ptr<const LineFollow::Goal> goal) override;
    void execute(std::shared_ptr<GoalHandle> goal_handle) override;

  private:
    std::unique_ptr<trnav::motion::two_ws::TwoWsBicycleModel> bicycle_model_;
    std::unique_ptr<trnav_2ws_core::TransientGuard> guard_;
    std::unique_ptr<trnav_2ws_core::LocalizationMonitor> loc_monitor_;

    // ── /line/error 최신값 캐시 ──
    // 구독 콜백 스레드와 execute 스레드가 동시에 만지므로 mutex 로 감싼다.
    struct LineSnapshot
    {
        ai_msgs::msg::LineError msg;
        rclcpp::Time recv_time;
        bool received{false};
    };
    rclcpp::Subscription<ai_msgs::msg::LineError>::SharedPtr line_sub_;
    mutable std::mutex line_mutex_;
    LineSnapshot line_snapshot_;

    void lineErrorCallback(const ai_msgs::msg::LineError::SharedPtr msg);
    LineSnapshot getLineSnapshot() const;
    /// goal 진입 시 캐시를 비운다 — 직전 goal 의 오차·카메라로 판단하지 않기 위해.
    void resetLineSnapshot();
    std::string expectedCamera(bool reverse) const;
    void reloadTuning();

    // mux active source 전환 — execute() 진입 시 호출 (action server 가 자기 source_id 책임).
    rclcpp::Client<trnav_msgs::srv::SelectMotionSource>::SharedPtr select_source_client_;
    int motion_source_id_{13}; // line_follow = 13 (10·11 은 stanley 예약, 12 는 turn_reverse)

    // 제어 파라미터 — goal 실행 직전 reloadTuning() 이 재적재한다(재기동 없이 튜닝).
    trnav_2ws_action_server::line_follow::Gains gains_;
    double accel_{0.3};        // 가속 ramp (m/s^2)
    double coast_decel_{0.15}; // 소실 coast 감속 (m/s^2)
    double stop_decel_{0.5};   // 정지 감속 (m/s^2)
    double conf_threshold_{0.5};
    double resume_max_offset_{0.9};
    double wait_line_timeout_sec_{3.0};
    double input_stale_timeout_sec_{0.5};
    int offset_filter_window_{5};

    // 진행 방향 ↔ 카메라 정합 검사용 논리명 (line_vision 로스터와 같은 이름).
    std::string forward_camera_{"cam_f"};
    std::string reverse_camera_{"cam_r"};

    // 지령 변화율 제한·가드 — yaw_control 과 같은 역할·같은 기본값.
    double steer_rate_limit_{0.35};
    double walk_accel_limit_{0.5};
    double walk_decel_limit_{1.0};
    double gate_blocked_timeout_sec_{5.0};
    double max_timeout_sec_{120.0};
    bool enable_localization_watchdog_{true};
};

} // namespace trnav_2ws_action_server::line_follow

#endif // TRNAV_2WS_ACTION_SERVER__LINE_FOLLOW__LINE_FOLLOW_ACTION_SERVER_HPP_
