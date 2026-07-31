// Copyright 2026 Ford_CATL_AMR
// Licensed under the Apache License, Version 2.0.
//
// surround depth 융합 노드 — depth 카메라 6대를 base_link 기준 3D 보셀 점유 격자와
// 360° 가상 스캔으로 합친다.
//
// 설계 근거: docs/adr/2026-07-31-surround-depth-occupancy.md
//
// 시간 축 정책: **누적하지 않는다.** 매 주기 최신 프레임만으로 격자를 다시 만든다.
// 과거 프레임을 쌓으려면 주행 중 자기운동 보정이 필요하고 그것은 오도메트리를 요구하는데,
// 이 저장소에 신뢰 가능한 오도메트리가 없다는 것이 애초에 로컬 표현을 고른 이유다(ADR §D1).

#ifndef DEPTH_OCCUPANCY_3D__DEPTH_OCCUPANCY_NODE_HPP_
#define DEPTH_OCCUPANCY_3D__DEPTH_OCCUPANCY_NODE_HPP_

#include <cstdint>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/camera_info.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>

#include "depth_occupancy_3d/geometry.hpp"

namespace depth_occupancy_3d
{

/// 카메라 1대의 최신 프레임 보관소.
///
/// 프레임을 큐에 쌓지 않고 **덮어쓰기만** 한다. 소비(타이머)가 유입(콜백)보다 느려도
/// 메모리는 카메라당 1프레임으로 고정된다 — 유계화 없는 큐가 RSS 11 GB 까지 자란
/// 선례(docs/issues_and_fixes/issues_and_fixes.md:279)를 반복하지 않기 위한 설계다.
struct CameraStream
{
  std::string name;
  rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr depth_subscription;
  rclcpp::Subscription<sensor_msgs::msg::CameraInfo>::SharedPtr info_subscription;

  sensor_msgs::msg::Image::ConstSharedPtr latest_depth;
  sensor_msgs::msg::CameraInfo::ConstSharedPtr latest_info;

  /// 미지원 인코딩 경고를 카메라당 한 번만 내기 위한 표식.
  bool warned_unsupported_encoding{false};
  /// TF 조회 실패 경고를 억제 없이 매번 내면 로그가 막히므로 throttle 과 함께 쓴다.
  bool warned_missing_transform{false};
};

/// 융합 1주기의 집계 결과. 관측성 로그와 시험에서 쓴다.
struct FusionStats
{
  std::size_t cameras_used{0};       ///< 이번 주기에 실제로 투영된 카메라 수
  std::size_t points_projected{0};   ///< 역투영된 픽셀 수(데시메이션 후)
  std::size_t points_kept{0};        ///< 필터를 통과해 격자에 들어간 점 수
  std::size_t voxels_occupied{0};    ///< 점유로 표시된 보셀 수
};

class DepthOccupancyNode : public rclcpp::Node
{
public:
  explicit DepthOccupancyNode(const rclcpp::NodeOptions & options);

private:
  /// 파라미터를 선언하고 읽는다. 미선언 접근을 만들지 않기 위해 한곳에 모은다.
  void declareParameters();

  /// 카메라별 구독을 만든다.
  void createSubscriptions();

  /// 융합 1주기. 최신 프레임 6장을 격자·스캔으로 굽고 발행한다.
  void onFusionTimer();

  /// 카메라 1대의 depth 프레임을 격자·스캔에 투영한다.
  ///
  /// image/info 는 stream_mutex_ 를 **놓은 뒤** 넘겨받은 스냅샷이다. 투영은 픽셀 수만큼
  /// 도는 무거운 작업이라 잠금 안에서 하면 구독 콜백이 그 시간만큼 굶는다(ros2-coding.md §2).
  /// 이 함수가 stream 에서 건드리는 것은 name 과 warned_* 뿐이며, 둘 다 타이머 스레드
  /// 전용이라 잠금이 필요 없다.
  ///
  /// \return 투영에 성공했으면 true (프레임·내부파라미터·TF 가 모두 있는 경우).
  bool projectCamera(
    CameraStream & stream, const sensor_msgs::msg::Image::ConstSharedPtr & image,
    const sensor_msgs::msg::CameraInfo::ConstSharedPtr & info, FusionStats & stats);

  /// depth 픽셀 원값을 m 단위로 바꾼다.
  ///
  /// \param[out] depth_m 유효한 값일 때만 기록된다.
  /// \return 유효 측정이면 true. 0(측정 실패)·NaN·범위 밖은 false.
  bool depthToMeters(
    const sensor_msgs::msg::Image & image, std::size_t u, std::size_t v, double & depth_m) const;

  void publishOccupancyCloud(const rclcpp::Time & stamp);
  void publishVirtualScan(const rclcpp::Time & stamp);

  // --- 파라미터 ---
  std::string output_frame_;
  std::vector<std::string> camera_names_;
  std::string depth_image_suffix_;
  std::string depth_info_suffix_;
  int decimation_{4};
  double min_range_m_{0.2};
  double max_range_m_{2.5};
  double obstacle_z_min_m_{0.05};
  double obstacle_z_max_m_{1.8};
  double transform_timeout_s_{0.05};
  GridSpec grid_;
  ScanSpec scan_;
  FootprintHalfExtent footprint_;

  // --- 상태 ---
  /// 카메라 스트림. latest_* 필드는 stream_mutex_ 가 지킨다.
  std::vector<CameraStream> streams_;
  /// streams_ 의 latest_depth/latest_info 를 지키는 유일한 잠금.
  /// writer 는 구독 콜백, reader 는 융합 타이머다.
  std::mutex stream_mutex_;

  /// 점유 보셀 표식. 생성자에서 한 번 할당하고 매 주기 재사용한다(재할당 없음).
  std::vector<std::uint8_t> occupancy_;
  /// 방위각 빈별 최근접 수평거리. 매 주기 무한대로 초기화한다.
  std::vector<float> scan_ranges_;

  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_publisher_;
  rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr scan_publisher_;
  rclcpp::TimerBase::SharedPtr fusion_timer_;

  std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
};

}  // namespace depth_occupancy_3d

#endif  // DEPTH_OCCUPANCY_3D__DEPTH_OCCUPANCY_NODE_HPP_
