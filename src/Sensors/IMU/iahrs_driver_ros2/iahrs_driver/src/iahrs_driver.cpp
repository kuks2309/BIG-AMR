// iahrs_driver - ROS2 driver for iAHRS IMU sensor
// Refactored: 2026-02-14 (Code Review fixes applied)

#include <chrono>
#include <memory>
#include <cmath>       // M4: C++ style header
#include <cstdio>      // M4
#include <cstdlib>     // M4
#include <cstring>     // M4
#include <termios.h>
#include <unistd.h>
#include <sys/fcntl.h>
#include <ctime>       // M4
#include <sys/types.h>
#include <string>
#include <mutex>       // C2: thread safety

#include "rclcpp/rclcpp.hpp"
// M3: Removed unused std_msgs/msg/float64.hpp, sensor_msgs/msg/magnetic_field.hpp
#include "sensor_msgs/msg/imu.hpp"
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "tf2_ros/transform_broadcaster.h"
#include "tf2/LinearMath/Quaternion.h"
#include "std_msgs/msg/bool.hpp"
#include "interfaces/srv/imu_reset.hpp"

// M3: Removed unused includes: dirent.h, pthread.h, signal.h, atomic, vector, iostream

#define SERIAL_SPEED B115200

using namespace std::chrono_literals;

// [C1,C2,H1-H7,M1-M8] All fixes integrated into IAHRS class
class IAHRS : public rclcpp::Node
{
public:
	IAHRS() : Node("iahrs_driver")
	{
		// H1, H4: Parameters with default values (serial_port parameterized)
		this->declare_parameter("serial_port", "/dev/IMU");
		this->declare_parameter("m_bSingle_TF_option", true);
		this->declare_parameter("tf_translation_z", 0.2);

		serial_port_ = this->get_parameter("serial_port").as_string();
		single_tf_option_ = this->get_parameter("m_bSingle_TF_option").as_bool();
		tf_translation_z_ = this->get_parameter("tf_translation_z").as_double();

		// Publisher QoS: RELIABLE (SensorData 깊이 유지). RELIABLE 발행자는 RELIABLE·
		// BEST_EFFORT 구독자 모두에 호환 — 기본 QoS(RELIABLE)로 IMU 를 구독하는 SLAM
		// 노드도, BEST_EFFORT 구독자도 전부 수신 가능. (과거 SensorDataQoS=BEST_EFFORT
		// 발행 시 RELIABLE 구독자가 비호환으로 IMU 미수신이었던 이력에 따른 고정.)
		imu_data_pub_ = this->create_publisher<sensor_msgs::msg::Imu>(
			"imu/data", rclcpp::SensorDataQoS().reliable());

		// TF broadcaster
		tf_broadcaster_ = std::make_shared<tf2_ros::TransformBroadcaster>(this);

		// Service
		euler_angle_reset_srv_ = create_service<interfaces::srv::ImuReset>(
			"all_data_reset",
			std::bind(&IAHRS::euler_angle_reset_callback, this, std::placeholders::_1, std::placeholders::_2));

		// Topic-based reset subscriber
		reset_sub_ = this->create_subscription<std_msgs::msg::Bool>(
			"imu/reset", 10,
			std::bind(&IAHRS::reset_topic_callback, this, std::placeholders::_1));

		// M6: Initialize covariance with named constants (from IMU datasheet)
		imu_data_msg_.linear_acceleration_covariance[0] = kLinearAccelCovX;
		imu_data_msg_.linear_acceleration_covariance[4] = kLinearAccelCovY;
		imu_data_msg_.linear_acceleration_covariance[8] = kLinearAccelCovZ;
		imu_data_msg_.angular_velocity_covariance[0] = kAngularVelCovX * kDegToRad;
		imu_data_msg_.angular_velocity_covariance[4] = kAngularVelCovY * kDegToRad;
		imu_data_msg_.angular_velocity_covariance[8] = kAngularVelCovZ * kDegToRad;
		imu_data_msg_.orientation_covariance[0] = kOrientationCovX * kDegToRad;
		imu_data_msg_.orientation_covariance[4] = kOrientationCovY * kDegToRad;
		imu_data_msg_.orientation_covariance[8] = kOrientationCovZ * kDegToRad;

		// C1: Open serial with error handling
		if (serial_open() != 0) {
			RCLCPP_FATAL(this->get_logger(), "Failed to open serial port: %s", serial_port_.c_str());
			throw std::runtime_error("Failed to open serial port");
		}

		// Initial euler angle reset
		double init_data[kMaxData];
		send_recv("za\n", init_data, kMaxData);
		usleep(10000);

		// M1: ASCII art via RCLCPP logging
		RCLCPP_INFO(this->get_logger(), "                       | Z axis");
		RCLCPP_INFO(this->get_logger(), "                       |");
		RCLCPP_INFO(this->get_logger(), "                       |   / X axis");
		RCLCPP_INFO(this->get_logger(), "                   ____|__/____");
		RCLCPP_INFO(this->get_logger(), "      Y axis     / *   | /    /|");
		RCLCPP_INFO(this->get_logger(), "      _________ /______|/    //");
		RCLCPP_INFO(this->get_logger(), "               /___________ //");
		RCLCPP_INFO(this->get_logger(), "              |____iahrs___|/");

		// M5: Timer-based callback at 100Hz (ROS2 style)
		timer_ = this->create_wall_timer(10ms, std::bind(&IAHRS::timer_callback, this));

		RCLCPP_INFO(this->get_logger(), "iAHRS driver initialized successfully");
	}

