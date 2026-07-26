#ifndef LIDAR_CALIBRATION_2D__SVD_ALIGNER_HPP_
#define LIDAR_CALIBRATION_2D__SVD_ALIGNER_HPP_

#include <Eigen/Core>
#include <Eigen/LU>
#include <Eigen/SVD>

#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <vector>

namespace lidar_calibration_2d
{

using Point2D = Eigen::Vector2d;
using PointCloud2D = std::vector<Point2D>;

struct CalibrationResult
{
    double dx = 0.0;
    double dy = 0.0;
    double dyaw = 0.0;
    double mean_correspondence_distance = std::numeric_limits<double>::max();
    int num_correspondences = 0;
    bool converged = false;
};

struct ICPConfig
{
    int max_iterations = 50;
    double transform_epsilon = 1e-6;
    double max_correspondence_dist = 0.3;
    int min_correspondences = 30;
};

/// Compute 2D rigid-body transform (R, t) that best aligns source points to target points
/// using SVD decomposition on the cross-covariance matrix.
///
/// Given N pairs (p_i, q_i):
///   1. Compute centroids p_bar, q_bar
///   2. Center points: p_i' = p_i - p_bar, q_i' = q_i - q_bar
///   3. Build 2x2 cross-covariance: H = sum(p_i' * q_i'^T)
///   4. SVD: H = U * S * V^T
///   5. R = V * U^T (correct for reflection if det < 0)
///   6. t = q_bar - R * p_bar
///
/// @param source  Source points (to be aligned)
/// @param target  Target points (reference)
/// @param R_out   Output 2x2 rotation matrix
/// @param t_out   Output 2x1 translation vector
/// @return        true if successful (enough points), false otherwise
inline bool computeSVDTransform2D(const std::vector<std::pair<Point2D, Point2D>> &correspondences,
                                  Eigen::Matrix2d &R_out, Eigen::Vector2d &t_out)
{
    const int n = static_cast<int>(correspondences.size());
    if (n < 3)
    {
        return false;
    }

    // Step 1: Compute centroids
    Point2D p_bar = Point2D::Zero();
    Point2D q_bar = Point2D::Zero();
    for (const auto &[p, q] : correspondences)
    {
        p_bar += p;
        q_bar += q;
    }
    p_bar /= static_cast<double>(n);
    q_bar /= static_cast<double>(n);

    // Step 2-3: Build cross-covariance matrix H
    Eigen::Matrix2d H = Eigen::Matrix2d::Zero();
    for (const auto &[p, q] : correspondences)
    {
        Point2D p_centered = p - p_bar;
        Point2D q_centered = q - q_bar;
        H += p_centered * q_centered.transpose();
    }

    // Step 4: SVD decomposition
    Eigen::JacobiSVD<Eigen::Matrix2d> svd(H, Eigen::ComputeFullU | Eigen::ComputeFullV);
    Eigen::Matrix2d U = svd.matrixU();
    Eigen::Matrix2d V = svd.matrixV();

    // Step 5: Compute rotation (correct for reflection)
    R_out = V * U.transpose();
    if (R_out.determinant() < 0)
    {
        V.col(1) *= -1.0;
        R_out = V * U.transpose();
    }

    // Step 6: Compute translation
    t_out = q_bar - R_out * p_bar;

    return true;
}

/// Run 2D ICP alignment using SVD for transform estimation.
///
/// This implements a custom 2D ICP loop:
///   1. Start with source and target point clouds (both in base_footprint)
///   2. For each iteration:
///      a. Find nearest-neighbor correspondences (brute force)
///      b. Filter by max_correspondence_dist
///      c. Estimate transform using SVD
///      d. Apply incremental transform to source
///      e. Check convergence
///   3. Return cumulative transform as CalibrationResult
///
/// @param source  Source point cloud (rear scan in base_footprint)
/// @param target  Target point cloud (front scan in base_footprint)
/// @param config  ICP configuration parameters
/// @return        CalibrationResult with dx, dy, dyaw
inline CalibrationResult alignSVD_ICP(PointCloud2D source, const PointCloud2D &target, const ICPConfig &config)
{
    CalibrationResult result;

    if (source.empty() || target.empty())
    {
        return result;
    }

    // Cumulative transform
    Eigen::Matrix2d R_total = Eigen::Matrix2d::Identity();
    Eigen::Vector2d t_total = Eigen::Vector2d::Zero();

    double thresh_sq = config.max_correspondence_dist * config.max_correspondence_dist;

    for (int iter = 0; iter < config.max_iterations; ++iter)
    {
        // Step a: Find nearest-neighbor correspondences (brute force O(n*m)).
        // Note: Intentionally brute-force — after overlap filtering and downsampling,
        // point counts are typically ~165 pts per cloud, so KD-tree overhead is unnecessary.
        // Total: 50 iters * 165 * 165 ≈ 1.3M distance calcs per sample — fast enough.
        std::vector<std::pair<Point2D, Point2D>> correspondences;
        correspondences.reserve(source.size());

        double total_dist = 0.0;

        for (const auto &src_pt : source)
        {
            double best_dist_sq = std::numeric_limits<double>::max();
            const Point2D *best_target = nullptr;

            for (const auto &tgt_pt : target)
            {
                double dist_sq = (src_pt - tgt_pt).squaredNorm();
                if (dist_sq < best_dist_sq)
                {
                    best_dist_sq = dist_sq;
                    best_target = &tgt_pt;
                }
            }

            // Step b: Filter by max correspondence distance
            if (best_target != nullptr && best_dist_sq < thresh_sq)
            {
                correspondences.emplace_back(src_pt, *best_target);
                total_dist += std::sqrt(best_dist_sq);
            }
        }

        // Step c: Check minimum correspondences
        if (static_cast<int>(correspondences.size()) < config.min_correspondences)
        {
            result.num_correspondences = static_cast<int>(correspondences.size());
            return result; // Not enough correspondences, return unconverged
        }

        result.mean_correspondence_distance = total_dist / static_cast<double>(correspondences.size());
        result.num_correspondences = static_cast<int>(correspondences.size());

        // Step d: Estimate transform using SVD
        Eigen::Matrix2d R_inc;
        Eigen::Vector2d t_inc;
        if (!computeSVDTransform2D(correspondences, R_inc, t_inc))
        {
            return result;
        }

        // Step e: Apply incremental transform to source points
        for (auto &pt : source)
        {
            pt = R_inc * pt + t_inc;
        }

        // Accumulate: T_total = T_inc * T_prev
        // R_total_new = R_inc * R_total_prev
        // t_total_new = R_inc * t_total_prev + t_inc
        Eigen::Vector2d t_new = R_inc * t_total + t_inc;
        R_total = R_inc * R_total;
        t_total = t_new;

        // Step f: Check convergence
        double translation_delta = t_inc.norm();
        double rotation_delta = std::abs(std::atan2(R_inc(1, 0), R_inc(0, 0)));

        if (translation_delta < config.transform_epsilon && rotation_delta < config.transform_epsilon)
        {
            result.converged = true;
            break;
        }
    }

    // Extract 2D parameters from cumulative transform
    result.dyaw = std::atan2(R_total(1, 0), R_total(0, 0));
    result.dx = t_total.x();
    result.dy = t_total.y();

    // If we exhausted iterations but got close, still mark as converged
    if (!result.converged && result.mean_correspondence_distance < 0.05)
    {
        result.converged = true;
    }

    return result;
}

} // namespace lidar_calibration_2d

#endif // LIDAR_CALIBRATION_2D__SVD_ALIGNER_HPP_
