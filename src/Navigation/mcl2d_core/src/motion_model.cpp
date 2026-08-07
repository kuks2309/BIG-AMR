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
    // 원본은 회전용 sin/cos 인자에도 Normalize 를 먹인다(33dcd3 · 33dcec) — 범위 밖 각이 들어오면
    //   같은 각이라도 sin/cos 의 부동소수점 결과가 갈리므로 동일하게 맞춘다.
    const double prev_theta = normalizeAngle(prev_odom.theta);
    const double cs = std::cos(prev_theta);
    const double sn = std::sin(prev_theta);

    ControlIncrement2D c;
    const double dx_b = dx * cs + dy * sn; // 로봇 전방 성분
    const double dy_b = dy * cs - dx * sn; // 로봇 좌측 성분
    // dθ 는 **정규화 후 atan2 로 한 번 더** 통과시킨다 — 원본이 그렇게 한다:
    //   supplyControlVar 가 Normalize(cur.angle − prev.angle) 를 부르고(33d91c),
    //   그 결과를 atan2(sin, cos) 에 다시 넣는다(33dca3 sin → 33dcba cos → 33dcc8 atan2).
    //   원본 Normalize 를 dlopen 해 직접 대조한 결과 **while 루프와 비트 동일**(2000/2000)이었고,
    //   이 조합이 원본 dθ 와 **400/400 비트 일치**한다(단독 Normalize·단독 atan2 는 각각 384·300).
    const double dtheta_normalized = normalizeAngle(cur_odom.theta - prev_odom.theta);
    c.dtheta = std::atan2(std::sin(dtheta_normalized), std::cos(dtheta_normalized));
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
