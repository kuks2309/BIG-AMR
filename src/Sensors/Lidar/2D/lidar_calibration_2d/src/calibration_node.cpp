// Copyright 2025 T-Robotics
// 2D LiDAR Calibration Node
// Calibrates the rear LiDAR relative to the front LiDAR using SVD-ICP alignment.
// Approach: Fix scan_front as reference, align scan_rear to it using ICP on overlap region.

#include <geometry_msgs/msg/transform_stamped.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>

#include <tf2/utils.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/create_timer_ros.h>
#include <tf2_ros/static_transform_broadcaster.h>
#include <tf2_ros/transform_listener.h>

#include <message_filters/subscriber.h>
#include <message_filters/sync_policies/approximate_time.h>
#include <message_filters/synchronizer.h>

#include <Eigen/Core>

#include "lidar_calibration_2d/scan_preprocessor.hpp"
#include "lidar_calibration_2d/scan_utils.hpp"
#include "lidar_calibration_2d/svd_aligner.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>

namespace lidar_calibration_2d
{

// ---- Symmetry analysis result ----
struct SymmetryResult
{
    double ideal_rear_tx{0.0};
    double ideal_rear_ty{0.0};
    double ideal_rear_yaw{0.0};
    double delta_tx{0.0};
    double delta_ty{0.0};
    double delta_yaw{0.0};
    bool is_symmetric{false};
};

inline double normalizeAngle(double angle)
{
    while (angle > M_PI)
    {
        angle -= 2.0 * M_PI;
    }
    while (angle < -M_PI)
    {
        angle += 2.0 * M_PI;
    }
    return angle;
}

class CalibrationNode : public rclcpp::Node
{
  public:
    using LaserScan = sensor_msgs::msg::LaserScan;
    using SyncPolicy = message_filters::sync_policies::ApproximateTime<LaserScan, LaserScan>;

    explicit CalibrationNode(const rclcpp::NodeOptions &options) : Node("lidar_calibration_2d_node", options)
    {
        // ---- Parameters ----
        scan_topic_front_ = this->get_parameter_or<std::string>("scan_topic_front", "scan_front");
        scan_topic_rear_ = this->get_parameter_or<std::string>("scan_topic_rear", "scan_rear");
        enable_average_filter_ = this->get_parameter_or<bool>("enable_average_filter", true);
        num_samples_ = this->get_parameter_or<int>("num_samples", 30);
        sample_interval_ = this->get_parameter_or<double>("sample_interval", 0.1);
        min_range_ = this->get_parameter_or<double>("min_range", 0.5);
        max_range_ = this->get_parameter_or<double>("max_range", 8.0);
        min_overlap_points_ = this->get_parameter_or<int>("min_overlap_points", 50);
        downsample_stride_ = this->get_parameter_or<int>("downsample_stride", 10);
        icp_max_iterations_ = this->get_parameter_or<int>("icp_max_iterations", 50);
        icp_transform_epsilon_ = this->get_parameter_or<double>("icp_transform_epsilon", 1e-6);
        icp_max_correspondence_dist_ = this->get_parameter_or<double>("icp_max_correspondence_dist", 0.5);
        icp_min_correspondences_ = this->get_parameter_or<int>("icp_min_correspondences", 30);
        broadcast_corrected_tf_ = this->get_parameter_or<bool>("broadcast_corrected_tf", true);
        tf_broadcast_duration_ = this->get_parameter_or<double>("tf_broadcast_duration", 30.0);
        output_file_ = this->get_parameter_or<std::string>("output_file", "calibration_result.yaml");
        output_dir_ = this->get_parameter_or<std::string>("output_dir", "");
        transform_tolerance_ = this->get_parameter_or<double>("transform_tolerance", 0.1);

        // ---- TF2 setup ----
        tf_buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
        auto timer_interface = std::make_shared<tf2_ros::CreateTimerROS>(this->get_node_base_interface(),
                                                                         this->get_node_timers_interface());
        tf_buffer_->setCreateTimerInterface(timer_interface);
        tf_listener_ = std::make_unique<tf2_ros::TransformListener>(*tf_buffer_);

        // ---- message_filters subscribers with SensorDataQoS ----
        sub_front_.subscribe(this, scan_topic_front_, rclcpp::SensorDataQoS().get_rmw_qos_profile());
        sub_rear_.subscribe(this, scan_topic_rear_, rclcpp::SensorDataQoS().get_rmw_qos_profile());

        // ---- ApproximateTime synchronizer ----
        sync_ = std::make_shared<message_filters::Synchronizer<SyncPolicy>>(SyncPolicy(10), sub_front_, sub_rear_);
        sync_->registerCallback(
            std::bind(&CalibrationNode::syncCallback, this, std::placeholders::_1, std::placeholders::_2));

        RCLCPP_INFO(this->get_logger(), "=== 2D LiDAR Calibration Node Started ===");
        RCLCPP_INFO(this->get_logger(), "  Front topic: %s (reference), Rear topic: %s (to calibrate)",
                    scan_topic_front_.c_str(), scan_topic_rear_.c_str());
        RCLCPP_INFO(this->get_logger(), "  Method: scan_front-centric ICP alignment");
        RCLCPP_INFO(this->get_logger(), "  Samples: %d, Interval: %.2f s, Downsample stride: %d", num_samples_,
                    sample_interval_, downsample_stride_);
        RCLCPP_INFO(this->get_logger(), "  ICP: max_iter=%d, max_corr_dist=%.2f, min_corr=%d", icp_max_iterations_,
                    icp_max_correspondence_dist_, icp_min_correspondences_);
        RCLCPP_INFO(this->get_logger(), "Waiting for scan messages...");
    }

