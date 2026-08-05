// SIL pose type adapter.
//
// 배경:
//   - translate_sim_odom_node 는 /rtabmap/localization_pose
//     (geometry_msgs::msg::PoseWithCovarianceStamped) 만 발행.
//   - LocalizationMonitor (trnav_motion_core) 는 /robot_pose
//     (geometry_msgs::msg::PoseStamped) 토픽 cache 만 사용 (TF lookup 없음).
//   - 실차에선 trnav_pose_publisher 가 map→base_link TF → /robot_pose
//     를 RELIABLE depth=10 으로 발행하지만, SIL 클로즈드 루프엔 해당 노드 없음.
//   - 본 어댑터는 SIL 전용으로 PoseWithCovariance → Pose 타입 변환만 수행하여
//     LocalizationMonitor 가 정상 동작하도록 /robot_pose 를 발행한다.
//
// QoS:
//   - sub /rtabmap/localization_pose : QoS(10).reliable() (translate_sim_odom
//     publisher 는 SensorDataQoS=BEST_EFFORT 이지만, ROS2 QoS 호환성 규칙상
//     RELIABLE sub 가 BEST_EFFORT pub 를 받지 못한다. 따라서 sub 측을
//     SensorDataQoS 로 맞춤).
//   - pub /robot_pose : QoS(10).reliable() (LocalizationMonitor pose_qos=0
//     default = RELIABLE depth=10, trnav_pose_publisher 와 동일).
//
// 기존 코드 영향 0 — 본 패키지는 SIL launch 에서만 포함된다.

#include <memory>

#include "geometry_msgs/msg/pose_stamped.hpp"
#include "geometry_msgs/msg/pose_with_covariance_stamped.hpp"
#include "rclcpp/rclcpp.hpp"

namespace sil_pose_adapter
{

class SilPoseAdapterNode : public rclcpp::Node
{
public:
    SilPoseAdapterNode() : rclcpp::Node("sil_pose_adapter_node")
    {
        // Publisher: /robot_pose RELIABLE depth=10
        // (LocalizationMonitor pose_qos=0 default 와 호환).
        pub_ = create_publisher<geometry_msgs::msg::PoseStamped>(
            "/robot_pose", rclcpp::QoS(10).reliable());

        // Subscriber: /rtabmap/localization_pose
        // translate_sim_odom_node 는 SensorDataQoS (BEST_EFFORT) 로 publish 하므로
        // sub 도 SensorDataQoS 로 호환성 맞춤.
        sub_ = create_subscription<geometry_msgs::msg::PoseWithCovarianceStamped>(
            "/rtabmap/localization_pose", rclcpp::SensorDataQoS(),
            [this](const geometry_msgs::msg::PoseWithCovarianceStamped::SharedPtr msg) {
                geometry_msgs::msg::PoseStamped out;
                out.header = msg->header;
                out.pose = msg->pose.pose;
                pub_->publish(out);
            });

        RCLCPP_INFO(get_logger(),
                    "sil_pose_adapter_node started "
                    "(sub: /rtabmap/localization_pose [SensorDataQoS], "
                    "pub: /robot_pose [RELIABLE depth=10])");
    }

private:
    rclcpp::Subscription<geometry_msgs::msg::PoseWithCovarianceStamped>::SharedPtr sub_;
    rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr pub_;
};

} // namespace sil_pose_adapter

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<sil_pose_adapter::SilPoseAdapterNode>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
