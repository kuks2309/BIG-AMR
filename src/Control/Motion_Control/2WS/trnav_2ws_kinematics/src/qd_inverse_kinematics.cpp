#include "trnav_2ws_kinematics/qd_inverse_kinematics.hpp"

namespace trnav::motion::two_ws
{

TwoWsDualSteerIK::TwoWsDualSteerIK(std::vector<WheelPosition> wheels, double wheel_radius, double gear_walk)
    : wheels_(std::move(wheels)), wheel_radius_(wheel_radius), gear_walk_(gear_walk)
{
}

IKResult TwoWsDualSteerIK::compute(const VelocityCommand &cmd) const
{
    // Ported from dual_steer_engine.py::compute(cmd, constrained=False)
    // Lines 89-102: Free mode — each wheel steers independently
    //
    // v_i = V_body + ω × r_i
    //   vx_i = vx - omega * y_i
    //   vy_i = vy + omega * x_i

    IKResult result;
    result.wheels.reserve(wheels_.size());

    for (const auto &wp : wheels_)
    {
        double vx_i = cmd.vx - cmd.omega * wp.y;
        double vy_i = cmd.vy + cmd.omega * wp.x;
        result.wheels.push_back(computeWheel(vx_i, vy_i));
    }

    return result;
}

IKResult TwoWsDualSteerIK::computeSpin(double omega) const
{
    return compute({0.0, 0.0, omega});
}

WheelOutput TwoWsDualSteerIK::computeWheel(double vx, double vy) const
{
    WheelOutput out{};

    double spd = std::hypot(vx, vy);
    if (spd < 1e-6)
    {
        out.steer_rad = 0.0;
        out.wheel_speed = 0.0;
        out.direction = 0;
        out.drive_rpm = 0.0;
        return out;
    }

    double angle = std::atan2(vy, vx);
    int direction = 1; // FWD by default (same as _make_free: direction=1)

    // ±90° normalization — 의도: 유일해(canonical) 확정. 한 바퀴 속도벡터는 항상 등가 2해
    // (θ,+v) ≡ (θ∓180°,−v) 를 갖는데, [-90°,+90°](반원, 180° 폭)로 정규화하면 방향↔각도가
    // 1:1(전단사)이 되어 정확히 한 해만 남고 항상 최소 조향각을 고른다. atan2 분기·입력 이력에
    // 무관한 결정론적 출력 → 상위 heading/CTE 폐루프가 요구하는 연속·유일 조향 목표 보장.
    // Seer(±140°, chassis_kinematics.py:64)는 접기범위 280°>반원이라 90~140°에서 2해가 공존(비유일).
    // Big-AMR 조향 한계 > 90° 이므로 ±90° 정규화는 항상 물리범위 내(한계초과 위험 0).
    //
    // ⚠ 2026-07-27 감사 정정 — 바로 위 「한계초과 위험 0」 단정은 **본 기체 근거가 아니다.**
    //   (원문은 이력 보존용으로 남김. 코드·수치 변경 0건.)
    //   · 근거로 단 ADR 은 **다른 기체**를 확인한 것이다:
    //     docs/adr/2026-07-26-qd-ik-pm90-unique-solution.md:71-72
    //     「하드웨어 정합: 확인 완료(2026-07-26) — **Carrier AGV** 실제 조향 한계 > 90°」.
    //     본 기체는 Foil_A082 다(docs/verified_facts/2026-07-27.md:11 「장비: Foil_A082 실기」).
    //   · 같은 패키지가 정반대로 서술한다: qd_crab_inverse_kinematics.cpp:23 「모터 **±90° 한계** 반영」
    //     (→ 한계가 90° 초과라는 위 전제와 불일치. **미판정**).
    //   · 「물리범위 내」 판정의 기준점인 **조향 절대 원점 자체가 미판정**이다:
    //     docs/verified_facts/2026-07-27.md §B-1 — 같은 시각 Seer 1040 encoder 와 판다 read 가
    //     조향 노드에서만 7.87 M counts(=137°) 어긋나며, (a)판다 read 오염 / (b)호밍 후 기준 재설정
    //     중 어느 쪽인지 미판정.
    //   ⇒ 여기서 확정 가능한 것은 「이 함수의 ±90° 정규화 **출력**은 홈 기준 **상대각** ±90° 이내」 뿐.
    //     물리 한계 초과 여부는 (a) 본 기체의 조향 한계값 (b) 조향 절대 원점 이 **둘 다 확정된 뒤에만**
    //     판정 가능하며, 현재 둘 다 미판정이다.
    //   판정에 필요한 측정: (a) Foil_A082 조향축 기계 스톱 각도 실측(잭업·수동),
    //     (b) 제어권 미획득 상태의 판다 0x6064 read 와 동시각 Seer 1040 encoder 대조.
    //   ※ 위 줄의 인용 「chassis_kinematics.py:64」는 같은 감사에서 그 파일에 주석을 덧붙이며
    //     행이 밀렸다 — 현재 위치는 `Tools/Kinematics/chassis_kinematics.py:83`
    //     (`if abs(th) > STEER_LIMIT_RAD:` ±140° 접기), 상수 정의는 :56.
    //     (디렉터리도 2026-07-27 세션 중 `Tool/` → `Tools/` 로 이동됐다.)
    // 상세: docs/adr/2026-07-26-qd-ik-pm90-unique-solution.md
    double steer = normalizeAngle(angle, direction);

    // RPM for feedback display
    //   rpm = (spd / wheel_radius) * 60 / (2π)
    //   motor_rpm = rpm * gear_ratio
    double wheel_rpm = (spd / wheel_radius_) * 60.0 / (2.0 * M_PI);

    out.steer_rad = steer;
    out.wheel_speed = spd;
    out.direction = direction;
    out.drive_rpm = wheel_rpm * gear_walk_;

    return out;
}

double TwoWsDualSteerIK::normalizeAngle(double angle_rad, int &direction)
{
    if (angle_rad > M_PI / 2.0)
    {
        angle_rad -= M_PI;
        direction = -direction;
    }
    else if (angle_rad < -M_PI / 2.0)
    {
        angle_rad += M_PI;
        direction = -direction;
    }

    return angle_rad;
}

} // namespace trnav::motion::two_ws
