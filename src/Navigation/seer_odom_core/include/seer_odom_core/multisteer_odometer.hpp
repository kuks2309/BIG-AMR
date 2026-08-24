// Seer MultiSteersOdometer 재구현 — 다중 조향 휠 오도메트리.
//
// 원본과 대조할 목적으로 만든 것이다. 복원 근거는
//   docs/comparison/seer-odom-production_vs_big-amr_2026-08-07.md §2·§9~§14,
//   채취물은 References/seer/libOdoCalculator/ 에 있다.
//
// 원본 대응: plugins/OdoCalculator/src/Odometer/{multisteerodometer,odometer}.cpp
#ifndef SEER_ODOM_CORE_MULTISTEER_ODOMETER_HPP
#define SEER_ODOM_CORE_MULTISTEER_ODOMETER_HPP

#include <map>
#include <string>
#include <vector>

#include <Eigen/Dense>

#include "seer_odom_core/types.hpp"

namespace seer_odom_core
{

// 각도를 [-π, π) 로 접는다. 원본 rbk::foundation::utils::Normalize(double) 이식.
//   **floor 1회** 방식이다 — 반복 감산으로 바꾸면 큰 각에서 결과가 갈린다(§14 실측).
double normalize(double x);

// 다중 조향 휠 오도미터. 사용 순서는 원본 run() 과 같다:
//   setMotorParams() 로 기하를 굳히고(계수행렬 사전 계산),
//   주기마다 setVitalInfo() → calSpeed() → caldPose() → calPose().
class MultiSteersOdometer
{
  public:
    // 기하를 받아 계수행렬을 사전 계산한다(원본 CalOdoCoef, 79~107행).
    //   휠 순서가 관측벡터 순서를 정하므로 호출 후 바뀌지 않아야 한다.
    //   휠이 2개 미만이면 거짓을 돌려주고 아무것도 굳히지 않는다.
    bool setMotorParams(const std::vector<MotorParam> &wheels);

    // 이번 주기 모터 계측. 키는 MotorParam::name 이다.
    void setVitalInfo(const std::map<std::string, MotorVitalInfo> &info);

    // 속도 산출 + 휠 일관성 판정(원본 CalSpeed, 110~156행).
    //   v_enc 와 조향각으로 관측벡터를 만들어 (vx, vy, vw) 를 얻는다.
    void calSpeed();

    // 변위 증분 산출(원본 CaldPose, 159~195행).
    //   같은 계수행렬을 dpos 에 적용해 (dx, dy, dyaw) 를 얻는다.
    //   **원본과 같이 속도를 0 으로 지운다** — 속도는 calSpeed() 소관이다.
    void caldPose();

    // 자세 누적(원본 AbstractOdometer::CalPose, odometer.cpp 425~454행).
    //   dt_sec 는 속도 경로에서만 쓰인다. 변위 누적 경로(기본)에서는 무시된다.
    void calPose(double dt_sec = 0.0);

    // 원본 flagCumEncPoseMode. 배포값은 1(엔코더 변위 누적)이다 — §4.
    void setCumEncPoseMode(bool on)
    {
        cum_enc_pose_mode_ = on;
    }
    // 원본 flagFirstInputGot. 첫 입력 전에는 증분·자세를 만들지 않는다.
    void setFirstInputGot(bool got)
    {
        first_input_got_ = got;
    }
    // 원본 thresConsistent. 배포값 0.02 — §4.
    void setThresConsistent(double t)
    {
        thres_consistent_ = t;
    }

    const OdometerOutput &output() const
    {
        return output_;
    }
    // 원본 flagWheelConsistent — calSpeed() 의 잔차가 임계 이하였는가.
    bool wheelConsistent() const
    {
        return wheel_consistent_;
    }
    bool coefReady() const
    {
        return coef_ready_;
    }

  private:
    // 관측벡터 b 를 채운다. select 가 v_enc 를 고르면 속도, dpos 를 고르면 변위가 된다 —
    //   원본에서 CalSpeed 와 CaldPose 가 슬롯만 바꿔 같은 사상을 쓰는 것과 같다.
    bool buildObservation(bool use_velocity, std::vector<double> &b) const;
    // coef_ · b 를 풀어 3성분으로 돌려준다.
    void applyCoef(const std::vector<double> &b, double &r0, double &r1, double &r2) const;

    std::vector<MotorParam> wheels_;
    // (AᵀA)⁻¹Aᵀ — 행 3 × 열 2n. 원본이 Eigen 표현식으로 굳히는 것과 같다.
    //   **Eigen 타입으로 들고 Eigen 곱을 쓴다** — 손으로 짠 누적 루프는 덧셈 순서가 달라
    //   yaw 성분에서 1~2 ULP 갈렸다(원본 대조 실측).
    Eigen::MatrixXd coef_;
    std::map<std::string, MotorVitalInfo> vital_;

    OdometerOutput output_;
    bool coef_ready_ = false;
    bool cum_enc_pose_mode_ = true;
    bool first_input_got_ = false;
    bool wheel_consistent_ = true;
    double thres_consistent_ = 0.02;
};

} // namespace seer_odom_core

#endif // SEER_ODOM_CORE_MULTISTEER_ODOMETER_HPP
