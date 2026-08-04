#pragma once
#include <trnav_msgs/msg/wheel_set_array.hpp>
#include <trnav_msgs/srv/select_motion_source.hpp>
#include <atomic>
#include <memory>
#include <mutex>
#include <rclcpp/rclcpp.hpp>
#include <set>
#include <unordered_map>

namespace trnav_motion_mux
{

struct SourceEntry
{
    uint8_t id;
    std::string name;
    std::string topic;
    std::chrono::milliseconds timeout;
    rclcpp::Subscription<trnav_msgs::msg::WheelSetArray>::SharedPtr sub;
    trnav_msgs::msg::WheelSetArray::SharedPtr latest;
    rclcpp::Time last_stamp;
};

class MotionMuxNode : public rclcpp::Node
{
  public:
    MotionMuxNode();

  private:
    void loadSources();
    void validateSources(int default_source_id);
    void onSelectSource(const std::shared_ptr<trnav_msgs::srv::SelectMotionSource::Request> req,
                        std::shared_ptr<trnav_msgs::srv::SelectMotionSource::Response> res);

    rclcpp::Publisher<trnav_msgs::msg::WheelSetArray>::SharedPtr pub_;
    rclcpp::Service<trnav_msgs::srv::SelectMotionSource>::SharedPtr select_srv_;
    std::unordered_map<uint8_t, std::unique_ptr<SourceEntry>> sources_;
    std::atomic<uint8_t> active_id_{0};
    std::mutex latest_mutex_;
};

} // namespace trnav_motion_mux
