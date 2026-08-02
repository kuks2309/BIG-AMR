// ROS2 메시지 ↔ mcl2d_core 타입 변환 (무손실). 노드와 비교 하니스가 공유하여
// "ROS 배관이 위치추정 결과를 바꾸지 않음"을 동일 코어로 증명한다.
#ifndef MCL2D_ROS2_CONVERSIONS_HPP
#define MCL2D_ROS2_CONVERSIONS_HPP

#include <cmath>
#include <vector>

#include "geometry_msgs/msg/pose_with_covariance_stamped.hpp"
#include "mcl2d_core/types.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"

namespace mcl2d
{

// quaternion(z,w) → yaw (2D)
inline double yawFromQuat(double z, double w)
{
    return std::atan2(2.0 * w * z, 1.0 - 2.0 * z * z);
}

// sensor_msgs/LaserScan → mcl2d::LaserScan (무손실 복사)
inline LaserScan fromRosScan(const sensor_msgs::msg::LaserScan &s)
{
    LaserScan out;
    out.angle_min = s.angle_min;
    out.angle_increment = s.angle_increment;
    out.range_min = s.range_min;
    out.range_max = s.range_max;
    out.ranges.assign(s.ranges.begin(), s.ranges.end());
    return out;
}

// nav_msgs/Odometry → mcl2d::Pose2D
inline Pose2D fromRosOdom(const nav_msgs::msg::Odometry &o)
{
    Pose2D p;
    p.x = o.pose.pose.position.x;
    p.y = o.pose.pose.position.y;
    p.theta = yawFromQuat(o.pose.pose.orientation.z, o.pose.pose.orientation.w);
    return p;
}

// mcl2d::Pose2D → geometry_msgs/PoseWithCovarianceStamped
inline geometry_msgs::msg::PoseWithCovarianceStamped toRosPose(const Pose2D &p)
{
    geometry_msgs::msg::PoseWithCovarianceStamped m;
    m.pose.pose.position.x = p.x;
    m.pose.pose.position.y = p.y;
    m.pose.pose.orientation.z = std::sin(p.theta * 0.5);
    m.pose.pose.orientation.w = std::cos(p.theta * 0.5);
    return m;
}

} // namespace mcl2d

#endif // MCL2D_ROS2_CONVERSIONS_HPP
