// A1 검증: 재위치추정(relocalization) 수렴 + 슬립(skid) 감지.
#include <cassert>
#include <cmath>
#include <cstdio>
#include <vector>

#include "mcl2d_core/particle_filter.hpp"
#include "mcl2d_core/skid_detector.hpp"

using namespace mcl2d;

static std::vector<std::pair<double, double>> makeRoom(double W, double H)
{
    std::vector<std::pair<double, double>> obs;
    const double s = 0.05;
    for (double x = 0; x <= W; x += s)
    {
        obs.emplace_back(x, 0.0);
        obs.emplace_back(x, H);
    }
    for (double y = 0; y <= H; y += s)
    {
        obs.emplace_back(0.0, y);
        obs.emplace_back(W, y);
    }
    // 대칭성 파괴용 내부 기둥 (한쪽에만) — 재위치추정 유일해 보장
    for (double x = 2.0; x <= 3.0; x += s)
    {
        obs.emplace_back(x, 2.0);
        obs.emplace_back(x, 3.0);
    }
    for (double y = 2.0; y <= 3.0; y += s)
    {
        obs.emplace_back(2.0, y);
        obs.emplace_back(3.0, y);
    }
    return obs;
}

// 방 + 내부 기둥 레이캐스트 스캔 합성
static LaserScan simScan(const Pose2D &t, const LaserMount &m, double W, double H)
{
    LaserScan s;
    s.angle_min = -M_PI;
    s.angle_increment = M_PI / 180.0;
    s.range_min = 0.05;
    s.range_max = 30.0;
    const double lx = t.x + m.x * std::cos(t.theta) - m.y * std::sin(t.theta);
    const double ly = t.y + m.x * std::sin(t.theta) + m.y * std::cos(t.theta);
    const double lth = t.theta + m.yaw;
    for (int i = 0; i < 360; ++i)
    {
        const double a = lth + s.angle_min + i * s.angle_increment;
        const double ca = std::cos(a), sa = std::sin(a);
        double best = s.range_max;
        if (ca > 1e-9)
            best = std::min(best, (W - lx) / ca);
        if (ca < -1e-9)
            best = std::min(best, (0.0 - lx) / ca);
        if (sa > 1e-9)
            best = std::min(best, (H - ly) / sa);
        if (sa < -1e-9)
            best = std::min(best, (0.0 - ly) / sa);
        // 내부 기둥 [2,3]x[2,3] 4변과의 교차도 근사 반영 (앞면만)
        auto hitSeg = [&](double t0) {
            double px = lx + t0 * ca, py = ly + t0 * sa;
            return px >= 1.99 && px <= 3.01 && py >= 1.99 && py <= 3.01;
        };
        for (double d = 0.1; d < best; d += 0.05)
        {
            if (hitSeg(d))
            {
                best = d;
                break;
            }
        }
        s.ranges.push_back(static_cast<float>(best));
    }
    return s;
}

static void testReloc()
{
    const double W = 10.0, H = 6.0;
    ObservationField field;
    field.build(makeRoom(W, H), {});
    Mcl2dParams p;
    p.max_particle_number = 6000;
    p.min_particle_number = 800;
    p.beams_used = 360;
    p.reloc_success_threshold = 0.08; // 희소맵 픽스처: 수렴 시 L~0.11, 이탈 시 <0.06 (측정 기반)
    LaserMount mount;
    ParticleFilter2D pf(p, std::move(field), mount, /*seed=*/3);

    Pose2D truth{6.5, 4.0, 0.7}; // 진짜 자세(비대칭 위치)
    std::vector<LaserScan> scans = {simScan(truth, mount, W, H)};
    // 위치 손실(중등도 오차) → 대략 위치 주변 영역에서 재위치추정 (반경 2m, 헤딩 미지 ±π)
    bool ok = pf.relocalize(Pose2D{5.5, 3.2, 0.0}, /*radius=*/2.0, /*angle=*/M_PI, scans);
    Pose2D est = pf.estimate();
    const double err = std::hypot(est.x - truth.x, est.y - truth.y);
    std::printf("[reloc] ok=%d truth=(%.2f,%.2f,%.2f) est=(%.2f,%.2f,%.2f) err=%.3f\n", ok, truth.x, truth.y,
                truth.theta, est.x, est.y, est.theta, err);
    assert(ok && "reloc 실패 보고");
    assert(err < 0.5 && "reloc 수렴 오차 과다");
    std::printf("[PASS] 재위치추정 수렴\n");
}

static void testSkid()
{
    Mcl2dParams p; // check_distance=1.0, check_angle=30deg, ratio=2.0, recover_time=1.0
    SkidDetector sd(p);
    // 정상: 휠·레이저 이동 일치
    assert(sd.update(0.5, 0.05, 0.5, 0.05, false, 0.1) == LocReportState::Normal);
    // 병진 불일치(큰 이동 + 2배 초과): 휠 2.0m 이동했는데 레이저는 0.3m → skid
    assert(sd.update(2.0, 0.0, 0.3, 0.0, false, 0.1) == LocReportState::Skidding);
    assert(sd.skidding());
    // 복구 전(이동 중)엔 유지
    assert(sd.update(0.0, 0.0, 0.0, 0.0, false, 0.1) == LocReportState::Skidding);
    // 정지 + recover_time(1.0s) 경과 → 복구
    sd.update(0.0, 0.0, 0.0, 0.0, true, 0.6);
    LocReportState st = sd.update(0.0, 0.0, 0.0, 0.0, true, 0.6); // 누적 1.2s > 1.0
    assert(st == LocReportState::Normal && !sd.skidding());
    // 회전 불일치: 휠 0°인데 레이저 40° → skid
    assert(sd.update(0.1, 0.0, 0.1, 0.70, false, 0.1) == LocReportState::Skidding);
    std::printf("[PASS] 슬립 감지·복구\n");
}

int main()
{
    setvbuf(stdout, nullptr, _IONBF, 0); // assert 전 출력 보장
    testReloc();
    testSkid();
    std::printf("[ALL PASS] A1 (reloc + skid)\n");
    return 0;
}
