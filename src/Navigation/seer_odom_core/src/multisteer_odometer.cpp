#include "seer_odom_core/multisteer_odometer.hpp"

#include <cmath>

#include <Eigen/Dense>

namespace seer_odom_core
{

double normalize(double x)
{
    const double pi = M_PI;
    // 빠른 경로 — 이미 치역 안이면 **그대로 돌려준다**(원본 0x18750 의 두 비교 + ret).
    if (!(x < -pi || x >= pi))
        return x;
    const double two_pi = pi + pi;
    // 원본은 floor 로 한 번에 접는다. 반복 감산으로 바꾸면 큰 각에서 누적 반올림이 달라진다.
    double r = x - two_pi * std::floor(x / two_pi); // [0, 2π)
    double y = (r < pi) ? r : r - two_pi;
    return (y < -pi) ? y + two_pi : y;
}

bool MultiSteersOdometer::setMotorParams(const std::vector<MotorParam> &wheels)
{
    coef_ready_ = false;
    coef_.clear();
    wheels_ = wheels;
    // 미지수가 3개(dx, dy, dyaw)이므로 관측이 3개 이상이어야 한다 — 휠 2개면 4개다.
    if (wheels_.size() < 2)
        return false;

    const int n = static_cast<int>(wheels_.size());
    const int rows = 2 * n;
    // 평면 강체 관계. 유효 휠 위치는 설계값 + 보정항이다.
    //   [ 1  0  -(y+cpy) ] [ dx   ]   [ cos δ · s ]
    //   [ 0  1   (x+cpx) ] [ dy   ] = [ sin δ · s ]
    //                      [ dyaw ]
    Eigen::MatrixXd a = Eigen::MatrixXd::Zero(rows, 3);
    for (int i = 0; i < n; ++i)
    {
        a(2 * i, 0) = 1.0;
        a(2 * i, 2) = -(wheels_[i].y + wheels_[i].cpy);
        a(2 * i + 1, 1) = 1.0;
        a(2 * i + 1, 2) = wheels_[i].x + wheels_[i].cpx;
    }

    // 원본이 굳히는 것과 같은 식 — (AᵀA)⁻¹Aᵀ. 동적 크기라 Eigen 이 PartialPivLU 로 역행렬을 만든다.
    const Eigen::MatrixXd ata = a.transpose() * a;
    // 특이하면 굳히지 않는다 — 원본은 이 자리를 검사하지 않지만, 굳은 쓰레기값으로
    //   매 주기 도는 것보다 서지 않는 편이 낫다(의도적 이탈).
    if (std::fabs(ata.determinant()) < 1e-12)
        return false;

    const Eigen::MatrixXd coef = ata.inverse() * a.transpose(); // 3 × rows
    coef_.assign(coef.data(), coef.data() + coef.size());       // Eigen 기본 열 우선
    coef_ready_ = true;
    return true;
}

void MultiSteersOdometer::setVitalInfo(const std::map<std::string, MotorVitalInfo> &info)
{
    vital_ = info;
}

bool MultiSteersOdometer::buildObservation(bool use_velocity, std::vector<double> &b) const
{
    b.assign(2 * wheels_.size(), 0.0);
    for (std::size_t i = 0; i < wheels_.size(); ++i)
    {
        const auto it = vital_.find(wheels_[i].name);
        if (it == vital_.end())
            return false;
        const double s = use_velocity ? it->second.v_enc : it->second.dpos;
        const double d = it->second.position; // 조향각
        b[2 * i] = std::cos(d) * s;
        b[2 * i + 1] = std::sin(d) * s;
    }
    return true;
}

void MultiSteersOdometer::applyCoef(const std::vector<double> &b, double &r0, double &r1,
                                    double &r2) const
{
    // coef_ 는 열 우선 3×m 이므로 (행 k, 열 j) 는 coef_[j*3 + k] 다.
    double acc[3] = {0.0, 0.0, 0.0};
    for (std::size_t j = 0; j < b.size(); ++j)
        for (int k = 0; k < 3; ++k)
            acc[k] += coef_[j * 3 + k] * b[j];
    r0 = acc[0];
    r1 = acc[1];
    r2 = acc[2];
}

void MultiSteersOdometer::calSpeed()
{
    if (!coef_ready_ || !first_input_got_)
    {
        // 원본 151행의 착지점 — 속도 3축을 0 으로 둔다.
        output_.vx = output_.vy = output_.vw = 0.0;
        return;
    }
    std::vector<double> b;
    if (!buildObservation(/*use_velocity=*/true, b))
    {
        output_.vx = output_.vy = output_.vw = 0.0;
        return;
    }
    applyCoef(b, output_.vx, output_.vy, output_.vw);

    // 휠 일관성 — 풀어낸 (vx, vy, vw) 를 관측으로 되돌려 잔차를 본다.
    //   원본은 잔차를 절대값으로 취합해 thresConsistent 와 비교하고 결과만 남긴다(경고 로그).
    double worst = 0.0;
    for (std::size_t i = 0; i < wheels_.size(); ++i)
    {
        const double ex = output_.vx - output_.vw * (wheels_[i].y + wheels_[i].cpy);
        const double ey = output_.vy + output_.vw * (wheels_[i].x + wheels_[i].cpx);
        worst = std::max(worst, std::fabs(ex - b[2 * i]));
        worst = std::max(worst, std::fabs(ey - b[2 * i + 1]));
    }
    wheel_consistent_ = (worst <= thres_consistent_);
}

void MultiSteersOdometer::caldPose()
{
    if (!coef_ready_ || !first_input_got_)
    {
        output_.vx = output_.vy = output_.vw = 0.0;
        return;
    }
    std::vector<double> b;
    if (buildObservation(/*use_velocity=*/false, b))
        applyCoef(b, output_.dx, output_.dy, output_.dyaw);
    // 원본 190행 — 이 함수는 증분만 만들고 **속도는 항상 지운다**.
    output_.vx = output_.vy = output_.vw = 0.0;
}

void MultiSteersOdometer::calPose(double dt_sec)
{
    if (!first_input_got_) // 원본 428행
        return;

    double dx, dy, dyaw;
    if (cum_enc_pose_mode_) // 원본 437행 — 배포값 1
    {
        dx = output_.dx;
        dy = output_.dy;
        dyaw = output_.dyaw;
    }
    else
    {
        dx = output_.vx * dt_sec;
        dy = output_.vy * dt_sec;
        dyaw = output_.vw * dt_sec;
    }

    // 원본 446~450행 — 각을 **먼저** 갱신·정규화하고 그 각으로 회전한다(end-point).
    output_.yaw = normalize(output_.yaw + dyaw);
    const double s = std::sin(output_.yaw);
    const double c = std::cos(output_.yaw);
    output_.x += c * dx - s * dy;
    output_.y += s * dx + c * dy;
}

} // namespace seer_odom_core
