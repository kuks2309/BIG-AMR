// RE 오라클 — 원본 libMCLoc.so 의 MCLMotionModel2D 결정론 함수를 dlopen 으로 직접 구동해
//   우리 재구현(mcl2d::supplyControlVar / doParticleMove)과 **비트 대조**한다.
//   방법: 원본이 실제로 받는 입력을 독립적으로 정의해 양쪽에 투입하고 결과를 비트로 대조한다.
//
// 원본 구조체 레이아웃은 전부 디스어셈블로 확인한 것이다:
//   ControlVar2D  : x@0 y@8 angle@0x10 is_stop@0x18 timestamp@0x20  (DoMoveAction 3d7c64~3d7cda)
//   MCLParticle2D : weight@0 log_weight@8 x@0x10 y@0x18 theta@0x20  (doParticleMoveAction 33cc30~33cc88)
//   MCLMotionModel2D 멤버: [0]=초기화 플래그 · 0x90=dθ · 0x98=trans · 0xa0=direction ·
//                          0xa8/0xb0=노이즈 스케일(원본 호출지가 d=0 이라 항상 0)
// 빌드: g++ -std=c++17 -O2 -I<core include> test_motion_oracle.cpp motion_model.cpp -ldl -o oracle
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <random>
#include <string>
#include <vector>

#include "mcl2d_core/motion_model.hpp"

namespace
{

struct OrigControlVar2D
{
    double x = 0, y = 0, angle = 0;
    bool is_stop = false;
    double timestamp = 0;
};
static_assert(sizeof(OrigControlVar2D) >= 40, "ControlVar2D 레이아웃");

struct OrigParticle
{
    double weight = 0, log_weight = 0, x = 0, y = 0, theta = 0;
};

constexpr std::size_t kModelSize = 0x800; // 실제 크기 미상 — 넉넉한 제로 버퍼
constexpr std::size_t kOffFlag = 0x00;
constexpr std::size_t kOffDTheta = 0x90;
constexpr std::size_t kOffTrans = 0x98;
constexpr std::size_t kOffDir = 0xa0;
constexpr std::size_t kOffNoiseT = 0xa8;
constexpr std::size_t kOffNoiseR = 0xb0;

using FnSupply = void (*)(void *, const OrigControlVar2D *, double);
using FnMove = void (*)(void *, OrigParticle *);

double &member(void *m, std::size_t off)
{
    return *reinterpret_cast<double *>(static_cast<char *>(m) + off);
}

// 비트 동일성 — 부호·NaN 까지 그대로 비교한다.
bool bitEqual(double a, double b)
{
    std::uint64_t ua, ub;
    std::memcpy(&ua, &a, 8);
    std::memcpy(&ub, &b, 8);
    return ua == ub;
}

int ulpDiff(double a, double b)
{
    std::int64_t ia, ib;
    std::memcpy(&ia, &a, 8);
    std::memcpy(&ib, &b, 8);
    if (ia < 0)
        ia = INT64_MIN - ia;
    if (ib < 0)
        ib = INT64_MIN - ib;
    const std::int64_t d = ia > ib ? ia - ib : ib - ia;
    return d > 1000000 ? 1000000 : static_cast<int>(d);
}

int g_fail = 0, g_cmp = 0, g_maxulp = 0;

void compare(const char *what, double orig, double ours)
{
    ++g_cmp;
    if (bitEqual(orig, ours))
        return;
    const int u = ulpDiff(orig, ours);
    if (u > g_maxulp)
        g_maxulp = u;
    if (u > 0)
    {
        ++g_fail;
        if (g_fail <= 10)
            std::printf("[DIFF] %-12s orig=%.17g ours=%.17g ulp=%d\n", what, orig, ours, u);
    }
}

} // namespace

