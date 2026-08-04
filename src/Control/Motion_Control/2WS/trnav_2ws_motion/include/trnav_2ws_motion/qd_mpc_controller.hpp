#ifndef TRNAV_2WS_MOTION__QD_MPC_CONTROLLER_HPP_
#define TRNAV_2WS_MOTION__QD_MPC_CONTROLLER_HPP_

// Kinematic MPC for path follow (BICYCLE 전륜).
//
// 알고리즘 (Python prototype mpc_test.py 의 C++ 이식, 2026-05-28):
//   - Decision var = [δ_0, ..., δ_{N-1}]  (N step 동안의 전륜 조향)
//   - Bicycle FK rollout (V_CONST 고정 — 외부 호출자 책임으로 단순화)
//   - Cost = Σ ( W_LAT*lat² + W_HDG*hdg² + W_DU*Δδ² + W_GOAL*goal_dist² )
//   - Solver = NLopt SLSQP
//   - Receding horizon — 매 update() 호출이 1회 optimize, 첫 δ 반환
//
// Path orientation 사용 (path.poses[i].yaw 직접) — Phase A 정공법 (jagged path 안정화).
// Output: bicycle delta_f (rad).

#include <cstddef>
#include <vector>

namespace trnav::motion::two_ws
{

struct MpcPose
{
    double x = 0.0;
    double y = 0.0;
    double yaw = 0.0;  // rad
};

struct MpcOutput
{
    bool valid = false;
    double delta_f = 0.0;   // rad — 전륜 조향
    double cost = 0.0;       // optimizer 의 최종 cost
    int n_iter = 0;          // optimizer 반복 횟수
    double e_d = 0.0;        // 현재 cycle 의 lat_err (debug)
    double e_theta = 0.0;    // heading_err (debug, rad)
    double remaining_to_goal = 0.0;  // m
};

class TwoWsMpcController
{
public:
    struct Params
    {
        // Bicycle
        double wheelbase = 0.66;
        double v_const = 0.5;            // m/s — 사용자 정책 고정
        double max_delta_rad = 0.7854;   // 45°

        // Horizon
        int N = 10;
        double dt_mpc = 0.1;             // s — MPC step

        // Cost weights
        double w_lat = 100.0;
        double w_hdg = 5.0;
        double w_du = 0.5;
        double w_goal = 20.0;

        // Solver
        double ftol_rel = 1e-3;
        int max_iter = 30;

        // Validation
        double max_lateral_offset = 1.0;
    };

    explicit TwoWsMpcController(const Params &params);
    void reset();

    // Hot-reload setters
    void setMaxDelta(double v) { params_.max_delta_rad = v; }

    bool setPath(const std::vector<MpcPose> &poses);
    bool initialized() const { return initialized_; }

    // Main update — NLopt SLSQP optimize. 1 cycle = 1 solve.
    // current_speed 인자는 호환성용 (kinematic MPC 는 v_const 사용).
    MpcOutput update(double robot_x, double robot_y, double robot_yaw,
                      double current_speed, double dt);

    int validateInitialPose(double robot_x, double robot_y, double robot_yaw) const;

private:
    // Internal: closest segment lat / hdg error.
    void closestSegmentError(double rx, double ry, double ryaw,
                              double &lat_err, double &hdg_err) const;

    // NLopt objective callback (static — this 캐스팅으로 자체 객체 접근).
    static double nloptObjective(unsigned n, const double *x, double *grad, void *data);

    // rollout + cost (objective 본문).
    double computeCost(const std::vector<double> &deltas,
                       double rx0, double ry0, double ryaw0) const;

    Params params_;
    std::vector<MpcPose> wp_;
    std::vector<double> seg_len_;
    std::vector<double> seg_cum_;
    double total_length_ = 0.0;
    std::vector<double> warm_start_;   // 이전 sol — receding warm start
    bool initialized_ = false;
};

} // namespace trnav::motion::two_ws

#endif  // TRNAV_2WS_MOTION__QD_MPC_CONTROLLER_HPP_
