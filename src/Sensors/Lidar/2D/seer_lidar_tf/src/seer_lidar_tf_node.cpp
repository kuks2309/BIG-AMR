// SEER SRC 컨트롤러에서 각 2D LiDAR 의 장착 pose(install_info: x/y/yaw)를 읽어
// `parent_frame -> <lidar>_frame` 정적 TF 로 발행한다.
//
// install_info 는 2D(x/y/yaw)만 제공하므로 z/roll/pitch = 0 (z 는 파라미터로 override 가능).
// 장착 캘리브는 거의 불변이므로 기본은 1회 읽어 latch. poll_period > 0 이면 주기 재조회한다.
//
// 프로토콜 구현은 여기 있지 않다 — seer_tcp_ip 가 저장소에서 Seer 와 TCP 로 말하는 유일한 지점이다.
#include <cmath>
#include <fstream>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include <geometry_msgs/msg/transform_stamped.hpp>
#include <rclcpp/rclcpp.hpp>
#include <tf2_ros/static_transform_broadcaster.h>

#include "seer_tcp_ip/api.hpp"

namespace
{

/// roll=pitch=0 인 yaw-only 쿼터니언.
void yawToQuat(double yawRad, double &x, double &y, double &z, double &w)
{
    x = 0.0;
    y = 0.0;
    z = std::sin(yawRad * 0.5);
    w = std::cos(yawRad * 0.5);
}

}  // namespace

class SeerLidarTf : public rclcpp::Node
{
  public:
    SeerLidarTf() : rclcpp::Node("seer_lidar_tf")
    {
        seer_ip_ = declare_parameter<std::string>("seer_ip", "192.168.44.82");
        seer_port_ = static_cast<std::uint16_t>(declare_parameter<int>("seer_port", 19204));
        parent_frame_ = declare_parameter<std::string>("parent_frame", "base_footprint");
        front_frame_ = declare_parameter<std::string>("front_frame", "scan_front");
        rear_frame_ = declare_parameter<std::string>("rear_frame", "scan_rear");
        // install_info 미제공 축 override (실측 장착 높이 등)
        z_front_ = declare_parameter<double>("z_front", 0.0);
        z_rear_ = declare_parameter<double>("z_rear", 0.0);
        connect_timeout_ = declare_parameter<double>("connect_timeout", 3.0);
        retry_period_ = declare_parameter<double>("retry_period", 5.0);
        // 0.0 = 1회만 읽고 latch. >0 = 주기 재조회(초).
        poll_period_ = declare_parameter<double>("poll_period", 0.0);
        // 값이 있으면 Seer 조회 → merger calibration YAML 로 써넣고 종료(TF 는 발행하지 않는다).
        calibration_out_ = declare_parameter<std::string>("calibration_out", "");

        // 조회 전용(19204). 지령 포트를 넣으면 seer_tcp_ip 게이트가 막는다(의도된 동작).
        api_ = std::make_unique<seer_tcp_ip::SeerApi>(seer_ip_, connect_timeout_);

        if (!calibration_out_.empty())
        {
            RCLCPP_INFO(get_logger(), "[write 모드] %s:%u 조회 → %s 기록 후 종료", seer_ip_.c_str(),
                        seer_port_, calibration_out_.c_str());
            writeOnce();
            return;
        }

        broadcaster_ = std::make_shared<tf2_ros::StaticTransformBroadcaster>(this);
        const double period = poll_period_ > 0.0 ? poll_period_ : retry_period_;
        timer_ = create_wall_timer(std::chrono::duration<double>(period), [this] { tick(); });
        RCLCPP_INFO(get_logger(), "[publish 모드] %s:%u API %u -> %s->(%s,%s), %s",
                    seer_ip_.c_str(), seer_port_, seer_tcp_ip::api::kLaser, parent_frame_.c_str(),
                    front_frame_.c_str(), rear_frame_.c_str(),
                    poll_period_ <= 0.0 ? "1회 latch" : "주기 폴링");
        tick();  // 시작 즉시 1회 시도
    }

