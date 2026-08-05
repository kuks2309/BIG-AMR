/**
 * @file trnav_motion_supervisor_node.cpp
 * @brief Motion source activator — calls trnav_motion_mux SelectMotionSource service
 *
 * Role: Service client only. Calls /select_motion_source once at boot
 *       to activate the configured default motion source.
 *
 * NOT a safety watchdog. This node does NOT publish /safe_to_move.
 * /safe_to_move is published by the separate package:
 *   src/Safety/amr_safety_watchdog/ (amr_safety_watchdog_node)
 *
 * See:
 *   - src/Control-Abstract/docs/trnav_motion_mux_architecture.md
 *   - src/Control-Abstract/docs/amr_safety_watchdog_architecture.md
 */

#include <trnav_msgs/srv/select_motion_source.hpp>
#include <chrono>
#include <memory>
#include <rclcpp/rclcpp.hpp>

using namespace std::chrono_literals;

class MotionSupervisorNode : public rclcpp::Node
{
  public:
    MotionSupervisorNode() : Node("trnav_motion_supervisor")
    {
        target_id_ = this->declare_parameter<int>("target_source_id", 1);
        service_name_ = this->declare_parameter<std::string>("target_service", "/select_motion_source");
        retries_ = this->declare_parameter<int>("call_retry_count", 3);
        retry_ms_ = this->declare_parameter<int>("call_retry_interval_ms", 1000);

        client_ = this->create_client<trnav_msgs::srv::SelectMotionSource>(service_name_);

        timer_ = this->create_wall_timer(std::chrono::milliseconds(retry_ms_), [this]() { this->tryCall(); });
    }

  private:
    void tryCall()
    {
        if (done_)
            return;
        if (!client_->service_is_ready())
        {
            if (++attempts_ >= retries_)
            {
                RCLCPP_ERROR(get_logger(), "Service %s not available after %d attempts, giving up",
                             service_name_.c_str(), retries_);
                timer_->cancel();
                done_ = true;
                return;
            }
            RCLCPP_INFO(get_logger(), "Waiting for %s service... attempt %d/%d", service_name_.c_str(), attempts_,
                        retries_);
            return;
        }
        auto req = std::make_shared<trnav_msgs::srv::SelectMotionSource::Request>();
        req->source_id = static_cast<uint8_t>(target_id_);
        auto future = client_->async_send_request(
            req, [this](rclcpp::Client<trnav_msgs::srv::SelectMotionSource>::SharedFuture resp) {
                auto r = resp.get();
                if (r->success)
                {
                    RCLCPP_INFO(get_logger(), "Source %d activated: %s", target_id_, r->message.c_str());
                }
                else
                {
                    RCLCPP_WARN(get_logger(), "Activation failed: %s", r->message.c_str());
                }
            });
        done_ = true;
        timer_->cancel();
    }

    rclcpp::Client<trnav_msgs::srv::SelectMotionSource>::SharedPtr client_;
    rclcpp::TimerBase::SharedPtr timer_;
    int target_id_;
    std::string service_name_;
    int retries_;
    int retry_ms_;
    int attempts_{0};
    bool done_{false};
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<MotionSupervisorNode>());
    rclcpp::shutdown();
    return 0;
}
