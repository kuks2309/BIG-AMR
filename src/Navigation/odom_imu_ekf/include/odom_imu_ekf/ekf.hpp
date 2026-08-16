// 휠 오도 + IMU 융합 EKF — Seer 레거시 RobotPosEKF(estimation::OdomEstimation) 이식.  comment-check: ignore
//
// 원본은 ROS robot_pose_ekf 의 이식본이고, 여기서는 그 수치·구조를 그대로 옮긴다.
// 근거는 배선 정본 Tools/seer_re/docs/legacy_runtime_wiring.md 부록 A 에 주소까지 기록돼 있다.
//
// ROS 의존이 없다 — 시각은 호출자가 주고 여기는 값만 받는다. 그래야 시계 없이 시험할 수 있다.
#ifndef ODOM_IMU_EKF_EKF_HPP
#define ODOM_IMU_EKF_EKF_HPP

#include <array>

namespace odom_imu_ekf
{

// 상태 차원. 원본이 ColumnVector(6)/SymmetricMatrix(6) 으로 잡는다 — (x, y, z, roll, pitch, yaw).
inline constexpr int kStateDim = 6;
// 상태 인덱스(0-based). 원본은 BFL 의 1-based 이므로 문서와 대조할 때 +1 해서 읽는다.
enum StateIndex
{
    kX = 0,
    kY = 1,
    kZ = 2,
    kRoll = 3,
    kPitch = 4,
    kYaw = 5
};

// 원본이 x·y 에만 거는 내부 스케일. 입력에서 나누고 출력에서 곱해 대칭이라
//   인터페이스에서는 보이지 않지만, **잡음 상수가 이 스케일 공간에서 정의돼 있어** 함께 옮긴다.
inline constexpr double kPositionScale = 100.0;

struct Pose3D
{
    double x = 0.0;     // m
    double y = 0.0;     // m
    double z = 0.0;     // m
    double roll = 0.0;  // rad
    double pitch = 0.0; // rad
    double yaw = 0.0;   // rad
};

struct Params
{
    // 시스템(프로세스) 잡음 대각. 원본 생성자가 6축 모두 1e6 으로 채운다(σ=1000).
    //   예측을 거의 믿지 않는 설정이라 관측이 자세를 지배한다.
    double system_noise = 1.0e6;
    // 초기 공분산 대각. 원본 initialize() 가 6×6 전량을 1e-6 으로 채운다(σ=0.001).
    double prior_covariance = 1.0e-6;
    // 관측 잡음 대각. ⚠ 원본은 이 자리에 **초기화되지 않은 힙 메모리**를 넘긴다 —
    //   재현 대상이 아니라서 값을 명시한다 — 이 항목만 원본에서 **의도적으로 이탈**한다.
    //   기본값은 원본 생성자가 측정모델에 넘긴 지역 행렬의 대각(1.0)이다.
    double odom_measurement_noise = 1.0;
    double imu_measurement_noise = 1.0;
    // IMU 갱신 게이트 [rad/s]. 원본은 |ω| > 1.0 deg/s 를 하드코딩한다.
    //   정지·직진 중 자이로 바이어스가 yaw 로 적분되는 것을 막는다.
    double imu_gate_rate = 1.0 * 3.14159265358979323846 / 180.0;
};

// 융합기 한 대. 오도·IMU 를 각각 넣고 update() 로 한 주기를 돌린 뒤 pose() 를 읽는다.
class OdomImuEkf
{
  public:
    explicit OdomImuEkf(const Params &params = {});

    // 휠 오도 측정. pose 는 오도 프레임 절대 자세(내부에서 증분만 쓴다),
    //   yaw_rate [rad/s] 는 IMU 게이트 판정에 쓰인다(원본 wzOdoAbsDeg 대응).
    void addOdom(const Pose3D &pose, double yaw_rate);
    // IMU 측정. 자세 3축만 쓴다(원본 Himu 가 roll·pitch·yaw 만 고른다).
    void addImu(double roll, double pitch, double yaw);

    // 한 주기 갱신. 오도·IMU 를 모두 한 번 이상 받았을 때만 참을 돌려준다.
    //   원본 run() 이 두 수신 플래그가 설 때까지 대기하는 것과 같은 성질이다.
    bool update();

    // 융합 자세. update() 가 참을 돌려준 뒤에만 의미가 있다.
    const Pose3D &pose() const
    {
        return pose_;
    }

    bool odomInitialized() const
    {
        return odom_init_;
    }
    bool imuInitialized() const
    {
        return imu_init_;
    }
    // 직전 update() 에서 IMU 관측을 실제로 반영했는가(게이트 통과 여부 진단용).
    bool lastImuApplied() const
    {
        return last_imu_applied_;
    }

  private:
    using Matrix6 = std::array<std::array<double, kStateDim>, kStateDim>;
    using Vector6 = std::array<double, kStateDim>;

    void predict(double d_trans, double d_yaw);
    // H 가 상태에서 고르는 인덱스 목록으로 주어지는 선형 관측 갱신.
    void correct(const int *indices, int count, const double *measurement, double noise);

    Params params_;
    Vector6 x_{};   // 상태 (x·y 는 내부 스케일)
    Matrix6 P_{};   // 공분산
    Pose3D pose_{}; // 출력(스케일 환원 후)

    bool odom_init_ = false;
    bool imu_init_ = false;
    bool last_imu_applied_ = false;

    bool has_odom_ = false;
    bool has_imu_ = false;
    Pose3D odom_cur_{}, odom_prev_{};
    double odom_yaw_rate_ = 0.0;
    double imu_roll_ = 0.0, imu_pitch_ = 0.0, imu_yaw_ = 0.0;
};

// 각도 정규화 → [−π, π).
double normalizeAngle(double a);

} // namespace odom_imu_ekf

#endif // ODOM_IMU_EKF_EKF_HPP
