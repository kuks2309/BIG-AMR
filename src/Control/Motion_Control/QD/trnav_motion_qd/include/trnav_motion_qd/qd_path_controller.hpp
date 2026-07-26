#ifndef TRNAV_MOTION_QD__QD_PATH_CONTROLLER_HPP_
#define TRNAV_MOTION_QD__QD_PATH_CONTROLLER_HPP_

#include "trnav_motion_core/recursive_moving_average.hpp"
#include <cmath>
#include <cstdint>

namespace trnav::motion::qd
{

// Translate Wave 2 범위: BICYCLE 모드만 우선 지원.
// Mode 2 (SEQUENTIAL_CTE) / Mode 3 (PURE_STANLEY) / Mode 10 (VY_OMEGA) /
// Mode 11 (FRONT_STANLEY) 는 후속 Wave 에서 추가.
enum class ControlMode : uint8_t
{
    BICYCLE = 1,
};

// 2026-04-27 Step 6: Translate Forward/Reverse 분리 후 QdPathController 가
// reverse 모드를 명시적으로 받아 BICYCLE heading PD 부호를 반전.
enum class TravelDirection : uint8_t
{
    FORWARD = 0,
    REVERSE = 1,
};

struct PathControlOutput
{
    double vy;         // (BICYCLE 미사용 — dual bicycle 경로 사용)
    double omega;      // (BICYCLE 미사용 — dual bicycle 경로 사용)
    double e_d;        // 횡방향 오차 (m), + 경로 좌측, - 경로 우측
    double e_theta;    // 헤딩 오차 (rad), [-pi, pi]
    double projection; // 경로 진행 거리 (m)
    int control_stage; // BICYCLE 에서는 항상 0
    double delta_f;    // 전륜 조향 (rad) — BICYCLE 출력
    double delta_r;    // 후륜 조향 (rad)
};

class QdPathController
{
  public:
    struct Params
    {
        double Kp_heading = 1.0;
        double Kd_heading = 0.3;
        double K_stanley = 2.0;
        double K_soft = 1.0;
        double heading_threshold = 0.785; // rad (45 deg) — validateInitialPose
        double max_lateral_offset = 1.0;  // m — validateInitialPose
        int heading_filter_window = 5;    // e_theta RMA 창 크기
        int cte_filter_window = 1;        // e_d RMA 창 크기
        ControlMode mode = ControlMode::BICYCLE;
        double max_delta = M_PI / 4.0; // rad (45 deg) — BICYCLE 조향 saturation
    };

    explicit QdPathController(const Params &params);
    void reset();
    void setPath(double start_x, double start_y, double end_x, double end_y);

    // Runtime mode switch (BICYCLE 만 유효. 후속 Wave 에서 enum 확장).
    void setMode(ControlMode mode);

    // Hot-reload 5 scalar gains atomically (no filter buffer / path state reset).
    void setGains(double Kp_heading, double Kd_heading, double K_stanley, double K_soft, double max_delta_rad);

    // Main control update. Call every cycle.
    PathControlOutput update(double robot_x, double robot_y, double robot_yaw, double vx, double dt,
                             TravelDirection dir = TravelDirection::FORWARD);

    // Initial pose validation. Returns 0 if OK, -2 if invalid.
    int validateInitialPose(double robot_x, double robot_y, double robot_yaw) const;

    double targetDistance() const
    {
        return target_distance_;
    }
    double pathAngle() const
    {
        return theta_path_;
    }

  private:
    double computeStanleyCTE(double e_d, double vx) const;
    double computeHeadingPD(double e_theta, double de_theta) const;
    PathControlOutput computeBicycle(double e_d, double e_theta, double de_theta, double vx, TravelDirection dir);

    Params params_;
    ControlMode mode_{ControlMode::BICYCLE};
    double start_x_{0.0}, start_y_{0.0};
    double end_x_{0.0}, end_y_{0.0};
    double theta_path_{0.0};
    double target_distance_{0.0};
    double ux_{0.0}, uy_{0.0}; // path unit vector
    double prev_e_theta_{0.0};
    bool initialized_{false};
    bool first_update_{true};
    trnav_motion_core::RecursiveMovingAverage e_theta_filter_;
    trnav_motion_core::RecursiveMovingAverage e_d_filter_;
};

} // namespace trnav::motion::qd

#endif // TRNAV_MOTION_QD__QD_PATH_CONTROLLER_HPP_
