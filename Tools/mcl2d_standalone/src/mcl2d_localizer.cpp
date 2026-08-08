#include "mcl2d_localizer.hpp"

#include <cmath>

#include "mcl2d_core/motion_model.hpp" // normalizeAngle

namespace mcl2d
{

Mcl2dLocalizer::Mcl2dLocalizer(const Mcl2dParams &params, std::uint32_t seed)
    : params_(params), seed_(seed), skid_(params_)
{
}

bool Mcl2dLocalizer::loadMap(const std::vector<std::pair<double, double>> &obstacles,
                             const std::vector<std::pair<double, double>> &reflectors)
{
    field_.build(obstacles, reflectors);
    pf_.reset(); // 맵 변경 시 재초기화 필요
    return !field_.empty();
}

void Mcl2dLocalizer::setInitialPose(const Pose2D &mean)
{
    if (field_.empty())
        return;
    if (mounts_.empty())
        mounts_.emplace_back(); // 미설정 시 로봇중심 단일 라이다
    pf_ = std::make_unique<ParticleFilter2D>(params_, field_, mounts_, seed_);
    pf_->initialize(mean);
    pose_ = mean; // 발행 자세도 함께 초기화 (오도 주기 전진의 출발점)
    odo_trans_since_scan_ = 0.0;
    odo_dtheta_since_scan_ = 0.0;
}

Pose2D Mcl2dLocalizer::advanceWithOdom(const Pose2D &prev_odom, const Pose2D &cur_odom, bool stopped)
{
    if (!pf_)
        return pose_;

    // 원본 오도 주기(MCLoc::PublishLoc → DoMoveAction): supplyControlValue(cv, 0.0) →
    //   moveRobotAccordingToMotion(자세 전진) → ParticlesAction(kMove) → 발행. 스캔은 쓰지 않는다.
    const ControlIncrement2D ctrl = supplyControlVar(prev_odom, cur_odom);

    // 슬립 판정은 스캔 주기에 하므로, 그 사이의 오도 이동량을 모아 둔다.
    odo_trans_since_scan_ += ctrl.trans;
    odo_dtheta_since_scan_ = normalizeAngle(odo_dtheta_since_scan_ + ctrl.dtheta);

    if (!stopped)
    {
        // 원본 DoMoveAction @0x3d7d13: cv.is_stop 이면 kMove 자체를 건너뛴다(정지 중 전진 금지).
        pf_->predict(prev_odom, cur_odom);
        // 원본 moveRobotAccordingToMotion @0x33f4b0 — 파티클과 **별개로** 발행 자세를 같은 결정론 식으로
        //   전진시킨다. 식이 동일하므로 파티클 1개에 doParticleMove 를 적용하는 것과 같다.
        Particle p{pose_, 1.0};
        doParticleMove(p, ctrl);
        pose_ = p.pose;
    }
    return pose_;
}

Pose2D Mcl2dLocalizer::updateWithScan(const std::vector<LaserScan> &scans, const Pose2D &cur_odom, bool stopped,
                                      double dt)
{
    if (!pf_)
        return pose_;

    // 원본 스캔 주기(MCLoc::DoNormalUpdateAction): 스캔 적용 → 우도 → 모드 선택 → kExtraMove →
    //   우도갱신 → 추정 → 리샘플. kMove 는 여기서 하지 않는다(오도 주기 소관).
    pf_->applyScan(scans);

    // 산포 모드 판정은 **직전 판정 이후 누적** 이동량으로 한다 — 원본이 DoNormalUpdateAction 안의
    //   정적 기준점(accumu)과의 차를 쓰고 그 자리에서 기준점을 갱신하기 때문이다(대조 문서 §1.1.2).
    if (!has_accum_)
    {
        accum_odom_ = cur_odom;
        has_accum_ = true;
    }
    const ControlIncrement2D accum = supplyControlVar(accum_odom_, cur_odom);
    accum_odom_ = cur_odom;

    // 모드 판정 우도는 **현재 발행 자세**에서 잰다 — 원본도 멤버로 들고 있는 로봇 자세를 쓴다
    //   (DoNormalUpdateAction 3ca4b7~3ca4e4 가 멤버 0xf50/0xf58/0xf60 을 읽어 파티클을 만든다).
    //   임계(best_particle_tolerant_threshold)와의 스케일 정합은 미검증이라 값 대신 진단으로 노출한다(debt-031).
    last_mode_likelihood_ = pf_->likelihoodAt(pose_);
    const ExtraMoveParams extra = selectExtraMove(accum.trans, accum.dtheta, last_mode_likelihood_, params_);
    pf_->extraMove(extra);
    pf_->updateWeights(scans);
    const Pose2D est = pf_->estimate();
    pf_->resample();
    last_extra_move_ = extra;
    pose_ = est; // 발행 자세를 파티클 평균으로 재설정

    // 위치추정 상태 판정 (Seer §6.6 ②③): 슬립 우선, 아니면 신뢰도 게이트.
    //   휠 오도 이동량은 마지막 스캔 갱신 이후 누적분을 쓴다(두 주기가 분리됐으므로).
    double trans_state = 0.0, dth_state = 0.0;
    if (has_prev_est_)
    {
        trans_state = std::hypot(est.x - prev_est_.x, est.y - prev_est_.y);
        dth_state = normalizeAngle(est.theta - prev_est_.theta);
    }
    LocReportState st =
        skid_.update(odo_trans_since_scan_, odo_dtheta_since_scan_, trans_state, dth_state, stopped, dt);
    if (st == LocReportState::Normal && pf_->meanWeight() < params_.stop_confidence)
    {
        st = LocReportState::LowConfidence; // 저신뢰 정지
    }
    report_state_ = st;
    prev_est_ = est;
    has_prev_est_ = true;
    odo_trans_since_scan_ = 0.0;
    odo_dtheta_since_scan_ = 0.0;
    return est;
}

Pose2D Mcl2dLocalizer::update(const Pose2D &prev_odom, const Pose2D &cur_odom, const std::vector<LaserScan> &scans,
                              bool stopped, double dt)
{
    // 오도와 스캔이 같은 주기로 오는 사용처용 — 두 단계를 순서대로 수행한다(단일 구현 유지).
    advanceWithOdom(prev_odom, cur_odom, stopped);
    return updateWithScan(scans, cur_odom, stopped, dt);
}

bool Mcl2dLocalizer::relocalize(const Pose2D &center, double radius, double angle_range,
                                const std::vector<LaserScan> &scans)
{
    if (!pf_)
        return false;
    const bool ok = pf_->relocalize(center, radius, angle_range, scans);
    if (ok)
    {
        report_state_ = LocReportState::Normal;
        skid_.reset();
        prev_est_ = pf_->estimate();
        has_prev_est_ = true;
        pose_ = prev_est_; // 재위치추정 성공 → 발행 자세도 새 추정으로 리셋
        odo_trans_since_scan_ = 0.0;
        odo_dtheta_since_scan_ = 0.0;
    }
    return ok;
}

double Mcl2dLocalizer::confidence() const
{
    return pf_ ? pf_->meanWeight() : 0.0;
}

} // namespace mcl2d
