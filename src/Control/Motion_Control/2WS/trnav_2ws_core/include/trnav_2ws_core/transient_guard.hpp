#ifndef AMR_MOTION_CORE__TRANSIENT_GUARD_HPP_
#define AMR_MOTION_CORE__TRANSIENT_GUARD_HPP_

#include <algorithm>
#include <cmath>

namespace trnav_2ws_core
{

class TransientGuard
{
  public:
    struct Params
    {
        double vy_rate_limit = 0.3;        // m/s per cycle
        double omega_rate_limit = 0.5;     // rad/s per cycle
        double steer_gate_threshold = 3.0; // deg, Phase 0->1 gate
        double steer_error_max = 10.0;     // deg, proportional decel range
        // deg — 이 값 이하의 조향 오차는 감쇠하지 않는다(측위 잡음발 소진동에
        // 구동을 깎지 않기 위한 불감대). 감쇠는 deadband~max 구간 선형, max 에서 0.
        double steer_error_deadband = 0.0;
        bool enable_proportional_decel = true;
        double runtime_gate_threshold = 15.0; // deg, runtime emergency gate
    };

    struct GuardInput
    {
        double vy_cmd;          // m/s
        double omega_cmd;       // rad/s
        double steer_error_deg; // max of |front_err|, |rear_err| in degrees
        bool is_phase0;         // true during Phase 0 (steer alignment)
    };

    struct GuardOutput
    {
        double vy_limited;    // rate-limited vy
        double omega_limited; // rate-limited omega
        double drive_scale;   // 0.0 ~ 1.0, proportional decel factor
        bool gate_blocked;    // true = zero drive velocity
    };

    explicit TransientGuard(const Params &params);
    void reset();
    GuardOutput apply(const GuardInput &input);

  private:
    static double clamp(double val, double lo, double hi);
    static double rateLimitStep(double current, double target, double max_change);

    Params params_;
    double prev_vy_{0.0};
    double prev_omega_{0.0};
};

} // namespace trnav_2ws_core

#endif // AMR_MOTION_CORE__TRANSIENT_GUARD_HPP_
