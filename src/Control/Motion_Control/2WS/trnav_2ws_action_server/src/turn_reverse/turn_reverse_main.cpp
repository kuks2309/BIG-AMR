#include "trnav_2ws_action_server/turn_reverse/turn_reverse_action_server.hpp"
#include "trnav_2ws_core/action_mutex.hpp"
#include "rclcpp/rclcpp.hpp"
#include <atomic>
#include <memory>

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("amr_turn_reverse_node");
    auto action_mutex = std::make_shared<std::atomic<bool>>(false);
    auto server =
        std::make_shared<trnav_2ws_action_server::turn_reverse::TurnReverseActionServer>(node, action_mutex);
    RCLCPP_INFO(node->get_logger(), "amr_turn_reverse_node started (action: "
                                    "/amr_motion_turn_reverse_abstract, publish: /motion/wheel_cmd/turn_reverse)");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