  private:
    // ---- Lookup and store initial TF transforms ----
    bool lookupAndStoreInitialTF(const geometry_msgs::msg::TransformStamped &tf_front_rear,
                                 const LaserScan::ConstSharedPtr &front_msg, const LaserScan::ConstSharedPtr &rear_msg)
    {
        tf_front_rear_init_ = tf_front_rear;
        try
        {
            tf_base_front_ =
                tf_buffer_->lookupTransform("base_footprint", front_msg->header.frame_id, front_msg->header.stamp,
                                            tf2::durationFromSec(transform_tolerance_));
            tf_base_rear_nominal_ =
                tf_buffer_->lookupTransform("base_footprint", rear_msg->header.frame_id, rear_msg->header.stamp,
                                            tf2::durationFromSec(transform_tolerance_));
        }
        catch (const tf2::TransformException &ex)
        {
            RCLCPP_WARN(this->get_logger(), "TF lookup (base_footprint) failed: %s", ex.what());
            return false;
        }
        initial_tf_stored_ = true;

        tf2::Quaternion q_init;
        tf2::fromMsg(tf_front_rear.transform.rotation, q_init);
        double r, p, y;
        tf2::Matrix3x3(q_init).getRPY(r, p, y);
        RCLCPP_INFO(this->get_logger(), "Initial TF (scan_front<-scan_rear): tx=%.4f ty=%.4f yaw=%.4f deg",
                    tf_front_rear.transform.translation.x, tf_front_rear.transform.translation.y, y * 180.0 / M_PI);
        return true;
    }

    // ---- Filter overlap region between front and rear scans ----
    void filterOverlapRegion(const PointCloud2D &front_local, const PointCloud2D &rear_in_front,
                             const geometry_msgs::msg::TransformStamped &tf_front_rear,
                             const LaserScan::ConstSharedPtr &front_msg, const LaserScan::ConstSharedPtr &rear_msg,
                             PointCloud2D &front_overlap_out, PointCloud2D &rear_overlap_out)
    {
        double tx_fr = tf_front_rear.transform.translation.x;
        double ty_fr = tf_front_rear.transform.translation.y;
        tf2::Quaternion q_fr;
        tf2::fromMsg(tf_front_rear.transform.rotation, q_fr);
        double roll_fr, pitch_fr, yaw_fr;
        tf2::Matrix3x3(q_fr).getRPY(roll_fr, pitch_fr, yaw_fr);
        double cos_yaw = std::cos(yaw_fr);
        double sin_yaw = std::sin(yaw_fr);

        // Filter front cloud: keep only points also visible to scan_rear
        front_overlap_out.reserve(front_local.size());
        for (const auto &pt : front_local)
        {
            double dx = pt.x() - tx_fr;
            double dy = pt.y() - ty_fr;
            double x_rear = cos_yaw * dx + sin_yaw * dy;
            double y_rear = -sin_yaw * dx + cos_yaw * dy;
            double angle = std::atan2(y_rear, x_rear);
            if (angle >= rear_msg->angle_min && angle <= rear_msg->angle_max)
            {
                front_overlap_out.push_back(pt);
            }
        }

        // Filter rear cloud (in front frame): keep only points visible to scan_front
        rear_overlap_out.reserve(rear_in_front.size());
        for (const auto &pt : rear_in_front)
        {
            double angle = std::atan2(pt.y(), pt.x());
            if (angle >= front_msg->angle_min && angle <= front_msg->angle_max)
            {
                rear_overlap_out.push_back(pt);
            }
        }
    }

