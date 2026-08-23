// 벽 3면 라이다 정밀 측위 ROS2 어댑터.
// 구독 scan(LaserScan) → 코어(wall_localizer_core) → 발행 wall_pose(PoseStamped,
// frame_id=station_frame, base_frame 의 스테이션 내 자세) + wall_localizer/diagnostics.
// 유효 해(OK/DEGRADED)일 때만 자세를 발행한다 — LOST 시 침묵해야 소비자
// (trnav_2ws_core::LocalizationMonitor)의 신선도 감시가 자연히 작동한다.

#include <cmath>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include "diagnostic_msgs/msg/diagnostic_array.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_listener.h"
#include "visualization_msgs/msg/marker_array.hpp"

#include "wall_localizer_core/wall_localizer.hpp"

namespace
{

constexpr double kDegToRad = M_PI / 180.0;

std::string statusText(wall_localizer_core::Status s)
{
    switch (s)
    {
    case wall_localizer_core::Status::OK:
        return "OK";
    case wall_localizer_core::Status::DEGRADED:
        return "DEGRADED";
    default:
        return "LOST";
    }
}

}  // namespace

class WallLocalizerNode : public rclcpp::Node
{
  public:
    WallLocalizerNode() : Node("wall_localizer")
    {
        station_frame_ = declare_parameter<std::string>("station_frame", "station");
        base_frame_ = declare_parameter<std::string>("base_frame", "base_link");

        walls_ = loadWallsFromParams();

        // 스테이션 진입 시 로봇 초기 추정 (대응 게이트 시드 + 벽 법선 정향 기준)
        initial_pose_.x_m = declare_parameter<double>("initial_x_m", 0.0);
        initial_pose_.y_m = declare_parameter<double>("initial_y_m", 0.0);
        initial_pose_.yaw_rad = declare_parameter<double>("initial_yaw_deg", 0.0) * kDegToRad;

        // 라이다 외부 파라미터: 기본은 첫 스캔 frame_id 로 TF 1회 lookup.
        // use_tf_extrinsic:=false 면 laser_*_m/deg 파라미터를 그대로 쓴다.
        use_tf_extrinsic_ = declare_parameter<bool>("use_tf_extrinsic", true);
        laser_fallback_.x_m = declare_parameter<double>("laser_x_m", 0.0);
        laser_fallback_.y_m = declare_parameter<double>("laser_y_m", 0.0);
        laser_fallback_.yaw_rad = declare_parameter<double>("laser_yaw_deg", 0.0) * kDegToRad;

        declareTuningParams();

        pose_pub_ = create_publisher<geometry_msgs::msg::PoseStamped>("wall_pose", 10);
        diag_pub_ =
            create_publisher<diagnostic_msgs::msg::DiagnosticArray>("wall_localizer/diagnostics", 10);
        marker_pub_ = create_publisher<visualization_msgs::msg::MarkerArray>(
            "wall_localizer/wall_markers", 10);
        tf_buffer_ = std::make_unique<tf2_ros::Buffer>(get_clock());
        tf_listener_ = std::make_unique<tf2_ros::TransformListener>(*tf_buffer_);
        scan_sub_ = create_subscription<sensor_msgs::msg::LaserScan>(
            "scan", rclcpp::SensorDataQoS(),
            [this](sensor_msgs::msg::LaserScan::SharedPtr msg) { scanCallback(msg); });

        RCLCPP_INFO(get_logger(), "wall_localizer: 기준 벽 %zu면, station_frame='%s'",
                    walls_.size(), station_frame_.c_str());
    }

  private:
    // wall_names + walls.<name>=[x1,y1,x2,y2] (m, 스테이션 프레임) → 기준 벽 목록.
    // 형식 오류는 기동 실패 — 잘못된 스테이션 정의로 조용히 뜨는 것보다 낫다.
    std::vector<wall_localizer_core::WallRef> loadWallsFromParams()
    {
        const auto names =
            declare_parameter<std::vector<std::string>>("wall_names", std::vector<std::string>{});
        if (names.size() < 2)
        {
            RCLCPP_FATAL(get_logger(),
                         "wall_names 에 기준 벽이 2면 미만입니다 (%zu) — 자세를 풀 수 없습니다",
                         names.size());
            throw std::runtime_error("wall_names invalid");
        }
        std::vector<wall_localizer_core::WallRef> walls;
        for (const auto &name : names)
        {
            const auto v = declare_parameter<std::vector<double>>("walls." + name,
                                                                  std::vector<double>{});
            if (v.size() != 4)
            {
                RCLCPP_FATAL(get_logger(), "walls.%s 는 [x1,y1,x2,y2] 4값이어야 합니다 (현재 %zu값)",
                             name.c_str(), v.size());
                throw std::runtime_error("wall endpoints invalid");
            }
            if (std::hypot(v[2] - v[0], v[3] - v[1]) < 1e-6)
            {
                RCLCPP_FATAL(get_logger(), "walls.%s 의 두 끝점이 같습니다 — 직선을 정의할 수 없습니다",
                             name.c_str());
                throw std::runtime_error("wall endpoints degenerate");
            }
            walls.push_back({name, {v[0], v[1]}, {v[2], v[3]}});
        }
        return walls;
    }

