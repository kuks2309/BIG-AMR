// Copyright 2024 pradyum
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef DUAL_LASER_MERGER__DUAL_LASER_MERGER_HPP_
#define DUAL_LASER_MERGER__DUAL_LASER_MERGER_HPP_

#include <pcl/kdtree/kdtree_flann.h>
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl_conversions/pcl_conversions.h>
#include <yaml-cpp/yaml.h>

#include <chrono>
#include <cmath>
#include <memory>
#include <string>
#include <vector>

#include <algorithm>
#include <cstdint>
#include <limits>

#include "geometry_msgs/msg/transform_stamped.hpp"
#include "rcl_interfaces/msg/parameter_descriptor.hpp"
#include "laser_geometry/laser_geometry.hpp"
#include "message_filters/subscriber.h"
#include "message_filters/sync_policies/approximate_time.h"
#include "message_filters/synchronizer.h"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"
#include "sensor_msgs/point_cloud2_iterator.hpp"
#include "std_msgs/msg/float64.hpp"
#include "tf2/LinearMath/Quaternion.h"
#include "tf2_ros/buffer.h"
#include "tf2_ros/static_transform_broadcaster.h"
#include "tf2_ros/transform_broadcaster.h"
#include "tf2_ros/transform_listener.h"
#include "tf2_sensor_msgs/tf2_sensor_msgs.hpp"

namespace merger_node
{

class MergerNode : public rclcpp::Node
{
  public:
    explicit MergerNode(const rclcpp::NodeOptions &options);

  private:
    std::shared_ptr<tf2_ros::Buffer> tf2_buffer;
    std::shared_ptr<tf2_ros::TransformListener> tf2_listener;
    std::shared_ptr<tf2_ros::TransformBroadcaster> tf2_broadcaster;
    std::shared_ptr<tf2_ros::StaticTransformBroadcaster> static_tf_broadcaster;
    std::shared_ptr<message_filters::Synchronizer<
        message_filters::sync_policies::ApproximateTime<sensor_msgs::msg::LaserScan, sensor_msgs::msg::LaserScan>>>
        message_filter;
    message_filters::Subscriber<sensor_msgs::msg::LaserScan> laser_1_sub;
    message_filters::Subscriber<sensor_msgs::msg::LaserScan> laser_2_sub;
    rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr merged_scan_pub;
    rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr merged_cloud_pub;
    rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr sync_skew_pub;
    laser_geometry::LaserProjection projector;

    int input_queue_size_param;
    std::string target_frame_param;
    double tolerance_param, min_height_param, max_height_param, angle_min_param, angle_max_param, angle_increment_param,
        scan_time_param, range_min_param, range_max_param, inf_epsilon_param, laser_1_x_offset, laser_1_y_offset,
        laser_1_yaw_offset, laser_2_x_offset, laser_2_y_offset, laser_2_yaw_offset, allowed_radius_param;
    bool use_inf_param, enable_dynamic_param_refresh_param, enable_shadow_filter_param, enable_average_filter_param;

    // Calibration YAML
    std::string calibration_file_param;
    std::string merged_scan_frame_param;
    std::string laser_1_frame_param;
    std::string laser_2_frame_param;
    bool calibration_loaded_;

    // Exclusion zone filtering
    struct ExclusionZone
    {
        std::string name;
        double x_min, x_max, y_min, y_max;
    };
    std::string filter_config_file_param;
    bool enable_exclusion_zones_param;
    std::vector<ExclusionZone> exclusion_zones_;

    // Mapping mode (rear exclusion)
    bool enable_mapping_mode_param;
    double mapping_keep_angle_min_param;
    double mapping_keep_angle_max_param;

    // Precomputed transforms: merged_scan → sensor (for point cloud transform)
    double m2f_tx_, m2f_ty_, m2f_cos_, m2f_sin_;
    double m2r_tx_, m2r_ty_, m2r_cos_, m2r_sin_;
    bool laser_1_flipped_, laser_2_flipped_; // upside-down sensors (Y-negate)