    bool done() const { return done_; }

  private:
    /// 레이저 목록 조회. 응답 편호·seq 대조와 부분 수신 처리는 seer_tcp_ip 가 한다.
    seer_tcp_ip::Json queryLasers()
    {
        return api_->call(seer_port_, seer_tcp_ip::api::kLaser)
            .value("lasers", seer_tcp_ip::Json::array());
    }

    /// device_name → (frame, z). front/rear 부분일치, 그 외는 매핑 없음.
    bool frameFor(const std::string &deviceName, std::string &frame, double &z) const
    {
        std::string low;
        for (char c : deviceName)
        {
            low += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        }
        if (low.find("front") != std::string::npos)
        {
            frame = front_frame_;
            z = z_front_;
            return true;
        }
        if (low.find("rear") != std::string::npos)
        {
            frame = rear_frame_;
            z = z_rear_;
            return true;
        }
        return false;
    }

    void tick()
    {
        seer_tcp_ip::Json lasers;
        try
        {
            lasers = queryLasers();
        }
        catch (const std::exception &e)
        {
            RCLCPP_WARN(get_logger(), "Seer 조회 실패(%s) — %.1fs 후 재시도", e.what(),
                        retry_period_);
            return;
        }

        const auto transforms = buildTransforms(lasers);
        if (transforms.empty())
        {
            RCLCPP_WARN(get_logger(), "install_info 를 가진 laser 가 없음 — 재시도");
            return;
        }
        broadcaster_->sendTransform(transforms);
        std::string names;
        for (const auto &t : transforms)
        {
            names += (names.empty() ? "" : ", ") + t.child_frame_id;
        }
        RCLCPP_INFO(get_logger(), "TF 발행 완료: %s -> [%s]", parent_frame_.c_str(), names.c_str());
        if (poll_period_ <= 0.0)
        {
            timer_->cancel();  // latch 후 종료(static 은 계속 유지된다)
        }
    }

    std::vector<geometry_msgs::msg::TransformStamped> buildTransforms(
        const seer_tcp_ip::Json &lasers)
    {
        std::vector<geometry_msgs::msg::TransformStamped> out;
        const auto stamp = now();
        for (const auto &laser : lasers)
        {
            const std::string dev =
                laser.value("device_info", seer_tcp_ip::Json::object()).value("device_name", "");
            if (!laser.contains("install_info"))
            {
                continue;
            }
            const auto ii = laser.at("install_info");
            std::string child;
            double z = 0.0;
            if (!frameFor(dev, child, z))
            {
                RCLCPP_WARN(get_logger(), "매핑 없는 device '%s' — 건너뜀", dev.c_str());
                continue;
            }
            geometry_msgs::msg::TransformStamped t;
            t.header.stamp = stamp;
            t.header.frame_id = parent_frame_;
            t.child_frame_id = child;
            t.transform.translation.x = ii.value("x", 0.0);
            t.transform.translation.y = ii.value("y", 0.0);
            t.transform.translation.z = z;
            yawToQuat(ii.value("yaw", 0.0) * M_PI / 180.0, t.transform.rotation.x,
                      t.transform.rotation.y, t.transform.rotation.z, t.transform.rotation.w);
            out.push_back(t);
            RCLCPP_INFO(get_logger(), "  %s: x=%.4f y=%.4f yaw=%.3fdeg -> %s", dev.c_str(),
                        ii.value("x", 0.0), ii.value("y", 0.0), ii.value("yaw", 0.0),
                        child.c_str());
        }
        return out;
    }

