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
        // 라이다 장착 자세 — [x0,y0,yaw0, x1,y1,yaw1, ...] (m, rad), update(scans) 순서와 일치.
        // 기본값은 이 기체(Foil_A082)의 Seer 컨트롤러 설정에서 읽은 값이다(2026-08-07,
        // 1500 robot_status_model_req → deviceTypes/laser: FrontLiDAR id0, RearLiDAR id1).
        //   FrontLiDAR  x 0.881676  y -0.578664  yaw -45°      ip 192.168.192.100:6060
        //   RearLiDAR   x -0.857    y  0.5971    yaw 135.29°   ip 192.168.192.101:6061
        // 둘 다 useForLocalization=true. 기체가 바뀌면 같은 조회로 값을 다시 받아 파라미터로 넘긴다.
        const std::vector<double> kFoilA082Mounts = {0.881676, -0.578664, -M_PI / 4,
                                                     -0.857, 0.5971, 135.29 * M_PI / 180.0};
        const auto mount_flat = declare_parameter<std::vector<double>>("laser_mounts", kFoilA082Mounts);
        if (mount_flat.size() < 3 || mount_flat.size() % 3 != 0)
        {
            RCLCPP_FATAL(get_logger(), "laser_mounts 는 3의 배수여야 한다(받은 값 %zu개) — [x,y,yaw] 반복",
                         mount_flat.size());
            throw std::invalid_argument("laser_mounts size must be a positive multiple of 3");
        }
        std::vector<LaserMount> mounts;
        for (std::size_t i = 0; i + 2 < mount_flat.size(); i += 3)
        {
            mounts.push_back({mount_flat[i], mount_flat[i + 1], mount_flat[i + 2]});
            RCLCPP_INFO(get_logger(), "laser[%zu] mount x=%.6f y=%.6f yaw=%.4f rad (%.3f deg)", i / 3,
                        mount_flat[i], mount_flat[i + 1], mount_flat[i + 2], mount_flat[i + 2] * 180.0 / M_PI);
        }
        loc_->setLasers(mounts);
        loc_->setInitialPose({init_x, init_y, init_theta});

        pub_ = create_publisher<geometry_msgs::msg::PoseWithCovarianceStamped>("mcl_pose", 10);
        tf_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);
        // 오도메트리는 BEST_EFFORT 로 구독한다. icp_odometry(rtabmap_odom)는 `qos` 파라미터를
        // 구독뿐 아니라 **발행에도** 적용해 /odom 을 BEST_EFFORT 로 내보내는데, 기본 RELIABLE 로
        // 구독하면 offered(BEST_EFFORT) < requested(RELIABLE) 라 한 건도 전달되지 않는다
        // (2026-08-02 실기 확인: "incompatible QoS ... No messages will be sent to it",
        //  `ros2 topic info /odom -v` → Reliability: BEST_EFFORT).
        // BEST_EFFORT 구독자는 RELIABLE 발행자와도 연결되므로 이쪽이 항상 넓다.
        rclcpp::QoS odom_qos(20);
        odom_qos.best_effort();
        sub_odom_ = create_subscription<nav_msgs::msg::Odometry>(
            "odom", odom_qos, [this](nav_msgs::msg::Odometry::SharedPtr m) { onOdom(*m); });
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

        // 산포 모드 진단 — 원본 MCLocUpdateMode 로그 대응. 모드 5(신뢰 높음)는 임계 0.8 이 원본 스케일
        //   값이라 우리 우도(보통 0.0x)에서는 선택되지 않을 수 있다(debt-031). 어느 모드가 실제로
        //   도는지·우도가 얼마인지를 남겨야 임계 환산의 근거가 쌓인다.
        const ExtraMoveParams &em = loc_->lastExtraMove();
        RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 5000,
                             "mode=%d radius=%.3fm angle=%.4frad w=%.4f (BPTT=%.2f) stopped=%d",
                             em.mode, em.radius, em.angle, loc_->lastModeLikelihood(),
                             params_.best_particle_tolerant_threshold, stopped ? 1 : 0);

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
