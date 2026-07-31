// Copyright 2026 Ford_CATL_AMR
// Licensed under the Apache License, Version 2.0.

#include "depth_occupancy_3d/depth_occupancy_node.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <limits>

#include <Eigen/Geometry>
#include <rclcpp_components/register_node_macro.hpp>
#include <sensor_msgs/image_encodings.hpp>
#include <sensor_msgs/point_cloud2_iterator.hpp>
#include <tf2_eigen/tf2_eigen.hpp>

namespace depth_occupancy_3d
{
namespace
{
/// 16UC1 depth 영상의 관례 단위는 mm 다.
constexpr double kMillimetersToMeters = 0.001;
/// 로그 폭주를 막는 throttle 주기.
constexpr int kLogThrottleMs = 5000;

/// 이 노드가 해독할 수 있는 depth 인코딩인지.
bool isSupportedDepthEncoding(const sensor_msgs::msg::Image & image)
{
  const bool encoding_ok = image.encoding == sensor_msgs::image_encodings::TYPE_16UC1 ||
                           image.encoding == sensor_msgs::image_encodings::TYPE_32FC1;
  // 바이트 순서가 호스트와 다르면 원시 버퍼를 그대로 읽을 수 없다. Jetson(ARM little-endian)
  // 에서 드라이버가 big-endian 을 낼 일은 없지만, 조용히 틀린 깊이를 만드느니 거부한다.
  return encoding_ok && image.is_bigendian == 0;
}
}  // namespace

DepthOccupancyNode::DepthOccupancyNode(const rclcpp::NodeOptions & options)
: rclcpp::Node("depth_occupancy_3d", options)
{
  declareParameters();

  if (!grid_.isUsable()) {
    throw std::runtime_error(
      "보셀 격자 파라미터가 유효하지 않다 — resolution > 0 이고 각 축의 max > min 이어야 한다.");
  }

  // 버퍼는 여기서 한 번만 잡고 매 주기 재사용한다. 유입률과 무관하게 메모리 상한을 고정한다.
  occupancy_.assign(grid_.cellCount(), 0U);
  scan_ranges_.assign(scan_.bin_count, std::numeric_limits<float>::infinity());

  RCLCPP_INFO(
    get_logger(), "보셀 격자 %zux%zux%zu (%zu 셀, %.1f MiB), 해상도 %.3f m", grid_.sizeX(),
    grid_.sizeY(), grid_.sizeZ(), grid_.cellCount(),
    static_cast<double>(occupancy_.size()) / (1024.0 * 1024.0), grid_.resolution);

  tf_buffer_ = std::make_unique<tf2_ros::Buffer>(get_clock());
  tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

  cloud_publisher_ = create_publisher<sensor_msgs::msg::PointCloud2>(
    "~/occupancy_points", rclcpp::SensorDataQoS());
  scan_publisher_ =
    create_publisher<sensor_msgs::msg::LaserScan>("~/virtual_scan", rclcpp::SensorDataQoS());

  createSubscriptions();

  const double rate_hz = get_parameter("rate_hz").as_double();
  const auto period = std::chrono::duration<double>(1.0 / std::max(rate_hz, 0.1));
  fusion_timer_ = create_wall_timer(
    std::chrono::duration_cast<std::chrono::nanoseconds>(period),
    std::bind(&DepthOccupancyNode::onFusionTimer, this));

  RCLCPP_INFO(
    get_logger(), "카메라 %zu 대, 융합 %.1f Hz, 데시메이션 %d", camera_names_.size(), rate_hz,
    decimation_);
}

void DepthOccupancyNode::declareParameters()
{
  output_frame_ = declare_parameter<std::string>("output_frame", "base_link");
  camera_names_ = declare_parameter<std::vector<std::string>>(
    "camera_names", std::vector<std::string>{"cam_f", "cam_lf", "cam_lr", "cam_r", "cam_rr",
                                             "cam_rf"});
  depth_image_suffix_ = declare_parameter<std::string>("depth_image_suffix", "/depth/image_raw");
  depth_info_suffix_ = declare_parameter<std::string>("depth_info_suffix", "/depth/camera_info");

  declare_parameter<double>("rate_hz", 10.0);

  // 데시메이션: 640x480 을 4로 줄이면 카메라당 19,200 픽셀 → 6대 15 Hz 에서 약 1.7 M pt/s.
  // 이 장비는 CPU 가 이미 포화 상태라 원본 해상도 역투영은 감당하지 못한다.
  decimation_ = std::max(1, static_cast<int>(declare_parameter<int>("decimation", 4)));

  min_range_m_ = declare_parameter<double>("min_range_m", 0.2);   // Gemini E 사양 하한
  max_range_m_ = declare_parameter<double>("max_range_m", 2.5);   // Gemini E 사양 상한
  obstacle_z_min_m_ = declare_parameter<double>("obstacle_z_min_m", 0.05);  // 바닥 제거
  obstacle_z_max_m_ = declare_parameter<double>("obstacle_z_max_m", 1.8);
  transform_timeout_s_ = declare_parameter<double>("transform_timeout_s", 0.05);

  // 카메라가 융합보다 느린 것은 정상이므로(실측 10~25 fps 대 융합 10 Hz) 융합 주기의
  // 몇 배로 잡는다. 막으려는 것은 느린 프레임이 아니라 갱신이 끊긴 프레임이다.
  max_frame_age_s_ = declare_parameter<double>("max_frame_age_s", 0.5);

  grid_.min_x = declare_parameter<double>("grid.min_x", -3.0);
  grid_.max_x = declare_parameter<double>("grid.max_x", 3.0);
  grid_.min_y = declare_parameter<double>("grid.min_y", -3.0);
  grid_.max_y = declare_parameter<double>("grid.max_y", 3.0);
  grid_.min_z = declare_parameter<double>("grid.min_z", 0.0);
  grid_.max_z = declare_parameter<double>("grid.max_z", 2.0);
  grid_.resolution = declare_parameter<double>("grid.resolution", 0.05);

  scan_.bin_count =
    static_cast<std::size_t>(std::max(1, static_cast<int>(declare_parameter<int>("scan.bins", 360))));
  footprint_.half_length = declare_parameter<double>("footprint.half_length", 1.01381);
  footprint_.half_width = declare_parameter<double>("footprint.half_width", 0.72074);
}

void DepthOccupancyNode::createSubscriptions()
{
  // QoS 는 드라이버의 depth 스트림(SENSOR_DATA = best-effort)과 맞춘다.
  // 불일치하면 메시지가 한 장도 오지 않는다(ros2-coding.md §1).
  const auto qos = rclcpp::SensorDataQoS();

  // 벡터를 **먼저** 최종 크기로 만든 뒤에 구독을 붙인다. 구독이 살아 있는 상태에서
  // push_back 하면 재할당·크기 변경이 콜백과 경쟁한다.
  streams_.resize(camera_names_.size());
  for (std::size_t index = 0; index < camera_names_.size(); ++index) {
    streams_[index].name = camera_names_[index];
  }

  for (std::size_t index = 0; index < streams_.size(); ++index) {
    const std::string & name = streams_[index].name;
    const std::string image_topic = "/" + name + depth_image_suffix_;
    const std::string info_topic = "/" + name + depth_info_suffix_;

    streams_[index].depth_subscription = create_subscription<sensor_msgs::msg::Image>(
      image_topic, qos,
      [this, index](sensor_msgs::msg::Image::ConstSharedPtr message) {
        // 덮어쓰기만 — 큐에 쌓지 않는다(CameraStream 주석 참조).
        const std::lock_guard<std::mutex> lock(stream_mutex_);
        streams_[index].latest_depth = std::move(message);
      });

    streams_[index].info_subscription = create_subscription<sensor_msgs::msg::CameraInfo>(
      info_topic, qos,
      [this, index](sensor_msgs::msg::CameraInfo::ConstSharedPtr message) {
        const std::lock_guard<std::mutex> lock(stream_mutex_);
        streams_[index].latest_info = std::move(message);
      });
  }
}

bool DepthOccupancyNode::depthToMeters(
  const sensor_msgs::msg::Image & image, std::size_t u, std::size_t v, double & depth_m) const
{
  if (image.encoding == sensor_msgs::image_encodings::TYPE_16UC1) {
    const std::size_t offset = v * image.step + u * sizeof(std::uint16_t);
    std::uint16_t raw = 0;
    std::memcpy(&raw, image.data.data() + offset, sizeof(raw));
    if (raw == 0) {
      return false;  // 0 = 측정 실패 (깊이 영상 관례)
    }
    depth_m = static_cast<double>(raw) * kMillimetersToMeters;
  } else {
    const std::size_t offset = v * image.step + u * sizeof(float);
    float raw = 0.0F;
    std::memcpy(&raw, image.data.data() + offset, sizeof(raw));
    if (!std::isfinite(raw) || raw <= 0.0F) {
      return false;
    }
    depth_m = static_cast<double>(raw);
  }
  return depth_m >= min_range_m_ && depth_m <= max_range_m_;
}

bool DepthOccupancyNode::projectCamera(
  CameraStream & stream, const sensor_msgs::msg::Image::ConstSharedPtr & image,
  const sensor_msgs::msg::CameraInfo::ConstSharedPtr & info, FusionStats & stats)
{
  if (!image || !info) {
    return false;
  }

  if (!isSupportedDepthEncoding(*image)) {
    if (!stream.warned_unsupported_encoding) {
      stream.warned_unsupported_encoding = true;
      RCLCPP_ERROR(
        get_logger(), "[%s] 해독할 수 없는 depth 인코딩 '%s' (is_bigendian=%u) — 이 카메라를 건너뛴다",
        stream.name.c_str(), image->encoding.c_str(), image->is_bigendian);
    }
    return false;
  }

  const PinholeIntrinsics intrinsics{info->k[0], info->k[4], info->k[2], info->k[5]};
  if (!intrinsics.isUsable()) {
    RCLCPP_WARN_THROTTLE(
      get_logger(), *get_clock(), kLogThrottleMs,
      "[%s] camera_info 의 초점거리가 0 이다 — 역투영 불가", stream.name.c_str());
    return false;
  }

  // base_link ← 광학 프레임. 이 연쇄는 전 구간 static 이므로(마운트 TF 는 launch 의
  // static_transform_publisher, 광학 프레임은 드라이버의 tf_publish_rate=0.0)
  // 특정 시각이 아니라 TimePointZero 로 조회한다 — 프레임 도착 시각과 무관하게 유효하다.
  Eigen::Isometry3d optical_to_base;
  try {
    const auto transform = tf_buffer_->lookupTransform(
      output_frame_, image->header.frame_id, tf2::TimePointZero,
      tf2::durationFromSec(transform_timeout_s_));
    optical_to_base = tf2::transformToEigen(transform);
  } catch (const tf2::TransformException & exception) {
    RCLCPP_WARN_THROTTLE(
      get_logger(), *get_clock(), kLogThrottleMs, "[%s] TF %s ← %s 조회 실패: %s",
      stream.name.c_str(), output_frame_.c_str(), image->header.frame_id.c_str(),
      exception.what());
    return false;
  }

  const auto step = static_cast<std::size_t>(decimation_);
  for (std::size_t v = 0; v < image->height; v += step) {
    for (std::size_t u = 0; u < image->width; u += step) {
      double depth_m = 0.0;
      if (!depthToMeters(*image, u, v, depth_m)) {
        continue;
      }
      ++stats.points_projected;

      const Point3 optical = backProject(
        static_cast<double>(u), static_cast<double>(v), depth_m, intrinsics);
      const Eigen::Vector3d in_base =
        optical_to_base * Eigen::Vector3d(optical.x, optical.y, optical.z);
      const Point3 point{in_base.x(), in_base.y(), in_base.z()};

      // 자기 차체는 장애물이 아니다.
      if (isInsideFootprint(point.x, point.y, footprint_)) {
        continue;
      }
      // 바닥면과 천장은 장애물이 아니다.
      if (point.z < obstacle_z_min_m_ || point.z > obstacle_z_max_m_) {
        continue;
      }

      ++stats.points_kept;

      std::size_t cell = 0;
      if (voxelIndex(grid_, point, cell) && occupancy_[cell] == 0U) {
        occupancy_[cell] = 1U;
        ++stats.voxels_occupied;
      }

      std::size_t bin = 0;
      if (azimuthBin(scan_, point.x, point.y, bin)) {
        const auto range = static_cast<float>(horizontalRange(point.x, point.y));
        scan_ranges_[bin] = std::min(scan_ranges_[bin], range);
      }
    }
  }
  return true;
}

void DepthOccupancyNode::onFusionTimer()
{
  // 매 주기 처음부터 다시 만든다 — 누적하지 않는다(헤더 '시간 축 정책' 참조).
  std::fill(occupancy_.begin(), occupancy_.end(), 0U);
  std::fill(scan_ranges_.begin(), scan_ranges_.end(), std::numeric_limits<float>::infinity());

  FusionStats stats;
  rclcpp::Time oldest_stamp = now();
  bool has_stamp = false;

  // 잠금은 shared_ptr 스냅샷을 뜨는 동안만 잡는다. 무거운 투영은 잠금 밖에서 한다 —
  // 안에서 하면 구독 콜백이 그 시간만큼 굶고, 그 지연이 곧 캡처 FPS 저하로 되돌아온다
  // (같은 형태의 선례: docs/issues_and_fixes/issues_and_fixes.md:241-252).
  std::vector<sensor_msgs::msg::Image::ConstSharedPtr> images(streams_.size());
  std::vector<sensor_msgs::msg::CameraInfo::ConstSharedPtr> infos(streams_.size());
  {
    const std::lock_guard<std::mutex> lock(stream_mutex_);
    for (std::size_t index = 0; index < streams_.size(); ++index) {
      images[index] = streams_[index].latest_depth;
      infos[index] = streams_[index].latest_info;
    }
  }

  // 갱신이 끊긴 프레임을 걷어낸다. 이 게이트가 없으면 카메라가 죽어도 마지막 프레임이
  // 계속 융합되어 그 방향 섹터에 유령 장애물이 남는다(섹터마다 카메라가 한 대뿐이라
  // 다른 카메라가 덮어쓰지 못한다).
  const rclcpp::Time cycle_time = now();
  for (std::size_t index = 0; index < streams_.size(); ++index) {
    if (!images[index]) {
      continue;
    }
    const rclcpp::Time stamp(images[index]->header.stamp, cycle_time.get_clock_type());
    const double age_s = (cycle_time - stamp).seconds();
    if (age_s > max_frame_age_s_) {
      images[index].reset();
      ++stats.cameras_stale;
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), kLogThrottleMs,
        "[%s] 프레임이 %.2f s 낡아 융합에서 제외한다 (상한 %.2f s) — 카메라가 멈췄을 수 있다",
        streams_[index].name.c_str(), age_s, max_frame_age_s_);
    }
  }

  for (std::size_t index = 0; index < streams_.size(); ++index) {
    if (!projectCamera(streams_[index], images[index], infos[index], stats)) {
      continue;
    }
    ++stats.cameras_used;
    const rclcpp::Time stamp(images[index]->header.stamp);
    if (!has_stamp || stamp < oldest_stamp) {
      oldest_stamp = stamp;
      has_stamp = true;
    }
  }

  if (stats.cameras_used == 0) {
    RCLCPP_WARN_THROTTLE(
      get_logger(), *get_clock(), kLogThrottleMs,
      "이번 주기에 투영된 카메라가 하나도 없다 (낡아서 제외 %zu 대) — "
      "프레임·camera_info·TF 중 하나가 없다",
      stats.cameras_stale);
    return;
  }

  // 일부만 살아 있으면 그 방향 섹터가 비었다는 뜻이라 조용히 넘기지 않는다.
  if (stats.cameras_used < streams_.size()) {
    RCLCPP_WARN_THROTTLE(
      get_logger(), *get_clock(), kLogThrottleMs,
      "카메라 %zu/%zu 만 융합됐다 (낡아서 제외 %zu 대) — 빠진 방향의 60° 섹터는 관측이 없다",
      stats.cameras_used, streams_.size(), stats.cameras_stale);
  }

  // 융합 결과의 시각은 **가장 오래된** 기여 프레임의 시각으로 찍는다. 소비자(충돌 회피)가
  // 보는 것은 "이 표현이 최신인가"가 아니라 "가장 낡은 부분이 얼마나 낡았나"이기 때문이다.
  const rclcpp::Time stamp = has_stamp ? oldest_stamp : now();
  publishOccupancyCloud(stamp);
  publishVirtualScan(stamp);

  RCLCPP_DEBUG(
    get_logger(), "카메라 %zu/%zu(낡음 %zu), 투영 %zu, 유효 %zu, 점유보셀 %zu",
    stats.cameras_used, streams_.size(), stats.cameras_stale, stats.points_projected,
    stats.points_kept, stats.voxels_occupied);
}

