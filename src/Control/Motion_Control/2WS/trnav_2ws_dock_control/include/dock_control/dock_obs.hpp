// dock_obs — 벽 3면 측위(/wall_pose)의 자세를 도킹 코어 관측으로 변환한다.
//
// 원본(LGIT)의 관측은 측면 카메라 마커(err_px)+라이다 거리+IMU 3원이었다. 이 기체는
// wall_localizer 가 스테이션 프레임 자세 T_station_base(x·y·yaw)를 단일 소스로 주므로,
// 목표 자세와의 차를 base_link 프레임의 접근축/직교축 성분으로 분해해 코어에 먹인다.
// 단위: m·rad 내부 단일, 출력 yaw 오차만 deg(코어 규약).
//
// ROS 를 모른다 — 코어와 같은 계약(rclcpp·메시지 참조 0).
#ifndef DOCK_CONTROL__DOCK_OBS_HPP_
#define DOCK_CONTROL__DOCK_OBS_HPP_

namespace dock_control
{

/// 스테이션 프레임 자세 — wall_localizer `/wall_pose` 출력 규약(T_station_base)과 동형.
struct StationPose
{
    double x_m{0.0};
    double y_m{0.0};
    double yaw_rad{0.0};
};

/// 도킹 목표 자세 (스테이션 프레임). 티치/설정으로 주입한다.
struct DockTargetPose
{
    double x_m{0.0};
    double y_m{0.0};
    double yaw_rad{0.0};
};

/// 도킹 코어 관측 3축.
/// 부호 규약: e_d > 0 = 목표가 접근축 **앞쪽**에 남아 있다(전진해야 한다).
///           e_lat > 0 = 목표가 접근축 기준 **좌수 +90° 방향**에 있다.
///           e_yaw_deg = 목표 − 현재, (−180, 180].
struct DockObservation
{
    double e_d_m{0.0};
    double e_lat_m{0.0};
    double e_yaw_deg{0.0};
    bool valid{false};  ///< 입력이 전부 유한할 때만 true — 무효 관측은 소비 금지(코어 게이트 규약)
};

/// T_station_base + 목표 → base_link 프레임 관측.
///
/// approach_axis_rad 는 **base_link 기준 접근축 방향각**이다 — 0 = 전방(+x),
/// +π/2 = 좌측(+y). 접근 방향은 실기 검증으로 확정한다(설정 주입).
/// 좌표 변환: e_station = target − cur (스테이션 프레임) → e_base = R(−yaw_cur)·e_station
/// → e_d = u·e_base, e_lat = n·e_base (u = 접근축 단위벡터, n = u 의 +90° 회전).
DockObservation wallPoseToDockObs(const StationPose &cur, const DockTargetPose &target,
                                  double approach_axis_rad);

}  // namespace dock_control

#endif  // DOCK_CONTROL__DOCK_OBS_HPP_
