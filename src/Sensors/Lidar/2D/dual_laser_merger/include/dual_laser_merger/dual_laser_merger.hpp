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

#include "geometry_msgs/msg/transform_stamped.hpp"
#include "laser_geometry/laser_geometry.hpp"
#include "message_filters/subscriber.h"
#include "message_filters/sync_policies/approximate_time.h"
#include "message_filters/synchronizer.h"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"
#include "sensor_msgs/point_cloud2_iterator.hpp"
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
};

} // namespace merger_node

#endif // DUAL_LASER_MERGER__DUAL_LASER_MERGER_HPP_
