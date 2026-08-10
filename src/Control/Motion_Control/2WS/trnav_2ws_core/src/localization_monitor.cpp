#include "trnav_2ws_core/localization_monitor.hpp"

#include <cmath>

namespace trnav_2ws_core
{

LocalizationMonitor::LocalizationMonitor(rclcpp::Node::SharedPtr node, const Params &params)
    : node_(node), params_(params), prev_jump_stamp_(0, 0, RCL_ROS_TIME)
{
    enable_watchdog_.store(params_.enable_watchdog);

    rclcpp::QoS qos(10);
    if (params_.pose_qos == 2)
    {
        qos = rclcpp::SensorDataQoS();
    }
    else if (params_.pose_qos == 1)
    {
        qos = rclcpp::QoS(10).reliable();
    }

    pose_sub_ = node_->create_subscription<geometry_msgs::msg::PoseStamped>(
        params_.pose_topic, qos,
        [this](const geometry_msgs::msg::PoseStamped::SharedPtr msg) { poseCallback(msg); });
}

void LocalizationMonitor::poseCallback(const geometry_msgs::msg::PoseStamped::SharedPtr msg)
{
    double x = msg->pose.position.x;
    double y = msg->pose.position.y;
    tf2::Quaternion q(msg->pose.orientation.x, msg->pose.orientation.y,
                      msg->pose.orientation.z, msg->pose.orientation.w);
    double roll, pitch, yaw;
    tf2::Matrix3x3(q).getRPY(roll, pitch, yaw);
    rclcpp::Time stamp(msg->header.stamp);

    // Jump detection
    if (enable_watchdog_.load() && max_cmd_speed_.load() > 0.01)
    {
        std::lock_guard<std::mutex> lock(jump_mutex_);
        if (prev_jump_valid_)
        {
            double dt = (stamp - prev_jump_stamp_).seconds();
            if (dt > 1e-6)
            {
                double jump_dist = std::hypot(x - prev_jump_x_, y - prev_jump_y_);
                double expected_dist = max_cmd_speed_.load() * dt;
                double effective_threshold = std::max(params_.position_jump_threshold,
                                                      expected_dist * 1.3);
                if (jump_dist > effective_threshold)
                {
                    RCLCPP_WARN(node_->get_logger(),
                                "Pose jump: %.3f m (exp=%.3f, thr=%.3f, dt=%.3f s) "
                                "(%.2f,%.2f)->(%.2f,%.2f)",
                                jump_dist, expected_dist, effective_threshold, dt,
                                prev_jump_x_, prev_jump_y_, x, y);
                    jump_detected_.store(true);
                    prev_jump_valid_ = false;
                }
            }
        }
        prev_jump_x_ = x;
        prev_jump_y_ = y;
        prev_jump_stamp_ = stamp;
        prev_jump_valid_ = true;
    }

    last_x_.store(x);
    last_y_.store(y);
    last_yaw_.store(yaw);
    last_stamp_ns_.store(stamp.nanoseconds());
    pose_received_.store(true);
}

bool LocalizationMonitor::checkLocalizationHealth()
{
    if (!enable_watchdog_.load())
    {
        last_fail_reason_.store(HealthFailReason::NONE);
        return true;
    }

    if (max_cmd_speed_.load() <= 0.01)
    {
        // 정지 — jump silent reset
        jump_detected_.store(false);
        {
            std::lock_guard<std::mutex> lock(jump_mutex_);
            prev_jump_valid_ = false;
        }
        last_fail_reason_.store(HealthFailReason::NONE);
        return true;
    }

    if (!pose_received_.load())
    {
        RCLCPP_WARN(node_->get_logger(),
                    "/robot_pose not yet received (cmd_speed=%.3f m/s)",
                    max_cmd_speed_.load());
        last_fail_reason_.store(HealthFailReason::TF_LOOKUP_FAIL);
        return false;
    }

    // Jump check
    if (jump_detected_.load())
    {
        jump_detected_.store(false);
        last_fail_reason_.store(HealthFailReason::JUMP);
        return false;
    }

    // Timeout check
    int64_t stamp_ns = last_stamp_ns_.load();
    rclcpp::Time stamp(stamp_ns, RCL_ROS_TIME);
    auto now_ros = node_->get_clock()->now();
    double age_sec = (now_ros - stamp).seconds();
    if (age_sec > params_.localization_timeout_sec)
    {
        RCLCPP_WARN(node_->get_logger(),
                    "/robot_pose stale: age=%.3f s > %.3f s (cmd_speed=%.3f m/s)",
                    age_sec, params_.localization_timeout_sec, max_cmd_speed_.load());
        last_fail_reason_.store(HealthFailReason::TIMEOUT);
        return false;
    }

    last_fail_reason_.store(HealthFailReason::NONE);
    return true;
}

bool LocalizationMonitor::lookupMapToBase(double &x, double &y, double &yaw) const
{
    rclcpp::Time discard;
    return lookupMapToBase(x, y, yaw, discard);
}

bool LocalizationMonitor::lookupMapToBase(double &x, double &y, double &yaw,
                                          rclcpp::Time &stamp) const
{
    if (!pose_received_.load())
    {
        return false;
    }
    int64_t stamp_ns = last_stamp_ns_.load();
    stamp = rclcpp::Time(stamp_ns, RCL_ROS_TIME);

    // ── 신선도 검사 ──
    // ⚠ `pose_received_` 는 **한 번 참이 되면 내려가지 않는다.** 그래서 종전에는 측위가
    //   멈춰도 이 함수가 성공을 반환하며 **얼어붙은 좌표**를 줬다. 그 값으로 거리를
    //   투영하면 기동이 진행되지 않고, 헤딩 가드는 고정된 맵 yaw 로 IMU 를 탓한다.
    //   특히 **goal 시작 시점**이 위험하다 — 전체 궤적을 낡은 시작 자세에서 계산한다.
    //   임계는 새 손잡이를 만들지 않고 `localization_timeout_sec` 를 그대로 쓴다:
    //   `checkLocalizationHealth` 의 TIMEOUT 판정과 **같은 기준**이어야 두 경로가
    //   서로 다른 말을 하지 않는다(0 이하면 검사 비활성).
    //   호출부에서 막던 것을 여기로 내렸다 — 3인자 판도 이 함수에 위임하므로
    //   `translate_*`·`mpc*`·`crab_linear` 까지 한 번에 닫힌다.
    if (params_.localization_timeout_sec > 0.0)
    {
        const double age_sec = (node_->get_clock()->now() - stamp).seconds();
        if (age_sec > params_.localization_timeout_sec)
        {
            return false;
        }
    }

    x = last_x_.load();
    y = last_y_.load();
    yaw = last_yaw_.load();
    return true;
}

} // namespace trnav_2ws_core