    // ---- Collect a single scan sample ----
    bool collectSample(PointCloud2D &&front_ds, PointCloud2D &&rear_ds, size_t raw_front_size, size_t raw_rear_size)
    {
        if (static_cast<int>(front_ds.size()) < min_overlap_points_ ||
            static_cast<int>(rear_ds.size()) < min_overlap_points_)
        {
            RCLCPP_WARN(this->get_logger(), "Not enough overlap points: front=%zu, rear=%zu (need %d). Skipping.",
                        front_ds.size(), rear_ds.size(), min_overlap_points_);
            return false;
        }

        ScanSample sample;
        sample.front_cloud = std::move(front_ds);
        sample.rear_cloud = std::move(rear_ds);
        samples_.push_back(std::move(sample));

        RCLCPP_INFO(this->get_logger(),
                    "Sample %zu/%d collected (overlap: front=%zu rear=%zu, raw: front=%zu rear=%zu)", samples_.size(),
                    num_samples_, samples_.back().front_cloud.size(), samples_.back().rear_cloud.size(), raw_front_size,
                    raw_rear_size);
        return true;
    }

    // ---- Synchronized scan callback ----
    void syncCallback(const LaserScan::ConstSharedPtr &front_msg, const LaserScan::ConstSharedPtr &rear_msg)
    {
        if (calibration_done_)
        {
            return;
        }

        // Enforce sample interval
        auto now = this->now();
        if (last_sample_time_.nanoseconds() > 0)
        {
            double elapsed = (now - last_sample_time_).seconds();
            if (elapsed < sample_interval_)
            {
                return;
            }
        }

        // Lookup TF: scan_front <- scan_rear
        geometry_msgs::msg::TransformStamped tf_front_rear;
        try
        {
            tf_front_rear =
                tf_buffer_->lookupTransform(front_msg->header.frame_id, rear_msg->header.frame_id,
                                            front_msg->header.stamp, tf2::durationFromSec(transform_tolerance_));
        }
        catch (const tf2::TransformException &ex)
        {
            RCLCPP_WARN(this->get_logger(), "TF lookup (%s<-%s) failed: %s", front_msg->header.frame_id.c_str(),
                        rear_msg->header.frame_id.c_str(), ex.what());
            return;
        }

        // Store initial transforms once
        if (!initial_tf_stored_)
        {
            if (!lookupAndStoreInitialTF(tf_front_rear, front_msg, rear_msg))
            {
                return;
            }
        }

        // Optional average filter + convert to Cartesian
        std::vector<float> filtered_front;
        std::vector<float> filtered_rear;
        if (enable_average_filter_)
        {
            filtered_front = applyAverageFilter(*front_msg);
            filtered_rear = applyAverageFilter(*rear_msg);
        }

        PointCloud2D front_local = laserScanToCartesian(*front_msg, filtered_front, min_range_, max_range_);
        PointCloud2D rear_local = laserScanToCartesian(*rear_msg, filtered_rear, min_range_, max_range_);

        // Transform rear scan to scan_front frame
        PointCloud2D rear_in_front = transformToBaseFrame(rear_local, tf_front_rear);

        // Filter to overlap region only
        PointCloud2D front_overlap;
        PointCloud2D rear_overlap;
        filterOverlapRegion(front_local, rear_in_front, tf_front_rear, front_msg, rear_msg, front_overlap,
                            rear_overlap);

        // Downsample and collect sample
        PointCloud2D front_ds = downsampleCloud(front_overlap, downsample_stride_);
        PointCloud2D rear_ds = downsampleCloud(rear_overlap, downsample_stride_);

        if (collectSample(std::move(front_ds), std::move(rear_ds), front_local.size(), rear_in_front.size()))
        {
            last_sample_time_ = now;
        }

        // Check if enough samples
        if (static_cast<int>(samples_.size()) >= num_samples_)
        {
            calibration_done_ = true;
            runCalibration();
        }
    }

