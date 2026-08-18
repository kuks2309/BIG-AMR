#include "translate_sim_odom/translate_sim_odom_node.hpp"

#include <cmath>
#include <limits>
#include <stdexcept>

#include "tf2/LinearMath/Quaternion.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"

namespace translate_sim_odom
{

TranslateSimOdomNode::TranslateSimOdomNode() : rclcpp::Node("translate_sim_odom_node")
{
    // ── 휠 기하 ──
    // **기본값을 두지 않는다.** 이 노드는 2WS·QD 플랜트로 모두 쓰이므로 어느 한쪽 값을
    //   기본값으로 두면 다른 쪽이 파라미터 없이 떴을 때 **조용히 남의 기하로 돈다** —
    //   플랜트가 컨트롤러와 어긋나면 SIL 이 검증하는 대상이 사라진다.
    //   정본은 런치가 얹는다(robot_geometry_2ws.yaml | robot_geometry_qd.yaml).
    //   미주입은 기동 실패로 처리한다 — 형제 노드 wheel_odometry.py 와 같은 규약이다.
    const double kUnset = std::numeric_limits<double>::quiet_NaN();
    w1_x_ = declare_parameter<double>("w1_x", kUnset);
    w1_y_ = declare_parameter<double>("w1_y", kUnset);
    w2_x_ = declare_parameter<double>("w2_x", kUnset);
    w2_y_ = declare_parameter<double>("w2_y", kUnset);
    if (std::isnan(w1_x_) || std::isnan(w1_y_) || std::isnan(w2_x_) || std::isnan(w2_y_))
    {
        throw std::runtime_error(
            "휠 기하 파라미터 미주입(w1_x/w1_y/w2_x/w2_y) — 런치가 기하 정본 YAML 을 얹어야 한다");
    }

    // ── Initial pose ──
    initial_x_ = declare_parameter<double>("initial_x", 0.0);
    initial_y_ = declare_parameter<double>("initial_y", 0.0);
    initial_yaw_ = declare_parameter<double>("initial_yaw", 0.0);
    x_.store(initial_x_);
    y_.store(initial_y_);
    yaw_.store(initial_yaw_);

    integrate_rate_hz_ = declare_parameter<double>("integrate_rate_hz", 50.0);

    // ── 구동·조향 동특성 ──
    // ⚠ 기본값 0 은 '제한 없음' 이라 지령이 곧 실제값인 즉응 모델이 된다. 이 노드를 QD·2WS 의
    //   SIL·HIL 런치 여러 개가 공유하고 일부는 이미 검증을 마쳤으므로, 기본값을 켜는 쪽으로
    //   바꾸면 그 검증이 말없이 무효가 된다. 동특성은 런치가 **명시적으로 켤 때만** 쓴다.
    //   권장값과 그 한계는 헤더 주석에 있다 — 자릿수 감으로만 쓸 것.
    drive_accel_mps2_ = declare_parameter<double>("drive_accel_mps2", 0.0);
    drive_decel_mps2_ = declare_parameter<double>("drive_decel_mps2", 0.0);
    steer_rate_rad_s_ = declare_parameter<double>("steer_rate_dps", 0.0) * M_PI / 180.0;

    // ── 엔코더 환산 상수 — translator YAML 과 같은 값을 쓴다 ──
    wheel_radius_ = declare_parameter<double>("wheel_radius", 0.125);
    pulses_per_rev_ = declare_parameter<double>("pulses_per_rev", 65536.0);
    gear_walk_ = declare_parameter<double>("gear_walk", 32.0);
    gear_steer_ = declare_parameter<double>("gear_steer", 315.0);

    // ── IMU yaw 잡음 (deg 1σ). 기본 0 ──
    imu_yaw_noise_rad_ = declare_parameter<double>("imu_yaw_noise_deg", 0.0) * M_PI / 180.0;

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
    // 엔코더 counts 를 담은 상세 상태. 상위가 속도 적분 대신 **위치**로 진행량을 풀 수 있게 한다 —
    //   실기 드라이브가 위치를 올려 주므로 SIL 도 같은 수단을 제공해야 액션 코드가 갈리지 않는다.
    wheel_state_detailed_pub_ =
        create_publisher<trnav_msgs::msg::WheelMotorState>("/wheel_motor_state_detailed", rclcpp::QoS(10));

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
    // 어느 모드로 도는지 로그에 남긴다 — 「즉응 플랜트로 통과한 결과」를 나중에 구분해야 한다.
    const bool dyn_on = (drive_accel_mps2_ > 0.0 || drive_decel_mps2_ > 0.0 || steer_rate_rad_s_ > 0.0);
    RCLCPP_INFO(get_logger(),
                "동특성 %s — 구동 가속 %.4f / 감속 %.4f m/s², 조향 슬루 %.1f deg/s, IMU yaw 잡음 %.3f deg",
                dyn_on ? "활성" : "비활성(즉응, 종전 거동)", drive_accel_mps2_, drive_decel_mps2_,
                steer_rate_rad_s_ * 180.0 / M_PI, imu_yaw_noise_rad_ * 180.0 / M_PI);
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

    double tgt_v0, tgt_s0, tgt_v1, tgt_s1;
    bool received;
    {
        std::lock_guard<std::mutex> lock(cmd_mtx_);
        tgt_v0 = cmd_v0_;
        tgt_s0 = cmd_s0_;
        tgt_v1 = cmd_v1_;
        tgt_s1 = cmd_s1_;
        received = cmd_received_;
    }

    // ── 동특성 — 지령을 즉시 따르지 않는다 ──
    // 구동: 크기가 줄어드는 방향(정지 포함)이면 감속 한계, 늘어나는 방향이면 가속 한계.
    //   부호가 뒤집히는 지령은 0 을 지나가므로 감속 한계가 먼저 적용된다.
    //   ⇒ 지령을 0 으로 끊어도 바퀴는 계속 구르고, 그동안의 회전이 엔코더에 그대로 쌓인다.
    // 조향: 슬루율 제한. 조향축은 ±115° 범위의 **비순환** 축이므로 최단경로 보정을 하지 않고
    //   선형으로 이동시킨다(물리 거동과 일치).
    auto slew_vel = [this](double actual, double target, double step_dt) {
        const bool decreasing = std::fabs(target) < std::fabs(actual) || (actual * target < 0.0);
        const double lim = decreasing ? drive_decel_mps2_ : drive_accel_mps2_;
        if (lim <= 0.0)
        {
            return target;
        }
        const double max_step = lim * step_dt;
        const double diff = target - actual;
        return (std::fabs(diff) <= max_step) ? target : actual + std::copysign(max_step, diff);
    };
    auto slew_ang = [this](double actual, double target, double step_dt) {
        if (steer_rate_rad_s_ <= 0.0)
        {
            return target;
        }
        const double max_step = steer_rate_rad_s_ * step_dt;
        const double diff = target - actual;
        return (std::fabs(diff) <= max_step) ? target : actual + std::copysign(max_step, diff);
    };

    if (received)
    {
        act_v0_ = slew_vel(act_v0_, tgt_v0, dt);
        act_v1_ = slew_vel(act_v1_, tgt_v1, dt);
        act_s0_ = slew_ang(act_s0_, tgt_s0, dt);
        act_s1_ = slew_ang(act_s1_, tgt_s1, dt);
    }

    // 정기구학은 **지령이 아니라 실제값** 으로 푼다.
    const double v0 = act_v0_;
    const double s0 = act_s0_;
    const double v1 = act_v1_;
    const double s1 = act_s1_;

    // ── 엔코더 — 실제 속도로 휠 주행거리 누적 ──
    // 관성 구간의 이동도 여기 들어온다. 상위가 이 값을 읽으면 「정착 대기 시간」 없이
    // 실제 진행량을 알 수 있다.
    travel0_m_ += v0 * dt;
    travel1_m_ += v1 * dt;

    // 2-wheel 정기구학 역산 (wheels[0]=w1, wheels[1]=w2)
    //   v_i = velocity_i (signed) · vx_i = v_i cos(θ_i) · vy_i = v_i sin(θ_i)
    //   IK forward eq: vx_i = vx - ω·y_i ,  vy_i = vy + ω·x_i
    //
    // 미지수 3(vx, vy, ω)에 식 4 — **과결정**이라 ω 를 어느 쌍에서 뽑을지 골라야 한다.
    //   x 성분 쌍:  vx_1 - vx_2 = ω(y_2 - y_1)  →  분모 = 두 바퀴의 **y 간격**
    //   y 성분 쌍:  vy_1 - vy_2 = ω(x_1 - x_2)  →  분모 = 두 바퀴의 **x 간격**
    //
    // ⚠ 어느 쌍을 쓰든 되는 것이 아니다 — 배치에 따라 한쪽 분모가 0 이 된다.
    //   QD(대각 배치)는 y 간격이 있어 x 성분 쌍이 잘 조건화되지만,
    //   **inline(2WS)은 y_1 = y_2 라 x 성분 쌍의 분모가 0** 이다. 그 경우 ω 가 0 으로 강제되면
    //   상위가 어떤 각속도를 지령해도 플랜트가 조용히 버려서, spin·turn 이 SIL 에서 재현되지 않고
    //   크랩의 yaw 유지 루프도 검증되지 않는다(yaw 가 변하지 않으니 heading error 가 늘 0 이다).
    //   ⇒ **분모가 큰 쪽**을 고른다. inline 에서는 x 간격이 휠베이스라 그쪽이 잘 조건화된다.
    //     대각 배치에서는 둘 다 유효하며 큰 쪽을 고르므로 QD 거동은 바뀌지 않는다.
    double vx_body = 0.0, vy_body = 0.0, omega = 0.0;
    if (received)
    {
        const double vx_1 = v0 * std::cos(s0);
        const double vy_1 = v0 * std::sin(s0);
        const double vx_2 = v1 * std::cos(s1);
        const double vy_2 = v1 * std::sin(s1);
        const double dy = w2_y_ - w1_y_;   // x 성분 쌍의 분모
        const double dx = w1_x_ - w2_x_;   // y 성분 쌍의 분모
        if (std::fabs(dx) >= std::fabs(dy) && std::fabs(dx) > 1e-6)
        {
            omega = (vy_1 - vy_2) / dx;
        }
        else if (std::fabs(dy) > 1e-6)
        {
            omega = (vx_1 - vx_2) / dy;
        }
        else
        {
            omega = 0.0;   // 두 바퀴가 같은 점 — 회전을 정할 수 없다
        }
        vx_body = vx_1 + omega * w1_y_;
        vy_body = vy_1 - omega * w1_x_;
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
    // yaw 잡음은 **발행값에만** 실는다 — 지상진값(TF·pose)은 오염시키지 않는다.
    // 상위가 yaw 를 누적하는 경로에서 방향 판정을 하는지(뒤로 튄 델타를 빼는지)는
    // 잡음이 없으면 원리적으로 구분되지 않는다. 기본 0 이므로 켤 때만 작동한다.
    double yaw_noise = 0.0;
    if (imu_yaw_noise_rad_ > 0.0)
    {
        yaw_noise = imu_yaw_noise_rad_ * noise_dist_(noise_rng_);
    }

    sensor_msgs::msg::Imu imu_msg;
    imu_msg.header.stamp = stamp;
    imu_msg.header.frame_id = "base_link";
    if (std::fabs(imu_yaw_offset_rad_) > 1e-6 || yaw_noise != 0.0)
    {
        tf2::Quaternion q_imu;
        q_imu.setRPY(0.0, 0.0, std::remainder(new_yaw + imu_yaw_offset_rad_ + yaw_noise, 2.0 * M_PI));
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

    // ── Publish /wheel_motor_state — 지령이 아니라 동특성을 통과한 **실제값**을 싣는다 ──
    trnav_msgs::msg::WheelMotor wheel_msg;
    wheel_msg.velocity_front = v0;
    wheel_msg.angle_front = s0;
    wheel_msg.velocity_rear = v1;
    wheel_msg.angle_rear = s1;
    wheel_state_pub_->publish(wheel_msg);

    // ── Publish /wheel_motor_state_detailed (엔코더 counts) ──
    // 환산은 translator 와 같은 식이다:
    //   구동 counts = 주행거리 / (2πr) × pulses_per_rev × gear_walk
    //   조향 counts = 각(rad) / 2π      × pulses_per_rev × gear_steer   ← **홈 기준 상대**
    // (can_relay 가 조향축에서 홈 오프셋을 빼 올리는 것과 같은 좌표계.)
    const double counts_per_m = pulses_per_rev_ * gear_walk_ / (2.0 * M_PI * wheel_radius_);
    const double counts_per_rad = pulses_per_rev_ * gear_steer_ / (2.0 * M_PI);

    trnav_msgs::msg::WheelMotorState det;
    det.header.stamp = stamp;
    det.header.frame_id = "base_link";
    det.encoder_walk_front = static_cast<int32_t>(std::llround(travel0_m_ * counts_per_m));
    det.encoder_walk_rear = static_cast<int32_t>(std::llround(travel1_m_ * counts_per_m));
    det.encoder_steer_front = static_cast<int32_t>(std::llround(s0 * counts_per_rad));
    det.encoder_steer_rear = static_cast<int32_t>(std::llround(s1 * counts_per_rad));
    det.velocity_front = v0;
    det.velocity_rear = v1;
    det.angle_front = s0;
    det.angle_rear = s1;
    det.motor_ready = received;
    det.error_code = 0;
    wheel_state_detailed_pub_->publish(det);
}

} // namespace translate_sim_odom
