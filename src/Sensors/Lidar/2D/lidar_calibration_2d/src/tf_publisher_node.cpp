// Copyright 2025 T-Robotics
// Static TF publisher for 2D LiDAR frames.
// Reads sensor mounting info from config params and broadcasts:
//   base_link -> scan_front
//   base_link -> scan_rear
//   base_link -> scan_merged

#include <geometry_msgs/msg/transform_stamped.hpp>
#include <rclcpp/rclcpp.hpp>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_ros/static_transform_broadcaster.h>

#include <cmath>
#include <string>
#include <vector>

namespace lidar_calibration_2d
{

class TFPublisherNode : public rclcpp::Node
{
  public:
    explicit TFPublisherNode(const rclcpp::NodeOptions &options) : Node("lidar_tf_publisher", options)
    {
        // --- Read sensor mounting params ---
        front_tx_ = this->get_parameter_or<double>("front_tx", 0.0);
        front_ty_ = this->get_parameter_or<double>("front_ty", 0.0);
        front_tz_ = this->get_parameter_or<double>("front_tz", 0.2865);
        front_yaw_ = this->get_parameter_or<double>("front_yaw", 0.0);
        front_upside_down_ = this->get_parameter_or<bool>("front_upside_down", false);

        rear_tx_ = this->get_parameter_or<double>("rear_tx", 0.0);
        rear_ty_ = this->get_parameter_or<double>("rear_ty", 0.0);
        rear_tz_ = this->get_parameter_or<double>("rear_tz", 0.2865);
        rear_yaw_ = this->get_parameter_or<double>("rear_yaw", 0.0);
        rear_upside_down_ = this->get_parameter_or<bool>("rear_upside_down", false);

        front_frame_ = this->get_parameter_or<std::string>("front_frame", "scan_front");
        rear_frame_ = this->get_parameter_or<std::string>("rear_frame", "scan_rear");
        merged_frame_ = this->get_parameter_or<std::string>("merged_frame", "scan_merged");
        base_frame_ = this->get_parameter_or<std::string>("base_frame", "base_link");

        // --- Create broadcaster ---
        static_broadcaster_ = std::make_shared<tf2_ros::StaticTransformBroadcaster>(this);

        // --- Build and send transforms ---
        std::vector<geometry_msgs::msg::TransformStamped> transforms;

        // base_link -> scan_front
        transforms.push_back(
            make_tf(base_frame_, front_frame_, front_tx_, front_ty_, front_tz_, front_yaw_, front_upside_down_));

        // base_link -> scan_rear
        transforms.push_back(
            make_tf(base_frame_, rear_frame_, rear_tx_, rear_ty_, rear_tz_, rear_yaw_, rear_upside_down_));

        // base_link -> scan_merged (두 라이다 위치의 중간점, z는 front 기준)
        double merged_tx = (front_tx_ + rear_tx_) / 2.0;
        double merged_ty = (front_ty_ + rear_ty_) / 2.0;
        double merged_tz = (front_tz_ + rear_tz_) / 2.0;
        transforms.push_back(make_tf(base_frame_, merged_frame_, merged_tx, merged_ty, merged_tz, 0.0, false));

        static_broadcaster_->sendTransform(transforms);

        // --- Log ---
        double front_roll = front_upside_down_ ? M_PI : 0.0;
        double rear_roll = rear_upside_down_ ? M_PI : 0.0;

        RCLCPP_INFO(this->get_logger(),
                    "=== LiDAR TF Publisher ===\n"
                    "  %s -> %s: tx=%.4f ty=%.4f tz=%.4f yaw=%.2fdeg roll=%.2fdeg\n"
                    "  %s -> %s: tx=%.4f ty=%.4f tz=%.4f yaw=%.2fdeg roll=%.2fdeg\n"
                    "  %s -> %s: tx=%.4f ty=%.4f tz=%.4f (midpoint)",
                    base_frame_.c_str(), front_frame_.c_str(), front_tx_, front_ty_, front_tz_,
                    front_yaw_ * 180.0 / M_PI, front_roll * 180.0 / M_PI, base_frame_.c_str(), rear_frame_.c_str(),
                    rear_tx_, rear_ty_, rear_tz_, rear_yaw_ * 180.0 / M_PI, rear_roll * 180.0 / M_PI,
                    base_frame_.c_str(), merged_frame_.c_str(), merged_tx, merged_ty, merged_tz);
    }

  private:
    geometry_msgs::msg::TransformStamped make_tf(const std::string &parent, const std::string &child, double tx,
                                                 double ty, double tz, double yaw, bool upside_down)
    {
        geometry_msgs::msg::TransformStamped t;
        t.header.stamp = this->now();
        t.header.frame_id = parent;
        t.child_frame_id = child;
        t.transform.translation.x = tx;
        t.transform.translation.y = ty;
        t.transform.translation.z = tz;

        tf2::Quaternion q;
        double roll = upside_down ? M_PI : 0.0;
        q.setRPY(roll, 0.0, yaw);
        t.transform.rotation.x = q.x();
        t.transform.rotation.y = q.y();
        t.transform.rotation.z = q.z();
        t.transform.rotation.w = q.w();

        return t;
    }

    // Parameters
    double front_tx_, front_ty_, front_tz_, front_yaw_;
    bool front_upside_down_;
    double rear_tx_, rear_ty_, rear_tz_, rear_yaw_;
    bool rear_upside_down_;
    std::string front_frame_, rear_frame_, merged_frame_, base_frame_;

    std::shared_ptr<tf2_ros::StaticTransformBroadcaster> static_broadcaster_;
};

} // namespace lidar_calibration_2d

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);

    rclcpp::NodeOptions options;
    options.automatically_declare_parameters_from_overrides(true);

    auto node = std::make_shared<lidar_calibration_2d::TFPublisherNode>(options);

    rclcpp::spin(node);
    if (rclcpp::ok())
    {
        rclcpp::shutdown();
    }
    return 0;
}
