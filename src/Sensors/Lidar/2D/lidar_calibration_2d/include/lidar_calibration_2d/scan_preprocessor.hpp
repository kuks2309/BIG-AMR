#ifndef LIDAR_CALIBRATION_2D__SCAN_PREPROCESSOR_HPP_
#define LIDAR_CALIBRATION_2D__SCAN_PREPROCESSOR_HPP_

#include <cmath>
#include <sensor_msgs/msg/laser_scan.hpp>
#include <vector>

namespace lidar_calibration_2d
{

/// Apply 3-point moving average to smooth LaserScan ranges.
/// Invalid ranges (inf, nan, out of bounds) are excluded from the average.
/// The filter is applied on a COPY of the ranges vector -- input is not modified.
///
/// @param scan  Input LaserScan (not modified)
/// @return      New ranges vector with smoothed values
inline std::vector<float> applyAverageFilter(const sensor_msgs::msg::LaserScan &scan)
{
    const auto &ranges = scan.ranges;
    const size_t n = ranges.size();
    std::vector<float> smoothed(n);

    for (size_t i = 0; i < n; ++i)
    {
        float sum = 0.0f;
        int count = 0;

        // Look at i-1, i, i+1
        for (int k = -1; k <= 1; ++k)
        {
            int idx = static_cast<int>(i) + k;
            if (idx < 0 || idx >= static_cast<int>(n))
                continue;
            float r = ranges[idx];
            if (std::isfinite(r) && r >= scan.range_min && r <= scan.range_max)
            {
                sum += r;
                count++;
            }
        }

        if (count > 0)
        {
            smoothed[i] = sum / static_cast<float>(count);
        }
        else
        {
            smoothed[i] = ranges[i]; // keep original if no valid neighbors
        }
    }

    return smoothed;
}

} // namespace lidar_calibration_2d

#endif // LIDAR_CALIBRATION_2D__SCAN_PREPROCESSOR_HPP_
