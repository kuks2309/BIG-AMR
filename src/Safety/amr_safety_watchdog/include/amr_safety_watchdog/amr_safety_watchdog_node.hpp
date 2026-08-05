// amr_safety_watchdog — publisher of /safe_to_move (std_msgs/Bool, 10Hz).
// NOT related to trnav_motion_supervisor. See amr_safety_watchdog_node.cpp for details.

#pragma once
#include <trnav_msgs/msg/safety_status.hpp>
#include <atomic>
#include <chrono>
#include <memory>
#include <mutex>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/bool.hpp>
#include <vector>

namespace amr_safety_watchdog
{

struct SafetySource
{
    std::string name;
    std::string topic;
    std::string type; // "bool" | "safety_status"
    bool enabled;
    bool invert;
    std::chrono::milliseconds timeout;
    rclcpp::SubscriptionBase::SharedPtr sub;
    std::atomic<bool> last_safe{false};
    rclcpp::Time last_stamp;
    std::mutex stamp_mutex;
};

class SafetyWatchdogNode : public rclcpp::Node
{
  public:
    SafetyWatchdogNode();

  private:
    void loadSources();
    void makeBoolSource(std::unique_ptr<SafetySource> &s);
    void makeSafetyStatusSource(std::unique_ptr<SafetySource> &s);
    void publishLoop();

    rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;
    std::vector<std::unique_ptr<SafetySource>> sources_;
    bool failsafe_on_boot_;
};

} // namespace amr_safety_watchdog
