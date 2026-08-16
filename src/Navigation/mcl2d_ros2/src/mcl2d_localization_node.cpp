// mcl2d_ros2 — 2D MCL 위치추정 ROS2 노드. 프레임워크-독립 코어(mcl2d_core)를 rclcpp 로 감싼다.
//   구독: scan (병합 스캔, sensor_msgs/LaserScan, BEST_EFFORT) · odom (nav_msgs/Odometry, BEST_EFFORT)
//         initialpose (geometry_msgs/PoseWithCovarianceStamped) — 런타임 재초기화
//   발행: mcl_pose (geometry_msgs/PoseWithCovarianceStamped) · TF **map→odom** (map→base_link 아님)
//   맵  : 파라미터 map_path(.smap). 비-ROS 어댑터와 같은 코어를 쓰므로 결과가 배관에 의존하지 않는다.
#include <cmath>
#include <memory>
#include <optional>

#include "geometry_msgs/msg/transform_stamped.hpp"
#include "mcl2d_core/motion_model.hpp" // normalizeAngle
#include "mcl2d_localizer.hpp"
#include "mcl2d_map/smap.hpp"
#include "mcl2d_ros2/conversions.hpp"
#include "rclcpp/rclcpp.hpp"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_broadcaster.h"
#include "tf2_ros/transform_listener.h"

using namespace mcl2d;

// z·roll·pitch 는 2D 추정기가 다루지 않는다. REP-105 관례대로 "미지원" 을 큰 분산으로 표시한다.
constexpr double kUnsupportedAxisVar = 1e6;