	~IAHRS()
	{
		if (serial_fd_ >= 0) {
			close(serial_fd_);
			serial_fd_ = -1;
			RCLCPP_INFO(this->get_logger(), "Serial port closed");
		}
	}

private:
	// M6: Covariance constants from IMU datasheet
	static constexpr double kDegToRad = M_PI / 180.0;
	static constexpr double kGToMps2 = 9.80665;
	static constexpr double kLinearAccelCovX = 0.0064;
	static constexpr double kLinearAccelCovY = 0.0063;
	static constexpr double kLinearAccelCovZ = 0.0064;
	static constexpr double kAngularVelCovX = 0.032;
	static constexpr double kAngularVelCovY = 0.028;
	static constexpr double kAngularVelCovZ = 0.006;
	static constexpr double kOrientationCovX = 0.013;
	static constexpr double kOrientationCovY = 0.011;
	static constexpr double kOrientationCovZ = 0.006;
	static constexpr int kCommRecvTimeout = 30;
	static constexpr int kMaxReconnectAttempts = 3;
	static constexpr int kRecvBuffSize = 1024;
	static constexpr int kMaxData = 10;
	static constexpr int kReconnectThreshold = 10;

	// H1: Parameters (serial_port parameterized, not hardcoded)
	std::string serial_port_;
	bool single_tf_option_;
	double tf_translation_z_;  // M7: TF translation parameterized

	// H2: Serial state as class members (not global)
	int serial_fd_ = -1;
	std::mutex serial_mutex_;  // C2: thread safety for serial access
	int consecutive_failures_ = 0;  // H7: reconnection tracking

	// M2: Only Euler angles needed (removed redundant IMU_DATA struct)
	double euler_roll_ = 0.0;
	double euler_pitch_ = 0.0;
	double euler_yaw_ = 0.0;

	// H3: All ROS2 members are private
	std::shared_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
	rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr imu_data_pub_;
	rclcpp::Service<interfaces::srv::ImuReset>::SharedPtr euler_angle_reset_srv_;
	rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr reset_sub_;
	rclcpp::TimerBase::SharedPtr timer_;
	sensor_msgs::msg::Imu imu_data_msg_;
	geometry_msgs::msg::TransformStamped transform_stamped_;

	// M1: Serial open with RCLCPP logging
	int serial_open()
	{
		RCLCPP_INFO(this->get_logger(), "Opening serial port: %s", serial_port_.c_str());

		serial_fd_ = open(serial_port_.c_str(), O_RDWR | O_NOCTTY);
		if (serial_fd_ < 0) {
			RCLCPP_ERROR(this->get_logger(), "Failed to open %s", serial_port_.c_str());
			return -1;
		}
		RCLCPP_INFO(this->get_logger(), "%s opened successfully", serial_port_.c_str());

		struct termios tio;
		tcgetattr(serial_fd_, &tio);
		cfmakeraw(&tio);
		tio.c_cflag = CS8 | CLOCAL | CREAD;
		tio.c_iflag &= ~(IXON | IXOFF);
		cfsetspeed(&tio, SERIAL_SPEED);
		tio.c_cc[VTIME] = 0;
		tio.c_cc[VMIN] = 0;

		int err = tcsetattr(serial_fd_, TCSAFLUSH, &tio);
		if (err != 0) {
			RCLCPP_ERROR(this->get_logger(), "tcsetattr() failed");
			close(serial_fd_);
			serial_fd_ = -1;
			return -1;
		}

		consecutive_failures_ = 0;
		return 0;
	}

