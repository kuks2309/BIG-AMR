#include "rclcpp/rclcpp.hpp"
#include "translate_sim_odom/translate_sim_odom_node.hpp"
#include <memory>

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<translate_sim_odom::TranslateSimOdomNode>();
    RCLCPP_INFO(node->get_logger(),
                "translate_sim_odom_node ready (sub: /motor/wheel_cmd, "
                "pub: TF map->base_link + /rtabmap/localization_pose + /imu/data + /wheel_motor_state)");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
