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

    // 산포 모드 판정은 **직전 판정 이후 누적** 이동량으로 한다 — 원본이 DoNormalUpdateAction 안의
    //   정적 기준점(accumu)과의 차를 쓰고 그 자리에서 기준점을 갱신하기 때문이다(대조 문서 §1.1.2).
    //   주기당 증분을 쓰면 스캔이 오도보다 느릴 때 이동량이 과소평가돼 모드가 최소 산포로 치우친다.
    if (!has_accum_)
    {
        accum_odom_ = prev_odom;
        has_accum_ = true;
    }
    const ControlIncrement2D accum = supplyControlVar(accum_odom_, cur_odom);
    accum_odom_ = cur_odom;

    // 모드 판정에 쓴 우도는 그대로 보관한다 — 임계(best_particle_tolerant_threshold)가 원본 스케일
    //   값이라 우리 우도 스케일에서 같은 의미인지 미검증이고(debt-031), 그 사실은 값을 바꾸는 대신
    //   진단으로 드러내야 판단 근거가 쌓인다.
    last_mode_likelihood_ = pf_->likelihoodAt(pf_->estimate());
    const ExtraMoveParams extra = selectExtraMove(accum.trans, accum.dtheta, last_mode_likelihood_, params_);
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
    //   휠 오도 이동량은 위에서 구한 주기 증분(ctrl)을 그대로 쓴다 — 같은 양을 두 번 계산하지 않는다.
    double trans_state = 0.0, dth_state = 0.0;
    if (has_prev_est_)
    {
        trans_state = std::hypot(est.x - prev_est_.x, est.y - prev_est_.y);
        dth_state = normalizeAngle(est.theta - prev_est_.theta);
    }
    LocReportState st = skid_.update(ctrl.trans, ctrl.dtheta, trans_state, dth_state, stopped, dt);
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
