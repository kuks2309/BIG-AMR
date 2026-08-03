// Copyright 2026 Ford_CATL_AMR
// Licensed under the Apache License, Version 2.0.
//
// usb_cam_publisher_node
// ----------------------
// Captures RGB frames from a single V4L2 USB camera via OpenCV and publishes
// them. One process per camera keeps a failing device from taking down the
// others. FPS is measured at the capture layer (V4L2 grab time) so ROS2
// serialization does not distort the raw USB performance numbers (see ADR 0001).
//
// publish_mode (default "compressed") picks what leaves this node:
//   compressed — the camera's own MJPEG buffer is forwarded untouched as
//                sensor_msgs/CompressedImage. No decode, no re-encode.
//   raw        — decode to bgr8 and publish sensor_msgs/Image (legacy path).
//   both       — forward MJPEG *and* decode for the raw topic (transition aid).
//
// Measured on this hardware (1280x720@30, one camera, 2026-08-03):
//   decode  6.55 ms/frame CPU, 2700 KB/frame  (19.5% of a core per camera)
//   passth. 0.15 ms/frame CPU,  131 KB/frame  ( 0.4% of a core per camera)
// i.e. 44x less CPU and ~21x less bandwidth; 6 cameras go from ~498 to ~24 MB/s.
// The UVC frames carry their own Huffman tables (DHT verified), so ordinary
// JPEG decoders — including browsers — read them directly.

#include <fcntl.h>
#include <linux/videodev2.h>
#include <sys/ioctl.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <cstring>
#include <memory>
#include <string>
#include <thread>

#include <opencv2/opencv.hpp>

#include <cv_bridge/cv_bridge.h>
#include <image_transport/image_transport.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/compressed_image.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <std_msgs/msg/header.hpp>

#include "usb_cam_publisher/pixel_format.hpp"

namespace usb_cam_publisher
{

class UsbCamPublisher : public rclcpp::Node
{
public:
  UsbCamPublisher()
  : Node("usb_cam_publisher")
  {
    // --- Parameters (public API; see ADR 0001) ---
    video_device_ = declare_parameter<std::string>("video_device", "/dev/video0");
    camera_name_ = declare_parameter<std::string>("camera_name", "usb_cam");
    frame_id_ = declare_parameter<std::string>("frame_id", camera_name_ + "_optical_frame");
    image_width_ = declare_parameter<int>("image_width", 1280);
    image_height_ = declare_parameter<int>("image_height", 720);
    framerate_ = declare_parameter<double>("framerate", 30.0);
    pixel_format_ = declare_parameter<std::string>("pixel_format", "MJPG");
    fps_report_interval_sec_ = declare_parameter<double>("fps_report_interval_sec", 5.0);
    // Orbbec Gemini E ships with V4L2_CID_EXPOSURE_AUTO_PRIORITY enabled, which
    // lets the camera HALVE its frame rate to lengthen exposure in dim light
    // (~30 -> ~15 fps). Disable it by default so the requested rate is held.
    disable_dynamic_framerate_ = declare_parameter<bool>("disable_dynamic_framerate", true);
    // Shared with the Python calibration UI via config/camera/camera_common.yaml.
    power_line_frequency_ = declare_parameter<int>("power_line_frequency", 2);
    buffersize_ = declare_parameter<int>("buffersize", 2);
    publish_mode_ = declare_parameter<std::string>("publish_mode", "compressed");
    if (publish_mode_ != "compressed" && publish_mode_ != "raw" && publish_mode_ != "both") {
      RCLCPP_WARN(
        get_logger(), "[%s] unknown publish_mode '%s' - falling back to 'compressed'",
        camera_name_.c_str(), publish_mode_.c_str());
      publish_mode_ = "compressed";
    }

    // Topic is namespaced under the camera name so multiple nodes never collide.
    // Sensor-data QoS (best-effort, keep-last) matches the low-latency CCTV intent
    // and the viewer's subscription profile, dropping stale frames under load
    // instead of queueing them.
    const std::string topic = camera_name_ + "/image_raw";
    if (publish_mode_ != "compressed") {
      publisher_ = image_transport::create_publisher(this, topic, rmw_qos_profile_sensor_data);
    }
    if (publish_mode_ != "raw") {
      // image_transport's companion-topic name, so tooling and subscribers that
      // already speak that convention (the viewer's image_transport:=compressed)
      // find it without extra configuration.
      compressed_publisher_ = create_publisher<sensor_msgs::msg::CompressedImage>(
        topic + "/compressed", rclcpp::SensorDataQoS());
    }

    if (!openDevice()) {
      RCLCPP_FATAL(
        get_logger(), "[%s] failed to open device '%s' - node will not publish",
        camera_name_.c_str(), video_device_.c_str());
      return;
    }

    running_.store(true);
    capture_thread_ = std::thread(&UsbCamPublisher::captureLoop, this);
    RCLCPP_INFO(
      get_logger(), "[%s] publishing %dx%d@%.1f (%s, mode=%s) from '%s' on topic '%s%s'",
      camera_name_.c_str(), image_width_, image_height_, framerate_,
      pixel_format_.c_str(), publish_mode_.c_str(), video_device_.c_str(), topic.c_str(),
      publish_mode_ == "compressed" ? "/compressed" : "");
  }

