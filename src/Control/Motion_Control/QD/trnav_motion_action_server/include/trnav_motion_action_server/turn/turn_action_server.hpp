#ifndef AMR_MOTION_ACTION_SERVER__TURN__TURN_ACTION_SERVER_HPP_
#define AMR_MOTION_ACTION_SERVER__TURN__TURN_ACTION_SERVER_HPP_

#include "trnav_interfaces/action/amr_motion_turn.hpp"
#include "trnav_msgs/srv/select_motion_source.hpp"
#include "trnav_motion_core/action_mutex.hpp"
#include "trnav_motion_qd/qd_action_server_base.hpp"
#include "trnav_motion_core/motion_profile.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"
#include <memory>

namespace trnav_motion_action_server::turn
{

class TurnActionServer : public trnav::motion::qd::QdActionServerBase<trnav_interfaces::action::AMRMotionTurn>
{
  public:
    using Turn = trnav_interfaces::action::AMRMotionTurn;

    explicit TurnActionServer(rclcpp::Node::SharedPtr node, trnav_motion_core::ActionMutex action_mutex);

  protected:
    bool validateGoal(std::shared_ptr<const Turn::Goal> goal) override;
    void execute(std::shared_ptr<GoalHandle> goal_handle) override;

  private:
    // mux active source 전환 — execute() 진입 시 호출. action server 가 자기 source_id 책임 (정공법).
    rclcpp::Client<trnav_msgs::srv::SelectMotionSource>::SharedPtr select_source_client_;
    int motion_source_id_{5};  // turn = 5

    // Turn precision parameters (shared with Spin, via safeParam)
    double imu_deadband_rad_{0.001};
    double min_speed_dps_{2.0};
    double fine_correction_threshold_deg_{0.3};
    double fine_correction_speed_dps_{3.0};
    double fine_correction_timeout_sec_{3.0};
    int settling_delay_ms_{200};
};

} // namespace trnav_motion_action_server::turn

#endif // AMR_MOTION_ACTION_SERVER__TURN__TURN_ACTION_SERVER_HPP_
