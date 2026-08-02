#include "mcl2d_core/particle_filter.hpp"

#include <algorithm>
#include <cmath>
#include <set>
#include <tuple>

#include "mcl2d_core/motion_model.hpp"

namespace mcl2d
{

ParticleFilter2D::ParticleFilter2D(const Mcl2dParams &params, ObservationField field, LaserMount mount,
                                   std::uint32_t seed)
    : params_(params), field_(std::move(field)), mounts_{mount}, rng_(seed)
{
}

ParticleFilter2D::ParticleFilter2D(const Mcl2dParams &params, ObservationField field, std::vector<LaserMount> mounts,
                                   std::uint32_t seed)
    : params_(params), field_(std::move(field)), mounts_(std::move(mounts)), rng_(seed)
{
    if (mounts_.empty())
        mounts_.emplace_back();
}

// ROS 프레임 스캔(rad·m) → 원본 프레임 그룹(도·mm)으로 변환해 field_.setScan.
//   beam.angle_deg = (scan_angle + mount.yaw)·180/π (로봇좌표), dist_mm = range·1000,
//   mount_*_mm = mount.xy·1000. is_valid = 실제 반사(range_min~range_max 내). scan 당 라이다 1대.
void ParticleFilter2D::applyScan(const std::vector<LaserScan> &scans)
{
    const std::size_t k = std::min(scans.size(), mounts_.size());
    std::vector<LaserScanGroup> groups;
    groups.reserve(k);
    for (std::size_t li = 0; li < k; ++li)
    {
        const LaserScan &s = scans[li];
        const LaserMount &m = mounts_[li];
        LaserScanGroup g;
        g.mount_lx_mm = m.x * 1000.0;
        g.mount_ly_mm = m.y * 1000.0;
        const int n = static_cast<int>(s.ranges.size());
        g.beams.reserve(static_cast<std::size_t>(n));
        for (int i = 0; i < n; ++i)
        {
            const double r = s.ranges[static_cast<std::size_t>(i)];
            const double ang = s.angle_min + i * s.angle_increment + m.yaw;
            const bool valid = (r >= s.range_min) && (s.range_max <= 0.0 || r < s.range_max);
            g.beams.push_back(PolarBeam{ang * 180.0 / M_PI, r * 1000.0, valid});
        }
        groups.push_back(std::move(g));
    }
    field_.setScan(std::move(groups));
}

double ParticleFilter2D::likelihoodAt(const Pose2D &pose) const
{
    return field_.getPostProb(pose.x * 1000.0, pose.y * 1000.0, pose.theta);
}

void ParticleFilter2D::initialize(const Pose2D &mean)
{
    const int n = std::max(1, params_.init_particle_number);
    particles_.assign(static_cast<std::size_t>(n), Particle{});
    std::uniform_real_distribution<double> u01(0.0, 1.0);
    std::uniform_real_distribution<double> uang(0.0, 2.0 * M_PI);
    std::uniform_real_distribution<double> uth(-params_.init_angle_scatter, params_.init_angle_scatter);
    for (auto &p : particles_)
    {
        const double r = u01(rng_) * params_.init_dist_scatter;
        const double a = uang(rng_);
        p.pose.x = mean.x + r * std::cos(a);
        p.pose.y = mean.y + r * std::sin(a);
        p.pose.theta = normalizeAngle(mean.theta + uth(rng_));
        p.weight = 1.0 / n;
    }
}

void ParticleFilter2D::initializeInRegion(const Pose2D &center, double half_extent, double angle_range)
{
    const int n = std::max(1, params_.max_particle_number);
    particles_.assign(static_cast<std::size_t>(n), Particle{});
    std::uniform_real_distribution<double> uxy(-half_extent, half_extent);
    std::uniform_real_distribution<double> uth(-angle_range, angle_range);
    for (auto &p : particles_)
    {
        p.pose.x = center.x + uxy(rng_);
        p.pose.y = center.y + uxy(rng_);
        p.pose.theta = normalizeAngle(center.theta + uth(rng_));
        p.weight = 1.0 / n;
    }
}

bool ParticleFilter2D::relocalize(const Pose2D &center, double radius, double angle_range,
                                  const std::vector<LaserScan> &scans)
{
    if (field_.empty())
        return false;
    initializeInRegion(center, radius, angle_range);

    const int max_iter = std::max(1, params_.reloc_max_iterations);
    for (int counter = 0; counter < max_iter; ++counter)
    {
        // 담금질(annealing) 스프레드: 초기 넓게 → 0으로 수축(반복 진행할수록 탐색반경 축소).
        // ※Seer 원시식 (max-counter)/100000×length(mm)은 그들 내부 스케일(mm/가중치) — 우리
        //   우도 스케일에 맞춰 radius 기준 수축으로 대응(RE 백로그: 원시 상수 1:1 미재현).
        const double frac = static_cast<double>(max_iter - counter) / max_iter; // 1 → ~0
        const double spread = radius * frac * 0.15;
        const double ang_spread = angle_range * frac * 0.1;
        std::uniform_real_distribution<double> u01(0.0, 1.0);
        std::uniform_real_distribution<double> uang(0.0, 2.0 * M_PI);
        std::uniform_real_distribution<double> uth(-ang_spread, ang_spread);
        for (auto &p : particles_)
        {
            const double r = u01(rng_) * spread;
            const double a = uang(rng_);
            p.pose.x += r * std::cos(a);
            p.pose.y += r * std::sin(a);
            p.pose.theta = normalizeAngle(p.pose.theta + uth(rng_));
        }
        updateWeights(scans); // 측정 갱신 (재추정 PDF는 RE 백로그 — 정상 PDF로 근사)
        // 수렴 판정: 현재 추정 자세의 우도 > 임계 → 조기 종료. (updateWeights 가 setScan 완료.)
        if (likelihoodAt(estimate()) > params_.reloc_success_threshold)
        {
            resample();
            break;
        }
        resample();
    }

    // 최종 성공검증: 추정 자세의 정상 PDF 우도 > 임계 (Seer 이중 게이팅).
    const double final_lik = likelihoodAt(estimate());
    return final_lik > params_.reloc_success_threshold;
}

void ParticleFilter2D::predict(const Pose2D &prev_odom, const Pose2D &cur_odom)
{
    const ControlIncrement2D c = supplyControlVar(prev_odom, cur_odom);
    for (auto &p : particles_)
        doParticleMove(p, c);
}

void ParticleFilter2D::extraMove(const ExtraMoveParams &e)
{
    for (auto &p : particles_)
        doExtraMove(p, e, rng_);
}

bool ParticleFilter2D::updateWeights(const LaserScan &scan)
{
    return updateWeights(std::vector<LaserScan>{scan});
}

bool ParticleFilter2D::updateWeights(const std::vector<LaserScan> &scans)
{
    if (particles_.empty())
        return false;
    applyScan(scans); // 스캔→그룹 변환 후 field_.setScan (파티클 무관, 1회)
    double sum = 0.0;
    for (auto &p : particles_)
    {
        p.weight = likelihoodAt(p.pose);
        sum += p.weight;
    }
    if (sum <= 0.0)
    {
        // 전 입자 우도 0 — 균등으로 두고 실패 보고(상위에서 reloc 판단).
        const double w = 1.0 / particles_.size();
        for (auto &p : particles_)
            p.weight = w;
        mean_weight_ = 0.0;
        return false;
    }
    mean_weight_ = sum / particles_.size();
    for (auto &p : particles_)
        p.weight /= sum; // 정규화 (합=1)
    return true;
}

int ParticleFilter2D::computeSampleNumber() const
{
    // 점유된 (x,y,theta) bin 수 k → n = k * factor, clamp[min,max] (Seer 실측)
    const double xy = std::max(1e-6, params_.adaptive_xy_step);
    const double abin = std::max(1e-6, params_.adaptive_angle_bin_deg * M_PI / 180.0);
    std::set<std::tuple<int, int, int>> bins;
    for (const auto &p : particles_)
    {
        bins.emplace(static_cast<int>(std::floor(p.pose.x / xy)), static_cast<int>(std::floor(p.pose.y / xy)),
                     static_cast<int>(std::floor(normalizeAngle(p.pose.theta) / abin)));
    }
    int n = static_cast<int>(std::lround(bins.size() * params_.adaptive_sample_factor));
    n = std::max(params_.min_particle_number, std::min(params_.max_particle_number, n));
    return n;
}

void ParticleFilter2D::resample()
{
    if (particles_.empty())
        return;
    const int m = computeSampleNumber();

    // 누적분포(CDF)
    std::vector<double> cdf(particles_.size());
    double acc = 0.0;
    for (std::size_t i = 0; i < particles_.size(); ++i)
    {
        acc += particles_[i].weight;
        cdf[i] = acc;
    }
    if (acc <= 0.0)
        return;

    // systematic: 단일 난수 u0 ∈ [0, 1/m) + 균등 stride 1/m (Seer: twist 1회 + stride)
    std::uniform_real_distribution<double> u(0.0, 1.0 / m);
    const double u0 = u(rng_);
    std::vector<Particle> next;
    next.reserve(static_cast<std::size_t>(m));
    std::size_t idx = 0;
    for (int j = 0; j < m; ++j)
    {
        const double thresh = (u0 + static_cast<double>(j) / m) * acc; // cdf 는 합=acc 기준
        while (idx + 1 < cdf.size() && cdf[idx] < thresh)
            ++idx;
        Particle p = particles_[idx];
        p.weight = 1.0 / m;
        next.push_back(p);
    }
    particles_.swap(next);
}

Pose2D ParticleFilter2D::estimate() const
{
    Pose2D est;
    if (particles_.empty())
        return est;
    double sw = 0.0, sx = 0.0, sy = 0.0, ss = 0.0, sc = 0.0;
    for (const auto &p : particles_)
    {
        sw += p.weight;
        sx += p.weight * p.pose.x;
        sy += p.weight * p.pose.y;
        ss += p.weight * std::sin(p.pose.theta);
        sc += p.weight * std::cos(p.pose.theta);
    }
    if (sw <= 0.0)
        return est;
    est.x = sx / sw;
    est.y = sy / sw;
    // 원형 평균. ★원본 getTheMeanParicle은 atan2f(float 단정밀도) 사용 — RE 제1원칙(원본
    //   100% 동일)에 따라 double atan2가 아닌 float atan2f로 맞춘다(오라클 비트 대조 확인).
    est.theta = ::atan2f(static_cast<float>(ss), static_cast<float>(sc));
    return est;
}

Pose2D ParticleFilter2D::step(const Pose2D &prev_odom, const Pose2D &cur_odom, const LaserScan &scan)
{
    return step(prev_odom, cur_odom, std::vector<LaserScan>{scan});
}

Pose2D ParticleFilter2D::step(const Pose2D &prev_odom, const Pose2D &cur_odom, const std::vector<LaserScan> &scans)
{
    // 원본(MCLoc) 순서: 새 스캔 적용 → **직전 추정 자세의 우도**로 산포 모드 선택 →
    //   kMove(결정론) → kExtraMove(산포) → 우도갱신 → 추정 → 리샘플.
    //   우도를 먼저 구하는 이유: 모드 판정이 "지금 얼마나 믿을 만한가"를 입력으로 쓰기 때문.
    applyScan(scans); // updateWeights 가 한 번 더 부르지만 비용은 빔 수 선형(파티클 루프 대비 무시 가능)
    const ControlIncrement2D c = supplyControlVar(prev_odom, cur_odom);
    const ExtraMoveParams e = selectExtraMove(c.trans, c.dtheta, likelihoodAt(estimate()), params_);
    predict(prev_odom, cur_odom);
    extraMove(e);
    updateWeights(scans);
    Pose2D est = estimate();
    resample();
    return est;
}

} // namespace mcl2d