  ~UsbCamPublisher() override
  {
    running_.store(false);
    // Note: cv::VideoCapture::read() is a blocking V4L2 dequeue. On a cleanly
    // stopped or unplugged camera it returns quickly (false), but a firmware-
    // wedged device can block this join until the process is killed. There is no
    // portable read-timeout on the V4L2 backend; a stuck camera needs a hard kill.
    if (capture_thread_.joinable()) {
      capture_thread_.join();
    }
    if (capture_.isOpened()) {
      capture_.release();
    }
  }

private:
  /// Set a V4L2 integer control on the device via a short-lived fd. Returns
  /// false (with a warning) if the device or control is unavailable; a missing
  /// control is non-fatal (the camera simply keeps its default).
  bool setV4l2Control(unsigned int control_id, int value)
  {
    const int fd = open(video_device_.c_str(), O_RDWR);
    if (fd < 0) {
      RCLCPP_WARN(
        get_logger(), "[%s] cannot open '%s' to set control 0x%x: %s",
        camera_name_.c_str(), video_device_.c_str(), control_id, std::strerror(errno));
      return false;
    }
    v4l2_control ctrl{};
    ctrl.id = control_id;
    ctrl.value = value;
    const bool ok = ioctl(fd, VIDIOC_S_CTRL, &ctrl) == 0;
    if (!ok) {
      RCLCPP_WARN(
        get_logger(), "[%s] VIDIOC_S_CTRL 0x%x=%d failed: %s",
        camera_name_.c_str(), control_id, value, std::strerror(errno));
    }
    close(fd);
    return ok;
  }

  /// Open the V4L2 device and apply the requested format/geometry/rate.
  bool openDevice()
  {
    // Must run before OpenCV starts streaming so the rate is held from frame 0.
    if (disable_dynamic_framerate_) {
      if (setV4l2Control(V4L2_CID_EXPOSURE_AUTO_PRIORITY, 0)) {
        RCLCPP_INFO(
          get_logger(), "[%s] disabled exposure auto-priority (constant frame rate)",
          camera_name_.c_str());
      }
    }
    // Anti-banding: match the mains frequency so rolling-shutter rows don't beat
    // against lighting flicker (horizontal dark bands). Shared value with the
    // Python calibration UI (config/camera/camera_common.yaml).
    if (setV4l2Control(V4L2_CID_POWER_LINE_FREQUENCY, power_line_frequency_)) {
      RCLCPP_INFO(
        get_logger(), "[%s] power_line_frequency=%d", camera_name_.c_str(),
        power_line_frequency_);
    }

    capture_.open(video_device_, cv::CAP_V4L2);
    if (!capture_.isOpened()) {
      return false;
    }
    capture_.set(cv::CAP_PROP_FOURCC, fourccFromString(pixel_format_));
    capture_.set(cv::CAP_PROP_FRAME_WIDTH, image_width_);
    capture_.set(cv::CAP_PROP_FRAME_HEIGHT, image_height_);
    capture_.set(cv::CAP_PROP_FPS, framerate_);
    // BUFFERSIZE must be >= 2: a single V4L2 buffer cannot be filled by the
    // driver while userspace holds it, so the stream degrades to every-other-
    // frame (~half FPS). Two buffers pipeline capture and processing to reach
    // the full rate at the cost of ~1 extra frame of latency. Measured on this
    // hardware: bufsize 1 -> ~15 fps, bufsize 2 -> ~30 fps (see docs/performance).
    capture_.set(cv::CAP_PROP_BUFFERSIZE, buffersize_);
    if (publish_mode_ != "raw") {
      // CONVERT_RGB=0 hands back the driver's own compressed buffer instead of a
      // decoded BGR image. This is where the 44x CPU saving comes from: nothing
      // decodes the MJPEG unless a consumer actually needs pixels.
      capture_.set(cv::CAP_PROP_CONVERT_RGB, 0);
    }

    // Report what the driver actually granted (may differ from requested).
    const int actual_w = static_cast<int>(capture_.get(cv::CAP_PROP_FRAME_WIDTH));
    const int actual_h = static_cast<int>(capture_.get(cv::CAP_PROP_FRAME_HEIGHT));
    const double actual_fps = capture_.get(cv::CAP_PROP_FPS);
    RCLCPP_INFO(
      get_logger(), "[%s] driver granted %dx%d@%.1f", camera_name_.c_str(),
      actual_w, actual_h, actual_fps);
    return true;
  }