    // ---- Run ICP calibration on all collected samples ----
    void runCalibration()
    {
        RCLCPP_INFO(this->get_logger(), "All %d samples collected. Running ICP calibration (scan_front-centric)...",
                    num_samples_);

        ICPConfig icp_config;
        icp_config.max_iterations = icp_max_iterations_;
        icp_config.transform_epsilon = icp_transform_epsilon_;
        icp_config.max_correspondence_dist = icp_max_correspondence_dist_;
        icp_config.min_correspondences = icp_min_correspondences_;

        std::vector<double> dx_values;
        std::vector<double> dy_values;
        std::vector<double> dyaw_values;
        std::vector<double> mean_dist_values;
        int successful = 0;

        for (int i = 0; i < static_cast<int>(samples_.size()); ++i)
        {
            // ICP: align rear_cloud (source) to front_cloud (target)
            // Both are in scan_front frame (rear via initial TF)
            CalibrationResult res = alignSVD_ICP(samples_[i].rear_cloud,  // source (copy, gets modified internally)
                                                 samples_[i].front_cloud, // target (reference)
                                                 icp_config);

            if (!res.converged || res.num_correspondences < icp_min_correspondences_)
            {
                RCLCPP_WARN(this->get_logger(), "Sample %d: ICP %s (corr: %d, dist: %.4f)", i + 1,
                            res.converged ? "too few correspondences" : "did not converge", res.num_correspondences,
                            res.mean_correspondence_distance);
                continue;
            }

            dx_values.push_back(res.dx);
            dy_values.push_back(res.dy);
            dyaw_values.push_back(res.dyaw);
            mean_dist_values.push_back(res.mean_correspondence_distance);
            successful++;

            RCLCPP_INFO(this->get_logger(), "Sample %d: dx=%.4f dy=%.4f dyaw=%.4f deg dist=%.4f (%d corr)", i + 1,
                        res.dx, res.dy, res.dyaw * 180.0 / M_PI, res.mean_correspondence_distance,
                        res.num_correspondences);
        }

        if (successful == 0)
        {
            RCLCPP_ERROR(this->get_logger(), "No successful ICP alignments! Cannot compute calibration.");
            rclcpp::shutdown();
            return;
        }

        // ---- Median ICP corrections ----
        double med_dx = computeMedian(dx_values);
        double med_dy = computeMedian(dy_values);
        double med_dyaw = computeMedian(dyaw_values);
        double med_dist = computeMedian(mean_dist_values);

        // ---- Extract initial TF components (scan_front <- scan_rear) ----
        double tx_init = tf_front_rear_init_.transform.translation.x;
        double ty_init = tf_front_rear_init_.transform.translation.y;
        tf2::Quaternion q_init;
        tf2::fromMsg(tf_front_rear_init_.transform.rotation, q_init);
        double r_init, p_init, yaw_init;
        tf2::Matrix3x3(q_init).getRPY(r_init, p_init, yaw_init);

        // ---- Compute corrected T_front_rear ----
        // T_corrected = T_correction * T_init
        // where T_correction = {med_dx, med_dy, med_dyaw}
        double corrected_fr_yaw = yaw_init + med_dyaw;
        double corrected_fr_tx = tx_init * std::cos(med_dyaw) - ty_init * std::sin(med_dyaw) + med_dx;
        double corrected_fr_ty = tx_init * std::sin(med_dyaw) + ty_init * std::cos(med_dyaw) + med_dy;

        // ---- Extract T_base_front components ----
        double tx_bf = tf_base_front_.transform.translation.x;
        double ty_bf = tf_base_front_.transform.translation.y;
        tf2::Quaternion q_bf;
        tf2::fromMsg(tf_base_front_.transform.rotation, q_bf);
        double r_bf, p_bf, yaw_bf;
        tf2::Matrix3x3(q_bf).getRPY(r_bf, p_bf, yaw_bf);

        // ---- Compute T_base_rear_corrected = T_base_front * T_front_rear_corrected ----
        double corrected_br_yaw = yaw_bf + corrected_fr_yaw;
        double corrected_br_tx = tx_bf + std::cos(yaw_bf) * corrected_fr_tx - std::sin(yaw_bf) * corrected_fr_ty;
        double corrected_br_ty = ty_bf + std::sin(yaw_bf) * corrected_fr_tx + std::cos(yaw_bf) * corrected_fr_ty;

        // ---- Extract nominal T_base_rear ----
        double tx_nom = tf_base_rear_nominal_.transform.translation.x;
        double ty_nom = tf_base_rear_nominal_.transform.translation.y;
        tf2::Quaternion q_nom;
        tf2::fromMsg(tf_base_rear_nominal_.transform.rotation, q_nom);
        double r_nom, p_nom, yaw_nom;
        tf2::Matrix3x3(q_nom).getRPY(r_nom, p_nom, yaw_nom);
        double nominal_z = tf_base_rear_nominal_.transform.translation.z;

        // ---- Compute integrator offsets ----
        // Integrator applies: P_base = R(yaw_tf + laserYaw) * P_local + (tx_tf + XOff, ty_tf + YOff)
        // So offset = corrected_base_rear - nominal_base_rear
        double laser2Yaw = corrected_br_yaw - yaw_nom;
        double laser2XOff = corrected_br_tx - tx_nom;
        double laser2YOff = corrected_br_ty - ty_nom;

        // ---- Symmetry analysis (base_link frame) ----
        SymmetryResult sym =
            computeSymmetryAnalysis(tx_bf, ty_bf, yaw_bf, corrected_br_tx, corrected_br_ty, corrected_br_yaw);

        // ---- Format output strings ----
        std::ostringstream current_xyz_ss;
        current_xyz_ss << std::fixed << std::setprecision(4) << tx_nom << " " << ty_nom << " " << nominal_z;
        std::string current_xyz = current_xyz_ss.str();

        std::ostringstream corrected_xyz_ss;
        corrected_xyz_ss << std::fixed << std::setprecision(4) << corrected_br_tx << " " << corrected_br_ty << " "
                         << nominal_z;
        std::string corrected_xyz_str = corrected_xyz_ss.str();

        std::ostringstream current_rpy_ss;
        current_rpy_ss << std::fixed << std::setprecision(11) << "0.0 0.0 " << yaw_nom;
        std::string current_rpy = current_rpy_ss.str();

        std::ostringstream corrected_rpy_ss;
        corrected_rpy_ss << std::fixed << std::setprecision(11) << "0.0 0.0 " << corrected_br_yaw;
        std::string corrected_rpy = corrected_rpy_ss.str();

        double dyaw_deg = med_dyaw * 180.0 / M_PI;

        // ---- Print results to terminal ----
        RCLCPP_INFO(this->get_logger(),
                    "\n"
                    "=== 2D LiDAR Calibration Results ===\n"
                    "Method: scan_front-centric ICP alignment\n"
                    "Samples collected: %d/%d\n"
                    "Successful ICP alignments: %d/%d\n"
                    "Median correspondence distance: %.4f m\n"
                    "Average filter: %s\n"
                    "\n"
                    "--- ICP correction (in scan_front frame) ---\n"
                    "  dx:   %+.6f m\n"
                    "  dy:   %+.6f m\n"
                    "  dyaw: %+.6f rad (%+.4f deg)\n"
                    "\n"
                    "--- Corrected T_front_rear ---\n"
                    "  tx: %.6f  ty: %.6f  yaw: %.6f rad\n"
                    "  (Initial: tx=%.6f ty=%.6f yaw=%.6f rad)\n"
                    "\n"
                    "--- laser_scan_integrator offset params ---\n"
                    "  (Apply these to integrate_2_scan.launch.py)\n"
                    "  laser2XOff: %.6f\n"
                    "  laser2YOff: %.6f\n"
                    "  laser2Yaw:  %.6f\n"
                    "\n"
                    "--- Corrected URDF joint values for scan2_joint ---\n"
                    "  Current:   xyz=\"%s\" rpy=\"%s\"\n"
                    "  Corrected: xyz=\"%s\" rpy=\"%s\"\n"
                    "\n"
                    "--- How to apply ---\n"
                    "  Option 1 (Recommended): Update laser_scan_integrator launch params\n"
                    "    Edit: src/Sensor/Lidar/2D/laser_scan_integrator/launch/integrate_2_scan.launch.py\n"
                    "    Set: laser2XOff=%.6f, laser2YOff=%.6f, laser2Yaw=%.6f\n"
                    "\n"
                    "  Option 2: Update URDF (more permanent)\n"
                    "    Edit: src/TF/tr_description/urdf/amr.urdf\n"
                    "    Change scan2_joint origin to corrected values above\n"
                    "    Then set integrator offsets back to 0.0\n",
                    static_cast<int>(samples_.size()), num_samples_, successful, num_samples_, med_dist,
                    enable_average_filter_ ? "ENABLED" : "DISABLED", med_dx, med_dy, med_dyaw, dyaw_deg,
                    corrected_fr_tx, corrected_fr_ty, corrected_fr_yaw, tx_init, ty_init, yaw_init, laser2XOff,
                    laser2YOff, laser2Yaw, current_xyz.c_str(), current_rpy.c_str(), corrected_xyz_str.c_str(),
                    corrected_rpy.c_str(), laser2XOff, laser2YOff, laser2Yaw);

        // ---- Symmetry analysis report ----
        RCLCPP_INFO(this->get_logger(),
                    "\n"
                    "--- Symmetry Analysis (base_link frame) ---\n"
                    "  Front:          tx=%+.4f  ty=%+.4f  yaw=%+.2f deg\n"
                    "  Rear corrected: tx=%+.4f  ty=%+.4f  yaw=%+.2f deg\n"
                    "  Ideal rear:     tx=%+.4f  ty=%+.4f  yaw=%+.2f deg\n"
                    "  Asymmetry:      dtx=%.4f m  dty=%.4f m  dyaw=%.3f deg\n"
                    "  Status: %s\n"
                    "  (Threshold: pos < 2mm, yaw < 0.5 deg)\n",
                    tx_bf, ty_bf, yaw_bf * 180.0 / M_PI, corrected_br_tx, corrected_br_ty,
                    corrected_br_yaw * 180.0 / M_PI, sym.ideal_rear_tx, sym.ideal_rear_ty,
                    sym.ideal_rear_yaw * 180.0 / M_PI, sym.delta_tx, sym.delta_ty, sym.delta_yaw * 180.0 / M_PI,
                    sym.is_symmetric ? "SYMMETRIC" : "NOT SYMMETRIC");

        // ---- Write YAML output ----
        writeYamlOutput(med_dx, med_dy, med_dyaw, dyaw_deg, med_dist, successful, laser2XOff, laser2YOff, laser2Yaw,
                        corrected_xyz_str, corrected_rpy, corrected_fr_tx, corrected_fr_ty, corrected_fr_yaw, tx_init,
                        ty_init, yaw_init, sym);

        // ---- Broadcast corrected TF for verification ----
        if (broadcast_corrected_tf_)
        {
            broadcastCorrectedTF(corrected_br_tx, corrected_br_ty, nominal_z, corrected_br_yaw);
        }
        else
        {
            RCLCPP_INFO(this->get_logger(), "TF broadcast disabled. Shutting down.");
            rclcpp::shutdown();
        }
    }