    void writeOnce()
    {
        seer_tcp_ip::Json lasers;
        try
        {
            lasers = queryLasers();
        }
        catch (const std::exception &e)
        {
            RCLCPP_ERROR(get_logger(), "Seer 조회 실패(%s) — 기록 안 함", e.what());
            done_ = true;
            return;
        }
        std::map<std::string, std::array<double, 3>> poses;
        for (const auto &laser : lasers)
        {
            const std::string dev =
                laser.value("device_info", seer_tcp_ip::Json::object()).value("device_name", "");
            if (!laser.contains("install_info"))
            {
                continue;
            }
            const auto ii = laser.at("install_info");
            std::string child;
            double z = 0.0;
            if (frameFor(dev, child, z))
            {
                poses[child] = {ii.value("x", 0.0), ii.value("y", 0.0), ii.value("yaw", 0.0)};
                RCLCPP_INFO(get_logger(), "  %s: x=%.4f y=%.4f yaw=%.3fdeg -> %s", dev.c_str(),
                            ii.value("x", 0.0), ii.value("y", 0.0), ii.value("yaw", 0.0),
                            child.c_str());
            }
        }
        if (poses.count(front_frame_) == 0 || poses.count(rear_frame_) == 0)
        {
            RCLCPP_ERROR(get_logger(), "front/rear pose 부족 — 기록 안 함");
            done_ = true;
            return;
        }
        writeCalibrationYaml(poses);
        done_ = true;
    }

    void writeCalibrationYaml(const std::map<std::string, std::array<double, 3>> &poses)
    {
        const auto &f = poses.at(front_frame_);
        const auto &r = poses.at(rear_frame_);
        const double fyawR = f[2] * M_PI / 180.0;
        const double ryawR = r[2] * M_PI / 180.0;
        std::ofstream os(calibration_out_);
        if (!os)
        {
            RCLCPP_ERROR(get_logger(), "calibration 파일을 열 수 없다: %s",
                         calibration_out_.c_str());
            return;
        }
        os.setf(std::ios::fixed);
        os.precision(17);
        os << "# SEER install_info -> merger calibration (seer_lidar_tf write 모드 생성)\n"
           << "# 출처: SEER " << seer_ip_ << ":" << seer_port_ << " API " << seer_tcp_ip::api::kLaser
           << ". install_info 는 2D(x/y/yaw)만 제공 -> z/roll=0, icp=0.\n"
           << "calibration:\n"
           << "  reference_frame: merged_lidar\n"
           << "  reference_sensor: /" << front_frame_ << "\n"
           << "  calibrated_sensor: /" << rear_frame_ << "\n"
           << "  icp_correction: {dx: 0.0, dy: 0.0, dyaw_rad: 0.0, dyaw_deg: 0.0}\n"
           << "  merged_lidar_to_scan_front:\n"
           << "    tx: " << f[0] << "\n    ty: " << f[1] << "\n    yaw_rad: " << fyawR
           << "\n    yaw_deg: " << f[2] << "\n    flipped: true\n"
           << "  merged_lidar_to_scan_rear_original:\n"
           << "    tx: " << r[0] << "\n    ty: " << r[1] << "\n    yaw_rad: " << ryawR
           << "\n    yaw_deg: " << r[2] << "\n    flipped: true\n"
           << "  merged_lidar_to_scan_rear_corrected:\n"
           << "    tx: " << r[0] << "\n    ty: " << r[1] << "\n    yaw_rad: " << ryawR
           << "\n    yaw_deg: " << r[2] << "\n    flipped: true\n";
        RCLCPP_INFO(get_logger(), "calibration 기록 완료: %s", calibration_out_.c_str());
    }

    std::string seer_ip_, parent_frame_, front_frame_, rear_frame_, calibration_out_;
    std::uint16_t seer_port_ = 19204;
    double z_front_ = 0.0, z_rear_ = 0.0, connect_timeout_ = 3.0, retry_period_ = 5.0,
           poll_period_ = 0.0;
    bool done_ = false;
    std::unique_ptr<seer_tcp_ip::SeerApi> api_;
    std::shared_ptr<tf2_ros::StaticTransformBroadcaster> broadcaster_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<SeerLidarTf>();
    if (!node->done())
    {
        rclcpp::spin(node);  // publish 모드: latch TF 유지
    }
    rclcpp::shutdown();
    return 0;
}