void DepthOccupancyNode::publishOccupancyCloud(const rclcpp::Time & stamp)
{
  sensor_msgs::msg::PointCloud2 cloud;
  cloud.header.stamp = stamp;
  cloud.header.frame_id = output_frame_;

  const std::size_t occupied =
    static_cast<std::size_t>(std::count(occupancy_.begin(), occupancy_.end(), 1U));

  sensor_msgs::PointCloud2Modifier modifier(cloud);
  modifier.setPointCloud2FieldsByString(1, "xyz");
  modifier.resize(occupied);

  sensor_msgs::PointCloud2Iterator<float> iter_x(cloud, "x");
  sensor_msgs::PointCloud2Iterator<float> iter_y(cloud, "y");
  sensor_msgs::PointCloud2Iterator<float> iter_z(cloud, "z");

  for (std::size_t cell = 0; cell < occupancy_.size(); ++cell) {
    if (occupancy_[cell] == 0U) {
      continue;
    }
    const auto center = voxelCenter(grid_, cell);
    *iter_x = static_cast<float>(center.x);
    *iter_y = static_cast<float>(center.y);
    *iter_z = static_cast<float>(center.z);
    ++iter_x;
    ++iter_y;
    ++iter_z;
  }

  cloud.is_dense = true;
  cloud_publisher_->publish(cloud);
}

void DepthOccupancyNode::publishVirtualScan(const rclcpp::Time & stamp)
{
  sensor_msgs::msg::LaserScan scan;
  scan.header.stamp = stamp;
  scan.header.frame_id = output_frame_;
  scan.angle_min = static_cast<float>(scan_.angle_min);
  scan.angle_max = static_cast<float>(scan_.angle_max);
  scan.angle_increment = static_cast<float>(scan_.angleIncrement());
  scan.time_increment = 0.0F;  // 6대를 한 번에 굽는 합성 스캔이라 빈별 시간차가 없다
  scan.scan_time = 0.0F;
  scan.range_min = static_cast<float>(min_range_m_);
  scan.range_max = static_cast<float>(max_range_m_);
  scan.ranges = scan_ranges_;  // 관측 없는 빈은 inf — LaserScan 규약상 '반환 없음'

  scan_publisher_->publish(scan);
}

}  // namespace depth_occupancy_3d

RCLCPP_COMPONENTS_REGISTER_NODE(depth_occupancy_3d::DepthOccupancyNode)
