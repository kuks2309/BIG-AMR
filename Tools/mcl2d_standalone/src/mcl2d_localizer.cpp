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
}

Pose2D Mcl2dLocalizer::update(const Pose2D &prev_odom, const Pose2D &cur_odom, const std::vector<LaserScan> &scans,
                              bool stopped, double dt)
{
    if (!pf_)
        return Pose2D{};

    // 원본 MCLoc 의 한 주기 순서를 그대로 조립한다(ADR 2026-07-31-mcl2d-motion-model-fidelity):
    //   스캔 적용 → 직전 추정 자세의 우도 → 산포 모드 선택 → kMove(정지면 생략) → kExtraMove → 우도갱신 → 추정 → 리샘플.
    pf_->applyScan(scans);
    const ControlIncrement2D ctrl = supplyControlVar(prev_odom, cur_odom);
    const ExtraMoveParams extra =
        selectExtraMove(ctrl.trans, ctrl.dtheta, pf_->likelihoodAt(pf_->estimate()), params_);
    if (!stopped)
    {
        // 원본 DoMoveAction @0x3d7d13: cv.is_stop 이면 kMove 자체를 건너뛴다(정지 중 파티클 전진 금지).
        pf_->predict(prev_odom, cur_odom);
    }
    pf_->extraMove(extra);
    pf_->updateWeights(scans);
    const Pose2D est = pf_->estimate();
    pf_->resample();
    last_extra_move_ = extra;

    // 위치추정 상태 판정 (Seer §6.6 ②③): 슬립 우선, 아니면 신뢰도 게이트.
    const double trans_odo = std::hypot(cur_odom.x - prev_odom.x, cur_odom.y - prev_odom.y);
    const double dth_odo = normalizeAngle(cur_odom.theta - prev_odom.theta);
    double trans_state = 0.0, dth_state = 0.0;
    if (has_prev_est_)
    {
        trans_state = std::hypot(est.x - prev_est_.x, est.y - prev_est_.y);
        dth_state = normalizeAngle(est.theta - prev_est_.theta);
    }
    LocReportState st = skid_.update(trans_odo, dth_odo, trans_state, dth_state, stopped, dt);
    if (st == LocReportState::Normal && pf_->meanWeight() < params_.stop_confidence)
    {
        st = LocReportState::LowConfidence; // 저신뢰 정지
    }
    report_state_ = st;
    prev_est_ = est;
    has_prev_est_ = true;
    return est;
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
    }
    return ok;
}

double Mcl2dLocalizer::confidence() const
{
    return pf_ ? pf_->meanWeight() : 0.0;
}

} // namespace mcl2d
