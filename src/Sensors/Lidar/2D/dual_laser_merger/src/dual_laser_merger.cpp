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
namespace
{
// Throttle for the two "this keeps happening" warnings. 2 s keeps them readable at 34 Hz.
constexpr int kWarnThrottleMs = 2000;
// A reporting window longer than this multiple of the nominal period means the clock jumped
// (e.g. use_sim_time attaching to /clock after construction) rather than that we were slow.
constexpr double kClockJumpFactor = 10.0;
} // namespace

MergerNode::MergerNode(const rclcpp::NodeOptions &options)
    : Node("dual_laser_merger", options), calibration_loaded_(false), m2f_tx_(0), m2f_ty_(0), m2f_cos_(1), m2f_sin_(0),
      m2r_tx_(0), m2r_ty_(0), m2r_cos_(1), m2r_sin_(0), laser_1_flipped_(false), laser_2_flipped_(false),
      max_pair_skew_param(0.0), publish_sync_diagnostics_param(true), output_stamp_param("laser_1"),
      sync_report_period_param(5.0), pair_count_(0), skew_reject_count_(0), skew_reject_window_(0), in_count_1_(0),
      in_count_2_(0), merge_fail_count_(0), skew_sum_(0.0), skew_max_(0.0),
      skew_report_last_(this->get_clock()->now())
{
    declare_param();
    // validate_params() used to be reachable only through refresh_param(), which sub_callback()
    // guards with `enable_dynamic_param_refresh && !calibration_loaded_`. The canonical launch
    // supplies a calibration file, so calibration_loaded_ is true and validation never ran —
    // every range/whitelist check in it was dead code. Validate once here, before any parameter
    // is consumed (setMaxIntervalDuration below reads max_pair_skew_param).
    validate_params();

    merged_scan_pub = this->create_publisher<sensor_msgs::msg::LaserScan>(
        this->get_parameter("merged_scan_topic").as_string(), rclcpp::SensorDataQoS());
    merged_cloud_pub = this->create_publisher<sensor_msgs::msg::PointCloud2>(
        this->get_parameter("merged_cloud_topic").as_string(), rclcpp::SensorDataQoS());
    // Always advertise; publish_sync_diagnostics only gates whether we write to it. Creating the
    // publisher conditionally made the parameter un-toggleable at runtime and forced a second
    // null-check at the publish site.
    // RELIABLE on purpose: SensorDataQoS is BEST_EFFORT, which `ros2 topic echo` (RELIABLE by
    // default) refuses to connect to — the first thing anyone investigating skew would try.
    // 34 Hz x 8 bytes is 272 B/s, so reliability costs nothing here.
    sync_skew_pub =
        this->create_publisher<std_msgs::msg::Float64>("~/sync_skew", rclcpp::QoS(rclcpp::KeepLast(50)).reliable());
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
    // NOTE: setAgePenalty is *not* a time tolerance. It weights "how old is the candidate" against
    // "how tight is the interval" in the matching cost, i.e. it trades latency for match quality.
    // The only stamp-distance bound the policy owns is setMaxIntervalDuration(), which defaults to
    // INT32_MAX seconds. Leaving it at the default means any two scans can be paired.
    message_filter->setAgePenalty(tolerance_param);
    if (max_pair_skew_param > 0.0)
    {
        message_filter->setMaxIntervalDuration(rclcpp::Duration::from_seconds(max_pair_skew_param));
    }
    message_filter->registerCallback(
        std::bind(&MergerNode::sub_callback, this, std::placeholders::_1, std::placeholders::_2));
    // Count what arrives, not just what pairs up. The policy can drop a scan before sub_callback
    // ever runs, so without these the log cannot distinguish "input stopped" from "pairing failed".
    laser_1_sub.registerCallback(
        std::function<void(const sensor_msgs::msg::LaserScan::ConstSharedPtr &)>(
            [this](const sensor_msgs::msg::LaserScan::ConstSharedPtr &) { in_count_1_++; }));
    laser_2_sub.registerCallback(
        std::function<void(const sensor_msgs::msg::LaserScan::ConstSharedPtr &)>(
            [this](const sensor_msgs::msg::LaserScan::ConstSharedPtr &) { in_count_2_++; }));

    // Time-driven, not callback-driven. Reporting from sub_callback() meant that the one failure
    // the diagnostic exists to catch — the synchroniser stops producing pairs — also stopped the
    // reporting, so silence read as "healthy". The timer joins the node's default callback group,
    // the same MutuallyExclusive group as the scan callbacks, so the counters stay serialised.
    if (publish_sync_diagnostics_param)
    {
        sync_report_timer_ = this->create_wall_timer(std::chrono::duration<double>(sync_report_period_param),
                                                     std::bind(&MergerNode::report_sync_stats, this));
    }
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
    // NOTE: not numeric_limits<double>::min() — that is the smallest *positive* normal (2.2e-308),
    // so the old default rejected every point (projectLaser emits z = 0, and 0 < 2.2e-308).
    // Running the node without a parameter file produced an all-inf scan; the canonical launches
    // only hid it by setting min_height explicitly.
    min_height_param = this->declare_parameter("min_height", -std::numeric_limits<double>::max());
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
    // "scan_merged", not "merged_scan": the canonical launch publishes base_link -> scan_merged and
    // passes merged_scan_frame:=scan_merged. With the old default the node broadcast
    // merged_scan -> scan_front/scan_rear while nobody published base_link -> merged_scan, so the
    // TF tree silently split in two.
    merged_scan_frame_param = this->declare_parameter("merged_scan_frame", "scan_merged");
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

    // Pair synchronisation. Defaults reproduce the legacy behaviour exactly:
    //   max_pair_skew = 0.0  → no bound on |t_front - t_rear| (what the node always did)
    //   output_stamp  = "laser_1" → merged stamp is laser 1's stamp (what the node always did,
    //                   as a side effect of pcl_cloud_out being copy-constructed from cloud 1)
    // For pose-critical consumers (docking, ICP odometry) set max_pair_skew to a fraction of the
    // scan period and output_stamp to "latest".
    // max_pair_skew is baked into the synchroniser policy by setMaxIntervalDuration() at
    // construction, so a runtime change would only move the callback-side gate and leave the policy
    // on the old value — half-applied, while `ros2 param set` reports success. Refuse the write
    // instead.
    rcl_interfaces::msg::ParameterDescriptor skew_desc;
    skew_desc.description = "[s] Upper bound on |t_front - t_rear| for a pair to be published. "
                            "0 disables the bound (legacy behaviour). Read-only: applied at startup.";
    skew_desc.read_only = true;
    max_pair_skew_param = this->declare_parameter("max_pair_skew", 0.0, skew_desc);

    rcl_interfaces::msg::ParameterDescriptor diag_desc;
    diag_desc.description = "Publish ~/sync_skew and log the periodic sync statistics line. "
                            "Read-only: the report timer is created at startup.";
    diag_desc.read_only = true;
    publish_sync_diagnostics_param = this->declare_parameter("publish_sync_diagnostics", true, diag_desc);

    rcl_interfaces::msg::ParameterDescriptor period_desc;
    period_desc.description = "[s] Period of the sync statistics log line. Read-only: timer period "
                              "is fixed at startup.";
    period_desc.read_only = true;
    sync_report_period_param = this->declare_parameter("sync_report_period", 5.0, period_desc);

    // output_stamp is consumed per-callback, so it is safe to change at runtime.
    output_stamp_param = this->declare_parameter("output_stamp", std::string("laser_1"));
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
    // Only output_stamp is refreshed among the sync parameters — the other three are declared
    // read_only precisely because re-reading them here could not take full effect.
    this->get_parameter("output_stamp", output_stamp_param);

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
    if (min_height_param >= max_height_param)
    {
        RCLCPP_WARN(this->get_logger(),
                    "min_height (%.3g) must be < max_height (%.3g). Resetting to [-DBL_MAX, DBL_MAX].",
                    min_height_param, max_height_param);
        min_height_param = -std::numeric_limits<double>::max();
        max_height_param = std::numeric_limits<double>::max();
    }
    if (enable_shadow_filter_param && range_max_param >= std::numeric_limits<double>::max())
    {
        // allowed_radius_scaled = allowed_radius / range_max collapses to 0, so radiusSearch finds
        // only the point itself and every point is turned into inf. Refuse rather than silently
        // blanking the scan.
        RCLCPP_ERROR(this->get_logger(),
                     "enable_shadow_filter requires a finite range_max (got %.3g) — the scaled radius "
                     "would be 0 and every point would be discarded. Disabling the shadow filter.",
                     range_max_param);
        enable_shadow_filter_param = false;
    }
    if (max_pair_skew_param < 0.0)
    {
        RCLCPP_WARN(this->get_logger(), "max_pair_skew (%.4f) must be >= 0. Resetting to 0 (unbounded).",
                    max_pair_skew_param);
        max_pair_skew_param = 0.0;
    }
    if (output_stamp_param != "laser_1" && output_stamp_param != "laser_2" && output_stamp_param != "latest" &&
        output_stamp_param != "earliest" && output_stamp_param != "midpoint")
    {
        RCLCPP_WARN(this->get_logger(),
                    "output_stamp '%s' is not one of laser_1|laser_2|latest|earliest|midpoint. "
                    "Resetting to 'laser_1'.",
                    output_stamp_param.c_str());
        output_stamp_param = "laser_1";
    }
}

