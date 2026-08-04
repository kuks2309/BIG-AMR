#include "amr_motor_cmd_translator/amr_motor_cmd_translator_node.hpp"
#include <rclcpp/rclcpp.hpp>

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<amr_motor_cmd_translator::MotorCmdTranslator>());
    rclcpp::shutdown();
    return 0;
}
