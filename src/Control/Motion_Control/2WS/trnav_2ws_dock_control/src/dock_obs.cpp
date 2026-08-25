#include "dock_control/dock_obs.hpp"

#include <cmath>

#include "dock_control/dock_core.hpp"

namespace dock_control
{

DockObservation wallPoseToDockObs(const StationPose &cur, const DockTargetPose &target,
                                  double approach_axis_rad)
{
    DockObservation obs;
    const bool finite = std::isfinite(cur.x_m) && std::isfinite(cur.y_m) &&
                        std::isfinite(cur.yaw_rad) && std::isfinite(target.x_m) &&
                        std::isfinite(target.y_m) && std::isfinite(target.yaw_rad) &&
                        std::isfinite(approach_axis_rad);
    if (!finite)
    {
        return obs;  // valid=false — 무효 관측은 축값도 신뢰 불가
    }

    // 스테이션 프레임 오차 → base_link 프레임 (수동 회전 R(−yaw))
    const double dx = target.x_m - cur.x_m;
    const double dy = target.y_m - cur.y_m;
    const double c = std::cos(cur.yaw_rad);
    const double s = std::sin(cur.yaw_rad);
    const double ex_base = c * dx + s * dy;
    const double ey_base = -s * dx + c * dy;

    // 접근축 성분 분해 — u = 접근축, n = u 의 +90°(좌수) 방향
    const double ua = std::cos(approach_axis_rad);
    const double ub = std::sin(approach_axis_rad);
    obs.e_d_m = ua * ex_base + ub * ey_base;
    obs.e_lat_m = -ub * ex_base + ua * ey_base;
    obs.e_yaw_deg = wrapPm180((target.yaw_rad - cur.yaw_rad) * 180.0 / M_PI);
    obs.valid = true;
    return obs;
}

}  // namespace dock_control