    // ---- Compute median of a vector ----
    static double computeMedian(std::vector<double> &values)
    {
        if (values.empty())
        {
            return 0.0;
        }
        std::sort(values.begin(), values.end());
        size_t n = values.size();
        if (n % 2 == 0)
        {
            return (values[n / 2 - 1] + values[n / 2]) / 2.0;
        }
        return values[n / 2];
    }

    // ---- Symmetry analysis ----
    SymmetryResult computeSymmetryAnalysis(double front_tx, double front_ty, double front_yaw, double rear_tx,
                                           double rear_ty, double rear_yaw) const
    {
        SymmetryResult result;

        // Ideal symmetric rear about base_link origin:
        //   ideal_rear = (-front.tx, -front.ty, front.yaw + pi)
        result.ideal_rear_tx = -front_tx;
        result.ideal_rear_ty = -front_ty;
        result.ideal_rear_yaw = normalizeAngle(front_yaw + M_PI);

        result.delta_tx = std::abs(rear_tx - result.ideal_rear_tx);
        result.delta_ty = std::abs(rear_ty - result.ideal_rear_ty);
        result.delta_yaw = std::abs(normalizeAngle(rear_yaw - result.ideal_rear_yaw));

        // Thresholds: 2mm position, 0.5 degree yaw
        const double threshold_pos = 0.002;
        const double threshold_yaw = 0.5 * M_PI / 180.0;
        result.is_symmetric =
            (result.delta_tx < threshold_pos && result.delta_ty < threshold_pos && result.delta_yaw < threshold_yaw);

        return result;
    }