    // ── Pair synchronisation (stamp skew of the two scans that ApproximateTime matched) ──
    // ApproximateTime bounds nothing by default: max_interval_duration_ inside the policy is
    // initialised to INT32_MAX seconds and the node never overrode it, so any pair could be
    // emitted no matter how far apart the two stamps were. `tolerance` is NOT that bound —
    // it is fed to setAgePenalty(), a latency-vs-quality weight in the matching cost function.
    // Statistics below are written only from sub_callback() and the report timer. Both live in the
    // node's default (MutuallyExclusive) callback group, so they are serialised and need no lock.
    // Move either to a Reentrant group, or add a second writer, and they must become guarded.
    double max_pair_skew_param;          // [s] 0 = unbounded (legacy behaviour)
    bool publish_sync_diagnostics_param;
    std::string output_stamp_param;      // laser_1 | laser_2 | latest | earliest | midpoint
    double sync_report_period_param;     // [s] how often the sync stats line is logged
    uint64_t pair_count_;                // pairs accepted by the skew gate, this window
    uint64_t skew_reject_count_;         // pairs rejected by max_pair_skew, cumulative
    uint64_t skew_reject_window_;        // pairs rejected by max_pair_skew, this window
    // Scans that reached the synchroniser, this window. The policy discards candidates internally
    // (approximate_time.h:728-731 dequeDeleteFront) without ever calling sub_callback, so those  comment-check: ignore
    // losses are invisible to the pair counters. Comparing inputs to pairs exposes them.
    uint64_t in_count_1_;
    uint64_t in_count_2_;
    uint64_t merge_fail_count_;          // pairs whose merge produced no cloud, cumulative
    double skew_sum_;                    // [s] sum of |t1 - t2| over accepted pairs, this window
    double skew_max_;                    // [s] worst |t1 - t2| over ALL observed pairs, this window
    rclcpp::Time skew_report_last_;
    rclcpp::TimerBase::SharedPtr sync_report_timer_;

    void sub_callback(const sensor_msgs::msg::LaserScan::ConstSharedPtr &lidar_1_msg,
                      const sensor_msgs::msg::LaserScan::ConstSharedPtr &lidar_2_msg);
    void project_scans(const sensor_msgs::msg::LaserScan::ConstSharedPtr &lidar_1_msg,
                       const sensor_msgs::msg::LaserScan::ConstSharedPtr &lidar_2_msg,
                       sensor_msgs::msg::PointCloud2 &cloud_in_1, sensor_msgs::msg::PointCloud2 &cloud_in_2);
    bool merge_clouds_calibration(sensor_msgs::msg::PointCloud2 &cloud_in_1, sensor_msgs::msg::PointCloud2 &cloud_in_2,
                                  pcl::PointCloud<pcl::PointXYZ> &pcl_cloud_out);
    bool merge_clouds_legacy(const sensor_msgs::msg::LaserScan::ConstSharedPtr &lidar_1_msg,
                             const sensor_msgs::msg::LaserScan::ConstSharedPtr &lidar_2_msg,
                             sensor_msgs::msg::PointCloud2 &cloud_in_1, sensor_msgs::msg::PointCloud2 &cloud_in_2,
                             pcl::PointCloud<pcl::PointXYZ> &pcl_cloud_out);
    void apply_shadow_filter(pcl::PointCloud<pcl::PointXYZ> &cloud);
    void convert_to_laserscan(const sensor_msgs::msg::PointCloud2 &cloud_out, const std::string &output_frame,
                              sensor_msgs::msg::LaserScan &merged);
    void declare_param();
    void refresh_param();
    void validate_params();
    bool load_calibration();
    bool load_filter_config();
    void apply_exclusion_zones(pcl::PointCloud<pcl::PointXYZ> &cloud);
    void apply_mapping_mode_filter(pcl::PointCloud<pcl::PointXYZ> &cloud);
    void transform_cloud(pcl::PointCloud<pcl::PointXYZ> &cloud, double tx, double ty, double cos_yaw, double sin_yaw);
    // Returns false when the pair must be discarded because |t1 - t2| exceeds max_pair_skew.
    bool accept_pair_skew(const rclcpp::Time &t1, const rclcpp::Time &t2, double &skew_out);
    rclcpp::Time resolve_output_stamp(const rclcpp::Time &t1, const rclcpp::Time &t2) const;
    void report_sync_stats();
};

} // namespace merger_node

#endif // DUAL_LASER_MERGER__DUAL_LASER_MERGER_HPP_
