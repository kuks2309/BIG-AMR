// ROS2 메시지 ↔ mcl2d_core 타입 변환.
// 노드와 비교 하니스가 **이 파일을 공유**한다 — 변환이 한 곳에만 있어야 "ROS 배관이 위치추정
// 결과를 바꾸지 않는다" 를 같은 코드로 보일 수 있다. 노드 쪽에 별도 변환을 두지 말 것.
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

// 쿼터니언 (z, w) → yaw [rad]. 평면 회전만 다루므로 x·y 성분은 0 으로 가정한다 —
//   roll·pitch 가 실린 자세를 넣으면 결과가 조용히 틀린다.
inline double yawFromQuat(double z, double w)
{
    return std::atan2(2.0 * w * z, 1.0 - 2.0 * z * z);
}

// sensor_msgs/LaserScan → mcl2d::LaserScan. 각·거리 단위(rad·m)는 양쪽이 같아 그대로 옮긴다.
//   intensities 는 코어가 쓰지 않아 버린다.
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

// nav_msgs/Odometry → mcl2d::Pose2D. 자세만 취하고 twist·공분산은 버린다 —
//   모션모델이 두 시점의 **자세 증분**만 쓰기 때문이다.
inline Pose2D fromRosOdom(const nav_msgs::msg::Odometry &o)
{
    Pose2D p;
    p.x = o.pose.pose.position.x;
    p.y = o.pose.pose.position.y;
    p.theta = yawFromQuat(o.pose.pose.orientation.z, o.pose.pose.orientation.w);
    return p;
}

// mcl2d::Pose2D → geometry_msgs/PoseWithCovarianceStamped.
//   header(frame_id·stamp)와 공분산은 **채우지 않는다** — 호출측이 관측 시각과 신뢰도를 알고 있다.
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
