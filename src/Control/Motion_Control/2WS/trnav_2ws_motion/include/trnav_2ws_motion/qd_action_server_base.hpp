#ifndef TRNAV_2WS_MOTION__QD_ACTION_SERVER_BASE_HPP_
#define TRNAV_2WS_MOTION__QD_ACTION_SERVER_BASE_HPP_

#include "trnav_2ws_core/action_mutex.hpp"
#include "trnav_2ws_core/math_utils.hpp"
#include "trnav_2ws_core/robot_geometry.hpp"
#include "trnav_2ws_kinematics/qd_inverse_kinematics.hpp"
#include "trnav_2ws_motion/qd_wheel_set_packer.hpp"

#include "trnav_msgs/msg/motor_status.hpp"
#include "trnav_msgs/msg/wheel_motor.hpp" // state feedback only (wheel_motor_state)
#include "trnav_msgs/msg/wheel_set_array.hpp"
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <std_msgs/msg/string.hpp>
#include <tf2/LinearMath/Matrix3x3.h>
#include <tf2/LinearMath/Quaternion.h>

#include <atomic>
#include <memory>
#include <string>
#include <thread>

namespace trnav::motion::two_ws
{

// Base class for QD platform action servers that publish motion commands via
// the trnav_motion_mux contract.
// Publishes trnav_msgs/WheelSetArray on the configured topic (RELIABLE, KeepLast(10)).
// The legacy trnav_msgs/WheelMotor subscription is retained only for state feedback
// (wheel_motor_state); the command path is fully WheelSetArray.
//
// QD-specific: instantiates TwoWsDualSteerIK + TwoWsWheelSetPacker as members. DD or other
// platforms must use a sibling base class (e.g., dd_action_server_base.hpp when added).
template <typename ActionT> class TwoWsActionServerBase
{
  public:
    using GoalHandle = rclcpp_action::ServerGoalHandle<ActionT>;

    TwoWsActionServerBase(rclcpp::Node::SharedPtr node, trnav_2ws_core::ActionMutex action_mutex,
                       const std::string &action_name, const std::string &publish_topic)
        : node_(node), action_mutex_(std::move(action_mutex)), packer_(loadGeometry(node))
    {
        // Safe param helper (double overload matching crab pattern)
        auto safe_param_d = [&](const std::string &name, double default_val) -> double {
            if (!node_->has_parameter(name))
            {
                return node_->declare_parameter(name, default_val);
            }
            return node_->get_parameter(name).as_double();
        };

        // Common params
        control_rate_hz_ = safe_param_d("control_rate_hz", 50.0);
        // 상류 조향 가드 한계(도). 기본 = 하류 체인 클램프 115 − |영점 오프셋| 1.676.
        // 0 이하 = 가드 해제. 근거는 publishWheelCmd 주석 참조.
        steer_cmd_limit_rad_ = safe_param_d("steer_cmd_limit_deg", 113.32) * M_PI / 180.0;
        steer_tolerance_rad_ = safe_param_d("steer_tolerance_deg", 1.0) * M_PI / 180.0;
        steer_timeout_sec_ = safe_param_d("steer_timeout_sec", 5.0);

        // IK setup — uses already-loaded geometry
        const auto &geom = packer_.geometry();
        std::vector<WheelPosition> wheels = {{geom.w1_x, geom.w1_y}, {geom.w2_x, geom.w2_y}};
        ik_ = std::make_unique<TwoWsDualSteerIK>(wheels, geom.wheel_radius, geom.gear_walk);

        // ⚠ 인라인 전제 검사 — 이 스택 전체가 「두 바퀴가 x 축 위(y=0)」를 전제로 한다.
        //   제자리 회전 자세가 ±90° 로 고정인 근거이며, spin 이 그것을 강제한다.
        //   전제가 깨진 채 돌면 **조용히 다른 자세**로 움직인다 — 2026-08-08 실증:
        //   QD 대각 기하(±0.330, ±0.135)가 흘러들어와 spin 이 −67.75° 를 세웠고
        //   제자리 회전이 187 mm 병진이 됐다(SIL). 조용히 도는 것보다 기동 실패가 낫다.
        if (!ik_->isInline())
        {
            RCLCPP_FATAL(node_->get_logger(),
                         "기하 전제 위반 — 이 스택은 인라인 듀얼스티어(y=0)만 지원한다. "
                         "w1=(%.4f, %.4f) w2=(%.4f, %.4f). params 파일(`config/*_params.yaml`)이 "
                         "빠졌거나 QD 대각 기하가 들어왔는지 확인할 것.",
                         geom.w1_x, geom.w1_y, geom.w2_x, geom.w2_y);
            throw std::runtime_error("2WS 인라인 전제 위반 — 기하 파라미터 확인 필요");
        }

        // Publishers — trnav_motion_mux contract
        wheel_cmd_pub_ =
            node_->create_publisher<trnav_msgs::msg::WheelSetArray>(publish_topic, rclcpp::QoS(10).reliable());

        // Result status reporter — abort/cancel/success 코드를 토픽으로 발행(bag 기록용).
        // action result(get_result 서비스)는 rosbag2(Humble) 미기록 → "<server>:<code>" 문자열 토픽으로 보강.
        action_name_ = action_name;
        result_status_pub_ =
            node_->create_publisher<std_msgs::msg::String>("/motion/last_result", rclcpp::QoS(10).reliable());

        // Subscribers — state feedback (legacy WheelMotor still valid for this path)
        wheel_state_sub_ = node_->create_subscription<trnav_msgs::msg::WheelMotor>(
            "wheel_motor_state", rclcpp::QoS(10),
            [this](const trnav_msgs::msg::WheelMotor::SharedPtr msg) { wheelStateCallback(msg); });

        motor_status_sub_ = node_->create_subscription<trnav_msgs::msg::MotorStatus>(
            "motor_status", rclcpp::QoS(10), [this](const trnav_msgs::msg::MotorStatus::SharedPtr /*msg*/) {});

        imu_sub_ = node_->create_subscription<sensor_msgs::msg::Imu>(
            "imu/data", rclcpp::SensorDataQoS(),
            [this](const sensor_msgs::msg::Imu::SharedPtr msg) { imuCallback(msg); });

        // Action server
        action_server_ = rclcpp_action::create_server<ActionT>(
            node_, action_name,
            [this](const rclcpp_action::GoalUUID &uuid, std::shared_ptr<const typename ActionT::Goal> goal) {
                return handleGoal(uuid, goal);
            },
            [this](std::shared_ptr<GoalHandle> gh) { return handleCancel(gh); },
            [this](std::shared_ptr<GoalHandle> gh) { handleAccepted(gh); });
    }

    virtual ~TwoWsActionServerBase() = default;

  protected:
    // Derived MUST implement
    virtual void execute(std::shared_ptr<GoalHandle> goal_handle) = 0;
    virtual bool validateGoal(std::shared_ptr<const typename ActionT::Goal> goal) = 0;

    // Provided by base — interface identical to legacy publishWheelCmd(vel_f,ang_f,vel_r,ang_r).
    // Internally repacks into WheelSetArray per configured RobotGeometry (Platform).
    //
    // ⚠ **상류 조향 가드** (2026-08-06 사용자 결정: 「115도면 최대 115도만 내면 됩니다」).
    //   하류 can_relay 는 counts 로 클램프하는데, 그 사이 translator 가 영점 오프셋
    //   (`steer_offset_*_deg`)을 빼므로 **여기서 낸 각보다 raw 가 |offset| 만큼 커진다**(+θ 쪽).
    //   그래서 상류가 하류 한계를 그대로 믿고 내면 조용히 잘린다 — 실제로 크랩 최대 자세가
    //   1.68도 잘렸다. 하류에서 자르지 말고 **여기서 내지 않는다.**
    //
    //   기본값 = 하류 체인 클램프(115도) − |영점 오프셋|(1.676도) = 113.32도.
    //   두 값의 정합은 `Tools/motion_chain_check/check_chain_contract.py` C4 가 재도출해 대조한다.
    //   0 이하로 두면 가드를 끈다(상류 무제한 — 하류 클램프에 맡긴다).
    void publishWheelCmd(double velocity_front, double angle_front, double velocity_rear, double angle_rear)
    {
        angle_front = guardSteer(angle_front, "front");
        angle_rear = guardSteer(angle_rear, "rear");
        auto msg = packer_.pack(velocity_front, angle_front, velocity_rear, angle_rear);
        msg.header.stamp = node_->get_clock()->now();
        wheel_cmd_pub_->publish(msg);
    }

    /// 조향 지령을 상류 한계로 포화시킨다. 거부가 아니라 포화 — 크랩 설계가 전제하는 동작이다.
    double guardSteer(double angle_rad, const char *which)
    {
        if (steer_cmd_limit_rad_ <= 0.0)
        {
            return angle_rad;
        }
        const double lim = steer_cmd_limit_rad_;
        if (angle_rad > lim || angle_rad < -lim)
        {
            const double capped = std::max(-lim, std::min(lim, angle_rad));
            RCLCPP_WARN_THROTTLE(node_->get_logger(), *node_->get_clock(), 1000,
                                 "조향 상류 가드 — %s %.2f deg -> %.2f deg (한계 %.2f deg). "
                                 "하류에서 잘리기 전에 여기서 포화시킨다",
                                 which, angle_rad * 180.0 / M_PI, capped * 180.0 / M_PI,
                                 lim * 180.0 / M_PI);
            return capped;
        }
        return angle_rad;
    }

    void publishStopCmd()
    {
        publishWheelCmd(0.0, last_angle_front_.load(), 0.0, last_angle_rear_.load());
    }

    // 종료 status 코드(-1 cancel / -2 invalid / -3 timeout / -4 loc_timeout / -5 loc_jump / -6 tf_fail /
    // -7 heading_divergence / -8 steer_unreachable / -9 final_yaw_tolerance — 뒤 셋은 yaw_control 계열 전용,
    // `AMRMotionYawControl.action` 참조 / 0 success)를
    // "<server>:<code>" 문자열로 /motion/last_result 에 발행. derived 의 finish_abort/succeed 에서 호출.
    void reportResult(int8_t code)
    {
        std_msgs::msg::String msg;
        msg.data = action_name_ + ":" + std::to_string(static_cast<int>(code));
        result_status_pub_->publish(msg);
    }

    // Safe parameter declaration helper
    template <typename T> T safeParam(const std::string &name, T default_val)
    {
        if (!node_->has_parameter(name))
        {
            node_->declare_parameter<T>(name, default_val);
        }
        return node_->get_parameter(name).get_value<T>();
    }

    // Members accessible to derived classes
    rclcpp::Node::SharedPtr node_;
    rclcpp::Publisher<trnav_msgs::msg::WheelSetArray>::SharedPtr wheel_cmd_pub_;
    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr result_status_pub_;
    std::string action_name_;
    std::unique_ptr<TwoWsDualSteerIK> ik_;
    trnav_2ws_core::ActionMutex action_mutex_;

    // atomic: execute thread + callback thread concurrent access
    std::atomic<double> last_angle_front_{0.0};
    std::atomic<double> last_angle_rear_{0.0};
    std::atomic<double> last_yaw_rad_{0.0};
    std::atomic<bool> imu_received_{false};

    double control_rate_hz_{50.0};
    double steer_cmd_limit_rad_{113.32 * M_PI / 180.0};   // 상류 조향 가드 (0 이하 = 해제)
    double steer_tolerance_rad_{0.0175};
    double steer_timeout_sec_{5.0};

  protected:
    // wheelStateCallback is virtual so Translate can override with timestamp tracking
    virtual void wheelStateCallback(const trnav_msgs::msg::WheelMotor::SharedPtr msg)
    {
        last_angle_front_.store(msg->angle_front);
        last_angle_rear_.store(msg->angle_rear);
    }

    // Accessor for derived classes that need explicit geometry (e.g. per-wheel bicycle)
    const trnav_2ws_core::RobotGeometry &geometry() const
    {
        return packer_.geometry();
    }

  private:
    // Load robot geometry from node parameters. Called before packer_ construction.
    static trnav_2ws_core::RobotGeometry loadGeometry(rclcpp::Node::SharedPtr node)
    {
        auto get_d = [&](const std::string &name, double default_val) {
            if (!node->has_parameter(name))
            {
                node->declare_parameter(name, default_val);
            }
            return node->get_parameter(name).as_double();
        };
        auto get_s = [&](const std::string &name, const std::string &default_val) {
            if (!node->has_parameter(name))
            {
                node->declare_parameter(name, default_val);
            }
            return node->get_parameter(name).as_string();
        };

        // ⚠ 기본값은 **이 저장소의 기체(Foil_A082, 인라인 듀얼스티어)** 기준이다.
        //    QD 에서 갈라져 나올 때 대각 배치 기본값(±0.330, ±0.135 · r 0.080 · gear 20)이
        //    그대로 남아 있었고, params 파일 없이 노드를 띄우면 **조용히 QD 기하로 풀렸다.**
        //    2026-08-08 실증: 그 상태의 spin 이 조향을 ±90° 가 아니라 **−67.75°(양 축 같은 부호)**
        //    로 세웠고 — `atan2(0.330, −0.135) = 112.2°` 를 ±90° 반평면으로 접은 값 — 제자리
        //    회전이 **187 mm 병진**이 됐다(SIL). 실기였다면 그대로 밀고 나갔다.
        //    인라인 배치는 두 바퀴가 x 축 위(y=0)라 제자리 회전 자세가 ±90° 하나로 고정된다.
        //    정본은 `config/*_params.yaml` 이며 아래는 그것과 같은 값으로 맞춘 안전한 기본값이다.
        trnav_2ws_core::RobotGeometry geom;
        geom.platform = trnav_2ws_core::parsePlatform(get_s("platform", "QD_DIAGONAL"));
        geom.w1_x = get_d("w1_x", 0.6039);
        geom.w1_y = get_d("w1_y", 0.0);
        geom.w2_x = get_d("w2_x", -0.5961);
        geom.w2_y = get_d("w2_y", 0.0);
        geom.wheel_radius = get_d("wheel_radius", 0.125);
        geom.gear_walk = get_d("gear_walk", 32.0);
        geom.num_wheels = 2; // QD default; other platforms override when added
        return geom;
    }

    void imuCallback(const sensor_msgs::msg::Imu::SharedPtr msg)
    {
        tf2::Quaternion q(msg->orientation.x, msg->orientation.y, msg->orientation.z, msg->orientation.w);
        double roll, pitch, yaw;
        tf2::Matrix3x3(q).getRPY(roll, pitch, yaw);
        last_yaw_rad_.store(yaw);
        imu_received_ = true;
    }

    rclcpp_action::GoalResponse handleGoal(const rclcpp_action::GoalUUID & /*uuid*/,
                                           std::shared_ptr<const typename ActionT::Goal> goal)
    {
        if (!validateGoal(goal))
        {
            return rclcpp_action::GoalResponse::REJECT;
        }
        bool expected = false;
        if (!action_mutex_->compare_exchange_strong(expected, true))
        {
            RCLCPP_WARN(node_->get_logger(), "Action rejected: another action is running");
            return rclcpp_action::GoalResponse::REJECT;
        }
        return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
    }

    rclcpp_action::CancelResponse handleCancel(std::shared_ptr<GoalHandle> /*goal_handle*/)
    {
        RCLCPP_INFO(node_->get_logger(), "Cancel request received");
        return rclcpp_action::CancelResponse::ACCEPT;
    }

    void handleAccepted(std::shared_ptr<GoalHandle> goal_handle)
    {
        std::thread([this, goal_handle]() { execute(goal_handle); }).detach();
    }

    // Subscriptions (prevent dangling)
    rclcpp::Subscription<trnav_msgs::msg::WheelMotor>::SharedPtr wheel_state_sub_;
    rclcpp::Subscription<trnav_msgs::msg::MotorStatus>::SharedPtr motor_status_sub_;
    rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr imu_sub_;
    typename rclcpp_action::Server<ActionT>::SharedPtr action_server_;

    // Packer must outlive publishWheelCmd calls
    TwoWsWheelSetPacker packer_;
};

} // namespace trnav::motion::two_ws

#endif // TRNAV_2WS_MOTION__QD_ACTION_SERVER_BASE_HPP_
