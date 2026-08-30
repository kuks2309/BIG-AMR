#include "trnav_qd_kinematics/qd_crab_inverse_kinematics.hpp"

#include <cmath>

namespace trnav::motion::qd
{

QdCrabIK::QdCrabIK(std::size_t num_wheels, double wheel_radius, double gear_walk)
    : num_wheels_(num_wheels), wheel_radius_(wheel_radius), gear_walk_(gear_walk)
{
}

void QdCrabIK::setInitial(double initial_base_steer, int initial_walk_dir)
{
    initial_base_steer_ = initial_base_steer;
    initial_walk_dir_ = (initial_walk_dir >= 0) ? 1 : -1;
    initialized_ = true;
}

namespace
{
// ±(π/2 + margin) wrap + walk direction flip.
// 모터 ±90° 한계 반영. cruise 중 ±90° boundary 미세 진동 (walk dir flip 토글) 회피 위해
// ±20° 마진 적용 — wrap threshold = ±110°. 본 마진 안에서는 wrap 안 함, motor saturate
// (±90° strict 시 최대 ±20° wheel cmd 어긋남) 으로 robot 진행은 거의 정확.
constexpr double WRAP_MARGIN = 25.0 * M_PI / 180.0; // 25° = 0.436 rad (HIL 분석 결과 cruise 최대 ±6° + 안전마진)
double wrapSteer(double steer, int &dir)
{
    if (steer > M_PI / 2.0 + WRAP_MARGIN)
    {
        steer -= M_PI;
        dir = -dir;
    }
    else if (steer < -M_PI / 2.0 - WRAP_MARGIN)
    {
        steer += M_PI;
        dir = -dir;
    }
    return steer;
}
} // namespace

IKResult QdCrabIK::compute(double vx_path, double theta_body, double delta_cte,
                           double delta_heading) const
{
    IKResult result;
    result.wheels.reserve(num_wheels_);

    const double speed = std::abs(vx_path);
    const double rpm = (speed / wheel_radius_) * 60.0 / (2.0 * M_PI) * gear_walk_;

    // base steer = theta_body + delta_cte (front wheel)
    // rear steer = base - delta_heading
    double base_raw = theta_body + delta_cte;
    double rear_raw = base_raw - delta_heading;

    int front_dir, rear_dir;
    double front_steer, rear_steer;

    constexpr double CLAMP_MARGIN = 25.0 * M_PI / 180.0; // ±25° (어제 결정)

    if (initialized_)
    {
        // ── 2단계 (cruise) state-aware: Phase 0 결정 (initial_base_steer_, initial_walk_dir_)
        //    기준 ±25° clamp + walk dir 고정. wrap 없음.
        //
        //    base_raw 가 initial 과 ±π/2 이상 차이나면 동등 각도 (base_raw ± π) 로 wrap 하여
        //    initial 영역 안으로 옮긴 후 clamp. 이로써 Phase 0 이 결정한 부호/방향이 cruise
        //    내내 유지됨.
        auto bring_into_region = [&](double raw)
        {
            double diff = raw - initial_base_steer_;
            // wrap_pi diff
            while (diff > M_PI) diff -= 2.0 * M_PI;
            while (diff < -M_PI) diff += 2.0 * M_PI;
            // |diff| > π/2 이면 raw ± π 로 옮겨서 initial 영역 (|diff| ≤ π/2)
            if (diff > M_PI / 2.0) raw -= M_PI;
            else if (diff < -M_PI / 2.0) raw += M_PI;
            // 재계산 diff (이제 |diff| ≤ π/2)
            diff = raw - initial_base_steer_;
            while (diff > M_PI) diff -= 2.0 * M_PI;
            while (diff < -M_PI) diff += 2.0 * M_PI;
            // ±25° clamp
            if (diff > CLAMP_MARGIN) diff = CLAMP_MARGIN;
            else if (diff < -CLAMP_MARGIN) diff = -CLAMP_MARGIN;
            return initial_base_steer_ + diff;
        };
        front_steer = bring_into_region(base_raw);
        rear_steer = bring_into_region(rear_raw);
        front_dir = initial_walk_dir_;
        rear_dir = initial_walk_dir_;
    }
    else
    {
        // ── 1단계 (Phase 0) fallback 또는 legacy: ±π/2 + 25° 마진 wrap
        const int dir_initial = (vx_path >= 0.0) ? 1 : -1;
        front_dir = dir_initial;
        rear_dir = dir_initial;
        front_steer = wrapSteer(base_raw, front_dir);
        rear_steer = wrapSteer(rear_raw, rear_dir);
    }

    // wheels[0] = W1 (front-left, w1_x>0), wheels[1] = W2 (rear-right, w2_x<0)
    // 진행 방향 기준 rear: walk dir > 0 → W2, walk dir < 0 → W1.
    // initialized 시 initial_walk_dir_ 기준, 아니면 wrap 후 front_dir 기준 (동등).
    const bool w2_is_rear = (front_dir > 0);

    WheelOutput w1{}, w2{};
    if (w2_is_rear)
    {
        // W1 = front, W2 = rear
        w1.steer_rad = front_steer;
        w1.direction = (speed < 1e-6) ? 0 : front_dir;
        w2.steer_rad = rear_steer;
        w2.direction = (speed < 1e-6) ? 0 : rear_dir;
    }
    else
    {
        // 역방향: W1 = rear, W2 = front
        w1.steer_rad = rear_steer;
        w1.direction = (speed < 1e-6) ? 0 : rear_dir;
        w2.steer_rad = front_steer;
        w2.direction = (speed < 1e-6) ? 0 : front_dir;
    }
    w1.wheel_speed = speed;
    w1.drive_rpm = rpm;
    w2.wheel_speed = speed;
    w2.drive_rpm = rpm;

    if (num_wheels_ >= 2)
    {
        result.wheels.push_back(w1);
        result.wheels.push_back(w2);
    }
    else
    {
        // 1-wheel platform fallback (이론상 미사용 — front only)
        result.wheels.push_back(w1);
    }
    return result;
}

} // namespace trnav::motion::qd
