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
    std::vector<WheelOutput> wheels; // [0]=W1(front, x>0), [1]=W2(rear, x<0)
};

/**
 * TwoWsDualSteerIK — inline dual-steer platform free (unconstrained) inverse kinematics
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
     * 제자리 회전 자세 — **푸는 것이 아니라 강제한다.**
     *
     * 이 스택의 기체는 두 바퀴가 x 축 위에 있는 **인라인 듀얼스티어**(y=0)다. 그러면
     *   v_i = ω × r_i = (−ω·y_i, ω·x_i) = (0, ω·x_i)
     * 이므로 조향각은 **항상 ±90°** 이고 부호는 x_i 의 부호로 갈린다(앞뒤가 반대 부호).
     * 바퀴마다 다른 것은 속도 |ω·x_i| 뿐이며 그것만 기하에서 계산한다.
     *
     * ⚠ **QD 대각 배치와 다르다.** QD 는 바퀴가 축에서 벗어나 있어 자세가 기하에 따라
     *   달라지므로 범용 IK 가 필요하다. 이 클래스는 그 배치가 아니다.
     *
     * ⚠ 예전에는 `compute({0,0,omega})` 로 범용 IK 를 태웠다. 계산 자체는 맞지만 결과가
     *   `wheels_[i].y == 0` 에 전적으로 의존해, 기하 파라미터가 어긋나면 **조용히 다른
     *   자세**가 나왔다 — 2026-08-08 실증: QD 기본값(±0.330, ±0.135)이 흘러들어와
     *   `atan2(0.330, −0.135) = 112.2°` → ±90° 반평면으로 접힌 **−67.75°(양 축 같은 부호)**
     *   가 나왔고, 제자리 회전이 **187 mm 병진**이 됐다(SIL). 실기였다면 그대로 밀고 나갔다.
     *   ⇒ 자세를 강제하고, 전제가 깨졌는지는 `isInline()` 으로 **기동 시 노출**한다.
     *
     * @param omega  Angular velocity (rad/s, +CCW)
     */
    IKResult computeSpin(double omega) const;

    /**
     * 인라인 전제 검사 — 모든 바퀴가 x 축 위(|y| ≤ tol)인가.
     *
     * `computeSpin` 이 ±90° 를 강제할 수 있는 근거이자, 이 클래스를 쓰는 스택 전체의 전제다.
     * 액션 서버는 **기동 시 이것을 확인하고 거짓이면 소리 내어 막아야 한다** — 조용히
     * 다른 자세로 도는 것보다 기동 실패가 낫다.
     *
     * @param tol_m  허용 오차(m). 기본 1 mm — 실측 휠 좌표의 유효숫자보다 작다.
     */
    bool isInline(double tol_m = 1e-3) const;

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