bool MergerNode::accept_pair_skew(const rclcpp::Time &t1, const rclcpp::Time &t2, double &skew_out)
{
    const double signed_skew = (t1 - t2).seconds(); // >0 means laser_1 is newer than laser_2
    skew_out = std::fabs(signed_skew);

    // Measure unconditionally, gate afterwards. A pair the gate rejects is precisely the pair whose
    // skew you need in order to choose max_pair_skew — recording it only on the accept path made
    // the log claim "max 0.00 ms" while every pair was being dropped for excessive skew.
    skew_max_ = std::max(skew_max_, skew_out);
    if (publish_sync_diagnostics_param)
    {
        std_msgs::msg::Float64 skew_msg;
        skew_msg.data = signed_skew;
        sync_skew_pub->publish(skew_msg);
    }

    if (max_pair_skew_param > 0.0 && skew_out > max_pair_skew_param)
    {
        skew_reject_count_++;
        skew_reject_window_++;
        RCLCPP_WARN_THROTTLE(this->get_logger(), *this->get_clock(), kWarnThrottleMs,
                             "Dropping scan pair: stamp skew %.1f ms > max_pair_skew %.1f ms (%lu dropped in total).",
                             skew_out * 1e3, max_pair_skew_param * 1e3,
                             static_cast<unsigned long>(skew_reject_count_));
        return false;
    }

    pair_count_++;
    skew_sum_ += skew_out;
    return true;
}