int main(int argc, char **argv)
{
    const char *so = (argc > 1) ? argv[1] : "libMCLoc.so";
    void *h = dlopen(so, RTLD_NOW | RTLD_LOCAL);
    if (!h)
    {
        std::printf("[SKIP] dlopen 실패: %s\n", dlerror());
        return 77; // 자산 부재 — 검증 환경 전용
    }
    auto supply = reinterpret_cast<FnSupply>(
        dlsym(h, "_ZN3rbk9algorithm16MCLMotionModel2D16supplyControlVarERKNS0_12ControlVar2DEd"));
    auto move =
        reinterpret_cast<FnMove>(dlsym(h, "_ZN3rbk9algorithm16MCLMotionModel2D20doParticleMoveActionERNS0_13MCLParticle2DE"));
    if (!supply || !move)
    {
        std::printf("[FAIL] 심볼 해석 실패 supply=%p move=%p\n", (void *)supply, (void *)move);
        return 1;
    }

    std::mt19937 rng(20260806);
    std::uniform_real_distribution<double> pos(-20.0, 20.0);
    std::uniform_real_distribution<double> ang(-M_PI, M_PI);
    std::uniform_real_distribution<double> small(-0.05, 0.05);

    std::vector<char> buf(kModelSize);

    // ── 대조 1: supplyControlVar — 오도 2시점 → (trans, direction, dtheta) ──────────
    int n1 = 0;
    for (int i = 0; i < 300; ++i)
    {
        mcl2d::Pose2D prev{}, cur{};
        if (i % 5 == 0) // 경계: 제자리(증분 0)
        {
            prev = {pos(rng), pos(rng), ang(rng)};
            cur = prev;
        }
        else if (i % 5 == 1) // 경계: 회전만
        {
            prev = {pos(rng), pos(rng), ang(rng)};
            cur = {prev.x, prev.y, ang(rng)};
        }
        else if (i % 5 == 2) // 미세 증분
        {
            prev = {pos(rng), pos(rng), ang(rng)};
            cur = {prev.x + small(rng), prev.y + small(rng), prev.theta + small(rng)};
        }
        else // 임의 큰 증분(각도 wrap 포함)
        {
            prev = {pos(rng), pos(rng), ang(rng)};
            cur = {pos(rng), pos(rng), ang(rng)};
        }

        std::memset(buf.data(), 0, buf.size());
        // 1st call: 플래그 0 → 원본의 "첫 샘플" 경로가 prev 를 내부에 적재
        OrigControlVar2D p{prev.x, prev.y, prev.theta, false, 1000.0};
        supply(buf.data(), &p, 0.0);
        // 2nd call: 플래그 1 → 계산 경로 (timestamp 증가시켜 로그 분기 회피)
        buf[kOffFlag] = 1;
        OrigControlVar2D c{cur.x, cur.y, cur.theta, false, 1000.1};
        supply(buf.data(), &c, 0.0);

        const mcl2d::ControlIncrement2D ours = mcl2d::supplyControlVar(prev, cur);
        const int before = g_fail;
        compare("trans", member(buf.data(), kOffTrans), ours.trans);
        compare("direction", member(buf.data(), kOffDir), ours.direction);
        compare("dtheta", member(buf.data(), kOffDTheta), ours.dtheta);
        if (g_fail > before && g_fail <= 12)
        {
            // 3자 대조: 하네스에서 같은 식을 직접 계산해 우리 함수 결과와 가른다
            const double ddx = cur.x - prev.x, ddy = cur.y - prev.y;
            const double kcs = std::cos(prev.theta), ksn = std::sin(prev.theta);
            const double xb = ddx * kcs + ddy * ksn, yb = ddy * kcs - ddx * ksn;
            std::printf("       ↳ 표본 %d prev=(%a, %a, %a) cur=(%a, %a, %a)\n"
                        "         하네스직접 trans=%.17g dir=%.17g | 우리함수 trans=%.17g dir=%.17g | 원본 trans=%.17g\n",
                        i, prev.x, prev.y, prev.theta, cur.x, cur.y, cur.theta,
                        std::sqrt(xb * xb + yb * yb), std::atan2(yb, xb), ours.trans, ours.direction,
                        member(buf.data(), kOffTrans));
        }
        ++n1;
    }

    // ── 대조 2: doParticleMoveAction — 증분을 직접 주입하고 파티클 이동 결과 대조 ──
    int n2 = 0;
    for (int i = 0; i < 300; ++i)
    {
        mcl2d::ControlIncrement2D c{};
        c.trans = (i % 7 == 0) ? 0.0 : std::fabs(pos(rng)) * 0.1;
        c.direction = ang(rng);
        c.dtheta = (i % 11 == 0) ? 0.0 : ang(rng);

        std::memset(buf.data(), 0, buf.size());
        buf[kOffFlag] = 1;
        member(buf.data(), kOffTrans) = c.trans;
        member(buf.data(), kOffDir) = c.direction;
        member(buf.data(), kOffDTheta) = c.dtheta;
        member(buf.data(), kOffNoiseT) = 0.0; // 원본 호출지가 d=0 이라 노이즈 스케일 0 (실측)
        member(buf.data(), kOffNoiseR) = 0.0;

        const mcl2d::Pose2D start{pos(rng), pos(rng), ang(rng)};
        OrigParticle op{1.0, 0.0, start.x, start.y, start.theta};
        move(buf.data(), &op);

        mcl2d::Particle ours{{start.x, start.y, start.theta}, 1.0};
        mcl2d::doParticleMove(ours, c);

        compare("particle.x", op.x, ours.pose.x);
        compare("particle.y", op.y, ours.pose.y);
        compare("particle.t", op.theta, ours.pose.theta);
        ++n2;
    }

    std::printf("표본: supplyControlVar %d · doParticleMove %d · 비교 %d 값\n", n1, n2, g_cmp);
    if (g_fail == 0)
        std::printf("[PASS] 원본 대조 비트 일치 — 불일치 0 (max ulp 0)\n");
    else
        std::printf("[FAIL] 불일치 %d / %d (max ulp %d)\n", g_fail, g_cmp, g_maxulp);
    dlclose(h);
    return g_fail == 0 ? 0 : 1;
}
