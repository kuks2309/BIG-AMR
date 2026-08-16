#include "mcl2d_core/motion_model.hpp"

#include <cmath>

namespace mcl2d
{

namespace
{
// U(−0.5, +0.5) 반폭 난수. 원본 RangeRandom(-1000, 1000) 을 같은 제수로 나눈 것과 **값 집합이 같다**.
//   상한이 배제되는 이유: 원본 구현(libfoundation @0x18c60)이 `rand() % (max - min) + min` 이라
//   +1 이 없어 [-1000, +999] 의 2,000개 값이다(2,001 아님). 제수는 원본 .rodata @0x59fef0 에서 읽었다.
//   난수원은 일부러 다르다 — 원본은 srand(time(NULL)) 1회라 수열 재현이 불가능하므로,
//   여기서는 시드 고정 mt19937 을 써 시험 재현성을 얻는다. 분포는 같고 수열은 다르다.
double rangeRandomHalf(std::mt19937 &rng)
{
    std::uniform_int_distribution<int> u(-1000, 999);
    return static_cast<double>(u(rng)) / 2000.0;
}

// 원본이 하드코딩한 리터럴 — robot.param 파라미터가 아니라서 설정으로 바꿀 수 없다.
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
    // 회전용 sin/cos 인자도 정규화한다(원본 @0x33dcd3 · @0x33dcec) — 범위 밖 각이 들어오면
    //   수학적으로 같은 각이라도 sin/cos 의 부동소수점 결과가 갈린다.
    const double prev_theta = normalizeAngle(prev_odom.theta);
    const double cs = std::cos(prev_theta);
    const double sn = std::sin(prev_theta);

    ControlIncrement2D c;
    const double dx_b = dx * cs + dy * sn; // 로봇 전방 성분
    const double dy_b = dy * cs - dx * sn; // 로봇 좌측 성분
    // dθ 는 정규화 후 atan2 로 한 번 더 통과시킨다 — 원본이 Normalize(cur.angle − prev.angle) 결과를
    //   다시 atan2(sin, cos) 에 넣기 때문이다(@0x33d91c → @0x33dca3 sin → @0x33dcba cos → @0x33dcc8 atan2).
    //   중복처럼 보여도 **둘 중 하나만 쓰면 원본과 비트가 갈린다** — 지우지 말 것.
    const double dtheta_normalized = normalizeAngle(cur_odom.theta - prev_odom.theta);
    c.dtheta = std::atan2(std::sin(dtheta_normalized), std::cos(dtheta_normalized));
    c.trans = std::sqrt(dx_b * dx_b + dy_b * dy_b);
    c.direction = std::atan2(dy_b, dx_b);
    return c;
}

void doParticleMove(Particle &p, const ControlIncrement2D &c)
{
    // c.direction 은 직전 헤딩 기준 상대각이므로 파티클 자신의 헤딩에 더해 절대 방향으로 되돌린다.
    const double heading = p.pose.theta + c.direction;
    p.pose.x += c.trans * std::cos(heading);
    p.pose.y += c.trans * std::sin(heading);
    p.pose.theta = normalizeAngle(p.pose.theta + c.dtheta);
}

void doExtraMove(Particle &p, const ExtraMoveParams &e, std::mt19937 &rng)
{
    // x·y 는 같은 반폭이지만 난수는 각각 독립 추첨이다(원본도 RangeRandom 을 두 번 부른다).
    //   같은 난수를 재사용하면 대각선 위에만 뿌려져 산포가 1차원으로 붕괴한다.
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
        // 회전이 없으면 거리만 본다. 각도 산포는 파라미터가 아니라 원본 리터럴로 고정된다.
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
        // 신뢰도가 높으면 회전 중이어도 좁게 뿌린다. force_extra_move 가 켜지면 거리도 파라미터로 대체.
        e = params.force_extra_move
                ? ExtraMoveParams{params.force_extra_move_dist, params.force_extra_move_angle, 5}
                : ExtraMoveParams{kMode5FallbackDistMm * kMmToM, params.force_extra_move_angle, 5};
    }
    else
    {
        // 회전 중인데 신뢰도가 낮다 — 이동량이 크면 넓은 산포, 아니면 기본 산포.
        e = moved_far ? ExtraMoveParams{params.extra_move_radius, params.extra_move_angle, 1}
                      : ExtraMoveParams{params.move_radius, params.extra_move_angle, 3};
    }
    return e;
}

} // namespace mcl2d
