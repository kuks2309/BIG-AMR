#include "trnav_2ws_action_server/spin/spin_action_server.hpp"
#include "trnav_2ws_core/action_mutex.hpp"
#include "rclcpp/rclcpp.hpp"
#include <atomic>
#include <memory>

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("amr_spin_node");
    auto action_mutex = std::make_shared<std::atomic<bool>>(false);
    auto spin_server = std::make_shared<trnav_2ws_action_server::spin::SpinActionServer>(node, action_mutex);
    RCLCPP_INFO(node->get_logger(),
                "amr_spin_node started (action: /amr_motion_spin_abstract, publish: /motion/wheel_cmd/spin)");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
