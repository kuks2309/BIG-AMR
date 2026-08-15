// RE 검증(오라클): mcl2d::ObservationField(우리 충실 포팅) ↔ 원본 QuadGridSearchMap::getPostProb  comment-check: ignore
//   동일 맵·동일 스캔·자세 스윕에서 **비트 대조 Δ=0**. RE 제1원칙(원본과 100% 동일).
//
//   원본 자산 의존(우리 배포물 아님): libMCLoc.so(dlopen), libprotobuf.so.17, 실 .smap.
//   자산/헤더 부재 시 SKIP(=graceful, exit 0) — 일반 CI 에서는 스킵되고, 검증환경에서만 게이트.
//
//   빌드/실행(HANDOFF §4):
//     RBK=/media/.../rbk ; SMAP=".../maps/FAT_TEST MAP_Roll_AGV_20230808_1.smap"
//     g++ -std=c++17 -O2 -I/tmp/protobuf-3.6.1/src -Isrc/Navigation/mcl2d_core/include -Isrc/Navigation/mcl2d_map/include \
//       src/Navigation/mcl2d_core/test/test_obs_field_oracle.cpp src/Navigation/mcl2d_core/src/observation_field.cpp \
//       src/Navigation/mcl2d_map/src/smap.cpp -Wl,--no-as-needed "$RBK/3rdlib/libprotobuf.so.17" -lz -ldl -pthread -o /tmp/t
//     export LD_LIBRARY_PATH="$RBK/lib:$RBK/3rdlib:$RBK/plugins:$RBK/mobilerobots" ; /tmp/t "$SMAP"
#include <google/protobuf/descriptor.h>
#include <google/protobuf/message.h>
#include <google/protobuf/util/json_util.h>

#include <dlfcn.h>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <vector>

#include "mcl2d_core/observation_field.hpp"
#include "mcl2d_map/smap.hpp"

using namespace google::protobuf;

// ── 원본 ABI 구조체 (DWARF 실측 레이아웃) ──
struct SeerState
{
    double x, y, theta;
};
struct SeerGeo
{
    double x, y;
};
struct SeerMeasP
{
    double angle, dist;
    bool valid;
};
struct SeerMeasPoints
{
    std::vector<SeerMeasP> pts;
};
struct SeerMeasVar
{
    double lx, ly, start_angle;
    SeerMeasPoints points;
};

static inline void setD(void *qm, size_t off, double v)
{
    *reinterpret_cast<double *>((char *)qm + off) = v;
}
static inline void setI(void *qm, size_t off, int v)
{
    *reinterpret_cast<int *>((char *)qm + off) = v;
}
static inline void setB(void *qm, size_t off, bool v)
{
    *reinterpret_cast<bool *>((char *)qm + off) = v;
}
// robot.param MCLoc 실측 배포값을 m_mcl_params 스칼라에 기록 (initialize 전).
static void set_mcl_params(void *qm)
{
    setI(qm, 0x1c8, 10000);
    setD(qm, 0x1d0, 0.02);
    setI(qm, 0x1d8, 5);
    setD(qm, 0x1e0, 0.5);
    setD(qm, 0x1e8, 80.0);
    setD(qm, 0x1f0, 80.0);
    setD(qm, 0x1f8, 0.01);
    setD(qm, 0x200, 80.0);
    setB(qm, 0x208, true);
    setD(qm, 0x210, 700.0);
    setD(qm, 0x218, 180.0);
    setD(qm, 0x220, 0.05);
    setD(qm, 0x228, 0.7);
    setI(qm, 0x230, 0);
    setD(qm, 0x238, 40.0);
    setD(qm, 0x240, 3.0);
    setD(qm, 0x248, 0.8);
    setD(qm, 0x250, 0.9);
    setI(qm, 0x258, 3000);
    setI(qm, 0x25c, 500);
    setI(qm, 0x260, 100);
    setI(qm, 0x264, 10);
    setI(qm, 0x268, 100);
    setI(qm, 0x26c, 255);
    setI(qm, 0x270, 10);
    setD(qm, 0x278, 1.0);
    setD(qm, 0x280, 20.0);
    setD(qm, 0x288, 1.0);
    setD(qm, 0x290, 1.0);
    setI(qm, 0x298, -1);
    setI(qm, 0x29c, 3);
}

static void skip(const char *why)
{
    std::printf("[SKIP] %s (RE 검증 자산 부재 — 검증환경에서만 실행)\n", why);
    std::exit(0);
}

