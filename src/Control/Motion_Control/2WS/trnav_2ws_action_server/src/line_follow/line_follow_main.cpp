#include "trnav_2ws_action_server/line_follow/line_follow_action_server.hpp"
#include "trnav_2ws_core/action_mutex.hpp"
#include "rclcpp/rclcpp.hpp"

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("amr_line_follow_node");
    auto action_mutex = std::make_shared<std::atomic<bool>>(false);
    auto server = std::make_shared<trnav_2ws_action_server::line_follow::LineFollowActionServer>(node, action_mutex);
    RCLCPP_INFO(node->get_logger(), "amr_line_follow_node started (action: /amr_motion_line_follow_abstract, "
                                    "publish: /motion/wheel_cmd/line_follow)");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
