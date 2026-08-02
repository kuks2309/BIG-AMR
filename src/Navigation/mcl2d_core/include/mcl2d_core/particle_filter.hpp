// ParticleFilter2D — 2D MCL 파티클필터 (Seer rbk::algorithm::ParticleFilter2D 재구현).
// 파이프라인: predict(균등산포 모션) → updateWeights(격자우도) → resample(systematic) → estimate(가중평균).
// 적응표본: n = (점유 bin 수) × factor, clamp[min,max] (Seer ComputeSampleNumber).
#ifndef MCL2D_CORE_PARTICLE_FILTER_HPP
#define MCL2D_CORE_PARTICLE_FILTER_HPP

#include <cstdint>
#include <random>
#include <vector>

#include "mcl2d_core/observation_field.hpp"
#include "mcl2d_core/types.hpp"

namespace mcl2d
{

class ParticleFilter2D
{
  public:
    // 단일 라이다. field = Seer 관측 우도장(ObservationField, 원본 비트일치).
    ParticleFilter2D(const Mcl2dParams &params, ObservationField field, LaserMount mount, std::uint32_t seed = 12345);
    // 다중 라이다(Roll_A084 전+후 듀얼). mounts 순서는 updateWeights(scans) 순서와 일치.
    ParticleFilter2D(const Mcl2dParams &params, ObservationField field, std::vector<LaserMount> mounts,
                     std::uint32_t seed = 12345);

    // 초기 자세 주변에 init_particle_number 개를 균등 산포로 생성.
    void initialize(const Pose2D &mean);

    // 영역([center ± half_extent] × [±angle_range]) 내 max_particle_number 개 균등 살포.
    void initializeInRegion(const Pose2D &center, double half_extent, double angle_range);

    // 전역 재위치추정 (Seer DoRelocAction): 영역 살포 → 담금질 반복(측정갱신+리샘플) →
    // 수렴 시 조기종료. 최종 추정 자세의 정상 PDF 우도 > 임계이면 성공(true).
    bool relocalize(const Pose2D &center, double radius, double angle_range, const std::vector<LaserScan> &scans);

    // kMove — 오도 두 시점 증분을 **결정론적으로** 전 파티클에 적용(산포 없음, 원본 실측).
    void predict(const Pose2D &prev_odom, const Pose2D &cur_odom);

    // kExtraMove — 산포. 크기는 selectExtraMove() 가 모드별로 고른 값.
    void extraMove(const ExtraMoveParams &e);

    // 단일 스캔으로 가중치 갱신(정규화). 갱신 안 되면 false.
    bool updateWeights(const LaserScan &scan);
    // 다중 라이다 스캔 융합 갱신. scans[i] 는 생성자 mounts[i] 장착.
    bool updateWeights(const std::vector<LaserScan> &scans);
    // 다중 라이다 한 주기.
    Pose2D step(const Pose2D &prev_odom, const Pose2D &cur_odom, const std::vector<LaserScan> &scans);

    // systematic 리샘플 (표본 수 = computeSampleNumber()).
    void resample();

    // 한 주기: predict → updateWeights → resample → estimate.
    Pose2D step(const Pose2D &prev_odom, const Pose2D &cur_odom, const LaserScan &scan);

    // 가중평균 자세 추정.
    Pose2D estimate() const;

    // 적응표본 수 (점유 (x,y,theta) bin 수 × factor, clamp).
    int computeSampleNumber() const;

    double meanWeight() const
    {
        return mean_weight_;
    }
    const std::vector<Particle> &particles() const
    {
        return particles_;
    }
    // 파티클 집합 직접 주입 (검증/오라클 대조용 — 동일 입력을 원본·우리에 투입).
    void setParticles(const std::vector<Particle> &ps)
    {
        particles_ = ps;
    }

    // ROS 프레임 스캔(rad·m) → 원본 프레임 그룹(도·mm) 변환 후 field_.setScan.
    //   공개 이유: 산포 모드 판정이 **새 스캔 기준** 우도를 요구하므로(원본 순서), 상위(MCLoc 역할)가
    //   updateWeights 보다 먼저 스캔을 넣고 likelihoodAt 을 물어봐야 한다.
    void applyScan(const std::vector<LaserScan> &scans);
    // 자세의 관측 우도(field_ 는 applyScan 이 setScan 완료 상태여야 함). pose 는 미터 프레임.
    double likelihoodAt(const Pose2D &pose) const;

  private:
    Mcl2dParams params_;
    ObservationField field_;
    std::vector<LaserMount> mounts_; // 1개 이상 (단일=원소1)
    std::mt19937 rng_;
    std::vector<Particle> particles_;
    double mean_weight_ = 0.0;
};

} // namespace mcl2d

#endif // MCL2D_CORE_PARTICLE_FILTER_HPP
