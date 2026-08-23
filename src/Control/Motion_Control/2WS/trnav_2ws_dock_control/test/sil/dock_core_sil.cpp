// dock_control 코어 SIL — 이식한 순수함수를 **직접 링크**해 Phase 4 를 폐루프로 돌린다.
//
// 왜 C++ 인가: 파이썬으로 다시 짜면 그것은 이식본이 아니라 내 재구현을 시험하는 것이 된다.
// 이 SIL 은 dock_core.cpp 를 그대로 링크하므로 **시험 대상이 실제 이식 코드**다.
// ROS 를 쓰지 않는다 — g++ 한 줄로 빌드된다(⟦CI:dock-no-ros⟧ 와 같은 성질).
//
// 범위: 코어 수준 SIL 이다. 제어 3축 + **재접근**(정본 :220-223)까지 담고,
//   FSM·진입 가드·관측 노이즈·지연은 없다(FSM/가드 = M3, dock_sim 전체 SIL = M4).
//   precisionAssist 는 ADR-PRECISION 결재 대기라 빠져 있다.
//   상수·게인은 **전부 정본 :176-232 값**을 쓴다 — 지어낸 값을 넣으면 다른 로봇을 시뮬레이션하게 된다.
#include "dock_control/dock_core.hpp"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace
{

using namespace dock_control;

/// 평면 기구학 플랜트. **상태는 전부 base_link 기준**이다 — 정본 :152-153 이
/// "거리축 = base_link y(라이다), 수평축 = base_link x(카메라 err_px)" 로 못박았다.
/// 따라서 상태 = 도크의 base_link 좌표 (mx, my) + 도크면 법선각 yaw_deg.
struct Plant
{
    double mx{0.0};       ///< 도크의 base_link x [m] — 수평축. 카메라가 err_px 로 관측
    double my{2.0};       ///< 도크의 base_link y [m] — 거리축. 라이다가 관측
    double yaw_deg{90.0}; ///< 도크면 법선각 [deg] — 정렬되면 +-90

    double arm{0.33};     ///< PHASE4_YAW_DV_ARM_M
    double fx{607.7};     ///< LEFT 카메라 실측 초점거리 [px]

    /// 로봇 절대 yaw [rad] — **IMU 가 보는 양**. 도크 좌표(base_link)와 달리 관성계 기준이다.
    /// ⚠ 새 멤버는 **반드시 맨 뒤에** 붙일 것. 아래 케이스 표가 위치 초기화라
    ///   중간에 끼우면 뒤 값이 통째로 밀린다(실제 사고: arm 에 fx 607.7 이 들어가 회전 0).
    double heading_rad{0.0};

    /// 한 스텝 적분. cmd 의 af==ar 를 전제로 한 crab 운동.
    ///
    /// **회전이 병진을 만든다** — base_link 는 로봇에 붙어 있으므로 로봇이 dth 만큼 CCW 회전하면
    /// 도크의 base_link 좌표가 R(-dth) 로 회전한다. 정본이 같은 변환을 명시한다:
    ///   :20  "spin 후 marker(base_link) = R(-delta) 회전"
    ///   :902-903  mx2 = mx*cos(d) + my*sin(d) ; my2 = -mx*sin(d) + my*cos(d)
    /// 이 결합을 빼면 yaw 축이 수평축을 흔들지 않는 것처럼 보여 SIL 이 낙관적이 된다
    /// (my~1m, w=8deg/s, dt=1/30s 면 한 틱에 dmx ~ 4.7mm — 허용치 8mm 급).
    void step(const DockWheelCommand &cmd, double dt)
    {
        const double v_body = 0.5 * (cmd.vf + cmd.vr);
        const double steer = cmd.af;

        // base_link 안에서의 로봇 속도. 조향각이 곧 속도 방향이다(crab).
        const double vx = v_body * std::cos(steer);
        const double vy = v_body * std::sin(steer);

        // ① 병진 — 로봇이 +x 로 가면 도크의 base_link x 는 그만큼 줄어든다.
        const double tx = mx - vx * dt;
        const double ty = my - vy * dt;

        // ② 회전 — R(-dth). composePhase4Wheels 의 역으로 얻은 각속도를 쓴다.
        //    정본 :1877-1881 이 vf = v + as*dv, vr = v - as*dv 이므로 dv = (vf-vr)/2,
        //    w_rad = dv/arm 의 부호는 as 가 이미 지령에 실려 있어 여기서 되풀이하지 않는다.
        const double w_rad = (cmd.vf - cmd.vr) / (2.0 * arm);
        const double dth = w_rad * dt;
        mx = tx * std::cos(dth) + ty * std::sin(dth);
        my = -tx * std::sin(dth) + ty * std::cos(dth);

        // ③ 도크면 법선각도 base_link 기준이라 같은 회전만큼 반대로 움직인다.
        yaw_deg -= dth * 180.0 / M_PI;
        heading_rad += dth;   // 로봇 자신은 +dth 만큼 돈다 (IMU 관측량)
    }

    /// 카메라 관측 err_px. 정본 :1727 `x_mm = err_px * z_cam / fx * 1000` 의 역이며,
    /// 그 x_mm 이 곧 도크의 base_link x 다 -> err_px = mx * fx / z_cam. **부호 조작 없음.**
    /// LEFT 측면 카메라는 도크를 옆으로 보므로 광축 거리 z_cam 은 |my| 로 근사한다.
    double errPx() const { return mx * fx / std::max(std::abs(my), 1e-3); }

    /// 라이다 거리 관측 — 접근측 부호를 걷어낸 양의 거리.
    double range(double approach_sign) const { return approach_sign * my; }
};

/// 정본 상수 (SIL 전용 사본 — 코어에는 리터럴을 두지 않는다).
/// **값·게인은 전부 정본 phase1_gui.py:176-232 에서 그대로 가져온다.** 그럴듯한 값을 지어내면
/// SIL 이 다른 로봇을 시뮬레이션하게 된다 — 수평 게인을 1/10 로 넣었다가 정본이 이미 해결한
/// 문제를 "새 발견"으로 보고한 전례가 있다.
struct Consts
{
    double near_zone_m{0.40};    // :195  PHASE4_NEAR_ZONE_M
    double v_near{0.08};         // :196  PHASE4_V_NEAR (rec_202838 실측)
    double v_staging{0.05};      // :190  PHASE4_V_STAGING (rec_154619)
    double delta_max_deg{25.0};  // :188  PHASE4_DELTA_MAX_DEG
    double kp_delta{0.015};      // :182  PHASE4_KP_DELTA [rad/px]. 근거 rec_163533 — 이보다 약하면
                                 //       수평 보정이 6cm 드리프트 후에야 잡힌다
    double ki_delta{0.0};        // :185  PHASE4_KI_DELTA — 정본 기본 0
    double kd_delta{0.0};        // :186  PHASE4_KD_DELTA — 정본 기본 0
    double kp_heading{1.0};      // :215  PHASE4_KP_HEADING [deg/s per deg] — 사용자 확정값
    double kd_heading{0.0};      // :216  PHASE4_KD_HEADING — 정본 기본 0 (라이다 각 미분 지터)
    double omega_max_deg_s{2.0}; // :205  PHASE4_OMEGA_MAX_DEG_S. 근거 v2 오버슛 관측
    double yaw_tol_deg{0.4};     // :206  PHASE4_YAW_TOL_DEG 데드밴드
    double yaw_done_deg{0.5};    // :208  PHASE4_YAW_DONE_DEG 완료 게이트 (TOL<DONE 히스테리시스)
    double arm_m{0.33};          // :219  PHASE4_YAW_DV_ARM_M
    double kp_y{0.30};           // :163  PHASE4_KP_Y  vy[m/s]=Kp·e_d[m]. ⚠ HIL 튜닝 대상
    double ki_y{0.05};           // :170  PHASE4_KI_Y  [1/s²] 데드밴드·정상외란 잔류 제거
    double kd_y{0.0};            // :171  PHASE4_KD_Y  정본 기본 0 (PI 로 bag 확인 후 부여)
    double i_band{0.05};         // :173  PHASE4_I_BAND (거리축) 적분 분리 밴드
    double i_clamp{0.03};        // PHASE4_I_CLAMP (거리축)
    double lpf_a{0.3};           // PHASE4_DY_LPF_A
    double i_band_px{30.0};      // :187  PHASE4_I_BAND_PX
    double i_clamp_delta{0.087}; // :187  PHASE4_I_CLAMP_DELTA
    double tol_center_mm{8.0};   // TOL_CENTER_MM
    double tol_d_m{0.01};        // STAGING 거리 허용오차 (:236 주석 "STAGING 0.01")
    double reapproach_m{0.08};   // :222  PHASE4_REAPPROACH_M
    int reapproach_max{2};       // :223  PHASE4_REAPPROACH_MAX
    double reapproach_v{0.024};  // :222  v상한 = 0.30 x 0.08
    double d_contact{0.03};      // :159  PHASE4_D_CONTACT (측면 20cm 정지 확정으로 FINAL 미사용)
    double yaw_runaway_deg{10.0};  // :224  PHASE4_YAW_RUNAWAY_DEG — IMU 누적 하드캡
    int converge_n{3};           // :176  PHASE4_CONVERGE_N — 3축 동시 충족을 **연속 N 사이클**
                                 //       요구해 단발 노이즈에 의한 오완료를 차단한다
};

struct Result
{
    int ticks{0};
    double d{0.0}, x_mm{0.0}, e_yaw{0.0};
    double min_abs_v{1e9};
    bool converged{false};
    double imu_cum{0.0};   ///< 종료 시점 IMU 누적 [deg]
    std::string stop;
};

/// Phase 4 폐루프 1회 실행. precisionAssist 는 **넣지 않는다**(ADR-PRECISION 대기).
Result runPhase4(Plant p, double approach_sign, double target_d, double v_stage,
                 const Consts &K, double dt, int max_ticks, bool verbose)
{
    // 게인은 전부 정본값(K).
    const PidGains g_d{K.kp_y, K.ki_y, K.kd_y};
    const PidGains g_px{K.kp_delta, K.ki_delta, K.kd_delta};
    const PidGains g_yaw{K.kp_heading, K.kd_heading, 0.0};
    const PidLimits lim_d{K.i_band, K.i_clamp, K.lpf_a};
    const PidLimits lim_px{K.i_band_px, K.i_clamp_delta, K.lpf_a};
    const double dmax = K.delta_max_deg * M_PI / 180.0;
    const double slim = M_PI / 2.0 + dmax;

    PidState st_d, st_px;
    ImuAccum imu;   // IMU 하드캡 상태 (정본 :1854-1859)
    double d_prev = 0.0, e_px_prev = 0.0, ey_prev = 0.0;
    bool have_d = false, have_px = false, have_ey = false;

    // 재접근 상태기 — 정본 :220-223. "정지하면 모든 게 멈춰야" 원칙상 모든 보정은 주행 중에만
    // 가능하므로, 거리 도달 시 잔차가 남으면 **크랩 조향을 유지한 채 후퇴 후 재진입**한다.
    bool retreating = false;
    int reapproach = 0;
    int conv = 0;   // 3축 동시 충족 연속 카운트 (PHASE4_CONVERGE_N)

    Result r;
    for (int t = 0; t < max_ticks; ++t)
    {
        r.ticks = t + 1;
        const double d_now = p.range(approach_sign);
        const double goal = retreating ? (target_d + K.reapproach_m) : target_d;
        const double e_d = d_now - goal;

        const double vcap = retreating ? K.reapproach_v
                                       : phase4Vcap(v_stage, e_d, K.near_zone_m, K.v_near);
        const double ded_raw = have_d ? (d_now - d_prev) / dt : 0.0;
        const double ep = d_prev - target_d;
        const double v_app = distPidStep(e_d, have_d ? &ep : nullptr, ded_raw, dt,
                                         st_d, g_d, vcap, lim_d).u;
        d_prev = d_now;
        have_d = true;

        double e_px_now = 0.0;
        const double delta = phase4Delta(p.errPx(), e_d, approach_sign,
                                         have_px ? &e_px_prev : nullptr, dt, st_px,
                                         g_px, dmax, lim_px, &e_px_now);
        e_px_prev = e_px_now;
        have_px = true;

        double steer = approach_sign * (M_PI / 2.0) - delta;
        steer = std::max(-slim, std::min(slim, steer));

        const double e_yaw = dockLineYawError(p.yaw_deg);
        double w_deg = 0.0;
        if (std::abs(e_yaw) > K.yaw_tol_deg)
        {
            const double de = have_ey ? (e_yaw - ey_prev) / dt : 0.0;
            w_deg = std::max(-K.omega_max_deg_s,
                             std::min(K.omega_max_deg_s, g_yaw.kp * e_yaw + g_yaw.ki * de));
        }
        ey_prev = e_yaw;
        have_ey = true;

        const DockWheelCommand cmd =
            composePhase4Wheels(v_app, steer, w_deg, approach_sign, K.arm_m);
        p.step(cmd, dt);

            r.min_abs_v = std::min(r.min_abs_v, std::abs(v_app));
        if (verbose && (t % 40 == 0))
        {
            std::printf("  t=%5.1fs d=%.4f e_d=%+.4f x=%+7.2fmm e_yaw=%+6.2f "
                        "v=%+.4f delta=%+.3f w=%+.2f | vf=%+.4f vr=%+.4f\n",
                        t * dt, d_now, e_d, p.mx * 1000.0, e_yaw, v_app, delta, w_deg,
                        cmd.vf, cmd.vr);
        }

        // IMU 하드 runaway 캡 — 정본 :1854-1859. 어떤 오작동이든 마커 이탈 전에 멈춘다.
        // 관측을 대신하는 것이 아니라 **관측이 틀렸을 때의 최후 방어선**이다.
        imuAccumStep(imu, p.heading_rad);
        r.imu_cum = imu.cum_deg;
        if (imuRunaway(imu, K.yaw_runaway_deg))
        {
            r.stop = "IMU runaway 하드캡";
            break;
        }

        if (d_now <= K.d_contact)
        {
            r.stop = "접촉 거리 도달";
            break;
        }

        // 거리 도달 판정 — 정본 :220-223 재접근 규약.
        if (std::abs(e_d) <= K.tol_d_m)
        {
            if (retreating)
            {
                retreating = false;           // 후퇴 완료 -> 재진입
            }
            else
            {
                const bool x_ok = std::abs(p.mx * 1000.0) <= K.tol_center_mm;
                const bool y_ok = std::abs(e_yaw) <= K.yaw_done_deg;
                // 연속 converge_n 사이클 동안 3축이 동시에 충족돼야 완료다.
                // 단발 노이즈 1샘플로 «완료» 판정이 나는 것을 막는다.
                conv = (x_ok && y_ok) ? conv + 1 : 0;
                if (conv >= K.converge_n)
                {
                    r.converged = true;
                    r.stop = "3축 수렴";
                    break;
                }
                if (x_ok && y_ok) { continue; }   // 카운트 누적 중 — 재접근 판단 보류
                if (reapproach < K.reapproach_max)
                {
                    ++reapproach;
                    retreating = true;        // 크랩 조향 유지한 채 후퇴
                }
                else
                {
                    r.stop = "재접근 한도 소진 — 잔차 남긴 완료";
                    break;
                }
            }
        }
        if (r.ticks == max_ticks) { r.stop = "시간 초과"; }
    }
    r.d = p.range(approach_sign);
    r.x_mm = p.mx * 1000.0;
    r.e_yaw = dockLineYawError(p.yaw_deg);
    return r;
}

/// 진입 조건 훑기 — 「어느 거리에서 어느 각도로 들어가면 안 되는가」의 지도를 만든다.
/// 격자: 초기 거리(base_link y) x 초기 자세오차 x 초기 수평오차.
/// 각 (거리, 자세) 칸에서 **성공하는 수평오차 구간**을 찾아 낸다.
void sweep(const Consts &K, double dt, int max_ticks, double target_d, double v_stage)
{
    const std::vector<double> dists = {0.40, 0.60, 0.80, 1.00, 1.50, 2.00};
    const std::vector<double> yaws = {-6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0};
    std::vector<double> xs;                       // 수평오차 [mm], 5mm 간격
    for (double x = -200.0; x <= 200.001; x += 5.0) { xs.push_back(x); }

    std::printf("\n진입 조건 훑기 — 성공하는 초기 수평오차 구간 [mm]\n");
    std::printf("  (성공 = |e_d|<=1mm & |x|<=%.0fmm & |e_yaw|<=%.1f deg 로 종료)\n",
                K.tol_center_mm, K.yaw_tol_deg);
    std::printf("  목표거리 %.2fm · 접근속도 %.2fm/s · %d Hz\n\n",
                target_d, v_stage, static_cast<int>(1.0 / dt + 0.5));

    std::printf("%9s |", "거리[m]");
    for (double y : yaws) { std::printf(" %14.0f", y); }
    std::printf("   <- 초기 자세오차 [deg]\n%s\n", std::string(9 + 2 + 15 * yaws.size(), '-').c_str());

    for (double d0 : dists)
    {
        std::printf("%9.2f |", d0);
        for (double y0 : yaws)
        {
            double lo = 1e9, hi = -1e9;
            int n_ok = 0;
            for (double x0 : xs)
            {
                Plant p{.mx = x0 / 1000.0, .my = d0, .yaw_deg = 90.0 + y0};
                const Result r = runPhase4(p, 1.0, target_d, v_stage, K, dt, max_ticks, false);
                if (r.converged)
                {
                    lo = std::min(lo, x0);
                    hi = std::max(hi, x0);
                    ++n_ok;
                }
            }
            if (n_ok == 0) { std::printf(" %14s", "없음"); }
            else
            {
                char buf[32];
                std::snprintf(buf, sizeof(buf), "%+.0f..%+.0f", lo, hi);
                std::printf(" %14s", buf);
            }
        }
        std::printf("\n");
    }
    std::printf("\n※ 구간은 5mm 간격 격자에서 수렴한 값의 최소~최대다(연속성은 별도 확인 사항).\n");
}

}  // namespace

