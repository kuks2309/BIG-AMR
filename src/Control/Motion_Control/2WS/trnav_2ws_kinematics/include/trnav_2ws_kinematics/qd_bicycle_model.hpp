#ifndef TRNAV_2WS_KINEMATICS__QD_BICYCLE_MODEL_HPP_
#define TRNAV_2WS_KINEMATICS__QD_BICYCLE_MODEL_HPP_

#include "trnav_2ws_kinematics/qd_inverse_kinematics.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

namespace trnav::motion::two_ws
{

/// Bicycle model command: simplified (v, delta) input
struct BicycleCommand
{
    double v;     // m/s, longitudinal velocity (+forward, -reverse)
    double delta; // rad, virtual front steering angle (+left/CCW, -right/CW)
};

/// Dual bicycle model command: front + rear steering
/// Matches Python DualBicycleCommand in bicycle_model_engine.py
///
/// Kinematics (reference at robot center, L_f = L_r = L/2):
///   omega = vx * (tan(delta_f) - tan(delta_r)) / L
///   vy    = vx * (tan(delta_f) + tan(delta_r)) / 2
struct DualBicycleCommand
{
    double vx;      // m/s, longitudinal velocity (+forward, -reverse)
    double delta_f; // rad, front virtual steering angle (+left/CCW)
    double delta_r; // rad, rear virtual steering angle (+left/CCW)
};

/// Bicycle model state: extracted from dual steer system
struct BicycleState
{
    double v;              // m/s, longitudinal velocity (= vx from VelocityCommand)
    double delta;          // rad, equivalent steering angle
    double curvature;      // 1/m, path curvature (omega/v)
    double turning_radius; // m, instantaneous turning radius (inf for straight)
    double vy_residual;    // m/s, lateral velocity not captured by bicycle model
};

/// TwoWsBicycleModel: Abstraction layer over TwoWsDualSteerIK for the inline dual-steer platform.
///
/// Provides bidirectional conversion between bicycle model (v, delta)
/// and the dual steer inverse kinematics system.
///
/// The virtual wheelbase L is computed from the X-axis projection
/// of wheel positions: L = |w1_x - w2_x|
///
/// Limitations:
///   - Bicycle model assumes vy = 0 (no lateral velocity)
///   - fromVelocityCommand() reports vy as vy_residual when vy != 0
///   - Approximation degrades for large delta or when vy is significant
///   - Pure spin (vx=0, omega!=0) is NOT round-trippable:
///     fromVelocityCommand({0,0,omega}) -> {v=0, delta=+/-pi/2}
///     toVelocityCommand({0, pi/2})     -> {0, 0, 0}  (omega lost)
///     This is an inherent limitation: bicycle model requires v!=0 for omega.
///   - kDeltaMax is a mathematical guard against tan() overflow only.
///     Physical omega limits are NOT enforced here -- caller's responsibility.
class TwoWsBicycleModel
{
  public:
    /// Construct from wheel positions (same as TwoWsDualSteerIK constructor params)
    /// Stores wheels internally for use in fromIKResult().
    /// @param wheels  Wheel positions in robot frame (expects 2 wheels)
    explicit TwoWsBicycleModel(const std::vector<WheelPosition> &wheels);

    /// Construct with explicit wheelbase (fromIKResult unavailable in this mode)
    /// @param wheelbase_m  Virtual wheelbase in meters (must be > 0)
    explicit TwoWsBicycleModel(double wheelbase_m);

    /// Get the computed virtual wheelbase
    double wheelbase() const
    {
        return L_;
    }

    // ── Forward conversion: Bicycle -> Dual Steer ──

    /// Convert bicycle command to body velocity command
    VelocityCommand toVelocityCommand(const BicycleCommand &cmd) const;

    /// Convert bicycle command directly to IK result (convenience)
    IKResult toIKResult(const BicycleCommand &cmd, const TwoWsDualSteerIK &ik) const;

    /// Convert dual bicycle command to body velocity command
    VelocityCommand toVelocityCommand(const DualBicycleCommand &cmd) const;

    /// Convert dual bicycle command directly to IK result (convenience)
    IKResult toIKResult(const DualBicycleCommand &cmd, const TwoWsDualSteerIK &ik) const;

    // ── Reverse conversion: Dual Steer -> Bicycle ──

    /// Extract bicycle state from body velocity command
    BicycleState fromVelocityCommand(const VelocityCommand &vel) const;

    /// Extract bicycle state from IK result (reverse IK)
    /// @pre Constructed with wheel positions (not explicit wheelbase)
    /// @throws std::runtime_error if constructed with explicit wheelbase (no wheels stored)
    BicycleState fromIKResult(const IKResult &result) const;

    // ── Utility ──

    /// Compute curvature from bicycle command
    double curvature(const BicycleCommand &cmd) const;

    /// Compute turning radius from bicycle command
    double turningRadius(const BicycleCommand &cmd) const;

    /// Compute omega from bicycle command
    double omega(const BicycleCommand &cmd) const;

    /// Compute delta from omega and v
    /// Uses atan(omega * L / vx) with guard for vx~0.
    double deltaFromOmega(double vx, double omega_val) const;

  private:
    double L_;                          // virtual wheelbase (m)
    std::vector<WheelPosition> wheels_; // stored for fromIKResult
    bool has_wheels_;                   // true if constructed from wheel positions

    /// Velocity threshold for zero-speed handling
    static constexpr double kSpeedEpsilon = 1e-6;
    /// Steering angle limit (mathematical guard: prevents tan() overflow near +/-90 deg)
    static constexpr double kDeltaMax = M_PI / 2.0 - 0.001; // ~89.94 deg
};

} // namespace trnav::motion::two_ws

#endif // TRNAV_2WS_KINEMATICS__QD_BICYCLE_MODEL_HPP_
