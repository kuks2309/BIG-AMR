#ifndef AMR_MOTION_ACTION_SERVER__SPIN__SPIN_ACTION_SERVER_HPP_
#define AMR_MOTION_ACTION_SERVER__SPIN__SPIN_ACTION_SERVER_HPP_

#include "trnav_2ws_interfaces/action/amr_motion_spin.hpp"
#include "trnav_msgs/srv/select_motion_source.hpp"
#include "trnav_2ws_core/action_mutex.hpp"
#include "trnav_2ws_motion/qd_action_server_base.hpp"
#include "trnav_2ws_core/motion_profile.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include <memory>

namespace trnav_2ws_action_server::spin
{

class SpinActionServer : public trnav::motion::two_ws::TwoWsActionServerBase<trnav_2ws_interfaces::action::AMRMotionSpin>
{
  public:
    using Spin = trnav_2ws_interfaces::action::AMRMotionSpin;

    explicit SpinActionServer(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex);

  protected:
    bool validateGoal(std::shared_ptr<const Spin::Goal> goal) override;
    void execute(std::shared_ptr<GoalHandle> goal_handle) override;

  private:
    // mux active source 전환 — execute() 진입 시 호출. action server 가 자기 source_id 책임 (정공법).
    rclcpp::Client<trnav_msgs::srv::SelectMotionSource>::SharedPtr select_source_client_;
    int motion_source_id_{3};  // spin = 3

    // Spin precision parameters (from YAML)
    double min_speed_dps_{2.0};
    double fine_correction_threshold_deg_{0.3};
    // ⚠ 제거됨(2026-08-09) — `fine_correction_speed_dps_` · `fine_correction_timeout_sec_` ·
    //   `settling_delay_ms_`. 셋 다 값을 읽어 담기만 하고 **읽는 코드가 없었다.**
    //   그중 `fine_correction_timeout_sec` 는 hot-reload 화이트리스트에까지 있어
    //   `ros2 param set` 이 성공을 반환하면서 거동은 하나도 안 바뀌었다(실측 확인).
    //   실제 fine timeout 은 기동 규모에 비례해 계산한다 — `.cpp` 의
    //   `max(2.0, 3.0 × target_abs / max_ω)`. 죽은 손잡이를 남기지 않는다.
    double spin_max_timeout_sec_{60.0};

    // start_yaw 원형 이동평균 샘플 수 — 시작 1회 IMU 노이즈가 절대 target 기준 전체를
    // 오프셋하는 것 방지 (차체 정지 구간 평활; 윈도우 = N / control_rate_hz).
    int start_yaw_window_{10};

    // 하이브리드: Stage1(사다리꼴 coarse) → 남은 오차 ≤ pid_band → Stage2(PID fine).
    double pid_band_deg_{5.0}; // coarse→PID 핸드오프 임계 (deg)

    // PID 회전 제어 게인 (yaml). Stage2 fine: ω_cmd[deg/s] = kp·e + ki·∫e + kd·de/dt, e=부호포함 남은오차[deg].
    // bang-bang fine 을 대체. SIL 검증 시드값 — 실차 재튜닝 대상.
    double kp_spin_{1.5};
    double ki_spin_{0.0};
    double kd_spin_{0.5};
    double integral_limit_deg_{30.0}; // I항 anti-windup clamp (deg·s)
    double settle_rate_dps_{2.0};     // 정착 판정: |실측 각속도| < 이 값
    int settle_count_{5};             // 정착 연속 cycle 수

    // Hot-reload param 콜백 핸들 (HIL 게인 튜닝 — ros2 param set 실시간 반영)
    rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr params_cb_handle_;
};

} // namespace trnav_2ws_action_server::spin

#endif // AMR_MOTION_ACTION_SERVER__SPIN__SPIN_ACTION_SERVER_HPP_