    // ---- Write YAML calibration results ----
    void writeYamlOutput(double dx, double dy, double dyaw_rad, double dyaw_deg, double median_dist,
                         int successful_alignments, double laser2XOff, double laser2YOff, double laser2Yaw,
                         const std::string &corrected_xyz, const std::string &corrected_rpy, double corrected_fr_tx,
                         double corrected_fr_ty, double corrected_fr_yaw, double initial_fr_tx, double initial_fr_ty,
                         double initial_fr_yaw, const SymmetryResult &sym)
    {
        // Determine output path
        std::string output_path;
        if (output_dir_.empty())
        {
            output_path = output_file_;
        }
        else
        {
            if (output_dir_.back() != '/')
            {
                output_path = output_dir_ + "/" + output_file_;
            }
            else
            {
                output_path = output_dir_ + output_file_;
            }
        }

        // Create directory if needed
        std::filesystem::path filepath(output_path);
        if (filepath.has_parent_path())
        {
            std::filesystem::create_directories(filepath.parent_path());
        }

        std::ofstream ofs(output_path);
        if (!ofs.is_open())
        {
            RCLCPP_ERROR(this->get_logger(), "Failed to open output file: %s", output_path.c_str());
            return;
        }

        // Get current timestamp
        auto now = std::chrono::system_clock::now();
        auto time_t_now = std::chrono::system_clock::to_time_t(now);
        std::tm tm_now{};
        localtime_r(&time_t_now, &tm_now);
        char time_buf[64];
        std::strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", &tm_now);

        ofs << std::fixed;
        ofs << "# Auto-generated by lidar_calibration_2d\n";
        ofs << "# Generated: " << time_buf << "\n";
        ofs << "# Method: scan_front-centric ICP alignment\n";
        ofs << "calibration:\n";
        ofs << "  reference_sensor: \"" << scan_topic_front_ << "\"\n";
        ofs << "  calibrated_sensor: \"" << scan_topic_rear_ << "\"\n";
        ofs << "  icp_correction:\n";
        ofs << "    dx: " << std::setprecision(6) << dx << "\n";
        ofs << "    dy: " << std::setprecision(6) << dy << "\n";
        ofs << "    dyaw_rad: " << std::setprecision(6) << dyaw_rad << "\n";
        ofs << "    dyaw_deg: " << std::setprecision(2) << dyaw_deg << "\n";
        ofs << "  corrected_front_rear_tf:\n";
        ofs << "    tx: " << std::setprecision(6) << corrected_fr_tx << "\n";
        ofs << "    ty: " << std::setprecision(6) << corrected_fr_ty << "\n";
        ofs << "    yaw_rad: " << std::setprecision(6) << corrected_fr_yaw << "\n";
        ofs << "  initial_front_rear_tf:\n";
        ofs << "    tx: " << std::setprecision(6) << initial_fr_tx << "\n";
        ofs << "    ty: " << std::setprecision(6) << initial_fr_ty << "\n";
        ofs << "    yaw_rad: " << std::setprecision(6) << initial_fr_yaw << "\n";
        ofs << "  statistics:\n";
        ofs << "    num_samples: " << num_samples_ << "\n";
        ofs << "    successful_alignments: " << successful_alignments << "\n";
        ofs << "    median_correspondence_distance: " << std::setprecision(4) << median_dist << "\n";
        ofs << "    average_filter_enabled: " << (enable_average_filter_ ? "true" : "false") << "\n";
        ofs << "    downsample_stride: " << downsample_stride_ << "\n";
        ofs << "  integrator_params:\n";
        ofs << "    laser2XOff: " << std::setprecision(6) << laser2XOff << "\n";
        ofs << "    laser2YOff: " << std::setprecision(6) << laser2YOff << "\n";
        ofs << "    laser2Yaw: " << std::setprecision(6) << laser2Yaw << "\n";
        ofs << "  corrected_urdf:\n";
        ofs << "    scan2_joint_xyz: \"" << corrected_xyz << "\"\n";
        ofs << "    scan2_joint_rpy: \"" << corrected_rpy << "\"\n";
        ofs << "  symmetry_analysis:\n";
        ofs << "    ideal_rear_tx: " << std::setprecision(6) << sym.ideal_rear_tx << "\n";
        ofs << "    ideal_rear_ty: " << std::setprecision(6) << sym.ideal_rear_ty << "\n";
        ofs << "    ideal_rear_yaw_rad: " << std::setprecision(6) << sym.ideal_rear_yaw << "\n";
        ofs << "    ideal_rear_yaw_deg: " << std::setprecision(2) << sym.ideal_rear_yaw * 180.0 / M_PI << "\n";
        ofs << "    delta_tx: " << std::setprecision(6) << sym.delta_tx << "\n";
        ofs << "    delta_ty: " << std::setprecision(6) << sym.delta_ty << "\n";
        ofs << "    delta_yaw_rad: " << std::setprecision(6) << sym.delta_yaw << "\n";
        ofs << "    delta_yaw_deg: " << std::setprecision(3) << sym.delta_yaw * 180.0 / M_PI << "\n";
        ofs << "    is_symmetric: " << (sym.is_symmetric ? "true" : "false") << "\n";
        ofs << "    threshold_pos_m: 0.002\n";
        ofs << "    threshold_yaw_deg: 0.5\n";
        ofs << "  verification:\n";
        ofs << "    corrected_tf_frame: \"scan_rear_calibrated\"\n";
        ofs << "    broadcast_duration_s: " << std::setprecision(1) << tf_broadcast_duration_ << "\n";

        ofs.close();

        RCLCPP_INFO(this->get_logger(), "Results saved to: %s", output_path.c_str());
    }

