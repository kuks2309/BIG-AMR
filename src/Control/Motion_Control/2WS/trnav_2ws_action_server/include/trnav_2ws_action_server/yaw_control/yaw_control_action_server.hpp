#ifndef AMR_MOTION_ACTION_SERVER__YAW_CONTROL__YAW_CONTROL_ACTION_SERVER_HPP_
#define AMR_MOTION_ACTION_SERVER__YAW_CONTROL__YAW_CONTROL_ACTION_SERVER_HPP_

#include <atomic>
#include <memory>

#include "trnav_2ws_interfaces/action/amr_motion_yaw_control.hpp"
#include "trnav_msgs/srv/select_motion_source.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"

#include "trnav_2ws_core/action_mutex.hpp"
#include "trnav_2ws_motion/qd_action_server_base.hpp"
#include "trnav_2ws_kinematics/qd_bicycle_model.hpp"
#include "trnav_2ws_core/localization_monitor.hpp"
#include "trnav_2ws_core/motion_profile.hpp"
#include "trnav_2ws_core/transient_guard.hpp"

namespace trnav_2ws_action_server::yaw_control
{

class YawControlActionServer
    : public trnav::motion::two_ws::TwoWsActionServerBase<trnav_2ws_interfaces::action::AMRMotionYawControl>
{
  public:
    using YawControl = trnav_2ws_interfaces::action::AMRMotionYawControl;

    explicit YawControlActionServer(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex);

  protected:
    bool validateGoal(std::shared_ptr<const YawControl::Goal> goal) override;
    void execute(std::shared_ptr<GoalHandle> goal_handle) override;

  private:
    std::unique_ptr<trnav::motion::two_ws::TwoWsBicycleModel> bicycle_model_;
    std::unique_ptr<trnav_2ws_core::TransientGuard> guard_;
    std::unique_ptr<trnav_2ws_core::LocalizationMonitor> loc_monitor_;

    // mux active source 전환 — execute() 진입 시 호출. action server 가 자기 source_id 책임 (정공법).
    rclcpp::Client<trnav_msgs::srv::SelectMotionSource>::SharedPtr select_source_client_;
    int motion_source_id_{6};  // yaw_control = 6

    // Control parameters (from YAML)
    double max_timeout_sec_{60.0};
    bool enable_localization_watchdog_{true};
    double walk_accel_limit_{0.5};
    double walk_decel_limit_{1.0};
    double steer_rate_limit_{0.35};
    double min_vx_{0.02}; // floor on profile speed (m/s) — prevents stuck-at-start when vx_profile=0

    // ── 조대(粗大) 헤딩 발산 탐지 ──
    // 제어 소스는 IMU 그대로다. 측위 heading 은 정밀도가 낮아 미세 제어에 쓰면 오히려 나빠지므로
    // **고장 탐지에만** 쓴다 — |보정 yaw − 맵 yaw| 가 임계를 연속 초과하면 status −7 로 abort.
    // 임계 5° 는 제어 목표가 아니라 고장 경계다: 정상 괴리는 0.09~0.25°, 고장 사례는 25° 였다.
    // 근거·설계: docs/adr/2026-08-10-yaw-control-heading-divergence-guard.md
    bool enable_heading_divergence_guard_{true};
    double heading_divergence_deg_{5.0};
    int heading_divergence_count_{10}; // 연속 cycle (50 Hz 기준 0.2 s) — 맵 순간 튐 오탐 방지

    // ── 조향 미도달 지속 감시 ──
    // TransientGuard 가 조향 오차로 구동을 0 으로 묶는 것(gate_blocked)은 정상 안전 동작이지만,
    // 그 상태가 무한 지속돼도 아무도 보고하지 않아 전역 타임아웃(60 s)까지 조용히 대기했다.
    // 임계는 **정상 조향 이동 시간보다 길어야** 오탐이 없다 — 실측상 0→31° 이동에 약 3 초.
    // 근거·설계: docs/adr/2026-08-10-yaw-control-gate-blocked-guard.md
    double gate_blocked_timeout_sec_{5.0};
};

} // namespace trnav_2ws_action_server::yaw_control

#endif // AMR_MOTION_ACTION_SERVER__YAW_CONTROL__YAW_CONTROL_ACTION_SERVER_HPP_