    // 코어 튜닝 파라미터 — 코어 기본값을 그대로 기본값으로 노출, 각도는 deg 경계 변환.
    void declareTuningParams()
    {
        auto &e = params_.extract;
        e.range_min_m = declare_parameter<double>("range_min_m", e.range_min_m);
        e.range_max_m = declare_parameter<double>("range_max_m", e.range_max_m);
        e.angle_min_rad =
            declare_parameter<double>("scan_angle_min_deg", e.angle_min_rad / kDegToRad) * kDegToRad;
        e.angle_max_rad =
            declare_parameter<double>("scan_angle_max_deg", e.angle_max_rad / kDegToRad) * kDegToRad;
        e.max_point_gap_m = declare_parameter<double>("max_point_gap_m", e.max_point_gap_m);
        e.split_dist_m = declare_parameter<double>("split_dist_m", e.split_dist_m);
        e.merge_angle_rad =
            declare_parameter<double>("merge_angle_deg", e.merge_angle_rad / kDegToRad) * kDegToRad;
        e.merge_dist_m = declare_parameter<double>("merge_dist_m", e.merge_dist_m);
        e.min_points = static_cast<int>(declare_parameter<int64_t>("min_points", e.min_points));
        e.min_length_m = declare_parameter<double>("min_length_m", e.min_length_m);

        auto &m = params_.match;
        m.gate_angle_rad =
            declare_parameter<double>("gate_angle_deg", m.gate_angle_rad / kDegToRad) * kDegToRad;
        m.gate_dist_m = declare_parameter<double>("gate_dist_m", m.gate_dist_m);
        m.min_overlap_ratio = declare_parameter<double>("min_overlap_ratio", m.min_overlap_ratio);
        m.refit_corridor_m = declare_parameter<double>("refit_corridor_m", m.refit_corridor_m);
        m.refit_margin_m = declare_parameter<double>("refit_margin_m", m.refit_margin_m);

        auto &s = params_.solve;
        s.min_normal_spread = declare_parameter<double>("min_normal_spread", s.min_normal_spread);
        s.max_iterations =
            static_cast<int>(declare_parameter<int64_t>("max_iterations", s.max_iterations));

        auto &q = params_.quality;
        q.min_walls = static_cast<int>(declare_parameter<int64_t>("min_walls", q.min_walls));
        q.max_dist_residual_m =
            declare_parameter<double>("max_dist_residual_m", q.max_dist_residual_m);
        q.max_angle_residual_rad =
            declare_parameter<double>("max_angle_residual_deg", q.max_angle_residual_rad / kDegToRad) *
            kDegToRad;
        q.max_jump_m = declare_parameter<double>("max_jump_m", q.max_jump_m);
        q.max_jump_rad =
            declare_parameter<double>("max_jump_deg", q.max_jump_rad / kDegToRad) * kDegToRad;
        q.max_consecutive_rejects = static_cast<int>(
            declare_parameter<int64_t>("max_consecutive_rejects", q.max_consecutive_rejects));
    }