    // ---- Broadcast corrected TF for RViz verification ----
    void broadcastCorrectedTF(double corrected_tx, double corrected_ty, double corrected_z, double corrected_yaw)
    {
        geometry_msgs::msg::TransformStamped corrected_tf;
        corrected_tf.header.stamp = this->now();
        corrected_tf.header.frame_id = "base_footprint";
        corrected_tf.child_frame_id = "scan_rear_calibrated";
        corrected_tf.transform.translation.x = corrected_tx;
        corrected_tf.transform.translation.y = corrected_ty;
        corrected_tf.transform.translation.z = corrected_z;

        tf2::Quaternion q;
        q.setRPY(0.0, 0.0, corrected_yaw);
        corrected_tf.transform.rotation = tf2::toMsg(q);

        // Broadcast static TF
        static_broadcaster_ = std::make_shared<tf2_ros::StaticTransformBroadcaster>(this);
        static_broadcaster_->sendTransform(corrected_tf);

        RCLCPP_INFO(this->get_logger(),
                    "\n--- Verification ---\n"
                    "  Broadcasting corrected TF as 'scan_rear_calibrated' for %.0f s.\n"
                    "  Open RViz and compare scan_rear vs scan_rear_calibrated frames.",
                    tf_broadcast_duration_);

        // Create wall timer to shutdown after broadcast duration
        shutdown_timer_ = this->create_wall_timer(std::chrono::duration<double>(tf_broadcast_duration_), [this]() {
            RCLCPP_INFO(this->get_logger(), "TF broadcast duration elapsed. Shutting down.");
            rclcpp::shutdown();
        });
    }

