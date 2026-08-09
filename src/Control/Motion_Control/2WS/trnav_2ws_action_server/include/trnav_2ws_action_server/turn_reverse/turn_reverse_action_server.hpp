#ifndef AMR_MOTION_ACTION_SERVER__TURN_REVERSE__TURN_REVERSE_ACTION_SERVER_HPP_
#define AMR_MOTION_ACTION_SERVER__TURN_REVERSE__TURN_REVERSE_ACTION_SERVER_HPP_

// 후진 원호(R-turn reverse) 액션 서버.
//
// 전진판은 `turn/turn_action_server.hpp`. 두 파일은 IK 입력의 vx 부호를 빼면 같다 —
// 한쪽을 고치면 다른 쪽도 고쳐야 한다(중복 비용은 ADR 이 명시적으로 수용).
// 근거·설계: docs/adr/2026-08-09-turn-reverse.md

#include "trnav_2ws_interfaces/action/amr_motion_turn_reverse.hpp"
#include "trnav_msgs/srv/select_motion_source.hpp"
#include "trnav_2ws_core/action_mutex.hpp"
#include "trnav_2ws_motion/qd_action_server_base.hpp"
#include "trnav_2ws_core/motion_profile.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include <memory>

namespace trnav_2ws_action_server::turn_reverse
{

class TurnReverseActionServer
    : public trnav::motion::two_ws::TwoWsActionServerBase<trnav_2ws_interfaces::action::AMRMotionTurnReverse>
{
  public:
    using TurnReverse = trnav_2ws_interfaces::action::AMRMotionTurnReverse;

    explicit TurnReverseActionServer(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex);

  protected:
    bool validateGoal(std::shared_ptr<const TurnReverse::Goal> goal) override;
    void execute(std::shared_ptr<GoalHandle> goal_handle) override;

  private:
    // mux active source 전환 — execute() 진입 시 호출. action server 가 자기 source_id 책임 (정공법).
    // ⚠ 12 인 이유: 10·11 은 stanley/stanley_reverse 예약(미구현)이라 침범하지 않는다.
    //   계약 정본은 `trnav_motion_mux.yaml` 의 Reserved IDs 주석.
    rclcpp::Client<trnav_msgs::srv::SelectMotionSource>::SharedPtr select_source_client_;
    int motion_source_id_{12}; // turn_reverse = 12

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
    int start_yaw_window_{10};    // start_yaw 원형 이동평균 샘플 수 (윈도우 = N / control_rate_hz)
};

} // namespace trnav_2ws_action_server::turn_reverse

#endif // AMR_MOTION_ACTION_SERVER__TURN_REVERSE__TURN_REVERSE_ACTION_SERVER_HPP_
