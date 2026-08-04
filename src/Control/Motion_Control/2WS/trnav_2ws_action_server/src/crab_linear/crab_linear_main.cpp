#include <atomic>
#include <memory>

#include "trnav_2ws_action_server/crab_linear/crab_linear_action_server.hpp"
#include "trnav_2ws_core/action_mutex.hpp"
#include "rclcpp/rclcpp.hpp"

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("amr_crab_linear_node");
    auto action_mutex = std::make_shared<std::atomic<bool>>(false);
    auto crab_linear_server =
        std::make_shared<trnav_2ws_action_server::crab_linear::CrabLinearActionServer>(node, action_mutex);
    RCLCPP_INFO(node->get_logger(),
                "amr_crab_linear_node started "
                "(action: /amr_motion_crab_linear_abstract, publish: /motion/wheel_cmd/crab_linear)");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
