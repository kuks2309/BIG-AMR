#ifndef LIDAR_CALIBRATION_2D__SCAN_UTILS_HPP_
#define LIDAR_CALIBRATION_2D__SCAN_UTILS_HPP_

#include <geometry_msgs/msg/transform_stamped.hpp>
#include <sensor_msgs/msg/laser_scan.hpp>
#include <tf2/utils.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

#include <Eigen/Core>
#include <cmath>
#include <limits>
#include <utility>
#include <vector>

namespace lidar_calibration_2d
{

using Point2D = Eigen::Vector2d;
using PointCloud2D = std::vector<Point2D>;
using CorrespondencePair = std::pair<Point2D, Point2D>; // (source/rear, target/front)
using CorrespondenceSet = std::vector<CorrespondencePair>;

/// Convert LaserScan ranges to 2D Cartesian points in the sensor-local frame.
/// Optionally uses pre-filtered (smoothed) ranges instead of raw scan ranges.
///
/// @param scan             Input LaserScan message
/// @param filtered_ranges  Optional pre-filtered ranges (if empty, uses scan.ranges)
/// @param min_range        Minimum valid range (meters)
/// @param max_range        Maximum valid range (meters)
/// @return                 PointCloud2D in sensor-local frame
inline PointCloud2D laserScanToCartesian(const sensor_msgs::msg::LaserScan &scan,
                                         const std::vector<float> &filtered_ranges, double min_range, double max_range)
{
    const auto &ranges = filtered_ranges.empty() ? scan.ranges : filtered_ranges;
    PointCloud2D cloud;
    cloud.reserve(ranges.size());

    for (size_t i = 0; i < ranges.size(); ++i)
    {
        float r = ranges[i];
        if (!std::isfinite(r) || r < min_range || r > max_range)
        {
            continue;
        }
        double angle = scan.angle_min + static_cast<double>(i) * scan.angle_increment;
        cloud.emplace_back(r * std::cos(angle), r * std::sin(angle));
    }

    return cloud;
}

/// Transform a 2D point cloud from sensor-local frame to base frame using a TF transform.
/// Extracts the 2D translation (tx, ty) and yaw from the 3D transform.
///
/// @param cloud      Input point cloud in sensor-local frame
/// @param transform  TF2 transform from base_frame to sensor_frame
/// @return           Point cloud in base frame
inline PointCloud2D transformToBaseFrame(const PointCloud2D &cloud,
                                         const geometry_msgs::msg::TransformStamped &transform)
{
    double tx = transform.transform.translation.x;
    double ty = transform.transform.translation.y;

    // Extract yaw from quaternion
    tf2::Quaternion q;
    tf2::fromMsg(transform.transform.rotation, q);
    double roll, pitch, yaw;
    tf2::Matrix3x3(q).getRPY(roll, pitch, yaw);

    double cos_yaw = std::cos(yaw);
    double sin_yaw = std::sin(yaw);

    PointCloud2D transformed;
    transformed.reserve(cloud.size());

    for (const auto &pt : cloud)
    {
        double x_base = pt.x() * cos_yaw - pt.y() * sin_yaw + tx;
        double y_base = pt.x() * sin_yaw + pt.y() * cos_yaw + ty;
        transformed.emplace_back(x_base, y_base);
    }

    return transformed;
}

/// Find spatial correspondences between two point clouds using nearest-neighbor matching.
/// Both clouds must be in the same frame (e.g., base_footprint).
///
/// For each point in the source (rear) cloud, find the nearest point in the target (front) cloud.
/// Only keep pairs where the distance is below the correspondence_threshold.
///
/// @param source                  Rear scan points in base frame
/// @param target                  Front scan points in base frame
/// @param correspondence_threshold  Max distance for a valid correspondence (meters)
/// @param min_range_from_origin   Min distance from origin to include (filters robot body)
/// @param max_range_from_origin   Max distance from origin to include
/// @return                        Set of correspondence pairs (source_pt, target_pt)
inline CorrespondenceSet findSpatialCorrespondences(const PointCloud2D &source, const PointCloud2D &target,
                                                    double correspondence_threshold, double min_range_from_origin,
                                                    double max_range_from_origin)
{
    CorrespondenceSet correspondences;
    double thresh_sq = correspondence_threshold * correspondence_threshold;
    double min_r_sq = min_range_from_origin * min_range_from_origin;
    double max_r_sq = max_range_from_origin * max_range_from_origin;

    for (const auto &src_pt : source)
    {
        // Distance from origin filter
        double src_dist_sq = src_pt.squaredNorm();
        if (src_dist_sq < min_r_sq || src_dist_sq > max_r_sq)
        {
            continue;
        }

        // Brute-force nearest-neighbor search in target (O(n*m)).
        // Intentional: point clouds are small (~165 pts) after overlap filter + downsample.
        double best_dist_sq = std::numeric_limits<double>::max();
        const Point2D *best_target = nullptr;

        for (const auto &tgt_pt : target)
        {
            double tgt_dist_sq = tgt_pt.squaredNorm();
            if (tgt_dist_sq < min_r_sq || tgt_dist_sq > max_r_sq)
            {
                continue;
            }

            double dist_sq = (src_pt - tgt_pt).squaredNorm();
            if (dist_sq < best_dist_sq)
            {
                best_dist_sq = dist_sq;
                best_target = &tgt_pt;
            }
        }

        if (best_target != nullptr && best_dist_sq < thresh_sq)
        {
            correspondences.emplace_back(src_pt, *best_target);
        }
    }

    return correspondences;
}

/// Downsample a 2D point cloud by taking every N-th point (stride-based).
///
/// @param cloud   Input point cloud
/// @param stride  Take every stride-th point (1 = no downsampling)
/// @return        Downsampled point cloud
inline PointCloud2D downsampleCloud(const PointCloud2D &cloud, int stride)
{
    if (stride <= 1)
    {
        return cloud;
    }
    PointCloud2D result;
    result.reserve(cloud.size() / static_cast<size_t>(stride) + 1);
    for (size_t i = 0; i < cloud.size(); i += static_cast<size_t>(stride))
    {
        result.push_back(cloud[i]);
    }
    return result;
}

} // namespace lidar_calibration_2d

#endif // LIDAR_CALIBRATION_2D__SCAN_UTILS_HPP_
