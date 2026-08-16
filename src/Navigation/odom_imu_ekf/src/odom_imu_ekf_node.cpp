// odom_imu_ekf — 휠 오도 + IMU 융합 노드. Seer 레거시 RobotPosEKF 자리에 대응한다.
//   구독: odom (nav_msgs/Odometry) · imu (sensor_msgs/Imu)
//   발행: odom_fused (nav_msgs/Odometry) · /diagnostics
//
// 레거시와 같이 **두 센서를 다 받기 전에는 발행하지 않는다.** IMU 가 없으면 측위는 이동량을
//   전혀 받지 못한다 — 조용히 멈추지 않도록 진단으로 드러낸다.
#include <cmath>
#include <memory>
#include <optional>

#include "diagnostic_msgs/msg/diagnostic_array.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "odom_imu_ekf/ekf.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/imu.hpp"

using namespace odom_imu_ekf;

namespace
{
// 쿼터니언 → roll·pitch·yaw. IMU 는 세 축을 모두 관측하므로 yaw 만 뽑지 않는다.
void quatToRpy(double x, double y, double z, double w, double &roll, double &pitch, double &yaw)
{
    const double sinr = 2.0 * (w * x + y * z);
    const double cosr = 1.0 - 2.0 * (x * x + y * y);
    roll = std::atan2(sinr, cosr);

    double sinp = 2.0 * (w * y - z * x);
    sinp = std::max(-1.0, std::min(1.0, sinp)); // 수치오차로 |sinp|>1 이 되면 asin 이 NaN 이 된다
    pitch = std::asin(sinp);

    const double siny = 2.0 * (w * z + x * y);
    const double cosy = 1.0 - 2.0 * (y * y + z * z);
    yaw = std::atan2(siny, cosy);
}
} // namespace

class OdomImuEkfNode : public rclcpp::Node
{
  public:
    OdomImuEkfNode() : rclcpp::Node("odom_imu_ekf")
    {
        Params p;
        p.system_noise = declare_parameter<double>("system_noise", p.system_noise);
        p.prior_covariance = declare_parameter<double>("prior_covariance", p.prior_covariance);
        p.odom_measurement_noise = declare_parameter<double>("odom_measurement_noise", p.odom_measurement_noise);
        p.imu_measurement_noise = declare_parameter<double>("imu_measurement_noise", p.imu_measurement_noise);
        // 원본은 이 게이트를 하드코딩하지만, 여기서는 현장 조정이 필요할 수 있어 파라미터로 연다.
        //   기본값은 원본과 같다.
        const double gate_deg = declare_parameter<double>("imu_gate_rate_deg", 1.0);
        p.imu_gate_rate = gate_deg * M_PI / 180.0;
        ekf_ = std::make_unique<OdomImuEkf>(p);

        publish_frame_ = declare_parameter<std::string>("publish_frame_id", "");
        const double diag_hz = declare_parameter<double>("diagnostic_rate_hz", 1.0);

        // 센서 스트림은 BEST_EFFORT 로 구독한다 — icp_odometry·드라이버가 SensorDataQoS 로 내보내면
        //   RELIABLE 구독자에게는 한 건도 오지 않는다(mcl2d 에서 이미 겪은 실패다).
        rclcpp::QoS odom_qos(20);
        odom_qos.best_effort();
        sub_odom_ = create_subscription<nav_msgs::msg::Odometry>(
            "odom", odom_qos, [this](nav_msgs::msg::Odometry::SharedPtr m) { onOdom(*m); });
        sub_imu_ = create_subscription<sensor_msgs::msg::Imu>(
            "imu", rclcpp::SensorDataQoS(), [this](sensor_msgs::msg::Imu::SharedPtr m) { onImu(*m); });

        pub_ = create_publisher<nav_msgs::msg::Odometry>("odom_fused", 10);
        pub_diag_ = create_publisher<diagnostic_msgs::msg::DiagnosticArray>("/diagnostics", 10);
        const double hz = (diag_hz > 0.0) ? diag_hz : 1.0;
        diag_timer_ = create_wall_timer(std::chrono::duration<double>(1.0 / hz), [this]() { publishDiag(); });

        RCLCPP_INFO(get_logger(), "odom_imu_ekf 기동 — IMU 게이트 %.2f deg/s. 오도·IMU 를 둘 다 받아야 발행한다",
                    gate_deg);
    }

  private:
    void onImu(const sensor_msgs::msg::Imu &m)
    {
        double r, p, y;
        quatToRpy(m.orientation.x, m.orientation.y, m.orientation.z, m.orientation.w, r, p, y);
        ekf_->addImu(r, p, y);
        imu_seen_ = true;
    }

