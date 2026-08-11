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
        // 자세 **값**이 이 시간 이상 변하지 않으면 STUCK 으로 본다(0 이하 = 검사 비활성).
        // ⚠ stamp 신선도와는 **다른 검사**다. 발행자가 값이 그대로여도 매 주기 새 stamp 를
        //   찍으면 신선도 검사는 통과한다 — 그때 소비자는 얼어붙은 좌표로 제어를 닫는다.
        //   지령 속도가 실려 있을 때만(정지 중에는 안 변하는 것이 정상) 판정한다.
        double pose_stuck_timeout_sec{2.0};
        // 「변했다」로 볼 최소 이동량[m] — **직전 메시지가 아니라 기준점에서의 누적**과 비교한다.
        // ⚠ 연속 메시지 차분과 비교하면 안 된다: 0.05 m/s · 50 Hz 면 메시지당 1 mm 라
        //   임계(2 mm)를 영원히 못 넘어 **정상 주행이 STUCK 으로 잡힌다**(실측).
        double pose_move_eps_m{0.002};
        bool enable_watchdog{true};
    };

    enum class HealthFailReason
    {
        NONE = 0,
        TIMEOUT = 1,
        JUMP = 2,
        TF_LOOKUP_FAIL = 3,  // 토픽 미수신 시 사용 (semantic 호환)
        STUCK = 4,           // 메시지는 오는데 **값이 얼어 있다** (신선도 검사로는 못 잡는다)
    };

    explicit LocalizationMonitor(rclcpp::Node::SharedPtr node, const Params &params);

    bool checkLocalizationHealth();

    HealthFailReason getLastFailReason() const
    {
        return last_fail_reason_.load();
    }

    void setMaxCmdSpeed(double speed)
    {
        // 정지 → 주행 전이에서 값-정지 타이머를 다시 건다. 그러지 않으면 오래 서 있던
        // 로봇이 출발하자마자 STUCK 으로 잡힌다(정지 중 값이 안 변하는 것은 정상이다).
        const double prev = max_cmd_speed_.exchange(speed);
        if (prev <= 0.01 && speed > 0.01)
        {
            last_move_ns_.store(node_->get_clock()->now().nanoseconds());
        }
    }

    void setEnableWatchdog(bool enable)
    {
        bool prev = enable_watchdog_.exchange(enable);
        if (enable && !prev)
        {
            // ⚠ 값-정지 타이머도 함께 재장전한다. 이것이 없으면 직전 goal 이 abort 로
            //   끝나며 남긴 `max_cmd_speed_`(비-0)와 낡은 `last_move_ns_` 조합 때문에
            //   **다음 goal 이 첫 주기에 즉시 STUCK 으로 죽고, 그 abort 가 다시 같은 상태를
            //   남겨 자기증식한다**(노드 재시작 전까지 wedge).
            last_move_ns_.store(node_->get_clock()->now().nanoseconds());
            move_ref_x_.store(last_x_.load());
            move_ref_y_.store(last_y_.load());
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
    std::atomic<int64_t> last_move_ns_{0};   // 자세 **값**이 마지막으로 변한 시각
    std::atomic<double> move_ref_x_{0.0};    // 값-정지 판정 기준점(누적 비교용)
    std::atomic<double> move_ref_y_{0.0};

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
