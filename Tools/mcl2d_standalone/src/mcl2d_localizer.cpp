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
    pf_.reset(); // 우도장이 바뀌면 살아 있는 파티클은 다른 맵 위의 값이라 버린다
    return !field_.empty();
}

void Mcl2dLocalizer::setInitialPose(const Pose2D &mean)
{
    if (field_.empty())
        return;
    if (mounts_.empty())
        mounts_.emplace_back(); // 미설정이면 로봇 중심에 라이다 1대가 있다고 본다
    pf_ = std::make_unique<ParticleFilter2D>(params_, field_, mounts_, seed_);
    pf_->initialize(mean);

    // 직전 추정·누적 기준점도 함께 버린다. 남겨두면 새 자세와 옛 자세의 차가 한 주기 이동량으로
    //   잡혀 슬립이 거짓으로 뜨고, 산포 모드 판정 기준점도 옛 위치에 묶인다.
    //   이 함수는 기동 시 1회가 아니라 런타임에도 불린다(RViz 의 2D Pose Estimate 등).
    has_prev_est_ = false;
    has_accum_ = false;
    skid_.reset();
    report_state_ = LocReportState::Normal;
}

Pose2D Mcl2dLocalizer::update(const Pose2D &prev_odom, const Pose2D &cur_odom, const std::vector<LaserScan> &scans,
                              bool stopped, double dt)
{
    if (!pf_)
        return Pose2D{};

    // 원본 MCLoc 의 한 주기 순서를 그대로 조립한다 — 순서를 바꾸면 결과가 달라진다:
    //   스캔 적용 → 직전 추정 자세의 우도 → 산포 모드 선택 → kMove(정지면 생략) → kExtraMove
    //   → 우도갱신 → 추정 → 리샘플.
    pf_->applyScan(scans);
    const ControlIncrement2D ctrl = supplyControlVar(prev_odom, cur_odom);

    // 산포 모드 판정은 **직전 판정 이후 누적** 이동량으로 한다. 주기당 증분을 쓰면 스캔이
    //   오도보다 느릴 때 이동량이 과소평가돼 모드가 최소 산포 쪽으로 치우친다.
    //   기준점은 판정 직후 현재 오도로 옮긴다 — 원본도 같은 자리에서 갱신한다.
    if (!has_accum_)
    {
        accum_odom_ = prev_odom;
        has_accum_ = true;
    }
    const ControlIncrement2D accum = supplyControlVar(accum_odom_, cur_odom);
    accum_odom_ = cur_odom;

    // 모드 판정에 쓴 우도를 그대로 보관한다. 임계 best_particle_tolerant_threshold 와 스케일이
    //   같은지 미검증이므로(debt-031) 임계를 임의로 조정하지 말고 이 값을 진단으로 관찰할 것.
    last_mode_likelihood_ = pf_->likelihoodAt(pf_->estimate());
    const ExtraMoveParams extra = selectExtraMove(accum.trans, accum.dtheta, last_mode_likelihood_, params_);
    if (!stopped)
    {
        // 정지 중에는 예측을 건너뛴다 — 원본도 is_stop 이면 kMove 를 아예 돌리지 않는다(@0x3d7d13).
        //   정지 상태의 오도 잡음이 파티클을 조금씩 밀어내는 것을 막는다.
        pf_->predict(prev_odom, cur_odom);
    }
    pf_->extraMove(extra);
    pf_->updateWeights(scans);
    const Pose2D est = pf_->estimate();
    pf_->resample();
    last_extra_move_ = extra;

    // 상태 판정은 슬립이 먼저다 — 미끄러지는 중이면 우도가 높아도 자세를 믿을 수 없다.
    //   휠 오도 이동량은 위에서 구한 주기 증분(ctrl)을 재사용한다.
    double trans_state = 0.0, dth_state = 0.0;
    if (has_prev_est_)
    {
        trans_state = std::hypot(est.x - prev_est_.x, est.y - prev_est_.y);
        dth_state = normalizeAngle(est.theta - prev_est_.theta);
    }
    LocReportState st = skid_.update(ctrl.trans, ctrl.dtheta, trans_state, dth_state, stopped, dt);
    if (st == LocReportState::Normal && pf_->meanWeight() < params_.stop_confidence)
    {
        st = LocReportState::LowConfidence; // 관측이 어느 파티클도 지지하지 않는 상태
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
