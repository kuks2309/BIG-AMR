#ifndef AMR_MOTION_ACTION_SERVER__TURN__TURN_ACTION_SERVER_HPP_
#define AMR_MOTION_ACTION_SERVER__TURN__TURN_ACTION_SERVER_HPP_

#include "trnav_2ws_interfaces/action/amr_motion_turn.hpp"
#include "trnav_msgs/srv/select_motion_source.hpp"
#include "trnav_2ws_core/action_mutex.hpp"
#include "trnav_2ws_motion/qd_action_server_base.hpp"
#include "trnav_2ws_core/motion_profile.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include <memory>

namespace trnav_2ws_action_server::turn
{

class TurnActionServer : public trnav::motion::two_ws::TwoWsActionServerBase<trnav_2ws_interfaces::action::AMRMotionTurn>
{
  public:
    using Turn = trnav_2ws_interfaces::action::AMRMotionTurn;

    explicit TurnActionServer(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex);

  protected:
    bool validateGoal(std::shared_ptr<const Turn::Goal> goal) override;
    void execute(std::shared_ptr<GoalHandle> goal_handle) override;

  private:
    // mux active source 전환 — execute() 진입 시 호출. action server 가 자기 source_id 책임 (정공법).
    rclcpp::Client<trnav_msgs::srv::SelectMotionSource>::SharedPtr select_source_client_;
    int motion_source_id_{5};  // turn = 5

    // ── Turn precision parameters ──
    // 2026-08-09 구조 변경: 델타 누적 → 절대 목표 yaw, bang-bang 미세보정 → PD.
    // 근거·설계: docs/adr/2026-08-09-turn-error-feedback.md
    //
    // 삭제된 이름: imu_deadband_deg · fine_correction_speed_dps ·
    //              fine_correction_timeout_sec · settling_delay_ms
    //   앞의 셋은 델타 누적/bang-bang 전용이라 쓸 곳이 없어졌고, settling_delay 는 PD 가
    //   연속 제어하므로 불필요하다. **주석으로 남기지 않고 지운다** — 값만 담고 읽히지 않는
    //   손잡이는 `ros2 param set` 이 성공을 반환하면서 거동은 안 바뀌는 함정이 된다
    //   (2026-08-09 spin_params.yaml 실측 + 사용자 지시).
    double min_speed_dps_{2.0};                 // Stage 1(coarse) 각속도 하한. fine 에는 걸지 않는다.
    double fine_correction_threshold_deg_{0.3}; // Stage 2 정착 판정 각오차 tol

    // ── Stage 1(사다리꼴 coarse) → |잔여| ≤ pid_band → Stage 2(PD fine) ──
    double pid_band_deg_{5.0}; // coarse→PD 인계 임계. kp·band ≈ ω_max 가 되게 잡아 인계 연속성 확보.
    double kp_turn_{0.6};      // 비례 게인 (deg/s per deg)
    double kd_turn_{0.1};      // 미분 게인 (오버슈트 댐핑, derivative-on-error = −실측 회전율)
    // ⚠ ki 는 **파라미터로도 두지 않는다.** 사용자 지시(2026-08-09): 「ki 는 진동을 만들 수
    //   있으므로 하지말고」. 항상 0 이어야 하는 게인은 손잡이가 아니라 함정이다.
    //   대가로 정상오차는 남을 수 있다 — spin 과 같은 방침(`ki_spin: 0.0`).
    double settle_rate_dps_{0.5}; // 정착 판정 회전율 상한 (spin 실기 튜닝값 승계)
    int settle_count_{5};         // 정착 판정 연속 cycle 수
    int start_yaw_window_{10};

    // 전역 시한 — Stage 1 은 「오차가 줄어드는 것」 외에 종료 조건이 없다.
    // IMU 두절·차체 구속에서 무한 원호가 되는 것을 막는다(spin·yaw_control 과 같은 규약).
    double max_timeout_sec_{60.0};    // start_yaw 원형 이동평균 샘플 수 (윈도우 = N / control_rate_hz)
};

} // namespace trnav_2ws_action_server::turn

#endif // AMR_MOTION_ACTION_SERVER__TURN__TURN_ACTION_SERVER_HPP_