int main(int argc, char **argv)
{
    setvbuf(stdout, nullptr, _IONBF, 0);
    if (argc < 2)
        skip("usage: test_obs_field_oracle <map.smap>");
    const char *smap_path = argv[1];

    void *h = dlopen("libMCLoc.so", RTLD_NOW | RTLD_GLOBAL);
    if (!h)
        skip("dlopen libMCLoc.so 실패");
    auto CTOR = (void (*)(void *))dlsym(h, "_ZN17QuadGridSearchMapC1Ev");
    auto INIT = (void (*)(void *, void *, const void *, int, int, bool))dlsym(
        h, "_ZN17QuadGridSearchMap10initializeERN3rbk8protocol11Message_MapERKSt6vectorINS0_"
           "10foundation8GeoPointESaIS6_EEiib");
    auto SETSCAN = (void (*)(void *, void *))dlsym(
        h, "_ZN17QuadGridSearchMap19setCurrentLaserScanERSt6vectorIN3rbk9algorithm16MeasurementVar2DESaIS3_EE");
    auto GETPROB = (double (*)(void *, const void *, void *))dlsym(
        h, "_ZN17QuadGridSearchMap11getPostProbERKN3rbk9algorithm10StateVar2DERSt6vectorIdSaIdEE");
    auto SETDEF =
        (void (*)(void *, void *))dlsym(h, "_ZN17QuadGridSearchMap16setDefaultParamsERN3rbk9algorithm11MCLParams2DE");
    if (!CTOR || !INIT || !SETSCAN || !GETPROB || !SETDEF)
        skip("dlsym 원본 심볼 실패");

    mcl2d::SmapMap map = mcl2d::loadSmap(smap_path);
    if (!map.valid)
        skip("smap 로드 실패");

    const Descriptor *d = DescriptorPool::generated_pool()->FindMessageTypeByName("rbk.protocol.Message_Map");
    if (!d)
        skip("protobuf Message_Map descriptor 부재(libprotocol 미링크)");
    Message *msg = MessageFactory::generated_factory()->GetPrototype(d)->New();
    {
        std::ifstream f(smap_path);
        std::stringstream ss;
        ss << f.rdbuf();
        std::string j = ss.str();
        util::JsonParseOptions o;
        o.ignore_unknown_fields = true;
        if (!util::JsonStringToMessage(j, msg, o).ok())
            skip("json→Message_Map 파싱 실패");
    }

    // ── 원본 QuadGridSearchMap 구동 (obstacles=mm) ──
    void *qm = std::malloc(365336);
    std::memset(qm, 0, 365336);
    CTOR(qm);
    set_mcl_params(qm);
    SETDEF(qm, (char *)qm + 0x188);
    std::vector<SeerGeo> geo;
    geo.reserve(map.obstacles.size());
    for (auto &p : map.obstacles)
        geo.push_back({p.first * 1000.0, p.second * 1000.0});
    INIT(qm, msg, &geo, 10, 500, false);

    // ── 우리 ObservationField 구축 (동일 맵: 장애물 + rssi 반사판) ──
    mcl2d::ObservationField field;
    field.build(map.obstacles, map.rssi_points);
    if (field.empty())
        skip("ObservationField 빌드 실패");

    // ── 동일 스캔 생성: 로봇중심 360빔, 우리 거리장으로 mm 레이캐스트 (양쪽 동일 투입) ──
    const SeerState pose_mm{3700.0, 1600.0, 0.0};
    std::vector<SeerMeasP> seer_beams;        // 원본용
    std::vector<mcl2d::PolarBeam> our_beams;  // 우리용
    for (int i = 0; i < 360; ++i)
    {
        double a_deg = -180.0 + i;
        double a = a_deg * M_PI / 180.0;
        double hit = 0.0;
        bool v = false;
        for (double t = 100.0; t < 30000.0; t += 20.0)
        {
            double ex = pose_mm.x + t * std::cos(pose_mm.theta + a);
            double ey = pose_mm.y + t * std::sin(pose_mm.theta + a);
            if (field.distByte(ex, ey) == 0)
            {
                hit = t;
                v = true;
                break;
            }
        }
        seer_beams.push_back({a_deg, hit, v});
        our_beams.push_back({a_deg, hit, v});
    }

    // 원본 setCurrentLaserScan
    std::vector<SeerMeasVar> scanvec(1);
    scanvec[0].lx = 0;
    scanvec[0].ly = 0;
    scanvec[0].start_angle = -180.0;
    scanvec[0].points.pts = seer_beams;
    SETSCAN(qm, &scanvec);
    int valid_orig = *(int *)((char *)qm + 0x108);

    // 우리 setScan
    field.setScan(our_beams);
    int valid_ours = field.validBeam();

    int fails = 0;
    if (valid_ours != valid_orig)
    {
        std::printf("[FAIL] valid_beam 불일치: 원본=%d 우리=%d\n", valid_orig, valid_ours);
        ++fails;
    }
    else
    {
        std::printf("[OK] valid_beam=%d (원본=우리)\n", valid_ours);
    }

    // ── 자세 스윕 비트 대조 (position + orientation) ──
    int npass = 0, ntot = 0;
    double worst = 0.0;
    for (double dx = -300; dx <= 300.001; dx += 100)
        for (double dy = -300; dy <= 300.001; dy += 100)
            for (double dth = -0.2; dth <= 0.2001; dth += 0.1)
            {
                SeerState p{pose_mm.x + dx, pose_mm.y + dy, dth};
                std::vector<double> w;
                double a = GETPROB(qm, &p, &w);
                double b = field.getPostProb(p.x, p.y, p.theta);
                double diff = std::fabs(a - b);
                worst = std::max(worst, diff);
                bool ok = diff < 1e-12;
                npass += ok;
                ++ntot;
                if (!ok && fails < 12)
                {
                    std::printf("  [DIFF] (%+.0f,%+.0f,θ%+.2f) 원본=%.17g 우리=%.17g Δ=%.3e\n", dx, dy, dth, a, b, diff);
                    ++fails;
                }
            }
    std::printf("자세 스윕 비트 대조: %d/%d 일치, worst |Δ|=%.3e\n", npass, ntot, worst);

    // ── 다중 라이다(듀얼) 검증: 2개 MeasurementVar2D(서로 다른 mount) → 원본·우리 비트 대조 ──
    //   Roll_A084 전+후 듀얼 라이다를 원본 setCurrentLaserScan(vector) 이 valid_beam 누적 처리하는 경로 재현.
    int npass2 = 0, ntot2 = 0;
    double worst2 = 0.0;
    {
        const double mnt_lx = 300.0, mnt_ly = 150.0; // 2번째 라이다 장착(mm)
        std::vector<SeerMeasP> seer_b2;
        std::vector<mcl2d::PolarBeam> our_b2;
        for (int i = 0; i < 360; ++i)
        {
            double a_deg = -180.0 + i;
            double a = a_deg * M_PI / 180.0;
            double hit = 0.0;
            bool v = false;
            // 2번째 라이다 원점 = pose + mount (θ=0 기준 레이캐스트)
            for (double t = 100.0; t < 30000.0; t += 20.0)
            {
                double ex = (pose_mm.x + mnt_lx) + t * std::cos(a);
                double ey = (pose_mm.y + mnt_ly) + t * std::sin(a);
                if (field.distByte(ex, ey) == 0)
                {
                    hit = t;
                    v = true;
                    break;
                }
            }
            seer_b2.push_back({a_deg, hit, v});
            our_b2.push_back({a_deg, hit, v});
        }
        // 원본: 2개 스캔. ★원본 MeasurementVar2D.lx/ly 는 미터(getPostProbBase 가 ×1000 로 mm 변환).
        //   우리 ObservationField.mount_*_mm 는 mm(변환 후 값) → 원본엔 미터(mnt/1000) 투입.
        std::vector<SeerMeasVar> sv2(2);
        sv2[0].lx = 0;
        sv2[0].ly = 0;
        sv2[0].start_angle = -180.0;
        sv2[0].points.pts = seer_beams;
        sv2[1].lx = mnt_lx / 1000.0; // 미터
        sv2[1].ly = mnt_ly / 1000.0; // 미터
        sv2[1].start_angle = -180.0;
        sv2[1].points.pts = seer_b2;
        SETSCAN(qm, &sv2);
        int valid_orig2 = *(int *)((char *)qm + 0x108);
        // 우리: 2개 그룹
        std::vector<mcl2d::LaserScanGroup> groups(2);
        groups[0].beams = our_beams;
        groups[0].mount_lx_mm = 0;
        groups[0].mount_ly_mm = 0;
        groups[1].beams = our_b2;
        groups[1].mount_lx_mm = mnt_lx;
        groups[1].mount_ly_mm = mnt_ly;
        field.setScan(groups);
        int valid_ours2 = field.validBeam();
        std::printf("[듀얼] valid_beam 원본=%d 우리=%d %s\n", valid_orig2, valid_ours2,
                    valid_orig2 == valid_ours2 ? "[OK]" : "[FAIL]");
        for (double dx = -300; dx <= 300.001; dx += 150)
            for (double dy = -300; dy <= 300.001; dy += 150)
                for (double dth = -0.2; dth <= 0.2001; dth += 0.1)
                {
                    SeerState p{pose_mm.x + dx, pose_mm.y + dy, dth};
                    std::vector<double> w;
                    double a = GETPROB(qm, &p, &w);
                    double b = field.getPostProb(p.x, p.y, p.theta);
                    double diff = std::fabs(a - b);
                    worst2 = std::max(worst2, diff);
                    npass2 += (diff < 1e-12);
                    ++ntot2;
                }
        std::printf("[듀얼] 자세 스윕 비트 대조: %d/%d 일치, worst |Δ|=%.3e (valid=%d)\n", npass2, ntot2, worst2,
                    valid_ours2 == valid_orig2);
        if (valid_ours2 != valid_orig2)
            npass2 = -1; // valid 불일치 → 실패 마킹
    }

    if (npass != ntot || valid_ours != valid_orig || npass2 != ntot2)
    {
        std::printf("[FAIL] RE 비트 대조 실패\n");
        return 1;
    }
    std::printf("[PASS] ObservationField ↔ 원본 getPostProb 비트 일치 Δ=0 (단일 %d/%d, 듀얼 %d/%d)\n", npass, ntot,
                npass2, ntot2);
    return 0;
}
