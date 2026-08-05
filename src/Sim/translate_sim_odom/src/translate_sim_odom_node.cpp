#include "translate_sim_odom/translate_sim_odom_node.hpp"

#include <cmath>

#include "tf2/LinearMath/Quaternion.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

namespace translate_sim_odom
{

TranslateSimOdomNode::TranslateSimOdomNode() : rclcpp::Node("translate_sim_odom_node")
{
    // ── Robot geometry params (QD diagonal) ──
    w1_x_ = declare_parameter<double>("w1_x", 0.330);
    w1_y_ = declare_parameter<double>("w1_y", 0.135);
    w2_x_ = declare_parameter<double>("w2_x", -0.330);
    w2_y_ = declare_parameter<double>("w2_y", -0.135);

    // ── Initial pose ──
    initial_x_ = declare_parameter<double>("initial_x", 0.0);
    initial_y_ = declare_parameter<double>("initial_y", 0.0);
    initial_yaw_ = declare_parameter<double>("initial_yaw", 0.0);
    x_.store(initial_x_);
    y_.store(initial_y_);
    yaw_.store(initial_yaw_);

    integrate_rate_hz_ = declare_parameter<double>("integrate_rate_hz", 50.0);

    // IMU yaw offset (S7 calibration test scenario). Default 0 = legacy behavior (IMU == map yaw).
    double imu_yaw_offset_deg = declare_parameter<double>("imu_yaw_offset_deg", 0.0);
    imu_yaw_offset_rad_ = imu_yaw_offset_deg * M_PI / 180.0;

    // ── Subscriber: /motor/wheel_cmd ──
    wheel_cmd_sub_ = create_subscription<trnav_msgs::msg::WheelSetArray>(
        "/motor/wheel_cmd", rclcpp::QoS(10).reliable(),
        [this](const trnav_msgs::msg::WheelSetArray::SharedPtr msg) { wheelCmdCallback(msg); });

    // ── Publishers ──
    // localization_pose: SensorDataQoS (BEST_EFFORT) — amr_translate_node 가
    // translate_pose_qos=2 (sensor_data) 로 구독.
    loc_pose_pub_ = create_publisher<geometry_msgs::msg::PoseWithCovarianceStamped>("/rtabmap/localization_pose",
                                                                                    rclcpp::SensorDataQoS());
    imu_pub_ = create_publisher<sensor_msgs::msg::Imu>("/imu/data", rclcpp::SensorDataQoS());
    wheel_state_pub_ = create_publisher<trnav_msgs::msg::WheelMotor>("/wheel_motor_state", rclcpp::QoS(10));

    // ── TF broadcaster ──
    tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);

    // ── Integration timer ──
    auto period = std::chrono::duration<double>(1.0 / integrate_rate_hz_);
    integrate_timer_ = create_wall_timer(std::chrono::duration_cast<std::chrono::nanoseconds>(period),
                                         [this]() { integrateAndPublish(); });

    RCLCPP_INFO(get_logger(),
                "TranslateSimOdom started. wheels w1=(%.3f,%.3f) w2=(%.3f,%.3f), init=(%.2f,%.2f,%.1fdeg), rate=%.1fHz",
                w1_x_, w1_y_, w2_x_, w2_y_, initial_x_, initial_y_, initial_yaw_ * 180.0 / M_PI, integrate_rate_hz_);
    if (std::fabs(imu_yaw_offset_rad_) > 1e-6)
    {
        RCLCPP_WARN(get_logger(), "IMU yaw offset = %.2f deg (intentional misalignment for calibration test)",
                    imu_yaw_offset_rad_ * 180.0 / M_PI);
    }
}

void TranslateSimOdomNode::wheelCmdCallback(const trnav_msgs::msg::WheelSetArray::SharedPtr msg)
{
    if (msg->wheels.size() < 2)
    {
        RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 1000, "Expected 2 wheels, got %zu — ignoring",
                             msg->wheels.size());
        return;
    }
    std::lock_guard<std::mutex> lock(cmd_mtx_);
    cmd_v0_ = msg->wheels[0].velocity;
    cmd_s0_ = msg->wheels[0].steering;
    cmd_v1_ = msg->wheels[1].velocity;
    cmd_s1_ = msg->wheels[1].steering;
    cmd_received_ = true;
}

