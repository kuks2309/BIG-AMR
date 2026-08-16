#include "odom_imu_ekf/ekf.hpp"

#include <cmath>

namespace odom_imu_ekf
{

double normalizeAngle(double a)
{
    while (a >= M_PI)
        a -= 2.0 * M_PI;
    while (a < -M_PI)
        a += 2.0 * M_PI;
    return a;
}

OdomImuEkf::OdomImuEkf(const Params &params) : params_(params)
{
    for (int i = 0; i < kStateDim; ++i)
        P_[i][i] = params_.prior_covariance;
}

void OdomImuEkf::addOdom(const Pose3D &pose, double yaw_rate)
{
    odom_prev_ = has_odom_ ? odom_cur_ : pose;
    odom_cur_ = pose;
    odom_yaw_rate_ = yaw_rate;
    has_odom_ = true;
}

void OdomImuEkf::addImu(double roll, double pitch, double yaw)
{
    imu_roll_ = roll;
    imu_pitch_ = pitch;
    imu_yaw_ = yaw;
    has_imu_ = true;
}

void OdomImuEkf::predict(double d_trans, double d_yaw)
{
    const double theta = x_[kYaw];
    const double c = std::cos(theta), s = std::sin(theta);

    // 원본 NonLinearAnalyticConditionalGaussianOdo::ExpectedValueGet 과 같은 식.  comment-check: ignore
    //   z·roll·pitch 는 예측에서 움직이지 않는다 — 관측으로만 바뀐다.
    x_[kX] += d_trans * c;
    x_[kY] += d_trans * s;
    x_[kYaw] = normalizeAngle(x_[kYaw] + d_yaw);

    // 야코비안은 항등에 yaw 열만 비영이다(원본 dfGet).
    //   F·P·Fᵀ 를 그 희소성만큼만 전개한다 — 6×6 곱을 돌리지 않는다.
    const double f16 = -d_trans * s;
    const double f26 = d_trans * c;
    for (int j = 0; j < kStateDim; ++j)
    {
        P_[kX][j] += f16 * P_[kYaw][j];
        P_[kY][j] += f26 * P_[kYaw][j];
    }
    for (int i = 0; i < kStateDim; ++i)
    {
        P_[i][kX] += f16 * P_[i][kYaw];
        P_[i][kY] += f26 * P_[i][kYaw];
    }
    for (int i = 0; i < kStateDim; ++i)
        P_[i][i] += params_.system_noise;
}

void OdomImuEkf::correct(const int *indices, int count, const double *measurement, double noise)
{
    // H 가 상태를 고르기만 하므로(원본 Hodom·Himu 는 0/1 행렬) 성분별 순차 갱신으로 같은 결과를 낸다.
    //   각 성분에서 S = P(i,i) + R, K = P(:,i)/S 이고 잔차는 스칼라다.
    for (int k = 0; k < count; ++k)
    {
        const int i = indices[k];
        double innovation = measurement[k] - x_[i];
        if (i == kRoll || i == kPitch || i == kYaw)
            innovation = normalizeAngle(innovation);

        const double s = P_[i][i] + noise;
        if (s <= 0.0)
            continue;

        double gain[kStateDim];
        for (int r = 0; r < kStateDim; ++r)
            gain[r] = P_[r][i] / s;

        for (int r = 0; r < kStateDim; ++r)
            x_[r] += gain[r] * innovation;
        x_[kRoll] = normalizeAngle(x_[kRoll]);
        x_[kPitch] = normalizeAngle(x_[kPitch]);
        x_[kYaw] = normalizeAngle(x_[kYaw]);

        // P ← (I − K·H)·P. H 가 i 행 하나만 고르므로 i 행을 뺀 갱신으로 끝난다.
        double row[kStateDim];
        for (int c = 0; c < kStateDim; ++c)
            row[c] = P_[i][c];
        for (int r = 0; r < kStateDim; ++r)
            for (int c = 0; c < kStateDim; ++c)
                P_[r][c] -= gain[r] * row[c];
    }
}

bool OdomImuEkf::update()
{
    last_imu_applied_ = false;
    if (!has_odom_ || !has_imu_)
        return false; // 원본 run() 과 같이 두 센서를 다 받기 전에는 진행하지 않는다

    // 오도 첫 주기는 기준선만 세운다(원본 m_odom_init 분기).
    if (!odom_init_)
    {
        x_[kX] = odom_cur_.x / kPositionScale;
        x_[kY] = odom_cur_.y / kPositionScale;
        x_[kYaw] = normalizeAngle(odom_cur_.yaw);
        odom_init_ = true;
    }
    else
    {
        // 예측 입력은 오도의 **증분**이다 — 절대값 드리프트는 들이지 않는다.
        const double dx = (odom_cur_.x - odom_prev_.x) / kPositionScale;
        const double dy = (odom_cur_.y - odom_prev_.y) / kPositionScale;
        const double d_yaw = normalizeAngle(odom_cur_.yaw - odom_prev_.yaw);
        // 이동 방향은 직전 오도 헤딩 기준으로 되돌려 병진량만 뽑는다.
        const double heading = normalizeAngle(odom_prev_.yaw);
        const double d_trans = dx * std::cos(heading) + dy * std::sin(heading);
        predict(d_trans, d_yaw);

        const int odom_idx[] = {kX, kY, kYaw};
        const double odom_meas[] = {odom_cur_.x / kPositionScale, odom_cur_.y / kPositionScale,
                                    normalizeAngle(odom_cur_.yaw)};
        correct(odom_idx, 3, odom_meas, params_.odom_measurement_noise);
    }

    // IMU 첫 주기도 기준선만 세운다(원본 m_imu_init 분기).
    if (!imu_init_)
    {
        imu_init_ = true;
    }
    else if (std::fabs(odom_yaw_rate_) > params_.imu_gate_rate)
    {
        // 회전 중일 때만 IMU 를 반영한다 — 정지·직진에서 자이로 바이어스가 yaw 로 새는 것을 막는다.
        const int imu_idx[] = {kRoll, kPitch, kYaw};
        const double imu_meas[] = {normalizeAngle(imu_roll_), normalizeAngle(imu_pitch_),
                                   normalizeAngle(imu_yaw_)};
        correct(imu_idx, 3, imu_meas, params_.imu_measurement_noise);
        last_imu_applied_ = true;
    }

    pose_.x = x_[kX] * kPositionScale;
    pose_.y = x_[kY] * kPositionScale;
    pose_.z = x_[kZ] * kPositionScale;
    pose_.roll = x_[kRoll];
    pose_.pitch = x_[kPitch];
    pose_.yaw = x_[kYaw];
    return true;
}

} // namespace odom_imu_ekf
