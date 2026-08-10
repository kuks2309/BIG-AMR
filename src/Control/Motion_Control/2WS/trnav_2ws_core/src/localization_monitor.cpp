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

    // ── 값-변화 시각 기록 ──
    // 발행자가 값이 그대로여도 새 stamp 를 찍을 수 있으므로, **좌표가 실제로 변한 시각**을
    // 따로 남긴다. 신선도(stamp 나이)와 살아있음(값 변화)은 다른 성질이다.
    if (pose_received_.load())
    {
        // ⚠ **기준점에서의 누적**과 비교한다. 직전 메시지와 비교하면 느린 주행에서
        //   메시지당 변화가 임계보다 작아(0.05 m/s · 50 Hz → 1 mm) 정상 주행이 STUCK 으로
        //   잡힌다. 누적이 임계를 넘을 때만 기준점을 옮기고 시각을 갱신한다.
        const double moved = std::hypot(x - move_ref_x_.load(), y - move_ref_y_.load());
        if (moved > params_.pose_move_eps_m)
        {
            move_ref_x_.store(x);
            move_ref_y_.store(y);
            last_move_ns_.store(node_->get_clock()->now().nanoseconds());
        }
    }
    else
    {
        move_ref_x_.store(x);
        move_ref_y_.store(y);
        last_move_ns_.store(node_->get_clock()->now().nanoseconds());
    }

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

    // ── 값-정지 판정(STUCK) ──
    // 여기까지 왔다는 것은 ① 워치독 켜짐 ② 지령 속도가 실려 있음 ③ 자세를 받았고
    // ④ 점프 없음 ⑤ stamp 도 신선하다는 뜻이다. 그런데도 **좌표가 변하지 않는다면**
    // 소비자는 얼어붙은 값으로 제어를 닫고 있는 것이다 — 진행거리가 0 에 머물러
    // 「목표 미달」로 판단하고 지령을 계속 내면 **개루프 주행**이 된다.
    if (params_.pose_stuck_timeout_sec > 0.0)
    {
        const double still_sec =
            (now_ros - rclcpp::Time(last_move_ns_.load(), RCL_ROS_TIME)).seconds();
        if (still_sec > params_.pose_stuck_timeout_sec)
        {
            RCLCPP_WARN(node_->get_logger(),
                        "/robot_pose 값이 %.2f s 동안 변하지 않는다 (stamp 는 신선함, "
                        "cmd_speed=%.3f m/s) — 얼어붙은 자세로 제어가 닫히고 있다",
                        still_sec, max_cmd_speed_.load());
            last_fail_reason_.store(HealthFailReason::STUCK);
            return false;
        }
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
