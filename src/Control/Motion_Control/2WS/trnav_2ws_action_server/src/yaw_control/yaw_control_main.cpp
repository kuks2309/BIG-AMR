#include "trnav_2ws_action_server/yaw_control/yaw_control_action_server.hpp"
#include "trnav_2ws_core/action_mutex.hpp"
#include "rclcpp/rclcpp.hpp"

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("amr_yaw_control_node");
    auto action_mutex = std::make_shared<std::atomic<bool>>(false);
    auto server = std::make_shared<trnav_2ws_action_server::yaw_control::YawControlActionServer>(node, action_mutex);
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
