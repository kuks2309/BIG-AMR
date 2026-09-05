// ParticleFilter2D — 2D MCL 파티클필터 (원본 rbk::algorithm::ParticleFilter2D 재구현).  comment-check: ignore
//
// 원본은 이동과 산포를 별개 액션으로 돌린다 — predict 는 **결정론**이고 산포는 extraMove 가 맡는다.
// 한 주기: applyScan → predict(kMove) → extraMove(kExtraMove) → updateWeights → estimate → resample.
// 표본 수는 고정이 아니라 적응형이다: 점유 (x, y, theta) bin 수 × factor 를 [min, max] 로 자른다 —
//   파티클이 퍼져 있으면 많이, 수렴하면 적게 써서 연산을 아낀다.
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
    // 단일 라이다. field 는 원본 getPostProb 와 비트 일치하는 관측 우도장이다.
    ParticleFilter2D(const Mcl2dParams &params, ObservationField field, LaserMount mount, std::uint32_t seed = 12345);
    // 다중 라이다. mounts[i] 는 scans[i] 의 장착 자세여야 한다 — **순서가 곧 대응 관계**다.
    ParticleFilter2D(const Mcl2dParams &params, ObservationField field, std::vector<LaserMount> mounts,
                     std::uint32_t seed = 12345);

    // 초기 자세 주변에 init_particle_number 개를 균등 산포로 생성한다(반폭은 init_*_scatter).
    void initialize(const Pose2D &mean);

    // 영역 [center ± half_extent] m × [±angle_range] rad 안에 max_particle_number 개를 균등 살포.
    void initializeInRegion(const Pose2D &center, double half_extent, double angle_range);

    // 전역 재위치추정. 영역 살포 → 담금질 반복(측정갱신+리샘플) → 수렴하면 조기 종료.
    // 최종 추정 자세의 우도가 reloc_success_threshold 를 넘어야 true 다 — 넘지 못하면
    //   파티클은 이미 재살포된 상태이므로 호출자는 실패를 무시하고 계속 돌리면 안 된다.
    bool relocalize(const Pose2D &center, double radius, double angle_range, const std::vector<LaserScan> &scans);

    // kMove — 오도 두 시점 증분을 전 파티클에 결정론적으로 적용한다. 난수를 쓰지 않는다.
    void predict(const Pose2D &prev_odom, const Pose2D &cur_odom);

    // kExtraMove — 산포. 크기는 selectExtraMove() 가 이동량·우도로 고른다.
    void extraMove(const ExtraMoveParams &e);

    // 단일 스캔으로 가중치 갱신 후 정규화. 유효 빔이 없어 갱신하지 못하면 false(가중치 불변).
    bool updateWeights(const LaserScan &scan);
    // 다중 라이다 융합 갱신. scans[i] 의 장착 자세는 생성자 mounts[i] 다.
    bool updateWeights(const std::vector<LaserScan> &scans);
    // 다중 라이다 한 주기(위 순서를 그대로 수행하고 추정 자세를 돌려준다).
    Pose2D step(const Pose2D &prev_odom, const Pose2D &cur_odom, const std::vector<LaserScan> &scans);

    // systematic 리샘플. 표본 수는 computeSampleNumber() 가 매번 다시 정한다.
    void resample();

    // 단일 라이다 한 주기.
    Pose2D step(const Pose2D &prev_odom, const Pose2D &cur_odom, const LaserScan &scan);

    // 가중평균 자세. theta 는 단순 평균이 아니라 sin/cos 평균이라 ±π 경계에서 접히지 않는다.
    Pose2D estimate() const;

    // 적응 표본 수 — 점유 bin 수 × adaptive_sample_factor 를 [min, max] 로 자른 값.
    int computeSampleNumber() const;

    double meanWeight() const
    {
        return mean_weight_;
    }
    const std::vector<Particle> &particles() const
    {
        return particles_;
    }
    // 파티클 집합 직접 주입. 원본과 같은 입력을 양쪽에 넣어 대조하는 오라클 시험 전용이다.
    void setParticles(const std::vector<Particle> &ps)
    {
        particles_ = ps;
    }

    // 스캔을 우도장에 적재한다. 프레임 변환이 여기서 일어난다 — 입력은 rad·m, 우도장 내부는 도·mm.
    //   public 인 이유: 산포 모드 판정이 **새 스캔 기준** 우도를 요구해서, 상위 계층이
    //   updateWeights 보다 먼저 스캔을 넣고 likelihoodAt 을 물어봐야 하기 때문이다.
    void applyScan(const std::vector<LaserScan> &scans);
    // 자세 하나의 관측 우도. pose 는 미터 프레임이며, **applyScan 을 먼저 부른 뒤에만** 유효하다.
    double likelihoodAt(const Pose2D &pose) const;

  private:
    Mcl2dParams params_;
    ObservationField field_;
    std::vector<LaserMount> mounts_; // 1개 이상 (단일=원소1)
    std::mt19937 rng_;
    std::vector<Particle> particles_;
    double mean_weight_ = 0.0;
    Pose2D accum_odom_;      // 산포 모드 판정의 누적 기준점 — 판정할 때마다 현재 오도로 갱신된다
    bool has_accum_ = false;
};

} // namespace mcl2d

#endif // MCL2D_CORE_PARTICLE_FILTER_HPP