  /// Length of the JPEG inside a driver buffer.
  ///
  /// The V4L2 buffer normally ends exactly at EOI (measured: 30/30 frames, 0%
  /// padding on this hardware), but one observed frame carried trailing zeros.
  /// Trimming to the last EOI keeps a stray tail out of the message; if no EOI
  /// is found the whole buffer is forwarded rather than dropping the frame.
  static size_t jpegLength(const cv::Mat & buffer)
  {
    const size_t total = buffer.total() * buffer.elemSize();
    const unsigned char * data = buffer.data;
    for (size_t i = total; i >= 2; --i) {
      if (data[i - 2] == 0xFF && data[i - 1] == 0xD9) {
        return i;
      }
    }
    return total;
  }

  /// Capture thread: grab -> publish, measuring FPS at grab time.
  void captureLoop()
  {
    cv::Mat frame;
    unsigned long long frames_in_window = 0;
    unsigned long long grab_failures = 0;
    unsigned long long decode_failures = 0;
    auto window_start = std::chrono::steady_clock::now();

    while (running_.load() && rclcpp::ok()) {
      if (!capture_.read(frame) || frame.empty()) {
        ++grab_failures;
        // Brief backoff avoids a busy-spin when a camera stalls or unplugs.
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
        continue;
      }

      // Capture-layer timestamp: taken the instant the frame is in hand.
      const rclcpp::Time stamp = now();

      std_msgs::msg::Header header;
      header.stamp = stamp;
      header.frame_id = frame_id_;

      if (publish_mode_ == "raw") {
        sensor_msgs::msg::Image::SharedPtr msg =
          cv_bridge::CvImage(header, "bgr8", frame).toImageMsg();
        publisher_.publish(msg);
      } else {
        // `frame` is the driver's MJPEG buffer (1 x N, CV_8U) — forward as is.
        auto compressed = std::make_unique<sensor_msgs::msg::CompressedImage>();
        compressed->header = header;
        compressed->format = "jpeg";
        const auto * bytes = frame.data;
        compressed->data.assign(bytes, bytes + jpegLength(frame));
        compressed_publisher_->publish(std::move(compressed));

        if (publish_mode_ == "both") {
          // Only "both" pays the decode, and only because a raw subscriber asked.
          const cv::Mat decoded = cv::imdecode(frame, cv::IMREAD_COLOR);
          if (!decoded.empty()) {
            publisher_.publish(cv_bridge::CvImage(header, "bgr8", decoded).toImageMsg());
          } else {
            ++decode_failures;
          }
        }
      }

      ++frames_in_window;
      const auto elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - window_start).count();
      if (elapsed >= fps_report_interval_sec_) {
        RCLCPP_INFO(
          get_logger(), "[%s] capture FPS: %.2f (grab_failures=%llu, decode_failures=%llu)",
          camera_name_.c_str(), computeFps(frames_in_window, elapsed),
          grab_failures, decode_failures);
        frames_in_window = 0;
        grab_failures = 0;
        decode_failures = 0;
        window_start = std::chrono::steady_clock::now();
      }
    }
    RCLCPP_INFO(get_logger(), "[%s] capture loop stopped", camera_name_.c_str());
  }

  // --- Configuration (immutable after construction) ---
  std::string video_device_;
  std::string camera_name_;
  std::string frame_id_;
  int image_width_ = 1280;
  int image_height_ = 720;
  double framerate_ = 30.0;
  std::string pixel_format_ = "MJPG";
  double fps_report_interval_sec_ = 5.0;
  bool disable_dynamic_framerate_ = true;
  int power_line_frequency_ = 2;  // anti-banding: 0=off,1=50Hz,2=60Hz (KR mains 60Hz)
  int buffersize_ = 2;            // V4L2 buffers; >=2 needed for full FPS
  std::string publish_mode_ = "compressed";  // compressed | raw | both

  // --- Runtime state ---
  cv::VideoCapture capture_;
  image_transport::Publisher publisher_;
  rclcpp::Publisher<sensor_msgs::msg::CompressedImage>::SharedPtr compressed_publisher_;
  std::thread capture_thread_;
  std::atomic<bool> running_{false};
};

}  // namespace usb_cam_publisher

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<usb_cam_publisher::UsbCamPublisher>());
  rclcpp::shutdown();
  return 0;
}
