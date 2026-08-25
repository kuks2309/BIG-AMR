#include "dock_control/dock_core.hpp"

#include <algorithm>
#include <cmath>

namespace dock_control
{

double wrapPm180(double deg)
{
    while (deg > 180.0) { deg -= 360.0; }
    while (deg <= -180.0) { deg += 360.0; }
    return deg;
}

double wrapMod180(double deg)
{
    // 정본 :265-271 — dock line 법선의 180도 모호성 전용. while 구조까지 동일하게 유지한다.
    while (deg > 90.0) { deg -= 180.0; }
    while (deg <= -90.0) { deg += 180.0; }
    return deg;
}

PidOutput distPidStep(double e, const double *e_prev, double d_raw, double dt,
                      PidState &state, const PidGains &gains, double cap,
                      const PidLimits &limits)
{
    // 정본 :363-371 의 연산 순서를 그대로 유지한다 — 순서를 바꾸면 부동소수 결과가 달라져
    // 골든 대조가 흔들린다.
    state.d_filt = limits.lpf_a * d_raw + (1.0 - limits.lpf_a) * state.d_filt;

    // 오차 부호 교차 -> I 하드 리셋. e_prev == nullptr 은 첫 cycle(정본의 None)이라 리셋하지 않는다.
    if (e_prev != nullptr && e * (*e_prev) < 0.0) { state.i_term = 0.0; }

    const double u_p = gains.kp * e;
    const double u_d = gains.kd * state.d_filt;
    const double u_raw = u_p + state.i_term + u_d;

    const bool saturating = (std::abs(u_raw) >= cap) && (e * u_raw > 0.0);
    if (std::abs(e) <= limits.i_band && !saturating)
    {
        state.i_term = std::max(-limits.i_clamp,
                                std::min(limits.i_clamp, state.i_term + gains.ki * e * dt));
    }

    PidOutput out;
    out.u = std::max(-cap, std::min(cap, u_p + state.i_term + u_d));
    out.u_p = u_p;
    out.u_i = state.i_term;
    out.u_d = u_d;
    return out;
}

double phase4Delta(double err_px, double e_d, double approach_sign,
                   const double *px_prev, double dt, PidState &state,
                   const PidGains &gains, double delta_max_rad,
                   const PidLimits &limits, double *out_e_px)
{
    // 정본 :1837-1838. travel 은 e_d 의 부호이며 0 은 전진 취급(>= 0).
    const double travel = (e_d >= 0.0) ? 1.0 : -1.0;
    const double e_px = travel * approach_sign * err_px;

    const double dpx_raw = (px_prev == nullptr) ? 0.0 : (e_px - *px_prev) / dt;

    // 정본 :1841-1843 — 같은 PID 엔진에 수평축 한계를 넘긴다. cap 은 delta_max_rad.
    const PidOutput out = distPidStep(e_px, px_prev, dpx_raw, dt, state, gains,
                                      delta_max_rad, limits);

    if (out_e_px != nullptr) { *out_e_px = e_px; }
    return out.u;
}

double geomEntryDelta(double cte_x, double e_d, double delta_max_rad)
{
    if (e_d <= 0.0) { return 0.0; }
    const double d = std::atan2(cte_x, e_d);
    return std::max(-delta_max_rad, std::min(delta_max_rad, d));
}

double geomEntryDeltaBiased(double cte_x, double e_d, double delta_max_rad, double bias_rad)
{
    const double d = geomEntryDelta(cte_x, e_d, delta_max_rad);
    if (bias_rad <= 0.0) { return d; }
    // 기하각보다 큰 바이어스는 얹지 않는다 — 오차가 거의 없는데 고정량을 더하면
    // «아무 이유 없이 3° 틀기» 가 된다. 상한을 기하각 자신으로 두면 과조향이
    // 기하각의 2배를 넘지 않고, 오차가 0 으로 갈수록 바이어스도 함께 0 으로 간다.
    const double applied = std::min(bias_rad, std::abs(d));
    const double biased = d + std::copysign(applied, d);
    return std::max(-delta_max_rad, std::min(delta_max_rad, biased));
}

double geomEntryTranslateNeed(double cte_x, double e_d, double delta_max_rad, double tol_m)
{
    // 경유점 안쪽 — 남은 거리로 지울 수 있는 양이 없다. 그래도 **완료 허용치 안이면 진입은
    // 성립한다**: 필요 진입각이 0 이고 조향이 순수 크랩(±90°)이라 그대로 들어가면 된다.
    // 종전에는 `|cte_x|` 를 통째로 부족분으로 돌려줘, 3-2 가 자기 허용치(5 px)까지 줄여도
    // 통과하지 못하고 재시도만 소진했다(실기: 잔류 3.2 mm 로 2 회 거부 후 실패).
    if (e_d <= 0.0) { return std::max(0.0, std::abs(cte_x) - tol_m); }
    const double reach = std::tan(delta_max_rad) * e_d;
    return std::max(0.0, std::abs(cte_x) - reach);
}

bool phase4AxesReady(bool has_lateral, bool has_range, bool has_yaw, bool yaw_channel_active)
{
    return has_lateral && has_range && (has_yaw || !yaw_channel_active);
}

double phase4Steer(double approach_sign, double delta, double delta_max_rad)
{
    const double steer = approach_sign * (M_PI / 2.0 - delta);
    const double slim = M_PI / 2.0 + delta_max_rad;   // 정본 :1845 — 90° 양쪽 보정 허용
    return std::max(-slim, std::min(slim, steer));
}

double steerFrameOffset(bool rear_approach, double approach_sign)
{
    if (!rear_approach) { return 0.0; }
    return -approach_sign * (M_PI / 2.0);
}

SteerTarget reachableSteer(double cur, double tgt, double limit_rad)
{
    // 현재도 목표도 구간 안이어야 한다. 조향은 단조 이동이므로 «양 끝이 구간 안» 이면 그
    // 사이도 구간 안이다 — 그래서 두 끝만 보면 경로 전체가 담보된다.
    // ±360° 는 같은 각·같은 방향이라 후보로 두지만, 구간(±115° 대)을 늘 벗어나므로 실질
    // 후보가 아니다. 남겨 두는 것은 「같은 각의 다른 표현이 들어와도 판정이 흔들리지 않는다」
    // 는 뜻이다. **±180° 는 후보가 아니다** — 헤더의 ⚠ 참조.
    if (!std::isfinite(cur) || !std::isfinite(tgt) || std::abs(cur) > limit_rad)
    {
        return SteerTarget{};
    }
    for (const double cand : {tgt, tgt - 2.0 * M_PI, tgt + 2.0 * M_PI})
    {
        if (std::abs(cand) <= limit_rad)
        {
            return SteerTarget{true, cand};
        }
    }
    return SteerTarget{};
}

DockWheelCommand composePhase4Wheels(double v_app, double steer_rad, double w_deg,
                                     double approach_sign, double arm_m)
{
    // 정본 :1877-1881.
    const double dv = (w_deg * M_PI / 180.0) * arm_m;
    DockWheelCommand cmd;
    cmd.af = steer_rad;
    cmd.ar = steer_rad;
    cmd.vf = v_app + approach_sign * dv;
    cmd.vr = v_app - approach_sign * dv;
    return cmd;
}

double phase4Vcap(double v_stage, double e_d, double near_zone_m, double v_near)
{
    // 정본 :1812-1814.
    return (std::abs(e_d) <= near_zone_m) ? std::min(v_stage, v_near) : v_stage;
}

void imuAccumStep(ImuAccum &state, double imu_yaw_rad)
{
    // 정본 :1854-1857.
    const double iy = imu_yaw_rad * 180.0 / M_PI;
    if (!state.have_prev)
    {
        state.prev_deg = iy;
        state.have_prev = true;
        return;
    }
    state.cum_deg += wrapPm180(iy - state.prev_deg);
    state.prev_deg = iy;
}

bool imuRunaway(const ImuAccum &state, double cap_deg)
{
    // 정본 :1859.
    return std::abs(state.cum_deg) > cap_deg;
}

bool orbitOvershoot(double imu_yaw_rad, double imu0_yaw_rad, double dphi_deg, double cap_deg)
{
    // 정본 :1272-1274.
    const double imu_rot = wrapPm180((imu_yaw_rad - imu0_yaw_rad) * 180.0 / M_PI);
    return std::abs(imu_rot) > std::abs(dphi_deg) + cap_deg;
}

double dockLineYawError(double yaw_err_deg)
{
    // 정본 :1864.
    return wrapPm180(yaw_err_deg - std::copysign(90.0, yaw_err_deg));
}

std::optional<double> computeOrbitCenter(double mx, double my, double yaw_err_deg,
                                         double nx_min)
{
    // 정본 :1352-1356.
    const double rad = yaw_err_deg * M_PI / 180.0;
    const double nx = std::cos(rad);
    const double ny = std::sin(rad);
    if (std::abs(nx) < nx_min) { return std::nullopt; }
    return my - mx * ny / nx;
}

HomeAbort returnHomeAbort(const HomeAbortInput &in)
{
    // 정본 :2030~2045 의 **제어흐름 순서 그대로**. 순서가 곧 의미다 — 정본은 라이다가 없으면
    // continue(:2040) 하므로 대기 중에는 FOV·timeout 을 검사하지 않는다.
    if (!in.obs_fresh) { return HomeAbort::STALE; }                      // 관측 자체가 낡음
    if (!in.has_lateral)                                                 // :2030~2031 + 유예
    {
        // 정본은 여기서 즉시 break 한다. 이식본은 **시간 유예**를 둔다 — 근거는
        // `HomeAbortInput::marker_grace_s` 주석(관측 미수신과 정보량이 같다 + 실기 결손률).
        return (in.marker_lost_elapsed_s > in.marker_grace_s) ? HomeAbort::STALE
                                                              : HomeAbort::MARKER_WAIT;
    }
    if (!in.has_range)                                                   // :2032~2040
    {
        return (in.lidar_wait_elapsed_s > in.lidar_wait_limit_s) ? HomeAbort::LIDAR_OVER
                                                                 : HomeAbort::LIDAR_WAIT;
    }
    if (std::abs(in.err_px) > in.fov_edge_px) { return HomeAbort::FOV; }  // :2042~2043
    if (in.elapsed_s > in.timeout_s) { return HomeAbort::TIMEOUT; }       // :2044~2045
    return HomeAbort::OK;
}

bool returnHomeDone(double e_d, double tol)
{
    // 정본 :2052 — **거리 단독**. 수평·자세를 더하면 v→0 이후 교착한다(FAILURES #24).
    return std::abs(e_d) <= tol;
}

double homeErrPxTarget(double dx_mm, double z_cam, double fx)
{
    // 정본 :2065. :2047 정변환 `x_mm = err_px*z/fx*1000` 의 역함수.
    // 변환이 성립하지 않는 관측(z·fx ≈ 0)에서는 0 — 무주입과 같아진다.
    if (!(std::abs(z_cam) > 1e-9) || !(std::abs(fx) > 1e-9)) { return 0.0; }
    return dx_mm * fx / (z_cam * 1000.0);
}

}  // namespace dock_control