class Mcl2dLocalizationNode : public rclcpp::Node
{
  public:
    Mcl2dLocalizationNode() : rclcpp::Node("mcl2d_localization")
    {
        const std::string map_path = declare_parameter<std::string>("map_path", "");
        const double init_x = declare_parameter<double>("init_x", 0.0);
        const double init_y = declare_parameter<double>("init_y", 0.0);
        const double init_theta = declare_parameter<double>("init_theta", 0.0);
        map_frame_ = declare_parameter<std::string>("map_frame", "map");
        odom_frame_ = declare_parameter<std::string>("odom_frame", "odom");
        base_frame_ = declare_parameter<std::string>("base_frame", "base_link");
        publish_tf_ = declare_parameter<bool>("publish_tf", true);

        // 코어 파라미터는 **일부만** 노출한다. 대부분은 원본 libMCLoc 대조로 고정된 충실도 값이라
        //   임의로 열면 그 기준선이 흔들린다. 여기 연 것은 처리율 손잡이(표본 수·빔 수)와
        //   현장 조정이 필요한 게이트뿐이다. 노드가 단일 스레드로 1코어를 포화시키므로
        //   표본 수·빔 수가 곧 처리율이다.
        declareTuned("init_particle_number", params_.init_particle_number);
        declareTuned("min_particle_number", params_.min_particle_number);
        declareTuned("max_particle_number", params_.max_particle_number);
        declareTuned("beams_used", params_.beams_used);
        declareTuned("motor_stop_threshold", params_.motor_stop_threshold);
        declareTuned("stop_confidence", params_.stop_confidence);
        declareTuned("init_dist_scatter", params_.init_dist_scatter);
        declareTuned("init_angle_scatter", params_.init_angle_scatter);

        // 파라미터는 노드가 단일 소유한다 — 로컬라이저에 넘긴 것과 정지 판정에 쓰는 것이 갈리지 않도록.
        //   위 declareTuned 가 params_ 를 먼저 확정한 뒤에 생성해야 로컬라이저가 같은 값을 받는다.
        loc_ = std::make_unique<Mcl2dLocalizer>(params_, /*seed=*/17);

        // 맵이 없으면 **기동을 실패시킨다.** 빈 경로를 통과시키면 파티클필터가 생성되지 않아
        //   update() 가 Pose2D{} 를 돌려주고 노드는 (0,0,0) 을 계속 발행한다 —
        //   "맵 원점에 정지해 있다" 와 구분되지 않는 조용한 오동작이다.
        if (map_path.empty())
        {
            RCLCPP_FATAL(get_logger(), "map_path 는 필수 파라미터다 — .smap 경로를 지정하라");
            throw std::invalid_argument("map_path is required");
        }
        const SmapMap m = loadSmap(map_path);
        if (!m.valid)
        {
            RCLCPP_FATAL(get_logger(), "맵 적재 실패: %s (파일 없음·JSON 파손·장애물 0 중 하나)",
                         map_path.c_str());
            throw std::runtime_error("map load failed: " + map_path);
        }
        loc_->loadMap(m.obstacles, m.rssi_points);
        RCLCPP_INFO(get_logger(), "loaded map %s (%zu obstacles)", m.map_name.c_str(), m.obstacles.size());
        // 라이다 장착 자세 — [x0, y0, yaw0, ...] (m, rad), 스캔 순서와 같은 순서.
        // 기본값이 0 인 것은 병합 스캔을 받기 때문이다 — merger 가 이미 base_link 로 변환해 놓았으므로
        //   여기서 마운트를 또 적용하면 **이중 변환**이 된다.
        //   개별 스캔을 직접 먹일 때만 실제 장착값을 넘기고, 그때 값의 정본은 merger 캘리브레이션이다.
        const std::vector<double> kMergedNoTransform = {0.0, 0.0, 0.0};
        const auto mount_flat = declare_parameter<std::vector<double>>("laser_mounts", kMergedNoTransform);
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
        // odom→base_link 를 조회하려고 둔다. 측위는 map→odom 만 내므로 base_link 의 부모가
        //   둘이 되지 않는다(publishMapToOdom 참조).
        tf_buffer_ = std::make_unique<tf2_ros::Buffer>(get_clock());
        tf_listener_ = std::make_unique<tf2_ros::TransformListener>(*tf_buffer_);
        // 오도는 BEST_EFFORT 로 구독한다 — icp_odometry(rtabmap_odom)가 `qos` 파라미터를 발행에도
        //   적용해 odom 을 BEST_EFFORT 로 내보내기 때문이다. RELIABLE 로 구독하면
        //   offered < requested 라 **한 건도 전달되지 않는다**(조용히 끊긴다).
        //   BEST_EFFORT 구독자는 RELIABLE 발행자와도 연결되므로 이쪽이 항상 넓다.
        rclcpp::QoS odom_qos(20);
        odom_qos.best_effort();
        sub_odom_ = create_subscription<nav_msgs::msg::Odometry>(
            "odom", odom_qos, [this](nav_msgs::msg::Odometry::SharedPtr m) { onOdom(*m); });
        // RViz2 의 "2D Pose Estimate" 가 내는 표준 토픽. 기동 후 유일한 재초기화 경로다 —
        //   init_* 파라미터는 기동 시 1회만 적용되므로 위치를 잃으면 이 토픽으로만 되돌릴 수 있다.
        sub_init_ = create_subscription<geometry_msgs::msg::PoseWithCovarianceStamped>(
            "initialpose", 10,
            [this](geometry_msgs::msg::PoseWithCovarianceStamped::SharedPtr m) { onInitialPose(*m); });
        // 병합 스캔 **하나만** 구독한다. 라이다는 전·후 2대지만 base_link 변환은 dual_laser_merger 가
        //   자기 캘리브레이션으로 수행하므로, 이 노드가 또 변환하면 두 곳이 서로 다른 값으로 같은
        //   변환을 하게 된다. 변환 규약을 merger 한 곳에 둔다 — 라이다 대수·배치가 바뀌어도 이 노드는
        //   손대지 않는다.
        // QoS 는 위 odom 과 같은 이유로 BEST_EFFORT 다 — merger 가 SensorDataQoS 로 발행한다.
        const rclcpp::QoS scan_qos = rclcpp::SensorDataQoS();
        sub_scan_ = create_subscription<sensor_msgs::msg::LaserScan>(
            "scan", scan_qos, [this](sensor_msgs::msg::LaserScan::SharedPtr m) { scan_ = fromRosScan(*m); });
    }

  private:
    // 코어 파라미터 하나를 ROS 파라미터로 노출한다. 기본값은 코어가 들고 있는 충실도 값이라
    //   지정하지 않으면 거동이 그대로다. 지정해서 값이 갈리면 WARN 을 남긴다 —
    //   결과를 나중에 해석할 때 무엇이 기준과 달랐는지 로그만 보고 알 수 있어야 한다.
    template <typename T> void declareTuned(const std::string &name, T &field)
    {
        const T fidelity = field;
        field = declare_parameter<T>(name, fidelity);
        if (field != fidelity)
        {
            RCLCPP_WARN(get_logger(), "%s = %s (이식 기준값 %s 에서 변경 — 충실도 기준선 이탈)",
                        name.c_str(), std::to_string(field).c_str(), std::to_string(fidelity).c_str());
        }
    }

