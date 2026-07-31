// 모션모델 단위 검증 — 원본(libMCLoc) 구조 충실 재작성분의 공개 함수 5개.
//   supplyControlVar / doParticleMove / doExtraMove / selectExtraMove / ParticleFilter2D::extraMove
// 근거: docs/adr/2026-07-31-mcl2d-motion-model-fidelity.md,
//       docs/comparison/seer-libmcloc-odom_vs_mcl2d-port_2026-07-31.md §1.1~§1.1.2
// NDEBUG 와 무관하게 실패할 수 있도록 자체 CHECK 매크로를 쓴다(assert 컴파일아웃 회피).
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>

#include "mcl2d_core/motion_model.hpp"

using namespace mcl2d;

static int g_fail = 0;
#define CHECK(cond, msg)                                                                                               \
    do                                                                                                                 \
    {                                                                                                                  \
        if (!(cond))                                                                                                   \
        {                                                                                                              \
            std::printf("[FAIL] %s  (%s:%d)\n", (msg), __FILE__, __LINE__);                                            \
            ++g_fail;                                                                                                  \
        }                                                                                                              \
    } while (0)

static bool near(double a, double b, double eps = 1e-9)
{
    return std::fabs(a - b) <= eps;
}

// ── supplyControlVar: 오도 증분의 로봇좌표 분해 ────────────────────────────────
static void testSupplyControlVar()
{
    // 1) 헤딩 0 에서 +x 로 0.5m → 전방 이동이므로 direction=0
    {
        const ControlIncrement2D c = supplyControlVar({0, 0, 0}, {0.5, 0, 0});
        CHECK(near(c.trans, 0.5), "전진 trans");
        CHECK(near(c.direction, 0.0), "전진 direction=0");
        CHECK(near(c.dtheta, 0.0), "전진 dtheta=0");
    }
    // 2) 헤딩 90° 에서 +y 로 0.5m → 로봇 기준으로는 여전히 '전방' → direction=0
    //    (맵 좌표 증분을 직전 헤딩으로 회전시키는지 확인하는 핵심 케이스)
    {
        const ControlIncrement2D c = supplyControlVar({0, 0, M_PI / 2}, {0, 0.5, M_PI / 2});
        CHECK(near(c.trans, 0.5), "헤딩90 전진 trans");
        CHECK(near(c.direction, 0.0, 1e-12), "헤딩90 전진 direction=0 (로봇좌표 분해)");
    }
    // 3) 헤딩 0 에서 +y 로 0.5m → 좌측 이동 → direction=+90°
    {
        const ControlIncrement2D c = supplyControlVar({0, 0, 0}, {0, 0.5, 0});
        CHECK(near(c.direction, M_PI / 2, 1e-12), "좌측 이동 direction=+90deg");
    }
    // 4) 제자리 회전 → trans=0, dtheta=Δ (경계를 넘는 회전은 정규화)
    {
        const ControlIncrement2D c = supplyControlVar({1, 2, 3.0}, {1, 2, -3.0});
        CHECK(near(c.trans, 0.0), "제자리 회전 trans=0");
        CHECK(near(c.dtheta, normalizeAngle(-6.0)), "회전 dtheta 정규화");
        CHECK(std::fabs(c.dtheta) <= M_PI, "dtheta 범위");
    }
}

// ── doParticleMove: 결정론(노이즈 없음) + 파티클 헤딩 기준 재투영 ──────────────
static void testDoParticleMove()
{
    const ControlIncrement2D c = supplyControlVar({0, 0, 0}, {1.0, 0, 0});

    // 1) 같은 입력은 항상 같은 출력 — 원본 d=0 이라 난수가 개입하지 않는다.
    Particle a{{0, 0, 0}, 1.0}, b{{0, 0, 0}, 1.0};
    doParticleMove(a, c);
    doParticleMove(b, c);
    CHECK(near(a.pose.x, b.pose.x) && near(a.pose.y, b.pose.y), "doParticleMove 결정론");
    CHECK(near(a.pose.x, 1.0) && near(a.pose.y, 0.0), "전진 1m 적용");

    // 2) 헤딩 90° 파티클은 같은 증분을 +y 로 받는다(파티클별 헤딩 기준 재투영).
    Particle p{{0, 0, M_PI / 2}, 1.0};
    doParticleMove(p, c);
    CHECK(near(p.pose.x, 0.0, 1e-12) && near(p.pose.y, 1.0, 1e-12), "헤딩90 파티클은 +y 로 이동");

    // 3) 회전 증분은 파티클 헤딩에 누적되고 정규화된다.
    Particle r{{0, 0, 3.0}, 1.0};
    doParticleMove(r, supplyControlVar({0, 0, 0}, {0, 0, 1.0}));
    CHECK(near(r.pose.theta, normalizeAngle(4.0)), "회전 누적+정규화");
}

