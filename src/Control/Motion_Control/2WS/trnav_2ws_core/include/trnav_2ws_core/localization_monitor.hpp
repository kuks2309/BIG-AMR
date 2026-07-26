#ifndef AMR_MOTION_CORE__LOCALIZATION_MONITOR_HPP_
#define AMR_MOTION_CORE__LOCALIZATION_MONITOR_HPP_

#include "geometry_msgs/msg/pose_stamped.hpp"
#include "rclcpp/rclcpp.hpp"
#include "tf2/LinearMath/Matrix3x3.h"
#include "tf2/LinearMath/Quaternion.h"
#include <atomic>
#include <memory>
#include <mutex>
#include <string>

namespace trnav_2ws_core
{

/// 정공법 (2026-05-18) — /robot_pose 토픽 구독 기반 LocalizationMonitor.
/// 분산 TF lookup 폐기 (trnav_pose_publisher 가 단일 발행). 자원 효율 + SSOT.
///
/// Atomic snapshot 주의: last_x_/y_/yaw_/stamp_ns_ 는 각각 독립 std::atomic.
/// 단일 필드 reader 는 일관된 값을 보지만, 여러 필드 cross-field atomicity 보장 안 됨.
/// 50Hz 발행 + µs-level atomic load 차이에서 negligible — 실용 안전.
class LocalizationMonitor
{
  public:
    struct Params
    {
        std::string pose_topic{"/robot_pose"};
        int pose_qos{0};  // 0=default(RELIABLE depth=10) 1=reliable 명시(동일) 2=BEST_EFFORT(SensorDataQoS). 2026-05-19: 외부 관측 호환 위해 RELIABLE default.
        double localization_timeout_sec{0.5};
        double position_jump_threshold{0.3};
        bool enable_watchdog{true};
    };

    enum class HealthFailReason
    {
        NONE = 0,
        TIMEOUT = 1,
        JUMP = 2,
        TF_LOOKUP_FAIL = 3,  // 토픽 미수신 시 사용 (semantic 호환)
    };

    explicit LocalizationMonitor(rclcpp::Node::SharedPtr node, const Params &params);

    bool checkLocalizationHealth();

    HealthFailReason getLastFailReason() const
    {
        return last_fail_reason_.load();
    }

    void setMaxCmdSpeed(double speed)
    {
        max_cmd_speed_.store(speed);
    }

    void setEnableWatchdog(bool enable)
    {
        bool prev = enable_watchdog_.exchange(enable);
        if (enable && !prev)
        {
            // off→on 전환 — 다음 health check 가 baseline 재구축
            std::lock_guard<std::mutex> lock(jump_mutex_);
            prev_jump_valid_ = false;
            last_fail_reason_.store(HealthFailReason::NONE);
        }
    }

    /// 3-arg overload — 토픽 snapshot 반환 (yaw 포함, stamp 무시).
    bool lookupMapToBase(double &x, double &y, double &yaw) const;

    /// 4-arg overload — stamp 포함 snapshot 반환 (checkLocalizationHealth 사용).
    bool lookupMapToBase(double &x, double &y, double &yaw, rclcpp::Time &stamp) const;

  private:
    void poseCallback(const geometry_msgs::msg::PoseStamped::SharedPtr msg);

    rclcpp::Node::SharedPtr node_;
    Params params_;

    rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr pose_sub_;

    // Atomic snapshot — callback writes, lookupMapToBase / checkLocalizationHealth reads.
    std::atomic<double> last_x_{0.0};
    std::atomic<double> last_y_{0.0};
    std::atomic<double> last_yaw_{0.0};
    std::atomic<int64_t> last_stamp_ns_{0};  // rclcpp::Time nanoseconds
    std::atomic<bool> pose_received_{false};

    // Jump detection (callback thread only, mutex protected from setEnableWatchdog reset)
    std::mutex jump_mutex_;
    bool prev_jump_valid_{false};
    double prev_jump_x_{0.0};
    double prev_jump_y_{0.0};
    rclcpp::Time prev_jump_stamp_;
    std::atomic<bool> jump_detected_{false};

    std::atomic<double> max_cmd_speed_{0.0};
    std::atomic<bool> enable_watchdog_{true};
    std::atomic<HealthFailReason> last_fail_reason_{HealthFailReason::NONE};
};

} // namespace trnav_2ws_core

#endif // AMR_MOTION_CORE__LOCALIZATION_MONITOR_HPP_
