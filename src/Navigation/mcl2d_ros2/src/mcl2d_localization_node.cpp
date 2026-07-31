// mcl2d_ros2 — 2D MCL 위치추정 ROS2 노드. 프레임워크-독립 코어(mcl2d_core)를 rclcpp로 감싼다.
//   구독: /scan_front, /scan_rear (sensor_msgs/LaserScan), /odom (nav_msgs/Odometry)
//   발행: /mcl_pose (geometry_msgs/PoseWithCovarianceStamped) + TF(map→base_link)
//   맵  : 파라미터 map_path(.smap) 로드. non-ROS 어댑터와 동일 mcl2d_core 사용.
#include <cmath>
#include <memory>
#include <optional>

#include "geometry_msgs/msg/transform_stamped.hpp"
#include "mcl2d_core/motion_model.hpp" // normalizeAngle
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

        // 파라미터는 노드가 단일 소유한다 — 로컬라이저에 넘긴 것과 정지 판정에 쓰는 것이 갈리지 않도록.
        loc_ = std::make_unique<Mcl2dLocalizer>(params_, /*seed=*/17);
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
    // 정지 판정. 원본은 오도 메시지의 is_stop 플래그를 쓰지만(DoMoveAction @0x3d7d13 의 kMove 생략 분기)
    //   nav_msgs/Odometry 에는 그 필드가 없다. **pose 증분을 1차 근거**로 쓰고 twist 는 보조로만 쓴다 —
    //   twist 는 선택 필드라 채우지 않는 발행자에서 0 으로 오고, twist 만 믿으면 항상 정지로 판정해
    //   예측(kMove)이 영구 생략된다(코드리뷰 2026-07-31 H1).
    bool isStopped(const nav_msgs::msg::Odometry &o, const Pose2D &cur, double dt) const
    {
        if (dt > 1e-6 && prev_odom_)
        {
            const double v = std::hypot(cur.x - prev_odom_->x, cur.y - prev_odom_->y) / dt;
            const double w = std::fabs(normalizeAngle(cur.theta - prev_odom_->theta)) / dt;
            return v < params_.motor_stop_threshold && w < params_.motor_stop_threshold;
        }
        // dt 를 못 구할 때만(스탬프 0·역행) twist 폴백. 전부 0 인 twist 는 '미채움'으로 보고 이동으로 취급한다.
        const double v = std::hypot(o.twist.twist.linear.x, o.twist.twist.linear.y);
        const double w = std::fabs(o.twist.twist.angular.z);
        if (v == 0.0 && w == 0.0)
            return false;
        return v < params_.motor_stop_threshold && w < params_.motor_stop_threshold;
    }

    void onOdom(const nav_msgs::msg::Odometry &o)
    {
        const Pose2D cur = fromRosOdom(o);
        const rclcpp::Time stamp(o.header.stamp);
        if (!prev_odom_ || !front_ || !rear_)
        {
            // 첫 샘플이거나 스캔 대기 — 기준만 세우고 반환한다(두 경로가 같은 상태를 남겨야 dt 가 어긋나지 않는다).
            prev_odom_ = cur;
            prev_stamp_ = stamp;
            return;
        }

        const double dt = prev_stamp_ ? std::max(0.0, (stamp - *prev_stamp_).seconds()) : 0.0;
        const bool stopped = isStopped(o, cur, dt);

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

    Mcl2dParams params_{}; // 로컬라이저와 정지 판정이 공유하는 단일 소유 파라미터
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
