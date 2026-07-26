#ifndef AMR_MOTION_CORE__ROBOT_GEOMETRY_HPP_
#define AMR_MOTION_CORE__ROBOT_GEOMETRY_HPP_

#include <string>

namespace trnav_motion_core
{

// Platform enumeration for wheel-array interpretation.
// Reference: trnav_motion_mux_architecture.md §플랫폼별 배열 해석
enum class Platform
{
    QD_DIAGONAL,     // 2 wheels: [0]=W1(전-좌), [1]=W2(후-우)
    DD,              // 2 wheels: [0]=Left, [1]=Right (steering always 0)
    FWS_INDEPENDENT, // 4 wheels: [0..3]=FL,FR,RL,RR (independent steer)
    ACKERMANN        // 4 wheels: [0..3]=FL,FR,RL,RR (rear steering=0)
};

// Platform-independent robot geometry.
// Populated from YAML via fromParams() — one yaml per robot variant.
struct RobotGeometry
{
    Platform platform;
    // QD-diagonal wheel positions (robot frame, m)
    // Only meaningful for 2-wheel QD; other platforms define own conventions.
    double w1_x; // +forward
    double w1_y; // +left
    double w2_x;
    double w2_y;
    double wheel_radius; // m
    double gear_walk;    // walk motor gear ratio (for RPM display)
    std::size_t num_wheels;
};

inline Platform parsePlatform(const std::string &name)
{
    if (name == "QD_DIAGONAL" || name == "qd_diagonal")
        return Platform::QD_DIAGONAL;
    if (name == "DD" || name == "dd")
        return Platform::DD;
    if (name == "FWS_INDEPENDENT" || name == "fws_independent")
        return Platform::FWS_INDEPENDENT;
    if (name == "ACKERMANN" || name == "ackermann")
        return Platform::ACKERMANN;
    // Default fallback — most robots today are QD diagonal.
    return Platform::QD_DIAGONAL;
}

} // namespace trnav_motion_core

#endif // AMR_MOTION_CORE__ROBOT_GEOMETRY_HPP_