    // 정지 판정. 원본은 오도 메시지의 is_stop 플래그를 쓰지만(DoMoveAction @0x3d7d13 의 kMove 생략 분기)
    //   nav_msgs/Odometry 에는 그 필드가 없어 여기서 만들어 낸다.
    //   **pose 증분이 1차 근거**이고 twist 는 보조다 — twist 는 선택 필드라 채우지 않는 발행자에서
    //   0 으로 오는데, 그것을 믿으면 항상 정지로 판정해 예측(kMove)이 영구 생략된다.
    bool isStopped(const nav_msgs::msg::Odometry &o, const Pose2D &cur, double dt) const
    {
        if (dt > 1e-6 && prev_odom_)
        {
            const double v = std::hypot(cur.x - prev_odom_->x, cur.y - prev_odom_->y) / dt;
            const double w = std::fabs(normalizeAngle(cur.theta - prev_odom_->theta)) / dt;
            return v < params_.motor_stop_threshold && w < params_.motor_stop_threshold;
        }
        // dt 를 못 구할 때만(스탬프 0·역행) twist 로 폴백한다.
        //   전부 0 인 twist 는 '정지' 가 아니라 '미채움' 으로 보고 이동으로 취급한다.
        const double v = std::hypot(o.twist.twist.linear.x, o.twist.twist.linear.y);
        const double w = std::fabs(o.twist.twist.angular.z);
        if (v == 0.0 && w == 0.0)
            return false;
        return v < params_.motor_stop_threshold && w < params_.motor_stop_threshold;
    }

    // RViz2 "2D Pose Estimate" → /initialpose. 파티클필터를 그 자세 주변으로 재초기화한다.
    void onInitialPose(const geometry_msgs::msg::PoseWithCovarianceStamped &m)
    {
        // 좌표계가 다르면 값이 그대로 다른 위치를 가리킨다. 변환하지 않고 거부한다 —
        //   조용히 받아들이면 "왜 엉뚱한 곳으로 갔는지" 를 추적할 수 없다.
        if (!m.header.frame_id.empty() && m.header.frame_id != map_frame_)
        {
            RCLCPP_WARN(get_logger(), "initialpose 프레임이 %s 다 — 이 노드는 %s 기준만 받는다(무시)",
                        m.header.frame_id.c_str(), map_frame_.c_str());
            return;
        }
        const Pose2D p{m.pose.pose.position.x, m.pose.pose.position.y,
                       yawFromQuat(m.pose.pose.orientation.z, m.pose.pose.orientation.w)};
        loc_->setInitialPose(p);
        // 오도 기준점도 버린다 — 새 자세에 옛 오도 증분을 얹으면 첫 주기에 헛된 예측이 들어간다.
        //
        // ⚠ 이 한 줄은 **미판정이다.** 반대 선택(기준점 유지)도 성립한다:
        //     버린다 — 한 주기 예측을 잃는 대신, 오도가 멎었다 재개할 때 생기는 가짜 대증분을 막는다.
        //     둔다   — 정상 흐름에서는 증분이 이미 작아 잃는 것이 없다.
        //   어느 쪽이 나은지 실측으로 가린 적이 없다. 확정된 설계로 인용하지 말 것.
        prev_odom_.reset();
        prev_stamp_.reset();
        RCLCPP_INFO(get_logger(), "initialpose 적용: x=%.3f y=%.3f yaw=%.4f rad (%.2f deg)", p.x, p.y, p.theta,
                    p.theta * 180.0 / M_PI);
    }

    void onOdom(const nav_msgs::msg::Odometry &o)
    {
        const Pose2D cur = fromRosOdom(o);
        const rclcpp::Time stamp(o.header.stamp);
        if (!prev_odom_ || !scan_)
        {
            // 첫 샘플이거나 아직 스캔이 없다 — 기준만 세우고 나간다.
            //   두 경로가 같은 상태를 남겨야 다음 주기 dt 가 어긋나지 않는다.
            prev_odom_ = cur;
            prev_stamp_ = stamp;
            return;
        }

        const double dt = prev_stamp_ ? std::max(0.0, (stamp - *prev_stamp_).seconds()) : 0.0;
        const bool stopped = isStopped(o, cur, dt);

        std::vector<LaserScan> scans = {*scan_};
        const Pose2D est = loc_->update(*prev_odom_, cur, scans, stopped, dt);
        prev_odom_ = cur;
        prev_stamp_ = stamp;

        // 산포 모드 진단. 임계와 우도의 스케일 정합이 미검증이라(debt-031) 신뢰도 높음 모드가
        //   실제로는 선택되지 않을 수 있다 — 어느 모드가 도는지·우도가 얼마인지를 남겨야
        //   임계를 환산할 근거가 쌓인다.
        const ExtraMoveParams &em = loc_->lastExtraMove();
        RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 5000,
                             "mode=%d radius=%.3fm angle=%.4frad w=%.4f (BPTT=%.2f) stopped=%d",
                             em.mode, em.radius, em.angle, loc_->lastModeLikelihood(),
                             params_.best_particle_tolerant_threshold, stopped ? 1 : 0);

