// mcl2d_ros2 — 2D MCL 위치추정 ROS2 노드. 프레임워크-독립 코어(mcl2d_core)를 rclcpp로 감싼다.
//   구독: /scan_front, /scan_rear (sensor_msgs/LaserScan), /odom (nav_msgs/Odometry)
//   발행: /mcl_pose (geometry_msgs/PoseWithCovarianceStamped) + TF(map→base_link)
//   맵  : 파라미터 map_path(.smap) 로드. non-ROS 어댑터와 동일 mcl2d_core 사용.
#include <cmath>
#include <memory>
#include <optional>

#include "geometry_msgs/msg/transform_stamped.hpp"
#include "mcl2d_localizer.hpp"
#include "mcl2d_map/smap.hpp"
#include "mcl2d_ros2/conversions.hpp"
#include "rclcpp/rclcpp.hpp"
#include "tf2_ros/transform_broadcaster.h"

using namespace mcl2d;

class Mcl2dLocalizationNode : public rclcpp::Node
{
  public:
    Mcl2dLocalizationNode() : rclcpp::Node("mcl2d_localization")
    {
        const std::string map_path = declare_parameter<std::string>("map_path", "");
        const double init_x = declare_parameter<double>("init_x", 0.0);
        const double init_y = declare_parameter<double>("init_y", 0.0);
        const double init_theta = declare_parameter<double>("init_theta", 0.0);

        loc_ = std::make_unique<Mcl2dLocalizer>(Mcl2dParams{}, /*seed=*/17);
        if (!map_path.empty())
        {
            SmapMap m = loadSmap(map_path);
            if (m.valid)
            {
                loc_->loadMap(m.obstacles, m.rssi_points);
                RCLCPP_INFO(get_logger(), "loaded map %s (%zu obstacles)", m.map_name.c_str(), m.obstacles.size());
            }
            else
            {
                RCLCPP_ERROR(get_logger(), "map load FAIL: %s", map_path.c_str());
            }
        }
        // Roll_A084 듀얼 라이다
        loc_->setLasers({{0.879, -0.579, -M_PI / 4}, {-0.879, 0.579, 3 * M_PI / 4}});
        loc_->setInitialPose({init_x, init_y, init_theta});

        pub_ = create_publisher<geometry_msgs::msg::PoseWithCovarianceStamped>("mcl_pose", 10);
        tf_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);
        sub_odom_ = create_subscription<nav_msgs::msg::Odometry>(
            "odom", 20, [this](nav_msgs::msg::Odometry::SharedPtr m) { onOdom(*m); });
        sub_front_ = create_subscription<sensor_msgs::msg::LaserScan>(
            "scan_front", 10, [this](sensor_msgs::msg::LaserScan::SharedPtr m) { front_ = fromRosScan(*m); });
        sub_rear_ = create_subscription<sensor_msgs::msg::LaserScan>(
            "scan_rear", 10, [this](sensor_msgs::msg::LaserScan::SharedPtr m) { rear_ = fromRosScan(*m); });
    }

  private:
    void onOdom(const nav_msgs::msg::Odometry &o)
    {
        const Pose2D cur = fromRosOdom(o);
        if (!prev_odom_)
        {
            prev_odom_ = cur;
            return;
        }
        if (!front_ || !rear_)
        {
            prev_odom_ = cur;
            prev_stamp_ = rclcpp::Time(o.header.stamp);
            return;
        } // 스캔 대기

        // 원본은 오도 메시지의 is_stop 플래그를 쓴다(DoMoveAction 의 kMove 생략 분기). nav_msgs/Odometry 에는
        // 그 플래그가 없으므로 twist 크기를 MotorStopThreshold(원본 배포값 0.02)와 비교해 대체한다.
        const Mcl2dParams p{};
        const double v = std::hypot(o.twist.twist.linear.x, o.twist.twist.linear.y);
        const bool stopped = (v < p.motor_stop_threshold) && (std::fabs(o.twist.twist.angular.z) < p.motor_stop_threshold);
        const rclcpp::Time stamp(o.header.stamp);
        const double dt = prev_stamp_ ? std::max(0.0, (stamp - *prev_stamp_).seconds()) : 0.0;

        std::vector<LaserScan> scans = {*front_, *rear_};
        const Pose2D est = loc_->update(*prev_odom_, cur, scans, stopped, dt);
        prev_odom_ = cur;
        prev_stamp_ = stamp;

        auto msg = toRosPose(est);
        msg.header.stamp = now();
        msg.header.frame_id = "map";
        pub_->publish(msg);

        geometry_msgs::msg::TransformStamped tf;
        tf.header = msg.header;
        tf.child_frame_id = "base_link";
        tf.transform.translation.x = est.x;
        tf.transform.translation.y = est.y;
        tf.transform.rotation = msg.pose.pose.orientation;
        tf_->sendTransform(tf);
    }

    std::unique_ptr<Mcl2dLocalizer> loc_;
    rclcpp::Publisher<geometry_msgs::msg::PoseWithCovarianceStamped>::SharedPtr pub_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr sub_odom_;
    rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr sub_front_, sub_rear_;
    std::unique_ptr<tf2_ros::TransformBroadcaster> tf_;
    std::optional<Pose2D> prev_odom_;
    std::optional<rclcpp::Time> prev_stamp_;
    std::optional<LaserScan> front_, rear_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<Mcl2dLocalizationNode>());
    rclcpp::shutdown();
    return 0;
}