// ── doExtraMove: 반폭 U(-0.5,+0.5) 산포, x·y 독립 ──────────────────────────────
static void testDoExtraMove()
{
    std::mt19937 rng(12345);
    const ExtraMoveParams e{0.040, 0.052, 1}; // 40mm / 3deg

    double sx = 0.0, sy = 0.0, max_abs = 0.0;
    int same_xy = 0;
    const int N = 20000;
    for (int i = 0; i < N; ++i)
    {
        Particle p{{0, 0, 0}, 1.0};
        doExtraMove(p, e, rng);
        sx += p.pose.x;
        sy += p.pose.y;
        max_abs = std::max(max_abs, std::max(std::fabs(p.pose.x), std::fabs(p.pose.y)));
        if (near(p.pose.x, p.pose.y))
            ++same_xy;
        CHECK(std::fabs(p.pose.x) <= e.radius * 0.5 + 1e-12, "x 반폭 초과");
        CHECK(std::fabs(p.pose.y) <= e.radius * 0.5 + 1e-12, "y 반폭 초과");
        CHECK(std::fabs(p.pose.theta) <= e.angle * 0.5 + 1e-12, "theta 반폭 초과");
    }
    // 평균 0 (대칭 균등) — 표본오차 여유를 두고 판정
    CHECK(std::fabs(sx / N) < 0.001 && std::fabs(sy / N) < 0.001, "산포 평균 0 근처");
    // x·y 가 같은 난수를 재사용하면 same_xy 가 N 이 된다(원본은 RangeRandom 을 두 번 호출).
    CHECK(same_xy < N / 100, "x·y 는 독립 난수여야 함");
    // 반폭에 실제로 근접하는 표본이 존재(스케일이 죽지 않았는지)
    CHECK(max_abs > e.radius * 0.45, "산포 스케일 소멸");
}

// ── selectExtraMove: 6모드 결정 트리 (원본 DoNormalUpdateAction) ───────────────
static void testSelectExtraMove()
{
    Mcl2dParams pr; // 배포 기본값: dist 20mm / angle 1deg / BPTT 0.8
    const double far_d = 0.05, near_d = 0.001;
    const double turn = 0.05, straight = 0.001; // rad (1deg=0.01745)
    const double low_w = 0.1, high_w = 0.9;

    // 모드 1: 많이 이동 + 회전 + 신뢰도 낮음 → 최대 산포(40mm, 3deg)
    {
        const ExtraMoveParams e = selectExtraMove(far_d, turn, low_w, pr);
        CHECK(e.mode == 1, "모드1 판정");
        CHECK(near(e.radius, pr.extra_move_radius) && near(e.angle, pr.extra_move_angle), "모드1 값");
    }
    // 모드 2: 많이 이동 + 회전 없음 → 40mm + 고정 2deg
    {
        const ExtraMoveParams e = selectExtraMove(far_d, straight, low_w, pr);
        CHECK(e.mode == 2, "모드2 판정");
        CHECK(near(e.radius, pr.extra_move_radius), "모드2 반경");
        CHECK(near(e.angle, 2.0 * M_PI / 180.0, 1e-12), "모드2 각도=고정 2deg");
    }
    // 모드 3: 미세 이동 + 회전 + 신뢰도 낮음 → 10mm, 3deg
    {
        const ExtraMoveParams e = selectExtraMove(near_d, turn, low_w, pr);
        CHECK(e.mode == 3, "모드3 판정");
        CHECK(near(e.radius, pr.move_radius) && near(e.angle, pr.extra_move_angle), "모드3 값");
    }
    // 모드 4: 미세 이동 + 회전 없음 → 저속 산포(10mm, 1deg) = 최소
    {
        const ExtraMoveParams e = selectExtraMove(near_d, straight, low_w, pr);
        CHECK(e.mode == 4, "모드4 판정");
        CHECK(near(e.radius, pr.low_speed_move_radius) && near(e.angle, pr.low_speed_move_angle), "모드4 값");
    }
    // 모드 5: 회전 중 + 신뢰도 높음 → 거리와 무관, ForceExtraMove=0 이면 10mm + 2deg
    {
        const ExtraMoveParams e1 = selectExtraMove(far_d, turn, high_w, pr);
        const ExtraMoveParams e2 = selectExtraMove(near_d, turn, high_w, pr);
        CHECK(e1.mode == 5 && e2.mode == 5, "모드5 판정(거리 무관)");
        CHECK(near(e1.radius, 0.010) && near(e1.angle, pr.force_extra_move_angle), "모드5 기본값");
        CHECK(near(e1.radius, e2.radius) && near(e1.angle, e2.angle), "모드5 는 거리에 불변");
    }
    // 모드 5 + ForceExtraMove: 파라미터 쌍으로 대체
    {
        Mcl2dParams f = pr;
        f.force_extra_move = true;
        f.force_extra_move_dist = 0.007;
        const ExtraMoveParams e = selectExtraMove(far_d, turn, high_w, f);
        CHECK(e.mode == 5 && near(e.radius, 0.007), "ForceExtraMove 값 대체");
    }
    // 임계 경계: dist 가 임계와 같으면 '멀다' 가 아니다(원본 ja/jbe 의미)
    {
        const ExtraMoveParams e = selectExtraMove(pr.extra_move_dist_threshold, straight, low_w, pr);
        CHECK(e.mode == 4, "dist==임계는 '멀다' 아님");
    }
    // 신뢰도 경계: w == BPTT 이면 '신뢰 높음'
    {
        const ExtraMoveParams e = selectExtraMove(near_d, turn, pr.best_particle_tolerant_threshold, pr);
        CHECK(e.mode == 5, "w==BPTT 는 신뢰 높음");
    }
}

int main()
{
    testSupplyControlVar();
    testDoParticleMove();
    testDoExtraMove();
    testSelectExtraMove();
    if (g_fail == 0)
        std::printf("[PASS] motion_model 단위 검증 통과 (supplyControlVar/doParticleMove/doExtraMove/selectExtraMove)\n");
    else
        std::printf("[FAIL] %d 건 실패\n", g_fail);
    return g_fail == 0 ? 0 : 1;
}
