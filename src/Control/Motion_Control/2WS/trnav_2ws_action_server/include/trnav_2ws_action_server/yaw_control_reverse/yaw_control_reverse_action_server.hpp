#ifndef AMR_MOTION_ACTION_SERVER__YAW_CONTROL_REVERSE__YAW_CONTROL_REVERSE_ACTION_SERVER_HPP_
#define AMR_MOTION_ACTION_SERVER__YAW_CONTROL_REVERSE__YAW_CONTROL_REVERSE_ACTION_SERVER_HPP_

#include <atomic>
#include <memory>

#include "trnav_2ws_interfaces/action/amr_motion_yaw_control_reverse.hpp"
#include "trnav_msgs/srv/select_motion_source.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"

#include "trnav_2ws_core/action_mutex.hpp"
#include "trnav_2ws_motion/qd_action_server_base.hpp"
#include "trnav_2ws_kinematics/qd_bicycle_model.hpp"
#include "trnav_2ws_core/localization_monitor.hpp"
#include "trnav_2ws_core/motion_profile.hpp"
#include "trnav_2ws_core/transient_guard.hpp"

namespace trnav_2ws_action_server::yaw_control_reverse
{

// 후진 전용 yaw 추종 노드. yaw_control 과 차이:
// 1. vx_max 는 magnitude (>0) — 내부에서 항상 -vx 적용
// 2. PID err_deg 부호 항상 반전 (forward 분기 제거)
// 3. feedback current_vx 항상 ≤ 0
// IK 는 vx_signed<0 입력으로 wheel direction 자동 처리 — 출력단에 추가 부호 곱하기 없음
// (translate_reverse 의 kReverseDir 패턴은 PathController forward 재사용 trick 의
//  부산물이라 본 노드엔 적용하지 않는다 — R1 SIL 1차에서 이중 부호 반전으로 발견 후 정정).
// effective_yaw 보정도 적용하지 않음 (PathController 미사용 — IMU yaw 직접 PID).
class YawControlReverseActionServer
    : public trnav::motion::two_ws::TwoWsActionServerBase<trnav_2ws_interfaces::action::AMRMotionYawControlReverse>
{
  public:
    using YawControlReverse = trnav_2ws_interfaces::action::AMRMotionYawControlReverse;

    explicit YawControlReverseActionServer(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex);

  protected:
    bool validateGoal(std::shared_ptr<const YawControlReverse::Goal> goal) override;
    void execute(std::shared_ptr<GoalHandle> goal_handle) override;

  private:
    std::unique_ptr<trnav::motion::two_ws::TwoWsBicycleModel> bicycle_model_;
    std::unique_ptr<trnav_2ws_core::TransientGuard> guard_;
    std::unique_ptr<trnav_2ws_core::LocalizationMonitor> loc_monitor_;

    // mux active source 전환 — execute() 진입 시 호출. action server 가 자기 source_id 책임 (정공법).
    rclcpp::Client<trnav_msgs::srv::SelectMotionSource>::SharedPtr select_source_client_;
    int motion_source_id_{7};  // yaw_control_reverse = 7 (2026-05-16 9→7, docs/abstraction/motion_source_id_contract.md)

    // Control parameters (from YAML — yaw_control_reverse_*)
    // ⚠ 아래 파라미터 멤버는 **두 스레드가 동시에 만진다** — `execute()` 는
    //   `handleAccepted` 가 detach 한 별도 스레드에서 돌고, 파라미터 콜백은 executor
    //   스레드에서 돈다. 비-atomic 이면 UB 이고, 최적화기가 루프 밖으로 로드를 끌어올리면
    //   hot-reload 가 진행 중 goal 에 **비결정적으로 반영되지 않는다**(고치려던 증상의 재발).
    //   베이스가 같은 이유로 atomic 을 쓴다(`qd_action_server_base.hpp`).
    // 최종 헤딩 오차 허용(−9). **정확도 규격이 아니라 조용한 실패 가드**다 —
    // 조향이 죽으면 IMU·맵이 둘 다 「안 돌았다」로 일치해 −7 이 뜨지 않고 거리만 채워
    // `status 0` 이 나간다. 실기 검증 기동을 깨지 않도록 넉넉히 잡는다.
    std::atomic<double> final_yaw_tol_deg_{10.0};
    std::atomic<bool> enable_final_yaw_check_{true};

    std::atomic<double> max_timeout_sec_{60.0};
    std::atomic<bool> enable_localization_watchdog_{true};
    std::atomic<double> walk_accel_limit_{0.5};
    std::atomic<double> walk_decel_limit_{1.0};
    std::atomic<double> steer_rate_limit_{0.35};
    std::atomic<double> min_vx_{0.02}; // floor on profile speed (m/s) — prevents stuck-at-start when vx_profile=0

    // ── 조대(粗大) 헤딩 발산 탐지 ── (전진판과 동일 규약)
    // 제어 소스는 IMU 그대로다. 측위 heading 은 정밀도가 낮아 미세 제어에 쓰면 오히려 나빠지므로
    // **고장 탐지에만** 쓴다. 임계는 제어 목표가 아니라 고장 경계다.
    // 근거·설계: docs/adr/2026-08-10-yaw-control-heading-divergence-guard.md
    std::atomic<bool> enable_heading_divergence_guard_{true};
    std::atomic<double> heading_divergence_deg_{5.0};
    std::atomic<int> heading_divergence_count_{10};

    // ── 조향 미도달 지속 감시 ──
    // 임계는 정상 조향 이동 시간보다 길어야 오탐이 없다 — 실측상 0→31° 이동에 약 3 초.
    // 근거·설계: docs/adr/2026-08-10-yaw-control-gate-blocked-guard.md
    std::atomic<double> gate_blocked_timeout_sec_{5.0};

    // hot-reload 콜백 핸들 (거짓 성공 제거 — ADR 2026-08-10-yaw-control-param-callback)
    rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr params_cb_handle_;
};

} // namespace trnav_2ws_action_server::yaw_control_reverse

#endif // AMR_MOTION_ACTION_SERVER__YAW_CONTROL_REVERSE__YAW_CONTROL_REVERSE_ACTION_SERVER_HPP_