rclcpp::Time MergerNode::resolve_output_stamp(const rclcpp::Time &t1, const rclcpp::Time &t2) const
{
    if (output_stamp_param == "laser_2")
    {
        return t2;
    }
    if (output_stamp_param == "latest")
    {
        return (t1 > t2) ? t1 : t2;
    }
    if (output_stamp_param == "earliest")
    {
        return (t1 < t2) ? t1 : t2;
    }
    if (output_stamp_param == "midpoint")
    {
        return t1 + rclcpp::Duration::from_seconds((t2 - t1).seconds() / 2.0);
    }
    return t1; // "laser_1" (default, legacy behaviour)
}

void MergerNode::report_sync_stats()
{
    const rclcpp::Time now = this->get_clock()->now();
    double elapsed = (now - skew_report_last_).seconds();

    // A clock jump (use_sim_time attaching to /clock after construction) can make elapsed negative
    // or absurd. Resync and drop the window rather than reporting a bogus rate — or, worse,
    // latching into a state where the window never closes again.
    if (elapsed <= 0.0 || elapsed > kClockJumpFactor * sync_report_period_param)
    {
        RCLCPP_WARN(this->get_logger(), "sync: clock jumped (%.3f s window) — discarding this window.", elapsed);
        pair_count_ = 0;
        skew_reject_window_ = 0;
        in_count_1_ = 0;
        in_count_2_ = 0;
        skew_sum_ = 0.0;
        skew_max_ = 0.0;
        skew_report_last_ = now;
        return;
    }

    const uint64_t seen = pair_count_ + skew_reject_window_;
    if (seen == 0)
    {
        // Silence is the symptom, so say it out loud. Reaching here means the synchroniser produced
        // no pair at all for a whole window: an input stopped, or the two stamps never match.
        RCLCPP_WARN(this->get_logger(),
                    "sync: no scan pairs in %.1f s (inputs received %lu/%lu) — %s",
                    elapsed, static_cast<unsigned long>(in_count_1_), static_cast<unsigned long>(in_count_2_),
                    (in_count_1_ == 0 || in_count_2_ == 0)
                        ? "an input topic is silent."
                        : "both inputs are publishing but no pair could be formed (check stamps/max_pair_skew).");
    }
    else
    {
        // in/out lets the reader see losses the pair counters cannot: if in is 170/170 but pairs is
        // 120 and dropped-by-skew is 0, the synchroniser policy discarded them internally.
        RCLCPP_INFO(this->get_logger(),
                    "sync: in %lu/%lu -> %lu pairs (%.2f/s) over %.1fs | skew(accepted) mean %.2f ms"
                    " | skew(observed) max %.2f ms | dropped-by-skew %lu this window, %lu total",
                    static_cast<unsigned long>(in_count_1_), static_cast<unsigned long>(in_count_2_),
                    static_cast<unsigned long>(pair_count_), pair_count_ / elapsed, elapsed,
                    pair_count_ > 0 ? (skew_sum_ / pair_count_) * 1e3 : 0.0, skew_max_ * 1e3,
                    static_cast<unsigned long>(skew_reject_window_),
                    static_cast<unsigned long>(skew_reject_count_));
    }

    pair_count_ = 0;
    skew_reject_window_ = 0;
    in_count_1_ = 0;
    in_count_2_ = 0;
    skew_sum_ = 0.0;
    skew_max_ = 0.0;
    skew_report_last_ = now;
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

// Shared skeleton for the point filters: reserve, test, keep, restore the cloud metadata. The two
// callers below used to repeat all of it and differ only in the predicate, which is also how one of
// them ended up with an early-out for the empty case and the other without.
template <typename Predicate>
static void filter_cloud(pcl::PointCloud<pcl::PointXYZ> &cloud, Predicate keep)
{
    pcl::PointCloud<pcl::PointXYZ> filtered;
    filtered.points.reserve(cloud.points.size());

    for (const auto &pt : cloud.points)
    {
        if (keep(pt))
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

void MergerNode::apply_exclusion_zones(pcl::PointCloud<pcl::PointXYZ> &cloud)
{
    if (exclusion_zones_.empty())
    {
        return;
    }

    filter_cloud(cloud, [this](const pcl::PointXYZ &pt) {
        for (const auto &zone : exclusion_zones_)
        {
            if (pt.x >= zone.x_min && pt.x <= zone.x_max && pt.y >= zone.y_min && pt.y <= zone.y_max)
            {
                return false;
            }
        }
        return true;
    });
}

void MergerNode::apply_mapping_mode_filter(pcl::PointCloud<pcl::PointXYZ> &cloud)
{
    // Keep points within [keep_angle_min, keep_angle_max]; remove points outside (rear)
    filter_cloud(cloud, [this](const pcl::PointXYZ &pt) {
        const double angle = std::atan2(pt.y, pt.x);
        return angle >= mapping_keep_angle_min_param && angle <= mapping_keep_angle_max_param;
    });
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

    // Step 0: Pair quality gate. ApproximateTime hands us the best-matching pair it could form,
    // not a pair that is guaranteed to be close in time. Measure the skew, optionally reject.
    const rclcpp::Time stamp_1(lidar_1_msg->header.stamp);
    const rclcpp::Time stamp_2(lidar_2_msg->header.stamp);
    double pair_skew = 0.0;
    if (!accept_pair_skew(stamp_1, stamp_2, pair_skew))
    {
        return;
    }
    RCLCPP_DEBUG(this->get_logger(), "pair skew %.3f ms (laser_1 %.6f, laser_2 %.6f)", pair_skew * 1e3,
                 stamp_1.seconds(), stamp_2.seconds());

    // Step 1: Project LaserScans to PointCloud2 (with optional average filter)
    sensor_msgs::msg::PointCloud2 cloud_in_1;
    sensor_msgs::msg::PointCloud2 cloud_in_2;
    project_scans(lidar_1_msg, lidar_2_msg, cloud_in_1, cloud_in_2);

    // Step 2: Transform and merge clouds
    pcl::PointCloud<pcl::PointXYZ> pcl_cloud_out;
    const bool merged_ok = calibration_loaded_
                               ? merge_clouds_calibration(cloud_in_1, cloud_in_2, pcl_cloud_out)
                               : merge_clouds_legacy(lidar_1_msg, lidar_2_msg, cloud_in_1, cloud_in_2, pcl_cloud_out);
    if (!merged_ok)
    {
        // Used to return silently. An empty input cloud or a TF failure would stop /scan_merged with
        // no trace at all, which is indistinguishable from "no input" at the consumer.
        merge_fail_count_++;
        RCLCPP_WARN_THROTTLE(this->get_logger(), *this->get_clock(), kWarnThrottleMs,
                             "Merge produced no cloud (empty input or transform failure) — no output for this "
                             "pair. %lu such pairs so far.",
                             static_cast<unsigned long>(merge_fail_count_));
        return;
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

    // Step 4: Publish merged PointCloud2.
    // The stamp carried this far comes from cloud 1 alone (pcl_cloud_out was copy-constructed from
    // it) and, on the way through PCL, was truncated to microseconds. Restore an explicit,
    // policy-selected stamp on both outputs so consumers are not silently given laser 1's clock.
    const std::string output_frame = calibration_loaded_ ? merged_scan_frame_param : target_frame_param;
    sensor_msgs::msg::PointCloud2 cloud_out;
    pcl::toROSMsg(pcl_cloud_out, cloud_out);
    // Both header fields have to be set explicitly. The stamp arrives here as laser 1's, truncated
    // to microseconds by the PCL round-trip; the frame_id arrives as laser 1's *sensor* frame even
    // though merge_clouds_calibration() already moved the points into the merged frame. The
    // LaserScan output was never affected because convert_to_laserscan() overwrites frame_id, so
    // only the PointCloud2 carried the mismatch.
    cloud_out.header.stamp = resolve_output_stamp(stamp_1, stamp_2);
    cloud_out.header.frame_id = output_frame;
    merged_cloud_pub->publish(cloud_out);

    // Step 5: Convert to LaserScan and publish
    sensor_msgs::msg::LaserScan merged;
    convert_to_laserscan(cloud_out, output_frame, merged);
    merged_scan_pub->publish(merged);
}

} // namespace merger_node

#include "rclcpp_components/register_node_macro.hpp"

RCLCPP_COMPONENTS_REGISTER_NODE(merger_node::MergerNode)