	// H7: Serial reconnection logic
	bool serial_reconnect()
	{
		RCLCPP_WARN(this->get_logger(), "Attempting serial reconnection...");
		if (serial_fd_ >= 0) {
			close(serial_fd_);
			serial_fd_ = -1;
		}
		usleep(100000);  // 100ms wait before reconnect

		for (int attempt = 0; attempt < kMaxReconnectAttempts; ++attempt) {
			if (serial_open() == 0) {
				RCLCPP_INFO(this->get_logger(), "Serial reconnection successful (attempt %d)", attempt + 1);
				return true;
			}
			RCLCPP_WARN(this->get_logger(), "Reconnection attempt %d/%d failed", attempt + 1, kMaxReconnectAttempts);
			usleep(500000);  // 500ms between attempts
		}

		RCLCPP_ERROR(this->get_logger(), "Serial reconnection failed after %d attempts", kMaxReconnectAttempts);
		return false;
	}

	static unsigned long get_tick_count()
	{
		struct timespec ts;
		clock_gettime(CLOCK_MONOTONIC, &ts);
		return ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
	}

	// C2: Mutex-protected serial communication
	int send_recv(const char* command, double* returned_data, int data_length)
	{
		std::lock_guard<std::mutex> lock(serial_mutex_);

		if (serial_fd_ < 0) return -1;  // C1: check fd validity

		char temp_buff[256];
		read(serial_fd_, temp_buff, 256);

		int command_len = std::strlen(command);
		int n = write(serial_fd_, command, command_len);
		if (n < 0) return -1;

		int recv_len = 0;
		char recv_buff[kRecvBuffSize + 1];
		unsigned long time_start = get_tick_count();

		while (recv_len < kRecvBuffSize) {
			int bytes_read = read(serial_fd_, recv_buff + recv_len, kRecvBuffSize - recv_len);
			if (bytes_read < 0) {
				return -1;
			} else if (bytes_read == 0) {
				usleep(1000);
			} else {
				recv_len += bytes_read;
				if (recv_buff[recv_len - 1] == '\r' || recv_buff[recv_len - 1] == '\n') {
					break;
				}
			}

			unsigned long time_current = get_tick_count();
			if ((time_current - time_start) >= static_cast<unsigned long>(kCommRecvTimeout)) break;
		}
		recv_buff[recv_len] = '\0';

		if (recv_len > 0 && recv_buff[0] == '!') {
			return -1;
		}

		if (std::strncmp(command, recv_buff, command_len - 1) == 0) {
			if (recv_buff[command_len - 1] == '=') {
				int data_count = 0;
				char* p = &recv_buff[command_len];
				char* pp = nullptr;

				for (int i = 0; i < data_length; i++) {
					// C3: Bounds check before parsing
					if (p >= recv_buff + recv_len) break;

					if (p[0] == '0' && (p + 1 < recv_buff + recv_len) && p[1] == 'x') {
						returned_data[i] = strtol(p + 2, &pp, 16);
						data_count++;
					} else {
						returned_data[i] = strtod(p, &pp);
						data_count++;
					}

					if (pp != nullptr && *pp == ',') {
						p = pp + 1;
					} else {
						break;
					}
				}
				return data_count;
			}
		}
		return 0;
	}

