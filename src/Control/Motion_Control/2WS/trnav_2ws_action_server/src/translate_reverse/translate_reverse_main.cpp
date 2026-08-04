#include <atomic>
#include <memory>

#include "trnav_2ws_action_server/translate_reverse/translate_reverse_action_server.hpp"
#include "trnav_2ws_core/action_mutex.hpp"
#include "rclcpp/rclcpp.hpp"

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("amr_translate_reverse_node");
    auto action_mutex = std::make_shared<std::atomic<bool>>(false);
    auto translate_server =
        std::make_shared<trnav_2ws_action_server::translate_reverse::TranslateReverseActionServer>(node, action_mutex);
    RCLCPP_INFO(node->get_logger(),
                "amr_translate_reverse_node started "
                "(action: /amr_motion_translate_reverse_abstract, publish: /motion/wheel_cmd/translate_reverse)");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
