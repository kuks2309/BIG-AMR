#include "mcl2d_core/motion_model.hpp"

#include <cmath>

namespace mcl2d
{

namespace
{
// 원본 난수: RangeRandom(-1000, 1000) / 2000.0.
//   원본 구현(libfoundation 0x18c60, 2026-08-06 실측): `rand() % (max - min) + min` — **+1 이 없어**
//   상한이 배제된다. 즉 RangeRandom(-1000,1000) 은 [-1000, +999] 의 2000개 값이다(2001 아님).
//   나눗셈 상수 0x59fef0 = 2000.0 실측. 시드는 원본이 최초 1회 srand(time(NULL)) — 재현 불가.
//   우리는 재현성을 위해 mt19937 을 쓰되 **값 집합은 원본과 같게** 맞춘다.
double rangeRandomHalf(std::mt19937 &rng)
{
    std::uniform_int_distribution<int> u(-1000, 999);
    return static_cast<double>(u(rng)) / 2000.0;
}

// 모드 2 의 각도·모드 5 의 거리는 원본에 하드코딩된 리터럴이다(파라미터 아님).
constexpr double kMode2AngleDeg = 2.0;      // .rodata 0x562980
constexpr double kMode5FallbackDistMm = 10.0; // .rodata 0x5629d8
constexpr double kDegToRad = M_PI / 180.0;
constexpr double kMmToM = 0.001;
} // namespace

double normalizeAngle(double a)
{
    while (a >= M_PI)
        a -= 2.0 * M_PI;
    while (a < -M_PI)
        a += 2.0 * M_PI;
    return a;
}

ControlIncrement2D supplyControlVar(const Pose2D &prev_odom, const Pose2D &cur_odom)
{
    const double dx = cur_odom.x - prev_odom.x;
    const double dy = cur_odom.y - prev_odom.y;
    const double cs = std::cos(prev_odom.theta);
    const double sn = std::sin(prev_odom.theta);

    ControlIncrement2D c;
    const double dx_b = dx * cs + dy * sn; // 로봇 전방 성분
    const double dy_b = dy * cs - dx * sn; // 로봇 좌측 성분
    // dθ 정규화는 원본과 **1 ulp 수준에서만** 다르다(오라클 실측: 400표본 중 16건).
    //   원본 경로: Normalize(d)(libfoundation 0x18750, floor 기반) → 조건부 atan2(sin,cos) 재정규화(33d91c→33dca3).
    //   후보 5개를 원본과 비트 대조한 결과 이 while 루프가 최선(384/400)이었고, 원본 식을 그대로 옮긴
    //   재현(349/400)·atan2 단독(300/400)은 오히려 낮았다 — 잔여 원인 미확정이라 추측으로 바꾸지 않는다.
    //   추적: docs/debt/registry.md debt-032
    c.dtheta = normalizeAngle(cur_odom.theta - prev_odom.theta);
    c.trans = std::sqrt(dx_b * dx_b + dy_b * dy_b);
    c.direction = std::atan2(dy_b, dx_b);
    return c;
}

void doParticleMove(Particle &p, const ControlIncrement2D &c)
{
    // 이동 방향을 파티클 자신의 헤딩 기준으로 재투영 — 노이즈는 붙지 않는다(원본 d=0).
    const double heading = p.pose.theta + c.direction;
    p.pose.x += c.trans * std::cos(heading);
    p.pose.y += c.trans * std::sin(heading);
    p.pose.theta = normalizeAngle(p.pose.theta + c.dtheta);
}

void doExtraMove(Particle &p, const ExtraMoveParams &e, std::mt19937 &rng)
{
    // x·y 는 같은 반폭이지만 난수는 각각 독립 — 원본이 RangeRandom 을 두 번 호출한다.
    p.pose.x += rangeRandomHalf(rng) * e.radius;
    p.pose.y += rangeRandomHalf(rng) * e.radius;
    p.pose.theta = normalizeAngle(p.pose.theta + rangeRandomHalf(rng) * e.angle);
}

ExtraMoveParams selectExtraMove(double trans, double dtheta, double likelihood, const Mcl2dParams &params)
{
    const double abs_dtheta = std::fabs(dtheta);
    const bool moved_far = trans > params.extra_move_dist_threshold;
    const bool turned = abs_dtheta > params.extra_move_angle_threshold;
    const bool confident = likelihood >= params.best_particle_tolerant_threshold;

    ExtraMoveParams e;
    if (!turned)
    {
        // 회전이 없으면 거리만 본다: 많이 움직였으면 큰 반경 + 고정 2°, 아니면 저속 산포.
        if (moved_far)
        {
            e = {params.extra_move_radius, kMode2AngleDeg * kDegToRad, 2};
        }
        else
        {
            e = {params.low_speed_move_radius, params.low_speed_move_angle, 4};
        }
    }
    else if (confident)
    {
        // 신뢰도가 높으면 회전 중이어도 작게 — ForceExtraMove 가 켜지면 그 값으로 대체.
        e = params.force_extra_move
                ? ExtraMoveParams{params.force_extra_move_dist, params.force_extra_move_angle, 5}
                : ExtraMoveParams{kMode5FallbackDistMm * kMmToM, params.force_extra_move_angle, 5};
    }
    else
    {
        // 회전 중 + 신뢰도 낮음: 이동량에 따라 큰 산포(40mm) / 기본 산포(10mm).
        e = moved_far ? ExtraMoveParams{params.extra_move_radius, params.extra_move_angle, 1}
                      : ExtraMoveParams{params.move_radius, params.extra_move_angle, 3};
    }
    return e;
}

} // namespace mcl2d
