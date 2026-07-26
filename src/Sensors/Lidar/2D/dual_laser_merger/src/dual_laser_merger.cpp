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

#include "dual_laser_merger/dual_laser_merger.hpp"

namespace merger_node
{
MergerNode::MergerNode(const rclcpp::NodeOptions &options)
    : Node("dual_laser_merger", options), calibration_loaded_(false), m2f_tx_(0), m2f_ty_(0), m2f_cos_(1), m2f_sin_(0),
      m2r_tx_(0), m2r_ty_(0), m2r_cos_(1), m2r_sin_(0), laser_1_flipped_(false), laser_2_flipped_(false)
{
    declare_param();

    merged_scan_pub = this->create_publisher<sensor_msgs::msg::LaserScan>(
        this->get_parameter("merged_scan_topic").as_string(), rclcpp::SensorDataQoS());
    merged_cloud_pub = this->create_publisher<sensor_msgs::msg::PointCloud2>(
        this->get_parameter("merged_cloud_topic").as_string(), rclcpp::SensorDataQoS());
    laser_1_sub.subscribe(this, this->get_parameter("laser_1_topic").as_string(),
                          rclcpp::SensorDataQoS().get_rmw_qos_profile());
    laser_2_sub.subscribe(this, this->get_parameter("laser_2_topic").as_string(),
                          rclcpp::SensorDataQoS().get_rmw_qos_profile());

    tf2_buffer = std::make_shared<tf2_ros::Buffer>(this->get_clock());
    tf2_listener = std::make_shared<tf2_ros::TransformListener>(*tf2_buffer, this);
    message_filter = std::make_shared<message_filters::Synchronizer<
        message_filters::sync_policies::ApproximateTime<sensor_msgs::msg::LaserScan, sensor_msgs::msg::LaserScan>>>(
        message_filters::sync_policies::ApproximateTime<sensor_msgs::msg::LaserScan, sensor_msgs::msg::LaserScan>(
            input_queue_size_param),
        laser_1_sub, laser_2_sub);
    message_filter->setAgePenalty(tolerance_param);
    message_filter->registerCallback(
        std::bind(&MergerNode::sub_callback, this, std::placeholders::_1, std::placeholders::_2));
    tf2_broadcaster = std::make_shared<tf2_ros::TransformBroadcaster>(*this);
    static_tf_broadcaster = std::make_shared<tf2_ros::StaticTransformBroadcaster>(*this);

    // Load calibration YAML
    calibration_loaded_ = load_calibration();
    if (calibration_loaded_)
    {
        RCLCPP_INFO(this->get_logger(), "Calibration mode: merging in '%s' frame", merged_scan_frame_param.c_str());
    }
    else if (!target_frame_param.empty())
    {
        RCLCPP_INFO(this->get_logger(), "Legacy mode: merging in '%s' frame", target_frame_param.c_str());
    }
    else
    {
        RCLCPP_ERROR(this->get_logger(), "No calibration file and no target_frame. Cannot merge.");
    }

    // Load exclusion zone config
    if (enable_exclusion_zones_param && !filter_config_file_param.empty())
    {
        if (!load_filter_config())
        {
            RCLCPP_WARN(this->get_logger(), "Exclusion zones enabled but filter config failed to load. "
                                            "Disabling exclusion zones.");
            enable_exclusion_zones_param = false;
        }
    }

    // Log mapping mode status
    if (enable_mapping_mode_param)
    {
        RCLCPP_INFO(this->get_logger(), "Mapping mode enabled: keeping points in angle range [%.1f, %.1f] deg",
                    mapping_keep_angle_min_param * 180.0 / M_PI, mapping_keep_angle_max_param * 180.0 / M_PI);
    }
}

void MergerNode::declare_param()
{
    this->declare_parameter("laser_1_topic", "laser_1");
    this->declare_parameter("laser_2_topic", "laser_2");
    this->declare_parameter("merged_scan_topic", "merged");
    this->declare_parameter("merged_cloud_topic", "merged_cloud");
    target_frame_param = this->declare_parameter("target_frame", "");
    tolerance_param = this->declare_parameter("tolerance", 0.01);
    input_queue_size_param =
        this->declare_parameter("queue_size", static_cast<int>(std::thread::hardware_concurrency()));
    min_height_param = this->declare_parameter("min_height", std::numeric_limits<double>::min());
    max_height_param = this->declare_parameter("max_height", std::numeric_limits<double>::max());
    angle_min_param = this->declare_parameter("angle_min", -M_PI);
    angle_max_param = this->declare_parameter("angle_max", M_PI);
    angle_increment_param = this->declare_parameter("angle_increment", M_PI / 180.0);
    scan_time_param = this->declare_parameter("scan_time", 1.0 / 30.0);
    range_min_param = this->declare_parameter("range_min", 0.0);
    range_max_param = this->declare_parameter("range_max", std::numeric_limits<double>::max());
    inf_epsilon_param = this->declare_parameter("inf_epsilon", 1.0);
    use_inf_param = this->declare_parameter("use_inf", true);
    enable_dynamic_param_refresh_param = this->declare_parameter("enable_dynamic_param_refresh", false);
    laser_1_x_offset = this->declare_parameter("laser_1_x_offset", 0.0);
    laser_1_y_offset = this->declare_parameter("laser_1_y_offset", 0.0);
    laser_1_yaw_offset = this->declare_parameter("laser_1_yaw_offset", 0.0);
    laser_2_x_offset = this->declare_parameter("laser_2_x_offset", 0.0);
    laser_2_y_offset = this->declare_parameter("laser_2_y_offset", 0.0);
    laser_2_yaw_offset = this->declare_parameter("laser_2_yaw_offset", 0.0);
    allowed_radius_param = this->declare_parameter("allowed_radius", 1.0);
    enable_shadow_filter_param = this->declare_parameter("enable_shadow_filter", false);
    enable_average_filter_param = this->declare_parameter("enable_average_filter", false);

    // Calibration YAML parameters
    calibration_file_param = this->declare_parameter("calibration_file", "");
    merged_scan_frame_param = this->declare_parameter("merged_scan_frame", "merged_scan");
    laser_1_frame_param = this->declare_parameter("laser_1_frame", "scan_front");
    laser_2_frame_param = this->declare_parameter("laser_2_frame", "scan_rear");

    // Exclusion zone parameters
    filter_config_file_param = this->declare_parameter("filter_config_file", "");
    enable_exclusion_zones_param = this->declare_parameter("enable_exclusion_zones", false);

    // Mapping mode parameters
    // Points are KEPT only if their atan2 angle is within [keep_angle_min, keep_angle_max].
    // Points outside this range (behind the robot) are removed.
    // Default: keep front 270-degree arc [-135, +135] deg, remove rear 90-degree arc.
    enable_mapping_mode_param = this->declare_parameter("enable_mapping_mode", false);
    mapping_keep_angle_min_param = this->declare_parameter("mapping_keep_angle_min", -2.356194); // -135 deg (= -3*PI/4)
    mapping_keep_angle_max_param = this->declare_parameter("mapping_keep_angle_max", 2.356194);  //  135 deg (= 3*PI/4)
}

void MergerNode::refresh_param()
{
    this->get_parameter("tolerance", tolerance_param);
    this->get_parameter("queue_size", input_queue_size_param);
    this->get_parameter("min_height", min_height_param);
    this->get_parameter("max_height", max_height_param);
    this->get_parameter("angle_min", angle_min_param);
    this->get_parameter("angle_max", angle_max_param);
    this->get_parameter("angle_increment", angle_increment_param);
    this->get_parameter("scan_time", scan_time_param);
    this->get_parameter("range_min", range_min_param);
    this->get_parameter("range_max", range_max_param);
    this->get_parameter("inf_epsilon", inf_epsilon_param);
    this->get_parameter("use_inf", use_inf_param);
    this->get_parameter("laser_1_x_offset", laser_1_x_offset);
    this->get_parameter("laser_1_y_offset", laser_1_y_offset);
    this->get_parameter("laser_1_yaw_offset", laser_1_yaw_offset);
    this->get_parameter("laser_2_x_offset", laser_2_x_offset);
    this->get_parameter("laser_2_y_offset", laser_2_y_offset);
    this->get_parameter("laser_2_yaw_offset", laser_2_yaw_offset);
    this->get_parameter("allowed_radius", allowed_radius_param);
    this->get_parameter("enable_shadow_filter", enable_shadow_filter_param);
    this->get_parameter("enable_average_filter", enable_average_filter_param);
    this->get_parameter("enable_exclusion_zones", enable_exclusion_zones_param);
    this->get_parameter("enable_mapping_mode", enable_mapping_mode_param);
    this->get_parameter("mapping_keep_angle_min", mapping_keep_angle_min_param);
    this->get_parameter("mapping_keep_angle_max", mapping_keep_angle_max_param);

    validate_params();
}

void MergerNode::validate_params()
{
    if (angle_increment_param <= 0.0)
    {
        RCLCPP_WARN(this->get_logger(), "angle_increment (%.6f) must be positive. Resetting to default (PI/180).",
                    angle_increment_param);
        angle_increment_param = M_PI / 180.0;
    }
    if (range_min_param < 0.0)
    {
        RCLCPP_WARN(this->get_logger(), "range_min (%.3f) must be >= 0. Resetting to 0.", range_min_param);
        range_min_param = 0.0;
    }
    if (range_max_param <= range_min_param)
    {
        RCLCPP_WARN(this->get_logger(),
                    "range_max (%.3f) must be > range_min (%.3f). Resetting range_max to max double.", range_max_param,
                    range_min_param);
        range_max_param = std::numeric_limits<double>::max();
    }
    if (angle_min_param >= angle_max_param)
    {
        RCLCPP_WARN(this->get_logger(), "angle_min (%.3f) must be < angle_max (%.3f). Resetting to [-PI, PI].",
                    angle_min_param, angle_max_param);
        angle_min_param = -M_PI;
        angle_max_param = M_PI;
    }
    if (mapping_keep_angle_min_param >= mapping_keep_angle_max_param)
    {
        RCLCPP_WARN(this->get_logger(),
                    "mapping_keep_angle_min (%.3f) must be < mapping_keep_angle_max (%.3f). "
                    "Resetting to defaults (-3*PI/4, 3*PI/4).",
                    mapping_keep_angle_min_param, mapping_keep_angle_max_param);
        mapping_keep_angle_min_param = -3.0 * M_PI / 4.0;
        mapping_keep_angle_max_param = 3.0 * M_PI / 4.0;
    }
}

bool MergerNode::load_calibration()
{
    if (calibration_file_param.empty())
    {
        return false;
    }

    try
    {
        YAML::Node config = YAML::LoadFile(calibration_file_param);
        auto cal = config["calibration"];

        // base_link → scan_front
        auto front = cal["merged_lidar_to_scan_front"];
        double front_tx = front["tx"].as<double>();
        double front_ty = front["ty"].as<double>();
        double front_yaw = front["yaw_rad"].as<double>();

        // base_link → scan_rear (ICP corrected)
        auto rear = cal["merged_lidar_to_scan_rear_corrected"];
        double rear_tx = rear["tx"].as<double>();
        double rear_ty = rear["ty"].as<double>();
        double rear_yaw = rear["yaw_rad"].as<double>();

        // Read flipped (upside-down) flags
        laser_1_flipped_ = front.IsDefined() && front["flipped"].IsDefined() ? front["flipped"].as<bool>() : false;
        laser_2_flipped_ = rear.IsDefined() && rear["flipped"].IsDefined() ? rear["flipped"].as<bool>() : false;

        // Precompute scan_merged → scan_front transform (YAML values directly)
        m2f_tx_ = front_tx;
        m2f_ty_ = front_ty;
        m2f_cos_ = std::cos(front_yaw);
        m2f_sin_ = std::sin(front_yaw);

        // Precompute scan_merged → scan_rear transform (YAML values directly)
        m2r_tx_ = rear_tx;
        m2r_ty_ = rear_ty;
        m2r_cos_ = std::cos(rear_yaw);
        m2r_sin_ = std::sin(rear_yaw);

        // Broadcast scan_merged → scan_front static TF
        geometry_msgs::msg::TransformStamped t_front;
        t_front.header.stamp = this->get_clock()->now();
        t_front.header.frame_id = merged_scan_frame_param;
        t_front.child_frame_id = laser_1_frame_param;
        t_front.transform.translation.x = front_tx;
        t_front.transform.translation.y = front_ty;
        t_front.transform.translation.z = 0.0;
        tf2::Quaternion q_front;
        q_front.setRPY(laser_1_flipped_ ? M_PI : 0.0, 0.0, front_yaw);
        t_front.transform.rotation.x = q_front.x();
        t_front.transform.rotation.y = q_front.y();
        t_front.transform.rotation.z = q_front.z();
        t_front.transform.rotation.w = q_front.w();

        // Broadcast scan_merged → scan_rear static TF
        geometry_msgs::msg::TransformStamped t_rear;
        t_rear.header.stamp = this->get_clock()->now();
        t_rear.header.frame_id = merged_scan_frame_param;
        t_rear.child_frame_id = laser_2_frame_param;
        t_rear.transform.translation.x = rear_tx;
        t_rear.transform.translation.y = rear_ty;
        t_rear.transform.translation.z = 0.0;
        tf2::Quaternion q_rear;
        q_rear.setRPY(laser_2_flipped_ ? M_PI : 0.0, 0.0, rear_yaw);
        t_rear.transform.rotation.x = q_rear.x();
        t_rear.transform.rotation.y = q_rear.y();
        t_rear.transform.rotation.z = q_rear.z();
        t_rear.transform.rotation.w = q_rear.w();

        std::vector<geometry_msgs::msg::TransformStamped> static_tfs;
        static_tfs.push_back(t_front);
        static_tfs.push_back(t_rear);
        static_tf_broadcaster->sendTransform(static_tfs);

        RCLCPP_INFO(this->get_logger(),
                    "Calibration loaded from: %s\n"
                    "  %s → %s: tx=%.4f ty=%.4f yaw=%.2fdeg flipped=%s\n"
                    "  %s → %s: tx=%.4f ty=%.4f yaw=%.2fdeg flipped=%s",
                    calibration_file_param.c_str(), merged_scan_frame_param.c_str(), laser_1_frame_param.c_str(),
                    front_tx, front_ty, front_yaw * 180.0 / M_PI, laser_1_flipped_ ? "true" : "false",
                    merged_scan_frame_param.c_str(), laser_2_frame_param.c_str(), rear_tx, rear_ty,
                    rear_yaw * 180.0 / M_PI, laser_2_flipped_ ? "true" : "false");

        return true;
    }
    catch (const std::exception &e)
    {
        RCLCPP_ERROR(this->get_logger(), "Failed to load calibration '%s': %s", calibration_file_param.c_str(),
                     e.what());
        return false;
    }
}

bool MergerNode::load_filter_config()
{
    if (filter_config_file_param.empty())
    {
        return false;
    }

    try
    {
        YAML::Node config = YAML::LoadFile(filter_config_file_param);
        auto zones = config["exclusion_zones"];

        if (!zones || !zones.IsSequence())
        {
            RCLCPP_WARN(this->get_logger(), "Filter config '%s': no 'exclusion_zones' sequence found.",
                        filter_config_file_param.c_str());
            return false;
        }

        exclusion_zones_.clear();
        for (const auto &zone_node : zones)
        {
            ExclusionZone zone;
            zone.name = zone_node["name"].as<std::string>("unnamed");
            zone.x_min = zone_node["x_min"].as<double>();
            zone.x_max = zone_node["x_max"].as<double>();
            zone.y_min = zone_node["y_min"].as<double>();
            zone.y_max = zone_node["y_max"].as<double>();

            if (zone.x_min >= zone.x_max || zone.y_min >= zone.y_max)
            {
                RCLCPP_WARN(this->get_logger(), "Exclusion zone '%s' has invalid bounds (min >= max). Skipping.",
                            zone.name.c_str());
                continue;
            }

            exclusion_zones_.push_back(zone);
            RCLCPP_INFO(this->get_logger(), "  Exclusion zone '%s': x=[%.3f, %.3f] y=[%.3f, %.3f]", zone.name.c_str(),
                        zone.x_min, zone.x_max, zone.y_min, zone.y_max);
        }

        RCLCPP_INFO(this->get_logger(), "Loaded %zu exclusion zone(s) from: %s", exclusion_zones_.size(),
                    filter_config_file_param.c_str());
        return !exclusion_zones_.empty();
    }
    catch (const std::exception &e)
    {
        RCLCPP_ERROR(this->get_logger(), "Failed to load filter config '%s': %s", filter_config_file_param.c_str(),
                     e.what());
        return false;
    }
}

void MergerNode::apply_exclusion_zones(pcl::PointCloud<pcl::PointXYZ> &cloud)
{
    if (exclusion_zones_.empty())
    {
        return;
    }

    pcl::PointCloud<pcl::PointXYZ> filtered;
    filtered.points.reserve(cloud.points.size());

    for (const auto &pt : cloud.points)
    {
        bool excluded = false;
        for (const auto &zone : exclusion_zones_)
        {
            if (pt.x >= zone.x_min && pt.x <= zone.x_max && pt.y >= zone.y_min && pt.y <= zone.y_max)
            {
                excluded = true;
                break;
            }
        }
        if (!excluded)
        {
            filtered.points.push_back(pt);
        }
    }

    filtered.width = filtered.points.size();
    filtered.height = 1;
    filtered.is_dense = cloud.is_dense;
    filtered.header = cloud.header;
    cloud = std::move(filtered);
}

void MergerNode::apply_mapping_mode_filter(pcl::PointCloud<pcl::PointXYZ> &cloud)
{
    pcl::PointCloud<pcl::PointXYZ> filtered;
    filtered.points.reserve(cloud.points.size());

    for (const auto &pt : cloud.points)
    {
        double angle = std::atan2(pt.y, pt.x);
        // Keep points within [keep_angle_min, keep_angle_max]; remove points outside (rear)
        if (angle >= mapping_keep_angle_min_param && angle <= mapping_keep_angle_max_param)
        {
            filtered.points.push_back(pt);
        }
    }

    filtered.width = filtered.points.size();
    filtered.height = 1;
    filtered.is_dense = cloud.is_dense;
    filtered.header = cloud.header;
    cloud = std::move(filtered);
}

static void apply_moving_average_3pt(const std::vector<float> &input_ranges, std::vector<float> &output_ranges)
{
    const size_t n = input_ranges.size();
    for (size_t i = 0; i < n; i++)
    {
        size_t prev = (i == 0) ? n - 1 : i - 1;
        size_t next = (i == n - 1) ? 0 : i + 1;
        output_ranges[i] = (input_ranges[prev] + input_ranges[i] + input_ranges[next]) / 3.0f;
    }
}

void MergerNode::transform_cloud(pcl::PointCloud<pcl::PointXYZ> &cloud, double tx, double ty, double cos_yaw,
                                 double sin_yaw)
{
    for (auto &pt : cloud.points)
    {
        double x = cos_yaw * pt.x - sin_yaw * pt.y + tx;
        double y = sin_yaw * pt.x + cos_yaw * pt.y + ty;
        pt.x = static_cast<float>(x);
        pt.y = static_cast<float>(y);
    }
}

// ── Extracted methods ──

void MergerNode::project_scans(const sensor_msgs::msg::LaserScan::ConstSharedPtr &lidar_1_msg,
                               const sensor_msgs::msg::LaserScan::ConstSharedPtr &lidar_2_msg,
                               sensor_msgs::msg::PointCloud2 &cloud_in_1, sensor_msgs::msg::PointCloud2 &cloud_in_2)
{
    if (enable_average_filter_param)
    {
        bool can_filter_1 = lidar_1_msg->ranges.size() >= 3;
        bool can_filter_2 = lidar_2_msg->ranges.size() >= 3;

        if (can_filter_1)
        {
            sensor_msgs::msg::LaserScan lidar_1_avg = *lidar_1_msg;
            apply_moving_average_3pt(lidar_1_msg->ranges, lidar_1_avg.ranges);
            projector.projectLaser(lidar_1_avg, cloud_in_1);
        }
        else
        {
            projector.projectLaser(*lidar_1_msg, cloud_in_1);
        }

        if (can_filter_2)
        {
            sensor_msgs::msg::LaserScan lidar_2_avg = *lidar_2_msg;
            apply_moving_average_3pt(lidar_2_msg->ranges, lidar_2_avg.ranges);
            projector.projectLaser(lidar_2_avg, cloud_in_2);
        }
        else
        {
            projector.projectLaser(*lidar_2_msg, cloud_in_2);
        }
    }
    else
    {
        projector.projectLaser(*lidar_1_msg, cloud_in_1);
        projector.projectLaser(*lidar_2_msg, cloud_in_2);
    }
}

bool MergerNode::merge_clouds_calibration(sensor_msgs::msg::PointCloud2 &cloud_in_1,
                                          sensor_msgs::msg::PointCloud2 &cloud_in_2,
                                          pcl::PointCloud<pcl::PointXYZ> &pcl_cloud_out)
{
    pcl::PointCloud<pcl::PointXYZ> pcl_cloud_in_1;
    pcl::PointCloud<pcl::PointXYZ> pcl_cloud_in_2;
    pcl::fromROSMsg(cloud_in_1, pcl_cloud_in_1);
    pcl::fromROSMsg(cloud_in_2, pcl_cloud_in_2);

    if (pcl_cloud_in_1.points.empty() || pcl_cloud_in_2.points.empty())
    {
        return false;
    }

    // Upside-down sensors: negate Y in sensor-local frame before rotation
    if (laser_1_flipped_)
    {
        for (auto &pt : pcl_cloud_in_1.points)
        {
            pt.y = -pt.y;
        }
    }
    if (laser_2_flipped_)
    {
        for (auto &pt : pcl_cloud_in_2.points)
        {
            pt.y = -pt.y;
        }
    }

    // Transform both clouds: sensor frame → merged_scan frame
    transform_cloud(pcl_cloud_in_1, m2f_tx_, m2f_ty_, m2f_cos_, m2f_sin_);
    transform_cloud(pcl_cloud_in_2, m2r_tx_, m2r_ty_, m2r_cos_, m2r_sin_);

    pcl_cloud_out = pcl_cloud_in_1;
    pcl_cloud_out += pcl_cloud_in_2;
    return true;
}

bool MergerNode::merge_clouds_legacy(const sensor_msgs::msg::LaserScan::ConstSharedPtr &lidar_1_msg,
                                     const sensor_msgs::msg::LaserScan::ConstSharedPtr &lidar_2_msg,
                                     sensor_msgs::msg::PointCloud2 &cloud_in_1,
                                     sensor_msgs::msg::PointCloud2 &cloud_in_2,
                                     pcl::PointCloud<pcl::PointXYZ> &pcl_cloud_out)
{
    geometry_msgs::msg::TransformStamped tf2_msg;
    tf2::Quaternion tf2_quaternion;

    if (lidar_1_msg->header.frame_id != target_frame_param)
    {
        tf2_msg.header = cloud_in_1.header;
        tf2_msg.child_frame_id = cloud_in_1.header.frame_id + "_calibrated";
        tf2_msg.transform.translation.x = laser_1_x_offset;
        tf2_msg.transform.translation.y = laser_1_y_offset;
        tf2_msg.transform.translation.z = 0.0;
        tf2_quaternion.setRPY(0, 0, laser_1_yaw_offset);
        tf2_msg.transform.rotation.x = tf2_quaternion.x();
        tf2_msg.transform.rotation.y = tf2_quaternion.y();
        tf2_msg.transform.rotation.z = tf2_quaternion.z();
        tf2_msg.transform.rotation.w = tf2_quaternion.w();
        tf2_broadcaster->sendTransform(tf2_msg);
        cloud_in_1.header.frame_id = tf2_msg.child_frame_id;

        try
        {
            cloud_in_1 = tf2_buffer->transform(cloud_in_1, target_frame_param, tf2::durationFromSec(tolerance_param));
        }
        catch (tf2::TransformException &ex)
        {
            RCLCPP_ERROR_STREAM(this->get_logger(), "Transform failure, Laser 1: " << ex.what());
            return false;
        }
    }

    if (lidar_2_msg->header.frame_id != target_frame_param)
    {
        tf2_msg.header = cloud_in_2.header;
        tf2_msg.child_frame_id = cloud_in_2.header.frame_id + "_calibrated";
        tf2_msg.transform.translation.x = laser_2_x_offset;
        tf2_msg.transform.translation.y = laser_2_y_offset;
        tf2_msg.transform.translation.z = 0.0;
        tf2_quaternion.setRPY(0, 0, laser_2_yaw_offset);
        tf2_msg.transform.rotation.x = tf2_quaternion.x();
        tf2_msg.transform.rotation.y = tf2_quaternion.y();
        tf2_msg.transform.rotation.z = tf2_quaternion.z();
        tf2_msg.transform.rotation.w = tf2_quaternion.w();
        tf2_broadcaster->sendTransform(tf2_msg);
        cloud_in_2.header.frame_id = tf2_msg.child_frame_id;

        try
        {
            cloud_in_2 = tf2_buffer->transform(cloud_in_2, target_frame_param, tf2::durationFromSec(tolerance_param));
        }
        catch (tf2::TransformException &ex)
        {
            RCLCPP_ERROR_STREAM(this->get_logger(), "Transform failure, Laser 2: " << ex.what());
            return false;
        }
    }

    pcl::PointCloud<pcl::PointXYZ> pcl_cloud_in_1;
    pcl::PointCloud<pcl::PointXYZ> pcl_cloud_in_2;
    pcl::fromROSMsg(cloud_in_1, pcl_cloud_in_1);
    pcl::fromROSMsg(cloud_in_2, pcl_cloud_in_2);

    if (pcl_cloud_in_1.points.empty() || pcl_cloud_in_2.points.empty())
    {
        return false;
    }

    pcl_cloud_out = pcl_cloud_in_1;
    pcl_cloud_out += pcl_cloud_in_2;
    return true;
}

void MergerNode::apply_shadow_filter(pcl::PointCloud<pcl::PointXYZ> &cloud)
{
    double allowed_radius_scaled = allowed_radius_param / range_max_param;
    pcl::KdTreeFLANN<pcl::PointXYZ> kdtree;
    std::vector<int> pointIndices;
    std::vector<float> pointDistances;
    kdtree.setInputCloud(cloud.makeShared());

    for (auto &point : cloud.points)
    {
        double dist_from_origin = std::sqrt(std::pow(point.x, 2) + std::pow(point.y, 2));
        int numNearbyPoints =
            kdtree.radiusSearch(point, allowed_radius_scaled * dist_from_origin, pointIndices, pointDistances);
        numNearbyPoints -= 1;
        if (numNearbyPoints == 0)
        {
            if (use_inf_param)
            {
                point.x = std::numeric_limits<double>::infinity();
                point.y = std::numeric_limits<double>::infinity();
            }
            else
            {
                point.x = range_max_param + inf_epsilon_param;
                point.y = range_max_param + inf_epsilon_param;
            }
        }
    }
}

void MergerNode::convert_to_laserscan(const sensor_msgs::msg::PointCloud2 &cloud_out, const std::string &output_frame,
                                      sensor_msgs::msg::LaserScan &merged)
{
    merged.header = cloud_out.header;
    merged.header.frame_id = output_frame;

    merged.angle_min = angle_min_param;
    merged.angle_max = angle_max_param;
    merged.angle_increment = angle_increment_param;
    merged.time_increment = 0.0;
    merged.scan_time = scan_time_param;
    merged.range_min = range_min_param;
    merged.range_max = range_max_param;

    uint32_t ranges_size = std::ceil((merged.angle_max - merged.angle_min) / merged.angle_increment);

    if (use_inf_param)
    {
        merged.ranges.assign(ranges_size, std::numeric_limits<double>::infinity());
    }
    else
    {
        merged.ranges.assign(ranges_size, merged.range_max + inf_epsilon_param);
    }

    for (sensor_msgs::PointCloud2ConstIterator<float> iter_x(cloud_out, "x"), iter_y(cloud_out, "y"),
         iter_z(cloud_out, "z");
         iter_x != iter_x.end(); ++iter_x, ++iter_y, ++iter_z)
    {
        if (std::isnan(*iter_x) || std::isnan(*iter_y) || std::isnan(*iter_z) || *iter_z > max_height_param ||
            *iter_z < min_height_param)
        {
            continue;
        }

        double range = hypot(*iter_x, *iter_y);
        if (range < merged.range_min || range > merged.range_max)
        {
            continue;
        }

        double angle = atan2(*iter_y, *iter_x);
        if (angle < merged.angle_min || angle > merged.angle_max)
        {
            continue;
        }

        int index = std::lround((angle - merged.angle_min) / merged.angle_increment);
        if (index < 0 || static_cast<uint32_t>(index) >= ranges_size)
        {
            continue;
        }
        if (range < merged.ranges[index])
        {
            merged.ranges[index] = range;
        }
    }
}

// ── Main callback (orchestrator) ──

void MergerNode::sub_callback(const sensor_msgs::msg::LaserScan::ConstSharedPtr &lidar_1_msg,
                              const sensor_msgs::msg::LaserScan::ConstSharedPtr &lidar_2_msg)
{
    if (!calibration_loaded_ && target_frame_param.empty())
    {
        RCLCPP_ERROR(this->get_logger(), "No calibration file and no target_frame. Cannot merge. Skipping callback.");
        return;
    }

    this->get_parameter<bool>("enable_dynamic_param_refresh", enable_dynamic_param_refresh_param);
    if (enable_dynamic_param_refresh_param && !calibration_loaded_)
    {
        refresh_param();
    }

    // Step 1: Project LaserScans to PointCloud2 (with optional average filter)
    sensor_msgs::msg::PointCloud2 cloud_in_1;
    sensor_msgs::msg::PointCloud2 cloud_in_2;
    project_scans(lidar_1_msg, lidar_2_msg, cloud_in_1, cloud_in_2);

    // Step 2: Transform and merge clouds
    pcl::PointCloud<pcl::PointXYZ> pcl_cloud_out;
    if (calibration_loaded_)
    {
        if (!merge_clouds_calibration(cloud_in_1, cloud_in_2, pcl_cloud_out))
        {
            return;
        }
    }
    else
    {
        if (!merge_clouds_legacy(lidar_1_msg, lidar_2_msg, cloud_in_1, cloud_in_2, pcl_cloud_out))
        {
            return;
        }
    }

    // Step 2.5a: Exclusion zone filter (remove body reflections)
    if (enable_exclusion_zones_param)
    {
        apply_exclusion_zones(pcl_cloud_out);
    }

    // Step 2.5b: Mapping mode filter (remove rear points)
    if (enable_mapping_mode_param)
    {
        apply_mapping_mode_filter(pcl_cloud_out);
    }

    // Step 3: Shadow filter (optional)
    if (enable_shadow_filter_param)
    {
        apply_shadow_filter(pcl_cloud_out);
    }

    // Step 4: Publish merged PointCloud2
    sensor_msgs::msg::PointCloud2 cloud_out;
    pcl::toROSMsg(pcl_cloud_out, cloud_out);
    merged_cloud_pub->publish(cloud_out);

    // Step 5: Convert to LaserScan and publish
    std::string output_frame = calibration_loaded_ ? merged_scan_frame_param : target_frame_param;
    sensor_msgs::msg::LaserScan merged;
    convert_to_laserscan(cloud_out, output_frame, merged);
    merged_scan_pub->publish(merged);
}

} // namespace merger_node

#include "rclcpp_components/register_node_macro.hpp"

RCLCPP_COMPONENTS_REGISTER_NODE(merger_node::MergerNode)
