#ifndef TRNAV_2WS_KINEMATICS__QD_INVERSE_KINEMATICS_HPP_
#define TRNAV_2WS_KINEMATICS__QD_INVERSE_KINEMATICS_HPP_

#include <cmath>
#include <vector>

namespace trnav::motion::two_ws
{

/// Wheel position in robot frame (m)
struct WheelPosition
{
    double x; // m (+forward)
    double y; // m (+left)
};

/// Body velocity command
struct VelocityCommand
{
    double vx;    // m/s (+forward)
    double vy;    // m/s (+left)
    double omega; // rad/s (+CCW)
};

/// Single wheel IK output
/// Ported from dual_steer_engine.py::WheelOutput
struct WheelOutput
{
    double steer_rad;   // rad, normalized to [-π/2, +π/2]
    double wheel_speed; // m/s (always >= 0)
    int direction;      // +1 FWD, -1 REV, 0 STOP
    double drive_rpm;   // motor RPM (Feedback display, gear_walk applied)
};

/// IK result for all wheels
struct IKResult
{
    std::vector<WheelOutput> wheels; // [0]=W1(front-left), [1]=W2(rear-right)
};

/**
 * TwoWsDualSteerIK — QD diagonal-pair platform-specific free (unconstrained) inverse kinematics
 *
 * Ported from: dual_steer_engine.py::KinematicEngine
 * Reference: §1.6.2 of AMR_Motion_Control_Implementation_Plan.md
 *
 * Each wheel computed independently:
 *   v_ix = vx - omega * y_i
 *   v_iy = vy + omega * x_i
 *   steer = atan2(v_iy, v_ix)
 *   speed = hypot(v_ix, v_iy)
 *   ±90° normalization: |steer| > π/2 → flip π, reverse direction
 *
 * Constrained modes (Mode A/B) are NOT implemented — simulator only.
 */
class TwoWsDualSteerIK
{
  public:
    /**
     * @param wheels     Wheel positions in robot frame
     * @param wheel_radius  Wheel radius (m)
     * @param gear_walk     Walk gear ratio (for RPM display)
     */
    TwoWsDualSteerIK(std::vector<WheelPosition> wheels, double wheel_radius, double gear_walk);

    /**
     * Free (unconstrained) IK — main entry point.
     * Ported from: dual_steer_engine.py::compute(cmd, constrained=False)
     *
     * @param cmd  Body velocity command {vx, vy, omega}
     * @return IKResult with one WheelOutput per wheel
     */
    IKResult compute(const VelocityCommand &cmd) const;

    /**
     * Pure spin convenience wrapper.
     * Ported from: dual_steer_engine.py::compute_free_normalized(omega)
     * Equivalent to: compute({0, 0, omega})
     *
     * @param omega  Angular velocity (rad/s, +CCW)
     */
    IKResult computeSpin(double omega) const;

  private:
    /**
     * Compute single wheel output (unconstrained).
     * Ported from: dual_steer_engine.py::_make_free(vx, vy) + ±90° normalization
     *
     * @param vx  Wheel-frame X velocity (m/s)
     * @param vy  Wheel-frame Y velocity (m/s)
     */
    WheelOutput computeWheel(double vx, double vy) const;

    /**
     * Normalize steer angle to [-π/2, +π/2].
     * Ported from: dual_steer_engine.py::_make_wheel() lines 258-264
     *              and compute_free_normalized() lines 144-153
     *
     * If |angle| > π/2: subtract copysign(π), flip direction.
     *
     * @param angle_rad  Input steer angle (rad)
     * @param direction  Input direction (+1 or -1), modified in-place
     * @return Normalized angle in [-π/2, +π/2]
     */
    static double normalizeAngle(double angle_rad, int &direction);

    std::vector<WheelPosition> wheels_;
    double wheel_radius_;
    double gear_walk_;
};

} // namespace trnav::motion::two_ws

#endif // TRNAV_2WS_KINEMATICS__QD_INVERSE_KINEMATICS_HPP_
