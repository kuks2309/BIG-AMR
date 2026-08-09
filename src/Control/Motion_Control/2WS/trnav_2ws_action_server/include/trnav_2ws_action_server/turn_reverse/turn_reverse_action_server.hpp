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

    // Turn precision parameters (전진판과 같은 yaml 키를 쓴다)
    double imu_deadband_rad_{0.001};
    double min_speed_dps_{2.0};
    double fine_correction_threshold_deg_{0.3};
    double fine_correction_speed_dps_{3.0};
    double fine_correction_timeout_sec_{3.0};
    int settling_delay_ms_{200};
};

} // namespace trnav_2ws_action_server::turn_reverse

#endif // AMR_MOTION_ACTION_SERVER__TURN_REVERSE__TURN_REVERSE_ACTION_SERVER_HPP_
