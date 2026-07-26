#include <atomic>
#include <memory>

#include "trnav_motion_action_server/mpc/mpc_action_server.hpp"
#include "trnav_motion_core/action_mutex.hpp"
#include "rclcpp/rclcpp.hpp"

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("amr_mpc_node");
    auto action_mutex = std::make_shared<std::atomic<bool>>(false);
    auto pp_server =
        std::make_shared<trnav_motion_action_server::mpc::MpcActionServer>(node, action_mutex);
    RCLCPP_INFO(node->get_logger(),
                "amr_mpc_node started "
                "(action: /amr_motion_mpc_abstract, publish: /motion/wheel_cmd/mpc)");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