    // base_frame ← 스캔 frame_id 정적 TF 를 1회 lookup 해 캐시. 실패 시 파라미터 폴백.
    bool lookupLaserExtrinsic(const std::string &laser_frame)
    {
        if (!use_tf_extrinsic_)
        {
            T_base_lidar_ = laser_fallback_;
            return true;
        }
        try
        {
            const auto tf =
                tf_buffer_->lookupTransform(base_frame_, laser_frame, tf2::TimePointZero);
            T_base_lidar_.x_m = tf.transform.translation.x;
            T_base_lidar_.y_m = tf.transform.translation.y;
            // 평면(2D) 가정의 yaw 추출 — 라이다가 roll/pitch 뒤집힘 장착이면 이 식이
            // 틀린다. 그런 구성은 use_tf_extrinsic:=false + laser_* 실측 파라미터로 쓸 것.
            const auto &q = tf.transform.rotation;
            T_base_lidar_.yaw_rad =
                std::atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z));
            RCLCPP_INFO(get_logger(), "라이다 외부 파라미터(TF %s←%s): x=%.3f y=%.3f yaw=%.2f deg",
                        base_frame_.c_str(), laser_frame.c_str(), T_base_lidar_.x_m,
                        T_base_lidar_.y_m, T_base_lidar_.yaw_rad / kDegToRad);
            return true;
        }
        catch (const tf2::TransformException &e)
        {
            RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000,
                                 "TF %s←%s 대기 중 (%s) — 수신 전에는 측위하지 않습니다",
                                 base_frame_.c_str(), laser_frame.c_str(), e.what());
            return false;
        }
    }

    void scanCallback(const sensor_msgs::msg::LaserScan::SharedPtr &msg)
    {
        if (localizer_ == nullptr)
        {
            if (!lookupLaserExtrinsic(msg->header.frame_id))
            {
                return;
            }
            localizer_ = std::make_unique<wall_localizer_core::WallLocalizer>(
                walls_, params_, T_base_lidar_, initial_pose_);
        }

        const std::vector<float> ranges(msg->ranges.begin(), msg->ranges.end());
        const wall_localizer_core::LocalizeResult res =
            localizer_->update(ranges, msg->angle_min, msg->angle_increment);

        if (res.status != wall_localizer_core::Status::LOST)
        {
            geometry_msgs::msg::PoseStamped ps;
            ps.header.stamp = msg->header.stamp;
            ps.header.frame_id = station_frame_;
            ps.pose.position.x = res.T_station_base.x_m;
            ps.pose.position.y = res.T_station_base.y_m;
            ps.pose.position.z = 0.0;
            ps.pose.orientation.z = std::sin(0.5 * res.T_station_base.yaw_rad);
            ps.pose.orientation.w = std::cos(0.5 * res.T_station_base.yaw_rad);
            pose_pub_->publish(ps);
        }
        publishDiagnostics(msg->header.stamp, res);
        publishWallMarkers(msg->header.stamp, res);
    }

    // 기준 벽(스테이션 프레임)을 base_link 프레임으로 변환해 RViz 마커로 그린다.
    // 스테이션 프레임은 TF 트리에 없으므로 현재 해(무효면 직전 해)의 역변환을 쓴다 —
    // RViz 고정 프레임이 map 이어도 TF(map→odom→base_link)를 타고 물리 벽 위에 겹친다.
    // 색: 매칭=초록, 미매칭=빨강, LOST=회색(직전 해 기준 표시).
    void publishWallMarkers(const rclcpp::Time &stamp,
                            const wall_localizer_core::LocalizeResult &res)
    {
        const bool lost = (res.status == wall_localizer_core::Status::LOST);
        const wall_localizer_core::Pose2D &T_station_base =
            lost ? localizer_->lastPose() : res.T_station_base;
        const wall_localizer_core::Pose2D T_base_station =
            wall_localizer_core::inverse(T_station_base);

        visualization_msgs::msg::MarkerArray arr;
        for (std::size_t i = 0; i < walls_.size(); ++i)
        {
            const bool matched =
                !lost && i < res.wall_fits.size() && res.wall_fits[i].matched;
            visualization_msgs::msg::Marker m;
            m.header.stamp = stamp;
            m.header.frame_id = base_frame_;
            m.ns = "walls";
            m.id = static_cast<int>(i);
            m.type = visualization_msgs::msg::Marker::LINE_STRIP;
            m.action = visualization_msgs::msg::Marker::ADD;
            // 선폭은 화면 가시성 기준 — 맵 전체 줌(수십 m 시야)에서도 수 픽셀이 되도록.
            // 0.03 m 는 전체 줌에서 1픽셀 미만이라 안 보인다(실기 확인).
            m.scale.x = 0.08;
            // 매칭 = 오렌지(사용자 지정), 미매칭 = 빨강, LOST = 회색
            m.color.r = lost ? 0.5f : (matched ? 1.0f : 0.9f);
            m.color.g = lost ? 0.5f : (matched ? 0.55f : 0.1f);
            m.color.b = lost ? 0.5f : 0.05f;
            m.color.a = 0.9f;
            m.lifetime = rclcpp::Duration::from_seconds(0.5);
            for (const auto &p_station : {walls_[i].p1, walls_[i].p2})
            {
                const wall_localizer_core::Point2D p_base =
                    wall_localizer_core::transformPoint(T_base_station, p_station);
                geometry_msgs::msg::Point gp;
                gp.x = p_base.x_m;
                gp.y = p_base.y_m;
                gp.z = 0.05;
                m.points.push_back(gp);
            }
            arr.markers.push_back(m);

            visualization_msgs::msg::Marker t;
            t.header = m.header;
            t.ns = "wall_labels";
            t.id = static_cast<int>(i);
            t.type = visualization_msgs::msg::Marker::TEXT_VIEW_FACING;
            t.action = visualization_msgs::msg::Marker::ADD;
            t.scale.z = 0.15;
            t.color = m.color;
            t.lifetime = m.lifetime;
            t.pose.position.x = 0.5 * (m.points[0].x + m.points[1].x);
            t.pose.position.y = 0.5 * (m.points[0].y + m.points[1].y);
            t.pose.position.z = 0.3;
            t.pose.orientation.w = 1.0;
            t.text = walls_[i].name +
                     (matched ? (" (" + std::to_string(res.wall_fits[i].seg_points) + "pt)")
                              : (lost ? " (lost)" : " (unmatched)"));
            arr.markers.push_back(t);
        }
        marker_pub_->publish(arr);
    }

    void publishDiagnostics(const rclcpp::Time &stamp,
                            const wall_localizer_core::LocalizeResult &res)
    {
        diagnostic_msgs::msg::DiagnosticArray arr;
        arr.header.stamp = stamp;
        diagnostic_msgs::msg::DiagnosticStatus st;
        st.name = "wall_localizer";
        st.hardware_id = station_frame_;
        st.level = (res.status == wall_localizer_core::Status::OK)
                       ? diagnostic_msgs::msg::DiagnosticStatus::OK
                       : (res.status == wall_localizer_core::Status::DEGRADED
                              ? diagnostic_msgs::msg::DiagnosticStatus::WARN
                              : diagnostic_msgs::msg::DiagnosticStatus::ERROR);
        st.message = statusText(res.status) + (res.reason.empty() ? "" : (": " + res.reason));

        auto kv = [&st](const std::string &k, const std::string &v) {
            diagnostic_msgs::msg::KeyValue e;
            e.key = k;
            e.value = v;
            st.values.push_back(e);
        };
        kv("num_segments", std::to_string(res.num_segments));
        kv("iterations", std::to_string(res.iterations));
        kv("normal_spread", std::to_string(res.normal_spread));
        for (const auto &f : res.wall_fits)
        {
            kv(f.name + "_matched", f.matched ? "1" : "0");
            if (f.matched)
            {
                kv(f.name + "_dist_residual_m", std::to_string(f.dist_residual_m));
                kv(f.name + "_angle_residual_deg",
                   std::to_string(f.angle_residual_rad / kDegToRad));
                kv(f.name + "_points", std::to_string(f.seg_points));
            }
        }
        arr.status.push_back(st);
        diag_pub_->publish(arr);
    }

    // --- 구성 (생성자 1회) ---
    std::string station_frame_;
    std::string base_frame_;
    std::vector<wall_localizer_core::WallRef> walls_;
    wall_localizer_core::WallLocalizerParams params_;
    wall_localizer_core::Pose2D initial_pose_;
    bool use_tf_extrinsic_{true};
    wall_localizer_core::Pose2D laser_fallback_;

    // --- 런타임 상태 ---
    wall_localizer_core::Pose2D T_base_lidar_;  // lookupLaserExtrinsic 1회 캐시
    std::unique_ptr<wall_localizer_core::WallLocalizer> localizer_;  // 외부 파라미터 확보 후 생성

    rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr pose_pub_;
    rclcpp::Publisher<diagnostic_msgs::msg::DiagnosticArray>::SharedPtr diag_pub_;
    rclcpp::Publisher<visualization_msgs::msg::MarkerArray>::SharedPtr marker_pub_;
    rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr scan_sub_;
    std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
    std::unique_ptr<tf2_ros::TransformListener> tf_listener_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    try
    {
        rclcpp::spin(std::make_shared<WallLocalizerNode>());
    }
    catch (const std::runtime_error &e)
    {
        // 파라미터 형식 오류 — 이미 FATAL 로그가 남았다. 비정상 종료로 상위에 알린다.
        rclcpp::shutdown();
        return 1;
    }
    rclcpp::shutdown();
    return 0;
}
