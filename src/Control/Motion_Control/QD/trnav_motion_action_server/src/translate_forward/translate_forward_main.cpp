#include <atomic>
#include <memory>

#include "trnav_motion_action_server/translate_forward/translate_forward_action_server.hpp"
#include "trnav_motion_core/action_mutex.hpp"
#include "rclcpp/rclcpp.hpp"

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("amr_translate_forward_node");
    auto action_mutex = std::make_shared<std::atomic<bool>>(false);
    auto translate_server =
        std::make_shared<trnav_motion_action_server::translate_forward::TranslateForwardActionServer>(node, action_mutex);
    RCLCPP_INFO(node->get_logger(),
                "amr_translate_forward_node started "
                "(action: /amr_motion_translate_forward_abstract, publish: /motion/wheel_cmd/translate_forward)");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
