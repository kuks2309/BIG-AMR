#include <atomic>
#include <memory>

#include "trnav_motion_action_server/mpc_reverse/mpc_reverse_action_server.hpp"
#include "trnav_motion_core/action_mutex.hpp"
#include "rclcpp/rclcpp.hpp"

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("amr_mpc_reverse_node");
    auto action_mutex = std::make_shared<std::atomic<bool>>(false);
    auto pp_rev_server =
        std::make_shared<trnav_motion_action_server::mpc_reverse::MpcReverseActionServer>(
            node, action_mutex);
    RCLCPP_INFO(node->get_logger(),
                "amr_mpc_reverse_node started "
                "(action: /amr_motion_mpc_reverse_abstract, "
                "publish: /motion/wheel_cmd/mpc_reverse)");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
