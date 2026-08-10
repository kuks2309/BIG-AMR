#ifndef TRNAV_2WS_CORE__VELOCITY_RAMP_HPP_
#define TRNAV_2WS_CORE__VELOCITY_RAMP_HPP_

#include <cmath>

namespace trnav_2ws_core
{

/**
 * rampToward — 부호 있는 속도 지령을 가·감속 한계 안에서 목표로 한 스텝 옮긴다.
 *
 * ⚠ **부호가 아니라 크기로 판정해야 한다.** 「가속」은 `tgt > cur` 이 아니라
 *   `|tgt| > |cur|` 이다. 부호 있는 비교를 쓰면 **후진 구간에서 두 한계가 뒤바뀐다**:
 *
 *     cur=-0.10 → tgt=-0.30 (후진 가속)  :  tgt < cur 이므로 감속 한계로 가속한다
 *     cur=-0.30 → tgt=-0.10 (후진 감속)  :  tgt > cur 이므로 가속 한계로 제동한다
 *
 *   `walk_accel_limit=0.5`, `walk_decel_limit=1.0` 이면 **설계값의 2배로 가속하고
 *   절반으로 제동**한다 — 제동거리가 2배가 된다. `yaw_control` 은 `vx_max < 0` 을
 *   정식으로 허용하므로(`AMRMotionYawControl.action` 의 `+forward/-reverse`) 실제로
 *   도달하는 경로다. 이 함수는 후진판 구현을 정본으로 삼아 통일한 것이다.
 *
 * 부호가 교차할 때는 **일단 0 까지 감속**한다 — 정지 없이 방향을 뒤집으면 구동축이
 * 급반전한다.
 *
 * @param cur     현재 지령 속도(부호 있음)
 * @param tgt     목표 속도(부호 있음)
 * @param a_step  한 주기 가속 한계(크기, ≥ 0)
 * @param d_step  한 주기 감속 한계(크기, ≥ 0)
 */
inline double rampToward(double cur, double tgt, double a_step, double d_step)
{
    // 목표가 사실상 0 — 감속 한계로 0 까지 내린다.
    if (std::fabs(tgt) < 0.01)
    {
        if (cur > d_step)
            return cur - d_step;
        if (cur < -d_step)
            return cur + d_step;
        return tgt;
    }
    // 부호 교차 — 방향을 뒤집기 전에 0 을 지난다.
    if (tgt * cur < 0.0)
    {
        if (cur > d_step)
            return cur - d_step;
        if (cur < -d_step)
            return cur + d_step;
        return 0.0;
    }
    const double abs_cur = std::fabs(cur);
    const double abs_tgt = std::fabs(tgt);
    const double sign = (tgt >= 0.0) ? 1.0 : -1.0;
    if (abs_tgt > abs_cur)
        return sign * std::fmin(abs_tgt, abs_cur + a_step);   // 가속
    if (abs_tgt < abs_cur)
        return sign * std::fmax(abs_tgt, abs_cur - d_step);   // 감속
    return tgt;
}

} // namespace trnav_2ws_core

#endif // TRNAV_2WS_CORE__VELOCITY_RAMP_HPP_