        auto msg = toRosPose(est);
        msg.header.stamp = o.header.stamp; // 관측 시각을 전파한다 — 발행 시각(now)으로 덮으면 소비자가 지연을 못 본다
        msg.header.frame_id = map_frame_;
        // 공분산을 비워 두면 소비자가 "불확실도 0" 으로 읽으므로 채운다.
        //   신뢰도(평균 우도)가 낮을수록 크게 잡는다. ⚠ 이 값은 **순서만 의미 있는 상대 지표**다 —
        //   표준편차로 환산하거나 필터 게인으로 쓰지 말 것.
        //   z·roll·pitch 는 이 추정기가 다루지 않으므로 큰 값으로 미지원을 표시한다.
        const double conf = std::max(loc_->confidence(), 1e-6);
        const double var_xy = params_.init_dist_scatter * params_.init_dist_scatter * (params_.stop_confidence / conf);
        const double var_yaw = params_.extra_move_angle * params_.extra_move_angle * (params_.stop_confidence / conf);
        msg.pose.covariance[0] = var_xy;   // x
        msg.pose.covariance[7] = var_xy;   // y
        msg.pose.covariance[35] = var_yaw; // yaw
        msg.pose.covariance[14] = kUnsupportedAxisVar;
        msg.pose.covariance[21] = kUnsupportedAxisVar;
        msg.pose.covariance[28] = kUnsupportedAxisVar;
        pub_->publish(msg);

        if (publish_tf_)
            publishMapToOdom(est, o.header.stamp);
    }

    // map→odom **만** 발행한다. map→base_link 를 직접 내면 오도메트리 노드가 이미 내고 있는
    //   odom→base_link 와 부모가 겹쳐 TF 트리가 깨진다 — 측위는 보정항만, base_link 의 부모는
    //   오도메트리가 소유한다.
    //   map→odom = (map→base) ∘ (odom→base)⁻¹ 를 2D 로 직접 계산한다.
    void publishMapToOdom(const Pose2D &est, const builtin_interfaces::msg::Time &stamp)
    {
        geometry_msgs::msg::TransformStamped ob;
        try
        {
            // 최신 것으로 조회한다(TimePointZero). 스캔·오도 스탬프가 서로 어긋나도 끊기지 않지만,
            //   그만큼 이 보정항은 정확히 est 시각의 것이 아니다.
            ob = tf_buffer_->lookupTransform(odom_frame_, base_frame_, tf2::TimePointZero);
        }
        catch (const tf2::TransformException &e)
        {
            // odom→base_link 가 없으면 보정항을 만들 수 없다. map→base_link 로 폴백하지 **않는다** —
            //   그 폴백이 바로 위에서 말한 부모 중복을 만든다. 조용히 넘기지 말고 주기적으로 알린다.
            RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000,
                                 "%s→%s TF 없음 — map→odom 미발행 (%s)", odom_frame_.c_str(),
                                 base_frame_.c_str(), e.what());
            return;
        }

        const double ox = ob.transform.translation.x;
        const double oy = ob.transform.translation.y;
        const double oyaw = yawFromQuat(ob.transform.rotation.z, ob.transform.rotation.w);

        const double th = normalizeAngle(est.theta - oyaw);
        const double c = std::cos(th), s = std::sin(th);

        geometry_msgs::msg::TransformStamped tf;
        tf.header.stamp = stamp;
        tf.header.frame_id = map_frame_;
        tf.child_frame_id = odom_frame_;
        tf.transform.translation.x = est.x - (c * ox - s * oy);
        tf.transform.translation.y = est.y - (s * ox + c * oy);
        tf.transform.rotation.z = std::sin(th * 0.5);
        tf.transform.rotation.w = std::cos(th * 0.5);
        tf_->sendTransform(tf);
    }

    Mcl2dParams params_{}; // 로컬라이저와 정지 판정이 공유하는 단일 소유 파라미터
    std::unique_ptr<Mcl2dLocalizer> loc_;
    rclcpp::Publisher<geometry_msgs::msg::PoseWithCovarianceStamped>::SharedPtr pub_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr sub_odom_;
    rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr sub_scan_;
    rclcpp::Subscription<geometry_msgs::msg::PoseWithCovarianceStamped>::SharedPtr sub_init_;
    std::unique_ptr<tf2_ros::TransformBroadcaster> tf_;
    std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
    std::unique_ptr<tf2_ros::TransformListener> tf_listener_;
    std::optional<Pose2D> prev_odom_;
    std::optional<rclcpp::Time> prev_stamp_;
    std::optional<LaserScan> scan_;
    std::string map_frame_, odom_frame_, base_frame_;
    bool publish_tf_ = true;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<Mcl2dLocalizationNode>());
    rclcpp::shutdown();
    return 0;
}