void TranslateSimOdomNode::integrateAndPublish()
{
    // ── Integrate ──
    double dt = 1.0 / integrate_rate_hz_;
    if (!first_step_)
    {
        auto now = this->now();
        dt = (now - last_integrate_time_).seconds();
        if (dt <= 0.0 || dt > 0.5)
        {
            dt = 1.0 / integrate_rate_hz_;
        }
        last_integrate_time_ = now;
    }
    else
    {
        last_integrate_time_ = this->now();
        first_step_ = false;
    }

    double v0, s0, v1, s1;
    bool received;
    {
        std::lock_guard<std::mutex> lock(cmd_mtx_);
        v0 = cmd_v0_;
        s0 = cmd_s0_;
        v1 = cmd_v1_;
        s1 = cmd_s1_;
        received = cmd_received_;
    }

    // 2-wheel kinematic body velocity (QD diagonal, wheels[0]=w1, wheels[1]=w2)
    //   v_i = velocity_i (signed)
    //   vx_i = v_i * cos(steering_i)
    //   vy_i = v_i * sin(steering_i)
    //   IK forward eq: vx_i = vx - omega * y_i,  vy_i = vy + omega * x_i
    //   Solve from wheel 0/1:
    //     omega = (vx_1 - vx_2) / (y_2 - y_1)
    //     vx_body = vx_1 + omega * y_1
    //     vy_body = vy_1 - omega * x_1
    double vx_body = 0.0, vy_body = 0.0, omega = 0.0;
    if (received)
    {
        double vx_1 = v0 * std::cos(s0);
        double vy_1 = v0 * std::sin(s0);
        double vx_2 = v1 * std::cos(s1);
        double dy = w2_y_ - w1_y_;
        if (std::fabs(dy) > 1e-6)
        {
            omega = (vx_1 - vx_2) / dy;
            vx_body = vx_1 + omega * w1_y_;
            vy_body = vy_1 - omega * w1_x_;
        }
        else
        {
            omega = 0.0;
            vx_body = (vx_1 + vx_2) / 2.0;
            vy_body = vy_1;
        }
    }

    // Euler integration in map frame
    double cur_yaw = yaw_.load();
    double dx_global = (vx_body * std::cos(cur_yaw) - vy_body * std::sin(cur_yaw)) * dt;
    double dy_global = (vx_body * std::sin(cur_yaw) + vy_body * std::cos(cur_yaw)) * dt;
    double dyaw = omega * dt;

    double new_x = x_.load() + dx_global;
    double new_y = y_.load() + dy_global;
    double new_yaw = std::remainder(cur_yaw + dyaw, 2.0 * M_PI);
    x_.store(new_x);
    y_.store(new_y);
    yaw_.store(new_yaw);

    // ── Publish TF map→base_link ──
    auto stamp = this->now();
    tf2::Quaternion q;
    q.setRPY(0.0, 0.0, new_yaw);

    geometry_msgs::msg::TransformStamped tf;
    tf.header.stamp = stamp;
    tf.header.frame_id = "map";
    tf.child_frame_id = "base_link";
    tf.transform.translation.x = new_x;
    tf.transform.translation.y = new_y;
    tf.transform.translation.z = 0.0;
    tf.transform.rotation.x = q.x();
    tf.transform.rotation.y = q.y();
    tf.transform.rotation.z = q.z();
    tf.transform.rotation.w = q.w();
    tf_broadcaster_->sendTransform(tf);

    // ── Publish /rtabmap/localization_pose ──
    geometry_msgs::msg::PoseWithCovarianceStamped pose_msg;
    pose_msg.header.stamp = stamp;
    pose_msg.header.frame_id = "map";
    pose_msg.pose.pose.position.x = new_x;
    pose_msg.pose.pose.position.y = new_y;
    pose_msg.pose.pose.position.z = 0.0;
    pose_msg.pose.pose.orientation.x = q.x();
    pose_msg.pose.pose.orientation.y = q.y();
    pose_msg.pose.pose.orientation.z = q.z();
    pose_msg.pose.pose.orientation.w = q.w();
    // Covariance: small (충분히 정밀한 SIL pose)
    pose_msg.pose.covariance[0] = 0.001;  // x
    pose_msg.pose.covariance[7] = 0.001;  // y
    pose_msg.pose.covariance[35] = 0.001; // yaw
    loc_pose_pub_->publish(pose_msg);

    // ── Publish /imu/data ──
    // IMU 의 자체 yaw 0 기준이 map 의 yaw 0 과 다른 상황을 모사 (S7 calibration test).
    // imu_published_yaw = ground_truth_yaw + imu_yaw_offset_rad_
    sensor_msgs::msg::Imu imu_msg;
    imu_msg.header.stamp = stamp;
    imu_msg.header.frame_id = "base_link";
    if (std::fabs(imu_yaw_offset_rad_) > 1e-6)
    {
        tf2::Quaternion q_imu;
        q_imu.setRPY(0.0, 0.0, std::remainder(new_yaw + imu_yaw_offset_rad_, 2.0 * M_PI));
        imu_msg.orientation.x = q_imu.x();
        imu_msg.orientation.y = q_imu.y();
        imu_msg.orientation.z = q_imu.z();
        imu_msg.orientation.w = q_imu.w();
    }
    else
    {
        imu_msg.orientation.x = q.x();
        imu_msg.orientation.y = q.y();
        imu_msg.orientation.z = q.z();
        imu_msg.orientation.w = q.w();
    }
    imu_msg.angular_velocity.z = omega;
    imu_msg.linear_acceleration.x = 0.0;
    imu_pub_->publish(imu_msg);

    // ── Publish /wheel_motor_state (cmd echo) ──
    trnav_msgs::msg::WheelMotor wheel_msg;
    wheel_msg.velocity_front = v0;
    wheel_msg.angle_front = s0;
    wheel_msg.velocity_rear = v1;
    wheel_msg.angle_rear = s1;
    wheel_state_pub_->publish(wheel_msg);
}

} // namespace translate_sim_odom
