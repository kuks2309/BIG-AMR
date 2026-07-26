#ifndef AMR_MOTION_CORE__MATH_UTILS_HPP_
#define AMR_MOTION_CORE__MATH_UTILS_HPP_

#include <cmath>

namespace trnav_motion_core
{

// Normalize angle to [-π, π]. NaN-safe (returns NaN) — does not hang on extreme inputs.
// Note: std::remainder uses round-half-even tie-break, so std::remainder(π, 2π) returns +π
// (and -π for -π input); it does NOT collapse ±π to a single sign. Callers needing a
// deterministic direction at the ±π boundary must handle the tie-break themselves.
inline double normalizeAngle(double angle)
{
    return std::remainder(angle, 2.0 * M_PI);
}

// Normalize angle (deg) to [-180, +180]. NaN-safe.
inline double normalizeAngleDeg(double deg)
{
    return std::remainder(deg, 360.0);
}

} // namespace trnav_motion_core

#endif // AMR_MOTION_CORE__MATH_UTILS_HPP_