    // ---- Data structures ----
    struct ScanSample
    {
        PointCloud2D front_cloud; // Front points in scan_front local frame
        PointCloud2D rear_cloud;  // Rear points in scan_front frame (via initial TF)
    };

    // ---- Parameters ----
    std::string scan_topic_front_;
    std::string scan_topic_rear_;
    bool enable_average_filter_{true};
    int num_samples_{30};
    double sample_interval_{0.1};
    double min_range_{0.5};
    double max_range_{8.0};
    int min_overlap_points_{50};
    int downsample_stride_{10};
    int icp_max_iterations_{50};
    double icp_transform_epsilon_{1e-6};
    double icp_max_correspondence_dist_{0.5};
    int icp_min_correspondences_{30};
    bool broadcast_corrected_tf_{true};
    double tf_broadcast_duration_{30.0};
    std::string output_file_;
    std::string output_dir_;
    double transform_tolerance_{0.1};

    // ---- TF2 ----
    std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
    std::unique_ptr<tf2_ros::TransformListener> tf_listener_;
    std::shared_ptr<tf2_ros::StaticTransformBroadcaster> static_broadcaster_;

    // ---- message_filters ----
    message_filters::Subscriber<LaserScan> sub_front_;
    message_filters::Subscriber<LaserScan> sub_rear_;
    std::shared_ptr<message_filters::Synchronizer<SyncPolicy>> sync_;

    // ---- Calibration state ----
    std::vector<ScanSample> samples_;
    rclcpp::Time last_sample_time_{0, 0, RCL_ROS_TIME};
    bool calibration_done_{false};
    bool initial_tf_stored_{false};
    geometry_msgs::msg::TransformStamped tf_front_rear_init_;
    geometry_msgs::msg::TransformStamped tf_base_front_;
    geometry_msgs::msg::TransformStamped tf_base_rear_nominal_;

    // ---- Timers ----
    rclcpp::TimerBase::SharedPtr shutdown_timer_;
};

} // namespace lidar_calibration_2d

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);

    rclcpp::NodeOptions options;
    options.automatically_declare_parameters_from_overrides(true);

    auto node = std::make_shared<lidar_calibration_2d::CalibrationNode>(options);

    rclcpp::spin(node);
    if (rclcpp::ok())
    {
        rclcpp::shutdown();
    }
    return 0;
}
