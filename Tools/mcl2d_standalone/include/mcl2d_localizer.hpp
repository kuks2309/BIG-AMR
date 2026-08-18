// non-ROS 위치추정 파사드 — mcl2d_core(2D 레이저 파티클필터)를 ROS 없이 직접 쓴다.
// 전송계층에 묶이지 않는 순수 호출 인터페이스만 제공하고, 파일·소켓·미들웨어 선택은 호출측 몫이다.
// 원본 libMCLoc 도 ROS 를 쓰지 않으므로(zmq·protobuf 를 링크한다) 이 경계가 원본 구조와 맞는다.
#ifndef MCL2D_LOCALIZER_HPP
#define MCL2D_LOCALIZER_HPP

#include <cstdint>
#include <memory>
#include <utility>
#include <vector>

#include "mcl2d_core/particle_filter.hpp"
#include "mcl2d_core/skid_detector.hpp"
#include "mcl2d_core/types.hpp"

namespace mcl2d
{

// 비-ROS 위치추정 파사드. 사용 순서: setParams → loadMap → setLasers → setInitialPose → update(반복).
class Mcl2dLocalizer
{
  public:
    explicit Mcl2dLocalizer(const Mcl2dParams &params = {}, std::uint32_t seed = 12345);

    // 장애물 점군 [m] + 반사판/rssi 점군 [m, 선택] 으로 관측 우도장을 만든다.
    // 맵을 바꾸면 파티클필터가 무효화되므로 setInitialPose 를 다시 불러야 한다.
    bool loadMap(const std::vector<std::pair<double, double>> &obstacles,
                 const std::vector<std::pair<double, double>> &reflectors = {});

    // 라이다 장착 자세. mounts[i] 가 update(scans) 의 scans[i] 에 대응한다 — 순서가 곧 대응 관계다.
    void setLasers(const std::vector<LaserMount> &mounts)
    {
        mounts_ = mounts;
    }

    // 초기 자세를 주고 그 주변에 파티클을 생성한다. loadMap·setLasers 뒤에 불러야 한다.
    // 런타임 재초기화 경로이기도 하다 — 직전 추정·누적 기준점·슬립 상태를 모두 버린다.
    void setInitialPose(const Pose2D &mean);

    // 한 주기 — 오도 두 시점과 스캔들로 추정 자세를 낸다.
    //   prev_odom·cur_odom : 오도 절대 자세. 여기서 **증분만** 취하므로 드리프트는 전파되지 않는다.
    //   stopped            : 참이면 예측(kMove)을 건너뛴다. 슬립 복구 판정에도 쓰인다.
    //   dt [s]             : 직전 호출 이후 경과. 슬립 복구 시간 누적에만 쓰인다.
    Pose2D update(const Pose2D &prev_odom, const Pose2D &cur_odom, const std::vector<LaserScan> &scans,
                  bool stopped = false, double dt = 0.05);

    // 전역 재위치추정. 실패해도 파티클은 이미 재살포된 뒤이므로 반환값을 무시하면 안 된다.
    bool relocalize(const Pose2D &center, double radius, double angle_range, const std::vector<LaserScan> &scans);

    // 마지막 갱신의 평균 관측 우도. 절대 스케일이 아니라 **상대 지표**다(맵 밀도·빔 수에 의존).
    double confidence() const;
    // 마지막 갱신의 보고 상태 (Normal/Skidding/LowConfidence).
    LocReportState reportState() const
    {
        return report_state_;
    }
    // 마지막 갱신에서 고른 산포 크기와 모드 번호. 진단 전용이며 제어에 쓰지 않는다.
    const ExtraMoveParams &lastExtraMove() const
    {
        return last_extra_move_;
    }
    // 그 모드 판정에 실제로 쓰인 우도. 임계 best_particle_tolerant_threshold 와 같은 스케일인지는
    //   확인되지 않았으므로(debt-031) 값으로 판단하지 말고 진단으로만 볼 것.
    double lastModeLikelihood() const
    {
        return last_mode_likelihood_;
    }
    bool ready() const
    {
        return pf_ != nullptr;
    }

  private:
    Mcl2dParams params_;
    std::uint32_t seed_;
    ObservationField field_;
    std::vector<LaserMount> mounts_;
    std::unique_ptr<ParticleFilter2D> pf_;
    SkidDetector skid_;
    LocReportState report_state_ = LocReportState::Normal;
    ExtraMoveParams last_extra_move_;
    double last_mode_likelihood_ = 0.0;
    Pose2D prev_est_;
    bool has_prev_est_ = false;
    Pose2D accum_odom_;     // 산포 모드 판정의 누적 기준점 — 판정할 때마다 현재 오도로 갱신된다
    bool has_accum_ = false;
};

} // namespace mcl2d

#endif // MCL2D_LOCALIZER_HPP