int main(int argc, char **argv)
{
    const bool verbose = (argc > 1 && std::strcmp(argv[1], "-v") == 0);
    const bool do_sweep = (argc > 1 && std::strcmp(argv[1], "--sweep") == 0);
    const Consts K;
    const double dt = 1.0 / 30.0;      // 30 Hz
    const int max_ticks = 30 * 120;    // 120 s
    const double target_d = 0.25;

    if (do_sweep)
    {
        sweep(K, dt, max_ticks, target_d, K.v_staging);
        return 0;
    }

    // Plant 초기값은 **base_link 좌표 [m]** — {mx(수평축), my(거리축), yaw_deg, arm, fx}.
    // as=-1 은 도크가 오른쪽(-y)에 있는 배치이므로 my·yaw 부호가 함께 뒤집힌다.
    struct Case { const char *name; Plant p; double as; double v_stage; };
    std::vector<Case> cases = {
        {"기준 — 정렬 근처",        {.mx = 0.030, .my = 1.20, .yaw_deg = 90.0},  1.0, 0.05},
        {"수평 오차 큼 (+120mm)",   {.mx = 0.120, .my = 1.20, .yaw_deg = 90.0},  1.0, 0.05},
        {"수평 오차 음(-120mm)",    {.mx = -0.120, .my = 1.20, .yaw_deg = 90.0},  1.0, 0.05},
        {"자세 오차 +4deg",         {.mx = 0.030, .my = 1.20, .yaw_deg = 94.0},  1.0, 0.05},
        {"자세 오차 -4deg",         {.mx = 0.030, .my = 1.20, .yaw_deg = 86.0},  1.0, 0.05},
        {"반대 접근측 (as=-1)",     {.mx = 0.030, .my = -1.20, .yaw_deg = -90.0}, -1.0, 0.05},
        {"목표보다 가까움(후퇴)",   {.mx = 0.020, .my = 0.22, .yaw_deg = 90.0},  1.0, 0.05},
    };

    std::printf("dock_control 코어 SIL — Phase 4 폐루프 (30 Hz, 목표거리 %.2f m)\n", target_d);
    std::printf("게인·상수 = 정본 phase1_gui.py:176-232 · 재접근 포함(%.2fm, 최대 %d회)\n",
                K.reapproach_m, K.reapproach_max);
    std::printf("⚠ precisionAssist 미이식(ADR-PRECISION 대기) · FSM·진입가드 없음(M3)"
                " · 관측 노이즈·지연 없음(M4)\n\n");
    std::printf("%-24s %7s %9s %10s %9s %10s %8s  %s\n",
                "시나리오", "틱", "d[m]", "x[mm]", "e_yaw[°]", "min|v|", "IMU누적", "종료");
    std::printf("%s\n", std::string(96, '-').c_str());

    int fail = 0;
    for (const auto &c : cases)
    {
        if (verbose) { std::printf("\n[%s]\n", c.name); }
        const Result r = runPhase4(c.p, c.as, target_d, c.v_stage, K, dt, max_ticks, verbose);
        const bool x_ok = std::abs(r.x_mm) <= K.tol_center_mm;
        const bool y_ok = std::abs(r.e_yaw) <= K.yaw_tol_deg;
        std::printf("%-24s %7d %9.4f %10.2f %9.3f %10.5f %8.2f  %s%s%s\n",
                    c.name, r.ticks, r.d, r.x_mm, r.e_yaw, r.min_abs_v, r.imu_cum, r.stop.c_str(),
                    x_ok ? "" : "  [x 미수렴]", y_ok ? "" : "  [yaw 미수렴]");
        if (!x_ok || !y_ok) { ++fail; }
    }
    std::printf("\n%d/%zu 시나리오에서 x 또는 yaw 가 허용범위(±%.0fmm / ±%.1f°) 밖\n",
                fail, cases.size(), K.tol_center_mm, K.yaw_tol_deg);
    return 0;   // 판정하지 않는다 — 원자료를 낸다 (합격선은 M1 수치 6종 결재 소관)
}