	// M5: Timer callback (ROS2 style, replaces while+spin_some loop)
	void timer_callback()
	{
		if (serial_fd_ < 0) return;

		double data[kMaxData];
		int no_data = 0;
		bool any_failure = false;

		// Read angular velocity (wx, wy, wz)
		no_data = send_recv("g\n", data, kMaxData);
		if (no_data >= 3) {
			imu_data_msg_.angular_velocity.x = data[0] * kDegToRad;
			imu_data_msg_.angular_velocity.y = data[1] * kDegToRad;
			imu_data_msg_.angular_velocity.z = data[2] * kDegToRad;
		} else {
			any_failure = true;
		}

		// Read linear acceleration (unit: g -> m/s^2)
		no_data = send_recv("a\n", data, kMaxData);
		if (no_data >= 3) {
			imu_data_msg_.linear_acceleration.x = data[0] * kGToMps2;
			imu_data_msg_.linear_acceleration.y = data[1] * kGToMps2;
			imu_data_msg_.linear_acceleration.z = data[2] * kGToMps2;
		} else {
			any_failure = true;
		}

		// Read Euler angles
		no_data = send_recv("e\n", data, kMaxData);
		if (no_data >= 3) {
			euler_roll_  = data[0] * kDegToRad;
			euler_pitch_ = data[1] * kDegToRad;
			euler_yaw_   = data[2] * kDegToRad;
		} else {
			any_failure = true;
		}

		// H7: Reconnection logic on consecutive failures
		if (any_failure) {
			consecutive_failures_++;
			if (consecutive_failures_ >= kReconnectThreshold) {
				RCLCPP_WARN(this->get_logger(),
					"Too many consecutive serial failures (%d), attempting reconnection...",
					consecutive_failures_);
				serial_reconnect();
			}
			return;
		}
		consecutive_failures_ = 0;

		// Compute quaternion from Euler angles
		tf2::Quaternion q;
		q.setRPY(euler_roll_, euler_pitch_, euler_yaw_);

		// Orientation
		imu_data_msg_.orientation.x = q.x();
		imu_data_msg_.orientation.y = q.y();
		imu_data_msg_.orientation.z = q.z();
		imu_data_msg_.orientation.w = q.w();
		imu_data_msg_.header.stamp = this->now();
		imu_data_msg_.header.frame_id = "imu_link";

		// Publish IMU data
		imu_data_pub_->publish(imu_data_msg_);

		// TF broadcast (optional via parameter)
		if (single_tf_option_) {
			transform_stamped_.header.stamp = this->now();
			transform_stamped_.header.frame_id = "base_link";
			transform_stamped_.child_frame_id = "imu_link";
			transform_stamped_.transform.translation.x = 0.0;
			transform_stamped_.transform.translation.y = 0.0;
			transform_stamped_.transform.translation.z = tf_translation_z_;  // M7: parameterized
			transform_stamped_.transform.rotation.x = q.x();
			transform_stamped_.transform.rotation.y = q.y();
			transform_stamped_.transform.rotation.z = q.z();
			transform_stamped_.transform.rotation.w = q.w();
			tf_broadcaster_->sendTransform(transform_stamped_);
		}
	}

	// H5, H6: Fixed service callback (void return, error checking)
	void euler_angle_reset_callback(
		[[maybe_unused]] const std::shared_ptr<interfaces::srv::ImuReset::Request> request,
		const std::shared_ptr<interfaces::srv::ImuReset::Response> response)
	{
		double send_data[kMaxData];
		int result = send_recv("ra\n", send_data, kMaxData);
		response->result = (result >= 0);

		if (response->result) {
			RCLCPP_INFO(this->get_logger(), "IMU euler angle reset successful");
		} else {
			RCLCPP_WARN(this->get_logger(), "IMU euler angle reset failed");
		}
	}

	// Topic-based reset callback
	void reset_topic_callback(const std_msgs::msg::Bool::SharedPtr msg)
	{
		if (!msg->data) return;

		double send_data[kMaxData];
		int result = send_recv("ra\n", send_data, kMaxData);

		if (result >= 0) {
			RCLCPP_INFO(this->get_logger(), "IMU euler angle reset (topic) successful");
		} else {
			RCLCPP_WARN(this->get_logger(), "IMU euler angle reset (topic) failed");
		}
	}
};


int main(int argc, char** argv)
{
	rclcpp::init(argc, argv);

	try {
		auto node = std::make_shared<IAHRS>();
		rclcpp::spin(node);
	} catch (const std::exception& e) {
		RCLCPP_FATAL(rclcpp::get_logger("iahrs_driver"), "Node initialization failed: %s", e.what());
		rclcpp::shutdown();
		return 1;
	}

	rclcpp::shutdown();
	return 0;
}
