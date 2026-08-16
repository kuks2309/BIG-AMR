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

// 스캔을 우도장이 쓰는 프레임으로 옮긴다. 입력 rad·m → 우도장 도·mm.
//   beam.angle_deg = (스캔각 + mount.yaw) 를 도로 환산한 **로봇좌표** 각이고, 거리·장착 좌표는 mm 다.
//   is_valid 는 range_min~range_max 안에 든 실제 반사만 참 — 범위 밖 값은 '무한' 이 아니라 무효다.
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
        // 담금질 스프레드 — 반복이 진행될수록 탐색 반경을 0 으로 좁힌다.
        // ⚠ 원본 식은 내부 mm·가중치 스케일을 전제로 해서 상수를 1:1 로 옮기지 못했다.
        //   여기서는 같은 '넓게 시작해 좁힌다' 성질만 radius 기준으로 재현한다(수치 동치 아님).
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
        // 조기 종료 — 추정 자세의 우도가 임계를 넘으면 남은 반복은 시간 낭비다.
        if (likelihoodAt(estimate()) > params_.reloc_success_threshold)
        {
            resample();
            break;
        }
        resample();
    }

    // 조기 종료했더라도 마지막에 한 번 더 본다 — 담금질 도중의 우도는 좁힌 산포에 기댄 값이라
    //   그것만으로 성공을 선언하면 실제로는 어긋난 자세를 통과시킬 수 있다.
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
        // 전 입자 우도 0. 정규화하면 0 나눗셈이므로 가중치를 균등으로 두고 실패를 알린다 —
        //   재위치추정 여부는 상위가 정한다.
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
    // 점유 bin 수가 곧 '퍼진 정도'다. 퍼져 있으면 표본을 늘리고 수렴하면 줄인다.
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

    // systematic 리샘플 — 난수를 m 번이 아니라 **한 번만** 뽑고 1/m 간격으로 훑는다.
    //   표본 분산이 다항 리샘플보다 작고, 원본도 같은 방식이다.
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
    // 각도는 원형 평균으로 낸다(단순 산술평균은 ±π 경계에서 접힌다).
    // atan2f 를 쓰는 것은 실수가 아니다 — 원본이 **단정밀도** atan2f 를 쓰므로 double 로 바꾸면
    //   결과가 원본과 갈린다. 정밀도를 올리지 말 것.
    est.theta = ::atan2f(static_cast<float>(ss), static_cast<float>(sc));
    return est;
}

Pose2D ParticleFilter2D::step(const Pose2D &prev_odom, const Pose2D &cur_odom, const LaserScan &scan)
{
    return step(prev_odom, cur_odom, std::vector<LaserScan>{scan});
}

Pose2D ParticleFilter2D::step(const Pose2D &prev_odom, const Pose2D &cur_odom, const std::vector<LaserScan> &scans)
{
    // 순서가 곧 규약이다: 새 스캔 적용 → 직전 추정 자세의 우도 → 산포 모드 선택 →
    //   kMove → kExtraMove → 우도갱신 → 추정 → 리샘플.
    //   우도를 **모드 선택 전에** 구해야 한다 — 모드 판정 입력이 "지금 얼마나 믿을 만한가" 이므로,
    //   갱신 뒤 우도를 쓰면 이번 산포가 자기 자신의 결과에 반응하는 순환이 된다.
    applyScan(scans); // updateWeights 가 한 번 더 부르지만 비용은 빔 수 선형(파티클 루프 대비 무시 가능)
    // 모드 판정은 **직전 판정 이후 누적** 이동량으로 한다. 주기당 증분을 쓰면 스캔이 오도보다
    //   느릴 때 이동량이 과소평가돼 산포가 최소 쪽으로 치우친다.
    //   파사드(Mcl2dLocalizer)도 같은 규칙을 쓴다 — 갈리면 같은 입력에 다른 산포가 나온다.
    if (!has_accum_)
    {
        accum_odom_ = prev_odom;
        has_accum_ = true;
    }
    const ControlIncrement2D accum = supplyControlVar(accum_odom_, cur_odom);
    accum_odom_ = cur_odom;
    const ExtraMoveParams e = selectExtraMove(accum.trans, accum.dtheta, likelihoodAt(estimate()), params_);
    predict(prev_odom, cur_odom);
    extraMove(e);
    updateWeights(scans);
    Pose2D est = estimate();
    resample();
    return est;
}

} // namespace mcl2d