    // 오도 수신이 한 주기를 돌린다 — 레거시도 오도를 받은 뒤에 융합·발행한다.
    void onOdom(const nav_msgs::msg::Odometry &m)
    {
        double r, p, y;
        quatToRpy(m.pose.pose.orientation.x, m.pose.pose.orientation.y, m.pose.pose.orientation.z,
                  m.pose.pose.orientation.w, r, p, y);
        Pose3D pose;
        pose.x = m.pose.pose.position.x;
        pose.y = m.pose.pose.position.y;
        pose.z = m.pose.pose.position.z;
        pose.roll = r;
        pose.pitch = p;
        pose.yaw = y;

        // 게이트 판정에 쓰는 회전율은 오도가 보고한 값이다(원본 wzOdoAbsDeg 가 odom.vel_rotate 다).
        ekf_->addOdom(pose, m.twist.twist.angular.z);
        if (!ekf_->update())
            return; // IMU 를 아직 못 받았다 — 레거시와 같이 발행하지 않는다

        // 자세만 융합 결과로 바꾸고 나머지는 수신 메시지를 그대로 물려 보낸다
        //   (원본 run() 이 CopyFrom 뒤에 getFilterOdometer 로 자세만 덮는 것과 같다).
        nav_msgs::msg::Odometry out = m;
        if (!publish_frame_.empty())
            out.header.frame_id = publish_frame_;
        const Pose3D &f = ekf_->pose();
        out.pose.pose.position.x = f.x;
        out.pose.pose.position.y = f.y;
        out.pose.pose.position.z = f.z;
        const double cy = std::cos(f.yaw * 0.5), sy = std::sin(f.yaw * 0.5);
        const double cp = std::cos(f.pitch * 0.5), sp = std::sin(f.pitch * 0.5);
        const double cr = std::cos(f.roll * 0.5), sr = std::sin(f.roll * 0.5);
        out.pose.pose.orientation.w = cr * cp * cy + sr * sp * sy;
        out.pose.pose.orientation.x = sr * cp * cy - cr * sp * sy;
        out.pose.pose.orientation.y = cr * sp * cy + sr * cp * sy;
        out.pose.pose.orientation.z = cr * cp * sy - sr * sp * cy;
        pub_->publish(out);
        ++published_;
    }

    void publishDiag()
    {
        diagnostic_msgs::msg::DiagnosticStatus st;
        st.name = std::string(get_name()) + ": odom-imu fusion";
        st.hardware_id = get_name();
        if (!imu_seen_)
        {
            // 조용한 무발행을 막는다 — 레거시도 이 상태에서는 아무것도 내보내지 않는다.
            st.level = diagnostic_msgs::msg::DiagnosticStatus::ERROR;
            st.message = "IMU not received — fused odom is not published";
        }
        else if (!ekf_->odomInitialized())
        {
            st.level = diagnostic_msgs::msg::DiagnosticStatus::WARN;
            st.message = "waiting for odom";
        }
        else
        {
            st.level = diagnostic_msgs::msg::DiagnosticStatus::OK;
            st.message = "ok";
        }
        auto kv = [&st](const std::string &k, const std::string &v) {
            diagnostic_msgs::msg::KeyValue e;
            e.key = k;
            e.value = v;
            st.values.push_back(e);
        };
        kv("imu_received", imu_seen_ ? "true" : "false");
        kv("odom_initialized", ekf_->odomInitialized() ? "true" : "false");
        kv("imu_initialized", ekf_->imuInitialized() ? "true" : "false");
        kv("last_imu_applied", ekf_->lastImuApplied() ? "true" : "false");
        kv("published", std::to_string(published_));

        diagnostic_msgs::msg::DiagnosticArray arr;
        arr.header.stamp = now();
        arr.status.push_back(st);
        pub_diag_->publish(arr);
    }

    std::unique_ptr<OdomImuEkf> ekf_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr sub_odom_;
    rclcpp::Subscription<sensor_msgs::msg::Imu>::SharedPtr sub_imu_;
    rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr pub_;
    rclcpp::Publisher<diagnostic_msgs::msg::DiagnosticArray>::SharedPtr pub_diag_;
    rclcpp::TimerBase::SharedPtr diag_timer_;
    std::string publish_frame_;
    bool imu_seen_ = false;
    std::uint64_t published_ = 0;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<OdomImuEkfNode>());
    rclcpp::shutdown();
    return 0;
}
