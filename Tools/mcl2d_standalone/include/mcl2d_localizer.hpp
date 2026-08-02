// non-ROS 위치추정 어댑터 — mcl2d_core(2D 레이저 파티클필터)를 ROS 없이 직접 쓰는 파사드.
// Seer 원본도 비-ROS(자체 zmq+protobuf 미들웨어)이므로, 본 어댑터는 어떤 전송계층에도
// 묶이지 않는 순수 호출 인터페이스를 제공한다(파일/소켓/zmq 등은 호출측이 선택).
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

    // 장애물 점군(m) + 반사판/rssi(m, 선택)으로 Seer 충실 관측 우도장 구축.
    bool loadMap(const std::vector<std::pair<double, double>> &obstacles,
                 const std::vector<std::pair<double, double>> &reflectors = {});

    // 라이다 장착 자세(Roll_A084는 전·후 2개). 순서는 update(scans) 순서와 일치.
    void setLasers(const std::vector<LaserMount> &mounts)
    {
        mounts_ = mounts;
    }

    // 초기 자세(주변 산포로 파티클 생성). 맵·라이다 설정 후 호출.
    void setInitialPose(const Pose2D &mean);

    // 한 주기: 직전/현재 오도 + 라이다 스캔들 → 추정 자세.
    //  stopped: 로봇 정지 여부(슬립 복구 판정용), dt: 경과 시간(s).
    Pose2D update(const Pose2D &prev_odom, const Pose2D &cur_odom, const std::vector<LaserScan> &scans,
                  bool stopped = false, double dt = 0.05);

    // 전역 재위치추정(위치 손실 시). 성공하면 true + 상태 Normal 복귀.
    bool relocalize(const Pose2D &center, double radius, double angle_range, const std::vector<LaserScan> &scans);

    // 마지막 갱신의 평균 우도(신뢰도 지표). 0 이면 위치 손실 가능.
    double confidence() const;
    // 마지막 갱신의 보고 상태 (Normal/Skidding/LowConfidence).
    LocReportState reportState() const
    {
        return report_state_;
    }
    // 마지막 갱신에서 선택된 산포(ExtraMove) 크기와 모드 번호 — 원본 MCLocUpdateMode 로그 대응.
    const ExtraMoveParams &lastExtraMove() const
    {
        return last_extra_move_;
    }
    // 그 모드 판정에 실제로 쓰인 우도. 임계(best_particle_tolerant_threshold)와 함께 봐야 의미가 있다 —
    //   두 값의 스케일 정합이 미검증이라(debt-031) 진단으로 노출한다.
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
    Pose2D accum_odom_;     // 산포 모드 판정용 기준점 (원본 DoNormalUpdateAction 의 정적 accumu 대응)
    bool has_accum_ = false;
};

} // namespace mcl2d

#endif // MCL2D_LOCALIZER_HPP
