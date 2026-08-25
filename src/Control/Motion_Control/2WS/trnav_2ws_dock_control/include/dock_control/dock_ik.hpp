// dock_control IK 어댑터 — QdDualSteerIK 를 도킹 계약(steer-hold)에 맞게 감싼다.
//
// 왜 감싸는가: `trnav_2ws_kinematics/src/qd_inverse_kinematics.cpp:45-48·84-86` 이 `spd < 1e-6` 에서 **조향을 0 으로 되돌린다.**
// 정본에는 그 임계가 없다(ik_parity_check 실측: 그 구간에서만 56건 차이, 그 밖은 비트 동일).
// 속도가 0 을 관통하는 순간(재접근 반전·완료 직전)에 조향이 0° 로 복귀하면 접지 마찰로 차체가
// 밀린다 — 정본 :1749-1751 이 금지한 동작이다. 이 어댑터가 그 구간에서 **직전 조향을 유지**한다.
//
// ROS 를 모른다 — trnav_2ws_kinematics 는 순수 수학 패키지다(소스 직접 컴파일 — plain cmake).
#ifndef DOCK_CONTROL__DOCK_IK_HPP_
#define DOCK_CONTROL__DOCK_IK_HPP_

#include "dock_control/dock_core.hpp"
#include "trnav_2ws_kinematics/qd_inverse_kinematics.hpp"

namespace dock_control
{

/// 바퀴 기하 — 정본 :88-89 ORBIT_W1/W2 에 대응. 리터럴 금지(⟦CI:dock-no-drive-constants⟧)라
/// 호출자가 기하 설정(2WS 인라인 실측 ±0.6039, 0)에서 읽어 주입한다.
struct DockGeometry
{
    double w1_x{0.0}, w1_y{0.0};  ///< W1 front-left [m]
    double w2_x{0.0}, w2_y{0.0};  ///< W2 rear-right [m]
    double wheel_radius_m{0.0};   ///< drive_rpm 산출용 (steer/speed 에는 무영향)
    double gear_walk{1.0};        ///< 상동
};

/// QdDualSteerIK 어댑터. **상태를 갖는다** — 직전 조향을 기억해 임계 미만에서 유지한다.
/// 페이즈 진입마다 resetHold() 로 초기화할 것.
class SteerHoldIk
{
public:
    /// @param geom 기하 주입 (계획 §3.5 기하 SSOT)
    /// @param hold_below IK 가 조향을 0 으로 되돌리는 임계. trnav_2ws_kinematics 의 임계(1e-6)와
    ///                   값과 같은 것을 주입한다 — 상류가 바뀌면 여기도 바뀌어야 하므로
    ///                   리터럴로 박지 않는다.
    SteerHoldIk(const DockGeometry &geom, double hold_below);

    /// ICR 을 base_link 의 점 C=(cx, cy) 에 놓는 공전. 정본 `orbit_wheel_cmd`(:274-296) 대응.
    /// body 속도는 vx = cy*w, vy = -cx*w 이며 바퀴별 분해는 QdDualSteerIK::compute 가 한다.
    DockWheelCommand orbit(double cx, double cy, double omega);

    /// 순수 전후(base_link x). 정본 `fwd_wheel_cmd`(:298-301) 대응.
    DockWheelCommand forward(double vx);

    /// 일반 body 속도 → 바퀴 지령. 위 둘의 공통 경로.
    DockWheelCommand compute(double vx, double vy, double omega);

    /// 조향 유지 상태 초기화. **페이즈 진입 1회** — 이전 페이즈의 조향이 새 페이즈로 새지 않게.
    void resetHold();

    /// 마지막으로 낸 조향 [rad]. 유지 이력이 없으면 false.
    bool lastSteer(double &af, double &ar) const;

private:
    DockGeometry geom_;
    trnav::motion::two_ws::TwoWsDualSteerIK ik_;
    double hold_below_;
    double last_af_{0.0};
    double last_ar_{0.0};
    bool have_last_{false};
};

}  // namespace dock_control

#endif  // DOCK_CONTROL__DOCK_IK_HPP_
